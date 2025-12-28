import collections
import collections.abc
import time

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime
from hydrus.core.files.images import HydrusImageMetadata
from hydrus.core.files.images import HydrusImageOpening
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client import ClientPDFHandling
from hydrus.client import ClientThreading
from hydrus.client.files import ClientFilesMaintenance
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui.duplicates import ClientGUIDuplicatesContentMergeOptions
from hydrus.client.gui.exporting import ClientGUIExport
from hydrus.client.gui.media import ClientGUIMediaSimpleActions
from hydrus.client.gui.metadata import ClientGUIEditTimestamps
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.panels import ClientGUIScrolledPanelsEdit
from hydrus.client.gui.panels import ClientGUIScrolledPanelsReview
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaResultPrettyInfo
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientFileMigration
from hydrus.client.metadata import ClientTags

def ApplyContentApplicationCommandToMedia( win: QW.QWidget, command: CAC.ApplicationCommand, media: collections.abc.Collection[ ClientMedia.MediaSingleton ] ):
    
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
            
        
        MoveOrDuplicateLocalFiles( win, service_key, action, media, source_service_key = source_service_key )
        
    else:
        
        content_updates = []
        
        if service_type in HC.REAL_TAG_SERVICES:
            
            tag = value
            
            content_updates = GetContentUpdatesForAppliedContentApplicationCommandTags( win, service_key, service_type, action, media, tag, BLOCK_SIZE = 64 )
            
        elif service_type in HC.RATINGS_SERVICES:
            
            if action in ( HC.CONTENT_UPDATE_SET, HC.CONTENT_UPDATE_FLIP ):
                
                if action == HC.CONTENT_UPDATE_FLIP and service_type == HC.LOCAL_RATING_INCDEC:
                    
                    pass
                    
                else:
                    
                    rating = value
                    
                    content_updates = GetContentUpdatesForAppliedContentApplicationCommandRatingsSetFlip( service_key, action, media, rating, BLOCK_SIZE = 256 )
                    
                
            elif action in ( HC.CONTENT_UPDATE_INCREMENT, HC.CONTENT_UPDATE_DECREMENT ):
                
                if service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    one_star_value = service.GetOneStarValue()
                    
                    content_updates = GetContentUpdatesForAppliedContentApplicationCommandRatingsNumericalIncDec( service_key, one_star_value, action, media, BLOCK_SIZE = 256 )
                    
                elif service_type == HC.LOCAL_RATING_INCDEC:
                    
                    content_updates = GetContentUpdatesForAppliedContentApplicationCommandRatingsIncDec( service_key, action, media, BLOCK_SIZE = 256 )
                    
                
            else:
                
                return True
                
            
        else:
            
            return False
            
        
        def do_it():
            
            job_status = ClientThreading.JobStatus()
            
            job_status.SetStatusTitle( f'setting {command.ToString()}' )
            
            start_time = HydrusTime.GetNowFloat()
            have_pubbed_message = False
            
            num_to_do = len( content_updates )
            
            for ( i, content_update ) in enumerate( content_updates ):
                
                if not have_pubbed_message and HydrusTime.TimeHasPassedFloat( start_time + 3 ):
                    
                    CG.client_controller.pub( 'message', job_status )
                    
                    have_pubbed_message = True
                    
                
                job_status.SetGauge( i, num_to_do )
                
                CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( service_key, content_update ) )
                
            
            job_status.FinishAndDismiss()
            
        
        CG.client_controller.CallToThread( do_it )
        
    
    return True
    

def ClearDeleteRecord( win, media ):
    
    clearable_media = [ m for m in media if CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in m.GetLocationsManager().GetDeleted() ]
    
    if len( clearable_media ) == 0:
        
        return
        
    
    result = ClientGUIDialogsQuick.GetYesNo( win, 'Clear the deletion record for {} previously deleted files?.'.format( HydrusNumbers.ToHumanInt( len( clearable_media ) ) ) )
    
    if result == QW.QDialog.DialogCode.Accepted:
        
        for chunk_of_media in HydrusLists.SplitIteratorIntoChunks( clearable_media, 64 ):
            
            clearee_hashes = [ m.GetHash() for m in chunk_of_media ]
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, clearee_hashes )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
            
            CG.client_controller.Write( 'content_updates', content_update_package )
            
        
    


