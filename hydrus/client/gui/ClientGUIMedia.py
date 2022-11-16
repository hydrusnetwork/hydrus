import itertools
import os
import time
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusPaths
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.media import ClientMedia

def CopyHashesToClipboard( win: QW.QWidget, hash_type: str, medias: typing.Sequence[ ClientMedia.Media ] ):
    
    sha256_hashes = list( itertools.chain.from_iterable( ( media.GetHashes( ordered = True ) for media in medias ) ) )
    
    if hash_type == 'sha256':
        
        desired_hashes = sha256_hashes
        
    else:
        
        num_hashes = len( sha256_hashes )
        num_remote_sha256_hashes = len( [ itertools.chain.from_iterable( ( media.GetHashes( discriminant = CC.DISCRIMINANT_NOT_LOCAL, ordered = True ) for media in medias ) ) ] )
        
        desired_hashes = HG.client_controller.Read( 'file_hashes', sha256_hashes, 'sha256', hash_type )
        
        num_missing = num_hashes - len( desired_hashes )
        
        if num_missing > 0:
            
            if num_missing == num_hashes:
                
                message = 'Unfortunately, none of the {} hashes could be found.'.format( hash_type )
                
            else:
                
                message = 'Unfortunately, {} of the {} hashes could not be found.'.format( HydrusData.ToHumanInt( num_missing ), hash_type )
                
            
            if num_remote_sha256_hashes > 0:
                
                message += ' {} of the files you wanted are not currently in this client. If they have never visited this client, the lookup is impossible.'.format( HydrusData.ToHumanInt( num_remote_sha256_hashes ) )
                
            
            if num_remote_sha256_hashes < num_hashes:
                
                message += ' It could be that some of the local files are currently missing this information in the hydrus database. A file maintenance job (under the database menu) can repopulate this data.'
                
            
            QW.QMessageBox.warning( win, 'Warning', message )
            
        
    
    if len( desired_hashes ) > 0:
        
        text_lines = [ desired_hash.hex() for desired_hash in desired_hashes ]
        
        if HG.client_controller.new_options.GetBoolean( 'prefix_hash_when_copying' ):
            
            text_lines = [ '{}:{}'.format( hash_type, hex_hash ) for hex_hash in text_lines ]
            
        
        hex_hashes_text = os.linesep.join( text_lines )
        
        HG.client_controller.pub( 'clipboard', 'text', hex_hashes_text )
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', '{} {} hashes copied'.format( HydrusData.ToHumanInt( len( desired_hashes ) ), hash_type ) )
        
        HG.client_controller.pub( 'message', job_key )
        
        job_key.Delete( 2 )
        
    
def CopyMediaURLs( medias ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        urls.update( media_urls )
        
    
    urls = sorted( urls )
    
    urls_string = os.linesep.join( urls )
    
    HG.client_controller.pub( 'clipboard', 'text', urls_string )
    
def CopyMediaURLClassURLs( medias, url_class ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        for url in media_urls:
            
            # can't do 'url_class.matches', as it will match too many
            if HG.client_controller.network_engine.domain_manager.GetURLClass( url ) == url_class:
                
                urls.add( url )
                
            
        
    
    urls = sorted( urls )
    
    urls_string = os.linesep.join( urls )
    
    HG.client_controller.pub( 'clipboard', 'text', urls_string )
    
def DoClearFileViewingStats( win: QW.QWidget, flat_medias: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    if len( flat_medias ) == 0:
        
        return
        
    
    if len( flat_medias ) == 1:
        
        insert = 'this file'
        
    else:
        
        insert = 'these {} files'.format( HydrusData.ToHumanInt( len( flat_medias ) ) )
        
    
    message = 'Clear the file viewing count/duration and \'last viewed time\' for {}?'.format( insert )
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.Accepted:
        
        hashes = { m.GetHash() for m in flat_medias }
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_DELETE, hashes )
        
        HG.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] } )
        
    
