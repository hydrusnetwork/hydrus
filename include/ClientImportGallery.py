import ClientConstants as CC
import ClientDownloading
import ClientImportFileSeeds
import ClientImportGallerySeeds
import ClientImporting
import ClientImportOptions
import ClientNetworkingJobs
import ClientPaths
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusPaths
import HydrusSerialisable
import threading
import time
import traceback
import wx

class GalleryImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IMPORT
    SERIALISABLE_NAME = 'Gallery Import'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, query, gallery_identifier ):
        
        # eventually move this to be ( name, first_url ). the name will be like 'samus_aran on gelbooru'
        # first_url is all the new system will need
        
        if gallery_identifier is None:
            
            gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART )
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._creation_time = HydrusData.GetNow()
        
        self._query = None
        self._gallery_identifier = gallery_identifier
        
        self._page_key = 'initialising page key'
        self._publish_to_page = False
        
        self._current_page_index = 0
        self._num_urls_found = 0
        
        self._file_limit = HC.options[ 'gallery_file_limit' ]
        
        self._gallery_paused = False
        self._files_paused = False
        
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        self._tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
        
        self._last_gallery_page_hit_timestamp = 0
        
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        self._lock = threading.Lock()
        
        self._gallery_status = ''
        self._gallery_status_can_change_timestamp = 0
        
        self._current_action = ''
        
        self._download_control_file_set = None
        self._download_control_file_clear = None
        
        self._download_control_gallery_set = None
        self._download_control_gallery_clear = None
        
        self._files_repeating_job = None
        self._gallery_repeating_job = None
        
        HG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        
    
    def _AddSearchPage( self, page_index ):
        
        try:
            
            gallery = ClientDownloading.GetGallery( self._gallery_identifier )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            self._files_paused = True
            self._gallery_paused = True
            
            HydrusData.ShowText( 'A downloader could not load its gallery! It has been paused and the full error has been written to the log!' )
            
            return
            
        
        gallery_url = gallery.GetGalleryPageURL( self._query, page_index )
        
        gallery_seed = ClientImportGallerySeeds.GallerySeed( gallery_url, can_generate_more_pages = True )
        
        self._gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusData.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_identifier = self._gallery_identifier.GetSerialisableTuple()
        
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        return ( self._creation_time, self._query, serialisable_gallery_identifier, self._current_page_index, self._num_urls_found, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_seed_log, serialisable_file_seed_cache, self._no_work_until, self._no_work_until_reason )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._creation_time, self._query, serialisable_gallery_identifier, self._current_page_index, self._num_urls_found, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_seed_log, serialisable_file_seed_cache, self._no_work_until, self._no_work_until_reason ) = serialisable_info
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        
    
    def _FileNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                if self._download_control_file_set is not None:
                    
                    wx.CallAfter( self._download_control_file_set, network_job )
                    
                
            
        
        def exit_call():
            
            with self._lock:
                
                if self._download_control_file_clear is not None:
                    
                    wx.CallAfter( self._download_control_file_clear )
                    
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _GalleryNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                if self._download_control_gallery_set is not None:
                    
                    wx.CallAfter( self._download_control_gallery_set, network_job )
                    
                
            
        
        def exit_call():
            
            with self._lock:
                
                if self._download_control_gallery_clear is not None:
                    
                    wx.CallAfter( self._download_control_gallery_clear )
                    
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _SetGalleryStatus( self, status, timeout = None ):
        
        if HydrusData.TimeHasPassed( self._gallery_status_can_change_timestamp ):
            
            self._gallery_status = status
            
            if timeout is not None:
                
                self._gallery_status_can_change_timestamp = HydrusData.GetNow() + timeout
                
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        def network_job_factory( method, url, **kwargs ):
            
            network_job = ClientNetworkingJobs.NetworkJobDownloader( page_key, method, url, **kwargs )
            
            wx.CallAfter( self._download_control_file_set, network_job )
            
            return network_job
            
        
        try:
            
            gallery = ClientDownloading.GetGallery( self._gallery_identifier )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            with self._lock:
                
                self._files_paused = True
                self._gallery_paused = True
                
                HydrusData.ShowText( 'A downloader could not load its gallery! It has been paused and the full error has been written to the log!' )
                
                return
                
            
        
        gallery.SetNetworkJobFactory( network_job_factory )
        
        try:
            
            if file_seed.WorksInNewSystem():
                
                def status_hook( text ):
                    
                    with self._lock:
                        
                        self._current_action = text
                        
                    
                
                did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, ClientImporting.GenerateDownloaderNetworkJobFactory( page_key ), self._FileNetworkJobPresentationContextFactory, self._file_import_options, self._tag_import_options )
                
                if file_seed.ShouldPresent( self._file_import_options ):
                    
                    file_seed.PresentToPage( page_key )
                    
                    did_substantial_work = True
                    
                
            else:
                
                with self._lock:
                    
                    self._current_action = 'reviewing file'
                    
                
                file_seed.PredictPreImportStatus( self._file_import_options, self._tag_import_options )
                
                status = file_seed.status
                
                url = file_seed.file_seed_data
                
                if status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                    
                    if self._tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB() and self._tag_import_options.WorthFetchingTags():
                        
                        downloaded_tags = gallery.GetTags( url )
                        
                        file_seed.AddTags( downloaded_tags )
                        
                    
                elif status == CC.STATUS_UNKNOWN:
                    
                    ( os_file_handle, temp_path ) = ClientPaths.GetTempPath()
                    
                    try:
                        
                        with self._lock:
                            
                            self._current_action = 'downloading file'
                            
                        
                        if self._tag_import_options.WorthFetchingTags():
                            
                            downloaded_tags = gallery.GetFileAndTags( temp_path, url )
                            
                            file_seed.AddTags( downloaded_tags )
                            
                        else:
                            
                            gallery.GetFile( temp_path, url )
                            
                        
                        file_seed.CheckPreFetchMetadata( self._tag_import_options )
                        
                        with self._lock:
                            
                            self._current_action = 'importing file'
                            
                        
                        file_seed.Import( temp_path, self._file_import_options )
                        
                        did_substantial_work = True
                        
                    finally:
                        
                        HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                        
                    
                
                did_substantial_work = file_seed.WriteContentUpdates( self._tag_import_options )
                
                if file_seed.ShouldPresent( self._file_import_options ):
                    
                    file_seed.PresentToPage( page_key )
                    
                    did_substantial_work = True
                    
                
            
        except HydrusExceptions.VetoException as e:
            
            status = CC.STATUS_VETOED
            
            note = HydrusData.ToUnicode( e )
            
            file_seed.SetStatus( status, note = note )
            
            if isinstance( e, HydrusExceptions.CancelledException ):
                
                time.sleep( 2 )
                
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_VETOED
            note = '404'
            
            file_seed.SetStatus( status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            file_seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            self._file_seed_cache.NotifyFileSeedsUpdated( ( file_seed, ) )
            
            if self._download_control_file_clear is not None:
                
                wx.CallAfter( self._download_control_file_clear )
                
            
        
        with self._lock:
            
            self._current_action = ''
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _WorkOnGallery( self, page_key ):
        
        gallery_seed = self._gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
        
        if gallery_seed is None:
            
            return
            
        
        with self._lock:
            
            # if file_limit reached, do nothing
            
            next_gallery_page_hit_timestamp = self._last_gallery_page_hit_timestamp + HG.client_controller.new_options.GetInteger( 'gallery_page_wait_period_pages' )
            
            if not HydrusData.TimeHasPassed( next_gallery_page_hit_timestamp ):
                
                if self._current_page_index == 0:
                    
                    page_check_status = 'checking first page ' + HydrusData.TimestampToPrettyTimeDelta( next_gallery_page_hit_timestamp )
                    
                else:
                    
                    page_check_status = 'checking next page ' + HydrusData.TimestampToPrettyTimeDelta( next_gallery_page_hit_timestamp )
                    
                
                self._SetGalleryStatus( self._query + ': ' + page_check_status )
                
                return
                
            
            self._SetGalleryStatus( self._query + ': ' + 'now checking next page' )
            
        
        def network_job_factory( method, url, **kwargs ):
            
            network_job = ClientNetworkingJobs.NetworkJobDownloader( page_key, method, url, **kwargs )
            
            network_job.OverrideBandwidth( 30 )
            
            if self._download_control_gallery_set is not None:
                
                wx.CallAfter( self._download_control_gallery_set, network_job )
                
            
            return network_job
            
        
        if gallery_seed.WorksInNewSystem():
            
            def status_hook( text ):
                
                with self._lock:
                    
                    self._current_action = text
                    
                
            
            def title_hook( text ):
                
                return
                
            
            network_job_factory = ClientImporting.GenerateDownloaderNetworkJobFactory( page_key )
            network_job_presentation_context_factory = self._GalleryNetworkJobPresentationContextFactory
            
            if self._file_limit is None:
                
                max_new_urls_allowed = None
                
            else:
                
                max_new_urls_allowed = self._file_limit - self._num_urls_found
                
            
            gallery_seed.WorkOnURL( self._gallery_seed_log, self._file_seed_cache, status_hook, title_hook, network_job_factory, network_job_presentation_context_factory, self._file_import_options, max_new_urls_allowed = max_new_urls_allowed )
            
        else:
            
            try:
                
                gallery = ClientDownloading.GetGallery( self._gallery_identifier )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                with self._lock:
                    
                    self._files_paused = True
                    self._gallery_paused = True
                    
                    HydrusData.ShowText( 'A downloader could not load its gallery! It has been paused and the full error has been written to the log!' )
                    
                    return False
                    
                
            
            gallery.SetNetworkJobFactory( network_job_factory )
            
            error_occurred = False
            
            num_already_in_file_seed_cache = 0
            new_file_seeds = []
            
            try:
                
                try:
                    
                    gallery_url = gallery_seed.url
                    
                    ( page_of_file_seeds, definitely_no_more_pages ) = gallery.GetPage( gallery_url )
                    
                finally:
                    
                    self._last_gallery_page_hit_timestamp = HydrusData.GetNow()
                    
                
                for file_seed in page_of_file_seeds:
                    
                    if self._file_seed_cache.HasFileSeed( file_seed ):
                        
                        num_already_in_file_seed_cache += 1
                        
                    else:
                        
                        with self._lock:
                            
                            if self._file_limit is not None and self._num_urls_found + 1 > self._file_limit:
                                
                                break
                                
                            
                        
                        new_file_seeds.append( file_seed )
                        
                    
                
                with self._lock:
                    
                    no_urls_found = len( page_of_file_seeds ) == 0
                    
                    no_new_urls = len( new_file_seeds ) == 0
                    
                    if definitely_no_more_pages or no_urls_found or no_new_urls:
                        
                        pass # dead search
                        
                    else:
                        
                        self._current_page_index += 1
                        
                        self._AddSearchPage( self._current_page_index )
                        
                    
                
                status = self._query + ': ' + HydrusData.ToHumanInt( len( new_file_seeds ) ) + ' new urls found'
                
                if num_already_in_file_seed_cache > 0:
                    
                    status += ' (' + HydrusData.ToHumanInt( num_already_in_file_seed_cache ) + ' of last page already in queue)'
                    
                
                gallery_seed_status = CC.STATUS_SUCCESSFUL_AND_NEW
                gallery_seed_note = status
                
                if len( new_file_seeds ) > 0:
                    
                    ClientImporting.WakeRepeatingJob( self._files_repeating_job )
                    
                
            except Exception as e:
                
                if isinstance( e, HydrusExceptions.NotFoundException ):
                    
                    text = 'gallery 404'
                    
                    gallery_seed_status = CC.STATUS_VETOED
                    gallery_seed_note = text
                    
                else:
                    
                    text = HydrusData.ToUnicode( e )
                    
                    gallery_seed_status = CC.STATUS_ERROR
                    gallery_seed_note = text
                    
                    HydrusData.DebugPrint( traceback.format_exc() )
                    
                
                error_occurred = True
                
            finally:
                
                if self._download_control_gallery_clear is not None:
                    
                    wx.CallAfter( self._download_control_gallery_clear )
                    
                
            
            gallery_seed.SetStatus( gallery_seed_status, note = gallery_seed_note )
            
            
            
            self._gallery_seed_log.NotifyGallerySeedsUpdated( ( gallery_seed, ) )
            
            self._gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
            
        
        with self._lock:
            
            status = gallery_seed_note
            
            if error_occurred:
                
                self._SetGalleryStatus( status, 5 )
                
            else:
                
                self._SetGalleryStatus( status )
                
            
        
        return True
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._file_seed_cache.WorkToDo()
            
            return not finished and not self._files_paused
            
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetGalleryIdentifier( self ):
        
        return self._gallery_identifier
        
    
    def GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._file_import_options, self._tag_import_options, self._file_limit )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._gallery_status, self._current_action, self._files_paused, self._gallery_paused )
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetValueRange()
            
        
    
    def InitialiseFirstSearchPage( self ):
        
        with self._lock:
            
            self._AddSearchPage( 0 )
            
        
    
    def NotifyFileSeedsUpdated( self, file_seed_cache_key, file_seeds ):
        
        if file_seed_cache_key == self._file_seed_cache.GetFileSeedCacheKey():
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlayGallery( self ):
        
        with self._lock:
            
            self._gallery_paused = not self._gallery_paused
            
            ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
            
        
    
    def Repage( self, page_key, publish_to_page ):
        
        with self._lock:
            
            self._page_key = page_key
            self._publish_to_page = publish_to_page
            
        
    
    def SetDownloadControls( self, file_download_control, gallery_download_control ):
        
        with self._lock:
            
            self._download_control_file_set = file_download_control.SetNetworkJob
            self._download_control_file_clear = file_download_control.ClearNetworkJob
            
            self._download_control_gallery_set = gallery_download_control.SetNetworkJob
            self._download_control_gallery_clear = gallery_download_control.ClearNetworkJob
            
        
    
    def SetFileLimit( self, file_limit ):
        
        with self._lock:
            
            self._file_limit = file_limit
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            self._tag_import_options = tag_import_options
            
        
    
    def Start( self, page_key, publish_to_page ):
        
        self._page_key = page_key
        self._publish_to_page = publish_to_page
        
        self._files_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles )
        self._gallery_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnGallery )
        
    
    def REPEATINGWorkOnFiles( self ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( self._page_key ):
                
                self._files_repeating_job.Cancel()
                
                return
                
            
            work_pending = self._file_seed_cache.WorkToDo() and not self._files_paused
            no_delays = HydrusData.TimeHasPassed( self._no_work_until )
            page_shown = not HG.client_controller.PageClosedButNotDestroyed( self._page_key )
            
            ok_to_work = work_pending and no_delays and page_shown
            
        
        while ok_to_work:
            
            try:
                
                self._WorkOnFiles( self._page_key )
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if ClientImporting.PageImporterShouldStopWorking( self._page_key ):
                    
                    self._files_repeating_job.Cancel()
                    
                    return
                    
                
                work_pending = self._file_seed_cache.WorkToDo() and not self._files_paused
                no_delays = HydrusData.TimeHasPassed( self._no_work_until )
                page_shown = not HG.client_controller.PageClosedButNotDestroyed( self._page_key )
                
                ok_to_work = work_pending and no_delays and page_shown
                
            
        
    
    def REPEATINGWorkOnGallery( self ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( self._page_key ):
                
                self._gallery_repeating_job.Cancel()
                
                return
                
            
            work_pending = self._gallery_seed_log.WorkToDo() and not self._gallery_paused
            no_delays = HydrusData.TimeHasPassed( self._no_work_until )
            page_shown = not HG.client_controller.PageClosedButNotDestroyed( self._page_key )
            
            ok_to_work = work_pending and no_delays and page_shown
            
        
        while ok_to_work:
            
            try:
                
                self._WorkOnGallery( self._page_key )
                
                time.sleep( 1 )
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if ClientImporting.PageImporterShouldStopWorking( self._page_key ):
                    
                    self._gallery_repeating_job.Cancel()
                    
                    return
                    
                
                work_pending = self._gallery_seed_log.WorkToDo() and not self._gallery_paused
                no_delays = HydrusData.TimeHasPassed( self._no_work_until )
                page_shown = not HG.client_controller.PageClosedButNotDestroyed( self._page_key )
                
                ok_to_work = work_pending and no_delays and page_shown
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IMPORT ] = GalleryImport

class MultipleGalleryImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MULTIPLE_GALLERY_IMPORT
    SERIALISABLE_NAME = 'Multiple Gallery Import'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, gallery_identifier = None ):
        
        if gallery_identifier is None:
            
            gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART )
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._gallery_identifier = gallery_identifier
        
        self._gallery_stream_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( self._gallery_identifier )
        
        self._current_query = None
        self._current_query_num_new_urls = 0
        self._current_query_num_urls = 0
        
        self._current_gallery_stream_identifier = None
        self._current_gallery_stream_identifier_page_index = 0
        self._current_gallery_stream_identifier_found_urls = set()
        
        self._pending_gallery_stream_identifiers = []
        
        self._pending_queries = []
        
        new_options = HG.client_controller.new_options
        
        self._file_limit = HC.options[ 'gallery_file_limit' ]
        self._gallery_paused = False
        self._files_paused = False
        
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        self._tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
        
        self._last_gallery_page_hit_timestamp = 0
        
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        self._lock = threading.Lock()
        
        self._gallery = None
        
        self._gallery_status = ''
        self._gallery_status_can_change_timestamp = 0
        
        self._current_action = ''
        
        self._download_control_file_set = None
        self._download_control_file_clear = None
        
        self._download_control_gallery_set = None
        self._download_control_gallery_clear = None
        
        self._files_repeating_job = None
        self._gallery_repeating_job = None
        
        HG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_identifier = self._gallery_identifier.GetSerialisableTuple()
        serialisable_gallery_stream_identifiers = [ gallery_stream_identifier.GetSerialisableTuple() for gallery_stream_identifier in self._gallery_stream_identifiers ]
        
        if self._current_gallery_stream_identifier is None:
            
            serialisable_current_gallery_stream_identifier = None
            
        else:
            
            serialisable_current_gallery_stream_identifier = self._current_gallery_stream_identifier.GetSerialisableTuple()
            
        
        serialisable_current_gallery_stream_identifier_found_urls = list( self._current_gallery_stream_identifier_found_urls )
        
        serialisable_pending_gallery_stream_identifiers = [ pending_gallery_stream_identifier.GetSerialisableTuple() for pending_gallery_stream_identifier in self._pending_gallery_stream_identifiers ]
        
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        serialisable_current_query_stuff = ( self._current_query, self._current_query_num_new_urls, serialisable_current_gallery_stream_identifier, self._current_gallery_stream_identifier_page_index, serialisable_current_gallery_stream_identifier_found_urls, serialisable_pending_gallery_stream_identifiers )
        
        return ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, self._pending_queries, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_seed_log, serialisable_file_seed_cache )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, self._pending_queries, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_seed_log, serialisable_file_seed_cache ) = serialisable_info
        
        ( self._current_query, self._current_query_num_new_urls, serialisable_current_gallery_stream_identifier, self._current_gallery_stream_identifier_page_index, serialisable_current_gallery_stream_identifier_found_urls, serialisable_pending_gallery_stream_identifier ) = serialisable_current_query_stuff
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        
        self._gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_stream_identifier ) for serialisable_gallery_stream_identifier in serialisable_gallery_stream_identifiers ]
        
        if serialisable_current_gallery_stream_identifier is None:
            
            self._current_gallery_stream_identifier = None
            
        else:
            
            self._current_gallery_stream_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_current_gallery_stream_identifier )
            
        
        self._current_gallery_stream_identifier_found_urls = set( serialisable_current_gallery_stream_identifier_found_urls )
        
        self._pending_gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_pending_gallery_stream_identifier ) for serialisable_pending_gallery_stream_identifier in serialisable_pending_gallery_stream_identifier ]
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        
    
    def _FileNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                if self._download_control_file_set is not None:
                    
                    wx.CallAfter( self._download_control_file_set, network_job )
                    
                
            
        
        def exit_call():
            
            with self._lock:
                
                if self._download_control_file_clear is not None:
                    
                    wx.CallAfter( self._download_control_file_clear )
                    
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _SetGalleryStatus( self, status, timeout = None ):
        
        if HydrusData.TimeHasPassed( self._gallery_status_can_change_timestamp ):
            
            self._gallery_status = status
            
            if timeout is not None:
                
                self._gallery_status_can_change_timestamp = HydrusData.GetNow() + timeout
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, pending_queries, get_tags_if_url_recognised_and_file_redundant, file_limit, gallery_paused, files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_file_seed_cache ) = old_serialisable_info
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, pending_queries, file_limit, gallery_paused, files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_file_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, pending_queries, file_limit, gallery_paused, files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_file_seed_cache ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, pending_queries, file_limit, gallery_paused, files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_seed_log, serialisable_file_seed_cache )
            
            return ( 3, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        def network_job_factory( method, url, **kwargs ):
            
            network_job = ClientNetworkingJobs.NetworkJobDownloader( page_key, method, url, **kwargs )
            
            wx.CallAfter( self._download_control_file_set, network_job )
            
            return network_job
            
        
        try:
            
            gallery = ClientDownloading.GetGallery( self._gallery_identifier )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            with self._lock:
                
                self._files_paused = True
                self._gallery_paused = True
                
                HydrusData.ShowText( 'A downloader could not load its gallery! It has been paused and the full error has been written to the log!' )
                
                return
                
            
        
        gallery.SetNetworkJobFactory( network_job_factory )
        
        try:
            
            if file_seed.WorksInNewSystem():
                
                def status_hook( text ):
                    
                    with self._lock:
                        
                        self._current_action = text
                        
                    
                
                did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, ClientImporting.GenerateDownloaderNetworkJobFactory( page_key ), self._FileNetworkJobPresentationContextFactory, self._file_import_options, self._tag_import_options )
                
                if file_seed.ShouldPresent( self._file_import_options ):
                    
                    file_seed.PresentToPage( page_key )
                    
                    did_substantial_work = True
                    
                
            else:
                
                with self._lock:
                    
                    self._current_action = 'reviewing file'
                    
                
                file_seed.PredictPreImportStatus( self._file_import_options, self._tag_import_options )
                
                status = file_seed.status
                
                url = file_seed.file_seed_data
                
                if status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                    
                    if self._tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB() and self._tag_import_options.WorthFetchingTags():
                        
                        downloaded_tags = gallery.GetTags( url )
                        
                        file_seed.AddTags( downloaded_tags )
                        
                    
                elif status == CC.STATUS_UNKNOWN:
                    
                    ( os_file_handle, temp_path ) = ClientPaths.GetTempPath()
                    
                    try:
                        
                        with self._lock:
                            
                            self._current_action = 'downloading file'
                            
                        
                        if self._tag_import_options.WorthFetchingTags():
                            
                            downloaded_tags = gallery.GetFileAndTags( temp_path, url )
                            
                            file_seed.AddTags( downloaded_tags )
                            
                        else:
                            
                            gallery.GetFile( temp_path, url )
                            
                        
                        file_seed.CheckPreFetchMetadata( self._tag_import_options )
                        
                        with self._lock:
                            
                            self._current_action = 'importing file'
                            
                        
                        file_seed.Import( temp_path, self._file_import_options )
                        
                        did_substantial_work = True
                        
                    finally:
                        
                        HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                        
                    
                
                did_substantial_work = file_seed.WriteContentUpdates( self._tag_import_options )
                
                if file_seed.ShouldPresent( self._file_import_options ):
                    
                    file_seed.PresentToPage( page_key )
                    
                    did_substantial_work = True
                    
                
            
        except HydrusExceptions.VetoException as e:
            
            status = CC.STATUS_VETOED
            
            note = HydrusData.ToUnicode( e )
            
            file_seed.SetStatus( status, note = note )
            
            if isinstance( e, HydrusExceptions.CancelledException ):
                
                time.sleep( 2 )
                
            
        except HydrusExceptions.NotFoundException:
            
            status = CC.STATUS_VETOED
            note = '404'
            
            file_seed.SetStatus( status, note = note )
            
            time.sleep( 2 )
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            file_seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            self._file_seed_cache.NotifyFileSeedsUpdated( ( file_seed, ) )
            
            wx.CallAfter( self._download_control_file_clear )
            
        
        with self._lock:
            
            self._current_action = ''
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _WorkOnGallery( self, page_key ):
        
        with self._lock:
            
            if self._current_query is None:
                
                if len( self._pending_queries ) == 0:
                    
                    self._SetGalleryStatus( '' )
                    
                    return False
                    
                else:
                    
                    self._current_query = self._pending_queries.pop( 0 )
                    self._current_query_num_new_urls = 0
                    self._current_query_num_urls = 0
                    
                    self._current_gallery_stream_identifier = None
                    self._pending_gallery_stream_identifiers = list( self._gallery_stream_identifiers )
                    
                
            
            if self._current_gallery_stream_identifier is None:
                
                if len( self._pending_gallery_stream_identifiers ) == 0:
                    
                    self._SetGalleryStatus( self._current_query + ': produced ' + HydrusData.ToHumanInt( self._current_query_num_new_urls ) + ' new urls', 5 )
                    
                    self._current_query = None
                    
                    return False
                    
                else:
                    
                    self._current_gallery_stream_identifier = self._pending_gallery_stream_identifiers.pop( 0 )
                    self._current_gallery_stream_identifier_page_index = 0
                    self._current_gallery_stream_identifier_found_urls = set()
                    
                
            
            next_gallery_page_hit_timestamp = self._last_gallery_page_hit_timestamp + HG.client_controller.new_options.GetInteger( 'gallery_page_wait_period_pages' )
            
            if not HydrusData.TimeHasPassed( next_gallery_page_hit_timestamp ):
                
                if self._current_gallery_stream_identifier_page_index == 0:
                    
                    page_check_status = 'checking first page ' + HydrusData.TimestampToPrettyTimeDelta( next_gallery_page_hit_timestamp )
                    
                else:
                    
                    page_check_status = HydrusData.ToHumanInt( self._current_query_num_new_urls ) + ' new urls found, checking next page ' + HydrusData.TimestampToPrettyTimeDelta( next_gallery_page_hit_timestamp )
                    
                
                self._SetGalleryStatus( self._current_query + ': ' + page_check_status )
                
                return True
                
            
            def network_job_factory( method, url, **kwargs ):
                
                network_job = ClientNetworkingJobs.NetworkJobDownloader( page_key, method, url, **kwargs )
                
                network_job.OverrideBandwidth( 30 )
                
                wx.CallAfter( self._download_control_gallery_set, network_job )
                
                return network_job
                
            
            try:
                
                gallery = ClientDownloading.GetGallery( self._current_gallery_stream_identifier )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                with self._lock:
                    
                    self._files_paused = True
                    self._gallery_paused = True
                    
                    HydrusData.ShowText( 'A downloader could not load its gallery! It has been paused and the full error has been written to the log!' )
                    
                    return False
                    
                
            
            gallery.SetNetworkJobFactory( network_job_factory )
            
            query = self._current_query
            page_index = self._current_gallery_stream_identifier_page_index
            
            self._SetGalleryStatus( self._current_query + ': ' + HydrusData.ToHumanInt( self._current_query_num_new_urls ) + ' new urls found, now checking page ' + HydrusData.ToHumanInt( self._current_gallery_stream_identifier_page_index + 1 ) )
            
        
        error_occurred = False
        
        num_already_in_file_seed_cache = 0
        new_file_seeds = []
        
        try:
            
            gallery_url = gallery.GetGalleryPageURL( query, page_index )
            
            # can_generate_more_pages = if recognised in the new system, I guess
            
            gallery_seed = ClientImportGallerySeeds.GallerySeed( gallery_url, can_generate_more_pages = False )
            
            self._gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
            
            try:
                
                ( page_of_file_seeds, definitely_no_more_pages ) = gallery.GetPage( gallery_url )
                
            finally:
                
                self._last_gallery_page_hit_timestamp = HydrusData.GetNow()
                
            
            with self._lock:
                
                no_urls_found = len( page_of_file_seeds ) == 0
                
                page_of_urls = [ file_seed.file_seed_data for file_seed in page_of_file_seeds ]
                no_new_urls = len( self._current_gallery_stream_identifier_found_urls.intersection( page_of_urls ) ) == len( page_of_file_seeds )
                
                if definitely_no_more_pages or no_urls_found or no_new_urls:
                    
                    self._current_gallery_stream_identifier = None
                    
                else:
                    
                    self._current_gallery_stream_identifier_page_index += 1
                    self._current_gallery_stream_identifier_found_urls.update( page_of_urls )
                    
                
            
            for file_seed in page_of_file_seeds:
                
                if self._file_seed_cache.HasFileSeed( file_seed ):
                    
                    num_already_in_file_seed_cache += 1
                    
                else:
                    
                    with self._lock:
                        
                        num_urls_estimate = max( self._current_query_num_new_urls, self._current_query_num_urls )
                        
                        if self._file_limit is not None and num_urls_estimate + 1 > self._file_limit:
                            
                            self._current_gallery_stream_identifier = None
                            
                            self._pending_gallery_stream_identifiers = []
                            
                            break
                            
                        
                    
                    self._current_query_num_urls += 1
                
                    self._current_query_num_new_urls += 1
                    
                    new_file_seeds.append( file_seed )
                    
                
            
            num_urls_added = self._file_seed_cache.AddFileSeeds( new_file_seeds )
            
            status = query + ': ' + HydrusData.ToHumanInt( len( new_file_seeds ) ) + ' new urls found'
            
            if num_already_in_file_seed_cache > 0:
                
                status += ' (' + HydrusData.ToHumanInt( num_already_in_file_seed_cache ) + ' of last page already in queue)'
                
            
            gallery_seed_status = CC.STATUS_SUCCESSFUL_AND_NEW
            gallery_seed_note = status
            
            if len( new_file_seeds ) > 0:
                
                ClientImporting.WakeRepeatingJob( self._files_repeating_job )
                
            
        except Exception as e:
            
            if isinstance( e, HydrusExceptions.NotFoundException ):
                
                text = 'gallery 404'
                
                gallery_seed_status = CC.STATUS_VETOED
                gallery_seed_note = text
                
            else:
                
                text = HydrusData.ToUnicode( e )
                
                gallery_seed_status = CC.STATUS_ERROR
                gallery_seed_note = text
                
                HydrusData.DebugPrint( traceback.format_exc() )
                
            
            with self._lock:
                
                self._current_gallery_stream_identifier = None
                
            
            error_occurred = True
            
        finally:
            
            wx.CallAfter( self._download_control_gallery_clear )
            
        
        gallery_seed.SetStatus( gallery_seed_status, note = gallery_seed_note )
        
        self._gallery_seed_log.NotifyGallerySeedsUpdated( ( gallery_seed, ) )
        
        with self._lock:
            
            status = gallery_seed_note
            
            if error_occurred:
                
                self._SetGalleryStatus( status, 5 )
                
            else:
                
                self._SetGalleryStatus( status )
                
            
        
        return True
        
    
    def AdvanceQueries( self, queries ):
        
        with self._lock:
            
            queries_lookup = set( queries )
            
            for query in queries:
                
                if query in self._pending_queries:
                    
                    index = self._pending_queries.index( query )
                    
                    if index > 0 and self._pending_queries[ index - 1 ] not in queries_lookup:
                        
                        self._pending_queries.remove( query )
                        
                        self._pending_queries.insert( index - 1, query )
                        
                    
                
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._file_seed_cache.WorkToDo()
            
            return not finished and not self._files_paused
            
        
    
    def DelayQueries( self, queries ):
        
        with self._lock:
            
            queries = list( queries )
            
            queries.reverse()
            
            queries_lookup = set( queries )
            
            for query in queries:
                
                if query in self._pending_queries:
                    
                    index = self._pending_queries.index( query )
                    
                    if index + 1 < len( self._pending_queries ) and self._pending_queries[ index + 1 ] not in queries_lookup:
                        
                        self._pending_queries.remove( query )
                        
                        self._pending_queries.insert( index + 1, query )
                        
                    
                
            
        
    
    def DeleteQueries( self, queries ):
        
        with self._lock:
            
            for query in queries:
                
                if query in self._pending_queries:
                    
                    self._pending_queries.remove( query )
                    
                
            
        
    
    def FinishCurrentQuery( self ):
        
        with self._lock:
            
            self._current_query = None
            self._gallery_paused = False
            
            ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
            
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetGalleryIdentifier( self ):
        
        return self._gallery_identifier
        
    
    def GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._file_import_options, self._tag_import_options, self._file_limit )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            cancellable = self._current_query is not None
            
            return ( list( self._pending_queries ), self._gallery_status, self._current_action, self._files_paused, self._gallery_paused, cancellable )
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetValueRange()
            
        
    
    def NotifyFileSeedsUpdated( self, file_seed_cache_key, file_seeds ):
        
        if file_seed_cache_key == self._file_seed_cache.GetFileSeedCacheKey():
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlayGallery( self ):
        
        with self._lock:
            
            self._gallery_paused = not self._gallery_paused
            
            ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
            
        
    
    def PendQuery( self, query ):
        
        with self._lock:
            
            if query not in self._pending_queries:
                
                self._pending_queries.append( query )
                
                ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
                
            
        
    
    def SetDownloadControls( self, file_download_control, gallery_download_control ):
        
        with self._lock:
            
            self._download_control_file_set = file_download_control.SetNetworkJob
            self._download_control_file_clear = file_download_control.ClearNetworkJob
            
            self._download_control_gallery_set = gallery_download_control.SetNetworkJob
            self._download_control_gallery_clear = gallery_download_control.ClearNetworkJob
            
        
    
    def SetFileLimit( self, file_limit ):
        
        with self._lock:
            
            self._file_limit = file_limit
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            self._tag_import_options = tag_import_options
            
        
    
    def Start( self, page_key ):
        
        self._files_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles, page_key )
        self._gallery_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnGallery, page_key )
        
    
    def REPEATINGWorkOnFiles( self, page_key ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( page_key ):
                
                self._files_repeating_job.Cancel()
                
                return
                
            
            work_to_do = self._file_seed_cache.WorkToDo() and not ( self._files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
            
        
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
                    
                
                work_to_do = self._file_seed_cache.WorkToDo() and not ( self._files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                
            
        
    
    def REPEATINGWorkOnGallery( self, page_key ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( page_key ):
                
                self._gallery_repeating_job.Cancel()
                
                return
                
            
            ok_to_work = not ( self._gallery_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
            
        
        while ok_to_work:
            
            try:
                
                work_to_do = self._WorkOnGallery( page_key )
                
                if work_to_do:
                    
                    time.sleep( 1 )
                    
                else:
                    
                    return
                    
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if ClientImporting.PageImporterShouldStopWorking( page_key ):
                    
                    self._gallery_repeating_job.Cancel()
                    
                    return
                    
                
                ok_to_work = not ( self._gallery_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MULTIPLE_GALLERY_IMPORT ] = MultipleGalleryImport
