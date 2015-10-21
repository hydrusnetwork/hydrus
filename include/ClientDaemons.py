import ClientDownloading
import ClientFiles
import collections
import hashlib
import httplib
import itertools
import HydrusConstants as HC
import HydrusData
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
import HydrusGlobals

def DAEMONCheckExportFolders():
    
    options = HydrusGlobals.client_controller.GetOptions()
    
    if not options[ 'pause_export_folders_sync' ]:
        
        export_folders = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
        
        for export_folder in export_folders:
            
            if options[ 'pause_export_folders_sync' ]:
                
                break
                
            
            export_folder.DoWork()
            
        
    
def DAEMONCheckImportFolders():
    
    options = HydrusGlobals.client_controller.GetOptions()
    
    if not options[ 'pause_import_folders_sync' ]:
        
        import_folders = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
        
        for import_folder in import_folders:
            
            if options[ 'pause_import_folders_sync' ]:
                
                break
                
            
            import_folder.DoWork()
            
        
    
def DAEMONDownloadFiles():
    
    hashes = HydrusGlobals.client_controller.Read( 'downloads' )
    
    num_downloads = len( hashes )
    
    if num_downloads > 0:
        
        successful_hashes = set()
        
        job_key = HydrusThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', 'initialising downloader' )
        
        HydrusGlobals.client_controller.pub( 'message', job_key )
        
        for hash in hashes:
            
            job_key.SetVariable( 'popup_text_1', 'downloading ' + HydrusData.ConvertIntToPrettyString( num_downloads - len( successful_hashes ) ) + ' files from repositories' )
            
            ( media_result, ) = HydrusGlobals.client_controller.Read( 'media_results', CC.COMBINED_FILE_SERVICE_KEY, ( hash, ) )
            
            service_keys = list( media_result.GetLocationsManager().GetCurrent() )
            
            random.shuffle( service_keys )
            
            for service_key in service_keys:
                
                if service_key == CC.LOCAL_FILE_SERVICE_KEY: break
                elif service_key == CC.TRASH_SERVICE_KEY: continue
                
                try: file_repository = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
                except HydrusExceptions.NotFoundException: continue
                
                if file_repository.CanDownload(): 
                    
                    try:
                        
                        request_args = { 'hash' : hash.encode( 'hex' ) }
                        
                        ( os_file_handle, temp_path ) = HydrusFileHandling.GetTempPath()
                        
                        try:
                            
                            file_repository.Request( HC.GET, 'file', request_args = request_args, temp_path = temp_path )
                            
                            HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
                            
                            HydrusGlobals.client_controller.WriteSynchronous( 'import_file', temp_path, override_deleted = True )
                            
                            successful_hashes.add( hash )
                            
                            break
                            
                        finally:
                            
                            HydrusFileHandling.CleanUpTempPath( os_file_handle, temp_path )
                            
                        
                    except HydrusExceptions.ServerBusyException:
                        
                        job_key.SetVariable( 'popup_text_1', file_repository.GetName() + ' was busy. waiting 30s before trying again' )
                        
                        time.sleep( 30 )
                        
                        job_key.Delete()
                        
                        HydrusGlobals.client_controller.pub( 'notify_new_downloads' )
                        
                        return
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Error downloading file!' )
                        HydrusData.ShowException( e )
                        
                    
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return
                    
                
            
        
        if len( successful_hashes ) > 0:
            
            job_key.SetVariable( 'popup_text_1', HydrusData.ConvertIntToPrettyString( len( successful_hashes ) ) + ' files downloaded' )
            
        else:
            
            job_key.SetVariable( 'popup_text_1', 'all files failed to download' )
            
        
        job_key.Delete()
        
    
def DAEMONFlushServiceUpdates( list_of_service_keys_to_service_updates ):
    
    service_keys_to_service_updates = HydrusData.MergeKeyToListDicts( list_of_service_keys_to_service_updates )
    
    HydrusGlobals.client_controller.WriteSynchronous( 'service_updates', service_keys_to_service_updates )
    
def DAEMONMaintainTrash():
    
    if HC.options[ 'trash_max_size' ] is not None:
        
        max_size = HC.options[ 'trash_max_size' ] * 1048576
        
        service_info = HydrusGlobals.client_controller.Read( 'service_info', CC.TRASH_SERVICE_KEY )
        
        while service_info[ HC.SERVICE_INFO_TOTAL_SIZE ] > max_size:
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            hashes = HydrusGlobals.client_controller.Read( 'oldest_trash_hashes' )
            
            if len( hashes ) == 0:
                
                return
                
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
            
            service_keys_to_content_updates = { CC.TRASH_SERVICE_KEY : [ content_update ] }
            
            HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
            
            HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            service_info = HydrusGlobals.client_controller.Read( 'service_info', CC.TRASH_SERVICE_KEY )
            
        
    
    if HC.options[ 'trash_max_age' ] is not None:
        
        max_age = HC.options[ 'trash_max_age' ] * 3600
        
        hashes = HydrusGlobals.client_controller.Read( 'oldest_trash_hashes', minimum_age = max_age )
        
        while len( hashes ) > 0:
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
            
            service_keys_to_content_updates = { CC.TRASH_SERVICE_KEY : [ content_update ] }
            
            HydrusGlobals.client_controller.WaitUntilPubSubsEmpty()
            
            HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            hashes = HydrusGlobals.client_controller.Read( 'oldest_trash_hashes', minimum_age = max_age )
            
        
    
def DAEMONSynchroniseAccounts():
    
    services = HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.RESTRICTED_SERVICES )
    
    options = HydrusGlobals.client_controller.GetOptions()
    
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
                
                HydrusGlobals.client_controller.WriteSynchronous( 'service_updates', { service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, account ) ] } )
                
                do_notify = True
                
            except Exception as e:
                
                print( 'Failed to refresh account for ' + service.GetName() + ':' )
                
                print( traceback.format_exc() )
                
            
        
    
    if do_notify:
        
        HydrusGlobals.client_controller.pub( 'notify_new_permissions' )
        
    
def DAEMONSynchroniseRepositories():
    
    options = HydrusGlobals.client_controller.GetOptions()
    
    if not options[ 'pause_repo_sync' ]:
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.REPOSITORIES )
        
        for service in services:
            
            if options[ 'pause_repo_sync' ]:
                
                break
                
            
            if HydrusGlobals.client_controller.CurrentlyIdle():
                
                service.Sync( only_when_idle = True )
                
            
        
        time.sleep( 5 )
        
    
def DAEMONSynchroniseSubscriptions():
    
    options = HydrusGlobals.client_controller.GetOptions()
    
    subscription_names = HydrusGlobals.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION )
    
    for name in subscription_names:
        
        p1 = options[ 'pause_subs_sync' ]
        p2 = HydrusGlobals.view_shutdown
        
        if p1 or p2:
            
            return
            
        
        subscription = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION, name )
        
        subscription.Sync()
        
    
def DAEMONUPnP():
    
    try:
        
        local_ip = HydrusNATPunch.GetLocalIP()
        
        current_mappings = HydrusNATPunch.GetUPnPMappings()
        
        our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_ip_address, external_port, protocol, enabled ) in current_mappings }
        
    except: return # This IGD probably doesn't support UPnP, so don't spam the user with errors they can't fix!
    
    services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.LOCAL_BOORU, ) )
    
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
                
            
        
    