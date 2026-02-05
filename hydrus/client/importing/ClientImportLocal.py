import collections
import collections.abc
import os
import threading
import time

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client import ClientThreading
from hydrus.client.files import ClientFiles
from hydrus.client.importing import ClientImportControl
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import TagImportOptionsLegacy
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientMetadataMigration
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientMetadataMigrationImporters
from hydrus.client.metadata import ClientTags

class HDDImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT
    SERIALISABLE_NAME = 'Local File Import'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, paths = None, file_import_options = None, metadata_routers = None, paths_to_additional_service_keys_to_tags = None, delete_after_success = None ):
        
        super().__init__()
        
        if metadata_routers is None:
            
            metadata_routers = []
            
        
        if paths_to_additional_service_keys_to_tags is None:
            
            paths_to_additional_service_keys_to_tags = collections.defaultdict( ClientTags.ServiceKeysToTags )
            
        
        if delete_after_success is None:
            
            delete_after_success = False
            
        
        if paths is None:
            
            self._file_seed_cache = None
            
        else:
            
            self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
            
            file_seeds = []
            
            for path in paths:
                
                file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_HDD, path )
                
                try:
                    
                    file_modified_time_ms = HydrusFileHandling.GetFileModifiedTimestampMS( path )
                    
                    file_seed.source_time = HydrusTime.SecondiseMS( file_modified_time_ms )
                    
                except Exception as e:
                    
                    pass
                    
                
                if path in paths_to_additional_service_keys_to_tags:
                    
                    file_seed.AddExternalAdditionalServiceKeysToTags( paths_to_additional_service_keys_to_tags[ path ] )
                    
                
                file_seeds.append( file_seed )
                
            
            self._file_seed_cache.AddFileSeeds( file_seeds )
            
        
        self._metadata_routers = HydrusSerialisable.SerialisableList( metadata_routers )
        
        self._file_import_options = file_import_options
        self._delete_after_success = delete_after_success
        
        self._page_key = b'initialising page key'
        
        self._files_status = ''
        self._paused = False
        
        self._lock = threading.Lock()
        
        self._files_repeating_job = None
        
        self._last_serialisable_change_timestamp = 0
        
        CG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        CG.client_controller.sub( self, 'Wake', 'notify_global_page_import_pause_change' )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_options = self._file_import_options.GetSerialisableTuple()
        serialisable_metadata_routers = self._metadata_routers.GetSerialisableTuple()
        
        return ( serialisable_file_seed_cache, serialisable_options, serialisable_metadata_routers, self._delete_after_success, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_file_seed_cache, serialisable_options, serialisable_metadata_routers, self._delete_after_success, self._paused ) = serialisable_info
        
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_options )
        self._metadata_routers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_metadata_routers )
        
    
    def _SerialisableChangeMade( self ):
        
        self._last_serialisable_change_timestamp = HydrusTime.GetNow()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_file_seed_cache, serialisable_options, serialisable_paths_to_tags, delete_after_success, paused ) = old_serialisable_info
            
            file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
            
            paths_to_additional_service_keys_to_tags = { path : { bytes.fromhex( service_key ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in serialisable_paths_to_tags.items() }
            
            for file_seed in file_seed_cache.GetFileSeeds():
                
                path = file_seed.file_seed_data
                
                if path in paths_to_additional_service_keys_to_tags:
                    
                    file_seed.AddExternalAdditionalServiceKeysToTags( paths_to_additional_service_keys_to_tags[ path ] )
                    
                
            
            serialisable_file_seed_cache = file_seed_cache.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_file_seed_cache, serialisable_options, delete_after_success, paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_file_seed_cache, serialisable_options, delete_after_success, paused ) = old_serialisable_info
            
            metadata_routers = HydrusSerialisable.SerialisableList()
            
            serialisable_metadata_routers = metadata_routers.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_file_seed_cache, serialisable_options, serialisable_metadata_routers, delete_after_success, paused )
            
            return ( 3, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        path = file_seed.file_seed_data
        
        with self._lock:
            
            self._files_status = 'importing'
            
        
        def status_hook( text ):
            
            with self._lock:
                
                self._files_status = HydrusText.GetFirstLine( text )
                
            
        
        file_seed.ImportPath( self._file_seed_cache, self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD, status_hook = status_hook )
        
        if file_seed.status in CC.SUCCESSFUL_IMPORT_STATES:
            
            if len( self._metadata_routers ) > 0:
                
                hash = file_seed.GetHash()
                
                media_result = CG.client_controller.Read( 'media_result', hash )
                
                for router in self._metadata_routers:
                    
                    try:
                        
                        router.Work( media_result, file_seed.file_seed_data )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Trying to run metadata routing on the file "{}" threw an error!'.format( file_seed.file_seed_data ) )
                        HydrusData.ShowException( e )
                        
                    
                
            
            real_presentation_import_options = FileImportOptionsLegacy.GetRealPresentationImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
            
            if file_seed.ShouldPresent( real_presentation_import_options ):
                
                file_seed.PresentToPage( self._page_key )
                
            
            if self._delete_after_success:
                
                try:
                    
                    ClientPaths.DeletePath( path )
                    
                except Exception as e:
                    
                    HydrusData.ShowText( 'While attempting to delete {}, the following error occurred:'.format( path ) )
                    HydrusData.ShowException( e )
                    
                
                possible_sidecar_paths = set()
                
                for router in self._metadata_routers:
                    
                    possible_sidecar_paths.update( router.GetPossibleImporterSidecarPaths( path ) )
                    
                
                for possible_sidecar_path in possible_sidecar_paths:
                    
                    if os.path.exists( possible_sidecar_path ):
                        
                        try:
                            
                            ClientPaths.DeletePath( possible_sidecar_path )
                            
                        except Exception as e:
                            
                            HydrusData.ShowText( 'While attempting to delete {}, the following error occurred:'.format( possible_sidecar_path ) )
                            HydrusData.ShowException( e )
                            
                        
                    
            
        
        with self._lock:
            
            self._files_status = ''
            
        
        time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            work_to_do = self._file_seed_cache.WorkToDo()
            
            return work_to_do and not self._paused
            
        
    
    def GetAPIInfoDict( self, simple ):
        
        with self._lock:
            
            d = {}
            
            d[ 'imports' ] = self._file_seed_cache.GetAPIInfoDict( simple )
            
            d[ 'files_paused' ] = self._paused
            
            return d
            
        
    
    def GetFileImportOptions( self ):
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetNumSeeds( self ):
        
        with self._lock:
            
            return len( self._file_seed_cache )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            currently_working = self._files_repeating_job is not None and self._files_repeating_job.CurrentlyWorking()
            
            text = ClientImportControl.GenerateLiveStatusText( self._files_status, self._paused, currently_working, 0, '' )
            
            return ( text, self._paused )
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetValueRange()
            
        
    
    def HasSerialisableChangesSince( self, since_timestamp ):
        
        with self._lock:
            
            return self._last_serialisable_change_timestamp > since_timestamp
            
        
    
    def NotifyFileSeedsUpdated( self, file_seed_cache_key, file_seeds ):
        
        if file_seed_cache_key == self._file_seed_cache.GetFileSeedCacheKey():
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def SetFileImportOptions( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ):
        
        with self._lock:
            
            if file_import_options.DumpToString() != self._file_import_options.DumpToString():
                
                self._file_import_options = file_import_options
                
                self._SerialisableChangeMade()
                
            
        
    
    def Start( self, page_key ):
        
        self._page_key = page_key
        
        self._files_repeating_job = CG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles )
        
        self._files_repeating_job.SetThreadSlotType( 'misc' )
        
    
    def CheckCanDoFileWork( self ):
        
        with self._lock:
            
            try:
                
                ClientImportControl.CheckImporterCanDoWorkBecauseStopped( self._page_key )
                
            except HydrusExceptions.VetoException:
                
                self._files_repeating_job.Cancel()
                
                raise
                
            
            ClientImportControl.CheckImporterCanDoFileWorkBecausePaused( self._paused, self._file_seed_cache, self._page_key )
            
            try:
                
                real_file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
                
                ClientImportControl.CheckImporterCanDoFileWorkBecausePausifyingProblem( real_file_import_options.GetLocationImportOptions() )
                
            except HydrusExceptions.VetoException:
                
                self._paused = True
                
                raise
                
            
        
        return True
        
    
    def REPEATINGWorkOnFiles( self ):
        
        while True:
            
            try:
                
                try:
                    
                    self.CheckCanDoFileWork()
                    
                except HydrusExceptions.VetoException as e:
                    
                    with self._lock:
                        
                        self._files_status = str( e )
                        
                    
                    break
                    
                
                self._WorkOnFiles()
                
                CG.client_controller.WaitUntilViewFree()
                
                self._SerialisableChangeMade()
                
            except Exception as e:
                
                with self._lock:
                    
                    self._files_status = 'stopping work: {}'.format( str( e ) )
                    
                
                HydrusData.ShowException( e )
                
                return
                
            
        
    
    def Wake( self ):
        
        ClientImporting.WakeRepeatingJob( self._files_repeating_job )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT ] = HDDImport

