import collections
import itertools
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusImageHandling

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIScrolledPanelsReview
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags

def ApplyContentApplicationCommandToMedia( parent: QW.QWidget, command: CAC.ApplicationCommand, media: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    if not command.IsContentCommand():
        
        return
        
    
    service_key = command.GetContentServiceKey()
    action = command.GetContentAction()
    value = command.GetContentValue()
    
    try:
        
        service = HG.client_controller.services_manager.GetService( service_key )
        
    except HydrusExceptions.DataMissing:
        
        command_processed = False
        
        return command_processed
        
    
    service_type = service.GetServiceType()
    
    if service_type == HC.LOCAL_FILE_DOMAIN:
        
        if value is not None:
            
            source_service_key = value
            
        else:
            
            source_service_key = None
            
        
        MoveOrDuplicateLocalFiles( parent, service_key, action, media, source_service_key = source_service_key )
        
    else:
        
        if service_type in HC.REAL_TAG_SERVICES:
            
            tag = value
            
            content_updates = GetContentUpdatesForAppliedContentApplicationCommandTags( parent, service_key, service_type, action, media, tag )
            
        elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
            
            if action in ( HC.CONTENT_UPDATE_SET, HC.CONTENT_UPDATE_FLIP ):
                
                rating = value
                
                content_updates = GetContentUpdatesForAppliedContentApplicationCommandRatingsSetFlip( service_key, action, media, rating )
                
            elif action in ( HC.CONTENT_UPDATE_INCREMENT, HC.CONTENT_UPDATE_DECREMENT ) and service_type == HC.LOCAL_RATING_NUMERICAL:
                
                one_star_value = service.GetOneStarValue()
                
                content_updates = GetContentUpdatesForAppliedContentApplicationCommandRatingsIncDec( service_key, one_star_value, action, media )
                
            else:
                
                return True
                
            
        else:
            
            return False
            
        
        if len( content_updates ) > 0:
            
            HG.client_controller.Write( 'content_updates', { service_key : content_updates } )
            
    
    return True
    

def EditFileNotes( win: QW.QWidget, media: ClientMedia.MediaSingleton, name_to_start_on = typing.Optional[ str ] ):
    
    names_to_notes = media.GetNotesManager().GetNamesToNotes()
    
    title = 'manage notes'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditFileNotesPanel( dlg, names_to_notes, name_to_start_on = name_to_start_on )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            hash = media.GetHash()
            
            ( names_to_notes, deletee_names ) = panel.GetValue()
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in names_to_notes.items() ]
            content_updates.extend( [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash, name ) ) for name in deletee_names ] )
            
            service_keys_to_content_updates = { CC.LOCAL_NOTES_SERVICE_KEY : content_updates }
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
        
    
def GetContentUpdatesForAppliedContentApplicationCommandRatingsSetFlip( service_key: bytes, action: int, media: typing.Collection[ ClientMedia.MediaSingleton ], rating: typing.Optional[ float ] ):
    
    hashes = set()
    
    for m in media:
        
        hashes.add( m.GetHash() )
        
    
    can_set = False
    can_unset = False
    
    for m in media:
        
        ratings_manager = m.GetRatingsManager()
        
        current_rating = ratings_manager.GetRating( service_key )
        
        if current_rating == rating and action == HC.CONTENT_UPDATE_FLIP:
            
            can_unset = True
            
        else:
            
            can_set = True
            
        
    
    if can_set:
        
        row = ( rating, hashes )
        
    elif can_unset:
        
        row = ( None, hashes )
        
    else:
        
        return []
        
    
    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, row ) ]
    
    return content_updates
    

def GetContentUpdatesForAppliedContentApplicationCommandRatingsIncDec( service_key: bytes, one_star_value: float, action: int, media: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    if action == HC.CONTENT_UPDATE_INCREMENT:
        
        direction = 1
        initialisation_rating = 0.0
        
    elif action == HC.CONTENT_UPDATE_DECREMENT:
        
        direction = -1
        initialisation_rating = 1.0
        
    else:
        
        return []
        
    
    ratings_to_hashes = collections.defaultdict( set )
    
    for m in media:
        
        ratings_manager = m.GetRatingsManager()
        
        current_rating = ratings_manager.GetRating( service_key )
        
        if current_rating is None:
            
            new_rating = initialisation_rating
            
        else:
            
            new_rating = current_rating + ( one_star_value * direction )
            
            new_rating = max( min( new_rating, 1.0 ), 0.0 )
            
        
        if current_rating != new_rating:
            
            ratings_to_hashes[ new_rating ].add( m.GetHash() )
            
        
    
    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) ) for ( rating, hashes ) in ratings_to_hashes.items() ]
    
    return content_updates
    

