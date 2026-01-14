import collections.abc

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client.media import ClientMediaResult
from hydrus.client.media import ClientMediaResultPrettyInfoObjects

def ConvertInfoLinesToTextBlock( info_lines: collections.abc.Collection[ ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine ] ) -> str:
    
    def convert_to_block_lines( lines, indent = '' ) -> list[ str ]:
        
        my_lines = []
        
        for line in lines:
            
            if isinstance( line, ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLinesSubmenu ):
                
                my_lines.append( indent + line.text + ':' )
                
                my_lines.extend( convert_to_block_lines( line.sublines, indent = indent + '  ' ) )
                
            else:
                
                my_lines.append( indent + line.text )
                
            
        
        return my_lines
        
    
    block_lines = convert_to_block_lines( info_lines )
    
    return '\n'.join( block_lines )
    

def GetPrettyMediaResultInfoLines( media_result: ClientMediaResult.MediaResult, only_interesting_lines = False ) -> list[ ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine ]:
    
    def timestamp_ms_is_interesting( timestamp_ms_1, timestamp_ms_2 ):
        
        distance_1 = abs( timestamp_ms_1 - HydrusTime.GetNowMS() )
        distance_2 = abs( timestamp_ms_2 - HydrusTime.GetNowMS() )
        
        # 50000 / 51000 = 0.98 = not interesting
        # 10000 / 51000 = 0.20 = interesting
        difference = min( distance_1, distance_2 ) / max( distance_1, distance_2, 1 )
        
        return difference < 0.9
        
    
    pretty_info_lines = []
    
    file_info_manager = media_result.GetFileInfoManager()
    locations_manager = media_result.GetLocationsManager()
    times_manager = locations_manager.GetTimesManager()
    
    ( hash_id, hash, size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) = file_info_manager.ToTuple()
    
    info_string = f'{HydrusData.ToHumanBytes( size )} {HC.mime_string_lookup[ mime ]}'
    
    if width is not None and height is not None:
        
        info_string += f' ({ClientData.ResolutionToPrettyString( ( width, height ) )})'
        
    
    if duration_ms is not None:
        
        info_string += f', {HydrusTime.MillisecondsDurationToPrettyTime( duration_ms )}'
        
    elif media_result.HasSimulatedDuration():
        
        ( simulated_duration_ms, source_string ) = media_result.GetSimulatedDurationMSAndSource()
        
        info_string += f', {HydrusTime.MillisecondsDurationToPrettyTime( simulated_duration_ms )} ({source_string})'
        
    
    if num_frames is not None:
        
        framerate = media_result.GetFileInfoManager().GetFramerate()
        
        if framerate is None:
            
            framerate_insert = ''
            
        elif framerate < 1:
            
            framerate_insert = ', {:.2f}fps'.format( framerate )
            
        elif framerate < 10:
            
            framerate_insert = ', {:.1f}fps'.format( framerate )
            
        else:
            
            framerate_insert = f', {round( framerate )}fps'
            
        
        info_string += f' ({HydrusNumbers.ToHumanInt( num_frames )} frames{framerate_insert})'
        
    
    if has_audio:
        
        audio_label = CG.client_controller.new_options.GetString( 'has_audio_label' )
        
        info_string += f', {audio_label}'
        
    
    if num_words is not None:
        
        info_string += f' ({HydrusNumbers.ToHumanInt( num_words )} words)'
        
    
    pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( info_string, True ) )
    
    if file_info_manager.size is not None:
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( f'{HydrusNumbers.ToHumanInt( file_info_manager.size )} bytes', False ) )
        
    
    if file_info_manager.FiletypeIsForced():
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( f'filetype was originally: {HC.mime_string_lookup[ file_info_manager.original_mime ]}', False ) )
        
    
    #
    
    current_service_keys = locations_manager.GetCurrent()
    deleted_service_keys = locations_manager.GetDeleted()
    
    seen_local_file_service_timestamps_ms = set()
    
    if CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in current_service_keys:
        
        timestamp_ms = times_manager.GetImportedTimestampMS( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
        
        line = f'imported: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) )}'
        
        line_is_interesting = True
        
        tooltip = f'imported: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ), reverse_iso_delta_setting = True )}'
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, line_is_interesting, tooltip = tooltip ) )
        
        seen_local_file_service_timestamps_ms.add( timestamp_ms )
        
    else:
        
        if CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in deleted_service_keys:
            
            line = 'you do not have this file, but you did once'
            
        else:
            
            if file_info_manager.size is None:
                
                line = 'you do not have this file, and you have never had it'
                
            else:
                
                line = 'you do not have this file, but your client has heard a bit about it'
                
            
        
        line_is_interesting = True
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, line_is_interesting ) )
        
    
    local_file_services = CG.client_controller.services_manager.GetLocalMediaFileServices()
    
    current_local_file_services = [ service for service in local_file_services if service.GetServiceKey() in current_service_keys ]
    
    if len( current_local_file_services ) > 0:
        
        state_local_service_timestamp = not only_interesting_lines or CG.client_controller.new_options.GetBoolean( 'file_info_line_consider_file_services_import_times_interesting' )
        
        line_is_interesting = CG.client_controller.new_options.GetBoolean( 'file_info_line_consider_file_services_interesting' )
        
        for local_file_service in current_local_file_services:
            
            timestamp_ms = times_manager.GetImportedTimestampMS( local_file_service.GetServiceKey() )
            
            if state_local_service_timestamp:
                
                line = f'added to {local_file_service.GetName()}: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) )}'
                
            else:
                
                line = local_file_service.GetName()
                
            
            tooltip = f'added to {local_file_service.GetName()}: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ), reverse_iso_delta_setting = True )}'
            
            pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, line_is_interesting, tooltip = tooltip ) )
            
            seen_local_file_service_timestamps_ms.add( timestamp_ms )
            
        
    
    #
    
    deleted_local_file_services = [ service for service in local_file_services if service.GetServiceKey() in deleted_service_keys ]
    
    local_file_deletion_reason = locations_manager.GetLocalFileDeletionReason()
    
    if CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in deleted_service_keys:
        
        timestamp_ms = times_manager.GetDeletedTimestampMS( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY )
        
        line = f'deleted from this client {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) )} ({local_file_deletion_reason})'
        
        line_is_interesting = True
        
        tooltip = f'deleted from this client {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ), reverse_iso_delta_setting = True )} ({local_file_deletion_reason})'
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, line_is_interesting, tooltip = tooltip ) )
        
    elif CC.TRASH_SERVICE_KEY in current_service_keys:
        
        # I used to list these always as part of 'interesting' lines, but without the trash qualifier, you get spammy 'removed from x 5 years ago' lines for migrations. not helpful!
        
        for local_file_service in deleted_local_file_services:
            
            timestamp_ms = times_manager.GetDeletedTimestampMS( local_file_service.GetServiceKey() )
            
            line = f'removed from {local_file_service.GetName()} {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) )}'
            
            tooltip = f'removed from {local_file_service.GetName()} {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ), reverse_iso_delta_setting = True )}'
            
            line_is_interesting = False
            
            pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, line_is_interesting, tooltip = tooltip ) )
            
        
    
    if locations_manager.IsTrashed():
        
        state_trash_timestamp = not only_interesting_lines or CG.client_controller.new_options.GetBoolean( 'file_info_line_consider_trash_time_interesting' )
        
        if state_trash_timestamp:
            
            line = f'sent to trash {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) )}'
            tooltip = f'sent to trash {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ), reverse_iso_delta_setting = True )}'
            
        else:
            
            line = 'in the trash'
            tooltip = 'in the trash'
            
        
        state_deletion_reason = not only_interesting_lines or CG.client_controller.new_options.GetBoolean( 'file_info_line_consider_trash_reason_interesting' )
        
        if state_deletion_reason:
            
            line = f'{line} ({local_file_deletion_reason})'
            tooltip = f'{tooltip} ({local_file_deletion_reason})'
            
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, True, tooltip = tooltip ) )
        
    
    #
    
    state_remote_service_timestamp = not only_interesting_lines or CG.client_controller.new_options.GetBoolean( 'file_info_line_consider_file_services_import_times_interesting' )
    
    line_is_interesting = CG.client_controller.new_options.GetBoolean( 'file_info_line_consider_file_services_interesting' )
    
    for service_key in current_service_keys.intersection( CG.client_controller.services_manager.GetServiceKeys( HC.REMOTE_FILE_SERVICES ) ):
        
        timestamp_ms = times_manager.GetImportedTimestampMS( service_key )
        
        try:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
        except HydrusExceptions.DataMissing:
            
            continue
            
        
        service_type = service.GetServiceType()
        
        if service_type == HC.IPFS:
            
            status_label = 'pinned'
            
        else:
            
            status_label = 'uploaded'
            
        
        if state_remote_service_timestamp:
            
            line = f'{status_label} to {service.GetName()} {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) )}'
            
        else:
            
            line = f'{status_label} to {service.GetName()}'
            
        
        tooltip = f'{status_label} to {service.GetName()} {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ), reverse_iso_delta_setting = True )}'
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, line_is_interesting, tooltip = tooltip ) )
        
    
    #
    
    times_manager = locations_manager.GetTimesManager()
    
    file_modified_timestamp_ms = times_manager.GetAggregateModifiedTimestampMS()
    
    if file_modified_timestamp_ms is not None:
        
        if CG.client_controller.new_options.GetBoolean( 'hide_uninteresting_modified_time' ):
            
            # if we haven't already printed this timestamp somewhere
            line_is_interesting = False not in ( timestamp_ms_is_interesting( timestamp_ms, file_modified_timestamp_ms ) for timestamp_ms in seen_local_file_service_timestamps_ms )
            
        else:
            
            line_is_interesting = True
            
        
        line = f'modified: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( file_modified_timestamp_ms ) )}'
        
        tooltip = f'modified: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( file_modified_timestamp_ms ), reverse_iso_delta_setting = True )}'
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, line_is_interesting, tooltip = tooltip ) )
        
        #
        
        modified_timestamp_lines = []
        
        timestamp_ms = times_manager.GetFileModifiedTimestampMS()
        
        if timestamp_ms is not None:
            
            line = f'local: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) )}'
            
            tooltip = f'local: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ), reverse_iso_delta_setting = True )}'
            
            modified_timestamp_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, False, tooltip = tooltip ) )
            
        
        for ( domain, timestamp_ms ) in sorted( times_manager.GetDomainModifiedTimestampsMS().items() ):
            
            line = f'{domain}: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ) )}'
            
            tooltip = f'{domain}: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( timestamp_ms ), reverse_iso_delta_setting = True )}'
            
            modified_timestamp_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, False, tooltip = tooltip ) )
            
        
        if len( modified_timestamp_lines ) > 1:
            
            pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLinesSubmenu( 'all modified times', False, modified_timestamp_lines ) )
            
        
    
    #
    
    if CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in current_service_keys and not locations_manager.inbox:
        
        state_archived_timestamp = not only_interesting_lines or CG.client_controller.new_options.GetBoolean( 'file_info_line_consider_archived_time_interesting' )
        
        archived_timestamp_ms = times_manager.GetArchivedTimestampMS()
        
        if archived_timestamp_ms is None:
            
            if state_archived_timestamp:
                
                line = f'archived: unknown time'
                
            else:
                
                line = 'archived'
                
            
            tooltip = f'archived: unknown time'
            
        else:
            
            if state_archived_timestamp:
                
                line = f'archived: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( archived_timestamp_ms ) )}'
                
            else:
                
                line = 'archived'
                
            
            tooltip = f'archived: {HydrusTime.TimestampToPrettyTimeDelta( HydrusTime.SecondiseMS( archived_timestamp_ms ), reverse_iso_delta_setting = True )}'
            
        
        line_is_interesting = CG.client_controller.new_options.GetBoolean( 'file_info_line_consider_archived_interesting' )
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( line, line_is_interesting, tooltip = tooltip ) )
        
        
    
    if file_info_manager.has_audio:
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( 'has audio', False ) )
        
    
    if file_info_manager.has_transparency:
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( 'has transparency', False ) )
        
    
    if file_info_manager.has_exif:
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( 'has exif data', False ) )
        
    
    if file_info_manager.has_human_readable_embedded_metadata:
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( 'has embedded metadata', False ) )
        
    
    if file_info_manager.has_icc_profile:
        
        pretty_info_lines.append( ClientMediaResultPrettyInfoObjects.PrettyMediaResultInfoLine( 'has icc profile', False ) )
        
    
    pretty_info_lines = [ line for line in pretty_info_lines if line.interesting or not only_interesting_lines ]
    
    return pretty_info_lines
    