def CopyHashesToClipboard( win: QW.QWidget, hash_type: str, medias: collections.abc.Sequence[ ClientMedia.Media ] ):
    
    if len( medias ) == 0:
        
        return
        
    
    hex_it = True
    
    desired_hashes = []
    
    flat_media = ClientMedia.FlattenMedia( medias )
    
    sha256_hashes = [ media.GetHash() for media in flat_media ]
    
    if hash_type in ( 'pixel_hash', 'blurhash' ):
        
        file_info_managers = [ media.GetFileInfoManager() for media in flat_media ]
        
        if hash_type == 'pixel_hash':
            
            desired_hashes = [ fim.pixel_hash for fim in file_info_managers if fim.pixel_hash is not None ]
            
        elif hash_type == 'blurhash':
            
            desired_hashes = [ fim.blurhash for fim in file_info_managers if fim.blurhash is not None ]
            
            hex_it = False
            
        
    elif hash_type == 'sha256':
        
        desired_hashes = sha256_hashes
        
    else:
        
        num_hashes = len( sha256_hashes )
        num_remote_medias = len( [ not media.GetLocationsManager().IsLocal() for media in flat_media ] )
        
        source_to_desired = CG.client_controller.Read( 'file_hashes', sha256_hashes, 'sha256', hash_type )
        
        desired_hashes = [ source_to_desired[ source_hash ] for source_hash in sha256_hashes if source_hash in source_to_desired ]
        
        num_missing = num_hashes - len( desired_hashes )
        
        if num_missing > 0:
            
            if num_missing == num_hashes:
                
                message = 'Unfortunately, none of the {} hashes could be found.'.format( hash_type )
                
            else:
                
                message = 'Unfortunately, {} of the {} hashes could not be found.'.format( HydrusNumbers.ToHumanInt( num_missing ), hash_type )
                
            
            if num_remote_medias > 0:
                
                message += ' {} of the files you wanted are not currently in this client. If they have never visited this client, the lookup is impossible.'.format( HydrusNumbers.ToHumanInt( num_remote_medias ) )
                
            
            if num_remote_medias < num_hashes:
                
                message += ' It could be that some of the local files are currently missing this information in the hydrus database. A file maintenance job (under the database menu) can repopulate this data.'
                
            
            ClientGUIDialogsMessage.ShowWarning( win, message )
            
        
    
    if len( desired_hashes ) > 0:
        
        if hex_it:
            
            text_lines = [ desired_hash.hex() for desired_hash in desired_hashes ]
            
        else:
            
            text_lines = desired_hashes
            
        
        if CG.client_controller.new_options.GetBoolean( 'prefix_hash_when_copying' ):
            
            text_lines = [ '{}:{}'.format( hash_type, hex_hash ) for hex_hash in text_lines ]
            
        
        hex_hashes_text = '\n'.join( text_lines )
        
        CG.client_controller.pub( 'clipboard', 'text', hex_hashes_text )
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusText( '{} {} hashes copied'.format( HydrusNumbers.ToHumanInt( len( desired_hashes ) ), hash_type ) )
        
        CG.client_controller.pub( 'message', job_status )
        
        job_status.FinishAndDismiss( 2 )
        
    

def DoClearFileViewingStats( win: QW.QWidget, flat_medias: collections.abc.Collection[ ClientMedia.MediaSingleton ] ):
    
    if len( flat_medias ) == 0:
        
        return
        
    
    if len( flat_medias ) == 1:
        
        insert = 'this file'
        
    else:
        
        insert = 'these {} files'.format( HydrusNumbers.ToHumanInt( len( flat_medias ) ) )
        
    
    message = 'Clear the file viewing count/duration and \'last viewed time\' for {}?'.format( insert )
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result == QW.QDialog.DialogCode.Accepted:
        
        hashes = { m.GetHash() for m in flat_medias }
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_DELETE, hashes )
        
        CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update ) )
        
    

def DoOpenKnownURLFromShortcut( win, media ):
    
    urls = media.GetLocationsManager().GetURLs()
    
    matched_labels_and_urls = []
    unmatched_urls = []
    
    if len( urls ) > 0:
        
        for url in urls:
            
            try:
                
                url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( url )
                
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
    

