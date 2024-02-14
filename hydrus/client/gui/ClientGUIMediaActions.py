import collections
import itertools
import typing

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageOpening

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientFiles
from hydrus.client import ClientPDFHandling
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIScrolledPanelsReview
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

def ApplyContentApplicationCommandToMedia( parent: QW.QWidget, command: CAC.ApplicationCommand, media: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    if not command.IsContentCommand():
        
        return
        
    
    service_key = command.GetContentServiceKey()
    action = command.GetContentAction()
    value = command.GetContentValue()
    
    try:
        
        service = CG.client_controller.services_manager.GetService( service_key )
        
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
        
        content_updates = []
        
        if service_type in HC.REAL_TAG_SERVICES:
            
            tag = value
            
            content_updates = GetContentUpdatesForAppliedContentApplicationCommandTags( parent, service_key, service_type, action, media, tag )
            
        elif service_type in HC.RATINGS_SERVICES:
            
            if action in ( HC.CONTENT_UPDATE_SET, HC.CONTENT_UPDATE_FLIP ):
                
                if action == HC.CONTENT_UPDATE_FLIP and service_type == HC.LOCAL_RATING_INCDEC:
                    
                    pass
                    
                else:
                    
                    rating = value
                    
                    content_updates = GetContentUpdatesForAppliedContentApplicationCommandRatingsSetFlip( service_key, action, media, rating )
                    
                
            elif action in ( HC.CONTENT_UPDATE_INCREMENT, HC.CONTENT_UPDATE_DECREMENT ):
                
                if service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    one_star_value = service.GetOneStarValue()
                    
                    content_updates = GetContentUpdatesForAppliedContentApplicationCommandRatingsNumericalIncDec( service_key, one_star_value, action, media )
                    
                elif service_type == HC.LOCAL_RATING_INCDEC:
                    
                    content_updates = GetContentUpdatesForAppliedContentApplicationCommandRatingsIncDec( service_key, action, media )
                    
                
            else:
                
                return True
                
            
        else:
            
            return False
            
        
        if len( content_updates ) > 0:
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( service_key, content_updates ) )
            
        
    
    return True
    

def ClearDeleteRecord( win, media ):
    
    clearable_media = [ m for m in media if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in m.GetLocationsManager().GetDeleted() ]
    
    if len( clearable_media ) == 0:
        
        return
        
    
    result = ClientGUIDialogsQuick.GetYesNo( win, 'Clear the deletion record for {} previously deleted files?.'.format( HydrusData.ToHumanInt( len( clearable_media ) ) ) )
    
    if result == QW.QDialog.Accepted:
        
        for chunk_of_media in HydrusData.SplitIteratorIntoChunks( clearable_media, 64 ):
            
            clearee_hashes = [ m.GetHash() for m in chunk_of_media ]
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, clearee_hashes )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
            
            CG.client_controller.Write( 'content_updates', content_update_package )
            
        
    

def EditFileNotes( win: QW.QWidget, media: ClientMedia.MediaSingleton, name_to_start_on = typing.Optional[ str ] ):
    
    names_to_notes = media.GetNotesManager().GetNamesToNotes()
    
    title = 'manage notes'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditFileNotesPanel( dlg, names_to_notes, name_to_start_on = name_to_start_on )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            hash = media.GetHash()
            
            ( names_to_notes, deletee_names ) = panel.GetValue()
            
            content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in names_to_notes.items() ]
            content_updates.extend( [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash, name ) ) for name in deletee_names ] )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, content_updates )
            
            CG.client_controller.Write( 'content_updates', content_update_package )
            
        
    

def EditFileTimestamps( win: QW.QWidget, ordered_medias: typing.List[ ClientMedia.MediaSingleton ] ):
    
    title = 'manage times'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditFileTimestampsPanel( dlg, ordered_medias )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            content_update_package = panel.GetContentUpdatePackage()
            
            if content_update_package.HasContent():
                
                CG.client_controller.Write( 'content_updates', content_update_package )
                
                result = panel.GetFileModifiedUpdateData()
                
                if result is not None:
                    
                    ( hashes_to_alter_modified_dates, file_modified_timestamp_ms, step_ms ) = result
                    
                    hashes_to_alter_modified_dates = set( hashes_to_alter_modified_dates )
                    
                    medias_to_alter_modified_dates = [ m for m in ordered_medias if m.GetHash() in hashes_to_alter_modified_dates ]
                    
                    def do_it():
                        
                        job_status = ClientThreading.JobStatus( cancellable = True )
                        
                        job_status.SetStatusTitle( 'setting file modified dates' )
                        
                        time_started = HydrusTime.GetNow()
                        showed_popup = False
                        
                        num_to_do = len( medias_to_alter_modified_dates )
                        
                        for ( i, m ) in enumerate( medias_to_alter_modified_dates ):
                            
                            job_status.SetStatusText( HydrusData.ConvertValueRangeToPrettyString( i, num_to_do ) )
                            job_status.SetVariable( 'popup_gauge_1', ( i, num_to_do ) )
                            
                            if not showed_popup and HydrusTime.TimeHasPassed( time_started + 3 ):
                                
                                CG.client_controller.pub( 'message', job_status )
                                
                                showed_popup = True
                                
                            
                            if job_status.IsCancelled():
                                
                                break
                                
                            
                            final_time_ms = file_modified_timestamp_ms + ( i * step_ms )
                            
                            CG.client_controller.client_files_manager.UpdateFileModifiedTimestampMS( m, final_time_ms )
                            
                        
                        job_status.FinishAndDismiss()
                        
                    
                    CG.client_controller.CallToThread( do_it )
                    
                
            
        
    

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
        
    
    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, row ) ]
    
    return content_updates
    