def DoOpenKnownURLFromShortcut( win, media ):
    
    urls = media.GetLocationsManager().GetURLs()
    
    matched_labels_and_urls = []
    unmatched_urls = []
    
    if len( urls ) > 0:
        
        for url in urls:
            
            try:
                
                url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( url )
                
            except HydrusExceptions.URLClassException:
                
                continue
                
            
            if url_class is None:
                
                unmatched_urls.append( url )
                
            else:
                
                label = url_class.GetName() + ': ' + url
                
                matched_labels_and_urls.append( ( label, url ) )
                
            
        
        matched_labels_and_urls.sort()
        unmatched_urls.sort()
        
    
    if len( matched_labels_and_urls ) == 0:
        
        return
        
    elif len( matched_labels_and_urls ) == 1:
        
        url = matched_labels_and_urls[0][1]
        
    else:
        
        matched_labels_and_urls.extend( ( url, url ) for url in unmatched_urls )
        
        try:
            
            url = ClientGUIDialogsQuick.SelectFromList( win, 'Select which URL', matched_labels_and_urls, sort_tuples = False )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
    
    ClientPaths.LaunchURLInWebBrowser( url )
    

def EditDuplicateActionOptions( win: QW.QWidget, duplicate_type: int ):
    
    new_options = HG.client_controller.new_options
    
    duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, 'edit duplicate merge options' ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditDuplicateActionOptionsPanel( dlg, duplicate_type, duplicate_action_options )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            duplicate_action_options = panel.GetValue()
            
            new_options.SetDuplicateActionOptions( duplicate_type, duplicate_action_options )
            
        
    

def OpenExternally( media ):
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    client_files_manager = HG.client_controller.client_files_manager
    
    path = client_files_manager.GetFilePath( hash, mime )
    
    new_options = HG.client_controller.new_options
    
    launch_path = new_options.GetMimeLaunch( mime )
    
    HydrusPaths.LaunchFile( path, launch_path )
    
def OpenURLs( urls ):
    
    urls = sorted( urls )
    
    if len( urls ) > 1:
        
        message = 'Open the {} URLs in your web browser?'.format( len( urls ) )
        
        if len( urls ) > 10:
            
            message += ' This will take some time.'
            
        
        tlw = HG.client_controller.GetMainTLW()
        
        result = ClientGUIDialogsQuick.GetYesNo( tlw, message )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
    
    def do_it( urls ):
        
        job_key = None
        
        num_urls = len( urls )
        
        if num_urls > 5:
            
            job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
            
            job_key.SetStatusTitle( 'Opening URLs' )
            
            HG.client_controller.pub( 'message', job_key )
            
        
        try:
            
            for ( i, url ) in enumerate( urls ):
                
                if job_key is not None:
                    
                    ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                    
                    if should_quit:
                        
                        return
                        
                    
                    job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i + 1, num_urls ) )
                    job_key.SetVariable( 'popup_gauge_1', ( i + 1, num_urls ) )
                    
                
                ClientPaths.LaunchURLInWebBrowser( url )
                
                time.sleep( 1 )
                
            
        finally:
            
            if job_key is not None:
                
                job_key.Finish()
                
                job_key.Delete( 1 )
                
            
        
    
    HG.client_controller.CallToThread( do_it, urls )
    
def OpenMediaURLs( medias ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        urls.update( media_urls )
        
    
    OpenURLs( urls )
    
def OpenMediaURLClassURLs( medias, url_class ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        for url in media_urls:
            
            # can't do 'url_class.matches', as it will match too many
            if HG.client_controller.network_engine.domain_manager.GetURLClass( url ) == url_class:
                
                urls.add( url )
                
            
        
    
    OpenURLs( urls )
    

def ShowDuplicatesInNewPage( location_context: ClientLocation.LocationContext, hash, duplicate_type ):
    
    # TODO: this can be replaced by a call to the MediaResult when it holds these hashes
    hashes = HG.client_controller.Read( 'file_duplicate_hashes', location_context, hash, duplicate_type )
    
    if hashes is not None and len( hashes ) > 0:
        
        HG.client_controller.pub( 'new_page_query', location_context, initial_hashes = hashes )
        
    
