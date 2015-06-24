import ClientData
import ClientFiles
import collections
import dircache
import hashlib
import httplib
import itertools
import HydrusConstants as HC
import ClientDownloading
import HydrusEncryption
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusNATPunch
import HydrusServer
import HydrusSerialisable
import HydrusTagArchive
import HydrusTags
import HydrusThreading
import ClientConstants as CC
import os
import Queue
import random
import shutil
import sqlite3
import stat
import sys
import threading
import time
import traceback
import wx
import yaml
import HydrusData
import HydrusNetworking
import HydrusGlobals

def DAEMONCheckExportFolders():
    
    options = wx.GetApp().GetOptions()
    
    if not options[ 'pause_export_folders_sync' ]:
        
        export_folders = wx.GetApp().Read( 'export_folders' )
        
        for export_folder in export_folders:
            
            export_folder.DoWork()
            
        
    
def DAEMONCheckImportFolders():
    
    options = wx.GetApp().GetOptions()
    
    if not options[ 'pause_import_folders_sync' ]:
        
        import_folders = wx.GetApp().Read( 'import_folders' )
        
        for ( folder_path, details ) in import_folders.items():
            
            if HydrusData.TimeHasPassed( details[ 'last_checked' ] + details[ 'check_period' ] ):
                
                if os.path.exists( folder_path ) and os.path.isdir( folder_path ):
                    
                    filenames = dircache.listdir( folder_path )
                    
                    raw_paths = [ folder_path + os.path.sep + filename for filename in filenames ]
                    
                    all_paths = ClientFiles.GetAllPaths( raw_paths )
                    
                    if details[ 'type' ] == HC.IMPORT_FOLDER_TYPE_SYNCHRONISE: 
                        
                        all_paths = [ path for path in all_paths if path not in details[ 'cached_imported_paths' ] ]
                        
                    
                    all_paths = [ path for path in all_paths if path not in details[ 'failed_imported_paths' ] ]
                    
                    successful_hashes = set()
                    
                    for ( i, path ) in enumerate( all_paths ):
                        
                        if options[ 'pause_import_folders_sync' ]: return
                        
                        info = os.lstat( path )
                        
                        size = info[6]
                        
                        if size == 0: continue
                        
                        ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                        
                        try:
                            
                            try:
                                
                                # try to get a write lock just to check it isn't being written to right now
                                
                                with open( path, 'ab' ) as f:
                                    
                                    pass
                                    
                                
                                with open( path, 'rb' ) as f_source:
                                    
                                    with open( temp_path, 'wb' ) as f_dest:
                                        
                                        HydrusFileHandling.CopyFileLikeToFileLike( f_source, f_dest )
                                        
                                    
                                
                            except:
                                
                                # could not lock, so try again later
                                
                                continue
                                
                            
                            try:
                                
                                if details[ 'local_tag' ] is not None: service_keys_to_tags = { CC.LOCAL_TAG_SERVICE_KEY : { details[ 'local_tag' ] } }
                                else: service_keys_to_tags = {}
                                
                                ( result, hash ) = wx.GetApp().WriteSynchronous( 'import_file', temp_path, service_keys_to_tags = service_keys_to_tags )
                                
                                if result in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ):
                                    
                                    successful_hashes.add( hash )
                                    
                                    if details[ 'type' ] == HC.IMPORT_FOLDER_TYPE_SYNCHRONISE: details[ 'cached_imported_paths' ].add( path )
                                    
                                elif result == CC.STATUS_DELETED:
                                    
                                    details[ 'failed_imported_paths' ].add( path )
                                    
                                
                                if details[ 'type' ] == HC.IMPORT_FOLDER_TYPE_DELETE:
                                    
                                    try: os.remove( path )
                                    except: details[ 'failed_imported_paths' ].add( path )
                                    
                                
                            except:
                                
                                details[ 'failed_imported_paths' ].add( path )
                                
                                HydrusData.ShowText( 'Import folder failed to import ' + path + ':' + os.linesep * 2 + traceback.format_exc() )
                                
                            
                        finally:
                            
                            HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                            
                        
                    
                    if len( successful_hashes ) > 0:
                        
                        text = HydrusData.ToString( len( successful_hashes ) ) + ' files imported from ' + folder_path
                        
                        job_key = HydrusData.JobKey()
                        
                        job_key.SetVariable( 'popup_message_title', 'import folder' )
                        job_key.SetVariable( 'popup_message_text_1', text )
                        job_key.SetVariable( 'popup_message_files', successful_hashes )
                        
                        HydrusGlobals.pubsub.pub( 'message', job_key )
                        
                    
                    details[ 'last_checked' ] = HydrusData.GetNow()
                    
                    wx.GetApp().WriteSynchronous( 'import_folder', folder_path, details )
                    
                
            
        
    