def GetContentUpdatesForAppliedContentApplicationCommandRatingsIncDec( service_key: bytes, action: int, media: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    if action == HC.CONTENT_UPDATE_INCREMENT:
        
        direction = 1
        
    elif action == HC.CONTENT_UPDATE_DECREMENT:
        
        direction = -1
        
    else:
        
        return []
        
    
    ratings_to_hashes = collections.defaultdict( set )
    
    for m in media:
        
        ratings_manager = m.GetRatingsManager()
        
        current_rating = ratings_manager.GetRating( service_key )
        
        new_rating = current_rating + direction
        
        ratings_to_hashes[ new_rating ].add( m.GetHash() )
        
    
    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) ) for ( rating, hashes ) in ratings_to_hashes.items() ]
    
    return content_updates
    

def GetContentUpdatesForAppliedContentApplicationCommandRatingsNumericalIncDec( service_key: bytes, one_star_value: float, action: int, media: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
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
            
        
    
    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating, hashes ) ) for ( rating, hashes ) in ratings_to_hashes.items() ]
    
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
            
        
    
    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_update_action, row, reason = reason ) for row in rows ]
    
    return content_updates
    
def GetLocalFileActionServiceKeys( media: typing.Collection[ ClientMedia.MediaSingleton ] ):
    
    local_media_file_service_keys = set( CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) ) )
    
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
    
    dest_service_name = CG.client_controller.services_manager.GetName( dest_service_key )
    
    applicable_media = [ m for m in media if m.GetLocationsManager().IsLocal() and dest_service_key not in m.GetLocationsManager().GetCurrent() and m.GetMime() not in HC.HYDRUS_UPDATE_FILES ]
    
    if len( applicable_media ) == 0:
        
        return
        
    
    ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys ) = GetLocalFileActionServiceKeys( media )
    
    do_yes_no = do_yes_no = CG.client_controller.new_options.GetBoolean( 'confirm_multiple_local_file_services_copy' )
    yes_no_text = 'Add {} files to {}?'.format( HydrusData.ToHumanInt( len( applicable_media ) ), dest_service_name )
    
    if action == HC.CONTENT_UPDATE_MOVE:
        
        do_yes_no = CG.client_controller.new_options.GetBoolean( 'confirm_multiple_local_file_services_move' )
        
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
                
                choice_tuples = []
                
                for potential_source_service_key in potential_source_service_keys:
                    
                    potential_source_service_name = CG.client_controller.services_manager.GetName( potential_source_service_key )
                    
                    text = 'move {} in "{}" to "{}"'.format( len( potential_source_service_keys_to_applicable_media[ potential_source_service_key ] ), potential_source_service_name, dest_service_name )
                    
                    description = 'Move from {} to {}.'.format( potential_source_service_name, dest_service_name )
                    
                    choice_tuples.append( ( text, potential_source_service_key, description ) )
                    
                
                choice_tuples.sort()
                
                try:
                    
                    source_service_key = ClientGUIDialogsQuick.SelectFromListButtons( win, 'select source service', choice_tuples, message = 'Select where we are moving from. Note this may not cover all files.' )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
        
        source_service_name = CG.client_controller.services_manager.GetName( source_service_key )
        
        applicable_media = potential_source_service_keys_to_applicable_media[ source_service_key ]
        
        yes_no_text = 'Move {} files from {} to {}?'.format( HydrusData.ToHumanInt( len( applicable_media ) ), source_service_name, dest_service_name )
        
    
    if len( applicable_media ) == 0:
        
        return
        
    
    if do_yes_no:
        
        result = ClientGUIDialogsQuick.GetYesNo( win, yes_no_text )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
    
    def work_callable():
        
        job_status = ClientThreading.JobStatus( cancellable = True )
        
        title = 'moving files' if action == HC.CONTENT_UPDATE_MOVE else 'adding files'
        
        job_status.SetStatusTitle( title )
        
        BLOCK_SIZE = 64
        
        pauser = HydrusThreading.BigJobPauser()
        
        num_to_do = len( applicable_media )
        
        if num_to_do > BLOCK_SIZE:
            
            CG.client_controller.pub( 'message', job_status )
            
        
        now_ms = HydrusTime.GetNowMS()
        
        for ( i, block_of_media ) in enumerate( HydrusLists.SplitListIntoChunks( applicable_media, BLOCK_SIZE ) ):
            
            if job_status.IsCancelled():
                
                break
                
            
            job_status.SetStatusText( HydrusData.ConvertValueRangeToPrettyString( i * BLOCK_SIZE, num_to_do ) )
            job_status.SetVariable( 'popup_gauge_1', ( i * BLOCK_SIZE, num_to_do ) )
            
            content_updates = []
            undelete_hashes = set()
            
            for m in block_of_media:
                
                if dest_service_key in m.GetLocationsManager().GetDeleted():
                    
                    undelete_hashes.add( m.GetHash() )
                    
                else:
                    
                    content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( m.GetMediaResult().GetFileInfoManager(), now_ms ) ) )
                    
                
            
            if len( undelete_hashes ) > 0:
                
                content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, undelete_hashes ) )
                
            
            CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( dest_service_key, content_updates ) )
            
            if action == HC.CONTENT_UPDATE_MOVE:
                
                block_of_hashes = [ m.GetHash() for m in block_of_media ]
                
                content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE_FROM_SOURCE_AFTER_MIGRATE, block_of_hashes, reason = 'Moved to {}'.format( dest_service_name ) ) ]
                
                CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( source_service_key, content_updates ) )
                
            
            pauser.Pause()
            
        
        job_status.FinishAndDismiss()
        
    
    def publish_callable( result ):
        
        pass
        
    
    job = ClientGUIAsync.AsyncQtJob( win, work_callable, publish_callable )
    
    job.start()
    

