from . import ClientImporting
from . import ClientImportOptions
from . import ClientImportFileSeeds
from . import ClientPaths
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNATPunch
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusThreading
from . import ClientConstants as CC
import random
import threading
import time
import wx

def DAEMONCheckExportFolders():
    
    controller = HG.client_controller
    
    if not controller.options[ 'pause_export_folders_sync' ]:
        
        HG.export_folders_running = True
        
        try:
            
            export_folder_names = controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
            
            for name in export_folder_names:
                
                export_folder = controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER, name )
                
                if controller.options[ 'pause_export_folders_sync' ] or HydrusThreading.IsThreadShuttingDown():
                    
                    break
                    
                
                export_folder.DoWork()
                
            
        finally:
            
            HG.export_folders_running = False
            
        
    
def DAEMONCheckImportFolders():
    
    controller = HG.client_controller
    
    if not controller.options[ 'pause_import_folders_sync' ]:
        
        HG.import_folders_running = True
        
        try:
            
            import_folder_names = controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            
            for name in import_folder_names:
                
                import_folder = controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER, name )
                
                if controller.options[ 'pause_import_folders_sync' ] or HydrusThreading.IsThreadShuttingDown():
                    
                    break
                    
                
                import_folder.DoWork()
                
            
        finally:
            
            HG.import_folders_running = False
            
        
    
def DAEMONDownloadFiles( controller ):
    
    hashes = controller.Read( 'downloads' )
    
    num_downloads = len( hashes )
    
    if num_downloads > 0:
        
        client_files_manager = controller.client_files_manager
        
        successful_hashes = set()
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', 'initialising downloader' )
        
        controller.pub( 'message', job_key )
        
        for hash in hashes:
            
            job_key.SetVariable( 'popup_text_1', 'downloading ' + HydrusData.ToHumanInt( num_downloads - len( successful_hashes ) ) + ' files from repositories' )
            
            ( media_result, ) = controller.Read( 'media_results', ( hash, ) )
            
            service_keys = list( media_result.GetLocationsManager().GetCurrent() )
            
            random.shuffle( service_keys )
            
            for service_key in service_keys:
                
                if service_key == CC.LOCAL_FILE_SERVICE_KEY: break
                elif service_key == CC.TRASH_SERVICE_KEY: continue
                
                try:
                    
                    service = controller.services_manager.GetService( service_key )
                    
                except:
                    
                    continue
                    
                
                if service.GetServiceType() == HC.FILE_REPOSITORY:
                    
                    file_repository = service
                    
                    if file_repository.IsFunctional():
                        
                        try:
                            
                            ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                            
                            try:
                                
                                file_repository.Request( HC.GET, 'file', { 'hash' : hash }, temp_path = temp_path )
                                
                                controller.WaitUntilModelFree()
                                
                                exclude_deleted = False # this is the important part here
                                do_not_check_known_urls_before_importing = False
                                do_not_check_hashes_before_importing = False
                                allow_decompression_bombs = True
                                min_size = None
                                max_size = None
                                max_gif_size = None
                                min_resolution = None
                                max_resolution = None
                                automatic_archive = False
                                associate_source_urls = True
                                
                                file_import_options = ClientImportOptions.FileImportOptions()
                                
                                file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
                                file_import_options.SetPostImportOptions( automatic_archive, associate_source_urls )
                                
                                file_import_job = ClientImportFileSeeds.FileImportJob( temp_path, file_import_options )
                                
                                file_import_job.DoWork()
                                
                                successful_hashes.add( hash )
                                
                                break
                                
                            finally:
                                
                                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                                
                            
                        except HydrusExceptions.ServerBusyException:
                            
                            job_key.SetVariable( 'popup_text_1', file_repository.GetName() + ' was busy. waiting 30s before trying again' )
                            
                            time.sleep( 30 )
                            
                            job_key.Delete()
                            
                            controller.pub( 'notify_new_downloads' )
                            
                            return
                            
                        except Exception as e:
                            
                            HydrusData.ShowText( 'Error downloading file!' )
                            HydrusData.ShowException( e )
                            
                        
                    
                elif service.GetServiceType() == HC.IPFS:
                    
                    multihashes = HG.client_controller.Read( 'service_filenames', service_key, { hash } )
                    
                    if len( multihashes ) > 0:
                        
                        multihash = multihashes[0]
                        
                        # this actually calls to a thread that can launch gui 'select from tree' stuff, so let's just break at this point
                        wx.CallAfter( service.ImportFile, multihash )
                        
                        break
                        
                    
                
                if HydrusThreading.IsThreadShuttingDown():
                    
                    return
                    
                
            
        
        if len( successful_hashes ) > 0:
            
            job_key.SetVariable( 'popup_text_1', HydrusData.ToHumanInt( len( successful_hashes ) ) + ' files downloaded' )
            
        
        job_key.Delete()
        
    
