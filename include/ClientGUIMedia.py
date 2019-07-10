from . import HydrusConstants as HC
from . import ClientConstants as CC
from . import ClientCaches
from . import ClientData
from . import ClientDragDrop
from . import ClientFiles
from . import ClientGUICanvas
from . import ClientGUIDialogs
from . import ClientGUIDialogsManage
from . import ClientGUIDialogsQuick
from . import ClientGUIDuplicates
from . import ClientGUIExport
from . import ClientGUIFunctions
from . import ClientGUIMenus
from . import ClientGUIScrolledPanels
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUIScrolledPanelsManagement
from . import ClientGUIScrolledPanelsReview
from . import ClientGUIShortcuts
from . import ClientGUITags
from . import ClientGUITopLevelWindows
from . import ClientMedia
from . import ClientPaths
from . import ClientSearch
from . import ClientTags
from . import ClientThreading
import collections
from . import HydrusExceptions
from . import HydrusNetwork
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusTags
from . import HydrusThreading
import itertools
import json
import os
import random
import threading
import time
import traceback
import wx
import yaml
from . import HydrusData
from . import HydrusGlobals as HG

def CopyMediaURLs( medias ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        urls.update( media_urls )
        
    
    urls = list( urls )
    
    urls.sort()
    
    urls_string = os.linesep.join( urls )
    
    HG.client_controller.pub( 'clipboard', 'text', urls_string )
    
def CopyMediaURLClassURLs( medias, url_class ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        for url in media_urls:
            
            if url_class.Matches( url ):
                
                urls.add( url )
                
            
        
    
    urls = list( urls )
    
    urls.sort()
    
    urls_string = os.linesep.join( urls )
    
    HG.client_controller.pub( 'clipboard', 'text', urls_string )
    
def DoOpenKnownURLFromShortcut( win, media ):
    
    urls = media.GetLocationsManager().GetURLs()
    
    matched_labels_and_urls = []
    unmatched_urls = []
    
    if len( urls ) > 0:
        
        for url in urls:
            
            url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( url )
            
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
    
def OpenURLs( urls ):
    
    urls = list( urls )
    
    urls.sort()
    
    if len( urls ) > 1:
        
        message = 'Open the {} URLs in your web browser?'.format( len( urls ) )
        
        if len( urls ) > 10:
            
            message += ' This will take some time.'
            
        
        with ClientGUIDialogs.DialogYesNo( HG.client_controller.gui, message ) as dlg:
            
            if dlg.ShowModal() != wx.ID_YES:
                
                return
                
            
        
    
    def do_it( urls ):
        
        job_key = None
        
        num_urls = len( urls )
        
        if num_urls > 5:
            
            job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
            
            job_key.SetVariable( 'popup_title', 'Opening URLs' )
            
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
            
            if url_class.Matches( url ):
                
                urls.add( url )
                
            
        
    
    OpenURLs( urls )
    
def AddFileViewingStatsMenu( menu, focus_media ):
    
    view_style = HG.client_controller.new_options.GetInteger( 'file_viewing_stats_menu_display' )
    
    if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_NONE:
        
        return
        
    
    fvsm = focus_media.GetFileViewingStatsManager()
    
    if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_SUMMED:
        
        combined_line = fvsm.GetPrettyCombinedLine()
        
        ClientGUIMenus.AppendMenuLabel( menu, combined_line )
        
    else:
        
        media_line = fvsm.GetPrettyMediaLine()
        preview_line = fvsm.GetPrettyPreviewLine()
        
        if view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_ONLY:
            
            ClientGUIMenus.AppendMenuLabel( menu, media_line )
            
        elif view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_IN_SUBMENU:
            
            submenu = wx.Menu()
            
            ClientGUIMenus.AppendMenuLabel( submenu, preview_line )
            
            ClientGUIMenus.AppendMenu( menu, submenu, media_line )
            
        elif view_style == CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_STACKED:
            
            ClientGUIMenus.AppendMenuLabel( menu, media_line )
            ClientGUIMenus.AppendMenuLabel( menu, preview_line )
            
        
    
def AddKnownURLsViewCopyMenu( win, menu, focus_media, selected_media = None ):
    
    # figure out which urls this focused file has
    
    focus_urls = focus_media.GetLocationsManager().GetURLs()
    
    focus_matched_labels_and_urls = []
    focus_unmatched_urls = []
    focus_labels_and_urls = []
    
    if len( focus_urls ) > 0:
        
        for url in focus_urls:
            
            url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( url )
            
            if url_class is None:
                
                focus_unmatched_urls.append( url )
                
            else:
                
                label = url_class.GetName() + ': ' + url
                
                focus_matched_labels_and_urls.append( ( label, url ) )
                
            
        
        focus_matched_labels_and_urls.sort()
        focus_unmatched_urls.sort()
        
        focus_labels_and_urls = list( focus_matched_labels_and_urls )
        
        focus_labels_and_urls.extend( ( ( url, url ) for url in focus_unmatched_urls ) )
        
    
    # figure out which urls these selected files have
    
    selected_media_url_classes = set()
    multiple_or_unmatching_selection_url_classes = False
    
    if selected_media is not None and len( selected_media ) > 1:
        
        selected_media = ClientMedia.FlattenMedia( selected_media )
        
        SAMPLE_SIZE = 256
        
        if len( selected_media ) > SAMPLE_SIZE:
            
            selected_media_sample = random.sample( selected_media, SAMPLE_SIZE )
            
        else:
            
            selected_media_sample = selected_media
            
        
        for media in selected_media_sample:
            
            media_urls = media.GetLocationsManager().GetURLs()
            
            for url in media_urls:
                
                url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( url )
                
                if url_class is None:
                    
                    multiple_or_unmatching_selection_url_classes = True
                    
                else:
                    
                    selected_media_url_classes.add( url_class )
                    
                
            
        
        if len( selected_media_url_classes ) > 1:
            
            multiple_or_unmatching_selection_url_classes = True
            
        
    
    if len( focus_labels_and_urls ) > 0 or len( selected_media_url_classes ) > 0 or multiple_or_unmatching_selection_url_classes:
        
        urls_menu = wx.Menu()
        
        urls_visit_menu = wx.Menu()
        urls_copy_menu = wx.Menu()
        
        # copy each this file's urls (of a particular type)
        
        if len( focus_labels_and_urls ) > 0:
            
            for ( label, url ) in focus_labels_and_urls:
                
                ClientGUIMenus.AppendMenuItem( win, urls_visit_menu, label, 'Open this url in your web browser.', ClientPaths.LaunchURLInWebBrowser, url )
                ClientGUIMenus.AppendMenuItem( win, urls_copy_menu, label, 'Copy this url to your clipboard.', HG.client_controller.pub, 'clipboard', 'text', url )
                
            
        
        # copy this file's urls
        
        there_are_focus_url_classes_to_action = len( focus_matched_labels_and_urls ) > 1
        multiple_or_unmatching_focus_url_classes = len( focus_unmatched_urls ) > 0 and len( focus_labels_and_urls ) > 1 # if there are unmatched urls and more than one thing total
        
        if there_are_focus_url_classes_to_action or multiple_or_unmatching_focus_url_classes:
            
            ClientGUIMenus.AppendSeparator( urls_visit_menu )
            ClientGUIMenus.AppendSeparator( urls_copy_menu )
            
        
        if there_are_focus_url_classes_to_action:
            
            urls = [ url for ( label, url ) in focus_matched_labels_and_urls ]
            
            label = 'open this file\'s ' + HydrusData.ToHumanInt( len( urls ) ) + ' recognised urls in your web browser'
            
            ClientGUIMenus.AppendMenuItem( win, urls_visit_menu, label, 'Open these urls in your web browser.', OpenURLs, urls )
            
            urls_string = os.linesep.join( urls )
            
            label = 'copy this file\'s ' + HydrusData.ToHumanInt( len( urls ) ) + ' recognised urls to your clipboard'
            
            ClientGUIMenus.AppendMenuItem( win, urls_copy_menu, label, 'Copy these urls to your clipboard.', HG.client_controller.pub, 'clipboard', 'text', urls_string )
            
        
        if multiple_or_unmatching_focus_url_classes:
            
            urls = [ url for ( label, url ) in focus_labels_and_urls ]
            
            label = 'open this file\'s ' + HydrusData.ToHumanInt( len( urls ) ) + ' urls in your web browser'
            
            ClientGUIMenus.AppendMenuItem( win, urls_visit_menu, label, 'Open these urls in your web browser.', OpenURLs, urls )
            
            urls_string = os.linesep.join( urls )
            
            label = 'copy this file\'s ' + HydrusData.ToHumanInt( len( urls ) ) + ' urls to your clipboard'
            
            ClientGUIMenus.AppendMenuItem( win, urls_copy_menu, label, 'Copy this url to your clipboard.', HG.client_controller.pub, 'clipboard', 'text', urls_string )
            
        
        # now by url match type
        
        there_are_selection_url_classes_to_action = len( selected_media_url_classes ) > 0
        
        if there_are_selection_url_classes_to_action or multiple_or_unmatching_selection_url_classes:
            
            ClientGUIMenus.AppendSeparator( urls_visit_menu )
            ClientGUIMenus.AppendSeparator( urls_copy_menu )
            
        
        if there_are_selection_url_classes_to_action:
            
            selected_media_url_classes = list( selected_media_url_classes )
            
            selected_media_url_classes.sort( key = lambda url_class: url_class.GetName() )
            
            for url_class in selected_media_url_classes:
                
                label = 'open files\' ' + url_class.GetName() + ' urls in your web browser'
                
                ClientGUIMenus.AppendMenuItem( win, urls_visit_menu, label, 'Open this url class in your web browser for all files.', OpenMediaURLClassURLs, selected_media, url_class )
                
                label = 'copy files\' ' + url_class.GetName() + ' urls'
                
                ClientGUIMenus.AppendMenuItem( win, urls_copy_menu, label, 'Copy this url class for all files.', CopyMediaURLClassURLs, selected_media, url_class )
                
            
        
        # now everything
        
        if multiple_or_unmatching_selection_url_classes:
            
            label = 'open all files\' urls'
            
            ClientGUIMenus.AppendMenuItem( win, urls_visit_menu, label, 'Open urls in your web browser for all files.', OpenMediaURLs, selected_media )
            
            label = 'copy all files\' urls'
            
            ClientGUIMenus.AppendMenuItem( win, urls_copy_menu, label, 'Copy urls for all files.', CopyMediaURLs, selected_media )
            
        
        #
        
        ClientGUIMenus.AppendMenu( urls_menu, urls_visit_menu, 'open' )
        ClientGUIMenus.AppendMenu( urls_menu, urls_copy_menu, 'copy' )
        
        ClientGUIMenus.AppendMenu( menu, urls_menu, 'known urls' )
        
    
def AddServiceKeyLabelsToMenu( menu, service_keys, phrase ):
    
    services_manager = HG.client_controller.services_manager
    
    if len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        name = services_manager.GetName( service_key )
        
        label = phrase + ' ' + name
        
        ClientGUIMenus.AppendMenuLabel( menu, label )
        
    else:
        
        submenu = wx.Menu()
        
        for service_key in service_keys:
            
            name = services_manager.GetName( service_key )
            
            ClientGUIMenus.AppendMenuLabel( submenu, name )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, phrase + '\u2026' )
        
    
def AddServiceKeysToMenu( event_handler, menu, service_keys, phrase, description, callable ):
    
    services_manager = HG.client_controller.services_manager
    
    if len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        name = services_manager.GetName( service_key )
        
        label = phrase + ' ' + name
        
        ClientGUIMenus.AppendMenuItem( event_handler, menu, label, description, callable, service_key )
        
    else:
        
        submenu = wx.Menu()
        
        for service_key in service_keys: 
            
            name = services_manager.GetName( service_key )
            
            ClientGUIMenus.AppendMenuItem( event_handler, submenu, name, description, callable, service_key )
            
        
        ClientGUIMenus.AppendMenu( menu, submenu, phrase + '\u2026' )
        
    
class MediaPanel( ClientMedia.ListeningMediaList, wx.ScrolledCanvas ):
    
    def __init__( self, parent, page_key, file_service_key, media_results ):
        
        wx.ScrolledCanvas.__init__( self, parent, size = ( 20, 20 ), style = wx.BORDER_SUNKEN )
        ClientMedia.ListeningMediaList.__init__( self, file_service_key, media_results )
        
        self._UpdateBackgroundColour()
        
        self.SetScrollRate( 0, 50 )
        
        self._page_key = page_key
        
        self._focussed_media = None
        self._next_best_media_after_focussed_media_removed = None
        self._shift_focussed_media = None
        
        self._selected_media = set()
        
        HG.client_controller.sub( self, 'AddMediaResults', 'add_media_results' )
        HG.client_controller.sub( self, 'SetFocussedMedia', 'set_focus' )
        HG.client_controller.sub( self, 'Collect', 'collect_media' )
        HG.client_controller.sub( self, 'Sort', 'sort_media' )
        HG.client_controller.sub( self, 'FileDumped', 'file_dumped' )
        HG.client_controller.sub( self, 'RemoveMedia', 'remove_media' )
        HG.client_controller.sub( self, '_UpdateBackgroundColour', 'notify_new_colourset' )
        HG.client_controller.sub( self, 'SelectByTags', 'select_files_with_tags' )
        
        self._due_a_forced_selection_pub = False
        
        self._PublishSelectionChange()
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'media' ] )
        
    
    def _Archive( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_INBOX )
        
        if len( hashes ) > 0:
            
            if HC.options[ 'confirm_archive' ]:
                
                if len( hashes ) > 1:
                    
                    message = 'Archive ' + HydrusData.ToHumanInt( len( hashes ) ) + ' files?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() != wx.ID_YES:
                            
                            return
                            
                        
                    
                
            
            HG.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes ) ] } )
            
        
    
    def _ArchiveDeleteFilter( self ):
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH, selected_media = set( self._selected_media ), for_media_viewer = True )
        
        if len( media_results ) > 0:
            
            canvas_frame = ClientGUICanvas.CanvasFrame( self.GetTopLevelParent() )
            
            canvas_window = ClientGUICanvas.CanvasMediaListFilterArchiveDelete( canvas_frame, self._page_key, media_results )
            
            canvas_frame.SetCanvas( canvas_window )
            
        
    
    def _CopyBMPToClipboard( self ):
        
        if self._focussed_media is not None:
            
            media = self._focussed_media.GetDisplayMedia()
            
            if media.GetMime() in HC.IMAGES and media.GetDuration() is None:
                
                HG.client_controller.pub( 'clipboard', 'bmp', media )
                
            else:
                
                wx.MessageBox( 'Sorry, cannot take bmps of anything but static images right now!' )
                
            
        
    
    def _CopyFilesToClipboard( self ):
        
        client_files_manager = HG.client_controller.client_files_manager
        
        media = self._GetSelectedFlatMedia( discriminant = CC.DISCRIMINANT_LOCAL )
        
        paths = []
        
        for m in media:
            
            hash = m.GetHash()
            mime = m.GetMime()
            
            path = client_files_manager.GetFilePath( hash, mime, check_file_exists = False )
            
            paths.append( path )
            
        
        HG.client_controller.pub( 'clipboard', 'paths', paths )
        
    
    def _CopyHashToClipboard( self, hash_type ):
        
        display_media = self._focussed_media.GetDisplayMedia()
        
        sha256_hash = display_media.GetHash()
        
        if hash_type == 'sha256':
            
            hex_hash = sha256_hash.hex()
            
        else:
            
            if display_media.GetLocationsManager().IsLocal():
                
                ( other_hash, ) = HG.client_controller.Read( 'file_hashes', ( sha256_hash, ), 'sha256', hash_type )
                
                hex_hash = other_hash.hex()
                
            else:
                
                wx.MessageBox( 'Unfortunately, you do not have that file in your database, so its non-sha256 hashes are unknown.' )
                
                return
                
            
        
        HG.client_controller.pub( 'clipboard', 'text', hex_hash )
        
    
    def _CopyHashesToClipboard( self, hash_type ):
        
        if hash_type == 'sha256':
            
            hex_hashes = os.linesep.join( [ hash.hex() for hash in self._GetSelectedHashes( ordered = True ) ] )
            
        else:
            
            sha256_hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_LOCAL, ordered = True )
            
            if len( sha256_hashes ) > 0:
                
                other_hashes = HG.client_controller.Read( 'file_hashes', sha256_hashes, 'sha256', hash_type )
                
                hex_hashes = os.linesep.join( [ other_hash.hex() for other_hash in other_hashes ] )
                
            else:
                
                wx.MessageBox( 'Unfortunately, none of those files are in your database, so their non-sha256 hashes are unknown.' )
                
                return
                
            
        
        HG.client_controller.pub( 'clipboard', 'text', hex_hashes )
        
    
    def _CopyPathToClipboard( self ):
        
        display_media = self._focussed_media.GetDisplayMedia()
        
        client_files_manager = HG.client_controller.client_files_manager
        
        path = client_files_manager.GetFilePath( display_media.GetHash(), display_media.GetMime() )
        
        HG.client_controller.pub( 'clipboard', 'text', path )
        
    
    def _CopyPathsToClipboard( self ):
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, selected_media = set( self._selected_media ) )
        
        client_files_manager = HG.client_controller.client_files_manager
        
        paths = []
        
        for media_result in media_results:
            
            paths.append( client_files_manager.GetFilePath( media_result.GetHash(), media_result.GetMime(), check_file_exists = False ) )
            
        
        text = os.linesep.join( paths )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _CopyServiceFilenameToClipboard( self, service_key ):
        
        display_media = self._focussed_media.GetDisplayMedia()
        
        hash = display_media.GetHash()
        
        ( filename, ) = HG.client_controller.Read( 'service_filenames', service_key, { hash } )
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        if service.GetServiceType() == HC.IPFS:
            
            multihash_prefix = service.GetMultihashPrefix()
            
            filename = multihash_prefix + filename
            
        
        HG.client_controller.pub( 'clipboard', 'text', filename )
        
    
    def _CopyServiceFilenamesToClipboard( self, service_key ):
        
        prefix = ''
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
        if service.GetServiceType() == HC.IPFS:
            
            prefix = service.GetMultihashPrefix()
            
        
        hashes = self._GetSelectedHashes( has_location = service_key )
        
        if len( hashes ) > 0:
            
            filenames = [ prefix + filename for filename in HG.client_controller.Read( 'service_filenames', service_key, hashes ) ]
            
            if len( filenames ) > 0:
                
                copy_string = os.linesep.join( filenames )
                
                HG.client_controller.pub( 'clipboard', 'text', copy_string )
                
            else:
                
                HydrusData.ShowText( 'Could not find any service filenames for that selection!' )
                
            
        else:
            
            HydrusData.ShowText( 'Could not find any files with the requested service!' )
            
        
    
    def _Delete( self, file_service_key = None ):
        
        if file_service_key is None or file_service_key in ( CC.LOCAL_FILE_SERVICE_KEY, CC.TRASH_SERVICE_KEY ):
            
            default_reason = 'Deleted from Media Page.'
            
        else:
            
            default_reason = 'admin'
            
        
        try:
            
            ( involves_physical_delete, jobs ) = ClientGUIDialogsQuick.GetDeleteFilesJobs( self, self._selected_media, default_reason, suggested_file_service_key = file_service_key )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if involves_physical_delete:
            
            self._SetFocussedMedia( None )
            
        
        def do_it( jobs ):
            
            for service_keys_to_content_updates in jobs:
                
                HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
            
        
        HG.client_controller.CallToThread( do_it, jobs )
        
    
    def _DeselectSelect( self, media_to_deselect, media_to_select ):
        
        if len( media_to_deselect ) > 0:
            
            for m in media_to_deselect: m.Deselect()
            
            self._RedrawMedia( media_to_deselect )
            
            self._selected_media.difference_update( media_to_deselect )
            
        
        if len( media_to_select ) > 0:
            
            for m in media_to_select: m.Select()
            
            self._RedrawMedia( media_to_select )
            
            self._selected_media.update( media_to_select )
            
        
        self._PublishSelectionChange()
        
    
    def _DownloadSelected( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_NOT_LOCAL )
        
        self._DownloadHashes( hashes )
        
    
    def _DownloadHashes( self, hashes ):
        
        HG.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, hashes ) ] } )
        
    
    def _EditDuplicateActionOptions( self, duplicate_type ):
        
        new_options = HG.client_controller.new_options
        
        duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit duplicate merge options' ) as dlg_2:
            
            panel = ClientGUIScrolledPanelsEdit.EditDuplicateActionOptionsPanel( dlg_2, duplicate_type, duplicate_action_options )
            
            dlg_2.SetPanel( panel )
            
            if dlg_2.ShowModal() == wx.ID_OK:
                
                duplicate_action_options = panel.GetValue()
                
                new_options.SetDuplicateActionOptions( duplicate_type, duplicate_action_options )
                
            
        
    
    def _ExportFiles( self, do_export_and_then_quit = False ):
        
        if len( self._selected_media ) > 0:
            
            flat_media = []
            
            for media in self._sorted_media:
                
                if media in self._selected_media:
                    
                    if media.IsCollection():
                        
                        flat_media.extend( media.GetFlatMedia() )
                        
                    else:
                        
                        flat_media.append( media )
                        
                    
                
            
            frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, 'export files' )
            
            panel = ClientGUIExport.ReviewExportFilesPanel( frame, flat_media, do_export_and_then_quit = do_export_and_then_quit )
            
            frame.SetPanel( panel )
            
        
    
    def _ExportTags( self ):
        
        if len( self._selected_media ) > 0:
            
            services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.COMBINED_TAG ) )
            
            service_keys = [ service.GetServiceKey() for service in services ]
            
            service_key = ClientGUIDialogs.SelectServiceKey( service_keys = service_keys )
            
            hashes = self._GetSelectedHashes()
            
            if service_key is not None:
                
                ClientGUITags.ExportToHTA( self, service_key, hashes )
                
            
        
    
    def _FullScreen( self, first_media = None ):
        
        if self._focussed_media is not None:
            
            display_media = self._focussed_media.GetDisplayMedia()
            
            new_options = HG.client_controller.new_options
            
            media_show_action = new_options.GetMediaShowAction( display_media.GetMime() )
            
            if media_show_action == CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY:
                
                hash = display_media.GetHash()
                mime = display_media.GetMime()
                
                client_files_manager = HG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                new_options = HG.client_controller.new_options
                
                launch_path = new_options.GetMimeLaunch( mime )
                
                HydrusPaths.LaunchFile( path, launch_path )
                
                return
                
            elif media_show_action == CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW:
                
                return
                
            
        
        media_results = self.GenerateMediaResults( discriminant = CC.DISCRIMINANT_LOCAL, for_media_viewer = True )
        
        if len( media_results ) > 0:
            
            if first_media is None and self._focussed_media is not None: first_media = self._focussed_media
            
            if first_media is not None and first_media.GetLocationsManager().IsLocal(): first_hash = first_media.GetDisplayMedia().GetHash()
            else: first_hash = None
            
            canvas_frame = ClientGUICanvas.CanvasFrame( self.GetTopLevelParent() )
            
            canvas_window = ClientGUICanvas.CanvasMediaListBrowser( canvas_frame, self._page_key, media_results, first_hash )
            
            canvas_frame.SetCanvas( canvas_window )
            
        
    
    def _GetNumSelected( self ):
        
        return sum( [ media.GetNumFiles() for media in self._selected_media ] )
        
    
    def _GetPrettyStatus( self ):
        
        num_files = len( self._hashes )
        
        num_selected = self._GetNumSelected()
        
        ( num_files_descriptor, selected_files_descriptor ) = self._GetSortedSelectedMimeDescriptors()
        
        if num_files == 1:
            
            num_files_string = '1 ' + num_files_descriptor
            
        else:
            
            num_files_string = HydrusData.ToHumanInt( num_files ) + ' ' + num_files_descriptor + 's'
            
        
        s = num_files_string # 23 files
        
        if num_selected == 0:
            
            if num_files > 0:
                
                pretty_total_size = self._GetPrettyTotalSize()
                
                s += ' - totalling ' + pretty_total_size
                
            
        else:
            
            s += ' - '
            
            if num_selected == 1 or selected_files_descriptor == num_files_descriptor:
                
                selected_files_string = HydrusData.ToHumanInt( num_selected )
                
            else:
                
                selected_files_string = HydrusData.ToHumanInt( num_selected ) + ' ' + selected_files_descriptor + 's'
                
            
            if num_selected == 1: # 23 files - 1 video selected, file_info
                
                ( selected_media, ) = self._selected_media
                
                s += selected_files_string + ' selected, ' + ', '.join( selected_media.GetPrettyInfoLines() )
                
            else: # 23 files - 5 selected, selection_info
                
                num_inbox = sum( ( media.GetNumInbox() for media in self._selected_media ) )
                
                if num_inbox == num_selected:
                    
                    inbox_phrase = 'all in inbox, '
                    
                elif num_inbox == 0:
                    
                    inbox_phrase = 'all archived, '
                    
                else:
                    
                    inbox_phrase = HydrusData.ToHumanInt( num_inbox ) + ' in inbox and ' + HydrusData.ToHumanInt( num_selected - num_inbox ) + ' archived, '
                    
                
                pretty_total_size = self._GetPrettyTotalSize( only_selected = True )
                
                s += selected_files_string + ' selected, ' + inbox_phrase + 'totalling ' + pretty_total_size
                
            
        
        return s
        
    
    def _GetPrettyTotalSize( self, only_selected = False ):
        
        if only_selected:
            
            media_source = self._selected_media
            
        else:
            
            media_source = self._sorted_media
            
        
        total_size = sum( [ media.GetSize() for media in media_source ] )
        
        unknown_size = False in ( media.IsSizeDefinite() for media in media_source )
        
        if total_size == 0:
            
            if unknown_size:
                
                return 'unknown size'
                
            else:
                
                return HydrusData.ToHumanBytes( 0 )
                
            
        else:
            
            if unknown_size:
                
                return HydrusData.ToHumanBytes( total_size ) + ' + some unknown size'
                
            else:
                
                return HydrusData.ToHumanBytes( total_size )
                
            
        
    
    def _GetSelectedHashes( self, has_location = None, discriminant = None, not_uploaded_to = None, ordered = False ):
        
        if ordered:
            
            result = []
            
            for media in self._sorted_media:
                
                if media in self._selected_media:
                    
                    result.extend( media.GetHashes( has_location, discriminant, not_uploaded_to, ordered ) )
                    
                
            
        else:
            
            result = set()
            
            for media in self._selected_media:
                
                result.update( media.GetHashes( has_location, discriminant, not_uploaded_to, ordered ) )
                
            
        
        return result
        
    
    def _GetSelectedCollections( self ):
        
        sorted_selected_collections = [ media for media in self._sorted_media if media.IsCollection() and media in self._selected_media ]
        
        return sorted_selected_collections
        

    def _GetSelectedFlatMedia( self, has_location = None, discriminant = None, not_uploaded_to = None ):
        
        # this now always delivers sorted results
        
        sorted_selected_media = [ media for media in self._sorted_media if media in self._selected_media ]
        
        flat_media = ClientMedia.FlattenMedia( sorted_selected_media )
        
        flat_media = [ media for media in flat_media if media.MatchesDiscriminant( has_location = has_location, discriminant = discriminant, not_uploaded_to = not_uploaded_to ) ]
        
        return flat_media
        
    
    def _GetSimilarTo( self, max_hamming ):
        
        if self._focussed_media is not None:
            
            hash = self._focussed_media.GetDisplayMedia().GetHash()
            
            initial_predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( hash, max_hamming ) ) ]
            
            HG.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_predicates = initial_predicates )
            
        
    
    def _GetSortedSelectedMimeDescriptors( self ):
        
        def GetDescriptor( classes ):
            
            if len( classes ) == 0:
                
                return 'file'
                
            
            if len( classes ) == 1:
                
                ( mime, ) = classes
                
                return HC.mime_string_lookup[ mime ]
                
            
            if len( classes.difference( HC.IMAGES ) ) == 0:
                
                return 'image'
                
            elif len( classes.difference( HC.VIDEO ) ) == 0:
                
                return 'video'
                
            elif len( classes.difference( HC.AUDIO ) ) == 0:
                
                return 'audio file'
                
            else:
                
                return 'file'
                
            
        
        if len( self._sorted_media ) > 1000:
            
            sorted_mime_descriptor = 'file'
            
        else:
            
            sorted_mimes = { media.GetMime() for media in self._sorted_media }
            
            sorted_mime_descriptor = GetDescriptor( sorted_mimes )
            
        
        if len( self._selected_media ) > 1000:
            
            selected_mime_descriptor = 'file'
            
        else:
            
            selected_mimes = { media.GetMime() for media in self._selected_media }
            
            selected_mime_descriptor = GetDescriptor( selected_mimes )
            
        
        return ( sorted_mime_descriptor, selected_mime_descriptor )
        
    
    def _HitMedia( self, media, ctrl, shift ):
        
        if media is None:
            
            if not ctrl and not shift:
                
                self._Select( 'none' )
                self._SetFocussedMedia( None )
                self._shift_focussed_media = None
                
            
        else:
            
            if ctrl:
                
                if media.IsSelected():
                    
                    self._DeselectSelect( ( media, ), () )
                    
                    if self._focussed_media == media:
                        
                        self._SetFocussedMedia( None )
                        
                    
                    self._shift_focussed_media = None
                    
                else:
                    
                    self._DeselectSelect( (), ( media, ) )
                    
                    if self._focussed_media is None: self._SetFocussedMedia( media )
                    
                    self._shift_focussed_media = media
                    
                
            elif shift and self._shift_focussed_media is not None:
                
                start_index = self._sorted_media.index( self._shift_focussed_media )
                
                end_index = self._sorted_media.index( media )
                
                if start_index < end_index: media_to_select = set( self._sorted_media[ start_index : end_index + 1 ] )
                else: media_to_select = set( self._sorted_media[ end_index : start_index + 1 ] )
                
                self._DeselectSelect( (), media_to_select )
                
                self._SetFocussedMedia( media )
                
                self._shift_focussed_media = media
                
            else:
                
                if not media.IsSelected():
                    
                    self._DeselectSelect( self._selected_media, ( media, ) )
                    
                else:
                    
                    self._PublishSelectionChange()
                    
                
                self._SetFocussedMedia( media )
                self._shift_focussed_media = media
                
            
        
    
    def _Inbox( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_ARCHIVE )
        
        if len( hashes ) > 0:
            
            if HC.options[ 'confirm_archive' ]:
                
                if len( hashes ) > 1:
                    
                    message = 'Send ' + HydrusData.ToHumanInt( len( hashes ) ) + ' files to inbox?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                        
                        if dlg.ShowModal() != wx.ID_YES: return
                        
                    
                
            
            HG.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY: [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes ) ] } )
            
        
    
    def _ManageNotes( self ):
        
        def wx_do_it( media, notes ):
            
            if not self:
                
                return
                
            
            title = 'manage notes'
            
            with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg, [ 'manage_file_notes' ] )
                
                control = wx.TextCtrl( panel, style = wx.TE_MULTILINE )
                
                size = ClientGUIFunctions.ConvertTextToPixels( control, ( 80, 14 ) )
                
                control.SetInitialSize( size )
                
                control.SetValue( notes )
                
                panel.SetControl( control )
                
                dlg.SetPanel( panel )
                
                wx.CallAfter( control.SetFocus )
                wx.CallAfter( control.SetInsertionPointEnd )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    notes = control.GetValue()
                    
                    hash = media.GetHash()
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( notes, hash ) ) ]
                    
                    service_keys_to_content_updates = { CC.LOCAL_NOTES_SERVICE_KEY : content_updates }
                    
                    HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                    
                
            
            self.SetFocus()
            
        
        def thread_wait( media ):
            
            # if it ultimately makes sense, I can load/cache notes in the media result
            
            notes = HG.client_controller.Read( 'file_notes', media.GetHash() )
            
            wx.CallAfter( wx_do_it, media, notes )
            
        
        if self._focussed_media is None:
            
            return
            
        
        HG.client_controller.CallToThread( thread_wait, self._focussed_media.GetDisplayMedia() )
        
    
    def _ManageRatings( self ):
        
        if len( self._selected_media ) > 0:
            
            if len( HG.client_controller.services_manager.GetServices( HC.RATINGS_SERVICES ) ) > 0:
                
                flat_media = self._GetSelectedFlatMedia()
                
                with ClientGUIDialogsManage.DialogManageRatings( self, flat_media ) as dlg:
                    
                    dlg.ShowModal()
                    
                
                self.SetFocus()
                
            
        
    
    def _ManageTags( self ):
        
        if len( self._selected_media ) > 0:
            
            num_files = self._GetNumSelected()
            
            title = 'manage tags for ' + HydrusData.ToHumanInt( num_files ) + ' files'
            frame_key = 'manage_tags_dialog'
            
            with ClientGUITopLevelWindows.DialogManage( self, title, frame_key ) as dlg:
                
                panel = ClientGUITags.ManageTagsPanel( dlg, self._file_service_key, self._selected_media )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
            self.SetFocus()
            
        
    
    def _ManageURLs( self ):
        
        if len( self._selected_media ) > 0:
            
            num_files = self._GetNumSelected()
            
            title = 'manage urls for {} files'.format( num_files )
            
            with ClientGUITopLevelWindows.DialogManage( self, title ) as dlg:
                
                panel = ClientGUIScrolledPanelsManagement.ManageURLsPanel( dlg, self._selected_media )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
            self.SetFocus()
            
        
    
    def _ModifyUploaders( self, file_service_key ):
        
        wx.MessageBox( 'this does not work yet!' )
        
        return
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            contents = [ HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, [ hash ] ) for hash in hashes ]
            
            subject_accounts = 'blah' # fetch subjects from server with the contents
            
            with ClientGUIDialogs.DialogModifyAccounts( self, file_service_key, subject_accounts ) as dlg: dlg.ShowModal()
            
            self.SetFocus()
            
        
    
    def _OpenExternally( self ):
        
        if self._focussed_media is not None:
            
            open_externally_media = self._focussed_media.GetDisplayMedia()
            
            if open_externally_media.GetLocationsManager().IsLocal():
                
                hash = open_externally_media.GetHash()
                mime = open_externally_media.GetMime()
                
                client_files_manager = HG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                new_options = HG.client_controller.new_options
                
                launch_path = new_options.GetMimeLaunch( mime )
                
                HydrusPaths.LaunchFile( path, launch_path )
                
                HG.client_controller.pub( 'media_focus_went_to_external_program', self._page_key )
                
            
        
    
    def _OpenFileInWebBrowser( self ):
        
        if self._focussed_media is not None:
            
            if self._focussed_media.GetLocationsManager().IsLocal():
                
                hash = self._focussed_media.GetHash()
                mime = self._focussed_media.GetMime()
                
                client_files_manager = HG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                self._SetFocussedMedia( None )
                
                ClientPaths.LaunchPathInWebBrowser( path )
                
            
        
    
    def _OpenFileLocation( self ):
        
        if self._focussed_media is not None:
            
            if self._focussed_media.GetLocationsManager().IsLocal():
                
                hash = self._focussed_media.GetHash()
                mime = self._focussed_media.GetMime()
                
                client_files_manager = HG.client_controller.client_files_manager
                
                path = client_files_manager.GetFilePath( hash, mime )
                
                self._SetFocussedMedia( None )
                
                HydrusPaths.OpenFileLocation( path )
                
            
        
    
    def _OpenKnownURL( self ):
        
        if self._focussed_media is not None:
            
            DoOpenKnownURLFromShortcut( self, self._focussed_media )
            
        
    
    def _PetitionFiles( self, remote_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:
            
            remote_service = HG.client_controller.services_manager.GetService( remote_service_key )
            
            service_type = remote_service.GetServiceType()
            
            if service_type == HC.FILE_REPOSITORY:
                
                if len( hashes ) == 1:
                    
                    message = 'Enter a reason for this file to be removed from ' + remote_service.GetName() + '.'
                    
                else:
                    
                    message = 'Enter a reason for these ' + HydrusData.ToHumanInt( len( hashes ) ) + ' files to be removed from ' + remote_service.GetName() + '.'
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        reason = dlg.GetValue()
                        
                        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes, reason = reason )
                        
                        service_keys_to_content_updates = { remote_service_key : ( content_update, ) }
                        
                        HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                        
                    
                
                self.SetFocus()
                
            elif service_type == HC.IPFS:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes, reason = 'ipfs' )
                
                service_keys_to_content_updates = { remote_service_key : ( content_update, ) }
                
                HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
        
    
    def _PublishSelectionChange( self, force_reload = False ):
        
        if HG.client_controller.gui.IsCurrentPage( self._page_key ):
            
            if len( self._selected_media ) == 0:
                
                tags_media = self._sorted_media
                
            else:
                
                tags_media = self._selected_media
                
            
            force_reload = force_reload or self._due_a_forced_selection_pub
            
            HG.client_controller.pub( 'new_tags_selection', self._page_key, tags_media, force_reload = force_reload )
            HG.client_controller.pub( 'new_page_status', self._page_key, self._GetPrettyStatus() )
            
            if force_reload:
                
                self._due_a_forced_selection_pub = False
                
            
        else:
            
            if force_reload:
                
                self._due_a_forced_selection_pub = True
                
            
        
    
    def _PublishSelectionIncrement( self, medias ):
        
        if HG.client_controller.gui.IsCurrentPage( self._page_key ):
            
            HG.client_controller.pub( 'increment_tags_selection', self._page_key, medias )
            HG.client_controller.pub( 'new_page_status', self._page_key, self._GetPrettyStatus() )
            
        else:
            
            self._due_a_forced_selection_pub = True
            
        
    
    def _RecalculateVirtualSize( self ): pass
    
    def _RedrawMedia( self, media ): pass
    
    def _Remove( self ):
        
        singletons = [ media for media in self._selected_media if not media.IsCollection() ]
        
        collections = [ media for media in self._selected_media if media.IsCollection() ]
        
        self._RemoveMediaDirectly( singletons, collections )
        
    
    def _RegenerateFileData( self, job_type ):
        
        flat_media = self._GetSelectedFlatMedia()
        
        num_files = len( flat_media )
        
        if num_files > 0:
            
            if job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_COMPLETE:
                
                text = 'This will reparse the {} selected files\' metadata and regenerate their thumbnails.'.format( HydrusData.ToHumanInt( num_files ) )
                text += os.linesep * 2
                text += 'If the files were imported before some more recent improvement in the parsing code (such as EXIF rotation or bad video resolution or duration or frame count calculation), this will update them.'
                
            elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL:
                
                text = 'This will force-regenerate the {} selected files\' thumbnails.'.format( HydrusData.ToHumanInt( num_files ) )
                
            elif job_type == ClientFiles.REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL:
                
                text = 'This will regenerate the {} selected files\' thumbnails, but only if they are the wrong size.'.format( HydrusData.ToHumanInt( num_files ) )
                
            
            do_it_now = True
            
            if num_files > 50:
                
                text += os.linesep * 2
                text += 'You have selected {} files, so this job may take some time. If you would like, you can simply schedule it to happen in idle time.'.format( HydrusData.ToHumanInt( num_files ) )
                
                yes_tuples = []
                
                yes_tuples.append( ( 'do it now', 'now' ) )
                yes_tuples.append( ( 'do it later', 'later' ) )
                
                with ClientGUIDialogs.DialogYesYesNo( self, text, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        value = dlg.GetValue()
                        
                        if value == 'now':
                            
                            do_it_now = True
                            
                        elif value == 'later':
                            
                            do_it_now = False
                            
                        else:
                            
                            return
                            
                        
                    else:
                        
                        return
                        
                    
                
            else:
                
                with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES:
                        
                        return
                        
                    
                
            
            if do_it_now:
                
                self._SetFocussedMedia( None )
                
                time.sleep( 0.1 )
                
                HG.client_controller.CallToThread( HG.client_controller.files_maintenance_manager.RunJobImmediately, flat_media, job_type )
                
            else:
                
                hashes = { media.GetHash() for media in flat_media }
                
                HG.client_controller.CallToThread( HG.client_controller.files_maintenance_manager.ScheduleJob, hashes, job_type )
                
            
        
    
    def _RescindDownloadSelected( self ):
        
        hashes = self._GetSelectedHashes( discriminant = CC.DISCRIMINANT_NOT_LOCAL )
        
        HG.client_controller.Write( 'content_updates', { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PEND, hashes ) ] } )
        
    
    def _RescindPetitionFiles( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            HG.client_controller.Write( 'content_updates', { file_service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PETITION, hashes ) ] } )
            
        
    
    def _RescindUploadFiles( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:   
            
            HG.client_controller.Write( 'content_updates', { file_service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PEND, hashes ) ] } )
            
        
    
    def _Select( self, select_type, extra_info = None ):
        
        if select_type == 'all':
            
            self._DeselectSelect( [], self._sorted_media )
            
        else:
            
            if select_type == 'invert':
                
                ( media_to_deselect, media_to_select ) = ( self._selected_media, { m for m in self._sorted_media if m not in self._selected_media } )
                
            elif select_type == 'none':
                
                ( media_to_deselect, media_to_select ) = ( self._selected_media, [] )
                
            elif select_type in ( 'inbox', 'archive' ):
                
                inbox_media = [ m for m in self._sorted_media if m.HasInbox() ]
                archive_media = [ m for m in self._sorted_media if not m.HasInbox() ]
                
                if select_type == 'inbox':
                    
                    media_to_deselect = [ m for m in archive_media if m in self._selected_media ]
                    media_to_select = [ m for m in inbox_media if m not in self._selected_media ]
                    
                elif select_type == 'archive':
                    
                    media_to_deselect = [ m for m in inbox_media if m in self._selected_media ]
                    media_to_select = [ m for m in archive_media if m not in self._selected_media ]
                    
                
            elif select_type == 'file_service':
                
                file_service_key = extra_info
                
                media_to_deselect = [ m for m in self._selected_media if file_service_key not in m.GetLocationsManager().GetCurrent() ]
                media_to_select = [ m for m in self._sorted_media if m not in self._selected_media and file_service_key in m.GetLocationsManager().GetCurrent() ]
                
            elif select_type in ( 'local', 'remote' ):
                
                local_media = [ m for m in self._sorted_media if m.GetLocationsManager().IsLocal() ]
                remote_media = [ m for m in self._sorted_media if m.GetLocationsManager().IsRemote() ]
                
                if select_type == 'local':
                    
                    media_to_deselect = [ m for m in remote_media if m in self._selected_media ]
                    media_to_select = [ m for m in local_media if m not in self._selected_media ]
                    
                elif select_type == 'remote':
                    
                    media_to_deselect = [ m for m in local_media if m in self._selected_media ]
                    media_to_select = [ m for m in remote_media if m not in self._selected_media ]
                    
                
            elif select_type == 'tags':
                
                ( and_or_or, select_tags ) = extra_info
                
                if and_or_or == 'AND':
                    
                    matching_media = { m for m in self._sorted_media if len( m.GetTagsManager().GetCurrentAndPending().intersection( select_tags ) ) == len( select_tags ) }
                    
                elif and_or_or == 'OR':
                    
                    matching_media = { m for m in self._sorted_media if len( m.GetTagsManager().GetCurrentAndPending().intersection( select_tags ) ) > 0 }
                    
                
                media_to_deselect = self._selected_media.difference( matching_media )
                media_to_select = matching_media.difference( self._selected_media )
                
            
            if self._focussed_media in media_to_deselect:
                
                self._SetFocussedMedia( None )
                
            
            self._DeselectSelect( media_to_deselect, media_to_select )
            
            self._shift_focussed_media = None
            
        
    
    def _SetCollectionsAsAlternate( self ):
        
        collections = self._GetSelectedCollections()
        
        if len( collections ) > 0:
            
            message = 'Are you sure you want to set files in the selected collections as alternates? Each collection will be considered a separate group of alternates.'
            message += os.linesep * 2
            message += 'Be careful applying this to large groups--any more than a few dozen files, and the client could hang a long time.'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    for collection in collections:
                        
                        media_group = collection.GetFlatMedia()
                        
                        self._SetDuplicates( HC.DUPLICATE_ALTERNATE, media_group = media_group, silent = True )
                        
                    
                
            
        
    
    def _SetDuplicates( self, duplicate_type, media_pairs = None, media_group = None, duplicate_action_options = None, silent = False ):
        
        yes_no_text = 'unknown duplicate action'
        
        if duplicate_action_options is None:
            
            yes_no_text = 'apply "{}"'.format( HC.duplicate_type_string_lookup[ duplicate_type ] )
            
            if duplicate_type in [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ] or ( HG.client_controller.new_options.GetBoolean( 'advanced_mode' ) and duplicate_type == HC.DUPLICATE_ALTERNATE ):
                
                yes_no_text += ' (with default duplicate metadata merge options)'
                
                new_options = HG.client_controller.new_options
                
                duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
                
            
        else:
            
            yes_no_text = 'apply "{}" (with custom duplicate metadata merge options)'.format( HC.duplicate_type_string_lookup[ duplicate_type ] )
            
        
        file_deletion_reason = 'Deleted from duplicate action on Media Page ({}).'.format( yes_no_text )
        
        if media_pairs is None:
            
            if media_group is None:
                
                flat_media = self._GetSelectedFlatMedia()
                
            else:
                
                flat_media = ClientMedia.FlattenMedia( media_group )
                
            
            if len( flat_media ) < 2:
                
                return False
                
            
            first_media = flat_media[0]
            
            if duplicate_type in ( HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_ALTERNATE ):
                
                media_pairs = list( itertools.combinations( flat_media, 2 ) )
                
            else:
                
                media_pairs = [ ( first_media, other_media ) for other_media in flat_media if other_media != first_media ]
                
            
        
        if len( media_pairs ) == 0:
            
            return False
            
        
        if not silent:
            
            if len( media_pairs ) > 100 and duplicate_type in ( HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_ALTERNATE ):
                
                if duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
                    
                    message = 'False positive records are complicated, and setting that relationship for many files at once is likely a mistake.'
                    message += os.linesep * 2
                    message += 'Are you sure all of these files are all potential duplicates and that they are all false positive matches with each other? If not, I recommend you step back for now.'
                    
                    yes_label = 'I know what I am doing'
                    no_label = 'step back for now'
                    
                elif duplicate_type == HC.DUPLICATE_ALTERNATE:
                    
                    message = 'Are you certain all these files are alternates with every other member of the selection, and that none are duplicates?'
                    message += os.linesep * 2
                    message += 'If some of them may be duplicates, I recommend you either deselect the possible duplicates and try again, or just leave this group to be processed in the normal duplicate filter.'
                    
                    yes_label = 'they are all alternates'
                    no_label = 'some may be duplicates'
                    
                
                with ClientGUIDialogs.DialogYesNo( self, message, yes_label = yes_label, no_label = no_label ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES:
                        
                        return False
                        
                    
                
            else:
                
                message = 'Are you sure you want to ' + yes_no_text + ' for the selected files?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES:
                        
                        return False
                        
                    
                
            
        
        pair_info = []
        
        for ( first_media, second_media ) in media_pairs:
            
            first_hash = first_media.GetHash()
            second_hash = second_media.GetHash()
            
            if duplicate_action_options is None:
                
                service_keys_to_content_updates = {}
                
            else:
                
                service_keys_to_content_updates = duplicate_action_options.ProcessPairIntoContentUpdates( first_media, second_media, file_deletion_reason = file_deletion_reason )
                
            
            pair_info.append( ( duplicate_type, first_hash, second_hash, service_keys_to_content_updates ) )
            
        
        if len( pair_info ) > 0:
            
            HG.client_controller.WriteSynchronous( 'duplicate_pair_status', pair_info )
            
            return True
            
        
        return False
        
    
    def _SetDuplicatesCustom( self ):
        
        duplicate_types = [ HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ]
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            duplicate_types.append( HC.DUPLICATE_ALTERNATE )
            
        
        choice_tuples = [ ( HC.duplicate_type_string_lookup[ duplicate_type ], duplicate_type ) for duplicate_type in duplicate_types ]
        
        try:
            
            duplicate_type = ClientGUIDialogsQuick.SelectFromList( self, 'select duplicate type', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        new_options = HG.client_controller.new_options
        
        duplicate_action_options = new_options.GetDuplicateActionOptions( duplicate_type )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit duplicate merge options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditDuplicateActionOptionsPanel( dlg, duplicate_type, duplicate_action_options, for_custom_action = True )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                duplicate_action_options = panel.GetValue()
                
                self._SetDuplicates( duplicate_type, duplicate_action_options = duplicate_action_options )
                
            
        
    
    def _SetDuplicatesFocusedBetter( self, duplicate_action_options = None ):
        
        flat_media = self._GetSelectedFlatMedia()
        
        if self._focussed_media is None:
            
            wx.MessageBox( 'No file is focused, so cannot set the focused file as better!' )
            
            return
            
        
        focused_hash = self._focussed_media.GetDisplayMedia().GetHash()
        
        ( better_media, ) = [ media for media in flat_media if media.GetHash() == focused_hash ]
        
        worse_flat_media = [ media for media in flat_media if media.GetHash() != focused_hash ]
        
        media_pairs = [ ( better_media, worse_media ) for worse_media in worse_flat_media ]
        
        self._SetDuplicates( HC.DUPLICATE_BETTER, media_pairs = media_pairs )
        
    
    def _SetDuplicatesFocusedKing( self ):
        
        if self._focussed_media is None:
            
            wx.MessageBox( 'No file is focused, so cannot set the focused file as king!' )
            
            return
            
        
        focused_hash = self._focussed_media.GetDisplayMedia().GetHash()
        
        HG.client_controller.WriteSynchronous( 'duplicate_set_king', focused_hash )
        
    
    def _SetFocussedMedia( self, media ):
        
        if media is None and self._focussed_media is not None:
            
            next_best_media = self._focussed_media
            
            i = self._sorted_media.index( next_best_media )
            
            while next_best_media in self._selected_media:
                
                if i == 0:
                    
                    next_best_media = None
                    
                    break
                    
                
                i -= 1
                
                next_best_media = self._sorted_media[ i ]
                
            
            self._next_best_media_after_focussed_media_removed = next_best_media
            
        else:
            
            self._next_best_media_after_focussed_media_removed = None
            
        
        self._focussed_media = media
        
        if self._focussed_media is None:
            
            publish_media = None
            
        else:
            
            publish_media = self._focussed_media.GetDisplayMedia()
            
        
        HG.client_controller.pub( 'preview_changed', self._page_key, publish_media )
        
    
    def _ShareOnLocalBooru( self ):
        
        if len( self._selected_media ) > 0:
            
            share_key = HydrusData.GenerateKey()
            
            name = ''
            text = ''
            timeout = HydrusData.GetNow() + 60 * 60 * 24
            hashes = self._GetSelectedHashes()
            
            with ClientGUIDialogs.DialogInputLocalBooruShare( self, share_key, name, text, timeout, hashes, new_share = True ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( share_key, name, text, timeout, hashes ) = dlg.GetInfo()
                    
                    info = {}
                    
                    info[ 'name' ] = name
                    info[ 'text' ] = text
                    info[ 'timeout' ] = timeout
                    info[ 'hashes' ] = hashes
                    
                    HG.client_controller.Write( 'local_booru_share', share_key, info )
                    
                
            
            self.SetFocus()
            
        
    
    def _ShowDuplicatesInNewPage( self, hash, duplicate_type ):
        
        hashes = HG.client_controller.Read( 'file_duplicate_hashes', self._file_service_key, hash, duplicate_type )
        
        if hashes is not None and len( hashes ) > 0:
            
            HG.client_controller.pub( 'new_page_query', self._file_service_key, initial_hashes = hashes )
            
        
    
    def _ShowSelectionInNewPage( self ):
        
        hashes = self._GetSelectedHashes( ordered = True )
        
        if hashes is not None and len( hashes ) > 0:
            
            HG.client_controller.pub( 'new_page_query', self._file_service_key, initial_hashes = hashes )
            
        
    
    def _Undelete( self ):
        
        hashes = self._GetSelectedHashes( has_location = CC.TRASH_SERVICE_KEY )
        
        num_to_undelete = len( hashes )
        
        if num_to_undelete > 0:
            
            do_it = False
            
            if not HC.options[ 'confirm_trash' ]:
                
                do_it = True
                
            else:
                
                if num_to_undelete == 1: text = 'Are you sure you want to undelete this file?'
                else: text = 'Are you sure you want to undelete these ' + HydrusData.ToHumanInt( num_to_undelete ) + ' files?'
                
                with ClientGUIDialogs.DialogYesNo( self, text ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        do_it = True
                        
                    
                
            
            if do_it:
                
                HG.client_controller.Write( 'content_updates', { CC.TRASH_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, hashes ) ] } )
                
            
        
    
    def _UpdateBackgroundColour( self ):
        
        self.Refresh()
        
    
    def _UploadDirectory( self, file_service_key ):
        
        hashes = self._GetSelectedHashes()
        
        if hashes is not None and len( hashes ) > 0:
            
            ipfs_service = HG.client_controller.services_manager.GetService( file_service_key )
            
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter a note to describe this directory.' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                note = dlg.GetValue()
                
                HG.client_controller.CallToThread( ipfs_service.PinDirectory, hashes, note )
                
            
        
    
    def _UploadFiles( self, file_service_key ):
        
        hashes = self._GetSelectedHashes( not_uploaded_to = file_service_key )
        
        if hashes is not None and len( hashes ) > 0:   
            
            HG.client_controller.Write( 'content_updates', { file_service_key : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, hashes ) ] } )
            
        
    
    def AddMediaResults( self, page_key, media_results, append = True ):
        
        if page_key == self._page_key:
            
            HG.client_controller.pub( 'refresh_page_name', self._page_key )
            
            return ClientMedia.ListeningMediaList.AddMediaResults( self, media_results, append = append )
            
        
    
    def ClearPageKey( self ):
        
        self._page_key = 'dead media panel page key'
        
    
    def Collect( self, page_key, collect_by = None ):
        
        if page_key == self._page_key:
            
            self._Select( 'none' )
            
            ClientMedia.ListeningMediaList.Collect( self, collect_by )
            
            self._RecalculateVirtualSize()
            
            # no refresh needed since the sort call that always comes after will do it
            
        
    
    def FileDumped( self, page_key, hash, status ):
        
        if page_key == self._page_key:
            
            media = self._GetMedia( { hash } )
            
            for m in media: m.Dumped( status )
            
            self._RedrawMedia( media )
            
        
    
    def PageHidden( self ):
        
        HG.client_controller.pub( 'preview_changed', self._page_key, None )
        
    
    def PageShown( self ):
        
        if self._focussed_media is None:
            
            publish_media = None
            
        else:
            
            publish_media = self._focussed_media.GetDisplayMedia()
            
        
        HG.client_controller.pub( 'preview_changed', self._page_key, publish_media )
        
        self._PublishSelectionChange()
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'copy_bmp':
                
                self._CopyBMPToClipboard()
                
            elif action == 'copy_file':
                
                self._CopyFilesToClipboard()
                
            elif action == 'copy_path':
                
                self._CopyPathsToClipboard()
                
            elif action == 'copy_sha256_hash':
                
                self._CopyHashesToClipboard( 'sha256' )
                
            elif action == 'duplicate_media_clear_focused_false_positives':
                
                if self._focussed_media is not None:
                    
                    hash = self._focussed_media.GetDisplayMedia().GetHash()
                    
                    ClientGUIDuplicates.ClearFalsePositives( self, ( hash, ) )
                    
                
            elif action == 'duplicate_media_dissolve_focus_alternate_group':
                
                if self._focussed_media is not None:
                    
                    hash = self._focussed_media.GetDisplayMedia().GetHash()
                    
                    ClientGUIDuplicates.DissolveAlternateGroup( self, ( hash, ) )
                    
                
            elif action == 'duplicate_media_dissolve_focus_duplicate_group':
                
                if self._focussed_media is not None:
                    
                    hash = self._focussed_media.GetDisplayMedia().GetHash()
                    
                    ClientGUIDuplicates.DissolveDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == 'duplicate_media_remove_focus_from_alternate_group':
                
                if self._focussed_media is not None:
                    
                    hash = self._focussed_media.GetDisplayMedia().GetHash()
                    
                    ClientGUIDuplicates.RemoveFromAlternateGroup( self, ( hash, ) )
                    
                
            elif action == 'duplicate_media_remove_focus_from_duplicate_group':
                
                if self._focussed_media is not None:
                    
                    hash = self._focussed_media.GetDisplayMedia().GetHash()
                    
                    ClientGUIDuplicates.RemoveFromDuplicateGroup( self, ( hash, ) )
                    
                
            elif action == 'duplicate_media_reset_focused_potential_search':
                
                if self._focussed_media is not None:
                    
                    hash = self._focussed_media.GetDisplayMedia().GetHash()
                    
                    ClientGUIDuplicates.ResetPotentialSearch( self, ( hash, ) )
                    
                
            elif action == 'duplicate_media_set_alternate':
                
                self._SetDuplicates( HC.DUPLICATE_ALTERNATE )
                
            elif action == 'duplicate_media_set_alternate_collections':
                
                self._SetCollectionsAsAlternate()
                
            elif action == 'duplicate_media_set_custom':
                
                self._SetDuplicatesCustom()
                
            elif action == 'duplicate_media_set_focused_better':
                
                self._SetDuplicatesFocusedBetter()
                
            elif action == 'duplicate_media_set_focused_king':
                
                self._SetDuplicatesFocusedKing()
                
            elif action == 'duplicate_media_set_same_quality':
                
                self._SetDuplicates( HC.DUPLICATE_SAME_QUALITY )
                
            elif action == 'export_files':
                
                self._ExportFiles()
                
            elif action == 'export_files_quick_auto_export':
                
                self._ExportFiles( do_export_and_then_quit = True )
                
            elif action == 'manage_file_ratings':
                
                self._ManageRatings()
                
            elif action == 'manage_file_tags':
                
                self._ManageTags()
                
            elif action == 'manage_file_urls':
                
                self._ManageURLs()
                
            elif action == 'manage_file_notes':
                
                self._ManageNotes()
                
            elif action == 'open_known_url':
                
                self._OpenKnownURL()
                
            elif action == 'archive_file':
                
                self._Archive()
                
            elif action == 'delete_file':
                
                self._Delete()
                
            elif action == 'inbox_file':
                
                self._Inbox()
                
            elif action == 'remove_file_from_view':
                
                self._Remove()
                
            elif action == 'get_similar_to_exact':
                
                self._GetSimilarTo( HC.HAMMING_EXACT_MATCH )
                
            elif action == 'get_similar_to_very_similar':
                
                self._GetSimilarTo( HC.HAMMING_VERY_SIMILAR )
                
            elif action == 'get_similar_to_similar':
                
                self._GetSimilarTo( HC.HAMMING_SIMILAR )
                
            elif action == 'get_similar_to_speculative':
                
                self._GetSimilarTo( HC.HAMMING_SPECULATIVE )
                
            elif action == 'open_file_in_external_program':
                
                self._OpenExternally()
                
            elif action == 'open_selection_in_new_page':
                
                self._ShowSelectionInNewPage()
                
            elif action == 'launch_the_archive_delete_filter':
                
                self._ArchiveDeleteFilter()
                
            else:
                
                command_processed = False
                
            
        elif command_type == CC.APPLICATION_COMMAND_TYPE_CONTENT:
            
            command_processed = ClientGUIFunctions.ApplyContentApplicationCommandToMedia( self, command, self._GetSelectedFlatMedia() )
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def ProcessContentUpdates( self, service_keys_to_content_updates ):
        
        ClientMedia.ListeningMediaList.ProcessContentUpdates( self, service_keys_to_content_updates )
        
        we_were_file_or_tag_affected = False
        
        for ( service_key, content_updates ) in list(service_keys_to_content_updates.items()):
            
            for content_update in content_updates:
                
                hashes = content_update.GetHashes()
                
                if self._HasHashes( hashes ):
                    
                    affected_media = self._GetMedia( hashes )
                    
                    self._RedrawMedia( affected_media )
                    
                    if content_update.GetDataType() in ( HC.CONTENT_TYPE_FILES, HC.CONTENT_TYPE_MAPPINGS ):
                        
                        we_were_file_or_tag_affected = True
                        
                    
                
            
        
        if we_were_file_or_tag_affected:
            
            self._PublishSelectionChange( force_reload = True )
            
        
    
    def ProcessServiceUpdates( self, service_keys_to_service_updates ):
        
        ClientMedia.ListeningMediaList.ProcessServiceUpdates( self, service_keys_to_service_updates )
        
        for ( service_key, service_updates ) in list(service_keys_to_service_updates.items()):
            
            for service_update in service_updates:
                
                ( action, row ) = service_update.ToTuple()
                
                if action in ( HC.SERVICE_UPDATE_DELETE_PENDING, HC.SERVICE_UPDATE_RESET ):
                    
                    self._RecalculateVirtualSize()
                    
                
                self._PublishSelectionChange( force_reload = True )
                
            
        
    
    def RemoveMedia( self, page_key, hashes ):
        
        if page_key == self._page_key:
            
            self._RemoveMediaByHashes( hashes )
            
        
    
    def SelectByTags( self, page_key, and_or_or, tags ):
        
        if page_key == self._page_key:
            
            self._Select( 'tags', ( and_or_or, tags ) )
            
        
    
    def SetDuplicateStatusForAll( self, duplicate_type ):
        
        media_group = ClientMedia.FlattenMedia( self._sorted_media )
        
        return self._SetDuplicates( duplicate_type, media_group = media_group )
        
    
    def SetFocussedMedia( self, page_key, media ):
        
        pass
        
    
    def Sort( self, page_key, media_sort = None ):
        
        if page_key == self._page_key:
            
            ClientMedia.ListeningMediaList.Sort( self, media_sort )
            
        
    
