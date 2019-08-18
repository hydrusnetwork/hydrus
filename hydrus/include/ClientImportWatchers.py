from . import ClientConstants as CC
from . import ClientDownloading
from . import ClientImporting
from . import ClientImportOptions
from . import ClientImportFileSeeds
from . import ClientImportGallerySeeds
from . import ClientNetworkingJobs
from . import ClientParsing
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
import threading
import time
import wx

class MultipleWatcherImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MULTIPLE_WATCHER_IMPORT
    SERIALISABLE_NAME = 'Multiple Watcher'
    SERIALISABLE_VERSION = 2
    
    ADDED_TIMESTAMP_DURATION = 15
    
    def __init__( self, url = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._page_key = 'initialising page key'
        
        self._watchers = HydrusSerialisable.SerialisableList()
        
        self._highlighted_watcher_url = None
        
        self._checker_options = HG.client_controller.new_options.GetDefaultWatcherCheckerOptions()
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        self._tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
        
        self._watcher_keys_to_watchers = {}
        
        self._watcher_keys_to_added_timestamps = {}
        self._watcher_keys_to_already_in_timestamps = {}
        
        self._watchers_repeating_job = None
        
        self._status_dirty = True
        self._status_cache = None
        self._status_cache_generation_time = 0
        
        #
        
        if url is not None:
            
            watcher = WatcherImport()
            
            watcher.SetURL( url )
            
            self._AddWatcher( watcher )
            
        
        self._last_time_watchers_changed = HydrusData.GetNowPrecise()
        
        self._last_pubbed_value_range = ( 0, 0 )
        self._next_pub_value_check_time = 0
        
    
    def _AddWatcher( self, watcher ):
        
        watcher.PublishToPage( False )
        watcher.Repage( self._page_key )
        
        self._watchers.append( watcher )
        
        self._last_time_watchers_changed = HydrusData.GetNowPrecise()
        
        watcher_key = watcher.GetWatcherKey()
        
        self._watcher_keys_to_watchers[ watcher_key ] = watcher
        self._watcher_keys_to_added_timestamps[ watcher_key ] = HydrusData.GetNow()
        
    
    def _CleanAddedTimestamps( self ):
        
        keys = list( self._watcher_keys_to_added_timestamps.keys() )
        
        for key in keys:
            
            if HydrusData.TimeHasPassed( self._watcher_keys_to_added_timestamps[ key ] + self.ADDED_TIMESTAMP_DURATION ):
                
                del self._watcher_keys_to_added_timestamps[ key ]
                
            
        
        keys = list( self._watcher_keys_to_already_in_timestamps.keys() )
        
        for key in keys:
            
            if HydrusData.TimeHasPassed( self._watcher_keys_to_already_in_timestamps[ key ] + self.ADDED_TIMESTAMP_DURATION ):
                
                del self._watcher_keys_to_already_in_timestamps[ key ]
                
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_watchers = self._watchers.GetSerialisableTuple()
        
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( serialisable_watchers, self._highlighted_watcher_url, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_watchers, self._highlighted_watcher_url, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options ) = serialisable_info
        
        self._watchers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_watchers )
        
        self._watcher_keys_to_watchers = { watcher.GetWatcherKey() : watcher for watcher in self._watchers }
        
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _RegenerateStatus( self ):
        
        file_seed_caches = [ watcher.GetFileSeedCache() for watcher in self._watchers ]
        
        self._status_cache = ClientImportFileSeeds.GenerateFileSeedCachesStatus( file_seed_caches )
        
        self._status_dirty = False
        self._status_cache_generation_time = HydrusData.GetNow()
        
    
    def _RemoveWatcher( self, watcher_key ):
        
        if watcher_key not in self._watcher_keys_to_watchers:
            
            return
            
        
        watcher = self._watcher_keys_to_watchers[ watcher_key ]
        
        watcher.PublishToPage( False )
        watcher.Repage( 'dead page key' )
        
        self._watchers.remove( watcher )
        
        self._last_time_watchers_changed = HydrusData.GetNowPrecise()
        
        del self._watcher_keys_to_watchers[ watcher_key ]
        
    
    def _SetDirty( self ):
        
        self._status_dirty = True
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            serialisable_watchers = old_serialisable_info
            
            try:
                
                checker_options = HG.client_controller.new_options.GetDefaultWatcherCheckerOptions()
                file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
                tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
                
            except:
                
                checker_options = ClientImportOptions.CheckerOptions()
                file_import_options = ClientImportOptions.FileImportOptions()
                tag_import_options = ClientImportOptions.TagImportOptions()
                
            
            serialisable_checker_options = checker_options.GetSerialisableTuple()
            serialisable_file_import_options = file_import_options.GetSerialisableTuple()
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            highlighted_watcher_key = None
            
            serialisable_highlighted_watcher_key = highlighted_watcher_key
            
            new_serialisable_info = ( serialisable_watchers, serialisable_highlighted_watcher_key, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options )
            
            return ( 2, new_serialisable_info )
            
        
    
    def AddURL( self, url, service_keys_to_tags = None ):
        
        if url == '':
            
            return None
            
        
        url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
        
        with self._lock:
            
            for watcher in self._watchers:
                
                if url == watcher.GetURL():
                    
                    watcher_key = watcher.GetWatcherKey()
                    
                    self._watcher_keys_to_already_in_timestamps[ watcher_key ] = HydrusData.GetNow()
                    
                    return None
                    
                
            
            watcher = WatcherImport()
            
            watcher.SetURL( url )
            
            if service_keys_to_tags is not None:
                
                watcher.SetFixedServiceKeysToTags( service_keys_to_tags )
                
            
            watcher.SetCheckerOptions( self._checker_options )
            watcher.SetFileImportOptions( self._file_import_options )
            watcher.SetTagImportOptions( self._tag_import_options )
            
            publish_to_page = False
            
            watcher.Start( self._page_key, publish_to_page )
            
            self._AddWatcher( watcher )
            
        
        return watcher
        
    
    def AddWatcher( self, watcher ):
        
        with self._lock:
            
            self._AddWatcher( watcher )
            
            self._SetDirty()
            
        
    
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
            
        
    
    def GetNumDead( self ):
        
        with self._lock:
            
            return len( [ watcher for watcher in self._watchers if watcher.IsDead() ] )
            
        
    
    def GetNumWatchers( self ):
        
        with self._lock:
            
            return len( self._watchers )
            
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._checker_options, self._file_import_options, self._tag_import_options )
            
        
    
    def GetTotalStatus( self ):
        
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
                
                if HydrusData.TimeHasPassed( added_timestamp + self.ADDED_TIMESTAMP_DURATION ):
                    
                    self._CleanAddedTimestamps()
                    
                else:
                    
                    return 'just added'
                    
                
            
            if watcher_key in self._watcher_keys_to_already_in_timestamps:
                
                already_in_timestamp = self._watcher_keys_to_already_in_timestamps[ watcher_key ]
                
                if HydrusData.TimeHasPassed( already_in_timestamp + self.ADDED_TIMESTAMP_DURATION ):
                    
                    self._CleanAddedTimestamps()
                    
                else:
                    
                    return 'already watching'
                    
                
            
        
        return watcher.GetSimpleStatus()
        
    
    def RemoveWatcher( self, watcher_key ):
        
        with self._lock:
            
            self._RemoveWatcher( watcher_key )
            
            self._SetDirty()
            
        
    
    def SetHighlightedWatcher( self, highlighted_watcher ):
        
        with self._lock:
            
            if highlighted_watcher is None:
                
                self._highlighted_watcher_url = None
                
            else:
                
                self._highlighted_watcher_url = highlighted_watcher.GetURL()
                
                highlighted_watcher.PublishToPage( True )
                
            
        
    
    def SetOptions( self, checker_options, file_import_options, tag_import_options ):
        
        with self._lock:
            
            self._checker_options = checker_options
            self._file_import_options = file_import_options
            self._tag_import_options = tag_import_options
            
        
    
    def Start( self, page_key ):
        
        with self._lock:
            
            self._page_key = page_key
            
        
        # set a 2s period so the page value/range is breddy snappy
        self._watchers_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), 2.0, self.REPEATINGWorkOnWatchers )
        
        for watcher in self._watchers:
            
            publish_to_page = False
            
            if self._highlighted_watcher_url is not None and watcher.GetURL() == self._highlighted_watcher_url:
                
                publish_to_page = True
                
            
            watcher.Start( page_key, publish_to_page )
            
        
    
    def REPEATINGWorkOnWatchers( self ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( self._page_key ):
                
                self._watchers_repeating_job.Cancel()
                
                return
                
            
            if not self._status_dirty: # if we think we are clean
                
                for watcher in self._watchers:
                    
                    file_seed_cache = watcher.GetFileSeedCache()
                    
                    if file_seed_cache.GetStatusGenerationTime() > self._status_cache_generation_time: # has there has been an update?
                        
                        self._SetDirty()
                        
                        break
                        
                    
                
            
        
        if HydrusData.TimeHasPassed( self._next_pub_value_check_time ):
            
            self._next_pub_value_check_time = HydrusData.GetNow() + 5
            
            current_value_range = self.GetValueRange()
            
            if current_value_range != self._last_pubbed_value_range:
                
                self._last_pubbed_value_range = current_value_range
                
                HG.client_controller.pub( 'refresh_page_name', self._page_key )
                
            
        
        # something like:
            # if any are dead, do some stuff with them based on some options here
            # might want to have this work on a 30s period or something
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MULTIPLE_WATCHER_IMPORT ] = MultipleWatcherImport

class WatcherImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_WATCHER_IMPORT
    SERIALISABLE_NAME = 'Watcher'
    SERIALISABLE_VERSION = 7
    
    MIN_CHECK_PERIOD = 30
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._page_key = 'initialising page key'
        self._publish_to_page = False
        
        self._url = ''
        
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        self._fixed_service_keys_to_tags = ClientTags.ServiceKeysToTags()
        
        self._checker_options = HG.client_controller.new_options.GetDefaultWatcherCheckerOptions()
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        self._tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
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
        
        self._creation_time = HydrusData.GetNow()
        
        self._file_velocity_status = ''
        self._file_status = ''
        self._watcher_status = ''
        
        self._watcher_key = HydrusData.GenerateKey()
        
        self._lock = threading.Lock()
        
        self._last_pubbed_page_name = ''
        
        self._files_repeating_job = None
        self._checker_repeating_job = None
        
        HG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        
    
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
                
                self._watcher_status = text
                
            
        
        def title_hook( text ):
            
            with self._lock:
                
                self._subject = text
                
            
        
        gallery_seed = ClientImportGallerySeeds.GallerySeed( self._url, can_generate_more_pages = False )
        
        gallery_seed.SetFixedServiceKeysToTags( self._fixed_service_keys_to_tags )
        
        self._gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
        
        with self._lock:
            
            self._watcher_status = 'checking'
            
        
        try:
            
            ( num_urls_added, num_urls_already_in_file_seed_cache, num_urls_total, result_404, added_new_gallery_pages, stop_reason ) = gallery_seed.WorkOnURL( 'watcher', self._gallery_seed_log, file_seeds_callable, status_hook, title_hook, self._NetworkJobFactory, self._CheckerNetworkJobPresentationContextFactory, self._file_import_options )
            
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
            
            delay = HG.client_controller.new_options.GetInteger( 'downloader_network_error_delay' )
            
            self._DelayWork( delay, str( e ) )
            
            HydrusData.PrintException( e )
            
        
        watcher_status = gallery_seed.note
        watcher_status_should_stick = gallery_seed.status != CC.STATUS_SUCCESSFUL_AND_NEW
        
        with self._lock:
            
            if self._check_now:
                
                self._check_now = False
                
            
            self._watcher_status = watcher_status
            
            self._last_check_time = HydrusData.GetNow()
            
            self._UpdateFileVelocityStatus()
            
            self._UpdateNextCheckTime()
            
            self._Compact()
            
        
        if not watcher_status_should_stick:
            
            time.sleep( 5 )
            
            with self._lock:
                
                self._watcher_status = ''
                
            
        
    
    def _Compact( self ):
        
        death_period = self._checker_options.GetDeathFileVelocityPeriod()
        
        compact_before_this_time = self._last_check_time - ( death_period * 2 )
        
        self._gallery_seed_log.Compact( compact_before_this_time )
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusData.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
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
        
        serialisable_fixed_service_keys_to_tags = self._fixed_service_keys_to_tags.GetSerialisableTuple()
        
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( self._url, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_fixed_service_keys_to_tags, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, self._last_check_time, self._files_paused, self._checking_paused, self._checking_status, self._subject, self._no_work_until, self._no_work_until_reason, self._creation_time )
        
    
    def _HasURL( self ):
        
        return self._url != ''
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._url, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_fixed_service_keys_to_tags, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, self._last_check_time, self._files_paused, self._checking_paused, self._checking_status, self._subject, self._no_work_until, self._no_work_until_reason, self._creation_time ) = serialisable_info
        
        self._fixed_service_keys_to_tags = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_fixed_service_keys_to_tags )
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _UpdateFileVelocityStatus( self ):
        
        self._file_velocity_status = self._checker_options.GetPrettyCurrentVelocity( self._file_seed_cache, self._last_check_time )
        
    
    def _UpdateNextCheckTime( self ):
        
        if self._check_now:
            
            self._next_check_time = self._last_check_time + self.MIN_CHECK_PERIOD
            
        else:
            
            if not HydrusData.TimeHasPassed( self._no_work_until ):
                
                self._next_check_time = self._no_work_until + 1
                
            else:
                
                if self._checking_status == ClientImporting.CHECKER_STATUS_OK:
                    
                    if self._checker_options.IsDead( self._file_seed_cache, self._last_check_time ):
                        
                        self._checking_status = ClientImporting.CHECKER_STATUS_DEAD
                        
                    
                
                if self._checking_status != ClientImporting.CHECKER_STATUS_OK:
                    
                    self._checking_paused = True
                    
                
                last_next_check_time = self._next_check_time
                
                self._next_check_time = self._checker_options.GetNextCheckTime( self._file_seed_cache, self._last_check_time, last_next_check_time )
                
            
        
    
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
            
            creation_time = HydrusData.GetNow()
            
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
            
            fixed_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
            serialisable_fixed_service_keys_to_tags = fixed_service_keys_to_tags.GetSerialisableTuple()
            
            new_serialisable_info = ( url, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_fixed_service_keys_to_tags, serialisable_checker_options, serialisable_file_import_options, serialisable_tag_import_options, last_check_time, files_paused, checking_paused, checking_status, subject, no_work_until, no_work_until_reason, creation_time )
            
            return ( 7, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        def status_hook( text ):
            
            with self._lock:
                
                self._file_status = text
                
            
        
        did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, self._NetworkJobFactory, self._FileNetworkJobPresentationContextFactory, self._file_import_options, self._tag_import_options )
        
        with self._lock:
            
            should_present = self._publish_to_page and file_seed.ShouldPresent( self._file_import_options )
            
            page_key = self._page_key
            
        
        if should_present:
            
            file_seed.PresentToPage( page_key )
            
            did_substantial_work = True
            
        
        with self._lock:
            
            self._file_status = ''
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def CanRetryFailed( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR ) > 0
            
        
    
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
            
            return self._file_seed_cache.GetHashes()
            
        
    
    def GetNetworkJobs( self ):
        
        with self._lock:
            
            return ( self._file_network_job, self._checker_network_job )
            
        
    
    def GetNewHashes( self ):
        
        with self._lock:
            
            file_import_options = ClientImportOptions.FileImportOptions()
            
            file_import_options.SetPresentationOptions( True, False, False )
            
            return self._file_seed_cache.GetPresentedHashes( file_import_options )
            
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._url, self._file_import_options, self._tag_import_options )
            
        
    
    def GetPresentedHashes( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetPresentedHashes( self._file_import_options )
            
        
    
    def GetSimpleStatus( self ):
        
        with self._lock:
            
            if self._checking_status == ClientImporting.CHECKER_STATUS_404:
                
                return '404'
                
            elif self._checking_status == ClientImporting.CHECKER_STATUS_DEAD:
                
                return 'DEAD'
                
            elif not HydrusData.TimeHasPassed( self._no_work_until ):
                
                return self._no_work_until_reason + ' - ' + 'next check ' + HydrusData.TimestampToPrettyTimeDelta( self._next_check_time )
                
            elif self._watcher_status != '':
                
                return self._watcher_status
                
            elif self._file_status != '':
                
                return self._file_status
                
            else:
                
                return ''
                
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            file_status = self._file_status
            
            if self._checking_status == ClientImporting.CHECKER_STATUS_404:
                
                watcher_status = 'URL 404'
                
            elif self._checking_status == ClientImporting.CHECKER_STATUS_DEAD:
                
                watcher_status = 'URL DEAD'
                
            elif not HydrusData.TimeHasPassed( self._no_work_until ):
                
                no_work_text = self._no_work_until_reason + ' - ' + 'next check ' + HydrusData.TimestampToPrettyTimeDelta( self._next_check_time )
                
                file_status = no_work_text
                watcher_status = no_work_text
                
            else:
                
                watcher_status = self._watcher_status
                
            
            return ( file_status, self._files_paused, self._file_velocity_status, self._next_check_time, watcher_status, self._subject, self._checking_status, self._check_now, self._checking_paused )
            
        
    
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
            
        
    
    def PausePlayChecking( self ):
        
        with self._lock:
            
            if self._checking_paused and self._IsDead():
                
                return # watcher is dead, so don't unpause until a checknow event
                
            else:
                
                self._checking_paused = not self._checking_paused
                
                ClientImporting.WakeRepeatingJob( self._checker_repeating_job )
                
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PublishToPage( self, publish_to_page ):
        
        with self._lock:
            
            self._publish_to_page = publish_to_page
            
        
    
    def Repage( self, page_key ):
        
        with self._lock:
            
            self._page_key = page_key
            
        
    
    def RetryFailed( self ):
        
        with self._lock:
            
            self._file_seed_cache.RetryFailures()
            
        
    
    def SetCheckerOptions( self, checker_options ):
        
        with self._lock:
            
            self._checker_options = checker_options
            
            self._UpdateNextCheckTime()
            
            self._UpdateFileVelocityStatus()
            
            ClientImporting.WakeRepeatingJob( self._checker_repeating_job )
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetFixedServiceKeysToTags( self, service_keys_to_tags ):
        
        with self._lock:
            
            self._fixed_service_keys_to_tags = ClientTags.ServiceKeysToTags( service_keys_to_tags )
            
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            self._tag_import_options = tag_import_options
            
        
    
    def SetURL( self, url ):
        
        if url is None:
            
            url = ''
            
        
        if url != '':
            
            url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
            
        
        with self._lock:
            
            self._url = url
            
            ClientImporting.WakeRepeatingJob( self._checker_repeating_job )
            
        
    
    def Start( self, page_key, publish_to_page ):
        
        self._page_key = page_key
        self._publish_to_page = publish_to_page
        
        self._UpdateNextCheckTime()
        
        self._UpdateFileVelocityStatus()
        
        self._files_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles )
        self._checker_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnChecker )
        
        self._files_repeating_job.SetThreadSlotType( 'watcher_files' )
        self._checker_repeating_job.SetThreadSlotType( 'watcher_check' )
        
    
    def REPEATINGWorkOnFiles( self ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( self._page_key ):
                
                self._files_repeating_job.Cancel()
                
                return
                
            
            files_paused = self._files_paused or HG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' )
            work_pending = self._file_seed_cache.WorkToDo() and not files_paused
            no_delays = HydrusData.TimeHasPassed( self._no_work_until )
            page_shown = not HG.client_controller.PageClosedButNotDestroyed( self._page_key )
            network_engine_good = not HG.client_controller.network_engine.IsBusy()
            
            ok_to_work = work_pending and no_delays and page_shown and network_engine_good
            
        
        while ok_to_work:
            
            try:
                
                self._WorkOnFiles()
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if ClientImporting.PageImporterShouldStopWorking( self._page_key ):
                    
                    self._files_repeating_job.Cancel()
                    
                    return
                    
                
                files_paused = self._files_paused or HG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' )
                work_pending = self._file_seed_cache.WorkToDo() and not files_paused
                no_delays = HydrusData.TimeHasPassed( self._no_work_until )
                page_shown = not HG.client_controller.PageClosedButNotDestroyed( self._page_key )
                network_engine_good = not HG.client_controller.network_engine.IsBusy()
                
                ok_to_work = work_pending and no_delays and page_shown and network_engine_good
                
            
        
    
    def REPEATINGWorkOnChecker( self ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( self._page_key ):
                
                self._checker_repeating_job.Cancel()
                
                return
                
            
            checking_paused = self._checking_paused or HG.client_controller.new_options.GetBoolean( 'pause_all_watcher_checkers' )
            
            able_to_check = self._checking_status == ClientImporting.CHECKER_STATUS_OK and self._HasURL() and not checking_paused
            check_due = HydrusData.TimeHasPassed( self._next_check_time )
            no_delays = HydrusData.TimeHasPassed( self._no_work_until )
            page_shown = not HG.client_controller.PageClosedButNotDestroyed( self._page_key )
            network_engine_good = not HG.client_controller.network_engine.IsBusy()
            
            time_to_check = able_to_check and check_due and no_delays and page_shown and network_engine_good
            
        
        if time_to_check:
            
            try:
                
                self._CheckWatchableURL()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_WATCHER_IMPORT ] = WatcherImport
