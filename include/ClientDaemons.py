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
import HydrusMessageHandling
import HydrusNATPunch
import HydrusServer
import HydrusTagArchive
import HydrusTags
import HydrusThreading
import ClientConstants as CC
import ClientConstantsMessages
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
    
    if not HC.options[ 'pause_export_folders_sync' ]:
        
        export_folders = wx.GetApp().ReadDaemon( 'export_folders' )
        
        for ( folder_path, details ) in export_folders.items():
            
            now = HydrusData.GetNow()
            
            if now > details[ 'last_checked' ] + details[ 'period' ]:
                
                if os.path.exists( folder_path ) and os.path.isdir( folder_path ):
                    
                    existing_filenames = dircache.listdir( folder_path )
                    
                    #
                    
                    predicates = details[ 'predicates' ]
                    
                    search_context = ClientData.FileSearchContext( CC.LOCAL_FILE_SERVICE_KEY, CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = True, predicates = predicates )
                    
                    query_hash_ids = wx.GetApp().Read( 'file_query_ids', search_context )
                    
                    query_hash_ids = list( query_hash_ids )
                    
                    random.shuffle( query_hash_ids )
                    
                    limit = search_context.GetSystemPredicates().GetLimit()
                    
                    if limit is not None: query_hash_ids = query_hash_ids[ : limit ]
                    
                    media_results = []
                    
                    i = 0
                    
                    base = 256
                    
                    while i < len( query_hash_ids ):
                        
                        if HC.options[ 'pause_export_folders_sync' ]: return
                        
                        if i == 0: ( last_i, i ) = ( 0, base )
                        else: ( last_i, i ) = ( i, i + base )
                        
                        sub_query_hash_ids = query_hash_ids[ last_i : i ]
                        
                        more_media_results = wx.GetApp().Read( 'media_results_from_ids', CC.LOCAL_FILE_SERVICE_KEY, sub_query_hash_ids )
                        
                        media_results.extend( more_media_results )
                        
                    
                    #
                    
                    phrase = details[ 'phrase' ]
                    
                    terms = ClientData.ParseExportPhrase( phrase )
                    
                    for media_result in media_results:
                        
                        hash = media_result.GetHash()
                        mime = media_result.GetMime()
                        
                        filename = ClientData.GenerateExportFilename( media_result, terms )
                        
                        ext = HC.mime_ext_lookup[ mime ]
                        
                        path = folder_path + os.path.sep + filename + ext
                        
                        if not os.path.exists( path ):
                            
                            source_path = ClientFiles.GetFilePath( hash, mime )
                            
                            shutil.copy( source_path, path )
                            
                        
                    
                    details[ 'last_checked' ] = now
                    
                    wx.GetApp().WriteSynchronous( 'export_folder', folder_path, details )
                    
                
            
        
    
def DAEMONCheckImportFolders():
    
    if not HC.options[ 'pause_import_folders_sync' ]:
        
        import_folders = wx.GetApp().ReadDaemon( 'import_folders' )
        
        for ( folder_path, details ) in import_folders.items():
            
            now = HydrusData.GetNow()
            
            if now > details[ 'last_checked' ] + details[ 'check_period' ]:
                
                if os.path.exists( folder_path ) and os.path.isdir( folder_path ):
                    
                    filenames = dircache.listdir( folder_path )
                    
                    raw_paths = [ folder_path + os.path.sep + filename for filename in filenames ]
                    
                    all_paths = ClientFiles.GetAllPaths( raw_paths )
                    
                    if details[ 'type' ] == HC.IMPORT_FOLDER_TYPE_SYNCHRONISE: 
                        
                        all_paths = [ path for path in all_paths if path not in details[ 'cached_imported_paths' ] ]
                        
                    
                    all_paths = [ path for path in all_paths if path not in details[ 'failed_imported_paths' ] ]
                    
                    successful_hashes = set()
                    
                    for ( i, path ) in enumerate( all_paths ):
                        
                        if HC.options[ 'pause_import_folders_sync' ]: return
                        
                        info = os.lstat( path )
                        
                        size = info[6]
                        
                        if size == 0: continue
                        
                        ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                        
                        try:
                            
                            try:
                                
                                # make read only perms to make sure it isn't being written/downloaded right now
                                
                                os.chmod( path, stat.S_IREAD )
                                
                                os.chmod( path, stat.S_IWRITE )
                                
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
                                
                                if result in ( 'successful', 'redundant' ):
                                    
                                    successful_hashes.add( hash )
                                    
                                    if details[ 'type' ] == HC.IMPORT_FOLDER_TYPE_SYNCHRONISE: details[ 'cached_imported_paths' ].add( path )
                                    
                                elif result == 'deleted':
                                    
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
                        
                    
                    details[ 'last_checked' ] = now
                    
                    wx.GetApp().WriteSynchronous( 'import_folder', folder_path, details )
                    
                
            
        
    