# this isn't really a 'media' guy, and it edits the options in place, so maybe move/edit/whatever!
def EditDuplicateContentMergeOptions( win: QW.QWidget, duplicate_type: int ):
    
    new_options = CG.client_controller.new_options
    
    duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, 'edit duplicate merge options' ) as dlg:
        
        panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
        
        ctrl = ClientGUIDuplicatesContentMergeOptions.EditDuplicateContentMergeOptionsWidget( panel, duplicate_type, duplicate_content_merge_options )
        
        panel.SetControl( ctrl )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            duplicate_content_merge_options = ctrl.GetValue()
            
            new_options.SetDuplicateContentMergeOptions( duplicate_type, duplicate_content_merge_options )
            
        
    


def EditFileNotes( win: QW.QWidget, media: ClientMedia.MediaSingleton, name_to_start_on = str | None ):
    
    names_to_notes = media.GetNotesManager().GetNamesToNotes()
    
    title = 'manage notes'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title, frame_key = 'manage_notes_dialog' ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditFileNotesPanel( dlg, names_to_notes, name_to_start_on = name_to_start_on )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            hash = media.GetHash()
            
            ( names_to_notes, deletee_names ) = panel.GetValue()
            
            content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in names_to_notes.items() ]
            content_updates.extend( [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash, name ) ) for name in deletee_names ] )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, content_updates )
            
            CG.client_controller.Write( 'content_updates', content_update_package )
            
        
    

def EditFileTimestamps( win: QW.QWidget, ordered_medias: list[ ClientMedia.MediaSingleton ] ):
    
    title = 'manage times'
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, title, frame_key = 'manage_times_dialog' ) as dlg:
        
        panel = ClientGUIEditTimestamps.EditFileTimestampsPanel( dlg, ordered_medias )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
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
                            
                            job_status.SetStatusText( HydrusNumbers.ValueRangeToPrettyString( i, num_to_do ) )
                            job_status.SetGauge( i, num_to_do )
                            
                            if not showed_popup and HydrusTime.TimeHasPassed( time_started + 3 ):
                                
                                CG.client_controller.pub( 'message', job_status )
                                
                                showed_popup = True
                                
                            
                            if job_status.IsCancelled():
                                
                                break
                                
                            
                            final_time_ms = file_modified_timestamp_ms + ( i * step_ms )
                            
                            CG.client_controller.client_files_manager.UpdateFileModifiedTimestampMS( m, final_time_ms )
                            
                        
                        job_status.FinishAndDismiss()
                        
                    
                    CG.client_controller.CallToThread( do_it )
                    
                
            
        
    

def ExportFiles( win: QW.QWidget, medias: collections.abc.Collection[ ClientMedia.Media ], do_export_and_then_quit = False ):
    
    flat_media = ClientMedia.FlattenMedia( medias )
    
    flat_media = [ m for m in flat_media if m.GetLocationsManager().IsLocal() ]
    
    if len( flat_media ) > 0:
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( win, 'export files', frame_key = 'export_files_frame' )
        
        panel = ClientGUIExport.ReviewExportFilesPanel( frame, flat_media, do_export_and_then_quit = do_export_and_then_quit )
        
        frame.SetPanel( panel )
        
    

def GetContentUpdatesForAppliedContentApplicationCommandRatingsSetFlip( service_key: bytes, action: int, media: collections.abc.Collection[ ClientMedia.MediaSingleton ], rating: float | None, BLOCK_SIZE = None ):
    
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
        
        thing_to_set = rating
        
    elif can_unset:
        
        thing_to_set = None
        
    else:
        
        return []
        
    
    if BLOCK_SIZE is None:
        
        rows = [ ( thing_to_set, hashes ) ]
        
    else:
        
        rows = [ ( thing_to_set, block_of_hashes ) for block_of_hashes in HydrusLists.SplitListIntoChunks( list( hashes ), BLOCK_SIZE ) ]
        
    
    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, row ) for row in rows ]
    
    return content_updates
    