def GetContentUpdatesForAppliedContentApplicationCommandTags( parent: QW.QWidget, service_key: bytes, service_type: int, action: int, media: typing.Collection[ ClientMedia.MediaSingleton ], tag: str ):
    
    hashes = set()
    
    for m in media:
        
        hashes.add( m.GetHash() )
        
    
    rows = [ ( tag, hashes ) ]
    
    can_add = False
    can_pend = False
    can_delete = False
    can_petition = True
    can_rescind_pend = False
    can_rescind_petition = False
    
    for m in media:
        
        tags_manager = m.GetTagsManager()
        
        current = tags_manager.GetCurrent( service_key, ClientTags.TAG_DISPLAY_STORAGE )
        pending = tags_manager.GetPending( service_key, ClientTags.TAG_DISPLAY_STORAGE )
        petitioned = tags_manager.GetPetitioned( service_key, ClientTags.TAG_DISPLAY_STORAGE )
        
        if tag not in current:
            
            can_add = True
            
        
        if tag not in current and tag not in pending:
            
            can_pend = True
            
        
        if tag in current and action == HC.CONTENT_UPDATE_FLIP:
            
            can_delete = True
            
        
        if tag in current and tag not in petitioned and action == HC.CONTENT_UPDATE_FLIP:
            
            can_petition = True
            
        
        if tag in pending and action == HC.CONTENT_UPDATE_FLIP:
            
            can_rescind_pend = True
            
        
        if tag in petitioned:
            
            can_rescind_petition = True
            
        
    
    reason = None
    
    if service_type == HC.LOCAL_TAG:
        
        if can_add:
            
            content_update_action = HC.CONTENT_UPDATE_ADD
            
        elif can_delete:
            
            content_update_action = HC.CONTENT_UPDATE_DELETE
            
        else:
            
            return []
            
        
    else:
        
        if can_rescind_petition:
            
            content_update_action = HC.CONTENT_UPDATE_RESCIND_PETITION
            
        elif can_pend:
            
            content_update_action = HC.CONTENT_UPDATE_PEND
            
        elif can_rescind_pend:
            
            content_update_action = HC.CONTENT_UPDATE_RESCIND_PEND
            
        elif can_petition:
            
            message = 'Enter a reason for this tag to be removed. A janitor will review your petition.'
            
            from hydrus.client.gui import ClientGUIDialogs
            
            with ClientGUIDialogs.DialogTextEntry( parent, message ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    content_update_action = HC.CONTENT_UPDATE_PETITION
                    
                    reason = dlg.GetValue()
                    
                else:
                    
                    return []
                    
                
            
        else:
            
            return []
            
        
    
    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_update_action, row, reason = reason ) for row in rows ]
    
    return content_updates
    
def GetLocalFileActionServiceKeys( media: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    local_media_file_service_keys = set( HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) ) )
    
    local_duplicable_to_file_service_keys = set()
    local_moveable_from_and_to_file_service_keys = set()
    
    for m in media:
        
        locations_manager = m.GetLocationsManager()
        
        current = locations_manager.GetCurrent()
        
        if locations_manager.IsLocal():
            
            can_send_to = local_media_file_service_keys.difference( current )
            can_send_from = local_media_file_service_keys.intersection( current )
            
            if len( can_send_to ) > 0:
                
                local_duplicable_to_file_service_keys.update( can_send_to )
                
                if len( can_send_from ) > 0:
                    
                    # can_send_from does not include trash. we won't say 'move from trash to blah' since that's a little complex. we'll just say 'add to blah' in that case I think
                    
                    local_moveable_from_and_to_file_service_keys.update( list( itertools.product( can_send_from, can_send_to ) ) )
                    
                
            
        
    
    return ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys )
    