def DAEMONDownloadFiles():
    
    hashes = wx.GetApp().ReadDaemon( 'downloads' )
    
    num_downloads = len( hashes )
    
    for hash in hashes:
        
        ( media_result, ) = wx.GetApp().ReadDaemon( 'media_results', CC.COMBINED_FILE_SERVICE_KEY, ( hash, ) )
        
        service_keys = list( media_result.GetLocationsManager().GetCurrent() )
        
        random.shuffle( service_keys )
        
        for service_key in service_keys:
            
            if service_key == CC.LOCAL_FILE_SERVICE_KEY: break
            
            try: file_repository = wx.GetApp().GetManager( 'services' ).GetService( service_key )
            except HydrusExceptions.NotFoundException: continue
            
            HydrusGlobals.pubsub.pub( 'downloads_status', HydrusData.ConvertIntToPrettyString( num_downloads ) + ' file downloads' )
            
            if file_repository.CanDownload(): 
                
                try:
                    
                    request_args = { 'hash' : hash.encode( 'hex' ) }
                    
                    ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                    
                    try:
                        
                        file_repository.Request( HC.GET, 'file', request_args = request_args, temp_path = temp_path )
                        
                        num_downloads -= 1
                        
                        wx.GetApp().WaitUntilGoodTimeToUseGUIThread()
                        
                        HydrusGlobals.pubsub.pub( 'downloads_status', HydrusData.ConvertIntToPrettyString( num_downloads ) + ' file downloads' )
                        
                        wx.GetApp().WriteSynchronous( 'import_file', temp_path )
                        
                    finally:
                        
                        HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                        
                    
                    break
                    
                except:
                    
                    HydrusData.ShowText( 'Error downloading file:' + os.linesep + traceback.format_exc() )
                    
                
            
            if HydrusGlobals.shutdown: return
            
        
    
    if num_downloads == 0: HydrusGlobals.pubsub.pub( 'downloads_status', 'no file downloads' )
    elif num_downloads > 0: HydrusGlobals.pubsub.pub( 'downloads_status', HydrusData.ConvertIntToPrettyString( num_downloads ) + ' inactive file downloads' )
    
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
    
    for thumbnail_path in thumbnail_paths_to_render:
        
        try:
            
            thumbnail_resized = HydrusFileHandling.GenerateThumbnail( thumbnail_path, HC.options[ 'thumbnail_dimensions' ] )
            
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
    
    do_notify = False
    
    for service in services:
        
        service_key = service.GetServiceKey()
        service_type = service.GetServiceType()
        
        account = service.GetInfo( 'account' )
        credentials = service.GetCredentials()
        
        if service_type in HC.REPOSITORIES:
            
            if HC.options[ 'pause_repo_sync' ]: continue
            
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
    