def GetContentUpdatesForAppliedContentApplicationCommandRatingsIncDec( service_key: bytes, action: int, media: collections.abc.Collection[ ClientMedia.MediaSingleton ], BLOCK_SIZE = None ):
    
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
        
    
    all_content_updates = []
    
    for ( rating, hashes ) in ratings_to_hashes.items():
        
        if BLOCK_SIZE is None:
            
            rows = [ ( rating, hashes ) ]
            
        else:
            
            rows = [ ( rating, block_of_hashes ) for block_of_hashes in HydrusLists.SplitListIntoChunks( list( hashes ), BLOCK_SIZE ) ]
            
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, row ) for row in rows ]
        
        all_content_updates.extend( content_updates )
        
    
    return all_content_updates
    

def GetContentUpdatesForAppliedContentApplicationCommandRatingsNumericalIncDec( service_key: bytes, one_star_value: float, action: int, media: collections.abc.Collection[ ClientMedia.MediaSingleton ], BLOCK_SIZE = None ):
    
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
            
        
    
    all_content_updates = []
    
    for ( rating, hashes ) in ratings_to_hashes.items():
        
        if BLOCK_SIZE is None:
            
            rows = [ ( rating, hashes ) ]
            
        else:
            
            rows = [ ( rating, block_of_hashes ) for block_of_hashes in HydrusLists.SplitListIntoChunks( list( hashes ), BLOCK_SIZE ) ]
            
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, row ) for row in rows ]
        
        all_content_updates.extend( content_updates )
        
    
    return all_content_updates
    

def GetContentUpdatesForAppliedContentApplicationCommandTags( win: QW.QWidget, service_key: bytes, service_type: int, action: int, media: collections.abc.Collection[ ClientMedia.MediaSingleton ], tag: str, BLOCK_SIZE = None ):
    
    hashes = set()
    
    for m in media:
        
        hashes.add( m.GetHash() )
        
    
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
            
            try:
                
                reason = ClientGUIDialogsQuick.EnterText( win, message )
                
            except HydrusExceptions.CancelledException:
                
                return []
                
            
            content_update_action = HC.CONTENT_UPDATE_PETITION
            
        else:
            
            return []
            
        
    
    if BLOCK_SIZE is None:
        
        rows = [ ( tag, hashes ) ]
        
    else:
        
        rows = [ ( tag, block_of_hashes ) for block_of_hashes in HydrusLists.SplitListIntoChunks( list( hashes ), BLOCK_SIZE ) ]
        
    
    content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, content_update_action, row, reason = reason ) for row in rows ]
    
    return content_updates
    