def DAEMONMaintainTrash( controller ):
    
    if HC.options[ 'trash_max_size' ] is not None:
        
        max_size = HC.options[ 'trash_max_size' ] * 1048576
        
        service_info = controller.Read( 'service_info', CC.TRASH_SERVICE_KEY )
        
        while service_info[ HC.SERVICE_INFO_TOTAL_SIZE ] > max_size:
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            hashes = controller.Read( 'trash_hashes', limit = 10 )
            
            if len( hashes ) == 0:
                
                return
                
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
            
            service_keys_to_content_updates = { CC.TRASH_SERVICE_KEY : [ content_update ] }
            
            controller.WaitUntilModelFree()
            
            controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            service_info = controller.Read( 'service_info', CC.TRASH_SERVICE_KEY )
            
            time.sleep( 2 )
            
        
    
    if HC.options[ 'trash_max_age' ] is not None:
        
        max_age = HC.options[ 'trash_max_age' ] * 3600
        
        hashes = controller.Read( 'trash_hashes', limit = 10, minimum_age = max_age )
        
        while len( hashes ) > 0:
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
            
            service_keys_to_content_updates = { CC.TRASH_SERVICE_KEY : [ content_update ] }
            
            controller.WaitUntilModelFree()
            
            controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            hashes = controller.Read( 'trash_hashes', limit = 10, minimum_age = max_age )
            
            time.sleep( 2 )
            
        
    
def DAEMONSynchroniseRepositories( controller ):
    
    if not controller.options[ 'pause_repo_sync' ]:
        
        services = controller.services_manager.GetServices( HC.REPOSITORIES )
        
        for service in services:
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            if controller.options[ 'pause_repo_sync' ]:
                
                return
                
            
            service.Sync( maintenance_mode = HC.MAINTENANCE_IDLE )
            
            if HydrusThreading.IsThreadShuttingDown():
                
                return
                
            
            time.sleep( 3 )
            
        
    

class SubscriptionJob( object ):
    
    def __init__( self, controller, name ):
        
        self._controller = controller
        self._name = name
        self._job_done = threading.Event()
        
    
    def _DoWork( self ):
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "' + self._name + '" about to start.' )
            
        
        subscription = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION, self._name )
        
        subscription.Sync()
        
    
    def IsDone( self ):
        
        return self._job_done.is_set()
        
    
    def Work( self ):
        
        try:
            
            self._DoWork()
            
        finally:
            
            self._job_done.set()
            
        
    
def DAEMONSynchroniseSubscriptions( controller ):
    
    def filter_finished_jobs( subs_jobs ):
        
        done_indices = [ i for ( i, ( thread, job ) ) in enumerate( subs_jobs ) if job.IsDone() ]
        
        done_indices.reverse()
        
        for i in done_indices:
            
            del subs_jobs[ i ]
            
        
    
    def wait_for_free_slot( controller, subs_jobs, max_simultaneous_subscriptions ):
        
        time.sleep( 0.1 )
        
        while True:
            
            p1 = controller.options[ 'pause_subs_sync' ]
            p2 = HydrusThreading.IsThreadShuttingDown()
            
            if p1 or p2:
                
                if HG.subscription_report_mode:
                    
                    HydrusData.ShowText( 'Subscriptions cancelling. Global sub pause is ' + str( p1 ) + ' and sub daemon thread shutdown status is ' + str( p2 ) + '.' )
                    
                
                if p2:
                    
                    for ( thread, job ) in subs_jobs:
                        
                        HydrusThreading.ShutdownThread( thread )
                        
                    
                
                raise HydrusExceptions.CancelledException( 'subs cancelling or thread shutting down' )
                
            
            filter_finished_jobs( subs_jobs )
            
            if len( subs_jobs ) < max_simultaneous_subscriptions:
                
                return
                
            
            time.sleep( 1.0 )
            
        
    
    def wait_for_all_finished( subs_jobs ):
        
        while True:
            
            filter_finished_jobs( subs_jobs )
            
            if len( subs_jobs ) == 0:
                
                return
                
            
            time.sleep( 1.0 )
            
        
    
    if HG.subscription_report_mode:
        
        HydrusData.ShowText( 'Subscription daemon started a run.' )
        
    
    subscription_names = list( controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ) )
    
    if controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
        
        random.shuffle( subscription_names )
        
    else:
        
        subscription_names.sort()
        
    
    HG.subscriptions_running = True
    
    subs_jobs = []
    
    try:
        
        for name in subscription_names:
            
            max_simultaneous_subscriptions = controller.new_options.GetInteger( 'max_simultaneous_subscriptions' )
            
            try:
                
                wait_for_free_slot( controller, subs_jobs, max_simultaneous_subscriptions )
                
            except HydrusExceptions.CancelledException:
                
                break
                
            
            job = SubscriptionJob( controller, name )
            
            thread = threading.Thread( target = job.Work, name = 'subscription thread' )
            
            thread.start()
            
            subs_jobs.append( ( thread, job ) )
            
        
        wait_for_all_finished( subs_jobs )
        
    finally:
        
        HG.subscriptions_running = False
        
    