def DAEMONDownloadFiles():
    
    hashes = wx.GetApp().Read( 'downloads' )
    
    num_downloads = len( hashes )
    
    for hash in hashes:
        
        ( media_result, ) = wx.GetApp().Read( 'media_results', CC.COMBINED_FILE_SERVICE_KEY, ( hash, ) )
        
        service_keys = list( media_result.GetLocationsManager().GetCurrent() )
        
        random.shuffle( service_keys )
        
        for service_key in service_keys:
            
            if service_key == CC.LOCAL_FILE_SERVICE_KEY: break
            
            try: file_repository = wx.GetApp().GetManager( 'services' ).GetService( service_key )
            except HydrusExceptions.NotFoundException: continue
            
            if file_repository.CanDownload(): 
                
                try:
                    
                    request_args = { 'hash' : hash.encode( 'hex' ) }
                    
                    ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                    
                    try:
                        
                        file_repository.Request( HC.GET, 'file', request_args = request_args, temp_path = temp_path )
                        
                        num_downloads -= 1
                        
                        wx.GetApp().WaitUntilWXThreadIdle()
                        
                        wx.GetApp().WriteSynchronous( 'import_file', temp_path )
                        
                    finally:
                        
                        HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                        
                    
                    break
                    
                except:
                    
                    HydrusData.ShowText( 'Error downloading file:' + os.linesep + traceback.format_exc() )
                    
                
            
            if HydrusGlobals.shutdown: return
            
        
    
def DAEMONFlushServiceUpdates( list_of_service_keys_to_service_updates ):
    
    service_keys_to_service_updates = HydrusData.MergeKeyToListDicts( list_of_service_keys_to_service_updates )
    
    wx.GetApp().WriteSynchronous( 'service_updates', service_keys_to_service_updates )
    
def DAEMONResizeThumbnails():
    
    if not wx.GetApp().CurrentlyIdle(): return
    
    full_size_thumbnail_paths = { path for path in ClientFiles.IterateAllThumbnailPaths() if not path.endswith( '_resized' ) }
    
    resized_thumbnail_paths = { path[:-8] for path in ClientFiles.IterateAllThumbnailPaths() if path.endswith( '_resized' ) }
    
    thumbnail_paths_to_render = list( full_size_thumbnail_paths.difference( resized_thumbnail_paths ) )
    
    random.shuffle( thumbnail_paths_to_render )
    
    i = 0
    
    limit = max( 100, len( thumbnail_paths_to_render ) / 10 )
    
    options = wx.GetApp().GetOptions()
    
    for thumbnail_path in thumbnail_paths_to_render:
        
        try:
            
            thumbnail_resized = HydrusFileHandling.GenerateThumbnail( thumbnail_path, options[ 'thumbnail_dimensions' ] )
            
            thumbnail_resized_path = thumbnail_path + '_resized'
            
            with open( thumbnail_resized_path, 'wb' ) as f: f.write( thumbnail_resized )
            
        except IOError as e: HydrusData.ShowText( 'Thumbnail read error:' + os.linesep + traceback.format_exc() )
        except Exception as e: HydrusData.ShowText( 'Thumbnail rendering error:' + os.linesep + traceback.format_exc() )
        
        if i % 10 == 0: time.sleep( 2 )
        else:
            
            if limit > 10000: time.sleep( 0.05 )
            elif limit > 1000: time.sleep( 0.25 )
            else: time.sleep( 0.5 )
            
        
        i += 1
        
        if i > limit: break
        
        if HydrusGlobals.shutdown: break
        
    
def DAEMONSynchroniseAccounts():
    
    services = wx.GetApp().GetManager( 'services' ).GetServices( HC.RESTRICTED_SERVICES )
    
    options = wx.GetApp().GetOptions()
    
    do_notify = False
    
    for service in services:
        
        service_key = service.GetServiceKey()
        service_type = service.GetServiceType()
        
        account = service.GetInfo( 'account' )
        credentials = service.GetCredentials()
        
        if service_type in HC.REPOSITORIES:
            
            if options[ 'pause_repo_sync' ]: continue
            
            info = service.GetInfo()
            
            if info[ 'paused' ]: continue
            
        
        if account.IsStale() and credentials.HasAccessKey() and not service.HasRecentError():
            
            try:
                
                response = service.Request( HC.GET, 'account' )
                
                account = response[ 'account' ]
                
                account.MakeFresh()
                
                wx.GetApp().WriteSynchronous( 'service_updates', { service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, account ) ] } )
                
                do_notify = True
                
            except Exception as e:
                
                print( 'Failed to refresh account for ' + service.GetName() + ':' )
                
                print( traceback.format_exc() )
                
            
        
    
    if do_notify: HydrusGlobals.pubsub.pub( 'notify_new_permissions' )
    