def MoveOrDuplicateLocalFiles( win: QW.QWidget, dest_service_key: bytes, action: int, media: collections.abc.Collection[ ClientMedia.MediaSingleton ], source_service_key: bytes | None = None ):
    
    dest_service_name = CG.client_controller.services_manager.GetName( dest_service_key )
    
    applicable_media = [ m for m in media if CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY in m.GetLocationsManager().GetCurrent() and m.GetMime() not in HC.HYDRUS_UPDATE_FILES ]
    
    if action == HC.CONTENT_UPDATE_MOVE:
        
        already_in_place = lambda m: dest_service_key in m.GetLocationsManager().GetCurrent()
        
        applicable_media = [ m for m in media if not already_in_place( m ) ]
        
    elif action == HC.CONTENT_UPDATE_ADD:
        
        already_in_place = lambda m: dest_service_key in m.GetLocationsManager().GetCurrent()
        
        applicable_media = [ m for m in media if not already_in_place( m ) ]
        
    
    if len( applicable_media ) == 0:
        
        return
        
    
    ( local_duplicable_to_file_service_keys, local_moveable_from_and_to_file_service_keys, local_mergable_from_and_to_file_service_keys ) = ClientGUIMediaSimpleActions.GetLocalFileActionServiceKeys( applicable_media )
    
    do_yes_no = CG.client_controller.new_options.GetBoolean( 'confirm_multiple_local_file_services_copy' )
    yes_no_text = 'Add {} files to {}?'.format( HydrusNumbers.ToHumanInt( len( applicable_media ) ), dest_service_name )
    
    if action in ( HC.CONTENT_UPDATE_MOVE, HC.CONTENT_UPDATE_MOVE_MERGE ):
        
        do_yes_no = CG.client_controller.new_options.GetBoolean( 'confirm_multiple_local_file_services_move' )
        
        if action == HC.CONTENT_UPDATE_MOVE:
            
            local_moveable_from_and_to_file_service_keys = { pair for pair in local_moveable_from_and_to_file_service_keys if pair[1] == dest_service_key }
            
        elif action == HC.CONTENT_UPDATE_MOVE_MERGE:
            
            local_moveable_from_and_to_file_service_keys = { pair for pair in local_mergable_from_and_to_file_service_keys if pair[1] == dest_service_key }
            
        else:
            
            raise NotImplementedError( 'Unknown action!' )
            
        
        potential_move_source_service_keys = { pair[0] for pair in local_moveable_from_and_to_file_service_keys }
        
        potential_move_source_service_keys_to_applicable_media = collections.defaultdict( list )
        
        for m in applicable_media:
            
            current = m.GetLocationsManager().GetCurrent()
            
            for potential_source_service_key in potential_move_source_service_keys:
                
                if potential_source_service_key in current:
                    
                    potential_move_source_service_keys_to_applicable_media[ potential_source_service_key ].append( m )
                    
                
            
        
        if source_service_key is None:
            
            if len( potential_move_source_service_keys ) == 0:
                
                return
                
            elif len( potential_move_source_service_keys ) == 1:
                
                ( source_service_key, ) = potential_move_source_service_keys
                
            else:
                
                do_yes_no = False
                
                choice_tuples = []
                
                for potential_source_service_key in potential_move_source_service_keys:
                    
                    potential_source_service_name = CG.client_controller.services_manager.GetName( potential_source_service_key )
                    
                    if action == HC.CONTENT_UPDATE_MOVE:
                        
                        text = 'move {} in "{}" to "{}"'.format( len( potential_move_source_service_keys_to_applicable_media[ potential_source_service_key ] ), potential_source_service_name, dest_service_name )
                        
                        description = 'Move from {} to {}.'.format( potential_source_service_name, dest_service_name )
                        
                    elif action == HC.CONTENT_UPDATE_MOVE_MERGE:
                        
                        text = 'move-merge {} in "{}" to "{}"'.format( len( potential_move_source_service_keys_to_applicable_media[ potential_source_service_key ] ), potential_source_service_name, dest_service_name )
                        
                        description = 'Move-merge from {} to {}.'.format( potential_source_service_name, dest_service_name )
                        
                    else:
                        
                        raise NotImplementedError( 'Unknown action!' )
                        
                    
                    choice_tuples.append( ( text, potential_source_service_key, description ) )
                    
                
                choice_tuples.sort()
                
                try:
                    
                    source_service_key = ClientGUIDialogsQuick.SelectFromListButtons( win, 'select source service', choice_tuples, message = 'Select where we are moving from.' )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
        
        source_service_name = CG.client_controller.services_manager.GetName( source_service_key )
        
        # source service name is done, now let's see if we have a merge/move difference
        
        # ok now we are sorted, let's go
        
        applicable_media = potential_move_source_service_keys_to_applicable_media[ source_service_key ]
        
        if action == HC.CONTENT_UPDATE_MOVE:
            
            yes_no_text = 'Move {} files from {} to {}?'.format( HydrusNumbers.ToHumanInt( len( applicable_media ) ), source_service_name, dest_service_name )
            
        elif action == HC.CONTENT_UPDATE_MOVE_MERGE:
            
            yes_no_text = 'Move-merge {} files from {} to {}?'.format( HydrusNumbers.ToHumanInt( len( applicable_media ) ), source_service_name, dest_service_name )
            
        else:
            
            raise NotImplementedError( 'Unknown action!' )
            
        
    
    if len( applicable_media ) == 0:
        
        return
        
    
    if do_yes_no:
        
        result = ClientGUIDialogsQuick.GetYesNo( win, yes_no_text )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
    
    applicable_media_results = [ m.GetMediaResult() for m in applicable_media ]
    
    CG.client_controller.CallToThread( ClientFileMigration.DoMoveOrDuplicateLocalFiles, dest_service_key, action, applicable_media_results, source_service_key )
    