def MoveOrDuplicateLocalFiles( win: QW.QWidget, dest_service_key: bytes, action: int, media: typing.Collection[ ClientMedia.MediaSingleton ], source_service_key: typing.Optional[ bytes ] = None ):
    
    dest_service_name = HG.client_controller.services_manager.GetName( dest_service_key )
    
    applicable_media = [ m for m in media if m.GetLocationsManager().IsLocal() and dest_service_key not in m.GetLocationsManager().GetCurrent() and m.GetMime() not in HC.HYDRUS_UPDATE_FILES ]
    
    if len( applicable_media ) == 0:
        
        return
        
    
    ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys ) = GetLocalFileActionServiceKeys( media )
    
    do_yes_no = do_yes_no = HG.client_controller.new_options.GetBoolean( 'confirm_multiple_local_file_services_copy' )
    yes_no_text = 'Add {} files to {}?'.format( HydrusData.ToHumanInt( len( applicable_media ) ), dest_service_name )
    
    if action == HC.CONTENT_UPDATE_MOVE:
        
        do_yes_no = HG.client_controller.new_options.GetBoolean( 'confirm_multiple_local_file_services_move' )
        
        local_moveable_from_and_to_file_service_keys = { pair for pair in local_moveable_from_and_to_file_service_keys if pair[1] == dest_service_key }
        
        potential_source_service_keys = { pair[0] for pair in local_moveable_from_and_to_file_service_keys }
        
        potential_source_service_keys_to_applicable_media = collections.defaultdict( list )
        
        for m in applicable_media:
            
            current = m.GetLocationsManager().GetCurrent()
            
            for potential_source_service_key in potential_source_service_keys:
                
                if potential_source_service_key in current:
                    
                    potential_source_service_keys_to_applicable_media[ potential_source_service_key ].append( m )
                    
                
            
        
        if source_service_key is None:
            
            if len( potential_source_service_keys ) == 0:
                
                return
                
            elif len( potential_source_service_keys ) == 1:
                
                ( source_service_key, ) = potential_source_service_keys
                
            else:
                
                do_yes_no = False
                
                num_applicable_media = len( applicable_media )
                
                choice_tuples = []
                
                for potential_source_service_key in potential_source_service_keys:
                    
                    potential_source_service_name = HG.client_controller.services_manager.GetName( potential_source_service_key )
                    
                    text = 'move {} in "{}" to "{}"'.format( len( potential_source_service_keys_to_applicable_media[ potential_source_service_key ] ), potential_source_service_name, dest_service_name )
                    
                    description = 'Move from {} to {}.'.format( potential_source_service_name, dest_service_name )
                    
                    choice_tuples.append( ( text, potential_source_service_key, description ) )
                    
                
                choice_tuples.sort()
                
                try:
                    
                    source_service_key = ClientGUIDialogsQuick.SelectFromListButtons( win, 'select source service', choice_tuples, message = 'Select where we are moving from. Note this may not cover all files.' )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
        
        source_service_name = HG.client_controller.services_manager.GetName( source_service_key )
        
        applicable_media = potential_source_service_keys_to_applicable_media[ source_service_key ]
        
        yes_no_text = 'Move {} files from {} to {}?'.format( HydrusData.ToHumanInt( len( applicable_media ) ), source_service_name, dest_service_name )
        
    
    if len( applicable_media ) == 0:
        
        return
        
    
    if do_yes_no:
        
        result = ClientGUIDialogsQuick.GetYesNo( win, yes_no_text )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
    
    def work_callable():
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        title = 'moving files' if action == HC.CONTENT_UPDATE_MOVE else 'adding files'
        
        job_key.SetStatusTitle( title )
        
        BLOCK_SIZE = 64
        
        if len( applicable_media ) > BLOCK_SIZE:
            
            HG.client_controller.pub( 'message', job_key )
            
        
        pauser = HydrusData.BigJobPauser()
        
        num_to_do = len( applicable_media )
        
        now = HydrusData.GetNow()
        
        for ( i, block_of_media ) in enumerate( HydrusData.SplitListIntoChunks( applicable_media, BLOCK_SIZE ) ):
            
            if job_key.IsCancelled():
                
                break
                
            
            job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i * BLOCK_SIZE, num_to_do ) )
            job_key.SetVariable( 'popup_gauge_1', ( i * BLOCK_SIZE, num_to_do ) )
            
            content_updates = []
            undelete_hashes = set()
            
            for m in block_of_media:
                
                if dest_service_key in m.GetLocationsManager().GetDeleted():
                    
                    undelete_hashes.add( m.GetHash() )
                    
                else:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( m.GetMediaResult().GetFileInfoManager(), now ) ) )
                    
                
            
            if len( undelete_hashes ) > 0:
                
                content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, undelete_hashes ) )
                
            
            HG.client_controller.WriteSynchronous( 'content_updates', { dest_service_key : content_updates } )
            
            if action == HC.CONTENT_UPDATE_MOVE:
                
                block_of_hashes = [ m.GetHash() for m in block_of_media ]
                
                content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, block_of_hashes, reason = 'Moved to {}'.format( dest_service_name ) ) ]
                
                HG.client_controller.WriteSynchronous( 'content_updates', { source_service_key : content_updates } )
                
            
            pauser.Pause()
            
        
        job_key.Delete()
        
    
    def publish_callable( result ):
        
        pass
        
    
    job = ClientGUIAsync.AsyncQtJob( win, work_callable, publish_callable )
    
    job.start()
    