class MediaPanelLoading( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_key ):
        
        self._current = None
        self._max = None
        
        MediaPanel.__init__( self, parent, page_key, file_service_key, [] )
        
        HG.client_controller.sub( self, 'SetNumQueryResults', 'set_num_query_results' )
        
    
    def _GetPrettyStatus( self ):
        
        s = 'Loading\u2026'
        
        if self._current is not None:
            
            s += ' ' + HydrusData.ToHumanInt( self._current )
            
            if self._max is not None:
                
                s += ' of ' + HydrusData.ToHumanInt( self._max )
                
            
        
        return s
        
    
    def GetSortedMedia( self ):
        
        return []
        
    
    def SetNumQueryResults( self, page_key, num_current, num_max ):
        
        if page_key == self._page_key:
            
            self._current = num_current
            
            self._max = num_max
            
            self._PublishSelectionChange()
            
        
    
class MediaPanelThumbnails( MediaPanel ):
    
    def __init__( self, parent, page_key, file_service_key, media_results ):
        
        self._clean_canvas_pages = {}
        self._dirty_canvas_pages = []
        self._num_rows_per_canvas_page = 1
        
        MediaPanel.__init__( self, parent, page_key, file_service_key, media_results )
        
        self._last_client_size = ( 20, 20 )
        self._num_columns = 1
        
        self._drag_init_coordinates = None
        self._thumbnails_being_faded_in = {}
        self._hashes_faded = set()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnail_scroll_rate = float( HG.client_controller.new_options.GetString( 'thumbnail_scroll_rate' ) )
        
        self.SetScrollRate( 0, int( round( thumbnail_span_height * thumbnail_scroll_rate ) ) )
        
        self.Bind( wx.EVT_LEFT_DOWN, self.EventLeftDown )
        self.Bind( wx.EVT_MOTION, self.EventDrag )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        self.Bind( wx.EVT_LEFT_DCLICK, self.EventMouseFullScreen )
        self.Bind( wx.EVT_MIDDLE_DOWN, self.EventMouseFullScreen )
        self.Bind( wx.EVT_PAINT, self.EventPaint )
        self.Bind( wx.EVT_SIZE, self.EventResize )
        self.Bind( wx.EVT_ERASE_BACKGROUND, self.EventEraseBackground )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        
        self.RefreshAcceleratorTable()
        
        HG.client_controller.sub( self, 'MaintainPageCache', 'memory_maintenance_pulse' )
        HG.client_controller.sub( self, 'NewFileInfo', 'new_file_info' )
        HG.client_controller.sub( self, 'NewThumbnails', 'new_thumbnails' )
        HG.client_controller.sub( self, 'ThumbnailsResized', 'redraw_all_thumbnails' )
        HG.client_controller.sub( self, 'RefreshAcceleratorTable', 'notify_new_options' )
        HG.client_controller.sub( self, 'WaterfallThumbnails', 'waterfall_thumbnails' )
        
    
    def _CalculateVisiblePageIndices( self ):
        
        y_start = self._GetYStart()
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        earliest_y = y_start * yUnit
        
        ( client_width, client_height ) = self.GetClientSize()
        
        last_y = earliest_y + client_height
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        page_height = self._num_rows_per_canvas_page * thumbnail_span_height
        
        first_visible_page_index = earliest_y // page_height
        
        last_visible_page_index = last_y // page_height
        
        page_indices = list( range( first_visible_page_index, last_visible_page_index + 1 ) )
        
        return page_indices
        
    
    def _CreateNewDirtyPage( self ):
        
        ( client_width, client_height ) = self.GetClientSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        self._dirty_canvas_pages.append( HG.client_controller.bitmap_manager.GetBitmap( client_width, self._num_rows_per_canvas_page * thumbnail_span_height ) )
        
    
    def _DeleteAllDirtyPages( self ):
        
        for bmp in self._dirty_canvas_pages:
            
            HG.client_controller.bitmap_manager.ReleaseBitmap( bmp )
            
        
        self._dirty_canvas_pages = []
        
    
    def _DirtyAllPages( self ):
        
        clean_indices = list(self._clean_canvas_pages.keys())
        
        for clean_index in clean_indices:
            
            self._DirtyPage( clean_index )
            
        
    
    def _DirtyPage( self, clean_index ):

        bmp = self._clean_canvas_pages[ clean_index ]
        
        del self._clean_canvas_pages[ clean_index ]
        
        thumbnails = [ thumbnail for ( thumbnail_index, thumbnail ) in self._GetThumbnailsFromPageIndex( clean_index ) ]
        
        if len( thumbnails ) > 0:
            
            HG.client_controller.GetCache( 'thumbnail' ).CancelWaterfall( self._page_key, thumbnails )
            
        
        self._dirty_canvas_pages.append( bmp )
        
    
    def _DrawCanvasPage( self, page_index, bmp ):
        
        ( bmp_width, bmp_height ) = bmp.GetSize()
        
        dc = wx.MemoryDC( bmp )
        
        new_options = HG.client_controller.new_options
        
        bg_colour = HG.client_controller.new_options.GetColour( CC.COLOUR_THUMBGRID_BACKGROUND )
        
        if HG.thumbnail_debug_mode and page_index % 2 == 0:
            
            bg_colour = ClientData.GetLighterDarkerColour( bg_colour )
            
        
        dc.SetBackground( wx.Brush( bg_colour ) )
        
        dc.Clear()
        
        #
        
        page_thumbnails = self._GetThumbnailsFromPageIndex( page_index )
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnails_to_render_later = []
        
        thumbnail_cache = HG.client_controller.GetCache( 'thumbnail' )
        
        thumbnail_margin = HG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        for ( thumbnail_index, thumbnail ) in page_thumbnails:
            
            hash = thumbnail.GetDisplayMedia().GetHash()
            
            if hash in self._hashes_faded and thumbnail_cache.HasThumbnailCached( thumbnail ):
                
                self._StopFading( hash )
                
                thumbnail_col = thumbnail_index % self._num_columns
                
                thumbnail_row = thumbnail_index // self._num_columns
                
                x = thumbnail_col * thumbnail_span_width + thumbnail_margin
                
                y = ( thumbnail_row - ( page_index * self._num_rows_per_canvas_page ) ) * thumbnail_span_height + thumbnail_margin
                
                dc.DrawBitmap( thumbnail.GetBmp(), x, y )
                
            else:
                
                thumbnails_to_render_later.append( thumbnail )
                
            
        
        HG.client_controller.GetCache( 'thumbnail' ).Waterfall( self._page_key, thumbnails_to_render_later )
        
    
    def _FadeThumbnails( self, thumbnails ):
        
        if len( thumbnails ) == 0:
            
            return
            
        
        self._hashes_faded.update( ( thumbnail.GetDisplayMedia().GetHash() for thumbnail in thumbnails ) )
        
        if not HG.client_controller.gui.IsCurrentPage( self._page_key ):
            
            self._DirtyAllPages()
            
            return
            
        
        now_precise = HydrusData.GetNowPrecise()
        
        for thumbnail in thumbnails:
            
            try:
                
                thumbnail_index = self._sorted_media.index( thumbnail )
                
            except HydrusExceptions.DataMissing:
                
                # probably means a collect happened during an ongoing waterfall or whatever
                
                return
                
            
            if self._GetPageIndexFromThumbnailIndex( thumbnail_index ) not in self._clean_canvas_pages:
                
                continue
                
            
            hash = thumbnail.GetDisplayMedia().GetHash()
            
            self._StopFading( hash )
            
            bmp = thumbnail.GetBmp()
            
            image = bmp.ConvertToImage()
            
            try: image.InitAlpha()
            except: pass
            
            image = image.AdjustChannels( 1, 1, 1, 0.20 )
            
            alpha_bmp = wx.Bitmap( image, 32 )
            
            image.Destroy()
            
            self._thumbnails_being_faded_in[ hash ] = ( bmp, alpha_bmp, thumbnail_index, thumbnail, now_precise, 0 )
            
        
        HG.client_controller.gui.RegisterAnimationUpdateWindow( self )
        
    
    def _GenerateMediaCollection( self, media_results ):
        
        return ThumbnailMediaCollection( self._file_service_key, media_results )
        
    
    def _GenerateMediaSingleton( self, media_result ):
        
        return ThumbnailMediaSingleton( self._file_service_key, media_result )
        
    
    def _GetMediaCoordinates( self, media ):
        
        try: index = self._sorted_media.index( media )
        except: return ( -1, -1 )
        
        row = index // self._num_columns
        column = index % self._num_columns
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnail_margin = HG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        ( x, y ) = ( column * thumbnail_span_width + thumbnail_margin, row * thumbnail_span_height + thumbnail_margin )
        
        return ( x, y )
        
    
    def _GetPageIndexFromThumbnailIndex( self, thumbnail_index ):
        
        thumbnails_per_page = self._num_columns * self._num_rows_per_canvas_page
        
        page_index = thumbnail_index // thumbnails_per_page
        
        return page_index
        
    
    def _GetThumbnailSpanDimensions( self ):
        
        thumbnail_border = HG.client_controller.new_options.GetInteger( 'thumbnail_border' )
        thumbnail_margin = HG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        return ClientData.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], ( thumbnail_border + thumbnail_margin ) * 2 )
        
    
    def _GetThumbnailUnderMouse( self, mouse_event ):
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        ( x_scroll, y_scroll ) = self.GetViewStart()
        
        y_offset = y_scroll * yUnit
        
        x = mouse_event.GetX()
        y = mouse_event.GetY() + y_offset
        
        ( t_span_x, t_span_y ) = self._GetThumbnailSpanDimensions()
        
        x_mod = x % t_span_x
        y_mod = y % t_span_y
        
        thumbnail_margin = HG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        if x_mod <= thumbnail_margin or y_mod <= thumbnail_margin or x_mod > t_span_x - thumbnail_margin or y_mod > t_span_y - thumbnail_margin:
            
            return None
            
        
        column_index = x // t_span_x
        row_index = y // t_span_y
        
        if column_index >= self._num_columns: return None
        
        thumbnail_index = self._num_columns * row_index + column_index
        
        if thumbnail_index >= len( self._sorted_media ): return None
        
        return self._sorted_media[ thumbnail_index ]
        
    
    def _GetThumbnailsFromPageIndex( self, page_index ):
        
        num_thumbnails_per_page = self._num_columns * self._num_rows_per_canvas_page
        
        start_index = num_thumbnails_per_page * page_index
        
        if start_index <= len( self._sorted_media ):
            
            end_index = min( len( self._sorted_media ), start_index + num_thumbnails_per_page )
            
            thumbnails = [ ( index, self._sorted_media[ index ] ) for index in range( start_index, end_index ) ]
            
        else:
            
            thumbnails = []
            
        
        return thumbnails
        
    
    def _GetYStart( self ):
        
        ( my_virtual_width, my_virtual_height ) = self.GetVirtualSize()
        
        ( my_width, my_height ) = self.GetClientSize()
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        max_y = ( my_virtual_height - my_height ) // yUnit
        
        if ( my_virtual_height - my_height ) % yUnit > 0:
            
            max_y += 1
            
        
        ( x_start, y_start ) = self.GetViewStart()
        
        y_start = max( 0, y_start )
        
        y_start = min( y_start, max_y )
        
        return y_start
        
    
    def _MoveFocussedThumbnail( self, rows, columns, shift ):
        
        if self._focussed_media is not None:
            
            media_to_use = self._focussed_media
            
        elif self._next_best_media_after_focussed_media_removed is not None:
            
            media_to_use = self._next_best_media_after_focussed_media_removed
            
            if columns == -1: # treat it as if the focussed area is between this and the next
                
                columns = 0
                
            
        elif len( self._sorted_media ) > 0:
            
            media_to_use = self._sorted_media[ 0 ]
            
        else:
            
            media_to_use = None
            
        
        if media_to_use is not None:
            
            current_position = self._sorted_media.index( media_to_use )
            
            new_position = current_position + columns + ( self._num_columns * rows )
            
            if new_position < 0:
                
                new_position = 0
                
            elif new_position > len( self._sorted_media ) - 1:
                
                new_position = len( self._sorted_media ) - 1
                
            
            new_media = self._sorted_media[ new_position ]
            
            self._HitMedia( new_media, False, shift )
            
            self._ScrollToMedia( new_media )
            
        
        
    
    def _RecalculateVirtualSize( self ):
        
        ( client_width, client_height ) = self.GetClientSize()
        
        if client_width > 0 and client_height > 0:
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
            
            num_media = len( self._sorted_media )
            
            num_rows = max( 1, num_media // self._num_columns )
            
            if num_media % self._num_columns > 0:
                
                num_rows += 1
                
            
            virtual_width = client_width
            
            virtual_height = num_rows * thumbnail_span_height
            
            ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
            
            excess = virtual_height % yUnit
            
            if excess > 0: # we want virtual height to fit exactly into scroll units, even if that puts some padding below bottom row
                
                top_up = yUnit - excess
                
                virtual_height += top_up
                
            
            virtual_height = max( virtual_height, client_height )
            
            if ( virtual_width, virtual_height ) != self.GetVirtualSize():
                
                self.SetVirtualSize( ( virtual_width, virtual_height ) )
                
            
        
    
    def _RedrawMedia( self, thumbnails ):
        
        visible_thumbnails = [ thumbnail for thumbnail in thumbnails if self._ThumbnailIsVisible( thumbnail ) ]
        
        thumbnail_cache = HG.client_controller.GetCache( 'thumbnail' )
        
        thumbnails_to_render_now = []
        thumbnails_to_render_later = []
        
        for thumbnail in visible_thumbnails:
            
            if thumbnail_cache.HasThumbnailCached( thumbnail ):
                
                thumbnails_to_render_now.append( thumbnail )
                
            else:
                
                thumbnails_to_render_later.append( thumbnail )
                
            
        
        if len( thumbnails_to_render_now ) > 0:
            
            self._FadeThumbnails( thumbnails_to_render_now )
            
        
        if len( thumbnails_to_render_later ) > 0:
            
            HG.client_controller.GetCache( 'thumbnail' ).Waterfall( self._page_key, thumbnails_to_render_later )
            
        
    
    def _ReinitialisePageCacheIfNeeded( self ):
        
        old_num_rows = self._num_rows_per_canvas_page
        old_num_columns = self._num_columns
        
        ( old_client_width, old_client_height ) = self._last_client_size
        
        ( client_width, client_height ) = self.GetClientSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        num_rows = ( client_height // thumbnail_span_height ) // 2 # roughly half a client_height's worth of thumbs
        
        self._num_rows_per_canvas_page = max( 1, num_rows )
        
        self._num_columns = max( 1, client_width // thumbnail_span_width )
        
        client_dimensions_changed = old_client_width != client_width or old_client_height != client_height
        thumb_layout_changed = old_num_columns != self._num_columns or old_num_rows != self._num_rows_per_canvas_page
        
        if client_dimensions_changed or thumb_layout_changed:
            
            width_got_bigger = old_client_width < client_width
            
            if thumb_layout_changed or width_got_bigger:
                
                self._DirtyAllPages()
                
                self._DeleteAllDirtyPages()
                
            
            self.Refresh()
            
        
    
    def _RemoveMediaDirectly( self, singleton_media, collected_media ):
        
        if self._focussed_media is not None:
            
            if self._focussed_media in singleton_media or self._focussed_media in collected_media:
                
                self._SetFocussedMedia( None )
                
            
        
        MediaPanel._RemoveMediaDirectly( self, singleton_media, collected_media )
        
        self._selected_media.difference_update( singleton_media )
        self._selected_media.difference_update( collected_media )
        
        self._shift_focussed_media = None
        
        self._RecalculateVirtualSize()
        
        self._DirtyAllPages()
        
        self._PublishSelectionChange()
        
        HG.client_controller.pub( 'refresh_page_name', self._page_key )
        
        self.Refresh()
        
    
    def _ScrollEnd( self, shift = False ):
        
        if len( self._sorted_media ) > 0:
            
            end_media = self._sorted_media[ -1 ]
            
            self._HitMedia( end_media, False, shift )
            
            self._ScrollToMedia( end_media )
            
        
    
    def _ScrollHome( self, shift = False ):
        
        if len( self._sorted_media ) > 0:
            
            home_media = self._sorted_media[ 0 ]
            
            self._HitMedia( home_media, False, shift )
            
            self._ScrollToMedia( home_media )
            
        
    
    def _ScrollToMedia( self, media ):
        
        if media is not None:
            
            ( x, y ) = self._GetMediaCoordinates( media )
            
            ( start_x, start_y ) = self.GetViewStart()
            
            ( x_unit, y_unit ) = self.GetScrollPixelsPerUnit()
            
            ( width, height ) = self.GetClientSize()
            
            ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
            
            new_options = HG.client_controller.new_options
            
            percent_visible = new_options.GetInteger( 'thumbnail_visibility_scroll_percent' ) / 100
            
            if y < start_y * y_unit:
                
                y_to_scroll_to = y / y_unit
                
                self.Scroll( -1, y_to_scroll_to )
                
                wx.QueueEvent( self.GetEventHandler(), wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE, pos = y_to_scroll_to ) )
                
            elif y > ( start_y * y_unit ) + height - ( thumbnail_span_height * percent_visible ):
                
                y_to_scroll_to = ( y - height ) // y_unit
                
                self.Scroll( -1, y_to_scroll_to )
                
                wx.QueueEvent( self.GetEventHandler(), wx.ScrollWinEvent( wx.wxEVT_SCROLLWIN_THUMBRELEASE, pos = y_to_scroll_to + 2 ) )
                
            
        
    
    def _StopFading( self, hash ):
        
        if hash in self._thumbnails_being_faded_in:
            
            ( bmp, alpha_bmp, thumbnail_index, thumbnail, animation_started, num_frames ) = self._thumbnails_being_faded_in[ hash ]
            
            del self._thumbnails_being_faded_in[ hash ]
            
            HG.client_controller.bitmap_manager.ReleaseBitmap( bmp )
            HG.client_controller.bitmap_manager.ReleaseBitmap( alpha_bmp )
            
        
    
    def _ThumbnailIsVisible( self, thumbnail ):
        
        try:
            
            index = self._sorted_media.index( thumbnail )
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
        if self._GetPageIndexFromThumbnailIndex( index ) in self._clean_canvas_pages:
            
            return True
            
        else:
            
            return False
            
        
    
    def _UpdateBackgroundColour( self ):
        
        MediaPanel._UpdateBackgroundColour( self )
    
        self._DirtyAllPages()
        
        self._DeleteAllDirtyPages()
        
        self.Refresh()
        
    
    def AddMediaResults( self, page_key, media_results, append = True ):
        
        if page_key == self._page_key:
            
            thumbnails = MediaPanel.AddMediaResults( self, page_key, media_results, append = append )
            
            self._RecalculateVirtualSize()
            
            HG.client_controller.GetCache( 'thumbnail' ).Waterfall( self._page_key, thumbnails )
            
            if len( self._selected_media ) == 0:
                
                self._PublishSelectionIncrement( thumbnails )
                
            
        
    
    def EventDrag( self, event ):
        
        we_started_dragging_on_this_panel = self._drag_init_coordinates is not None
        
        if we_started_dragging_on_this_panel and event.LeftIsDown() and event.Dragging():
            
            ( old_x, old_y ) = self._drag_init_coordinates
            
            ( x, y ) = wx.GetMousePosition()
            
            ( delta_x, delta_y ) = ( x - old_x, y - old_y )
            
            if abs( delta_x ) > 10 or abs( delta_y ) > 10:
                
                media = self._GetSelectedFlatMedia( discriminant = CC.DISCRIMINANT_LOCAL )
                
                if len( media ) > 0:
                    
                    alt_down = event.AltDown()
                    
                    result = ClientDragDrop.DoFileExportDragDrop( self, self._page_key, media, alt_down )
                    
                    if result not in ( wx.DragError, wx.DragNone ):
                        
                        HG.client_controller.pub( 'media_focus_went_to_external_program', self._page_key )
                        
                    
                
            
        
        event.Skip()
        
    
    def EventEraseBackground( self, event ):
        
        pass
        
    
    def EventKeyDown( self, event ):
        
        # accelerator tables can't handle escape key in windows, gg
        
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            
            self._Select( 'none' )
            
        elif event.GetKeyCode() in ( wx.WXK_PAGEUP, wx.WXK_PAGEDOWN ):
            
            if event.GetKeyCode() == wx.WXK_PAGEUP:
                
                direction = -1
                
            elif event.GetKeyCode() == wx.WXK_PAGEDOWN:
                
                direction = 1
                
            
            shift = event.ShiftDown()
            
            self._MoveFocussedThumbnail( self._num_rows_per_canvas_page * direction, 0, shift )
            
        else: event.Skip()
        
    
    def EventLeftDown( self, event ):
        
        self._drag_init_coordinates = wx.GetMousePosition()
        
        self._HitMedia( self._GetThumbnailUnderMouse( event ), event.CmdDown(), event.ShiftDown() )
        
        # this specifically does not scroll to media, as for clicking (esp. double-clicking attempts), the scroll can be jarring
        
        event.Skip()
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'copy_files': self._CopyFilesToClipboard()
            elif command == 'ctrl-space':
                
                if self._focussed_media is not None:
                    
                    self._HitMedia( self._focussed_media, True, False )
                    
                
            elif command == 'delete_file':
                
                if data is None:
                    
                    self._Delete()
                    
                else:
                    
                    self._Delete( data )
                    
                
            elif command == 'fullscreen': self._FullScreen()
            elif command == 'scroll_end': self._ScrollEnd( False )
            elif command == 'scroll_home': self._ScrollHome( False )
            elif command == 'shift_scroll_end': self._ScrollEnd( True )
            elif command == 'shift_scroll_home': self._ScrollHome( True )
            elif command == 'select': self._Select( data )
            elif command == 'undelete': self._Undelete()
            elif command == 'key_up': self._MoveFocussedThumbnail( -1, 0, False )
            elif command == 'key_down': self._MoveFocussedThumbnail( 1, 0, False )
            elif command == 'key_left': self._MoveFocussedThumbnail( 0, -1, False )
            elif command == 'key_right': self._MoveFocussedThumbnail( 0, 1, False )
            elif command == 'key_shift_up': self._MoveFocussedThumbnail( -1, 0, True )
            elif command == 'key_shift_down': self._MoveFocussedThumbnail( 1, 0, True )
            elif command == 'key_shift_left': self._MoveFocussedThumbnail( 0, -1, True )
            elif command == 'key_shift_right': self._MoveFocussedThumbnail( 0, 1, True )
            else: event.Skip()
            
        
    
    def EventMouseFullScreen( self, event ):
        
        t = self._GetThumbnailUnderMouse( event )
        
        if t is not None:
            
            locations_manager = t.GetLocationsManager()
            
            if locations_manager.IsLocal():
                
                self._FullScreen( t )
                
            elif len( locations_manager.GetCurrentRemote() ) > 0:
                
                self._DownloadHashes( t.GetHashes() )
                
            
        
        event.Skip()
        
    
    def EventPaint( self, event ):
        
        dc = wx.PaintDC( self )
        
        ( client_x, client_y ) = self.GetClientSize()
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        page_height = self._num_rows_per_canvas_page * thumbnail_span_height
        
        page_indices_to_display = self._CalculateVisiblePageIndices()
        
        earliest_page_index_to_display = min( page_indices_to_display )
        last_page_index_to_display = max( page_indices_to_display )
        
        page_indices_to_draw = list( page_indices_to_display )
        
        if earliest_page_index_to_display > 0:
            
            page_indices_to_draw.append( earliest_page_index_to_display - 1 )
            
        
        page_indices_to_draw.append( last_page_index_to_display + 1 )
        
        page_indices_to_draw.sort()
        
        potential_clean_indices_to_steal = [ page_index for page_index in list(self._clean_canvas_pages.keys()) if page_index not in page_indices_to_draw ]
        
        random.shuffle( potential_clean_indices_to_steal )
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        y_start = self._GetYStart()
        
        earliest_y = y_start * yUnit
        
        '''
        
        # an old effort to get a neat image drawn behind the thumbs. real hassle working with transparency and bmps across multiple platforms at the time
        
        bg_colour = HG.client_controller.new_options.GetColour( CC.COLOUR_THUMBGRID_BACKGROUND )
        
        dc.SetBackground( wx.Brush( bg_colour ) )
        
        dc.Clear()
        
        background_bmp = HG.client_controller.bitmap_manager.GetMediaBackgroundBitmap()
        
        if background_bmp is not None:
            
            ( background_bmp_width, background_bmp_height ) = background_bmp.GetSize()
            
            dc.DrawBitmap( background_bmp, client_x - background_bmp_width, client_y - background_bmp_height )
            
        '''
        
        for page_index in page_indices_to_draw:
            
            if page_index not in self._clean_canvas_pages:
                
                if len( self._dirty_canvas_pages ) == 0:
                    
                    if len( potential_clean_indices_to_steal ) > 0:
                        
                        index_to_steal = potential_clean_indices_to_steal.pop()
                        
                        self._DirtyPage( index_to_steal )
                        
                    else:
                        
                        self._CreateNewDirtyPage()
                        
                    
                
                bmp = self._dirty_canvas_pages.pop()
                
                self._DrawCanvasPage( page_index, bmp )
                
                self._clean_canvas_pages[ page_index ] = bmp
                
            
            if page_index in page_indices_to_display:
                
                bmp = self._clean_canvas_pages[ page_index ]
                
                page_virtual_y = page_height * page_index
                
                page_client_y = page_virtual_y - earliest_y
                
                dc.DrawBitmap( bmp, 0, page_client_y )
                
            
        
    
    def EventResize( self, event ):
        
        self._ReinitialisePageCacheIfNeeded()
        
        self._RecalculateVirtualSize()
        
        self._last_client_size = self.GetClientSize()
        
    
    def EventShowMenu( self, event ):
        
        new_options = HG.client_controller.new_options
        
        advanced_mode = new_options.GetBoolean( 'advanced_mode' )
        
        services_manager = HG.client_controller.services_manager
        
        thumbnail = self._GetThumbnailUnderMouse( event )
        
        if thumbnail is not None:
            
            self._HitMedia( thumbnail, event.CmdDown(), event.ShiftDown() )
            
        
        all_locations_managers = [ media.GetLocationsManager() for media in self._sorted_media ]
        selected_locations_managers = [ media.GetLocationsManager() for media in self._selected_media ]
        
        selection_has_local = True in ( locations_manager.IsLocal() for locations_manager in selected_locations_managers )
        selection_has_local_file_domain = True in ( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() for locations_manager in selected_locations_managers )
        selection_has_trash = True in ( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() for locations_manager in selected_locations_managers )
        selection_has_inbox = True in ( media.HasInbox() for media in self._selected_media )
        selection_has_archive = True in ( media.HasArchive() for media in self._selected_media )
        
        all_file_domains = HydrusData.MassUnion( locations_manager.GetCurrent() for locations_manager in all_locations_managers )
        all_specific_file_domains = all_file_domains.difference( { CC.COMBINED_FILE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY } )
        all_local_file_domains = services_manager.Filter( all_specific_file_domains, ( HC.LOCAL_FILE_DOMAIN, ) )
        all_file_repos = services_manager.Filter( all_specific_file_domains, ( HC.FILE_REPOSITORY, ) )
        
        has_local = True in ( locations_manager.IsLocal() for locations_manager in all_locations_managers )
        has_remote = True in ( locations_manager.IsRemote() for locations_manager in all_locations_managers )
        
        num_inbox = sum( ( media.GetNumFiles() for media in self._sorted_media if media.HasInbox() ) )
        num_archive = sum( ( media.GetNumFiles() for media in self._sorted_media if media.HasArchive() ) )
        
        media_has_inbox = num_inbox > 0
        media_has_archive = num_archive > 0
        
        menu = wx.Menu()
        
        if self._focussed_media is not None:
            
            # variables
            
            num_selected = self._GetNumSelected()
            
            multiple_selected = num_selected > 1
            
            collections_selected = True in ( media.IsCollection() for media in self._selected_media )
            
            services_manager = HG.client_controller.services_manager
            
            services = services_manager.GetServices()
            
            service_keys_to_names = { service.GetServiceKey() : service.GetName() for service in services }
            
            tag_repositories = [ service for service in services if service.GetServiceType() == HC.TAG_REPOSITORY ]
            
            file_repositories = [ service for service in services if service.GetServiceType() == HC.FILE_REPOSITORY ]
            
            ipfs_services = [ service for service in services if service.GetServiceType() == HC.IPFS ]
            
            local_ratings_services = [ service for service in services if service.GetServiceType() in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
            
            local_booru_service = [ service for service in services if service.GetServiceType() == HC.LOCAL_BOORU ][0]
            
            local_booru_is_running = local_booru_service.GetPort() is not None
            
            i_can_post_ratings = len( local_ratings_services ) > 0
            
            focussed_is_local = CC.COMBINED_LOCAL_FILE_SERVICE_KEY in self._focussed_media.GetLocationsManager().GetCurrent()
            
            file_service_keys = { repository.GetServiceKey() for repository in file_repositories }
            upload_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_CREATE ) }
            petition_resolve_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_OVERRULE ) }
            petition_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_PETITION ) } - petition_resolve_permission_file_service_keys
            user_manage_permission_file_service_keys = { repository.GetServiceKey() for repository in file_repositories if repository.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE ) }
            ipfs_service_keys = { service.GetServiceKey() for service in ipfs_services }
            
            focussed_is_ipfs = True in ( service_key in ipfs_service_keys for service_key in self._focussed_media.GetLocationsManager().GetCurrentRemote() )
            
            if multiple_selected:
                
                download_phrase = 'download all possible selected'
                rescind_download_phrase = 'cancel downloads for all possible selected'
                upload_phrase = 'upload all possible selected to'
                rescind_upload_phrase = 'rescind pending selected uploads to'
                petition_phrase = 'petition all possible selected for removal from'
                rescind_petition_phrase = 'rescind selected petitions for'
                remote_delete_phrase = 'delete all possible selected from'
                modify_account_phrase = 'modify the accounts that uploaded selected to'
                
                pin_phrase = 'pin all to'
                rescind_pin_phrase = 'rescind pin to'
                unpin_phrase = 'unpin all from'
                rescind_unpin_phrase = 'rescind unpin from'
                
                manage_tags_phrase = 'selected files\' tags'
                manage_urls_phrase = 'selected files\' urls'
                manage_ratings_phrase = 'selected files\' ratings'
                
                archive_phrase = 'archive selected'
                inbox_phrase = 'return selected to inbox'
                remove_phrase = 'remove selected from view'
                local_delete_phrase = 'delete selected'
                trash_delete_phrase = 'delete selected from trash now'
                undelete_phrase = 'undelete selected'
                dump_phrase = 'dump selected to 4chan'
                export_phrase = 'files'
                copy_phrase = 'files'
                
            else:
                
                download_phrase = 'download'
                rescind_download_phrase = 'cancel download'
                upload_phrase = 'upload to'
                rescind_upload_phrase = 'rescind pending upload to'
                petition_phrase = 'petition for removal from'
                rescind_petition_phrase = 'rescind petition for'
                remote_delete_phrase = 'delete from'
                modify_account_phrase = 'modify the account that uploaded this to'
                
                pin_phrase = 'pin to'
                rescind_pin_phrase = 'rescind pin to'
                unpin_phrase = 'unpin from'
                rescind_unpin_phrase = 'rescind unpin from'
                
                manage_tags_phrase = 'file\'s tags'
                manage_urls_phrase = 'file\'s urls'
                manage_ratings_phrase = 'file\'s ratings'
                
                archive_phrase = 'archive'
                inbox_phrase = 'return to inbox'
                remove_phrase = 'remove from view'
                local_delete_phrase = 'delete'
                trash_delete_phrase = 'delete from trash now'
                undelete_phrase = 'undelete'
                dump_phrase = 'dump to 4chan'
                export_phrase = 'file'
                copy_phrase = 'file'
                
            
            # info about the files
            
            groups_of_current_remote_service_keys = [ locations_manager.GetCurrentRemote() for locations_manager in selected_locations_managers ]
            groups_of_pending_remote_service_keys = [ locations_manager.GetPendingRemote() for locations_manager in selected_locations_managers ]
            groups_of_petitioned_remote_service_keys = [ locations_manager.GetPetitionedRemote() for locations_manager in selected_locations_managers ]
            groups_of_deleted_remote_service_keys = [ locations_manager.GetDeletedRemote() for locations_manager in selected_locations_managers ]
            
            current_remote_service_keys = HydrusData.MassUnion( groups_of_current_remote_service_keys )
            pending_remote_service_keys = HydrusData.MassUnion( groups_of_pending_remote_service_keys )
            petitioned_remote_service_keys = HydrusData.MassUnion( groups_of_petitioned_remote_service_keys )
            deleted_remote_service_keys = HydrusData.MassUnion( groups_of_deleted_remote_service_keys )
            
            common_current_remote_service_keys = HydrusData.IntelligentMassIntersect( groups_of_current_remote_service_keys )
            common_pending_remote_service_keys = HydrusData.IntelligentMassIntersect( groups_of_pending_remote_service_keys )
            common_petitioned_remote_service_keys = HydrusData.IntelligentMassIntersect( groups_of_petitioned_remote_service_keys )
            common_deleted_remote_service_keys = HydrusData.IntelligentMassIntersect( groups_of_deleted_remote_service_keys )
            
            disparate_current_remote_service_keys = current_remote_service_keys - common_current_remote_service_keys
            disparate_pending_remote_service_keys = pending_remote_service_keys - common_pending_remote_service_keys
            disparate_petitioned_remote_service_keys = petitioned_remote_service_keys - common_petitioned_remote_service_keys
            disparate_deleted_remote_service_keys = deleted_remote_service_keys - common_deleted_remote_service_keys
            
            some_downloading = True in ( locations_manager.IsDownloading() for locations_manager in selected_locations_managers )
            
            pending_file_service_keys = pending_remote_service_keys.intersection( file_service_keys )
            petitioned_file_service_keys = petitioned_remote_service_keys.intersection( file_service_keys )
            
            common_current_file_service_keys = common_current_remote_service_keys.intersection( file_service_keys )
            common_pending_file_service_keys = common_pending_remote_service_keys.intersection( file_service_keys )
            common_petitioned_file_service_keys = common_petitioned_remote_service_keys.intersection( file_service_keys )
            common_deleted_file_service_keys = common_deleted_remote_service_keys.intersection( file_service_keys )
            
            disparate_current_file_service_keys = disparate_current_remote_service_keys.intersection( file_service_keys )
            disparate_pending_file_service_keys = disparate_pending_remote_service_keys.intersection( file_service_keys )
            disparate_petitioned_file_service_keys = disparate_petitioned_remote_service_keys.intersection( file_service_keys )
            disparate_deleted_file_service_keys = disparate_deleted_remote_service_keys.intersection( file_service_keys )
            
            pending_ipfs_service_keys = pending_remote_service_keys.intersection( ipfs_service_keys )
            petitioned_ipfs_service_keys = petitioned_remote_service_keys.intersection( ipfs_service_keys )
            
            common_current_ipfs_service_keys = common_current_remote_service_keys.intersection( ipfs_service_keys )
            common_pending_ipfs_service_keys = common_pending_file_service_keys.intersection( ipfs_service_keys )
            common_petitioned_ipfs_service_keys = common_petitioned_remote_service_keys.intersection( ipfs_service_keys )
            
            disparate_current_ipfs_service_keys = disparate_current_remote_service_keys.intersection( ipfs_service_keys )
            disparate_pending_ipfs_service_keys = disparate_pending_remote_service_keys.intersection( ipfs_service_keys )
            disparate_petitioned_ipfs_service_keys = disparate_petitioned_remote_service_keys.intersection( ipfs_service_keys )
            
            # valid commands for the files
            
            uploadable_file_service_keys = set()
            
            downloadable_file_service_keys = set()
            
            petitionable_file_service_keys = set()
            
            deletable_file_service_keys = set()
            
            modifyable_file_service_keys = set()
            
            pinnable_ipfs_service_keys = set()
            
            unpinnable_ipfs_service_keys = set()
            
            for locations_manager in selected_locations_managers:
                
                # FILE REPOS
                
                # we can upload (set pending) to a repo_id when we have permission, a file is local, not current, not pending, and either ( not deleted or we_can_overrule )
                
                if locations_manager.IsLocal():
                    
                    uploadable_file_service_keys.update( upload_permission_file_service_keys - locations_manager.GetCurrentRemote() - locations_manager.GetPendingRemote() - ( locations_manager.GetDeletedRemote() - petition_resolve_permission_file_service_keys ) )
                    
                
                # we can download (set pending to local) when we have permission, a file is not local and not already downloading and current
                
                if not locations_manager.IsLocal() and not locations_manager.IsDownloading():
                    
                    downloadable_file_service_keys.update( ipfs_service_keys.union( file_service_keys ) & locations_manager.GetCurrentRemote() )
                    
                
                # we can petition when we have permission and a file is current and it is not already petitioned
                
                petitionable_file_service_keys.update( ( petition_permission_file_service_keys & locations_manager.GetCurrentRemote() ) - locations_manager.GetPetitionedRemote() )
                
                # we can delete remote when we have permission and a file is current and it is not already petitioned
                
                deletable_file_service_keys.update( ( petition_resolve_permission_file_service_keys & locations_manager.GetCurrentRemote() ) - locations_manager.GetPetitionedRemote() )
                
                # we can modify users when we have permission and the file is current or deleted
                
                modifyable_file_service_keys.update( user_manage_permission_file_service_keys & ( locations_manager.GetCurrentRemote() | locations_manager.GetDeletedRemote() ) )
                
                # IPFS
                
                # we can pin if a file is local, not current, not pending
                
                if locations_manager.IsLocal():
                    
                    pinnable_ipfs_service_keys.update( ipfs_service_keys - locations_manager.GetCurrentRemote() - locations_manager.GetPendingRemote() )
                    
                
                # we can unpin a file if it is current and not petitioned
                
                unpinnable_ipfs_service_keys.update( ( ipfs_service_keys & locations_manager.GetCurrentRemote() ) - locations_manager.GetPetitionedRemote() )
                
            
            # do the actual menu
            
            if multiple_selected:
                
                ClientGUIMenus.AppendMenuLabel( menu, HydrusData.ToHumanInt( num_selected ) + ' files, ' + self._GetPrettyTotalSize( only_selected = True ) )
                
            else:
                
                for line in self._focussed_media.GetPrettyInfoLines():
                    
                    ClientGUIMenus.AppendMenuLabel( menu, line, line )
                    
                
            
            if len( self._selected_media ) == 1:
                
                AddFileViewingStatsMenu( menu, self._focussed_media )
                
            
            if len( disparate_current_file_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, disparate_current_file_service_keys, 'some uploaded to' )
                
            
            if multiple_selected and len( common_current_file_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, common_current_file_service_keys, 'selected uploaded to' )
                
            
            if len( disparate_pending_file_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, disparate_pending_file_service_keys, 'some pending to' )
                
            
            if len( common_pending_file_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, common_pending_file_service_keys, 'pending to' )
                
            
            if len( disparate_petitioned_file_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, disparate_petitioned_file_service_keys, 'some petitioned from' )
                
            
            if len( common_petitioned_file_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, common_petitioned_file_service_keys, 'petitioned from' )
                
            
            if len( disparate_deleted_file_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, disparate_deleted_file_service_keys, 'some deleted from' )
                
            
            if len( common_deleted_file_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, common_deleted_file_service_keys, 'deleted from' )
                
            
            if len( disparate_current_ipfs_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, disparate_current_ipfs_service_keys, 'some pinned to' )
                
            
            if multiple_selected and len( common_current_ipfs_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, common_current_ipfs_service_keys, 'selected pinned to' )
                
            
            if len( disparate_pending_ipfs_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, disparate_pending_ipfs_service_keys, 'some to be pinned to' )
                
            
            if len( common_pending_ipfs_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, common_pending_ipfs_service_keys, 'to be pinned to' )
                
            
            if len( disparate_petitioned_ipfs_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, disparate_petitioned_ipfs_service_keys, 'some to be unpinned from' )
                
            
            if len( common_petitioned_ipfs_service_keys ) > 0:
                
                AddServiceKeyLabelsToMenu( menu, common_petitioned_ipfs_service_keys, unpin_phrase )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            #
            
            len_interesting_remote_service_keys = 0
            
            len_interesting_remote_service_keys += len( downloadable_file_service_keys )
            len_interesting_remote_service_keys += len( uploadable_file_service_keys )
            len_interesting_remote_service_keys += len( pending_file_service_keys )
            len_interesting_remote_service_keys += len( petitionable_file_service_keys )
            len_interesting_remote_service_keys += len( petitioned_file_service_keys )
            len_interesting_remote_service_keys += len( deletable_file_service_keys )
            len_interesting_remote_service_keys += len( modifyable_file_service_keys )
            len_interesting_remote_service_keys += len( pinnable_ipfs_service_keys )
            len_interesting_remote_service_keys += len( pending_ipfs_service_keys )
            len_interesting_remote_service_keys += len( unpinnable_ipfs_service_keys )
            len_interesting_remote_service_keys += len( petitioned_ipfs_service_keys )
            
            if multiple_selected:
                
                len_interesting_remote_service_keys += len( ipfs_service_keys )
                
            
            if len_interesting_remote_service_keys > 0:
                
                remote_action_menu = wx.Menu()
                
                if len( downloadable_file_service_keys ) > 0:
                    
                    ClientGUIMenus.AppendMenuItem( self, remote_action_menu, download_phrase, 'Download all possible selected files.', self._DownloadSelected )
                    
                
                if some_downloading:
                    
                    ClientGUIMenus.AppendMenuItem( self, remote_action_menu, rescind_download_phrase, 'Stop downloading any of the selected files.', self._RescindDownloadSelected )
                    
                
                if len( uploadable_file_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, uploadable_file_service_keys, upload_phrase, 'Upload all selected files to the file repository.', self._UploadFiles )
                    
                
                if len( pending_file_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, pending_file_service_keys, rescind_upload_phrase, 'Rescind the pending upload to the file repository.', self._RescindUploadFiles )
                    
                
                if len( petitionable_file_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, petitionable_file_service_keys, petition_phrase, 'Petition these files for deletion from the file repository.', self._PetitionFiles )
                    
                
                if len( petitioned_file_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, petitioned_file_service_keys, rescind_petition_phrase, 'Rescind the petition to delete these files from the file repository.', self._RescindPetitionFiles )
                    
                
                if len( deletable_file_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, deletable_file_service_keys, remote_delete_phrase, 'Delete these files from the file repository.', self._Delete )
                    
                
                if len( modifyable_file_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, modifyable_file_service_keys, modify_account_phrase, 'Modify the account(s) that uploaded these files to the file repository.', self._ModifyUploaders )
                    
                
                if len( pinnable_ipfs_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, pinnable_ipfs_service_keys, pin_phrase, 'Pin these files to the ipfs service.', self._UploadFiles )
                    
                
                if len( pending_ipfs_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, pending_ipfs_service_keys, rescind_pin_phrase, 'Rescind the pending pin to the ipfs service.', self._RescindUploadFiles )
                    
                
                if len( unpinnable_ipfs_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, unpinnable_ipfs_service_keys, unpin_phrase, 'Unpin these files from the ipfs service.', self._PetitionFiles )
                    
                
                if len( petitioned_ipfs_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, petitioned_ipfs_service_keys, rescind_unpin_phrase, 'Rescind the pending unpin from the ipfs service.', self._RescindPetitionFiles )
                    
                
                if multiple_selected and len( ipfs_service_keys ) > 0:
                    
                    AddServiceKeysToMenu( self, remote_action_menu, ipfs_service_keys, 'pin new directory to', 'Pin these files as a directory to the ipfs service.', self._UploadDirectory )
                    
                
                ClientGUIMenus.AppendMenu( menu, remote_action_menu, 'remote services' )
                
            
            #
            
            manage_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, manage_menu, manage_tags_phrase, 'Manage tags for the selected files.', self._ManageTags )
            
            if i_can_post_ratings:
                
                ClientGUIMenus.AppendMenuItem( self, manage_menu, manage_ratings_phrase, 'Manage ratings for the selected files.', self._ManageRatings )
                
            
            ClientGUIMenus.AppendMenuItem( self, manage_menu, manage_urls_phrase, 'Manage urls for the selected files.', self._ManageURLs )
            ClientGUIMenus.AppendMenuItem( self, manage_menu, 'file\'s notes', 'Manage notes for the focused file.', self._ManageNotes )
            
            ClientGUIMenus.AppendMenu( menu, manage_menu, 'manage' )
            
            #
            
            if selection_has_local:
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'archive/delete filter', 'Launch a special media viewer that will quickly archive (left-click) and delete (right-click) the selected media.', self._ArchiveDeleteFilter )
                
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if selection_has_inbox:
                
                ClientGUIMenus.AppendMenuItem( self, menu, archive_phrase, 'Archive the selected files.', self._Archive )
                
            
            if selection_has_archive:
                
                ClientGUIMenus.AppendMenuItem( self, menu, inbox_phrase, 'Put the selected files back in the inbox.', self._Inbox )
                
            
            ClientGUIMenus.AppendMenuItem( self, menu, remove_phrase, 'Remove the selected files from the current view.', self._Remove )
            
            if selection_has_local_file_domain:
                
                ClientGUIMenus.AppendMenuItem( self, menu, local_delete_phrase, 'Delete the selected files from \'my files\'.', self._Delete )
                
            
            if selection_has_trash:
                
                ClientGUIMenus.AppendMenuItem( self, menu, trash_delete_phrase, 'Delete the selected files from the trash, forcing an immediate physical delete from your hard drive.', self._Delete, CC.TRASH_SERVICE_KEY )
                ClientGUIMenus.AppendMenuItem( self, menu, undelete_phrase, 'Restore the selected files back to \'my files\'.', self._Undelete )
                
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if focussed_is_local:
                
                ClientGUIMenus.AppendMenuItem( self, menu, 'open externally', 'Launch this file with your OS\'s default program for it.', self._OpenExternally )
                
            
            #
            
            AddKnownURLsViewCopyMenu( self, menu, self._focussed_media, selected_media = self._selected_media )
            
            # share
            
            share_menu = wx.Menu()
            
            #
            
            if focussed_is_local:
                
                show_open_in_web = True
                show_open_in_explorer = advanced_mode and not HC.PLATFORM_LINUX
                
                if show_open_in_web or show_open_in_explorer:
                    
                    open_menu = wx.Menu()
                    
                    if show_open_in_web:
                        
                        ClientGUIMenus.AppendMenuItem( self, open_menu, 'in web browser', 'Show this file in your OS\'s web browser.', self._OpenFileInWebBrowser )
                        
                    
                    if show_open_in_explorer:
                        
                        ClientGUIMenus.AppendMenuItem( self, open_menu, 'in file browser', 'Show this file in your OS\'s file browser.', self._OpenFileLocation )
                        
                    
                    ClientGUIMenus.AppendMenu( share_menu, open_menu, 'open' )
                    
                
            
            copy_menu = wx.Menu()
            
            if selection_has_local:
                
                ClientGUIMenus.AppendMenuItem( self, copy_menu, copy_phrase, 'Copy the selected files to the clipboard.', self._CopyFilesToClipboard )
                
                if advanced_mode:
                    
                    copy_hash_menu = wx.Menu()
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha256 (hydrus default)', 'Copy the selected file\'s SHA256 hash to the clipboard.', self._CopyHashToClipboard, 'sha256' )
                    ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'md5', 'Copy the selected file\'s MD5 hash to the clipboard.', self._CopyHashToClipboard, 'md5' )
                    ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha1', 'Copy the selected file\'s SHA1 hash to the clipboard.', self._CopyHashToClipboard, 'sha1' )
                    ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha512', 'Copy the selected file\'s SHA512 hash to the clipboard.', self._CopyHashToClipboard, 'sha512' )
                    
                    ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hash' )
                    
                    if multiple_selected:
                        
                        copy_hash_menu = wx.Menu()
                        
                        ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha256 (hydrus default)', 'Copy the selected files\' SHA256 hashes to the clipboard.', self._CopyHashesToClipboard, 'sha256' )
                        ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'md5', 'Copy the selected files\' MD5 hashes to the clipboard.', self._CopyHashesToClipboard, 'md5' )
                        ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha1', 'Copy the selected files\' SHA1 hashes to the clipboard.', self._CopyHashesToClipboard, 'sha1' )
                        ClientGUIMenus.AppendMenuItem( self, copy_hash_menu, 'sha512', 'Copy the selected files\' SHA512 hashes to the clipboard.', self._CopyHashesToClipboard, 'sha512' )
                        
                        ClientGUIMenus.AppendMenu( copy_menu, copy_hash_menu, 'hashes' )
                        
                    
                
            else:
                
                if advanced_mode:
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_menu, 'sha256 hash', 'Copy the selected file\'s SHA256 hash to the clipboard.', self._CopyHashToClipboard, 'sha256' )
                    
                    if multiple_selected:
                        
                        ClientGUIMenus.AppendMenuItem( self, copy_menu, 'sha256 hashes', 'Copy the selected files\' SHA256 hash to the clipboard.', self._CopyHashesToClipboard, 'sha256' )
                        
                    
                
            
            for ipfs_service_key in self._focussed_media.GetLocationsManager().GetCurrentRemote().intersection( ipfs_service_keys ):
                
                name = service_keys_to_names[ ipfs_service_key ]
                
                ClientGUIMenus.AppendMenuItem( self, copy_menu, name + ' multihash', 'Copy the selected file\'s multihash to the clipboard.', self._CopyServiceFilenameToClipboard, ipfs_service_key )
                
            
            if multiple_selected:
                
                for ipfs_service_key in disparate_current_ipfs_service_keys.union( common_current_ipfs_service_keys ):
                    
                    name = service_keys_to_names[ ipfs_service_key ]
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_menu, name + ' multihashes', 'Copy the selected files\' multihashes to the clipboard.', self._CopyServiceFilenamesToClipboard, ipfs_service_key )
                    
                
            
            if focussed_is_local:
                
                if self._focussed_media.GetMime() in HC.IMAGES and self._focussed_media.GetDuration() is None:
                    
                    ClientGUIMenus.AppendMenuItem( self, copy_menu, 'image (bitmap)', 'Copy the selected file\'s image data to the clipboard (as a bmp).', self._CopyBMPToClipboard )
                    
                
                ClientGUIMenus.AppendMenuItem( self, copy_menu, 'path', 'Copy the selected file\'s path to the clipboard.', self._CopyPathToClipboard )
                
            
            if multiple_selected and selection_has_local:
                
                ClientGUIMenus.AppendMenuItem( self, copy_menu, 'paths', 'Copy the selected files\' paths to the clipboard.', self._CopyPathsToClipboard )
                
            
            ClientGUIMenus.AppendMenu( share_menu, copy_menu, 'copy' )
            
            #
            
            export_menu  = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, export_menu, export_phrase, 'Export the selected files to an external folder.', self._ExportFiles )
            
            if advanced_mode:
                
                ClientGUIMenus.AppendMenuItem( self, export_menu, 'tags', 'Export the selected files\' tags to an external database.', self._ExportTags )
                
            
            ClientGUIMenus.AppendMenu( share_menu, export_menu, 'export' )
            
            #
            
            if local_booru_is_running:
                
                ClientGUIMenus.AppendMenuItem( self, share_menu, 'on local booru', 'Share the selected files on your client\'s local booru.', self._ShareOnLocalBooru )
                
            
            #
            
            ClientGUIMenus.AppendMenu( menu, share_menu, 'share' )
            
            #
            
            ClientGUIMenus.AppendSeparator( menu )
            
        
        ClientGUIMenus.AppendMenuItem( self, menu, 'refresh', 'Refresh the current search.', HG.client_controller.pub, 'refresh_query', self._page_key )
        
        if len( self._sorted_media ) > 0:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            select_menu = wx.Menu()
            
            if len( self._selected_media ) < len( self._sorted_media ):
                
                all_label = 'all (' + HydrusData.ToHumanInt( len( self._sorted_media ) ) + ')'
                
                if media_has_archive and not media_has_inbox:
                    
                    all_label += ' (all in archive)'
                    
                elif media_has_inbox and not media_has_archive:
                    
                    all_label += ' (all in inbox)'
                    
                
                ClientGUIMenus.AppendMenuItem( self, select_menu, all_label, 'Select everything.', self._Select, 'all' )
                
            
            if media_has_archive and media_has_inbox:
                
                inbox_label = 'inbox (' + HydrusData.ToHumanInt( num_inbox ) + ')'
                archive_label = 'archive (' + HydrusData.ToHumanInt( num_archive ) + ')'
                
                ClientGUIMenus.AppendMenuItem( self, select_menu, inbox_label, 'Select everything in the inbox.', self._Select, 'inbox' )
                ClientGUIMenus.AppendMenuItem( self, select_menu, archive_label, 'Select everything that is archived.', self._Select, 'archive' )
                
            
            if len( all_specific_file_domains ) > 1:
                
                selectable_file_domains = list( all_local_file_domains )
                
                if CC.TRASH_SERVICE_KEY in all_specific_file_domains:
                    
                    selectable_file_domains.append( CC.TRASH_SERVICE_KEY )
                    
                
                selectable_file_domains.extend( all_file_repos )
                
                for service_key in selectable_file_domains:
                    
                    name = services_manager.GetName( service_key )
                    
                    ClientGUIMenus.AppendMenuItem( self, select_menu, name, 'Select everything in ' + name + '.', self._Select, 'file_service', service_key )
                    
                
            
            if has_local and has_remote:
                
                ClientGUIMenus.AppendMenuItem( self, select_menu, 'local', 'Select everything in the client.', self._Select, 'local' )
                ClientGUIMenus.AppendMenuItem( self, select_menu, 'remote', 'Select everything that is not in the client.', self._Select, 'remote' )
                
            
            if len( self._selected_media ) > 0:
                
                if len( self._selected_media ) < len( self._sorted_media ):
                
                    invert_label = 'invert (' + HydrusData.ToHumanInt( len( self._sorted_media ) - len( self._selected_media ) ) + ')'
                    
                    ClientGUIMenus.AppendMenuItem( self, select_menu, invert_label, 'Swap what is and is not selected.', self._Select, 'invert' )
                    
                
                ClientGUIMenus.AppendMenuItem( self, select_menu, 'none (0)', 'Deselect everything.', self._Select, 'none' )
                
            
            ClientGUIMenus.AppendMenu( menu, select_menu, 'select' )
            
        
        if self._focussed_media is not None:
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'open selection in a new page', 'Copy your current selection into a simple new page.', self._ShowSelectionInNewPage )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            duplicates_menu = wx.Menu()
            
            focussed_hash = self._focussed_media.GetDisplayMedia().GetHash()
            
            if HG.client_controller.DBCurrentlyDoingJob():
                
                file_duplicate_info = None
                
            else:
                
                file_duplicate_info = HG.client_controller.Read( 'file_duplicate_info', self._file_service_key, focussed_hash )
                
            
            focus_is_in_duplicate_group = False
            focus_is_in_alternate_group = False
            focus_has_fps = False
            focus_can_be_searched = self._focussed_media.GetDisplayMedia().GetMime() in HC.MIMES_WE_CAN_PHASH
            
            if file_duplicate_info is None:
                
                ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'could not fetch file\'s duplicates (db currently locked)' )
                
            else:
                
                file_duplicate_types_to_counts = file_duplicate_info[ 'counts' ]
                
                if len( file_duplicate_types_to_counts ) > 0:
                    
                    duplicates_view_menu = wx.Menu()
                    
                    if HC.DUPLICATE_MEMBER in file_duplicate_types_to_counts:
                        
                        if file_duplicate_info[ 'is_king' ]:
                            
                            ClientGUIMenus.AppendMenuLabel( duplicates_view_menu, 'this is the best quality file of its group' )
                            
                        else:
                            
                            ClientGUIMenus.AppendMenuItem( self, duplicates_view_menu, 'show the best quality file of this file\'s group', 'Load up a new search with this file\'s best quality duplicate.', self._ShowDuplicatesInNewPage, focussed_hash, HC.DUPLICATE_KING )
                            
                        
                        ClientGUIMenus.AppendSeparator( duplicates_view_menu )
                        
                    
                    for duplicate_type in ( HC.DUPLICATE_MEMBER, HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE, HC.DUPLICATE_POTENTIAL ):
                        
                        if duplicate_type in file_duplicate_types_to_counts:
                            
                            count = file_duplicate_types_to_counts[ duplicate_type ]
                            
                            if count > 0:
                                
                                label = HydrusData.ToHumanInt( count ) + ' ' + HC.duplicate_type_string_lookup[ duplicate_type ]
                                
                                ClientGUIMenus.AppendMenuItem( self, duplicates_view_menu, label, 'Show these duplicates in a new page.', self._ShowDuplicatesInNewPage, focussed_hash, duplicate_type )
                                
                                if duplicate_type == HC.DUPLICATE_MEMBER:
                                    
                                    focus_is_in_duplicate_group = True
                                    
                                elif duplicate_type == HC.DUPLICATE_ALTERNATE:
                                    
                                    focus_is_in_alternate_group = True
                                    
                                elif duplicate_type == HC.DUPLICATE_FALSE_POSITIVE:
                                    
                                    focus_has_fps = True
                                    
                                
                            
                        
                    
                    ClientGUIMenus.AppendMenu( duplicates_menu, duplicates_view_menu, 'view this file\'s relations' )
                    
                
            
            focus_is_definitely_king = file_duplicate_info is not None and file_duplicate_info[ 'is_king' ]
            
            dissolution_actions_available = focus_can_be_searched or focus_is_in_duplicate_group or focus_is_in_alternate_group or focus_has_fps
            
            single_action_available = dissolution_actions_available or not focus_is_definitely_king
            
            if multiple_selected or single_action_available:
                
                duplicates_action_submenu = wx.Menu()
                
                if file_duplicate_info is None:
                    
                    ClientGUIMenus.AppendMenuLabel( duplicates_action_submenu, 'could not fetch info to check for available file actions (db currently locked)' )
                    
                else:
                    
                    if not focus_is_definitely_king:
                        
                        ClientGUIMenus.AppendMenuItem( self, duplicates_action_submenu, 'set this file as the best quality of its group', 'Set the focused media to be the King of its group.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_set_focused_king' ) )
                        
                    
                    if dissolution_actions_available:
                        
                        duplicates_single_dissolution_menu = wx.Menu()
                        
                        media_to_action = self._focussed_media.GetDisplayMedia()
                        
                        if focus_can_be_searched:
                            
                            ClientGUIMenus.AppendMenuItem( self, duplicates_single_dissolution_menu, 'schedule this file to be searched for potentials again', 'Queue this file for another potentials search. Will not remove any existing potentials.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_reset_focused_potential_search' ) )
                            
                        
                        if focus_is_in_duplicate_group:
                            
                            if not focus_is_definitely_king:
                                
                                ClientGUIMenus.AppendMenuItem( self, duplicates_single_dissolution_menu, 'remove this file from its duplicate group', 'Extract this file from its duplicate group and reset its search status.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_remove_focus_from_duplicate_group' ) )
                                
                            
                            ClientGUIMenus.AppendMenuItem( self, duplicates_single_dissolution_menu, 'dissolve this file\'s duplicate group completely', 'Completely eliminate this file\'s duplicate group and reset all files\' search status.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_dissolve_focus_duplicate_group' ) )
                            
                        
                        if focus_is_in_alternate_group:
                            
                            ClientGUIMenus.AppendMenuItem( self, duplicates_single_dissolution_menu, 'remove this file from its alternate group', 'Extract this file\'s duplicate group from its alternate group and reset the duplicate group\'s search status.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_remove_focus_from_alternate_group' ) )
                            
                            ClientGUIMenus.AppendMenuItem( self, duplicates_single_dissolution_menu, 'dissolve thes file\'s alternate group completely', 'Completely eliminate this file\'s alternate group and all duplicate group members. This resets search status for all involved files.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_dissolve_focus_alternate_group' ) )
                            
                        
                        if focus_has_fps:
                            
                            ClientGUIMenus.AppendMenuItem( self, duplicates_single_dissolution_menu, 'delete all false-positive relationships this file\'s alternate group has with other groups', 'Clear out all false-positive relationships this file\'s alternates group has with other groups and resets search status.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_clear_focused_false_positives' ) )
                            
                        
                        ClientGUIMenus.AppendMenu( duplicates_action_submenu, duplicates_single_dissolution_menu, 'remove/reset for this file' )
                        
                    
                
                if multiple_selected:
                    
                    ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
                    
                    label = 'set this file as better than the ' + HydrusData.ToHumanInt( num_selected - 1 ) + ' other selected'
                    
                    ClientGUIMenus.AppendMenuItem( self, duplicates_action_submenu, label, 'Set the focused media to be better than the other selected files.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_set_focused_better' ) )
                    
                    num_files = self._GetNumSelected()
                    
                    num_pairs = num_files * ( num_files - 1 ) / 2 # com // ations -- n!/2(n-2)!
                    
                    num_pairs_text = HydrusData.ToHumanInt( num_pairs ) + ' pairs'
                    
                    ClientGUIMenus.AppendMenuItem( self, duplicates_action_submenu, 'set all selected as same quality duplicates', 'Set all the selected files as same quality duplicates.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_set_same_quality' ) )
                    
                    ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
                    
                    ClientGUIMenus.AppendMenuItem( self, duplicates_action_submenu, 'set all selected as alternates', 'Set all the selected files as alternates.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_set_alternate' ) )
                    
                    ClientGUIMenus.AppendMenuItem( self, duplicates_action_submenu, 'set a relationship with custom metadata merge options', 'Choose which duplicates status to set to this selection and customise non-default duplicate metadata merge options.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_set_custom' ) )
                    
                    if collections_selected:
                        
                        ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
                        
                        ClientGUIMenus.AppendMenuItem( self, duplicates_action_submenu, 'set selected collections as groups of alternates', 'Set files in the selection which are collected together as alternates.', self.ProcessApplicationCommand, ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, 'duplicate_media_set_alternate_collections' ) )
                        
                    
                    duplicates_edit_action_submenu = wx.Menu()
                    
                    for duplicate_type in ( HC.DUPLICATE_BETTER, HC.DUPLICATE_SAME_QUALITY ):
                        
                        ClientGUIMenus.AppendMenuItem( self, duplicates_edit_action_submenu, 'for ' + HC.duplicate_type_string_lookup[ duplicate_type ], 'Edit what happens when you set this status.', self._EditDuplicateActionOptions, duplicate_type )
                        
                    
                    if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                        
                        ClientGUIMenus.AppendMenuItem( self, duplicates_edit_action_submenu, 'for ' + HC.duplicate_type_string_lookup[ HC.DUPLICATE_ALTERNATE ] + ' (advanced!)', 'Edit what happens when you set this status.', self._EditDuplicateActionOptions, HC.DUPLICATE_ALTERNATE )
                        
                    
                    ClientGUIMenus.AppendSeparator( duplicates_action_submenu )
                    
                    ClientGUIMenus.AppendMenu( duplicates_action_submenu, duplicates_edit_action_submenu, 'edit default duplicate metadata merge options' )
                    '''
                    if advanced_mode:
                        
                        duplicates_multiple_dissolution_menu = wx.Menu()
                        
                        # reset all search status
                        # dissolve all medias
                        # dissolve all alternates
                        # clear all fps
                        # clear all fps within group
                        
                        ClientGUIMenus.AppendMenu( duplicates_action_submenu, duplicates_multiple_dissolution_menu, 'remove/reset for this file' )
                        
                    '''
                
                ClientGUIMenus.AppendMenu( duplicates_menu, duplicates_action_submenu, 'set relationship' )
                
            
            if self._focussed_media.HasImages():
                
                similar_menu = wx.Menu()
                
                ClientGUIMenus.AppendMenuItem( self, similar_menu, 'exact match', 'Search the database for files that look precisely like this one.', self._GetSimilarTo, HC.HAMMING_EXACT_MATCH )
                ClientGUIMenus.AppendMenuItem( self, similar_menu, 'very similar', 'Search the database for files that look just like this one.', self._GetSimilarTo, HC.HAMMING_VERY_SIMILAR )
                ClientGUIMenus.AppendMenuItem( self, similar_menu, 'similar', 'Search the database for files that look generally like this one.', self._GetSimilarTo, HC.HAMMING_SIMILAR )
                ClientGUIMenus.AppendMenuItem( self, similar_menu, 'speculative', 'Search the database for files that probably look like this one. This is sometimes useful for symbols with sharp edges or lines.', self._GetSimilarTo, HC.HAMMING_SPECULATIVE )
                
                ClientGUIMenus.AppendMenu( duplicates_menu, similar_menu, 'find similar-looking files' )
                
            
            if duplicates_menu.GetMenuItemCount() == 0:
                
                ClientGUIMenus.AppendMenuLabel( duplicates_menu, 'no file relationships or actions available for this file at present' )
                
            
            ClientGUIMenus.AppendMenu( menu, duplicates_menu, 'file relationships' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            regen_menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, regen_menu, 'thumbnails, but only if wrong size', 'Regenerate the selected files\' thumbnails, but only if they are the wrong size.', self._RegenerateFileData, ClientFiles.REGENERATE_FILE_DATA_JOB_REFIT_THUMBNAIL )
            ClientGUIMenus.AppendMenuItem( self, regen_menu, 'thumbnails', 'Regenerate the selected files\'s thumbnails.', self._RegenerateFileData, ClientFiles.REGENERATE_FILE_DATA_JOB_FORCE_THUMBNAIL )
            ClientGUIMenus.AppendMenuItem( self, regen_menu, 'file metadata and thumbnails', 'Regenerated the selected files\' metadata and thumbnails.', self._RegenerateFileData, ClientFiles.REGENERATE_FILE_DATA_JOB_COMPLETE )
            
            ClientGUIMenus.AppendMenu( menu, regen_menu, 'regenerate' )
            
        
        HG.client_controller.PopupMenu( self, menu )
        
        event.Skip()
        
    
    def MaintainPageCache( self ):
        
        if not HG.client_controller.GetGUI().IsCurrentPage( self._page_key ):
            
            self._DirtyAllPages()
            
        
        self._DeleteAllDirtyPages()
        
    
    def NewFileInfo( self, hashes ):
        
        affected_media = self._GetMedia( hashes )
        
        for media in affected_media:
            
            media.RefreshFileInfo()
            
        
    
    def NewThumbnails( self, hashes ):
        
        affected_thumbnails = self._GetMedia( hashes )
        
        if len( affected_thumbnails ) > 0:
            
            self._RedrawMedia( affected_thumbnails )
            
        
    
    def RefreshAcceleratorTable( self ):
        
        if not self:
            
            return
            
        
        entries = [
        ( wx.ACCEL_NORMAL, wx.WXK_HOME, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'scroll_home' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_HOME, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'scroll_home' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_END, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'scroll_end' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_END, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'scroll_end' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'delete_file' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'delete_file' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_RETURN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'fullscreen' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_ENTER, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'fullscreen' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_UP, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_up' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_UP, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_up' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_DOWN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_down' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_DOWN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_down' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_LEFT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_left' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_LEFT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_left' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_RIGHT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_right' ) ),
        ( wx.ACCEL_NORMAL, wx.WXK_NUMPAD_RIGHT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_right' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_HOME, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'shift_scroll_home' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_HOME, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'shift_scroll_home' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_END, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'shift_scroll_end' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_END, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'shift_scroll_end' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'undelete' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_DELETE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'undelete' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_UP, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_up' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_UP, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_up' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_DOWN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_down' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_DOWN, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_down' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_LEFT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_left' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_LEFT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_left' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_RIGHT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_right' ) ),
        ( wx.ACCEL_SHIFT, wx.WXK_NUMPAD_RIGHT, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'key_shift_right' ) ),
        ( wx.ACCEL_CTRL, ord( 'A' ), ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'select', 'all' ) ),
        ( wx.ACCEL_CTRL, wx.WXK_SPACE, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'ctrl-space' )  )
        ]
        
        if HC.PLATFORM_OSX:
            
            entries.append( ( wx.ACCEL_NORMAL, wx.WXK_BACK, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'delete_file' ) ) )
            entries.append( ( wx.ACCEL_SHIFT, wx.WXK_BACK, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( 'undelete' ) ) )
            
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
    def SetFocussedMedia( self, page_key, media ):
        
        MediaPanel.SetFocussedMedia( self, page_key, media )
        
        if page_key == self._page_key:
            
            if media is None:
                
                self._SetFocussedMedia( None )
                
            else:
                
                try:
                    
                    my_media = self._GetMedia( media.GetHashes() )[0]
                    
                    self._HitMedia( my_media, False, False )
                    
                    self._ScrollToMedia( self._focussed_media )
                    
                except:
                    
                    pass
                    
                
            
        
    
    def Sort( self, page_key, media_sort = None ):
        
        MediaPanel.Sort( self, page_key, media_sort )
        
        self._DirtyAllPages()
        
        self.Refresh()
        
    
    def ThumbnailsResized( self ):
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnail_scroll_rate = float( HG.client_controller.new_options.GetString( 'thumbnail_scroll_rate' ) )
        
        self.SetScrollRate( 0, int( round( thumbnail_span_height * thumbnail_scroll_rate ) ) )
        
        self._thumbnails_being_faded_in = {}
        self._hashes_faded = set()
        
        self._ReinitialisePageCacheIfNeeded()
        
        self._RecalculateVirtualSize()
        
        self._DirtyAllPages()
        
        self.Refresh()
        
    
    def TIMERAnimationUpdate( self ):
        
        FRAME_DURATION = 1.0 / 60
        NUM_FRAMES_TO_FILL_IN = 15
        
        loop_started = HydrusData.GetNowPrecise()
        loop_should_break_time = loop_started + ( FRAME_DURATION / 2 )
        
        ( thumbnail_span_width, thumbnail_span_height ) = self._GetThumbnailSpanDimensions()
        
        thumbnail_margin = HG.client_controller.new_options.GetInteger( 'thumbnail_margin' )
        
        hashes = list( self._thumbnails_being_faded_in.keys() )
        
        random.shuffle( hashes )
        
        dcs = {}
        
        ( xUnit, yUnit ) = self.GetScrollPixelsPerUnit()
        
        y_start = self._GetYStart()
        
        earliest_y = y_start * yUnit
        
        page_height = self._num_rows_per_canvas_page * thumbnail_span_height
        
        for hash in hashes:
            
            ( original_bmp, alpha_bmp, thumbnail_index, thumbnail, animation_started, num_frames_rendered ) = self._thumbnails_being_faded_in[ hash ]
            
            num_frames_supposed_to_be_rendered = int( ( loop_started - animation_started ) / FRAME_DURATION )
            
            num_frames_to_render = num_frames_supposed_to_be_rendered - num_frames_rendered
            
            if num_frames_to_render == 0:
                
                continue
                
            
            delete_entry = False
            
            try:
                
                expected_thumbnail = self._sorted_media[ thumbnail_index ]
                
            except:
                
                expected_thumbnail = None
                
            
            page_index = self._GetPageIndexFromThumbnailIndex( thumbnail_index )
            
            if expected_thumbnail != thumbnail:
                
                delete_entry = True
                
            elif page_index not in self._clean_canvas_pages:
                
                delete_entry = True
                
            else:
                
                times_to_draw = 1
                
                if num_frames_supposed_to_be_rendered >= NUM_FRAMES_TO_FILL_IN:
                    
                    bmp_to_use = original_bmp
                    
                    delete_entry = True
                    
                else:
                    
                    times_to_draw = num_frames_to_render
                    
                    bmp_to_use = alpha_bmp
                    
                    num_frames_rendered += times_to_draw
                    
                    self._thumbnails_being_faded_in[ hash ] = ( original_bmp, alpha_bmp, thumbnail_index, thumbnail, animation_started, num_frames_rendered )
                    
                
                thumbnail_col = thumbnail_index % self._num_columns
                
                thumbnail_row = thumbnail_index // self._num_columns
                
                x = thumbnail_col * thumbnail_span_width + thumbnail_margin
                
                y = ( thumbnail_row - ( page_index * self._num_rows_per_canvas_page ) ) * thumbnail_span_height + thumbnail_margin
                
                if page_index not in dcs:
                    
                    canvas_bmp = self._clean_canvas_pages[ page_index ]
                    
                    dc = wx.MemoryDC( canvas_bmp )
                    
                    dcs[ page_index ] = dc
                    
                
                dc = dcs[ page_index ]
                
                for i in range( times_to_draw ):
                    
                    dc.DrawBitmap( bmp_to_use, x, y, True )
                    
                
                #
                
                page_virtual_y = page_height * page_index
                
                page_client_y = page_virtual_y - earliest_y
                
                client_y = page_client_y + y
                
                self.RefreshRect( wx.Rect( x, client_y, thumbnail_span_width - thumbnail_margin, thumbnail_span_height - thumbnail_margin ) )
                
            
            if delete_entry:
                
                del self._thumbnails_being_faded_in[ hash ]
                
                HG.client_controller.bitmap_manager.ReleaseBitmap( original_bmp )
                HG.client_controller.bitmap_manager.ReleaseBitmap( alpha_bmp )
                
            
            if HydrusData.TimeHasPassedPrecise( loop_should_break_time ):
                
                break
                
            
        
        if len( self._thumbnails_being_faded_in ) == 0:
            
            HG.client_controller.gui.UnregisterAnimationUpdateWindow( self )
            
        
        
    
    def WaterfallThumbnails( self, page_key, thumbnails ):
        
        if self._page_key == page_key:
            
            self._FadeThumbnails( thumbnails )
            
        
    