def OpenURLs( win: QW.QWidget, urls ):
    
    urls = sorted( urls )
    
    if len( urls ) > 1:
        
        message = 'Open the {} URLs in your web browser?'.format( len( urls ) )
        
        if len( urls ) > 10:
            
            message += ' This will take some time.'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( win, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
    
    def do_it( urls ):
        
        job_status = None
        
        num_urls = len( urls )
        
        if num_urls > 5:
            
            job_status = ClientThreading.JobStatus( pausable = True, cancellable = True )
            
            job_status.SetStatusTitle( 'Opening URLs' )
            
            CG.client_controller.pub( 'message', job_status )
            
        
        try:
            
            for ( i, url ) in enumerate( urls ):
                
                if job_status is not None:
                    
                    ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                    
                    if should_quit:
                        
                        return
                        
                    
                    job_status.SetStatusText( HydrusNumbers.ValueRangeToPrettyString( i, num_urls ) )
                    job_status.SetGauge( i, num_urls )
                    
                
                ClientPaths.LaunchURLInWebBrowser( url )
                
                time.sleep( 1 )
                
            
        finally:
            
            if job_status is not None:
                
                job_status.FinishAndDismiss( 1 )
                
            
        
    
    CG.client_controller.CallToThread( do_it, urls )
    

def OpenMediaURLs( win: QW.QWidget, medias ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        urls.update( media_urls )
        
    
    OpenURLs( win, urls )
    

def OpenMediaURLClassURLs( win: QW.QWidget, medias, url_class ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        for url in media_urls:
            
            # can't do 'url_class.matches', as it will match too many
            if CG.client_controller.network_engine.domain_manager.GetURLClass( url ) == url_class:
                
                urls.add( url )
                
            
        
    
    OpenURLs( win, urls )
    

def RedownloadURLClassURLsForceRefetch( win: QW.QWidget, medias, url_class ):
    
    urls = set()
    
    for media in medias:
        
        media_urls = media.GetLocationsManager().GetURLs()
        
        for url in media_urls:
            
            # can't do 'url_class.matches', as it will match too many
            if CG.client_controller.network_engine.domain_manager.GetURLClass( url ) == url_class:
                
                urls.add( url )
                
            
        
    
    if len( urls ) == 0:
        
        return
        
    
    message = f'Open a new search page and force metadata redownload for {len( urls )} "{url_class.GetName()}" URLs? This is inefficient and should only be done to fill in known gaps in one-time jobs.'
    message += '\n' * 2
    message += 'DO NOT USE THIS TO RECHECK TEN THOUSAND URLS EVERY MONTH JUST FOR MAYBE A FEW NEW TAGS.'
    
    result = ClientGUIDialogsQuick.GetYesNo( win, message )
    
    if result != QW.QDialog.DialogCode.Accepted:
        
        return
        
    
    CG.client_controller.gui.RedownloadURLsForceFetch( urls )
    

def SetFilesForcedFiletypes( win: QW.QWidget, medias: collections.abc.Collection[ ClientMedia.Media ] ):
    
    # boot a panel, it shows the user what current mimes are, what forced mimes are, and they have the choice to set all to x
    # if it comes back yes, we save to db
    
    medias = ClientMedia.FlattenMedia( medias )
    
    file_info_managers = [ media.GetFileInfoManager() for media in medias ]
    
    original_mimes_count = collections.Counter( file_info_manager.GetOriginalMime() for file_info_manager in file_info_managers )
    forced_mimes_count = collections.Counter( file_info_manager.mime for file_info_manager in file_info_managers if file_info_manager.FiletypeIsForced() )
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, 'force filetypes' ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditFilesForcedFiletypePanel( dlg, original_mimes_count, forced_mimes_count )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.DialogCode.Accepted:
            
            forced_mime = panel.GetValue()
            
            def work_callable():
                
                job_status = ClientThreading.JobStatus( cancellable = True )
                
                job_status.SetStatusTitle( 'forcing filetypes' )
                
                BLOCK_SIZE = 64
                
                pauser = HydrusThreading.BigJobPauser()
                
                if len( medias ) > BLOCK_SIZE:
                    
                    CG.client_controller.pub( 'message', job_status )
                    
                
                for ( num_done, num_to_do, block_of_media ) in HydrusLists.SplitListIntoChunksRich( medias, BLOCK_SIZE ):
                    
                    if job_status.IsCancelled():
                        
                        break
                        
                    
                    job_status.SetStatusText( HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do ) )
                    job_status.SetGauge( num_done, num_to_do )
                    
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
                        
                        CG.client_controller.WriteSynchronous( 'file_maintenance_add_jobs_hashes', hashes_we_needed_to_dupe, ClientFilesMaintenance.REGENERATE_FILE_DATA_JOB_DELETE_NEIGHBOUR_DUPES, HydrusTime.GetNow() + 3600 )
                        
                    
                    pauser.Pause()
                    
                
                job_status.FinishAndDismiss()
                
            
            def publish_callable( result ):
                
                pass
                
            
            job = ClientGUIAsync.AsyncQtJob( win, work_callable, publish_callable )
            
            job.start()
            
        
    

def ShowFileEmbeddedMetadata( win: QW.QWidget, media: ClientMedia.MediaSingleton ):
    
    info_lines = ClientMediaResultPrettyInfo.GetPrettyMediaResultInfoLines( media.GetMediaResult() )
    
    mime = media.GetMime()
    top_line_text = ClientMediaResultPrettyInfo.ConvertInfoLinesToTextBlock( info_lines )
    exif_dict = None
    file_text = None
    extra_rows = []
    
    if media.GetLocationsManager().IsLocal():
        
        hash = media.GetHash()
        
        if mime == HC.APPLICATION_PDF:
            
            path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
            
            try:
                
                file_text = ClientPDFHandling.GetHumanReadableEmbeddedMetadata( path )
                
            except HydrusExceptions.LimitedSupportFileException:
                
                file_text = 'Could not read PDF metadata!'
                
            
        elif mime in HC.FILES_THAT_CAN_HAVE_EXIF or mime in HC.FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA:
            
            path = CG.client_controller.client_files_manager.GetFilePath( hash, mime )
            
            raw_pil_image = HydrusImageOpening.RawOpenPILImage( path )
            
            if mime in HC.FILES_THAT_CAN_HAVE_EXIF:
                
                exif_dict = HydrusImageMetadata.GetEXIFDict( raw_pil_image )
                
            
            if mime in HC.FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA:
                
                file_text = HydrusImageMetadata.GetEmbeddedFileText( raw_pil_image )
                
            
            if mime == HC.IMAGE_JPEG:
                
                extra_rows.append( ( 'progressive', 'yes' if 'progression' in raw_pil_image.info else 'no' ) )
                
                extra_rows.append( ( 'subsampling', HydrusImageMetadata.subsampling_str_lookup[ HydrusImageMetadata.GetJpegSubsamplingRaw( raw_pil_image ) ] ) )
                
            
        
    else:
        
        file_text = 'This file is not local to this computer!'
        
    
    frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( win, 'Detailed File Metadata' )
    
    panel = ClientGUIScrolledPanelsReview.ReviewFileEmbeddedMetadata( frame, mime, top_line_text, exif_dict, file_text, extra_rows )
    
    frame.SetPanel( panel )
    

def UndeleteMedia( win, media ):
    
    undeletable_media = [ m for m in media if m.GetLocationsManager().IsLocal() ]
    
    if len( undeletable_media ) == 0:
        
        return
        
    
    media_deleted_service_keys = HydrusLists.MassUnion( ( m.GetLocationsManager().GetDeleted() for m in undeletable_media ) )
    
    local_file_services = CG.client_controller.services_manager.GetServices( ( HC.LOCAL_FILE_DOMAIN, ) )
    
    undeletable_services = [ local_file_service for local_file_service in local_file_services if local_file_service.GetServiceKey() in media_deleted_service_keys ]
    
    if len( undeletable_services ) > 0:
        
        do_it = False
        
        if len( undeletable_services ) > 1:
            
            choice_tuples = []
            
            for ( i, service ) in enumerate( undeletable_services ):
                
                choice_tuples.append( ( service.GetName(), service, 'Undelete back to {}.'.format( service.GetName() ) ) )
                
            
            if len( choice_tuples ) > 1:
                
                service = CG.client_controller.services_manager.GetService( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
                
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
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    do_it = True
                    
                
            else:
                
                do_it = True
                
            
        
        if do_it:
            
            for chunk_of_media in HydrusLists.SplitIteratorIntoChunks( undeletable_media, 64 ):
                
                service_key = undelete_service.GetServiceKey()
                
                undeletee_hashes = [ m.GetHash() for m in chunk_of_media if service_key in m.GetLocationsManager().GetDeleted() ]
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, undeletee_hashes )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( service_key, content_update )
                
                CG.client_controller.Write( 'content_updates', content_update_package )
                
            
        
    