def DAEMONSynchroniseRepositories():
    
    HydrusGlobals.repos_changed = False
    
    options = wx.GetApp().GetOptions()
    
    if not options[ 'pause_repo_sync' ]:
        
        services = wx.GetApp().GetManager( 'services' ).GetServices( HC.REPOSITORIES )
        
        for service in services:
            
            if HydrusGlobals.shutdown: raise Exception( 'Application shutting down!' )
            
            ( service_key, service_type, name, info ) = service.ToTuple()
            
            if info[ 'paused' ]: continue
            
            if not service.CanDownloadUpdate() and not service.CanProcessUpdate(): continue
            
            try:
                
                job_key = HydrusData.JobKey( pausable = True, cancellable = True )
                
                job_key.SetVariable( 'popup_message_title', 'repository synchronisation - ' + name )
                
                HydrusGlobals.pubsub.pub( 'message', job_key )
                
                num_updates_downloaded = 0
                
                if service.CanDownloadUpdate():
                    
                    job_key.SetVariable( 'popup_message_title', 'repository synchronisation - ' + name + ' - downloading' )
                    job_key.SetVariable( 'popup_message_text_1', 'checking' )
                    
                    while service.CanDownloadUpdate():
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or options[ 'pause_repo_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if options[ 'pause_repo_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'repository synchronisation paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.repos_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'repositories were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                time.sleep( 5 )
                                
                                job_key.Cancel()
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                
                                return
                                
                            
                        
                        now = HydrusData.GetNow()
                        
                        ( first_timestamp, next_download_timestamp, next_processing_timestamp ) = service.GetTimestamps()
                        
                        if first_timestamp is None:
                            
                            gauge_range = None
                            gauge_value = 0
                            
                            update_index_string = 'initial update: '
                            
                        else:
                            
                            gauge_range = ( ( now - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                            gauge_value = ( ( next_download_timestamp - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                            
                            update_index_string = 'update ' + HydrusData.ConvertValueRangeToPrettyString( gauge_value, gauge_range ) + ': '
                            
                        
                        subupdate_index_string = 'service update: '
                        
                        job_key.SetVariable( 'popup_message_text_1', update_index_string + subupdate_index_string + 'downloading and parsing' )
                        job_key.SetVariable( 'popup_message_gauge_1', ( gauge_value, gauge_range ) )
                        
                        service_update_package = service.Request( HC.GET, 'service_update_package', { 'begin' : next_download_timestamp } )
                        
                        begin = service_update_package.GetBegin()
                        
                        subindex_count = service_update_package.GetSubindexCount()
                        
                        for subindex in range( subindex_count ):
                            
                            path = ClientFiles.GetExpectedContentUpdatePackagePath( service_key, begin, subindex )
                            
                            if not os.path.exists( path ):
                                
                                subupdate_index_string = 'content update ' + HydrusData.ConvertValueRangeToPrettyString( subindex + 1, subindex_count ) + ': '
                                
                                job_key.SetVariable( 'popup_message_text_1', update_index_string + subupdate_index_string + 'downloading and parsing' )
                                
                                content_update_package = service.Request( HC.GET, 'content_update_package', { 'begin' : begin, 'subindex' : subindex } )
                                
                                obj_string = HydrusSerialisable.DumpToString( content_update_package )
                                
                                job_key.SetVariable( 'popup_message_text_1', update_index_string + subupdate_index_string + 'saving to disk' )
                                
                                with open( path, 'wb' ) as f: f.write( obj_string )
                                
                            
                        
                        job_key.SetVariable( 'popup_message_text_1', update_index_string + 'committing' )
                        
                        path = ClientFiles.GetExpectedServiceUpdatePackagePath( service_key, begin )
                        
                        obj_string = HydrusSerialisable.DumpToString( service_update_package )
                        
                        with open( path, 'wb' ) as f: f.write( obj_string )
                        
                        next_download_timestamp = service_update_package.GetNextBegin()
                        
                        service_updates = [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_DOWNLOAD_TIMESTAMP, next_download_timestamp ) ]
                        
                        service_keys_to_service_updates = { service_key : service_updates }
                        
                        wx.GetApp().WriteSynchronous( 'service_updates', service_keys_to_service_updates )
                        
                        # this waits for pubsubs to flush, so service updates are processed
                        wx.GetApp().WaitUntilWXThreadIdle()
                        
                        num_updates_downloaded += 1
                        
                    
                
                num_updates_processed = 0
                total_content_weight_processed = 0
                update_time_tracker = []
                update_speed_string = ''
                
                if service.CanProcessUpdate():
                    
                    job_key.SetVariable( 'popup_message_title', 'repository synchronisation - ' + name + ' - processing' )
                    
                    WEIGHT_THRESHOLD = 200.0
                    
                    while service.CanProcessUpdate():
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or options[ 'pause_repo_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if options[ 'pause_repo_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'repository synchronisation paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.repos_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'repositories were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                time.sleep( 5 )
                                
                                job_key.Cancel()
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                
                                return
                                
                            
                            precise_timestamp = HydrusData.GetNowPrecise()
                            
                        
                        now = HydrusData.GetNow()
                        
                        ( first_timestamp, next_download_timestamp, next_processing_timestamp ) = service.GetTimestamps()
                        
                        gauge_range = ( ( now - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                        
                        if next_processing_timestamp == 0: gauge_value = 0
                        else: gauge_value = ( ( next_processing_timestamp - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                        
                        update_index_string = 'update ' + HydrusData.ConvertValueRangeToPrettyString( gauge_value, gauge_range ) + ': '
                        
                        subupdate_index_string = 'service update: '
                        
                        job_key.SetVariable( 'popup_message_text_1', update_index_string + subupdate_index_string + 'loading from disk' )
                        job_key.SetVariable( 'popup_message_gauge_1', ( gauge_value, gauge_range ) )
                        
                        path = ClientFiles.GetExpectedServiceUpdatePackagePath( service_key, next_processing_timestamp )
                        
                        with open( path, 'rb' ) as f: obj_string = f.read()
                        
                        service_update_package = HydrusSerialisable.CreateFromString( obj_string )
                        
                        subindex_count = service_update_package.GetSubindexCount()
                        
                        pending_content_updates = []
                        pending_weight = 0
                        
                        for subindex in range( subindex_count ):
                            
                            subupdate_index_string = 'content update ' + HydrusData.ConvertValueRangeToPrettyString( subindex + 1, subindex_count ) + ': '
                            
                            path = ClientFiles.GetExpectedContentUpdatePackagePath( service_key, next_processing_timestamp, subindex )
                            
                            job_key.SetVariable( 'popup_message_text_1', update_index_string + subupdate_index_string + 'loading from disk' )
                            
                            with open( path, 'rb' ) as f: obj_string = f.read()
                            
                            job_key.SetVariable( 'popup_message_text_1', update_index_string + subupdate_index_string + 'parsing' )
                            
                            content_update_package = HydrusSerialisable.CreateFromString( obj_string )
                            
                            job_key.SetVariable( 'popup_message_text_1', update_index_string + subupdate_index_string + 'processing' )
                            
                            c_u_p_num_rows = content_update_package.GetNumRows()
                            c_u_p_total_weight_processed = 0
                            precise_timestamp = HydrusData.GetNowPrecise()
                            
                            for content_update in content_update_package.IterateContentUpdates():
                                
                                while job_key.IsPaused() or job_key.IsCancelled() or options[ 'pause_repo_sync' ] or HydrusGlobals.shutdown:
                                    
                                    time.sleep( 0.1 )
                                    
                                    if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_2', 'paused' )
                                    
                                    if options[ 'pause_repo_sync' ]: job_key.SetVariable( 'popup_message_text_2', 'repository synchronisation paused' )
                                    
                                    if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                                    
                                    if job_key.IsCancelled():
                                        
                                        job_key.SetVariable( 'popup_message_text_2', 'cancelled' )
                                        
                                        print( job_key.ToString() )
                                        
                                        return
                                        
                                    
                                    if HydrusGlobals.repos_changed:
                                        
                                        job_key.SetVariable( 'popup_message_text_2', 'repositories were changed during processing; this job was abandoned' )
                                        
                                        print( job_key.ToString() )
                                        
                                        time.sleep( 5 )
                                        
                                        job_key.Cancel()
                                        
                                        HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                        
                                        return
                                        
                                    
                                    precise_timestamp = HydrusData.GetNowPrecise()
                                    
                                
                                pending_content_updates.append( content_update )
                                
                                content_update_weight = len( content_update.GetHashes() )
                                
                                pending_weight += content_update_weight
                                
                                c_u_p_total_weight_processed += content_update_weight
                                
                                content_update_index_string = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( c_u_p_total_weight_processed, c_u_p_num_rows ) + ': '
                                
                                job_key.SetVariable( 'popup_message_text_2', content_update_index_string + 'committing' + update_speed_string )
                                
                                job_key.SetVariable( 'popup_message_gauge_2', ( c_u_p_total_weight_processed, c_u_p_num_rows ) )
                                
                                if pending_weight > WEIGHT_THRESHOLD:
                                    
                                    wx.GetApp().WaitUntilWXThreadIdle()
                                    
                                    wx.GetApp().WriteSynchronous( 'content_updates', { service_key : pending_content_updates } )
                                    
                                    it_took = HydrusData.GetNowPrecise() - precise_timestamp
                                    
                                    precise_timestamp = HydrusData.GetNowPrecise()
                                    
                                    if wx.GetApp().CurrentlyIdle(): ideal_packet_time = 10.0
                                    else: ideal_packet_time = 0.5
                                    
                                    WEIGHT_THRESHOLD = max( 200.0, WEIGHT_THRESHOLD * ideal_packet_time / it_took )
                                    
                                    total_content_weight_processed += pending_weight
                                    
                                    #
                                    
                                    if len( update_time_tracker ) > 10:
                                        
                                        update_time_tracker.pop( 0 )
                                        
                                    
                                    update_time_tracker.append( ( pending_weight, it_took ) )
                                    
                                    recent_total_weight = 0
                                    recent_total_time = 0.0
                                    
                                    for ( weight, it_took ) in update_time_tracker:
                                        
                                        recent_total_weight += weight
                                        recent_total_time += it_took
                                        
                                        recent_speed = int( recent_total_weight / recent_total_time )
                                        
                                        update_speed_string = ' at ' + HydrusData.ConvertIntToPrettyString( recent_speed ) + ' rows/s'
                                        
                                    
                                    #
                                    
                                    pending_content_updates = []
                                    pending_weight = 0
                                    
                                
                            
                        
                        if len( pending_content_updates ) > 0:
                            
                            wx.GetApp().WaitUntilWXThreadIdle()
                            
                            wx.GetApp().WriteSynchronous( 'content_updates', { service_key : pending_content_updates } )
                            
                            WEIGHT_THRESHOLD = 200.0
                            
                            total_content_weight_processed += pending_weight
                            
                        
                        job_key.SetVariable( 'popup_message_text_2', 'committing service updates' )
                        
                        service_updates = [ service_update for service_update in service_update_package.IterateServiceUpdates() ]
                        
                        next_processing_timestamp = service_update_package.GetNextBegin()
                        
                        service_updates.append( HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_PROCESSING_TIMESTAMP, next_processing_timestamp ) )
                        
                        service_keys_to_service_updates = { service_key : service_updates }
                        
                        wx.GetApp().WriteSynchronous( 'service_updates', service_keys_to_service_updates )
                        
                        HydrusGlobals.pubsub.pub( 'notify_new_pending' )
                        
                        # this waits for pubsubs to flush, so service updates are processed
                        wx.GetApp().WaitUntilWXThreadIdle()
                        
                        job_key.SetVariable( 'popup_message_gauge_2', ( 0, 1 ) )
                        job_key.SetVariable( 'popup_message_text_2', '' )
                        
                        num_updates_processed += 1
                        
                    
                
                job_key.DeleteVariable( 'popup_message_gauge_1' )
                job_key.DeleteVariable( 'popup_message_text_2' )
                job_key.DeleteVariable( 'popup_message_gauge_2' )
                
                if service_type == HC.FILE_REPOSITORY and service.CanDownload():
                    
                    job_key.SetVariable( 'popup_message_text_1', 'reviewing existing thumbnails' )
                    
                    thumbnail_hashes_i_have = ClientFiles.GetAllThumbnailHashes()
                    
                    job_key.SetVariable( 'popup_message_text_1', 'reviewing service thumbnails' )
                    
                    thumbnail_hashes_i_should_have = wx.GetApp().Read( 'thumbnail_hashes_i_should_have', service_key )
                    
                    thumbnail_hashes_i_need = thumbnail_hashes_i_should_have.difference( thumbnail_hashes_i_have )
                    
                    if len( thumbnail_hashes_i_need ) > 0:
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or options[ 'pause_repo_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if options[ 'pause_repo_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'repository synchronisation paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.repos_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'repositories were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                time.sleep( 5 )
                                
                                job_key.Cancel()
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                
                                return
                                
                            
                        
                        def SaveThumbnails( batch_of_thumbnails ):
                            
                            job_key.SetVariable( 'popup_message_text_1', 'saving thumbnails to database' )
                            
                            wx.GetApp().WriteSynchronous( 'thumbnails', batch_of_thumbnails )
                            
                            HydrusGlobals.pubsub.pub( 'add_thumbnail_count', service_key, len( batch_of_thumbnails ) )
                            
                        
                        thumbnails = []
                        
                        for ( i, hash ) in enumerate( thumbnail_hashes_i_need ):
                            
                            job_key.SetVariable( 'popup_message_text_1', 'downloading thumbnail ' + HydrusData.ConvertValueRangeToPrettyString( i, len( thumbnail_hashes_i_need ) ) )
                            job_key.SetVariable( 'popup_message_gauge_1', ( i, len( thumbnail_hashes_i_need ) ) )
                            
                            request_args = { 'hash' : hash.encode( 'hex' ) }
                            
                            thumbnail = service.Request( HC.GET, 'thumbnail', request_args = request_args )
                            
                            thumbnails.append( ( hash, thumbnail ) )
                            
                            if i % 50 == 0:
                                
                                SaveThumbnails( thumbnails )
                                
                                thumbnails = []
                                
                            
                            wx.GetApp().WaitUntilWXThreadIdle()
                            
                        
                        if len( thumbnails ) > 0: SaveThumbnails( thumbnails )
                        
                        job_key.DeleteVariable( 'popup_message_gauge_1' )
                        
                    
                
                job_key.SetVariable( 'popup_message_title', 'repository synchronisation - ' + name + ' - finished' )
                
                updates_text = HydrusData.ConvertIntToPrettyString( num_updates_downloaded ) + ' updates downloaded, ' + HydrusData.ConvertIntToPrettyString( num_updates_processed ) + ' updates processed'
                
                if service_type == HC.TAG_REPOSITORY: content_text = HydrusData.ConvertIntToPrettyString( total_content_weight_processed ) + ' mappings added'
                elif service_type == HC.FILE_REPOSITORY: content_text = HydrusData.ConvertIntToPrettyString( total_content_weight_processed ) + ' files added'
                
                job_key.SetVariable( 'popup_message_text_1', updates_text + ', and ' + content_text )
                
                print( job_key.ToString() )
                
                if total_content_weight_processed > 0: job_key.Finish()
                else: job_key.Delete()
                
            except Exception as e:
                
                job_key.Cancel()
                
                print( traceback.format_exc() )
                
                HydrusData.ShowText( 'Failed to update ' + name + ':' )
                
                HydrusData.ShowException( e )
                
                time.sleep( 3 )
                
            
        
        time.sleep( 5 )
        
    
def DAEMONSynchroniseSubscriptions():
    
    HydrusGlobals.subs_changed = False
    
    options = wx.GetApp().GetOptions()
    
    if not options[ 'pause_subs_sync' ]:
        
        subscription_names = wx.GetApp().Read( 'subscription_names' )
        
        for name in subscription_names:
            
            info = wx.GetApp().Read( 'subscription', name )
            
            site_type = info[ 'site_type' ]
            query_type = info[ 'query_type' ]
            query = info[ 'query' ]
            frequency_type = info[ 'frequency_type' ]
            frequency = info[ 'frequency' ]
            get_tags_if_redundant = info[ 'get_tags_if_redundant' ]
            initial_limit = info[ 'initial_limit' ]
            advanced_tag_options = info[ 'advanced_tag_options' ]
            advanced_import_options = info[ 'advanced_import_options' ]
            last_checked = info[ 'last_checked' ]
            url_cache = info[ 'url_cache' ]
            paused = info[ 'paused' ]
            
            if paused: continue
            
            now = HydrusData.GetNow()
            
            if last_checked is None: last_checked = 0
            
            if last_checked + ( frequency_type * frequency ) < now:
                
                try:
                    
                    job_key = HydrusData.JobKey( pausable = True, cancellable = True )
                    
                    job_key.SetVariable( 'popup_message_title', 'subscriptions - ' + name )
                    job_key.SetVariable( 'popup_message_text_1', 'checking' )
                    
                    HydrusGlobals.pubsub.pub( 'message', job_key )
                    
                    do_tags = len( advanced_tag_options ) > 0
                    
                    if site_type == HC.SITE_TYPE_BOORU:
                        
                        ( booru_name, booru_query_type ) = query_type
                        
                        try: booru = wx.GetApp().Read( 'remote_booru', booru_name )
                        except: raise Exception( 'While attempting to execute a subscription on booru ' + name + ', the client could not find that booru in the db.' )
                        
                        tags = query.split( ' ' )
                        
                        all_args = ( ( booru, tags ), )
                        
                    elif site_type == HC.SITE_TYPE_HENTAI_FOUNDRY:
                        
                        info = {}
                        
                        info[ 'rating_nudity' ] = 3
                        info[ 'rating_violence' ] = 3
                        info[ 'rating_profanity' ] = 3
                        info[ 'rating_racism' ] = 3
                        info[ 'rating_sex' ] = 3
                        info[ 'rating_spoilers' ] = 3
                        
                        info[ 'rating_yaoi' ] = 1
                        info[ 'rating_yuri' ] = 1
                        info[ 'rating_teen' ] = 1
                        info[ 'rating_guro' ] = 1
                        info[ 'rating_furry' ] = 1
                        info[ 'rating_beast' ] = 1
                        info[ 'rating_male' ] = 1
                        info[ 'rating_female' ] = 1
                        info[ 'rating_futa' ] = 1
                        info[ 'rating_other' ] = 1
                        
                        info[ 'filter_media' ] = 'A'
                        info[ 'filter_order' ] = 'date_new'
                        info[ 'filter_type' ] = 0
                        
                        advanced_hentai_foundry_options = info
                        
                        if query_type == 'artist': all_args = ( ( 'artist pictures', query, advanced_hentai_foundry_options ), ( 'artist scraps', query, advanced_hentai_foundry_options ) )
                        else:
                            
                            tags = query.split( ' ' )
                            
                            all_args = ( ( query_type, tags, advanced_hentai_foundry_options ), )
                            
                        
                    elif site_type == HC.SITE_TYPE_PIXIV: all_args = ( ( query_type, query ), )
                    else: all_args = ( ( query, ), )
                    
                    gallery_parsers = [ ClientDownloading.GetGalleryParser( site_type, *args ) for args in all_args ]
                    
                    gallery_parsers[0].SetupGallerySearch() # for now this is cookie-based for hf, so only have to do it on one
                    
                    all_urls = []
                    
                    page_index = 0
                    
                    while True:
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or options[ 'pause_subs_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if options[ 'pause_subs_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'subscriptions paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.subs_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'subscriptions were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                time.sleep( 5 )
                                
                                job_key.Cancel()
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_subs_sync_daemon' )
                                
                                return
                                
                            
                        
                        if last_checked == 0 and initial_limit is not None and len( all_urls ) >= initial_limit: break
                        
                        gallery_parsers_to_remove = []
                        
                        for gallery_parser in gallery_parsers:
                            
                            if last_checked == 0 and initial_limit is not None and len( all_urls ) >= initial_limit: break
                            
                            page_of_urls = gallery_parser.GetPage( page_index )
                            
                            if len( page_of_urls ) == 0: gallery_parsers_to_remove.append( gallery_parser )
                            else:
                                
                                fresh_urls = [ url for url in page_of_urls if url not in url_cache ]
                                
                                reached_url_cache = len( fresh_urls ) != len( page_of_urls )
                                
                                if reached_url_cache: gallery_parsers_to_remove.append( gallery_parser )
                                
                                if initial_limit is not None:
                                    
                                    while len( fresh_urls ) > 0:
                                        
                                        url = fresh_urls.pop( 0 )
                                        
                                        all_urls.append( url )
                                        
                                        if len( all_urls ) >= initial_limit:
                                            
                                            break
                                            
                                        
                                    
                                else:
                                    
                                    all_urls.extend( fresh_urls )
                                    
                                
                                job_key.SetVariable( 'popup_message_text_1', 'found ' + HydrusData.ConvertIntToPrettyString( len( all_urls ) ) + ' new files' )
                                
                            
                            time.sleep( 5 )
                            
                        
                        for gallery_parser in gallery_parsers_to_remove: gallery_parsers.remove( gallery_parser )
                        
                        if len( gallery_parsers ) == 0: break
                        
                        page_index += 1
                        
                    
                    all_urls.reverse() # to do oldest first, which means we can save incrementally
                    
                    num_new = 0
                    
                    successful_hashes = set()
                    
                    for ( i, url ) in enumerate( all_urls ):
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or options[ 'pause_subs_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if options[ 'pause_subs_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'subscriptions paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.subs_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'subscriptions were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                time.sleep( 5 )
                                
                                job_key.Cancel()
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_subs_sync_daemon' )
                                
                                return
                                
                            
                        
                        try:
                            
                            url_cache.add( url )
                            
                            x_out_of_y = 'file ' + HydrusData.ConvertValueRangeToPrettyString( i, len( all_urls ) ) + ': '
                            
                            job_key.SetVariable( 'popup_message_text_1', x_out_of_y + 'checking url status' )
                            job_key.SetVariable( 'popup_message_gauge_1', ( i, len( all_urls ) ) )
                            
                            if len( successful_hashes ) > 0:
                                
                                job_key_s_h = set( successful_hashes )
                                
                                job_key.SetVariable( 'popup_message_files', job_key_s_h )
                                
                            
                            ( status, hash ) = wx.GetApp().Read( 'url_status', url )
                            
                            if status == CC.STATUS_DELETED and not advanced_import_options[ 'exclude_deleted_files' ]: status = CC.STATUS_NEW
                            
                            if status == CC.STATUS_REDUNDANT:
                                
                                if do_tags and get_tags_if_redundant:
                                    
                                    try:
                                        
                                        job_key.SetVariable( 'popup_message_text_1', x_out_of_y + 'found file in db, fetching tags' )
                                        
                                        tags = gallery_parser.GetTags( url )
                                        
                                        service_keys_to_tags = ClientDownloading.ConvertTagsToServiceKeysToTags( tags, advanced_tag_options )
                                        
                                        service_keys_to_content_updates = ClientDownloading.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags )
                                        
                                        wx.GetApp().WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                                        
                                    except: pass
                                    
                                
                            elif status == CC.STATUS_NEW:
                                
                                num_new += 1
                                
                                job_key.SetVariable( 'popup_message_text_1', x_out_of_y + 'downloading file' )
                                
                                ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                                
                                try:
                                    
                                    if do_tags: tags = gallery_parser.GetFileAndTags( temp_path, url )
                                    else:
                                        
                                        gallery_parser.GetFile( temp_path, url )
                                        
                                        tags = []
                                        
                                    
                                    service_keys_to_tags = ClientDownloading.ConvertTagsToServiceKeysToTags( tags, advanced_tag_options )
                                    
                                    job_key.SetVariable( 'popup_message_text_1', x_out_of_y + 'importing file' )
                                    
                                    ( status, hash ) = wx.GetApp().WriteSynchronous( 'import_file', temp_path, advanced_import_options = advanced_import_options, service_keys_to_tags = service_keys_to_tags, url = url )
                                    
                                finally:
                                    
                                    HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                                    
                                
                                if status in ( CC.STATUS_SUCCESSFUL, CC.STATUS_REDUNDANT ): successful_hashes.add( hash )
                                
                            
                        except Exception as e:
                            
                            HydrusData.ShowText( 'While trying to execute subscription ' + name + ', the url ' + url + ' caused this problem:' )
                            
                            HydrusData.ShowException( e )
                            
                        
                        if i % 20 == 0:
                            
                            info[ 'site_type' ] = site_type
                            info[ 'query_type' ] = query_type
                            info[ 'query' ] = query
                            info[ 'frequency_type' ] = frequency_type
                            info[ 'frequency' ] = frequency
                            info[ 'get_tags_if_redundant' ] = get_tags_if_redundant
                            info[ 'initial_limit' ] = initial_limit
                            info[ 'advanced_tag_options' ] = advanced_tag_options
                            info[ 'advanced_import_options' ] = advanced_import_options
                            info[ 'last_checked' ] = last_checked
                            info[ 'url_cache' ] = url_cache
                            info[ 'paused' ] = paused
                            
                            wx.GetApp().WriteSynchronous( 'subscription', name, info )
                            
                        
                        wx.GetApp().WaitUntilWXThreadIdle()
                        
                        time.sleep( 3 )
                        
                    
                    job_key.DeleteVariable( 'popup_message_gauge_1' )
                    
                    if len( successful_hashes ) > 0:
                        
                        job_key.SetVariable( 'popup_message_text_1', HydrusData.ToString( len( successful_hashes ) ) + ' files imported' )
                        job_key.SetVariable( 'popup_message_files', successful_hashes )
                        
                    else: job_key.SetVariable( 'popup_message_text_1', 'no new files' )
                    
                    print( job_key.ToString() )
                    
                    job_key.DeleteVariable( 'popup_message_text_1' )
                    
                    if len( successful_hashes ) > 0: job_key.Finish()
                    else: job_key.Delete()
                    
                    last_checked = now
                    
                except Exception as e:
                    
                    job_key.Cancel()
                    
                    last_checked = now + HC.UPDATE_DURATION
                    
                    HydrusData.ShowText( 'Problem with ' + name + ':' )
                    
                    HydrusData.ShowException( e )
                    
                    time.sleep( 3 )
                    
                
                info[ 'site_type' ] = site_type
                info[ 'query_type' ] = query_type
                info[ 'query' ] = query
                info[ 'frequency_type' ] = frequency_type
                info[ 'frequency' ] = frequency
                info[ 'get_tags_if_redundant' ] = get_tags_if_redundant
                info[ 'initial_limit' ] = initial_limit
                info[ 'advanced_tag_options' ] = advanced_tag_options
                info[ 'advanced_import_options' ] = advanced_import_options
                info[ 'last_checked' ] = last_checked
                info[ 'url_cache' ] = url_cache
                info[ 'paused' ] = paused
                
                wx.GetApp().WriteSynchronous( 'subscription', name, info )
                
            
        
        time.sleep( 3 )
        
    
def DAEMONUPnP():
    
    try:
        
        local_ip = HydrusNATPunch.GetLocalIP()
        
        current_mappings = HydrusNATPunch.GetUPnPMappings()
        
        our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_ip_address, external_port, protocol, enabled ) in current_mappings }
        
    except: return # This IGD probably doesn't support UPnP, so don't spam the user with errors they can't fix!
    
    services = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.LOCAL_BOORU, ) )
    
    for service in services:
        
        info = service.GetInfo()
        
        internal_port = info[ 'port' ]
        upnp = info[ 'upnp' ]
        
        if ( local_ip, internal_port ) in our_mappings:
            
            current_external_port = our_mappings[ ( local_ip, internal_port ) ]
            
            if upnp is None or current_external_port != upnp: HydrusNATPunch.RemoveUPnPMapping( current_external_port, 'TCP' )
            
        
    
    for service in services:
        
        info = service.GetInfo()
        
        internal_port = info[ 'port' ]
        upnp = info[ 'upnp' ]
        
        if upnp is not None:
            
            if ( local_ip, internal_port ) not in our_mappings:
                
                service_type = service.GetServiceType()
                
                external_port = upnp
                
                protocol = 'TCP'
                
                description = HC.service_string_lookup[ service_type ] + ' at ' + local_ip + ':' + str( internal_port )
                
                duration = 3600
                
                HydrusNATPunch.AddUPnPMapping( local_ip, internal_port, external_port, protocol, description, duration = duration )
                
            
        
    