class Selectable( object ):
    
    def __init__( self ): self._selected = False
    
    def Deselect( self ): self._selected = False
    
    def IsSelected( self ): return self._selected
    
    def Select( self ): self._selected = True
    
class Thumbnail( Selectable ):
    
    def __init__( self, file_service_key ):
        
        Selectable.__init__( self )
        
        self._dump_status = CC.DUMPER_NOT_DUMPED
        self._file_service_key = file_service_key
        
    
    def _ScaleUpThumbnailDimensions( self, thumbnail_dimensions, scale_up_dimensions ):
        
        ( thumb_width, thumb_height ) = thumbnail_dimensions
        ( scale_up_width, scale_up_height ) = scale_up_dimensions
        
        # we want to expand the image so that the smallest dimension fills everything
        
        scale_factor = max( scale_up_width / thumb_width, scale_up_height / thumb_height )
        
        destination_width = int( round( thumb_width * scale_factor ) )
        destination_height = int( round( thumb_height * scale_factor ) )
        
        offset_x = ( scale_up_width - destination_width ) // 2
        offset_y = ( scale_up_height - destination_height ) // 2
        
        offset_position = ( offset_x, offset_y )
        destination_dimensions = ( destination_width, destination_height )
        
        return ( offset_position, destination_dimensions )
        
    
    def Dumped( self, dump_status ):
        
        self._dump_status = dump_status
        
    
    def GetBmp( self ):
        
        inbox = self.HasInbox()
        
        local = self.GetLocationsManager().IsLocal()
        
        thumbnail_hydrus_bmp = HG.client_controller.GetCache( 'thumbnail' ).GetThumbnail( self )
        
        thumbnail_border = HG.client_controller.new_options.GetInteger( 'thumbnail_border' )
        
        ( width, height ) = ClientData.AddPaddingToDimensions( HC.options[ 'thumbnail_dimensions' ], thumbnail_border * 2 )
        
        bmp = HG.client_controller.bitmap_manager.GetBitmap( width, height, 24 )
        
        dc = wx.MemoryDC( bmp )
        
        new_options = HG.client_controller.new_options
        
        if not local:
            
            if self._selected:
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED
                
            else:
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND_REMOTE
                
            
        else:
            
            if self._selected:
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND_SELECTED
                
            else:
                
                background_colour_type = CC.COLOUR_THUMB_BACKGROUND
                
            
        
        dc.SetPen( wx.TRANSPARENT_PEN )
        
        dc.SetBrush( wx.Brush( new_options.GetColour( background_colour_type ) ) )
        
        dc.DrawRectangle( thumbnail_border, thumbnail_border, width - ( thumbnail_border * 2 ), height - ( thumbnail_border * 2 ) )
        
        thumbnail_fill = HG.client_controller.new_options.GetBoolean( 'thumbnail_fill' )
        
        ( thumb_width, thumb_height ) = thumbnail_hydrus_bmp.GetSize()
        
        if thumbnail_fill:
            
            wx_image = thumbnail_hydrus_bmp.GetWxImage()
            
            scale_up_dimensions = HC.options[ 'thumbnail_dimensions' ]
            
            ( offset_position, destination_dimensions ) = self._ScaleUpThumbnailDimensions( ( thumb_width, thumb_height ), scale_up_dimensions )
            
            ( destination_width, destination_height ) = destination_dimensions
            
            wx_image = wx_image.Scale( destination_width, destination_height, wx.IMAGE_QUALITY_HIGH )
            
            wx_bmp = wx.Bitmap( wx_image )
            
            wx_image.Destroy()
            
            ( x_offset, y_offset ) = offset_position
            
            x_offset += thumbnail_border
            y_offset += thumbnail_border
            
        else:
            
            wx_bmp = thumbnail_hydrus_bmp.GetWxBitmap()
            
            x_offset = ( width - thumb_width ) // 2
            
            y_offset = ( height - thumb_height ) // 2
            
        
        dc.DrawBitmap( wx_bmp, x_offset, y_offset )
        
        HG.client_controller.bitmap_manager.ReleaseBitmap( wx_bmp )
        
        new_options = HG.client_controller.new_options
        
        tm = self.GetTagsManager()
        
        tags = tm.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY ).union( tm.GetPending( CC.COMBINED_TAG_SERVICE_KEY ) )
        
        if len( tags ) > 0:
            
            siblings_manager = HG.client_controller.tag_siblings_manager
            
            tags = siblings_manager.CollapseTags( CC.COMBINED_TAG_SERVICE_KEY, tags )
            
            upper_tag_summary_generator = new_options.GetTagSummaryGenerator( 'thumbnail_top' )
            
            upper_summary = upper_tag_summary_generator.GenerateSummary( tags )
            
            lower_tag_summary_generator = new_options.GetTagSummaryGenerator( 'thumbnail_bottom_right' )
            
            lower_summary = lower_tag_summary_generator.GenerateSummary( tags )
            
            if len( upper_summary ) > 0 or len( lower_summary ) > 0:
                
                gc = wx.GraphicsContext.Create( dc )
                
                if len( upper_summary ) > 0:
                    
                    text_colour_with_alpha = upper_tag_summary_generator.GetTextColour()
                    
                    # protip, this renders unicode characters (such as \U0001f50a) in the Supplementary Multilingual Plane incorrectly, wew
                    # DeviceContext does render them ok somehow
                    
                    gc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ), text_colour_with_alpha )
                    
                    background_colour_with_alpha = upper_tag_summary_generator.GetBackgroundColour()
                    
                    gc.SetBrush( wx.Brush( background_colour_with_alpha ) )
                    
                    gc.SetPen( wx.TRANSPARENT_PEN )
                    
                    ( text_x, text_y ) = gc.GetTextExtent( upper_summary )
                    
                    top_left_x = int( ( width - text_x ) // 2 )
                    top_left_y = thumbnail_border
                    
                    gc.DrawRectangle( thumbnail_border, top_left_y, width - ( thumbnail_border * 2 ), text_y + 1 )
                    
                    gc.DrawText( upper_summary, top_left_x, top_left_y )
                    
                
                if len( lower_summary ) > 0:
                    
                    text_colour_with_alpha = lower_tag_summary_generator.GetTextColour()
                    
                    gc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ), text_colour_with_alpha )
                    
                    background_colour_with_alpha = lower_tag_summary_generator.GetBackgroundColour()
                    
                    gc.SetBrush( wx.Brush( background_colour_with_alpha ) )
                    
                    gc.SetPen( wx.TRANSPARENT_PEN )
                    
                    ( text_x, text_y ) = gc.GetTextExtent( lower_summary )
                    
                    top_left_x = width - text_x - thumbnail_border
                    top_left_y = height - text_y - thumbnail_border
                    
                    gc.DrawRectangle( top_left_x - 1, top_left_y - 1, text_x + 1, text_y + 1 )
                    
                    gc.DrawText( lower_summary, top_left_x, top_left_y )
                    
                
                del gc
                
            
        
        if thumbnail_border > 0:
            
            if not local:
                
                if self._selected:
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED
                    
                else:
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER_REMOTE
                    
                
            else:
                
                if self._selected:
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER_SELECTED
                    
                else:
                    
                    border_colour_type = CC.COLOUR_THUMB_BORDER
                    
                
            
            # I had a hell of a time getting a transparent box to draw right with a pen border without crazy +1px in the params for reasons I did not understand
            # so I just decided four rects is neater and fine and actually prob faster in some cases
            
            #         _____            ______                              _____            ______      ________________
            # ___________(_)___  _________  /_______   _______ ______      __  /______      ___  /_________  /__  /__  /
            # ___  __ \_  /__  |/_/  _ \_  /__  ___/   __  __ `/  __ \     _  __/  __ \     __  __ \  _ \_  /__  /__  / 
            # __  /_/ /  / __>  < /  __/  / _(__  )    _  /_/ // /_/ /     / /_ / /_/ /     _  / / /  __/  / _  /  /_/  
            # _  .___//_/  /_/|_| \___//_/  /____/     _\__, / \____/      \__/ \____/      /_/ /_/\___//_/  /_/  (_)   
            # /_/                                      /____/                                                            
            
            dc.SetBrush( wx.Brush( new_options.GetColour( border_colour_type ) ) )
            
            rectangles = []
            
            side_height = height - ( thumbnail_border * 2 )
            
            rectangles.append( ( 0, 0, width, thumbnail_border ) ) # top
            rectangles.append( ( 0, height - thumbnail_border, width, thumbnail_border ) ) # bottom
            rectangles.append( ( 0, thumbnail_border, thumbnail_border, side_height ) ) # left
            rectangles.append( ( width - thumbnail_border, thumbnail_border, thumbnail_border, side_height ) ) # right
            
            dc.DrawRectangleList( rectangles )
            
        
        locations_manager = self.GetLocationsManager()
        
        icons_to_draw = []
        
        if locations_manager.IsDownloading():
            
            icons_to_draw.append( CC.GlobalBMPs.downloading )
            
        
        if CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() or CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted():
            
            icons_to_draw.append( CC.GlobalBMPs.trash )
            
        
        if inbox:
            
            icons_to_draw.append( CC.GlobalBMPs.inbox )
            
        
        if len( icons_to_draw ) > 0:
            
            icon_x = 0
            
            for icon in icons_to_draw:
                
                dc.DrawBitmap( icon, width + icon_x - 18, 0 )
                
                icon_x -= 18
                
            
        
        if self._dump_status == CC.DUMPER_DUMPED_OK: dc.DrawBitmap( CC.GlobalBMPs.dump_ok, width - 18, 18 )
        elif self._dump_status == CC.DUMPER_RECOVERABLE_ERROR: dc.DrawBitmap( CC.GlobalBMPs.dump_recoverable, width - 18, 18 )
        elif self._dump_status == CC.DUMPER_UNRECOVERABLE_ERROR: dc.DrawBitmap( CC.GlobalBMPs.dump_fail, width - 18, 18 )
        
        if self.IsCollection():
            
            dc.DrawBitmap( CC.GlobalBMPs.collection, 1, height - 17 )
            
            num_files_str = str( len( self._hashes ) )
            
            dc.SetFont( wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT ) )
            
            ( text_x, text_y ) = dc.GetTextExtent( num_files_str )
            
            dc.SetBrush( wx.Brush( CC.COLOUR_UNSELECTED ) )
            
            dc.SetTextForeground( CC.COLOUR_SELECTED_DARK )
            
            dc.SetPen( wx.TRANSPARENT_PEN )
            
            dc.DrawRectangle( 17, height - text_y - 3, text_x + 2, text_y + 2 )
            
            dc.DrawText( num_files_str, 18, height - text_y - 2 )
            
        
        # repo icons
        
        services_manager = HG.client_controller.services_manager
        
        repo_icon_x = 0
        
        current = locations_manager.GetCurrentRemote()
        pending = locations_manager.GetPendingRemote()
        petitioned = locations_manager.GetPetitionedRemote()
        
        current_to_display = current.difference( petitioned )
        
        #
        
        service_types = [ services_manager.GetService( service_key ).GetServiceType() for service_key in current_to_display ]
        
        if HC.FILE_REPOSITORY in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.file_repository, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        if HC.IPFS in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.ipfs, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        #
        
        service_types = [ services_manager.GetService( service_key ).GetServiceType() for service_key in pending ]
        
        if HC.FILE_REPOSITORY in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.file_repository_pending, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        if HC.IPFS in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.ipfs_pending, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        #
        
        service_types = [ services_manager.GetService( service_key ).GetServiceType() for service_key in petitioned ]
        
        if HC.FILE_REPOSITORY in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.file_repository_petitioned, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        if HC.IPFS in service_types:
            
            dc.DrawBitmap( CC.GlobalBMPs.ipfs_petitioned, repo_icon_x, 0 )
            
            repo_icon_x += 20
            
        
        return bmp
        
    
class ThumbnailMediaCollection( Thumbnail, ClientMedia.MediaCollection ):
    
    def __init__( self, file_service_key, media_results ):
        
        ClientMedia.MediaCollection.__init__( self, file_service_key, media_results )
        Thumbnail.__init__( self, file_service_key )
        
    
class ThumbnailMediaSingleton( Thumbnail, ClientMedia.MediaSingleton ):
    
    def __init__( self, file_service_key, media_result ):
        
        ClientMedia.MediaSingleton.__init__( self, media_result )
        Thumbnail.__init__( self, file_service_key )
        
    