def ShowFileEmbeddedMetadata( win: QW.QWidget, media: ClientMedia.MediaSingleton ):
    
    if not media.GetLocationsManager().IsLocal():
        
        QW.QMessageBox.warning( win, 'Warning', 'This file is not local to this computer!' )
        
        return
        
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    path = HG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    pil_image = HydrusImageHandling.RawOpenPILImage( path )
    
    exif_dict = None
    file_text = None
    
    if mime in HC.FILES_THAT_CAN_HAVE_EXIF:
        
        exif_dict = HydrusImageHandling.GetEXIFDict( pil_image )
        
    
    if mime in HC.FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA:
        
        file_text = HydrusImageHandling.GetEmbeddedFileText( pil_image )
        
    
    if exif_dict is None and file_text is None:
        
        QW.QMessageBox.information( win, 'Nothing found', 'Sorry, could not see any human-readable information in this file! Hydrus should have known this, so if this keeps happening, you may need to schedule a rescan of this info in file maintenance.' )
        
        return
        
    
    frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( win, 'Embedded Metadata' )
    
    panel = ClientGUIScrolledPanelsReview.ReviewFileEmbeddedMetadata( frame, exif_dict, file_text )
    
    frame.SetPanel( panel )
    

def UndeleteFiles( hashes ):
    
    local_file_service_keys = HG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
    
    for chunk_of_hashes in HydrusData.SplitIteratorIntoChunks( hashes, 64 ):
        
        media_results = HG.client_controller.Read( 'media_results', chunk_of_hashes )
        
        service_keys_to_hashes = collections.defaultdict( list )
        
        for media_result in media_results:
            
            locations_manager = media_result.GetLocationsManager()
            
            if CC.TRASH_SERVICE_KEY not in locations_manager.GetCurrent():
                
                continue
                
            
            hash = media_result.GetHash()
            
            for service_key in locations_manager.GetDeleted().intersection( local_file_service_keys ):
                
                service_keys_to_hashes[ service_key ].append( hash )
                
            
        
        for ( service_key, service_hashes ) in service_keys_to_hashes.items():
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, service_hashes )
            
            service_keys_to_content_updates = { service_key : [ content_update ] }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    

def UndeleteMedia( win, media ):
    
    media_deleted_service_keys = HydrusData.MassUnion( ( m.GetLocationsManager().GetDeleted() for m in media ) )
    
    local_file_services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) )
    
    undeletable_services = [ local_file_service for local_file_service in local_file_services if local_file_service.GetServiceKey() in media_deleted_service_keys ]
    
    if len( undeletable_services ) > 0:
        
        do_it = False
        
        if len( undeletable_services ) > 1:
            
            choice_tuples = []
            
            for ( i, service ) in enumerate( undeletable_services ):
                
                choice_tuples.append( ( service.GetName(), service, 'Undelete back to {}.'.format( service.GetName() ) ) )
                
            
            if len( choice_tuples ) > 1:
                
                service = HG.client_controller.services_manager.GetService( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                
                choice_tuples.append( ( 'all the above', service, 'Undelete back to all services the files have been deleted from.' ) )
                
            
            try:
                
                undelete_service = ClientGUIDialogsQuick.SelectFromListButtons( win, 'Undelete for?', choice_tuples )
                
                do_it = True
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
        else:
    
            ( undelete_service, ) = undeletable_services
            
            if HC.options[ 'confirm_trash' ]:
                
                result = ClientGUIDialogsQuick.GetYesNo( win, 'Undelete this file back to {}?'.format( undelete_service.GetName() ) )
                
                if result == QW.QDialog.Accepted:
                    
                    do_it = True
                    
                
            else:
                
                do_it = True
                
            
        
        if do_it:
            
            for chunk_of_media in HydrusData.SplitIteratorIntoChunks( media, 64 ):
                
                service_keys_to_content_updates = collections.defaultdict( list )
                
                service_key = undelete_service.GetServiceKey()
                
                undeletee_hashes = [ m.GetHash() for m in chunk_of_media if service_key in m.GetLocationsManager().GetDeleted() ]
                
                service_keys_to_content_updates[ service_key ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, undeletee_hashes ) ]
                
                HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
            
        
    