def DAEMONSynchroniseMessages():
    
    services = wx.GetApp().GetManager( 'services' ).GetServices( ( HC.MESSAGE_DEPOT, ) )
    
    for service in services:
        
        try:
            
            service_key = service.GetServiceKey()
            service_type = service.GetServiceType()
            name = service.GetName()
            
            if service.CanCheck():
                
                contact = service.GetContact()
                
                connection = service.GetConnection()
                
                private_key = service.GetPrivateKey()
                
                # is the account associated?
                
                if not contact.HasPublicKey():
                    
                    try:
                        
                        public_key = HydrusEncryption.GetPublicKey( private_key )
                        
                        connection.Post( 'contact', public_key = public_key )
                        
                        wx.GetApp().WriteSynchronous( 'contact_associated', service_key )
                        
                        contact = service.GetContact()
                        
                        HydrusData.ShowText( 'associated public key with account at ' + name )
                        
                    except:
                        
                        continue
                        
                    
                
                # see if there are any new message_keys to download or statuses
                
                last_check = service.GetLastCheck()
                
                ( message_keys, statuses ) = connection.Get( 'message_info_since', since = last_check )
                
                decrypted_statuses = []
                
                for status in statuses:
                    
                    try: decrypted_statuses.append( HydrusMessageHandling.UnpackageDeliveredStatus( status, private_key ) )
                    except: pass
                    
                
                new_last_check = HydrusData.GetNow() - 5
                
                wx.GetApp().WriteSynchronous( 'message_info_since', service_key, message_keys, decrypted_statuses, new_last_check )
                
                if len( message_keys ) > 0: HydrusData.ShowText( 'Checked ' + name + ' up to ' + HydrusData.ConvertTimestampToPrettyTime( new_last_check ) + ', finding ' + HydrusData.ToString( len( message_keys ) ) + ' new messages' )
                
            
            # try to download any messages that still need downloading
            
            if service.CanDownload():
                
                serverside_message_keys = wx.GetApp().ReadDaemon( 'message_keys_to_download', service_key )
                
                if len( serverside_message_keys ) > 0:
                    
                    connection = service.GetConnection()
                    
                    private_key = service.GetPrivateKey()
                    
                    num_processed = 0
                    
                    for serverside_message_key in serverside_message_keys:
                        
                        try:
                            
                            encrypted_message = connection.Get( 'message', message_key = serverside_message_key.encode( 'hex' ) )
                            
                            message = HydrusMessageHandling.UnpackageDeliveredMessage( encrypted_message, private_key )
                            
                            wx.GetApp().WriteSynchronous( 'message', message, serverside_message_key = serverside_message_key )
                            
                            num_processed += 1
                            
                        except Exception as e:
                            
                            if issubclass( e, httplib.HTTPException ): break # it was an http error; try again later
                            
                        
                    
                    if num_processed > 0:
                        
                        HydrusData.ShowText( 'Downloaded and parsed ' + HydrusData.ToString( num_processed ) + ' messages from ' + name )
                        
                    
                
            
        except Exception as e:
            
            HydrusData.ShowText( 'Failed to check ' + name + ':' )
            
            HydrusData.ShowException( e )
            
        
    
    wx.GetApp().WriteSynchronous( 'flush_message_statuses' )
    
    # send messages to recipients and update my status to sent/failed
    
    messages_to_send = wx.GetApp().ReadDaemon( 'messages_to_send' )
    
    for ( message_key, contacts_to ) in messages_to_send:
        
        message = wx.GetApp().ReadDaemon( 'transport_message', message_key )
        
        contact_from = message.GetContactFrom()
        
        from_anon = contact_from is None or contact_from.GetName() == 'Anonymous'
        
        if not from_anon:
            
            my_public_key = contact_from.GetPublicKey()
            my_contact_key = contact_from.GetContactKey()
            
            my_message_depot = wx.GetApp().GetManager( 'services' ).GetService( contact_from.GetServiceKey() )
            
            from_connection = my_message_depot.GetConnection()
            
        
        service_status_updates = []
        local_status_updates = []
        
        for contact_to in contacts_to:
            
            public_key = contact_to.GetPublicKey()
            contact_key = contact_to.GetContactKey()
            
            encrypted_message = HydrusMessageHandling.PackageMessageForDelivery( message, public_key )
            
            try:
                
                to_connection = contact_to.GetConnection()
                
                to_connection.Post( 'message', message = encrypted_message, contact_key = contact_key )
                
                status = 'sent'
                
            except:
                
                HydrusData.ShowText( 'Sending a message failed: ' + os.linesep + traceback.format_exc() )
                
                status = 'failed'
                
            
            status_key = hashlib.sha256( contact_key + message_key ).digest()
            
            if not from_anon: service_status_updates.append( ( status_key, HydrusMessageHandling.PackageStatusForDelivery( ( message_key, contact_key, status ), my_public_key ) ) )
            
            local_status_updates.append( ( contact_key, status ) )
            
        
        if not from_anon: from_connection.Post( 'message_statuses', contact_key = my_contact_key, statuses = service_status_updates )
        
        wx.GetApp().WriteSynchronous( 'message_statuses', message_key, local_status_updates )
        
    
    wx.GetApp().ReadDaemon( 'status_num_inbox' )
    