def SetFilesForcedFiletypes( win: QW.QWidget, medias: typing.Collection[ ClientMedia.Media ] ):
    
    # boot a panel, it shows the user what current mimes are, what forced mimes are, and they have the choice to set all to x
    # if it comes back yes, we save to db
    
    medias = ClientMedia.FlattenMedia( medias )
    
    file_info_managers = [ media.GetFileInfoManager() for media in medias ]
    
    original_mimes_count = collections.Counter( file_info_manager.GetOriginalMime() for file_info_manager in file_info_managers )
    forced_mimes_count = collections.Counter( file_info_manager.mime for file_info_manager in file_info_managers if file_info_manager.FiletypeIsForced() )
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, 'force filetypes' ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditFilesForcedFiletypePanel( dlg, original_mimes_count, forced_mimes_count )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            forced_mime = panel.GetValue()
            
            def work_callable():
                
                job_status = ClientThreading.JobStatus( cancellable = True )
                
                job_status.SetStatusTitle( 'forcing filetypes' )
                
                BLOCK_SIZE = 64
                
                pauser = HydrusThreading.BigJobPauser()
                
                num_to_do = len( medias )
                
                if num_to_do > BLOCK_SIZE:
                    
                    CG.client_controller.pub( 'message', job_status )
                    
                
                for ( i, block_of_media ) in enumerate( HydrusLists.SplitListIntoChunks( medias, BLOCK_SIZE ) ):
                    
                    if job_status.IsCancelled():
                        
                        break
                        
                    
                    job_status.SetStatusText( HydrusData.ConvertValueRangeToPrettyString( i * BLOCK_SIZE, num_to_do ) )
                    job_status.SetVariable( 'popup_gauge_1', ( i * BLOCK_SIZE, num_to_do ) )
                    
                    hashes = { media.GetHash() for media in block_of_media }
                    
                    CG.client_controller.WriteSynchronous( 'force_filetype', hashes, forced_mime )
                    
                    hashes_we_needed_to_dupe = set()
                    
                    for media in block_of_media:
                        
                        hash = media.GetHash()
                        
                        current_mime = media.GetMime()
                        mime_to_move_to = forced_mime
                        
                        if mime_to_move_to is None:
                            
                            mime_to_move_to = media.GetFileInfoManager().GetOriginalMime()
                            
                        
                        needed_to_dupe_the_file = CG.client_controller.client_files_manager.ChangeFileExt( hash, current_mime, mime_to_move_to )
                        
                        if needed_to_dupe_the_file:
                            
                            hashes_we_needed_to_dupe.add( hash )
                            
                        
                    
                    if len( hashes_we_needed_to_dupe ) > 0:
                        
                        CG.client_controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', hashes_we_needed_to_dupe, ClientFiles.REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES, HydrusTime.GetNow() + 3600 )
                        
                    
                    pauser.Pause()
                    
                
                job_status.FinishAndDismiss()
                
            
            def publish_callable( result ):
                
                pass
                
            
            job = ClientGUIAsync.AsyncQtJob( win, work_callable, publish_callable )
            
            job.start()
            
        
    

