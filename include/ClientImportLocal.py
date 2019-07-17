from . import ClientConstants as CC
from . import ClientData
from . import ClientFiles
from . import ClientImporting
from . import ClientImportFileSeeds
from . import ClientImportOptions
from . import ClientPaths
from . import ClientTags
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusPaths
from . import HydrusSerialisable
from . import HydrusThreading
import os
import threading
import time

class HDDImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT
    SERIALISABLE_NAME = 'Local File Import'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, paths = None, file_import_options = None, paths_to_service_keys_to_tags = None, delete_after_success = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        if paths is None:
            
            self._file_seed_cache = None
            
        else:
            
            self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
            
            file_seeds = []
            
            for path in paths:
                
                file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_HDD, path )
                
                try:
                    
                    s = os.stat( path )
                    
                    file_seed.source_time = int( min( s.st_mtime, s.st_ctime ) )
                    
                except:
                    
                    pass
                    
                
                if path in paths_to_service_keys_to_tags:
                    
                    file_seed.SetFixedServiceKeysToTags( paths_to_service_keys_to_tags[ path ] )
                    
                
                file_seeds.append( file_seed )
                
            
            self._file_seed_cache.AddFileSeeds( file_seeds )
            
        
        self._file_import_options = file_import_options
        self._delete_after_success = delete_after_success
        
        self._current_action = ''
        self._paused = False
        
        self._lock = threading.Lock()
        
        self._files_repeating_job = None
        
        HG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_options = self._file_import_options.GetSerialisableTuple()
        
        return ( serialisable_file_seed_cache, serialisable_options, self._delete_after_success, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_file_seed_cache, serialisable_options, self._delete_after_success, self._paused ) = serialisable_info
        
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_file_seed_cache, serialisable_options, serialisable_paths_to_tags, delete_after_success, paused ) = old_serialisable_info
            
            file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
            
            paths_to_service_keys_to_tags = { path : { bytes.fromhex( service_key ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in serialisable_paths_to_tags.items() }
            
            for file_seed in file_seed_cache.GetFileSeeds():
                
                path = file_seed.file_seed_data
                
                if path in paths_to_service_keys_to_tags:
                    
                    file_seed.SetFixedServiceKeysToTags( paths_to_service_keys_to_tags[ path ] )
                    
                
            
            serialisable_file_seed_cache = file_seed_cache.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_file_seed_cache, serialisable_options, delete_after_success, paused )
            
            return ( 2, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        path = file_seed.file_seed_data
        
        with self._lock:
            
            self._current_action = 'importing'
            
        
        file_seed.ImportPath( self._file_seed_cache, self._file_import_options )
        
        did_substantial_work = True
        
        if file_seed.status in CC.SUCCESSFUL_IMPORT_STATES:
            
            if file_seed.ShouldPresent( self._file_import_options ):
                
                file_seed.PresentToPage( page_key )
                
                did_substantial_work = True
                
            
            if self._delete_after_success:
                
                try:
                    
                    ClientPaths.DeletePath( path )
                    
                except Exception as e:
                    
                    HydrusData.ShowText( 'While attempting to delete ' + path + ', the following error occurred:' )
                    HydrusData.ShowException( e )
                    
                
                txt_path = path + '.txt'
                
                if os.path.exists( txt_path ):
                    
                    try:
                        
                        ClientPaths.DeletePath( txt_path )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'While attempting to delete ' + txt_path + ', the following error occurred:' )
                        HydrusData.ShowException( e )
                        
                    
                
            
        
        with self._lock:
            
            self._current_action = ''
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            work_to_do = self._file_seed_cache.WorkToDo()
            
            return work_to_do and not self._paused
            
        
    
    def GetFileImportOptions( self ):
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._current_action, self._paused )
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetValueRange()
            
        
    
    def NotifyFileSeedsUpdated( self, file_seed_cache_key, file_seeds ):
        
        if file_seed_cache_key == self._file_seed_cache.GetFileSeedCacheKey():
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def Start( self, page_key ):
        
        self._files_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles, page_key )
        
        self._files_repeating_job.SetThreadSlotType( 'misc' )
        
    
    def REPEATINGWorkOnFiles( self, page_key ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( page_key ):
                
                self._files_repeating_job.Cancel()
                
                return
                
            
            paused = self._paused or HG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' )
            
            work_to_do = self._file_seed_cache.WorkToDo() and not ( paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
            
        
        while work_to_do:
            
            try:
                
                self._WorkOnFiles( page_key )
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if ClientImporting.PageImporterShouldStopWorking( page_key ):
                    
                    self._files_repeating_job.Cancel()
                    
                    return
                    
                
                paused = self._paused or HG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' )
                
                work_to_do = self._file_seed_cache.WorkToDo() and not ( paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT ] = HDDImport

class ImportFolder( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER
    SERIALISABLE_NAME = 'Import Folder'
    SERIALISABLE_VERSION = 6
    
    def __init__( self, name, path = '', file_import_options = None, tag_import_options = None, tag_service_keys_to_filename_tagging_options = None, mimes = None, actions = None, action_locations = None, period = 3600, check_regularly = True, show_working_popup = True, publish_files_to_popup_button = True, publish_files_to_page = False ):
        
        if mimes is None:
            
            mimes = HC.ALLOWED_MIMES
            
        
        if file_import_options is None:
            
            file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'quiet' )
            
        
        if tag_import_options is None:
            
            tag_import_options = ClientImportOptions.TagImportOptions()
            
        
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
        self._mimes = mimes
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        self._tag_service_keys_to_filename_tagging_options = tag_service_keys_to_filename_tagging_options
        self._actions = actions
        self._action_locations = action_locations
        self._period = period
        self._check_regularly = check_regularly
        
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
                    
                    if file_seed is None or HG.view_shutdown:
                        
                        break
                        
                    
                    path = file_seed.file_seed_data
                    
                    try:
                        
                        if os.path.exists( path ) and not os.path.isdir( path ):
                            
                            ClientPaths.DeletePath( path )
                            
                        
                        txt_path = path + '.txt'
                        
                        if os.path.exists( txt_path ):
                            
                            ClientPaths.DeletePath( txt_path )
                            
                        
                        self._file_seed_cache.RemoveFileSeeds( ( file_seed, ) )
                        
                    except Exception as e:
                        
                        raise Exception( 'Tried to delete "{}", but could not.'.format( path ) )
                        
                    
                
            elif action == CC.IMPORT_FOLDER_MOVE:
                
                while True:
                    
                    file_seed = self._file_seed_cache.GetNextFileSeed( status )
                    
                    if file_seed is None or HG.view_shutdown:
                        
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
                        
                        HydrusData.ShowText( 'Import folder tried to move ' + path + ', but could not:' )
                        
                        HydrusData.ShowException( e )
                        
                        HydrusData.ShowText( 'Import folder has been paused.' )
                        
                        self._paused = True
                        
                        return
                        
                    
                
            elif status == CC.IMPORT_FOLDER_IGNORE:
                
                pass
                
            
        
    
    def _CheckFolder( self, job_key ):
        
        all_paths = ClientFiles.GetAllFilePaths( [ self._path ] )
        
        all_paths = HydrusPaths.FilterFreePaths( all_paths )
        
        file_seeds = []
        
        for path in all_paths:
            
            if job_key.IsCancelled():
                
                break
                
            
            if path.endswith( '.txt' ):
                
                continue
                
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_HDD, path )
            
            if not self._file_seed_cache.HasFileSeed( file_seed ):
                
                file_seeds.append( file_seed )
                
            
            job_key.SetVariable( 'popup_text_1', 'checking: found ' + HydrusData.ToHumanInt( len( file_seeds ) ) + ' new files' )
            
        
        self._file_seed_cache.AddFileSeeds( file_seeds )
        
        self._last_checked = HydrusData.GetNow()
        self._check_now = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        serialisable_tag_service_keys_to_filename_tagging_options = [ ( service_key.hex(), filename_tagging_options.GetSerialisableTuple() ) for ( service_key, filename_tagging_options ) in list(self._tag_service_keys_to_filename_tagging_options.items()) ]
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        # json turns int dict keys to strings
        action_pairs = list(self._actions.items())
        action_location_pairs = list(self._action_locations.items())
        
        return ( self._path, self._mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, self._period, self._check_regularly, serialisable_file_seed_cache, self._last_checked, self._paused, self._check_now, self._show_working_popup, self._publish_files_to_popup_button, self._publish_files_to_page )
        
    
    def _ImportFiles( self, job_key ):
        
        did_work = False
        
        time_to_save = HydrusData.GetNow() + 600
        
        num_files_imported = 0
        presentation_hashes = []
        presentation_hashes_fast = set()
        
        i = 0
        
        num_total = len( self._file_seed_cache )
        num_total_unknown = self._file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
        num_total_done = num_total - num_total_unknown
        
        while True:
            
            file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
            
            p1 = HC.options[ 'pause_import_folders_sync' ] or self._paused
            p2 = HydrusThreading.IsThreadShuttingDown()
            p3 = job_key.IsCancelled()
            
            if file_seed is None or p1 or p2 or p3:
                
                break
                
            
            did_work = True
            
            if HydrusData.TimeHasPassed( time_to_save ):
                
                HG.client_controller.WriteSynchronous( 'serialisable', self )
                
                time_to_save = HydrusData.GetNow() + 600
                
            
            gauge_num_done = num_total_done + num_files_imported + 1
            
            job_key.SetVariable( 'popup_text_1', 'importing file ' + HydrusData.ConvertValueRangeToPrettyString( gauge_num_done, num_total ) )
            job_key.SetVariable( 'popup_gauge_1', ( gauge_num_done, num_total ) )
            
            path = file_seed.file_seed_data
            
            file_seed.ImportPath( self._file_seed_cache, self._file_import_options, limited_mimes = self._mimes )
            
            if file_seed.status in CC.SUCCESSFUL_IMPORT_STATES:
                
                if file_seed.HasHash():
                    
                    hash = file_seed.GetHash()
                    
                    if self._tag_import_options.HasAdditionalTags():
                        
                        in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                        
                        downloaded_tags = []
                        
                        service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( file_seed.status, in_inbox, hash, downloaded_tags ) # additional tags
                        
                        if len( service_keys_to_content_updates ) > 0:
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                            
                        
                    
                    service_keys_to_tags = ClientTags.ServiceKeysToTags()
                    
                    for ( tag_service_key, filename_tagging_options ) in list(self._tag_service_keys_to_filename_tagging_options.items()):
                        
                        if not HG.client_controller.services_manager.ServiceExists( tag_service_key ):
                            
                            continue
                            
                        
                        try:
                            
                            tags = filename_tagging_options.GetTags( tag_service_key, path )
                            
                            if len( tags ) > 0:
                                
                                service_keys_to_tags[ tag_service_key ] = tags
                                
                            
                        except Exception as e:
                            
                            HydrusData.ShowText( 'Trying to parse filename tags in the import folder "' + self._name + '" threw an error!' )
                            
                            HydrusData.ShowException( e )
                            
                        
                    
                    if len( service_keys_to_tags ) > 0:
                        
                        service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
                        
                        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                    
                
                num_files_imported += 1
                
                if hash not in presentation_hashes_fast:
                    
                    if file_seed.ShouldPresent( self._file_import_options ):
                        
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
        
        ( self._path, self._mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, self._period, self._check_regularly, serialisable_file_seed_cache, self._last_checked, self._paused, self._check_now, self._show_working_popup, self._publish_files_to_popup_button, self._publish_files_to_page ) = serialisable_info
        
        self._actions = dict( action_pairs )
        self._action_locations = dict( action_location_pairs )
        
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        self._tag_service_keys_to_filename_tagging_options = dict( [ ( bytes.fromhex( encoded_service_key ), HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filename_tagging_options ) ) for ( encoded_service_key, serialisable_filename_tagging_options ) in serialisable_tag_service_keys_to_filename_tagging_options ] )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( path, mimes, serialisable_file_import_options, action_pairs, action_location_pairs, period, open_popup, tag, serialisable_file_seed_cache, last_checked, paused ) = old_serialisable_info
            
            # edited out tag carry-over to tio due to bit rot
            
            tag_import_options = ClientImportOptions.TagImportOptions()
            
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
                
                filename_tagging_options = ClientImportOptions.FilenameTaggingOptions()
                
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
            
        
    
    def CheckNow( self ):
        
        self._paused = False
        self._check_now = True
        
    
    def DoWork( self ):
        
        if HG.view_shutdown:
            
            return
            
        
        if HC.options[ 'pause_import_folders_sync' ] or self._paused:
            
            return
            
        
        checked_folder = False
        
        did_import_file_work = False
        
        error_occured = False
        
        job_key = ClientThreading.JobKey( pausable = False, cancellable = True )
        
        try:
            
            if not os.path.exists( self._path ) or not os.path.isdir( self._path ):
                
                raise Exception( 'Path "' + self._path + '" does not seem to exist, or is not a directory.' )
                
            
            pubbed_job_key = False
            
            job_key.SetVariable( 'popup_title', 'import folder - ' + self._name )
            
            due_by_check_now = self._check_now
            due_by_period = self._check_regularly and HydrusData.TimeHasPassed( self._last_checked + self._period )
            
            if due_by_check_now or due_by_period:
                
                if not pubbed_job_key and self._show_working_popup:
                    
                    HG.client_controller.pub( 'message', job_key )
                    
                    pubbed_job_key = True
                    
                
                self._CheckFolder( job_key )
                
                checked_folder = True
                
            
            file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
            
            if file_seed is not None:
                
                if not pubbed_job_key and self._show_working_popup:
                    
                    HG.client_controller.pub( 'message', job_key )
                    
                    pubbed_job_key = True
                    
                
                did_import_file_work = self._ImportFiles( job_key )
                
            
        except Exception as e:
            
            error_occured = True
            self._paused = True
            
            HydrusData.ShowText( 'The import folder "' + self._name + '" encountered an exception! It has been paused!' )
            HydrusData.ShowException( e )
            
        
        if checked_folder or did_import_file_work or error_occured:
            
            HG.client_controller.WriteSynchronous( 'serialisable', self )
            
        
        job_key.Delete()
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def Paused( self ):
        
        return self._paused
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def ToListBoxTuple( self ):
        
        return ( self._name, self._path, self._paused, self._check_regularly, self._period )
        
    
    def ToTuple( self ):
        
        return ( self._name, self._path, self._mimes, self._file_import_options, self._tag_import_options, self._tag_service_keys_to_filename_tagging_options, self._actions, self._action_locations, self._period, self._check_regularly, self._paused, self._check_now, self._show_working_popup, self._publish_files_to_popup_button, self._publish_files_to_page )
        
    
    def SetFileSeedCache( self, file_seed_cache ):
        
        self._file_seed_cache = file_seed_cache
        
    
    def SetTuple( self, name, path, mimes, file_import_options, tag_import_options, tag_service_keys_to_filename_tagging_options, actions, action_locations, period, check_regularly, paused, check_now, show_working_popup, publish_files_to_popup_button, publish_files_to_page ):
        
        if path != self._path:
            
            self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
            
        
        if set( mimes ) != set( self._mimes ):
            
            self._file_seed_cache.RemoveFileSeedsByStatus( ( CC.STATUS_VETOED, ) )
            
        
        self._name = name
        self._path = path
        self._mimes = mimes
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