def DAEMONSynchroniseRepositories():
    
    HydrusGlobals.repos_changed = False
    
    if not HC.options[ 'pause_repo_sync' ]:
        
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
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or HC.options[ 'pause_repo_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if HC.options[ 'pause_repo_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'repository synchronisation paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.repos_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'repositories were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                
                                return
                                
                            
                        
                        now = HydrusData.GetNow()
                        
                        ( first_timestamp, next_download_timestamp, next_processing_timestamp ) = service.GetTimestamps()
                        
                        if first_timestamp is None:
                            
                            range = None
                            value = 0
                            
                            update_index_string = 'initial update: '
                            
                        else:
                            
                            range = ( ( now - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                            value = ( ( next_download_timestamp - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                            
                            update_index_string = 'update ' + HydrusData.ConvertIntToPrettyString( value ) + '/' + HydrusData.ConvertIntToPrettyString( range ) + ': '
                            
                        
                        job_key.SetVariable( 'popup_message_text_1', update_index_string + 'downloading and parsing' )
                        job_key.SetVariable( 'popup_message_gauge_1', ( value, range ) )
                        
                        update = service.Request( HC.GET, 'update', { 'begin' : next_download_timestamp } )
                        
                        ( begin, end ) = update.GetBeginEnd()
                        
                        job_key.SetVariable( 'popup_message_text_1', update_index_string + 'saving to disk' )
                        
                        update_path = ClientFiles.GetUpdatePath( service_key, begin )
                        
                        with open( update_path, 'wb' ) as f: f.write( yaml.safe_dump( update ) )
                        
                        next_download_timestamp = end + 1
                        
                        service_updates = [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_DOWNLOAD_TIMESTAMP, next_download_timestamp ) ]
                        
                        service_keys_to_service_updates = { service_key : service_updates }
                        
                        wx.GetApp().WriteSynchronous( 'service_updates', service_keys_to_service_updates )
                        
                        # this waits for pubsubs to flush, so service updates are processed
                        wx.GetApp().WaitUntilGoodTimeToUseGUIThread()
                        
                        num_updates_downloaded += 1
                        
                    
                
                num_updates_processed = 0
                total_content_weight_processed = 0
                
                if service.CanProcessUpdate():
                    
                    job_key.SetVariable( 'popup_message_title', 'repository synchronisation - ' + name + ' - processing' )
                    
                    WEIGHT_THRESHOLD = 50.0
                    
                    while service.CanProcessUpdate():
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or HC.options[ 'pause_repo_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if HC.options[ 'pause_repo_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'repository synchronisation paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.repos_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'repositories were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                
                                return
                                
                            
                        
                        now = HydrusData.GetNow()
                        
                        ( first_timestamp, next_download_timestamp, next_processing_timestamp ) = service.GetTimestamps()
                        
                        range = ( ( now - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                        
                        if next_processing_timestamp == 0: value = 0
                        else: value = ( ( next_processing_timestamp - first_timestamp ) / HC.UPDATE_DURATION ) + 1
                        
                        update_index_string = 'update ' + HydrusData.ConvertIntToPrettyString( value ) + '/' + HydrusData.ConvertIntToPrettyString( range ) + ': '
                        
                        job_key.SetVariable( 'popup_message_text_1', update_index_string + 'loading from disk' )
                        job_key.SetVariable( 'popup_message_gauge_1', ( value, range ) )
                        
                        update_path = ClientFiles.GetUpdatePath( service_key, next_processing_timestamp )
                        
                        with open( update_path, 'rb' ) as f: update_yaml = f.read()
                        
                        job_key.SetVariable( 'popup_message_text_1', update_index_string + 'parsing' )
                        
                        update = yaml.safe_load( update_yaml )
                        
                        job_key.SetVariable( 'popup_message_text_1', update_index_string + 'processing' )
                        
                        num_content_updates = update.GetNumContentUpdates()
                        content_updates = []
                        current_weight = 0
                        
                        for ( i, content_update ) in enumerate( update.IterateContentUpdates() ):
                            
                            while job_key.IsPaused() or job_key.IsCancelled() or HC.options[ 'pause_repo_sync' ] or HydrusGlobals.shutdown:
                                
                                time.sleep( 0.1 )
                                
                                if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_2', 'paused' )
                                
                                if HC.options[ 'pause_repo_sync' ]: job_key.SetVariable( 'popup_message_text_2', 'repository synchronisation paused' )
                                
                                if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                                
                                if job_key.IsCancelled():
                                    
                                    job_key.SetVariable( 'popup_message_text_2', 'cancelled' )
                                    
                                    print( job_key.ToString() )
                                    
                                    return
                                    
                                
                                if HydrusGlobals.repos_changed:
                                    
                                    job_key.SetVariable( 'popup_message_text_2', 'repositories were changed during processing; this job was abandoned' )
                                    
                                    print( job_key.ToString() )
                                    
                                    HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                    
                                    return
                                    
                                
                            
                            content_update_index_string = 'content part ' + HydrusData.ConvertIntToPrettyString( i ) + '/' + HydrusData.ConvertIntToPrettyString( num_content_updates ) + ': '
                            
                            job_key.SetVariable( 'popup_message_gauge_2', ( i, num_content_updates ) )
                            
                            content_updates.append( content_update )
                            
                            current_weight += len( content_update.GetHashes() )
                            
                            if current_weight > WEIGHT_THRESHOLD:
                                
                                job_key.SetVariable( 'popup_message_text_2', content_update_index_string + 'committing' )
                                
                                wx.GetApp().WaitUntilGoodTimeToUseGUIThread()
                                
                                before_precise = HydrusData.GetNowPrecise()
                                
                                wx.GetApp().WriteSynchronous( 'content_updates', { service_key : content_updates } )
                                
                                after_precise = HydrusData.GetNowPrecise()
                                
                                if wx.GetApp().CurrentlyIdle(): ideal_packet_time = 10.0
                                else: ideal_packet_time = 0.5
                                
                                too_long = ideal_packet_time * 1.5
                                too_short = ideal_packet_time * 0.8
                                really_too_long = ideal_packet_time * 20
                                
                                if after_precise - before_precise > too_long: WEIGHT_THRESHOLD /= 1.5
                                elif after_precise - before_precise < too_short: WEIGHT_THRESHOLD *= 1.05
                                
                                if after_precise - before_precise > really_too_long or WEIGHT_THRESHOLD < 1.0:
                                    
                                    job_key.SetVariable( 'popup_message_text_2', 'taking a break' )
                                    
                                    time.sleep( 10 )
                                    
                                    WEIGHT_THRESHOLD = 1.0
                                    
                                
                                total_content_weight_processed += current_weight
                                
                                content_updates = []
                                current_weight = 0
                                
                            
                        
                        if len( content_updates ) > 0:
                            
                            content_update_index_string = 'content part ' + HydrusData.ConvertIntToPrettyString( num_content_updates ) + '/' + HydrusData.ConvertIntToPrettyString( num_content_updates ) + ': '
                            
                            job_key.SetVariable( 'popup_message_text_2', content_update_index_string + 'committing' )
                            
                            wx.GetApp().WriteSynchronous( 'content_updates', { service_key : content_updates } )
                            
                            total_content_weight_processed += current_weight
                            
                        
                        job_key.SetVariable( 'popup_message_text_2', 'committing service updates' )
                        
                        service_updates = [ service_update for service_update in update.IterateServiceUpdates() ]
                        
                        ( begin, end ) = update.GetBeginEnd()
                        
                        next_processing_timestamp = end + 1
                        
                        service_updates.append( HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_NEXT_PROCESSING_TIMESTAMP, next_processing_timestamp ) )
                        
                        service_keys_to_service_updates = { service_key : service_updates }
                        
                        wx.GetApp().WriteSynchronous( 'service_updates', service_keys_to_service_updates )
                        
                        HydrusGlobals.pubsub.pub( 'notify_new_pending' )
                        
                        # this waits for pubsubs to flush, so service updates are processed
                        wx.GetApp().WaitUntilGoodTimeToUseGUIThread()
                        
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
                    
                    thumbnail_hashes_i_should_have = wx.GetApp().ReadDaemon( 'thumbnail_hashes_i_should_have', service_key )
                    
                    thumbnail_hashes_i_need = thumbnail_hashes_i_should_have.difference( thumbnail_hashes_i_have )
                    
                    if len( thumbnail_hashes_i_need ) > 0:
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or HC.options[ 'pause_repo_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if HC.options[ 'pause_repo_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'repository synchronisation paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.repos_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'repositories were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_repo_sync_daemon' )
                                
                                return
                                
                            
                        
                        def SaveThumbnails( batch_of_thumbnails ):
                            
                            job_key.SetVariable( 'popup_message_text_1', 'saving thumbnails to database' )
                            
                            wx.GetApp().WriteSynchronous( 'thumbnails', batch_of_thumbnails )
                            
                            HydrusGlobals.pubsub.pub( 'add_thumbnail_count', service_key, len( batch_of_thumbnails ) )
                            
                        
                        thumbnails = []
                        
                        for ( i, hash ) in enumerate( thumbnail_hashes_i_need ):
                            
                            job_key.SetVariable( 'popup_message_text_1', 'downloading thumbnail ' + HydrusData.ConvertIntToPrettyString( i ) + '/' + HydrusData.ConvertIntToPrettyString( len( thumbnail_hashes_i_need ) ) )
                            job_key.SetVariable( 'popup_message_gauge_1', ( i, len( thumbnail_hashes_i_need ) ) )
                            
                            request_args = { 'hash' : hash.encode( 'hex' ) }
                            
                            thumbnail = service.Request( HC.GET, 'thumbnail', request_args = request_args )
                            
                            thumbnails.append( ( hash, thumbnail ) )
                            
                            if i % 50 == 0:
                                
                                SaveThumbnails( thumbnails )
                                
                                thumbnails = []
                                
                            
                            wx.GetApp().WaitUntilGoodTimeToUseGUIThread()
                            
                        
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
    
    if not HC.options[ 'pause_subs_sync' ]:
        
        subscription_names = wx.GetApp().ReadDaemon( 'subscription_names' )
        
        for name in subscription_names:
            
            info = wx.GetApp().ReadDaemon( 'subscription', name )
            
            site_type = info[ 'site_type' ]
            query_type = info[ 'query_type' ]
            query = info[ 'query' ]
            frequency_type = info[ 'frequency_type' ]
            frequency = info[ 'frequency' ]
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
                        
                        try: booru = wx.GetApp().ReadDaemon( 'remote_booru', booru_name )
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
                    
                    downloaders = [ ClientDownloading.GetDownloader( site_type, *args ) for args in all_args ]
                    
                    downloaders[0].SetupGallerySearch() # for now this is cookie-based for hf, so only have to do it on one
                    
                    all_url_args = []
                    
                    while True:
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or HC.options[ 'pause_subs_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if HC.options[ 'pause_subs_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'subscriptions paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.subs_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'subscriptions were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_subs_sync_daemon' )
                                
                                return
                                
                            
                        
                        downloaders_to_remove = []
                        
                        for downloader in downloaders:
                            
                            page_of_url_args = downloader.GetAnotherPage()
                            
                            if len( page_of_url_args ) == 0: downloaders_to_remove.append( downloader )
                            else:
                                
                                fresh_url_args = [ url_args for url_args in page_of_url_args if url_args[0] not in url_cache ]
                                
                                # i.e. we have hit the url cache, so no need to fetch any more pages
                                if len( fresh_url_args ) == 0 or len( fresh_url_args ) != len( page_of_url_args ): downloaders_to_remove.append( downloader )
                                
                                all_url_args.extend( fresh_url_args )
                                
                                job_key.SetVariable( 'popup_message_text_1', 'found ' + HydrusData.ConvertIntToPrettyString( len( all_url_args ) ) + ' new files' )
                                
                            
                            time.sleep( 5 )
                            
                        
                        for downloader in downloaders_to_remove: downloaders.remove( downloader )
                        
                        if len( downloaders ) == 0: break
                        
                    
                    all_url_args.reverse() # to do oldest first, which means we can save incrementally
                    
                    num_new = 0
                    
                    successful_hashes = set()
                    
                    for ( i, url_args ) in enumerate( all_url_args ):
                        
                        while job_key.IsPaused() or job_key.IsCancelled() or HC.options[ 'pause_subs_sync' ] or HydrusGlobals.shutdown:
                            
                            time.sleep( 0.1 )
                            
                            if job_key.IsPaused(): job_key.SetVariable( 'popup_message_text_1', 'paused' )
                            
                            if HC.options[ 'pause_subs_sync' ]: job_key.SetVariable( 'popup_message_text_1', 'subscriptions paused' )
                            
                            if HydrusGlobals.shutdown: raise Exception( 'application shutting down!' )
                            
                            if job_key.IsCancelled():
                                
                                job_key.SetVariable( 'popup_message_text_1', 'cancelled' )
                                
                                print( job_key.ToString() )
                                
                                return
                                
                            
                            if HydrusGlobals.subs_changed:
                                
                                job_key.SetVariable( 'popup_message_text_1', 'subscriptions were changed during processing; this job was abandoned' )
                                
                                print( job_key.ToString() )
                                
                                HydrusGlobals.pubsub.pub( 'notify_restart_subs_sync_daemon' )
                                
                                return
                                
                            
                        
                        try:
                            
                            url = url_args[0]
                            
                            url_cache.add( url )
                            
                            x_out_of_y = 'file ' + HydrusData.ConvertIntToPrettyString( i ) + '/' + HydrusData.ConvertIntToPrettyString( len( all_url_args ) ) + ': '
                            
                            job_key.SetVariable( 'popup_message_text_1', x_out_of_y + 'checking url status' )
                            job_key.SetVariable( 'popup_message_gauge_1', ( i, len( all_url_args ) ) )
                            
                            if len( successful_hashes ) > 0:
                                
                                job_key_s_h = set( successful_hashes )
                                
                                job_key.SetVariable( 'popup_message_files', job_key_s_h )
                                
                            
                            ( status, hash ) = wx.GetApp().ReadDaemon( 'url_status', url )
                            
                            if status == 'deleted' and 'exclude_deleted_files' not in advanced_import_options: status = 'new'
                            
                            if status == 'redundant':
                                
                                if do_tags:
                                    
                                    try:
                                        
                                        job_key.SetVariable( 'popup_message_text_1', x_out_of_y + 'found file in db, fetching tags' )
                                        
                                        tags = downloader.GetTags( *url_args )
                                        
                                        service_keys_to_tags = ClientDownloading.ConvertTagsToServiceKeysToTags( tags, advanced_tag_options )
                                        
                                        service_keys_to_content_updates = ClientDownloading.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( hash, service_keys_to_tags )
                                        
                                        wx.GetApp().WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                                        
                                    except: pass
                                    
                                
                            elif status == 'new':
                                
                                num_new += 1
                                
                                job_key.SetVariable( 'popup_message_text_1', x_out_of_y + 'downloading file' )
                                
                                ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                                
                                try:
                                    
                                    if do_tags: tags = downloader.GetFileAndTags( temp_path, *url_args )
                                    else:
                                        
                                        downloader.GetFile( temp_path, *url_args )
                                        
                                        tags = []
                                        
                                    
                                    service_keys_to_tags = ClientDownloading.ConvertTagsToServiceKeysToTags( tags, advanced_tag_options )
                                    
                                    job_key.SetVariable( 'popup_message_text_1', x_out_of_y + 'importing file' )
                                    
                                    ( status, hash ) = wx.GetApp().WriteSynchronous( 'import_file', temp_path, advanced_import_options = advanced_import_options, service_keys_to_tags = service_keys_to_tags, url = url )
                                    
                                finally:
                                    
                                    HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                                    
                                
                                if status in ( 'successful', 'redundant' ): successful_hashes.add( hash )
                                
                            
                        except Exception as e:
                            
                            HydrusData.ShowText( 'While trying to execute subscription ' + name + ', the url ' + url + ' caused this problem:' )
                            
                            HydrusData.ShowException( e )
                            
                        
                        if i % 20 == 0:
                            
                            info[ 'site_type' ] = site_type
                            info[ 'query_type' ] = query_type
                            info[ 'query' ] = query
                            info[ 'frequency_type' ] = frequency_type
                            info[ 'frequency' ] = frequency
                            info[ 'advanced_tag_options' ] = advanced_tag_options
                            info[ 'advanced_import_options' ] = advanced_import_options
                            info[ 'last_checked' ] = last_checked
                            info[ 'url_cache' ] = url_cache
                            info[ 'paused' ] = paused
                            
                            wx.GetApp().WriteSynchronous( 'subscription', name, info )
                            
                        
                        wx.GetApp().WaitUntilGoodTimeToUseGUIThread()
                        
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
                
            
        
    