def ShowFileEmbeddedMetadata( win: QW.QWidget, media: ClientMedia.MediaSingleton ):
    
    if not media.GetLocationsManager().IsLocal():
        
        ClientGUIDialogsMessage.ShowWarning( win, 'The file is not local to this computer!' )
        
        return
        
    
    exif_dict = None
    file_text = None
    
    extra_rows = []
    
    hash = media.GetHash()
    mime = media.GetMime()
    
    path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
    
    if mime == HC.APPLICATION_PDF:
        
        try:
            
            file_text = ClientPDFHandling.GetHumanReadableEmbeddedMetadata( path )
            
        except HydrusExceptions.LimitedSupportFileException:
            
            file_text = 'Could not read PDF metadata!'
            
        
    else:
        
        raw_pil_image = HydrusImageOpening.RawOpenPILImage( path )
        
        if mime in HC.FILES_THAT_CAN_HAVE_EXIF:
            
            exif_dict = HydrusImageMetadata.GetEXIFDict( raw_pil_image )
            
        
        if mime in HC.FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA:
            
            file_text = HydrusImageMetadata.GetEmbeddedFileText( raw_pil_image )
            
        
        if mime == HC.IMAGE_JPEG:
            
            extra_rows.append( ( 'progressive', 'yes' if 'progression' in raw_pil_image.info else 'no' ) )
            
            extra_rows.append( ( 'subsampling', HydrusImageMetadata.GetJpegSubsampling( raw_pil_image )) )
            
        
    
    if exif_dict is None and file_text is None:
        
        ClientGUIDialogsMessage.ShowWarning( win, 'Sorry, could not see any human-readable information in this file! Hydrus should have known this, so if this keeps happening, you may need to schedule a rescan of this info in file maintenance.' )
        
        return
        
    
    frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( win, 'Embedded Metadata' )
    
    panel = ClientGUIScrolledPanelsReview.ReviewFileEmbeddedMetadata( frame, exif_dict, file_text, extra_rows )
    
    frame.SetPanel( panel )
    

def UndeleteFiles( hashes ):
    
    local_file_service_keys = CG.client_controller.services_manager.GetServiceKeys( ( HC.LOCAL_FILE_DOMAIN, ) )
    
    for chunk_of_hashes in HydrusData.SplitIteratorIntoChunks( hashes, 64 ):
        
        media_results = CG.client_controller.Read( 'media_results', chunk_of_hashes )
        
        service_keys_to_hashes = collections.defaultdict( list )
        
        for media_result in media_results:
            
            locations_manager = media_result.GetLocationsManager()
            
            if CC.TRASH_SERVICE_KEY not in locations_manager.GetCurrent():
                
                continue
                
            
            hash = media_result.GetHash()
            
            for service_key in locations_manager.GetDeleted().intersection( local_file_service_keys ):
                
                service_keys_to_hashes[ service_key ].append( hash )
                
            
        
        for ( service_key, service_hashes ) in service_keys_to_hashes.items():
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, service_hashes )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( service_key, content_update )
            
            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
            
        
    

def UndeleteMedia( win, media ):
    
    undeletable_media = [ m for m in media if m.GetLocationsManager().IsLocal() ]
    
    if len( undeletable_media ) == 0:
        
        return
        
    
    media_deleted_service_keys = HydrusData.MassUnion( ( m.GetLocationsManager().GetDeleted() for m in undeletable_media ) )
    
    local_file_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) )
    
    undeletable_services = [ local_file_service for local_file_service in local_file_services if local_file_service.GetServiceKey() in media_deleted_service_keys ]
    
    if len( undeletable_services ) > 0:
        
        do_it = False
        
        if len( undeletable_services ) > 1:
            
            choice_tuples = []
            
            for ( i, service ) in enumerate( undeletable_services ):
                
                choice_tuples.append( ( service.GetName(), service, 'Undelete back to {}.'.format( service.GetName() ) ) )
                
            
            if len( choice_tuples ) > 1:
                
                service = CG.client_controller.services_manager.GetService( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                
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
            
            for chunk_of_media in HydrusData.SplitIteratorIntoChunks( undeletable_media, 64 ):
                
                service_key = undelete_service.GetServiceKey()
                
                undeletee_hashes = [ m.GetHash() for m in chunk_of_media if service_key in m.GetLocationsManager().GetDeleted() ]
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, undeletee_hashes )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( service_key, content_update )
                
                CG.client_controller.Write( 'content_updates', content_update_package )
                
            
        
    
