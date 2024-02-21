import collections
import os
import threading
import time
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFileHandling

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientFiles
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientPaths
from hydrus.client import ClientThreading
from hydrus.client.importing import ClientImportControl
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientMetadataMigration
from hydrus.client.metadata import ClientMetadataMigrationExporters
from hydrus.client.metadata import ClientMetadataMigrationImporters
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearch

class HDDImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT
    SERIALISABLE_NAME = 'Local File Import'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, paths = None, file_import_options = None, metadata_routers = None, paths_to_additional_service_keys_to_tags = None, delete_after_success = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
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
                    
                except:
                    
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
                
                self._files_status = ClientImportControl.NeatenStatusText( text )
                
            
        
        file_seed.ImportPath( self._file_seed_cache, self._file_import_options, FileImportOptions.IMPORT_TYPE_LOUD, status_hook = status_hook )
        
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
                        
                    
                
            
            real_presentation_import_options = FileImportOptions.GetRealPresentationImportOptions( self._file_import_options, FileImportOptions.IMPORT_TYPE_LOUD )
            
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
            
        
    
    def SetFileImportOptions( self, file_import_options: FileImportOptions.FileImportOptions ):
        
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
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT ] = HDDImport

class ImportFolder( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER
    SERIALISABLE_NAME = 'Import Folder'
    SERIALISABLE_VERSION = 9
    
    def __init__(
        self,
        name,
        path = '',
        file_import_options = None,
        tag_import_options = None,
        metadata_routers: typing.Optional[ typing.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ] ] = None,
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
            
            file_import_options = FileImportOptions.FileImportOptions()
            file_import_options.SetIsDefault( True )
            
        
        if tag_import_options is None:
            
            tag_import_options = TagImportOptions.TagImportOptions()
            
        
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
            
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._path = path
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
        
    
    def _ActionPaths( self ):
        
        for status in ( CC.STATUS_SUCCESSFUL_AND_NEW, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, CC.STATUS_DELETED, CC.STATUS_ERROR ):
            
            action = self._actions[ status ]
            
            if action == CC.IMPORT_FOLDER_DELETE:
                
                while True:
                    
                    file_seed = self._file_seed_cache.GetNextFileSeed( status )
                    
                    if file_seed is None or HG.started_shutdown:
                        
                        break
                        
                    
                    path = file_seed.file_seed_data
                    
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
                
                while True:
                    
                    file_seed = self._file_seed_cache.GetNextFileSeed( status )
                    
                    if file_seed is None or HG.started_shutdown:
                        
                        break
                        
                    
                    path = file_seed.file_seed_data
                    
                    try:
                        
                        dest_dir = self._action_locations[ status ]
                        
                        if not os.path.exists( dest_dir ):
                            
                            raise Exception( 'Tried to move "{}" to "{}", but the destination directory did not exist.'.format( path, dest_dir ) )
                            
                        
                        if os.path.exists( path ) and not os.path.isdir( path ):
                            
                            filename = os.path.basename( path )
                            
                            dest_path = os.path.join( dest_dir, filename )
                            
                            dest_path = HydrusPaths.AppendPathUntilNoConflicts( dest_path )
                            
                            HydrusPaths.MergeFile( path, dest_path )
                            
                        
                        txt_path = path + '.txt'
                        
                        if os.path.exists( txt_path ):
                            
                            txt_filename = os.path.basename( txt_path )
                            
                            txt_dest_path = os.path.join( dest_dir, txt_filename )
                            
                            txt_dest_path = HydrusPaths.AppendPathUntilNoConflicts( txt_dest_path )
                            
                            HydrusPaths.MergeFile( txt_path, txt_dest_path )
                            
                        
                        self._file_seed_cache.RemoveFileSeeds( ( file_seed, ) )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( f'Import folder tried to move "{path}", but it encountered an error:' )
                        
                        HydrusData.ShowException( e )
                        
                        HydrusData.ShowText( 'Import folder has been paused.' )
                        
                        self._paused = True
                        
                        return
                        
                    
                
            elif status == CC.IMPORT_FOLDER_IGNORE:
                
                file_seeds = self._file_seed_cache.GetFileSeeds( status )
                
                for file_seed in file_seeds:
                    
                    path = file_seed.file_seed_data
                    
                    try:
                        
                        if not os.path.exists( path ):
                            
                            self._file_seed_cache.RemoveFileSeeds( ( file_seed, ) )
                            
                        
                    except Exception as e:
                        
                        raise Exception( 'Tried to check existence of "{}", but could not.'.format( path ) ) from e
                        
                    
                
            
        
    
    def _CheckFolder( self, job_status: ClientThreading.JobStatus ):
        
        ( all_paths, num_sidecars ) = ClientFiles.GetAllFilePaths( [ self._path ] )
        
        paths_to_file_seeds = { path : ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_HDD, path ) for path in all_paths }
        
        new_paths = [ path for ( path, file_seed ) in paths_to_file_seeds.items() if not self._file_seed_cache.HasFileSeed( file_seed ) ]
        
        job_status.SetStatusText( f'checking: found {HydrusData.ToHumanInt( len( new_paths ) )} new files' )
        
        old_new_paths = HydrusPaths.FilterOlderModifiedFiles( new_paths, self._last_modified_time_skip_period )
        
        free_old_new_paths = HydrusPaths.FilterFreePaths( old_new_paths )
        
        file_seeds = [ paths_to_file_seeds[ path ] for path in free_old_new_paths ]
        
        job_status.SetStatusText( f'checking: found {HydrusData.ToHumanInt( len( file_seeds ) )} new files to import' )
        
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
        
        did_work = False
        
        time_to_save = HydrusTime.GetNow() + 600
        
        num_files_imported = 0
        presentation_hashes = []
        presentation_hashes_fast = set()
        
        i = 0
        
        # don't want to start at 23/100 because of carrying over failed results or whatever
        # num_to_do is num currently unknown
        num_total = self._file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
        
        while True:
            
            file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
            
            p1 = CG.client_controller.new_options.GetBoolean( 'pause_import_folders_sync' ) or self._paused
            p2 = HydrusThreading.IsThreadShuttingDown()
            p3 = job_status.IsCancelled()
            
            if file_seed is None or p1 or p2 or p3:
                
                break
                
            
            did_work = True
            
            if HydrusTime.TimeHasPassed( time_to_save ):
                
                CG.client_controller.WriteSynchronous( 'serialisable', self )
                
                time_to_save = HydrusTime.GetNow() + 600
                
            
            gauge_num_done = num_files_imported + 1
            
            job_status.SetStatusText( 'importing file ' + HydrusData.ConvertValueRangeToPrettyString( gauge_num_done, num_total ) )
            job_status.SetVariable( 'popup_gauge_1', ( gauge_num_done, num_total ) )
            
            path = file_seed.file_seed_data
            
            file_seed.ImportPath( self._file_seed_cache, self._file_import_options, FileImportOptions.IMPORT_TYPE_QUIET )
            
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
                    
                    real_presentation_import_options = FileImportOptions.GetRealPresentationImportOptions( self._file_import_options, FileImportOptions.IMPORT_TYPE_LOUD )
                    
                    if file_seed.ShouldPresent( real_presentation_import_options ):
                        
                        presentation_hashes.append( hash )
                        
                        presentation_hashes_fast.add( hash )
                        
                    
                
            elif file_seed.status == CC.STATUS_ERROR:
                
                HydrusData.Print( 'A file failed to import from import folder ' + self._name + ':' + path )
                
            
            i += 1
            
            if i % 10 == 0:
                
                self._ActionPaths()
                
            
        
        if num_files_imported > 0:
            
            HydrusData.Print( 'Import folder ' + self._name + ' imported ' + HydrusData.ToHumanInt( num_files_imported ) + ' files.' )
            
            if len( presentation_hashes ) > 0:
                
                ClientImporting.PublishPresentationHashes( self._name, presentation_hashes, self._publish_files_to_popup_button, self._publish_files_to_page )
                
            
        
        self._ActionPaths()
        
        return did_work
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self._path,
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
            
            tag_import_options = TagImportOptions.TagImportOptions()
            
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
                
                filename_tagging_options = TagImportOptions.FilenameTaggingOptions()
                
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
            
            file_import_options.SetAllowedSpecificFiletypes( mimes )
            
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
        
        stop_time = HydrusTime.GetNow() + 3600
        
        job_status = ClientThreading.JobStatus( pausable = False, cancellable = True, stop_time = stop_time )
        
        popup_desired = self._show_working_popup or self._check_now
        
        try:
            
            real_file_import_options = FileImportOptions.GetRealFileImportOptions( self._file_import_options, FileImportOptions.IMPORT_TYPE_QUIET )
            
            real_file_import_options.CheckReadyToImport()
            
            if not os.path.exists( self._path ) or not os.path.isdir( self._path ):
                
                raise Exception( 'Path "' + self._path + '" does not seem to exist, or is not a directory.' )
                
            
            pubbed_job_status = False
            
            job_status.SetStatusTitle( 'import folder - ' + self._name )
            
            due_by_check_now = self._check_now
            due_by_period = self._check_regularly and HydrusTime.TimeHasPassed( self._last_checked + self._period )
            
            if due_by_check_now or due_by_period:
                
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
        
    
    def GetMetadataRouters( self ):
        
        return list( self._metadata_routers )
        
    
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
        
    
    def SetMetadataRouters( self, metadata_routers: typing.Collection[ ClientMetadataMigration.SingleFileMetadataRouter ] ):
        
        self._metadata_routers = HydrusSerialisable.SerialisableList( metadata_routers )
        
    
    def SetTuple( self, name, path, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page ):
        
        if path != self._path:
            
            self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
            
        
        if not file_import_options.IsDefault() and not self._file_import_options.IsDefault():
            
            mimes = set( file_import_options.GetAllowedSpecificFiletypes() )
            
            if mimes != set( self._file_import_options.GetAllowedSpecificFiletypes() ):
                
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