class ImportFolder( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER
    SERIALISABLE_NAME = 'Import Folder'
    SERIALISABLE_VERSION = 10
    
    def __init__(
        self,
        name,
        path = '',
        search_subdirectories = True,
        file_import_options = None,
        tag_import_options = None,
        metadata_routers: collections.abc.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ] = None,
        tag_service_keys_to_filename_tagging_options = None,
        actions = None,
        action_locations = None,
        period = 3600,
        check_regularly = True,
        show_working_popup = True,
        publish_files_to_popup_button = True,
        publish_files_to_page = False
    ):
        
        if file_import_options is None:
            
            file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
            file_import_options.SetIsDefault( True )
            
        
        if tag_import_options is None:
            
            tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy()
            
        
        if metadata_routers is None:
            
            metadata_routers = []
            
        
        metadata_routers = HydrusSerialisable.SerialisableList( metadata_routers )
        
        if tag_service_keys_to_filename_tagging_options is None:
            
            tag_service_keys_to_filename_tagging_options = {}
            
        
        if actions is None:
            
            actions = {}
            
            actions[ CC.STATUS_SUCCESSFUL_AND_NEW ] = CC.IMPORT_FOLDER_IGNORE
            actions[ CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ] = CC.IMPORT_FOLDER_IGNORE
            actions[ CC.STATUS_DELETED ] = CC.IMPORT_FOLDER_IGNORE
            actions[ CC.STATUS_ERROR ] = CC.IMPORT_FOLDER_IGNORE
            
        
        if action_locations is None:
            
            action_locations = {}
            
        
        super().__init__( name )
        
        self._path = path
        self._search_subdirectories = search_subdirectories
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        self._metadata_routers = metadata_routers
        self._tag_service_keys_to_filename_tagging_options = tag_service_keys_to_filename_tagging_options
        self._actions = actions
        self._action_locations = action_locations
        self._period = period
        self._check_regularly = check_regularly
        
        self._last_modified_time_skip_period = 60
        
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        self._last_checked = 0
        self._paused = False
        self._check_now = False
        
        self._show_working_popup = show_working_popup
        self._publish_files_to_popup_button = publish_files_to_popup_button
        self._publish_files_to_page = publish_files_to_page
        
    
    def _ActionSeed( self, file_seed: ClientImportFileSeeds.FileSeed ):
        
        status = file_seed.status
        
        if status not in self._actions:
            
            return
            
        
        action = self._actions[ status ]
        
        path = file_seed.file_seed_data
        
        if action == CC.IMPORT_FOLDER_DELETE:
            
            try:
                
                if os.path.exists( path ) and not os.path.isdir( path ):
                    
                    ClientPaths.DeletePath( path )
                    
                
                possible_sidecar_paths = set()
                
                for router in self._metadata_routers:
                    
                    possible_sidecar_paths.update( router.GetPossibleImporterSidecarPaths( path ) )
                    
                
                for possible_sidecar_path in possible_sidecar_paths:
                    
                    if os.path.exists( possible_sidecar_path ):
                        
                        ClientPaths.DeletePath( possible_sidecar_path )
                        
                    
                
                self._file_seed_cache.RemoveFileSeeds( ( file_seed, ) )
                
            except Exception as e:
                
                raise Exception( 'Tried to delete "{}", but could not.'.format( path ) )
                
            
        elif action == CC.IMPORT_FOLDER_MOVE:
            
            try:
                
                dest_dir = self._action_locations[ status ]
                
                if not os.path.exists( dest_dir ):
                    
                    raise Exception( 'Tried to move "{}" to "{}", but the destination directory did not exist.'.format( path, dest_dir ) )
                    
                
                if os.path.exists( path ) and not os.path.isdir( path ):
                    
                    filename = os.path.basename( path )
                    
                    dest_path = os.path.join( dest_dir, filename )
                    
                    dest_path = HydrusPaths.AppendPathUntilNoConflicts( dest_path )
                    
                    HydrusPaths.MergeFile( path, dest_path )
                    
                
                possible_sidecar_paths = set()
                
                for router in self._metadata_routers:
                    
                    possible_sidecar_paths.update( router.GetPossibleImporterSidecarPaths( path ) )
                    
                
                for possible_sidecar_path in possible_sidecar_paths:
                    
                    if os.path.exists( possible_sidecar_path ):
                        
                        txt_filename = os.path.basename( possible_sidecar_path )
                        
                        txt_dest_path = os.path.join( dest_dir, txt_filename )
                        
                        txt_dest_path = HydrusPaths.AppendPathUntilNoConflicts( txt_dest_path )
                        
                        HydrusPaths.MergeFile( possible_sidecar_path, txt_dest_path )
                        
                    
                
                self._file_seed_cache.RemoveFileSeeds( ( file_seed, ) )
                
            except Exception as e:
                
                HydrusData.ShowText( f'Import folder tried to move "{path}", but it encountered an error:' )
                
                HydrusData.ShowException( e )
                
                HydrusData.ShowText( 'Import folder has been paused.' )
                
                self._paused = True
                
            
        
    
    def _CheckFolder( self, job_status: ClientThreading.JobStatus ):
        
        ( file_paths, sidecar_paths ) = ClientFiles.GetAllFilePaths( self._path, self._search_subdirectories )
        
        paths_to_file_seeds = { path : ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_HDD, path ) for path in file_paths }
        
        new_paths = [ path for ( path, file_seed ) in paths_to_file_seeds.items() if not self._file_seed_cache.HasFileSeed( file_seed ) ]
        
        job_status.SetStatusText( f'checking: found {HydrusNumbers.ToHumanInt( len( new_paths ) )} new files' )
        
        old_new_paths = HydrusPaths.FilterOlderModifiedFiles( new_paths, self._last_modified_time_skip_period )
        
        free_old_new_paths = HydrusPaths.FilterFreePaths( old_new_paths )
        
        file_seeds = [ paths_to_file_seeds[ path ] for path in free_old_new_paths ]
        
        job_status.SetStatusText( f'checking: found {HydrusNumbers.ToHumanInt( len( file_seeds ) )} new files to import' )
        
        self._file_seed_cache.AddFileSeeds( file_seeds )
        
        self._last_checked = HydrusTime.GetNow()
        self._check_now = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        serialisable_metadata_routers = self._metadata_routers.GetSerialisableTuple()
        serialisable_tag_service_keys_to_filename_tagging_options = [ ( service_key.hex(), filename_tagging_options.GetSerialisableTuple() ) for ( service_key, filename_tagging_options ) in list(self._tag_service_keys_to_filename_tagging_options.items()) ]
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        # json turns int dict keys to strings
        action_pairs = list(self._actions.items())
        action_location_pairs = list(self._action_locations.items())
        
        return (
            self._path,
            self._search_subdirectories,
            serialisable_file_import_options,
            serialisable_tag_import_options,
            serialisable_metadata_routers,
            serialisable_tag_service_keys_to_filename_tagging_options,
            action_pairs,
            action_location_pairs,
            self._period,
            self._check_regularly,
            serialisable_file_seed_cache,
            self._last_checked,
            self._paused,
            self._check_now,
            self._last_modified_time_skip_period,
            self._show_working_popup,
            self._publish_files_to_popup_button,
            self._publish_files_to_page
        )
        
    
    def _ImportFiles( self, job_status ):
        
        SAVE_PERIOD = 600
        
        did_work = False
        
        time_to_save = HydrusTime.GetNow() + SAVE_PERIOD
        
        num_files_imported = 0
        presentation_hashes = []
        presentation_hashes_fast = set()
        
        pauser = HydrusThreading.BigJobPauser()
        
        i = 0
        
        # don't want to start at 23/100 because of carrying over failed results or whatever
        # num_to_do is num currently unknown
        num_total = self._file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
        
        file_seed = None
        
        while True:
            
            previous_file_seed = file_seed
            
            file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
            
            p1 = CG.client_controller.new_options.GetBoolean( 'pause_import_folders_sync' ) or self._paused
            p2 = HydrusThreading.IsThreadShuttingDown()
            p3 = job_status.IsCancelled()
            
            if file_seed is None or p1 or p2 or p3:
                
                break
                
            
            if previous_file_seed is not None and previous_file_seed == file_seed:
                
                raise Exception( f'Somehow we did not process the file job: {previous_file_seed.file_seed_data}! Please let hydev know about this.' )
                
            
            did_work = True
            
            if HydrusTime.TimeHasPassed( time_to_save ):
                
                CG.client_controller.WriteSynchronous( 'serialisable', self )
                
                time_to_save = HydrusTime.GetNow() + SAVE_PERIOD
                
            
            job_status.SetStatusText( 'importing: ' + HydrusNumbers.ValueRangeToPrettyString( num_files_imported, num_total ) )
            job_status.SetGauge( num_files_imported, num_total )  
            
            path = file_seed.file_seed_data
            
            try:
                
                file_seed.ImportPath( self._file_seed_cache, self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_QUIET )
                
                if file_seed.status in CC.SUCCESSFUL_IMPORT_STATES:
                    
                    hash = None
                    
                    if file_seed.HasHash():
                        
                        hash = file_seed.GetHash()
                        
                        if self._tag_import_options.HasAdditionalTags() or len( self._metadata_routers ) > 0:
                            
                            media_result = CG.client_controller.Read( 'media_result', hash )
                            
                            if self._tag_import_options.HasAdditionalTags():
                                
                                downloaded_tags = []
                                
                                content_update_package = self._tag_import_options.GetContentUpdatePackage( file_seed.status, media_result, downloaded_tags ) # additional tags
                                
                                if content_update_package.HasContent():
                                    
                                    CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                                    
                                
                            
                            for metadata_router in self._metadata_routers:
                                
                                try:
                                    
                                    metadata_router.Work( media_result, path )
                                    
                                except Exception as e:
                                    
                                    HydrusData.ShowText( 'Trying to run metadata routing in the import folder "' + self._name + '" threw an error!' )
                                    
                                    HydrusData.ShowException( e )
                                    
                                
                            
                        
                        service_keys_to_tags = ClientTags.ServiceKeysToTags()
                        
                        for ( tag_service_key, filename_tagging_options ) in self._tag_service_keys_to_filename_tagging_options.items():
                            
                            if not CG.client_controller.services_manager.ServiceExists( tag_service_key ):
                                
                                continue
                                
                            
                            try:
                                
                                tags = filename_tagging_options.GetTags( tag_service_key, path )
                                
                                if len( tags ) > 0:
                                    
                                    service_keys_to_tags[ tag_service_key ] = tags
                                    
                                
                            except Exception as e:
                                
                                HydrusData.ShowText( 'Trying to parse filename tags in the import folder "' + self._name + '" threw an error!' )
                                
                                HydrusData.ShowException( e )
                                
                            
                        
                        if len( service_keys_to_tags ) > 0:
                            
                            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromServiceKeysToTags( { hash }, service_keys_to_tags )
                            
                            CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                            
                        
                    
                    num_files_imported += 1
                    
                    if hash not in presentation_hashes_fast:
                        
                        real_presentation_import_options = FileImportOptionsLegacy.GetRealPresentationImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
                        
                        if file_seed.ShouldPresent( real_presentation_import_options ):
                            
                            presentation_hashes.append( hash )
                            
                            presentation_hashes_fast.add( hash )
                            
                        
                    
                elif file_seed.status == CC.STATUS_ERROR:
                    
                    HydrusData.Print( f'Import folder "{self._name}" failed to import: "{path}"' )
                    
                
                i += 1
                
            finally:
                
                self._ActionSeed( file_seed )
                
                pauser.Pause()
                
            
        
        if num_files_imported > 0:
            
            HydrusData.Print( 'Import folder ' + self._name + ' imported ' + HydrusNumbers.ToHumanInt( num_files_imported ) + ' files.' )
            
            if len( presentation_hashes ) > 0:
                
                ClientImporting.PublishPresentationHashes( self._name, presentation_hashes, self._publish_files_to_popup_button, self._publish_files_to_page )
                
            
        
        return did_work
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self._path,
            self._search_subdirectories,
            serialisable_file_import_options,
            serialisable_tag_import_options,
            serialisable_metadata_routers,
            serialisable_tag_service_keys_to_filename_tagging_options,
            action_pairs,
            action_location_pairs,
            self._period,
            self._check_regularly,
            serialisable_file_seed_cache,
            self._last_checked,
            self._paused,
            self._check_now,
            self._last_modified_time_skip_period,
            self._show_working_popup,
            self._publish_files_to_popup_button,
            self._publish_files_to_page
        ) = serialisable_info
        
        self._actions = dict( action_pairs )
        self._action_locations = dict( action_location_pairs )
        
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        self._metadata_routers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_metadata_routers )
        self._tag_service_keys_to_filename_tagging_options = dict( [ ( bytes.fromhex( encoded_service_key ), HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filename_tagging_options ) ) for ( encoded_service_key, serialisable_filename_tagging_options ) in serialisable_tag_service_keys_to_filename_tagging_options ] )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( path, mimes, serialisable_file_import_options, action_pairs, action_location_pairs, period, open_popup, tag, serialisable_file_seed_cache, last_checked, paused ) = old_serialisable_info
            
            # edited out tag carry-over to tio due to bit rot
            
            tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy()
            
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, action_pairs, action_location_pairs, period, open_popup, serialisable_file_seed_cache, last_checked, paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, action_pairs, action_location_pairs, period, open_popup, serialisable_file_seed_cache, last_checked, paused ) = old_serialisable_info
            
            serialisable_txt_parse_tag_service_keys = []
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, period, open_popup, serialisable_file_seed_cache, last_checked, paused )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, period, open_popup, serialisable_file_seed_cache, last_checked, paused ) = old_serialisable_info
            
            check_now = False
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, period, open_popup, serialisable_file_seed_cache, last_checked, paused, check_now )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_txt_parse_tag_service_keys, action_pairs, action_location_pairs, period, open_popup, serialisable_file_seed_cache, last_checked, paused, check_now ) = old_serialisable_info
            
            txt_parse_tag_service_keys = [ bytes.fromhex( service_key ) for service_key in serialisable_txt_parse_tag_service_keys ]
            
            tag_service_keys_to_filename_tagging_options = {}
            
            for service_key in txt_parse_tag_service_keys:
                
                filename_tagging_options = TagImportOptionsLegacy.FilenameTaggingOptions()
                
                filename_tagging_options._load_from_neighbouring_txt_files = True
                
                tag_service_keys_to_filename_tagging_options[ service_key ] = filename_tagging_options
                
            
            serialisable_tag_service_keys_to_filename_tagging_options = [ ( service_key.hex(), filename_tagging_options.GetSerialisableTuple() ) for ( service_key, filename_tagging_options ) in list(tag_service_keys_to_filename_tagging_options.items()) ]
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, open_popup, serialisable_file_seed_cache, last_checked, paused, check_now )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, open_popup, serialisable_file_seed_cache, last_checked, paused, check_now ) = old_serialisable_info
            
            check_regularly = not paused
            show_working_popup = True
            publish_files_to_page = False
            publish_files_to_popup_button = open_popup
            
            new_serialisable_info = ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, check_regularly, serialisable_file_seed_cache, last_checked, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( path, mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, check_regularly, serialisable_file_seed_cache, last_checked, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page ) = old_serialisable_info
            
            file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
            
            file_import_options.GetFileFilteringImportOptions().SetAllowedSpecificFiletypes( mimes )
            
            serialisable_file_import_options = file_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( path, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, check_regularly, serialisable_file_seed_cache, last_checked, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( path, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, check_regularly, serialisable_file_seed_cache, last_checked, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page ) = old_serialisable_info
            
            tag_service_keys_to_filename_tagging_options = dict( [ ( bytes.fromhex( encoded_service_key ), HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filename_tagging_options ) ) for ( encoded_service_key, serialisable_filename_tagging_options ) in serialisable_tag_service_keys_to_filename_tagging_options ] )
            
            metadata_routers = HydrusSerialisable.SerialisableList()
            
            try:
                
                for ( service_key, filename_tagging_options ) in tag_service_keys_to_filename_tagging_options.items():
                    
                    # beardy access here, but this is once off
                    if hasattr( filename_tagging_options, '_load_from_neighbouring_txt_files' ) and filename_tagging_options._load_from_neighbouring_txt_files:
                        
                        importers = [ ClientMetadataMigrationImporters.SingleFileMetadataImporterTXT() ]
                        exporter = ClientMetadataMigrationExporters.SingleFileMetadataExporterMediaTags( service_key = service_key )
                        
                        metadata_router = ClientMetadataMigration.SingleFileMetadataRouter( importers = importers, exporter = exporter )
                        
                        metadata_routers.append( metadata_router )
                        
                    
                
            except Exception as e:
                
                HydrusData.Print( 'Failed to update import folder with new metadata routers.' )
                
                HydrusData.PrintException( e )
                
            
            serialisable_metadata_routers = metadata_routers.GetSerialisableTuple()
            
            new_serialisable_info = ( path, serialisable_file_import_options, serialisable_tag_import_options, serialisable_metadata_routers, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, period, check_regularly, serialisable_file_seed_cache, last_checked, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            (
                path,
                serialisable_file_import_options,
                serialisable_tag_import_options,
                serialisable_metadata_routers,
                serialisable_tag_service_keys_to_filename_tagging_options,
                action_pairs,
                action_location_pairs,
                period,
                check_regularly,
                serialisable_file_seed_cache,
                last_checked,
                paused,
                check_now,
                show_working_popup,
                publish_files_to_popup_button,
                publish_files_to_page
            ) = old_serialisable_info
            
            last_modified_time_skip_period = 60
            
            new_serialisable_info = (
                path,
                serialisable_file_import_options,
                serialisable_tag_import_options,
                serialisable_metadata_routers,
                serialisable_tag_service_keys_to_filename_tagging_options,
                action_pairs,
                action_location_pairs,
                period,
                check_regularly,
                serialisable_file_seed_cache,
                last_checked,
                paused,
                check_now,
                last_modified_time_skip_period,
                show_working_popup,
                publish_files_to_popup_button,
                publish_files_to_page
            )
            
            return ( 9, new_serialisable_info )
            
        
        if version == 9:
            
            (
                path,
                serialisable_file_import_options,
                serialisable_tag_import_options,
                serialisable_metadata_routers,
                serialisable_tag_service_keys_to_filename_tagging_options,
                action_pairs,
                action_location_pairs,
                period,
                check_regularly,
                serialisable_file_seed_cache,
                last_checked,
                paused,
                check_now,
                last_modified_time_skip_period,
                show_working_popup,
                publish_files_to_popup_button,
                publish_files_to_page
            ) = old_serialisable_info
            
            search_subdirectories = True
            
            new_serialisable_info = (
                path,
                search_subdirectories,
                serialisable_file_import_options,
                serialisable_tag_import_options,
                serialisable_metadata_routers,
                serialisable_tag_service_keys_to_filename_tagging_options,
                action_pairs,
                action_location_pairs,
                period,
                check_regularly,
                serialisable_file_seed_cache,
                last_checked,
                paused,
                check_now,
                last_modified_time_skip_period,
                show_working_popup,
                publish_files_to_popup_button,
                publish_files_to_page
            )
            
            return ( 10, new_serialisable_info )
            
        
    
    def CheckNow( self ):
        
        self._paused = False
        self._check_now = True
        
    
    def DoWork( self ):
        
        if HG.started_shutdown:
            
            return
            
        
        if CG.client_controller.new_options.GetBoolean( 'pause_import_folders_sync' ) or self._paused:
            
            return
            
        
        checked_folder = False
        
        did_import_file_work = False
        
        error_occured = False
        
        job_status = ClientThreading.JobStatus( pausable = False, cancellable = True )
        
        popup_desired = self._show_working_popup or self._check_now
        
        try:
            
            real_file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_QUIET )
            
            real_file_import_options.GetLocationImportOptions().CheckReadyToImport()
            
            pubbed_job_status = False
            
            job_status.SetStatusTitle( 'import folder - ' + self._name )
            
            due_by_check_now = self._check_now
            due_by_period = self._check_regularly and HydrusTime.TimeHasPassed( self._last_checked + self._period )
            
            if due_by_check_now or due_by_period:
                
                if not os.path.exists( self._path ) or not os.path.isdir( self._path ):
                    
                    raise Exception( 'Path "' + self._path + '" does not seem to exist, or is not a directory.' )
                    
                
                if not pubbed_job_status and popup_desired:
                    
                    CG.client_controller.pub( 'message', job_status )
                    
                    pubbed_job_status = True
                    
                
                self._CheckFolder( job_status )
                
                checked_folder = True
                
                file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
                
                if file_seed is not None:
                    
                    if not pubbed_job_status and popup_desired:
                        
                        CG.client_controller.pub( 'message', job_status )
                        
                        pubbed_job_status = True
                        
                    
                    did_import_file_work = self._ImportFiles( job_status )
                    
                
            
        except Exception as e:
            
            error_occured = True
            self._paused = True
            
            HydrusData.ShowText( 'The import folder "' + self._name + '" encountered an exception! It has been paused!' )
            HydrusData.ShowException( e )
            
        
        if checked_folder or did_import_file_work or error_occured:
            
            CG.client_controller.WriteSynchronous( 'serialisable', self )
            
        
        job_status.FinishAndDismiss()
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetLastModifiedTimeSkipPeriod( self ) -> int:
        
        return self._last_modified_time_skip_period
        
    
    def GetNextWorkTime( self ):
        
        if self._paused:
            
            return None
            
        
        if self._check_now:
            
            return HydrusTime.GetNow()
            
        
        if self._check_regularly:
            
            return self._last_checked + self._period
            
        
        return None
        
    
    def GetMetadataRouters( self ):
        
        return list( self._metadata_routers )
        
    
    def GetSearchSubdirectories( self ) -> bool:
        
        return self._search_subdirectories
        
    
    def Paused( self ):
        
        return self._paused
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def ToListBoxTuple( self ):
        
        return ( self._name, self._path, self._paused, self._check_regularly, self._period )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._file_import_options, self._tag_import_options, self._tag_service_keys_to_filename_tagging_options, self._actions, self._action_locations, self._period, self._check_regularly, self._paused, self._check_now, self._show_working_popup, self._publish_files_to_popup_button, self._publish_files_to_page )
        
    
    def SetFileSeedCache( self, file_seed_cache ):
        
        self._file_seed_cache = file_seed_cache
        
    
    def SetLastModifiedTimeSkipPeriod( self, value: int ):
        
        self._last_modified_time_skip_period = value
        
    
    def SetMetadataRouters( self, metadata_routers: collections.abc.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ] ):
        
        self._metadata_routers = HydrusSerialisable.SerialisableList( metadata_routers )
        
    
    def SetSearchSubdirectories( self, search_subdirectories: bool ):
        
        self._search_subdirectories = search_subdirectories
        
    
    def SetTuple( self, name, path, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page ):
        
        if path != self._path:
            
            self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
            
        
        if not file_import_options.IsDefault() and not self._file_import_options.IsDefault():
            
            file_filtering_import_options = file_import_options.GetFileFilteringImportOptions()
            
            mimes = set( file_filtering_import_options.GetAllowedSpecificFiletypes() )
            
            if mimes != set( self._file_import_options.GetFileFilteringImportOptions().GetAllowedSpecificFiletypes() ):
                
                self._file_seed_cache.RemoveFileSeedsByStatus( ( CC.STATUS_VETOED, ) )
                
            
        
        self._name = name
        self._path = path
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        self._tag_service_keys_to_filename_tagging_options = tag_service_keys_to_filename_tagging_options
        self._actions = actions
        self._action_locations = action_locations
        self._period = period
        self._check_regularly = check_regularly
        self._paused = paused
        self._check_now = check_now
        self._show_working_popup = show_working_popup
        self._publish_files_to_popup_button = publish_files_to_popup_button
        self._publish_files_to_page = publish_files_to_page
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER ] = ImportFolder

class ImportFoldersManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        
        super().__init__( controller, 10 )
        
        self._import_folder_names_fetched = False
        self._import_folder_names_to_next_work_time_cache: dict[ str, int ] = {}
        
        self._controller.sub( self, 'NotifyImportFoldersHaveChanged', 'notify_new_import_folders' )
        
    
    def _DoWork( self ):
        
        if self._controller.new_options.GetBoolean( 'pause_import_folders_sync' ):
            
            return
            
        
        name = self._GetImportFolderNameThatIsDue()
        
        if name is None:
            
            return
            
        
        try:
            
            import_folder = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER, name )
            
        except HydrusExceptions.DBException as e:
            
            if isinstance( e.db_e, HydrusExceptions.DataMissing ):
                
                with self._lock:
                    
                    if name in self._import_folder_names_to_next_work_time_cache:
                        
                        del self._import_folder_names_to_next_work_time_cache[ name ]
                        
                    
                    return
                    
                
            else:
                
                raise
                
            
        
        import_folder.DoWork()
        
        with self._lock:
            
            next_work_time = import_folder.GetNextWorkTime()
            
            if next_work_time is None:
                
                if name in self._import_folder_names_to_next_work_time_cache:
                    
                    del self._import_folder_names_to_next_work_time_cache[ name ]
                    
                
            else:
                
                self._import_folder_names_to_next_work_time_cache[ name ] = max( next_work_time, HydrusTime.GetNow() + 180 )
                
            
        
    
    def _GetImportFolderNameThatIsDue( self ):
        
        if not self._import_folder_names_fetched:
            
            import_folder_names = self._controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
            
            with self._lock:
                
                for name in import_folder_names:
                    
                    self._import_folder_names_to_next_work_time_cache[ name ] = HydrusTime.GetNow()
                    
                
                self._import_folder_names_fetched = True
                
            
        
        with self._lock:
            
            for ( name, time_due ) in self._import_folder_names_to_next_work_time_cache.items():
                
                if HydrusTime.TimeHasPassed( time_due ):
                    
                    return name
                    
                
            
        
        return None
        
    
    def _GetTimeUntilNextWork( self ):
        
        if self._controller.new_options.GetBoolean( 'pause_import_folders_sync' ):
            
            return 1800
            
        
        if not self._import_folder_names_fetched:
            
            return 180
            
        
        if len( self._import_folder_names_to_next_work_time_cache ) == 0:
            
            return 1800
            
        
        next_work_time = min( self._import_folder_names_to_next_work_time_cache.values() )
        
        return max( HydrusTime.TimeUntil( next_work_time ), 1 )
        
    
    def GetName( self ) -> str:
        
        return 'import folders'
        
    
    def _DoMainLoop( self ):
        
        while True:
            
            self._CheckShutdown()
            
            self._controller.WaitUntilViewFree()
            
            try:
                
                HG.import_folders_running = True
                
                self._DoWork()
                
            except Exception as e:
                
                self._serious_error_encountered = True
                
                HydrusData.PrintException( e )
                
                message = 'There was an unexpected problem during import folders work! They will not run again this program boot. A full traceback of this error should be written to the log.'
                message += '\n' * 2
                message += str( e )
                
                HydrusData.ShowText( message )
                
                return
                
            finally:
                
                HG.import_folders_running = False
                
            
            with self._lock:
                
                wait_period = self._GetTimeUntilNextWork()
                
            
            self._wake_from_idle_sleep_event.wait( wait_period )
            
            self._wake_from_work_sleep_event.clear()
            self._wake_from_idle_sleep_event.clear()
            
        
    
    def NotifyImportFoldersHaveChanged( self ):
        
        with self._lock:
            
            self._import_folder_names_fetched = False
            self._import_folder_names_to_next_work_time_cache = {}
            
        
        self.Wake()
        
    
