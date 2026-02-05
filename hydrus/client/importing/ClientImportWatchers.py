import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.importing import ClientImportControl
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import TagImportOptionsLegacy
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingFunctions
from hydrus.client.networking import ClientNetworkingJobs

class MultipleWatcherImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MULTIPLE_WATCHER_IMPORT
    SERIALISABLE_NAME = 'Multiple Watcher'
    SERIALISABLE_VERSION = 3
    
    ADDED_TIMESTAMP_DURATION = 15
    
    def __init__( self, url = None ):
        
        super().__init__()
        
        self._lock = threading.Lock()
        
        self._page_key = b'initialising page key'
        
        self._watchers = HydrusSerialisable.SerialisableList()
        
        self._highlighted_watcher_url = None
        
        self._checker_options = CG.client_controller.new_options.GetDefaultWatcherCheckerOptions()
        
        self._file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        self._file_import_options.SetIsDefault( True )
        
        self._tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
        
        self._note_import_options = NoteImportOptions.NoteImportOptions()
        self._note_import_options.SetIsDefault( True )
        
        self._watcher_keys_to_watchers = {}
        
        self._watcher_keys_to_added_timestamps = {}
        self._watcher_keys_to_already_in_timestamps = {}
        
        self._watchers_repeating_job = None
        
        self._status_dirty = True
        self._status_cache = ClientImportFileSeeds.FileSeedCacheStatus()
        
        #
        
        if url is not None:
            
            watcher = WatcherImport()
            
            watcher.SetURL( url )
            
            self._AddWatcher( watcher )
            
        
        self._have_started = False
        
        self._last_time_watchers_changed = HydrusTime.GetNowPrecise()
        
        self._last_serialisable_change_timestamp = 0
        
        self._last_pubbed_value_range = ( 0, 0 )
        self._next_pub_value_check_time = 0
        
        CG.client_controller.sub( self, 'Wake', 'notify_global_page_import_pause_change' )
        
    
    def _AddWatcher( self, watcher ):
        
        watcher.PublishToPage( False )
        watcher.Repage( self._page_key )
        
        self._watchers.append( watcher )
        
        self._last_time_watchers_changed = HydrusTime.GetNowPrecise()
        
        watcher_key = watcher.GetWatcherKey()
        
        self._watcher_keys_to_watchers[ watcher_key ] = watcher
        self._watcher_keys_to_added_timestamps[ watcher_key ] = HydrusTime.GetNow()
        
    
    def _CleanAddedTimestamps( self ):
        
        keys = list( self._watcher_keys_to_added_timestamps.keys() )
        
        for key in keys:
            
            if HydrusTime.TimeHasPassed( self._watcher_keys_to_added_timestamps[ key ] + self.ADDED_TIMESTAMP_DURATION ):
                
                del self._watcher_keys_to_added_timestamps[ key ]
                
            
        
        keys = list( self._watcher_keys_to_already_in_timestamps.keys() )
        
        for key in keys:
            
            if HydrusTime.TimeHasPassed( self._watcher_keys_to_already_in_timestamps[ key ] + self.ADDED_TIMESTAMP_DURATION ):
                
                del self._watcher_keys_to_already_in_timestamps[ key ]
                
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_watchers = self._watchers.GetSerialisableTuple()
        
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        serialisable_note_import_options = self._note_import_options.GetSerialisableTuple()
        
        return ( serialisable_watchers, self._highlighted_watcher_url, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, serialisable_note_import_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_watchers, self._highlighted_watcher_url, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, serialisable_note_import_options ) = serialisable_info
        
        self._watchers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_watchers )
        
        self._watcher_keys_to_watchers = { watcher.GetWatcherKey() : watcher for watcher in self._watchers }
        
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        self._note_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_note_import_options )
        
    
    def _RegenerateStatus( self ):
        
        file_seed_caches = [ watcher.GetFileSeedCache() for watcher in self._watchers ]
        
        self._status_cache = ClientImportFileSeeds.GenerateFileSeedCachesStatus( file_seed_caches )
        
        self._status_dirty = False
        
    
    def _RemoveWatcher( self, watcher_key ):
        
        if watcher_key not in self._watcher_keys_to_watchers:
            
            return
            
        
        watcher = self._watcher_keys_to_watchers[ watcher_key ]
        
        watcher.PublishToPage( False )
        watcher.Repage( 'dead page key' )
        
        self._watchers.remove( watcher )
        
        self._last_time_watchers_changed = HydrusTime.GetNowPrecise()
        
        del self._watcher_keys_to_watchers[ watcher_key ]
        
    
    def _SerialisableChangeMade( self ):
        
        self._last_serialisable_change_timestamp = HydrusTime.GetNow()
        
    
    def _SetDirty( self ):
        
        self._status_dirty = True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            serialisable_watchers = old_serialisable_info
            
            try:
                
                checker_options = CG.client_controller.new_options.GetDefaultWatcherCheckerOptions()
                
                file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
                file_import_options.SetIsDefault( True )
                
                tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
                
            except Exception as e:
                
                checker_options = ClientImportOptions.CheckerOptions()
                file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
                tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy()
                
            
            serialisable_checker_options = checker_options.GetSerialisableTuple()
            serialisable_file_import_options = file_import_options.GetSerialisableTuple()
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            highlighted_watcher_key = None
            
            serialisable_highlighted_watcher_key = highlighted_watcher_key
            
            new_serialisable_info = ( serialisable_watchers, serialisable_highlighted_watcher_key, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_watchers, serialisable_highlighted_watcher_key, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options ) = old_serialisable_info
            
            note_import_options = NoteImportOptions.NoteImportOptions()
            note_import_options.SetIsDefault( True )
            
            serialisable_note_import_options = note_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_watchers, serialisable_highlighted_watcher_key, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, serialisable_note_import_options )
            
            return ( 3, new_serialisable_info )
            
        
    
    def AddURL( self, url, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if url == '':
            
            return None
            
        
        if not ClientNetworkingFunctions.LooksLikeAFullURL( url ):
            
            return None
            
        
        url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url, for_server = True )
        
        with self._lock:
            
            for watcher in self._watchers:
                
                if url == watcher.GetURL():
                    
                    watcher_key = watcher.GetWatcherKey()
                    
                    self._watcher_keys_to_already_in_timestamps[ watcher_key ] = HydrusTime.GetNow()
                    
                    return None
                    
                
            
            watcher = WatcherImport()
            
            watcher.SetURL( url )
            
            if filterable_tags is not None:
                
                watcher.AddExternalFilterableTags( filterable_tags )
                
            
            if additional_service_keys_to_tags is not None:
                
                watcher.AddExternalAdditionalServiceKeysToTags( additional_service_keys_to_tags )
                
            
            watcher.SetCheckerOptions( self._checker_options )
            watcher.SetFileImportOptions( self._file_import_options )
            watcher.SetTagImportOptions( self._tag_import_options )
            watcher.SetNoteImportOptions( self._note_import_options )
            
            publish_to_page = False
            
            if self._have_started:
                
                watcher.Start( self._page_key, publish_to_page )
                
            
            self._AddWatcher( watcher )
            
        
        return watcher
        
    
    def AddWatcher( self, watcher ):
        
        with self._lock:
            
            self._AddWatcher( watcher )
            
            self._SetDirty()
            
        
    
    def ClearHighlightedWatcher( self ):
        
        with self._lock:
            
            if self._highlighted_watcher_url is not None:
                
                self._highlighted_watcher_url = None
                
                self._SerialisableChangeMade()
                
            
        
    
    def GetAPIInfoDict( self, simple ):
        
        highlighted_watcher = self.GetHighlightedWatcher()
        
        with self._lock:
            
            d = {}
            
            d[ 'watcher_imports' ] = [ watcher_import.GetAPIInfoDict( simple ) for watcher_import in self._watchers ]
            
            if highlighted_watcher is None:
                
                d[ 'highlight' ] = None
                
            else:
                
                d[ 'highlight' ] = highlighted_watcher.GetWatcherKey().hex()
                
            
            return d
            
        
    
    def GetCheckerOptions( self ) -> ClientImportOptions.CheckerOptions:
        
        with self._lock:
            
            return self._checker_options
            
        
    
    def GetFileImportOptions( self ) -> FileImportOptionsLegacy.FileImportOptionsLegacy:
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetHighlightedWatcher( self ):
        
        with self._lock:
            
            if self._highlighted_watcher_url is not None:
                
                for watcher in self._watchers:
                    
                    if watcher.GetURL() == self._highlighted_watcher_url:
                        
                        return watcher
                        
                    
                
                self._highlighted_watcher_url = None
                
            
            return None
            
        
    
    def GetLastTimeWatchersChanged( self ):
        
        with self._lock:
            
            return self._last_time_watchers_changed
            
        
    
    def GetNoteImportOptions( self ):
        
        with self._lock:
            
            return self._note_import_options
            
        
    
    def GetNumDead( self ):
        
        with self._lock:
            
            return len( [ watcher for watcher in self._watchers if watcher.IsDead() ] )
            
        
    
    def GetNumSeeds( self ):
        
        with self._lock:
            
            return sum( ( watcher.GetNumSeeds() for watcher in self._watchers ) )
            
        
    
    def GetNumWatchers( self ):
        
        with self._lock:
            
            return len( self._watchers )
            
        
    
    def GetTagImportOptions( self ) -> TagImportOptionsLegacy.TagImportOptionsLegacy:
        
        with self._lock:
            
            return self._tag_import_options
            
        
    
    def GetTotalStatus( self ) -> ClientImportFileSeeds.FileSeedCacheStatus:
        
        with self._lock:
            
            if self._status_dirty:
                
                self._RegenerateStatus()
                
            
            return self._status_cache
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            total_value = 0
            total_range = 0
            
            for watcher in self._watchers:
                
                ( value, range ) = watcher.GetValueRange()
                
                if value != range:
                    
                    total_value += value
                    total_range += range
                    
                
            
            return ( total_value, total_range )
            
        
    
    def GetWatchers( self ):
        
        with self._lock:
            
            return list( self._watchers )
            
        
    
    def GetWatcherSimpleStatus( self, watcher ):
        
        with self._lock:
            
            watcher_key = watcher.GetWatcherKey()
            
            if watcher_key in self._watcher_keys_to_added_timestamps:
                
                added_timestamp = self._watcher_keys_to_added_timestamps[ watcher_key ]
                
                if HydrusTime.TimeHasPassed( added_timestamp + self.ADDED_TIMESTAMP_DURATION ):
                    
                    self._CleanAddedTimestamps()
                    
                else:
                    
                    return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_WORKING, 'just added' )
                    
                
            
            if watcher_key in self._watcher_keys_to_already_in_timestamps:
                
                already_in_timestamp = self._watcher_keys_to_already_in_timestamps[ watcher_key ]
                
                if HydrusTime.TimeHasPassed( already_in_timestamp + self.ADDED_TIMESTAMP_DURATION ):
                    
                    self._CleanAddedTimestamps()
                    
                else:
                    
                    return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_WORKING, 'already watching' )
                    
                
            
        
        return watcher.GetSimpleStatus()
        
    
    def HasSerialisableChangesSince( self, since_timestamp ):
        
        with self._lock:
            
            if self._last_serialisable_change_timestamp > since_timestamp:
                
                return True
                
            
            for watcher in self._watchers:
                
                if watcher.HasSerialisableChangesSince( since_timestamp ):
                    
                    return True
                    
                
            
            return False
            
        
    
    def RemoveWatcher( self, watcher_key ):
        
        with self._lock:
            
            self._RemoveWatcher( watcher_key )
            
            self._SetDirty()
            
            self._SerialisableChangeMade()
            
        
    
    def SetCheckerOptions( self, checker_options ):
        
        with self._lock:
            
            if checker_options.DumpToString() != self._checker_options.DumpToString():
                
                self._checker_options = checker_options
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            changes_made = file_import_options.DumpToString() != self._file_import_options.DumpToString()
            
            self._file_import_options = file_import_options
            
            if changes_made:
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetHighlightedWatcher( self, highlighted_watcher ):
        
        with self._lock:
            
            highlighted_watcher_url = highlighted_watcher.GetURL()
            
            if highlighted_watcher_url != self._highlighted_watcher_url:
                
                self._highlighted_watcher_url = highlighted_watcher_url
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetNoteImportOptions( self, note_import_options ):
        
        with self._lock:
            
            changes_made = note_import_options.DumpToString() != self._note_import_options.DumpToString()
            
            self._note_import_options = note_import_options
            
            if changes_made:
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            changes_made = tag_import_options.DumpToString() != self._tag_import_options.DumpToString()
            
            self._tag_import_options = tag_import_options
            
            if changes_made:
                
                self._SerialisableChangeMade()
                
            
        
    
    def Start( self, page_key ):
        
        with self._lock:
            
            if self._have_started:
                
                return
                
            
            self._page_key = page_key
            
            # set a 2s period so the page value/range is breddy snappy
            self._watchers_repeating_job = CG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), 2.0, self.REPEATINGWorkOnWatchers )
            
            for watcher in self._watchers:
                
                publish_to_page = False
                
                if self._highlighted_watcher_url is not None and watcher.GetURL() == self._highlighted_watcher_url:
                    
                    publish_to_page = True
                    
                
                watcher.Start( page_key, publish_to_page )
                
            
            self._have_started = True
            
        
    
    def REPEATINGWorkOnWatchers( self ):
        
        with self._lock:
            
            if ClientImportControl.PageImporterShouldStopWorking( self._page_key ):
                
                self._watchers_repeating_job.Cancel()
                
                return
                
            
            if not self._status_dirty: # if we think we are clean
                
                for watcher in self._watchers:
                    
                    file_seed_cache = watcher.GetFileSeedCache()
                    
                    if file_seed_cache.GetStatus().GetGenerationTime() > self._status_cache.GetGenerationTime(): # has there has been an update?
                        
                        self._SetDirty()
                        
                        break
                        
                    
                
            
        
        if HydrusTime.TimeHasPassed( self._next_pub_value_check_time ):
            
            self._next_pub_value_check_time = HydrusTime.GetNow() + 5
            
            current_value_range = self.GetValueRange()
            
            if current_value_range != self._last_pubbed_value_range:
                
                self._last_pubbed_value_range = current_value_range
                
                CG.client_controller.pub( 'refresh_page_name', self._page_key )
                
            
        
    
    def Wake( self ):
        
        ClientImporting.WakeRepeatingJob( self._watchers_repeating_job )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MULTIPLE_WATCHER_IMPORT ] = MultipleWatcherImport

class WatcherImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_WATCHER_IMPORT
    SERIALISABLE_NAME = 'Watcher'
    SERIALISABLE_VERSION = 9
    
    MIN_CHECK_PERIOD = 30
    
    def __init__( self ):
        
        super().__init__()
        
        self._page_key = b'initialising page key'
        self._publish_to_page = False
        
        self._url = ''
        
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        self._external_filterable_tags = set()
        self._external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
        
        self._checker_options = CG.client_controller.new_options.GetDefaultWatcherCheckerOptions()
        
        self._file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        self._file_import_options.SetIsDefault( True )
        
        self._tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
        
        self._note_import_options = NoteImportOptions.NoteImportOptions()
        self._note_import_options.SetIsDefault( True )
        
        self._last_check_time = 0
        self._checking_status = ClientImporting.CHECKER_STATUS_OK
        self._subject = 'unknown subject'
        
        self._next_check_time = None
        
        self._file_network_job = None
        self._checker_network_job = None
        
        self._check_now = False
        self._files_paused = False
        self._checking_paused = False
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        self._creation_time = HydrusTime.GetNow()
        
        self._file_velocity_status = ''
        self._files_status = ''
        self._watcher_status = ''
        
        self._watcher_key = HydrusData.GenerateKey()
        
        self._have_started = False
        
        self._lock = threading.Lock()
        self._files_working_lock = threading.Lock()
        self._checker_working_lock = threading.Lock()
        
        self._last_pubbed_page_name = ''
        
        self._files_repeating_job = None
        self._checker_repeating_job = None
        
        self._last_serialisable_change_timestamp = 0
        
        CG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        CG.client_controller.sub( self, 'Wake', 'notify_global_page_import_pause_change' )
        
    
    def _CheckerNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                self._checker_network_job = network_job
                
            
        
        def exit_call():
            
            with self._lock:
                
                self._checker_network_job = None
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _CheckWatchableURL( self ):
        
        def file_seeds_callable( file_seeds ):
            
            return ClientImporting.UpdateFileSeedCacheWithFileSeeds( self._file_seed_cache, file_seeds )
            
        
        def status_hook( text ):
            
            with self._lock:
                
                self._watcher_status = HydrusText.GetFirstLine( text )
                
            
        
        def title_hook( text ):
            
            with self._lock:
                
                self._subject = HydrusText.GetFirstLine( text )
                
            
        
        gallery_seed = ClientImportGallerySeeds.GallerySeed( self._url, can_generate_more_pages = False )
        
        gallery_seed.AddExternalFilterableTags( self._external_filterable_tags )
        gallery_seed.AddExternalAdditionalServiceKeysToTags( self._external_additional_service_keys_to_tags )
        
        self._gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
        
        with self._lock:
            
            self._watcher_status = 'checking'
            
        
        try:
            
            ( num_urls_added, num_urls_already_in_file_seed_cache, num_urls_total, result_404, added_new_gallery_pages, can_search_for_more_files, stop_reason ) = gallery_seed.WorkOnURL( 'watcher', self._gallery_seed_log, file_seeds_callable, status_hook, title_hook, self._NetworkJobFactory, self._CheckerNetworkJobPresentationContextFactory, self._file_import_options )
            
            if num_urls_added > 0:
                
                ClientImporting.WakeRepeatingJob( self._files_repeating_job )
                
            
            if result_404:
                
                with self._lock:
                    
                    self._checking_paused = True
                    
                    self._checking_status = ClientImporting.CHECKER_STATUS_404
                    
                
            
            if gallery_seed.status == CC.STATUS_ERROR:
                
                # the [DEAD] stuff can override watcher status, so let's give a brief time for this to display the error
                
                with self._lock:
                    
                    self._checking_paused = True
                    
                    self._watcher_status = gallery_seed.note
                    
                
                time.sleep( 5 )
                
            
        except HydrusExceptions.NetworkException as e:
            
            delay = CG.client_controller.new_options.GetInteger( 'downloader_network_error_delay' )
            
            self._DelayWork( delay, str( e ) )
            
            gallery_seed.SetStatus( CC.STATUS_ERROR, str( e ) )
            
            HydrusData.PrintException( e )
            
        finally:
            
            self._gallery_seed_log.NotifyGallerySeedsUpdated( ( gallery_seed, ) )
            
        
        with self._lock:
            
            if self._check_now:
                
                self._check_now = False
                
            
            self._last_check_time = HydrusTime.GetNow()
            
            self._UpdateFileVelocityStatus()
            
            self._UpdateNextCheckTime()
            
            self._Compact()
            
            self._watcher_status = ''
            
        
    
    def _Compact( self ):
        
        death_period = self._checker_options.GetDeathFileVelocityPeriod()
        
        compact_before_this_time = self._last_check_time - ( death_period * 2 )
        
        self._gallery_seed_log.Compact( 500, compact_before_this_time )
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusTime.GetNow() + time_delta
        self._no_work_until_reason = HydrusText.GetFirstLine( reason )
        
    
    def _FileNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                self._file_network_job = network_job
                
            
        
        def exit_call():
            
            with self._lock:
                
                self._file_network_job = None
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _NetworkJobFactory( self, *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJobWatcherPage( self._watcher_key, *args, **kwargs )
        
        return network_job
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        serialisable_external_filterable_tags = list( self._external_filterable_tags )
        serialisable_external_additional_service_keys_to_tags = self._external_additional_service_keys_to_tags.GetSerialisableTuple()
        
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        serialisable_note_import_options = self._note_import_options.GetSerialisableTuple()
        
        return (
            self._url,
            serialisable_gallery_seed_log,
            serialisable_file_seed_cache,
            serialisable_external_filterable_tags,
            serialisable_external_additional_service_keys_to_tags,
            serialisable_checker_options,
            serialisable_file_import_options,
            serialisable_tag_import_options,
            serialisable_note_import_options,
            self._last_check_time,
            self._files_paused,
            self._checking_paused,
            self._checking_status,
            self._subject,
            self._no_work_until,
            self._no_work_until_reason,
            self._creation_time
        )
        
    
    def _HasURL( self ):
        
        return self._url != ''
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self._url,
            serialisable_gallery_seed_log,
            serialisable_file_seed_cache,
            serialisable_external_filterable_tags,
            serialisable_external_additional_service_keys_to_tags,
            serialisable_checker_options,
            serialisable_file_import_options,
            serialisable_tag_import_options,
            serialisable_note_import_options,
            self._last_check_time,
            self._files_paused,
            self._checking_paused,
            self._checking_status,
            self._subject,
            self._no_work_until,
            self._no_work_until_reason,
            self._creation_time
            ) = serialisable_info
        
        self._external_filterable_tags = set( serialisable_external_filterable_tags )
        self._external_additional_service_keys_to_tags = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_external_additional_service_keys_to_tags )
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        self._note_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_note_import_options )
        
    
    def _SerialisableChangeMade( self ):
        
        self._last_serialisable_change_timestamp = HydrusTime.GetNow()
        
    
    def _UpdateFileVelocityStatus( self ):
        
        self._file_velocity_status = self._checker_options.GetPrettyCurrentVelocity( self._file_seed_cache, self._last_check_time )
        
    
    def _UpdateNextCheckTime( self ):
        
        if self._check_now:
            
            self._next_check_time = self._last_check_time + self.MIN_CHECK_PERIOD
            
        else:
            
            if not HydrusTime.TimeHasPassed( self._no_work_until ):
                
                self._next_check_time = self._no_work_until + 1
                
            else:
                
                if self._checking_status == ClientImporting.CHECKER_STATUS_OK:
                    
                    if self._checker_options.IsDead( self._file_seed_cache, self._last_check_time ):
                        
                        self._checking_status = ClientImporting.CHECKER_STATUS_DEAD
                        
                    
                
                if self._checking_status != ClientImporting.CHECKER_STATUS_OK:
                    
                    self._checking_paused = True
                    
                
                self._next_check_time = self._checker_options.GetNextCheckTime( self._file_seed_cache, self._last_check_time )
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( url, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_file_import_options, serialisable_tag_import_options, times_to_check, check_period, last_check_time, paused ) = old_serialisable_info
            
            checker_options = ClientImportOptions.CheckerOptions( intended_files_per_check = 8, never_faster_than = 300, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
            
            serialisable_checker_options = checker_options.GetSerialisableTuple()
            
            files_paused = paused
            checking_paused = paused
            
            new_serialisable_info = ( url, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( url, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused ) = old_serialisable_info
            
            checking_status = ClientImporting.CHECKER_STATUS_OK
            subject = 'unknown subject'
            
            new_serialisable_info = ( url, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( url, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject ) = old_serialisable_info
            
            no_work_until = 0
            no_work_until_reason = ''
            
            new_serialisable_info = ( url, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( url, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason ) = old_serialisable_info
            
            creation_time = HydrusTime.GetNow()
            
            new_serialisable_info = ( url, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( url, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( url, serialisable_gallery_seed_log, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( url, serialisable_gallery_seed_log, serialisable_file_seed_cache, urls_to_filenames, urls_to_md5_base64, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time ) = old_serialisable_info
            
            external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
            serialisable_external_additional_service_keys_to_tags = external_additional_service_keys_to_tags.GetSerialisableTuple()
            
            new_serialisable_info = ( url, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_external_additional_service_keys_to_tags, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( url, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_external_additional_service_keys_to_tags, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time ) = old_serialisable_info
            
            filterable_tags = set()
            
            serialisable_external_filterable_tags = list( filterable_tags )
            
            new_serialisable_info = ( url, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_external_filterable_tags, serialisable_external_additional_service_keys_to_tags, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( url, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_external_filterable_tags, serialisable_external_additional_service_keys_to_tags, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time ) = old_serialisable_info
            
            note_import_options = NoteImportOptions.NoteImportOptions()
            note_import_options.SetIsDefault( True )
            
            serialisable_note_import_options = note_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( url, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_external_filterable_tags, serialisable_external_additional_service_keys_to_tags, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, serialisable_note_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time )
            
            return ( 9, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        def status_hook( text ):
            
            with self._lock:
                
                self._files_status = HydrusText.GetFirstLine( text )
                
            
        
        did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, self._NetworkJobFactory, self._FileNetworkJobPresentationContextFactory, self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD, self._tag_import_options, self._note_import_options )
        
        with self._lock:
            
            real_presentation_import_options = FileImportOptionsLegacy.GetRealPresentationImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
            
            should_present = self._publish_to_page and file_seed.ShouldPresent( real_presentation_import_options )
            
            page_key = self._page_key
            
        
        if should_present:
            
            file_seed.PresentToPage( page_key )
            
            did_substantial_work = True
            
        
        with self._lock:
            
            self._files_status = ''
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def AddExternalAdditionalServiceKeysToTags( self, service_keys_to_tags ):
        
        with self._lock:
            
            external_additional_service_keys_to_tags = ClientTags.ServiceKeysToTags( service_keys_to_tags )
            
            if external_additional_service_keys_to_tags.DumpToString() != self._external_additional_service_keys_to_tags.DumpToString():
                
                self._external_additional_service_keys_to_tags.update( service_keys_to_tags )
                
                self._SerialisableChangeMade()
                
            
        
    
    def AddExternalFilterableTags( self, tags ):
        
        with self._lock:
            
            tags_set = set( tags )
            
            if tags_set != self._external_filterable_tags:
                
                self._external_filterable_tags.update( tags )
                
                self._SerialisableChangeMade()
                
            
        
    
    def GetAPIInfoDict( self, simple ):
        
        with self._lock:
            
            d = {}
            
            d[ 'url' ] = self._url
            d[ 'watcher_key' ] = self._watcher_key.hex()
            d[ 'created' ] = self._creation_time
            d[ 'last_check_time' ] = self._last_check_time
            d[ 'next_check_time' ] = self._next_check_time
            d[ 'files_paused' ] = self._files_paused
            d[ 'checking_paused' ] = self._checking_paused
            d[ 'checking_status' ] = self._checking_status
            d[ 'subject' ] = self._subject
            d[ 'imports' ] = self._file_seed_cache.GetAPIInfoDict( simple )
            d[ 'gallery_log' ] = self._gallery_seed_log.GetAPIInfoDict( simple )
            
            return d
            
        
    
    def CanRetryFailed( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR ) > 0
            
        
    
    def CanRetryIgnored( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetFileSeedCount( CC.STATUS_VETOED ) > 0
            
        
    
    def CheckingPaused( self ):
        
        with self._lock:
            
            return self._checking_paused
            
        
    
    def CheckNow( self ):
        
        with self._lock:
            
            self._check_now = True
            
            self._checking_paused = False
            
            self._no_work_until = 0
            self._no_work_until_reason = ''
            
            self._checking_status = ClientImporting.CHECKER_STATUS_OK
            
            self._UpdateNextCheckTime()
            
            ClientImporting.WakeRepeatingJob( self._checker_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def CurrentlyAlive( self ):
        
        with self._lock:
            
            return self._checking_status == ClientImporting.CHECKER_STATUS_OK
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._file_seed_cache.WorkToDo()
            
            return not finished and not self._files_paused
            
        
    
    def FilesPaused( self ):
        
        with self._lock:
            
            return self._files_paused
            
        
    
    def GetCheckerOptions( self ):
        
        with self._lock:
            
            return self._checker_options
            
        
    
    def GetCheckingStatus( self ):
        
        with self._lock:
            
            return self._checking_status
            
        
    
    def GetCreationTime( self ):
        
        with self._lock:
            
            return self._creation_time
            
        
    
    def GetFileImportOptions( self ):
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetFileSeedCache( self ):
        
        with self._lock:
            
            return self._file_seed_cache
            
        
    
    def GetGallerySeedLog( self ):
        
        with self._lock:
            
            return self._gallery_seed_log
            
        
    
    def GetHashes( self ):
        
        with self._lock:
            
            fsc = self._file_seed_cache
            
        
        return fsc.GetHashes()
        
    
    def GetNetworkJobs( self ):
        
        with self._lock:
            
            return ( self._file_network_job, self._checker_network_job )
            
        
    
    def GetNextCheckTime( self ):
        
        with self._lock:
            
            return self._next_check_time
            
        
    
    def GetNoteImportOptions( self ):
        
        with self._lock:
            
            return self._note_import_options
            
        
    
    def GetNumSeeds( self ):
        
        with self._lock:
            
            return len( self._file_seed_cache ) + len( self._gallery_seed_log )
            
        
    
    def GetPresentedHashes( self, presentation_import_options = None ):
        
        with self._lock:
            
            fsc = self._file_seed_cache
            
            fio = self._file_import_options
            
        
        if presentation_import_options is None:
            
            presentation_import_options = FileImportOptionsLegacy.GetRealPresentationImportOptions( fio, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
            
        
        return fsc.GetPresentedHashes( presentation_import_options )
        
    
    def GetSimpleStatus( self ):
        
        with self._lock:
            
            files_work_to_do = self._file_seed_cache.WorkToDo()
            
            checker_go = HydrusTime.TimeHasPassed( self._next_check_time ) and not self._checking_paused
            files_go = files_work_to_do and not self._files_paused
            
            work_is_going_on = self._checker_working_lock.locked() or self._files_working_lock.locked()
            
            if not HydrusTime.TimeHasPassed( self._no_work_until ):
                
                if self._next_check_time is None:
                    
                    text = '{} - working again {}'.format( self._no_work_until_reason, HydrusTime.TimestampToPrettyTimeDelta( self._no_work_until ) )
                    
                else:
                    
                    text = '{} - next check {}'.format( self._no_work_until_reason, HydrusTime.TimestampToPrettyTimeDelta( max( self._no_work_until, self._next_check_time ) ) )
                    
                
                return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_DEFERRED, text )
                
            elif checker_go or files_go:
                
                if work_is_going_on:
                    
                    return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_WORKING, 'working' )
                    
                else:
                    
                    return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_PENDING, 'pending' )
                    
                
            elif self._checking_status == ClientImporting.CHECKER_STATUS_404:
                
                return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_DONE, '404' )
                
            elif self._checking_status == ClientImporting.CHECKER_STATUS_DEAD:
                
                return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_DONE, 'DEAD' )
                
            else:
                
                if self._checking_paused:
                    
                    if work_is_going_on:
                        
                        return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_PAUSING, 'pausing' + HC.UNICODE_ELLIPSIS )
                        
                    else:
                        
                        return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_PAUSED, '' )
                        
                    
                else:
                    
                    if self._next_check_time is None or HydrusTime.TimeHasPassed( self._next_check_time ):
                        
                        return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_PENDING, 'pending' )
                        
                    else:
                        
                        return ( ClientImporting.DOWNLOADER_SIMPLE_STATUS_DEFERRED, HydrusTime.TimestampToPrettyTimeDelta( self._next_check_time, no_prefix = True ) )
                        
                    
                
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            if not HydrusTime.TimeHasPassed( self._no_work_until ):
                
                if self._next_check_time is None:
                    
                    no_work_text = '{} - working again {}'.format( self._no_work_until_reason, HydrusTime.TimestampToPrettyTimeDelta( self._no_work_until ) )
                    
                else:
                    
                    no_work_text = '{} - next check {}'.format( self._no_work_until_reason, HydrusTime.TimestampToPrettyTimeDelta( max( self._no_work_until, self._next_check_time ) ) )
                    
                
                files_status = no_work_text
                watcher_status = no_work_text
                
            else:
                
                files_work_to_do = self._file_seed_cache.WorkToDo()
                
                checker_go = HydrusTime.TimeHasPassed( self._next_check_time ) and not self._checking_paused
                files_go = files_work_to_do and not self._files_paused
                
                if checker_go and not self._checker_working_lock.locked() and self._checker_repeating_job is not None and self._checker_repeating_job.WaitingOnWorkSlot():
                    
                    self._watcher_status = 'waiting for a work slot'
                    
                
                if files_go and not self._files_working_lock.locked() and self._files_repeating_job is not None and self._files_repeating_job.WaitingOnWorkSlot():
                    
                    self._files_status = 'waiting for a work slot'
                    
                
                currently_working = self._files_repeating_job is not None and self._files_repeating_job.CurrentlyWorking()
                
                files_status = ClientImportControl.GenerateLiveStatusText( self._files_status, self._files_paused, currently_working, self._no_work_until, self._no_work_until_reason )
                
                currently_working = self._checker_repeating_job is not None and self._checker_repeating_job.CurrentlyWorking()
                
                watcher_status = ClientImportControl.GenerateLiveStatusText( self._watcher_status, self._checking_paused, currently_working, self._no_work_until, self._no_work_until_reason )
                
            
            return ( files_status, self._files_paused, self._file_velocity_status, self._next_check_time, watcher_status, self._subject, self._checking_status, self._check_now, self._checking_paused )
            
        
    
    def GetSubject( self ):
        
        with self._lock:
            
            if self._subject in ( None, '' ):
                
                return 'unknown subject'
                
            else:
                
                return self._subject
                
            
        
    
    def GetTagImportOptions( self ):
        
        with self._lock:
            
            return self._tag_import_options
            
        
    
    def GetWatcherKey( self ):
        
        with self._lock:
            
            return self._watcher_key
            
        
    
    def GetURL( self ):
        
        with self._lock:
            
            return self._url
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetValueRange()
            
        
    
    def HasSerialisableChangesSince( self, since_timestamp ):
        
        return self._last_serialisable_change_timestamp > since_timestamp
        
    
    def HasURL( self ):
        
        with self._lock:
            
            return self._HasURL()
            
        
    
    def _IsDead( self ):
        
        return self._checking_status in ( ClientImporting.CHECKER_STATUS_404, ClientImporting.CHECKER_STATUS_DEAD )
        
    
    def IsDead( self ):
        
        with self._lock:
            
            return self._IsDead()
            
        
    
    def NotifyFileSeedsUpdated( self, file_seed_cache_key, file_seeds ):
        
        if file_seed_cache_key == self._file_seed_cache.GetFileSeedCacheKey():
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def PausePlayChecking( self ):
        
        with self._lock:
            
            if self._checking_paused and self._IsDead():
                
                return # watcher is dead, so don't unpause until a checknow event
                
            else:
                
                self._checking_paused = not self._checking_paused
                
                ClientImporting.WakeRepeatingJob( self._checker_repeating_job )
                
                self._SerialisableChangeMade()
                
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def PublishToPage( self, publish_to_page ):
        
        with self._lock:
            
            self._publish_to_page = publish_to_page
            
        
    
    def Repage( self, page_key ):
        
        with self._lock:
            
            self._page_key = page_key
            
        
    
    def RetryFailed( self ):
        
        with self._lock:
            
            self._file_seed_cache.RetryFailed()
            
            self._SerialisableChangeMade()
            
        
    
    def RetryIgnored( self, ignored_regex = None ):
        
        with self._lock:
            
            self._file_seed_cache.RetryIgnored( ignored_regex = ignored_regex )
            
            self._SerialisableChangeMade()
            
        
    
    def SetCheckerOptions( self, checker_options: ClientImportOptions.CheckerOptions ):
        
        with self._lock:
            
            change_made = checker_options.DumpToString() != self._checker_options.DumpToString()
            
            self._checker_options = checker_options
            
            if change_made:
                
                self._UpdateNextCheckTime()
                
                self._UpdateFileVelocityStatus()
                
                ClientImporting.WakeRepeatingJob( self._checker_repeating_job )
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetFileImportOptions( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ):
        
        with self._lock:
            
            if file_import_options.DumpToString() != self._file_import_options.DumpToString():
                
                self._file_import_options = file_import_options
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetNoteImportOptions( self, note_import_options: NoteImportOptions.NoteImportOptions ):
        
        with self._lock:
            
            if note_import_options.DumpToString() != self._note_import_options.DumpToString():
                
                self._note_import_options = note_import_options
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetTagImportOptions( self, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy ):
        
        with self._lock:
            
            if tag_import_options.DumpToString() != self._tag_import_options.DumpToString():
                
                self._tag_import_options = tag_import_options
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetURL( self, url ):
        
        if url is None:
            
            url = ''
            
        
        if not ClientNetworkingFunctions.LooksLikeAFullURL( url ):
            
            url = ''
            
        
        if url != '':
            
            try:
                
                url = CG.client_controller.network_engine.domain_manager.NormaliseURL( url, for_server = True )
                
            except HydrusExceptions.URLClassException:
                
                url = ''
                
            
        
        with self._lock:
            
            self._url = url
            
            ClientImporting.WakeRepeatingJob( self._checker_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def Start( self, page_key, publish_to_page ):
        
        with self._lock:
            
            if self._have_started:
                
                return
                
            
            self._page_key = page_key
            self._publish_to_page = publish_to_page
            
            self._UpdateNextCheckTime()
            
            self._UpdateFileVelocityStatus()
            
            self._files_repeating_job = CG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles )
            self._checker_repeating_job = CG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnChecker )
            
            self._files_repeating_job.SetThreadSlotType( 'watcher_files' )
            self._checker_repeating_job.SetThreadSlotType( 'watcher_check' )
            
            self._have_started = True
            
        
    
    def CheckCanDoFileWork( self ):
        
        with self._lock:
            
            try:
                
                ClientImportControl.CheckImporterCanDoWorkBecauseStopped( self._page_key )
                
            except HydrusExceptions.VetoException:
                
                self._files_repeating_job.Cancel()
                
                raise
                
            
            ClientImportControl.CheckImporterCanDoFileWorkBecausePaused( self._files_paused, self._file_seed_cache, self._page_key )
            
            try:
                
                real_file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
                
                ClientImportControl.CheckImporterCanDoFileWorkBecausePausifyingProblem( real_file_import_options.GetLocationImportOptions() )
                
            except HydrusExceptions.VetoException:
                
                self._files_paused = True
                
                raise
                
            
        
        self.CheckCanDoNetworkWork()
        
    
    def CheckCanDoNetworkWork( self ):
        
        with self._lock:
            
            ClientImportControl.CheckCanDoNetworkWork( self._no_work_until, self._no_work_until_reason )
            
        
        return True
        
    
    def REPEATINGWorkOnFiles( self ):
        
        with self._files_working_lock:
            
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
                    
                
            
        
    
    def CheckCanDoCheckerWork( self ):
        
        with self._lock:
            
            try:
                
                ClientImportControl.CheckImporterCanDoWorkBecauseStopped( self._page_key )
                
            except HydrusExceptions.VetoException:
                
                self._checker_repeating_job.Cancel()
                
                raise
                
            
            while self._gallery_seed_log.WorkToDo():
                # some old unworked gallery url is hanging around, let's clear it
                
                gallery_seed = self._gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
                
                gallery_seed.SetStatus( CC.STATUS_VETOED, note = 'check never finished' )
                
                self._gallery_seed_log.NotifyGallerySeedsUpdated( ( gallery_seed, ) )
                
            
            if self._checking_paused:
                
                raise HydrusExceptions.VetoException( 'paused' )
                
            
            if CG.client_controller.new_options.GetBoolean( 'pause_all_paged_importers' ):
                
                raise HydrusExceptions.VetoException( 'all paged importers are paused! hit network->pause to resume!' )
                
            
            if CG.client_controller.new_options.GetBoolean( 'pause_all_watcher_checkers' ):
                
                raise HydrusExceptions.VetoException( 'all checkers are paused! hit network->pause to resume!' )
                
            
            if not self._HasURL():
                
                raise HydrusExceptions.VetoException( 'no url set yet!' )
                
            
            if self._checking_status == ClientImporting.CHECKER_STATUS_404:
                
                raise HydrusExceptions.VetoException( 'URL 404' )
                
            elif self._checking_status == ClientImporting.CHECKER_STATUS_DEAD:
                
                raise HydrusExceptions.VetoException( 'URL DEAD' )
                
            
            check_due = HydrusTime.TimeHasPassed( self._next_check_time )
            
            if not check_due:
                
                raise HydrusExceptions.VetoException( '' )
                
            
        
        return self.CheckCanDoNetworkWork()
        
    
    def REPEATINGWorkOnChecker( self ):
        
        with self._checker_working_lock:
            
            try:
                
                try:
                    
                    self.CheckCanDoCheckerWork()
                    
                except HydrusExceptions.VetoException as e:
                    
                    with self._lock:
                        
                        self._watcher_status = str( e )
                        
                    
                    return
                    
                
                self._CheckWatchableURL()
                
                self._SerialisableChangeMade()
                
            except Exception as e:
                
                with self._lock:
                    
                    self._watcher_status = 'stopping work: {}'.format( str( e ) )
                    
                
                HydrusData.ShowException( e )
                
                return
                
            
        
    

    def Wake( self ):
        
        ClientImporting.WakeRepeatingJob( self._files_repeating_job )
        ClientImporting.WakeRepeatingJob( self._checker_repeating_job )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_WATCHER_IMPORT ] = WatcherImport
