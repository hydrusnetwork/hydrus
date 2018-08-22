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
    
    def __init__( self, query = None, gallery_identifier = None ):
        
        # eventually move this to be ( name, first_url ). the name will be like 'samus_aran on gelbooru'
        # then queue up a first url
        
        if query is None:
            
            query = 'samus_aran'
            
        
        if gallery_identifier is None:
            
            gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART )
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._creation_time = HydrusData.GetNow()
        self._gallery_import_key = HydrusData.GenerateKey()
        
        self._query = query
        self._gallery_identifier = gallery_identifier
        
        self._page_key = 'initialising page key'
        self._publish_to_page = False
        
        self._current_page_index = 0
        self._num_new_urls_found = 0
        self._num_urls_found = 0
        
        self._file_limit = HC.options[ 'gallery_file_limit' ]
        
        self._gallery_paused = False
        self._files_paused = False
        
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        self._tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
        
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        self._lock = threading.Lock()
        
        self._gallery_status = ''
        self._gallery_status_can_change_timestamp = 0
        
        self._current_action = ''
        
        self._file_network_job = None
        self._gallery_network_job = None
        
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
        
    
    def _AmOverFileLimit( self ):
        
        if self._file_limit is not None and self._num_new_urls_found >= self._file_limit:
            
            return True
            
        
        return False
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusData.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_import_key = self._gallery_import_key.encode( 'hex' )
        
        serialisable_gallery_identifier = self._gallery_identifier.GetSerialisableTuple()
        
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        return ( serialisable_gallery_import_key, self._creation_time, self._query, serialisable_gallery_identifier, self._current_page_index, self._num_urls_found, self._num_new_urls_found, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_seed_log, serialisable_file_seed_cache, self._no_work_until, self._no_work_until_reason )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_import_key, self._creation_time, self._query, serialisable_gallery_identifier, self._current_page_index, self._num_urls_found, self._num_new_urls_found, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_seed_log, serialisable_file_seed_cache, self._no_work_until, self._no_work_until_reason ) = serialisable_info
        
        self._gallery_import_key = serialisable_gallery_import_key.decode( 'hex' )
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        
    
    def _FileNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                self._file_network_job = network_job
                
            
        
        def exit_call():
            
            with self._lock:
                
                self._file_network_job = None
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _GalleryNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                self._gallery_network_job = network_job
                
            
        
        def exit_call():
            
            with self._lock:
                
                self._gallery_network_job = None
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _NetworkJobFactory( self, *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJobDownloader( self._gallery_import_key, *args, **kwargs )
        
        return network_job
        
    
    def _WorkOnFiles( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        try:
            
            if file_seed.WorksInNewSystem():
                
                def status_hook( text ):
                    
                    with self._lock:
                        
                        self._current_action = text
                        
                    
                
                did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, self._NetworkJobFactory, self._FileNetworkJobPresentationContextFactory, self._file_import_options, self._tag_import_options )
                
                with self._lock:
                    
                    should_present = self._publish_to_page and file_seed.ShouldPresent( self._file_import_options )
                    
                    page_key = self._page_key
                    
                
                if should_present:
                    
                    file_seed.PresentToPage( page_key )
                    
                    did_substantial_work = True
                    
                
            else:
                
                def network_job_factory( method, url, **kwargs ):
                    
                    network_job = ClientNetworkingJobs.NetworkJobDownloader( self._gallery_import_key, method, url, **kwargs )
                    
                    with self._lock:
                        
                        self._file_network_job = network_job
                        
                    
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
                
                with self._lock:
                    
                    should_present = self._publish_to_page and file_seed.ShouldPresent( self._file_import_options )
                    
                    page_key = self._page_key
                    
                
                if should_present:
                    
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
            
            with self._lock:
                
                self._file_network_job = None
                
            
        
        with self._lock:
            
            self._current_action = ''
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _WorkOnGallery( self ):
        
        gallery_seed = self._gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
        
        if gallery_seed is None:
            
            return
            
        
        with self._lock:
            
            if self._AmOverFileLimit():
                
                self._gallery_paused = True
                
                self._gallery_status = ''
                
                return
                
            
            self._gallery_status = 'checking next page'
            
        
        if gallery_seed.WorksInNewSystem():
            
            def file_seeds_callable( file_seeds ):
                
                if self._file_limit is None:
                    
                    max_new_urls_allowed = None
                    
                else:
                    
                    max_new_urls_allowed = self._file_limit - self._num_new_urls_found
                    
                
                return ClientImporting.UpdateFileSeedCacheWithFileSeeds( self._file_seed_cache, file_seeds, max_new_urls_allowed )
                
            
            def status_hook( text ):
                
                with self._lock:
                    
                    self._gallery_status = text
                    
                
            
            def title_hook( text ):
                
                return
                
            
            try:
                
                ( num_urls_added, num_urls_already_in_file_seed_cache, num_urls_total, result_404, can_add_more_file_urls, stop_reason ) = gallery_seed.WorkOnURL( 'download page', self._gallery_seed_log, file_seeds_callable, status_hook, title_hook, self._NetworkJobFactory, self._GalleryNetworkJobPresentationContextFactory, self._file_import_options )
                
                self._num_new_urls_found += num_urls_added
                self._num_urls_found += num_urls_total
                
                if num_urls_added > 0:
                    
                    ClientImporting.WakeRepeatingJob( self._files_repeating_job )
                    
                
                self._current_page_index += 1
                
            except HydrusExceptions.NetworkException as e:
                
                with self._lock:
                    
                    self._DelayWork( 4 * 3600, HydrusData.ToUnicode( e ) )
                    
                
                return
                
            except Exception as e:
                
                gallery_seed_status = CC.STATUS_ERROR
                gallery_seed_note = HydrusData.ToUnicode( e )
                
                gallery_seed.SetStatus( gallery_seed_status, note = gallery_seed_note )
                
                HydrusData.PrintException( e )
                
                with self._lock:
                    
                    self._gallery_paused = True
                    
                
            
        else:
            
            def network_job_factory( method, url, **kwargs ):
                
                network_job = ClientNetworkingJobs.NetworkJobDownloader( self._gallery_import_key, method, url, **kwargs )
                
                network_job.SetGalleryToken( 'download page' )
                
                network_job.OverrideBandwidth( 30 )
                
                with self._lock:
                    
                    self._gallery_network_job = network_job
                    
                
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
            
            num_already_in_file_seed_cache = 0
            new_file_seeds = []
            
            try:
                
                gallery_url = gallery_seed.url
                
                ( page_of_file_seeds, definitely_no_more_pages ) = gallery.GetPage( gallery_url )
                
                
                # do files
                
                for file_seed in page_of_file_seeds:
                    
                    self._num_urls_found += 1
                    
                    if self._file_seed_cache.HasFileSeed( file_seed ):
                        
                        num_already_in_file_seed_cache += 1
                        
                    else:
                        
                        with self._lock:
                            
                            if self._AmOverFileLimit():
                                
                                self._gallery_paused = True
                                
                                break
                                
                            
                        
                        new_file_seeds.append( file_seed )
                        
                        self._num_new_urls_found += 1
                        
                    
                
                num_urls_added = self._file_seed_cache.AddFileSeeds( new_file_seeds )
                
                # do gallery pages
                
                with self._lock:
                    
                    no_urls_found = len( page_of_file_seeds ) == 0
                    
                    no_new_urls = len( new_file_seeds ) == 0
                    
                    am_over_limit = self._AmOverFileLimit()
                    
                    if definitely_no_more_pages or no_urls_found or no_new_urls or am_over_limit:
                        
                        pass # dead search
                        
                    else:
                        
                        self._current_page_index += 1
                        
                        self._AddSearchPage( self._current_page_index )
                        
                    
                
                # report and finish up
                
                status = self._query + ': ' + HydrusData.ToHumanInt( len( new_file_seeds ) ) + ' new urls found'
                
                if num_already_in_file_seed_cache > 0:
                    
                    status += ' (' + HydrusData.ToHumanInt( num_already_in_file_seed_cache ) + ' of last page already in queue)'
                    
                
                if am_over_limit:
                    
                    status += ' - hit file limit'
                    
                
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
                    
                
            finally:
                
                with self._lock:
                    
                    self._gallery_network_job = None
                    
                
            
            gallery_seed.SetStatus( gallery_seed_status, note = gallery_seed_note )
            
        
        self._gallery_seed_log.NotifyGallerySeedsUpdated( ( gallery_seed, ) )
        
        with self._lock:
            
            self._gallery_status = ''
            
        
        return True
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._file_seed_cache.WorkToDo()
            
            return not finished and not self._files_paused
            
        
    
    def FilesPaused( self ):
        
        with self._lock:
            
            return self._files_paused
            
        
    
    def GalleryFinished( self ):
        
        with self._lock:
            
            return not self._gallery_seed_log.WorkToDo()
            
        
    
    def GalleryPaused( self ):
        
        with self._lock:
            
            return self._gallery_paused
            
        
    
    def GetCreationTime( self ):
        
        with self._lock:
            
            return self._creation_time
            
        
    
    def GetCurrentAction( self ):
        
        with self._lock:
            
            return self._current_action
            
        
    
    def GetFileImportOptions( self ):
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetFileSeedCache( self ):
        
        with self._lock:
            
            return self._file_seed_cache
            
        
    
    def GetFileLimit( self ):
        
        with self._lock:
            
            return self._file_limit
            
        
    
    def GetGalleryIdentifier( self ):
        
        with self._lock:
            
            return self._gallery_identifier
            
        
    
    def GetGalleryImportKey( self ):
        
        with self._lock:
            
            return self._gallery_import_key
            
        
    
    def GetGallerySeedLog( self ):
        
        with self._lock:
            
            return self._gallery_seed_log
            
        
    
    def GetGalleryStatus( self ):
        
        with self._lock:
            
            return self._gallery_status
            
        
    
    def GetNetworkJobs( self ):
        
        with self._lock:
            
            return ( self._file_network_job, self._gallery_network_job )
            
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._file_import_options, self._tag_import_options, self._file_limit )
            
        
    
    def GetPresentedHashes( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetPresentedHashes( self._file_import_options )
            
        
    
    def GetQueryText( self ):
        
        with self._lock:
            
            return self._query
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._gallery_status, self._current_action, self._files_paused, self._gallery_paused )
            
        
    
    def GetTagImportOptions( self ):
        
        with self._lock:
            
            return self._tag_import_options
            
        
    
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
            
        
    
    def PublishToPage( self, publish_to_page ):
        
        with self._lock:
            
            self._publish_to_page = publish_to_page
            
        
    
    def Repage( self, page_key ):
        
        with self._lock:
            
            self._page_key = page_key
            
        
    
    def SetFileLimit( self, file_limit ):
        
        with self._lock:
            
            self._file_limit = file_limit
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetFileSeedCache( self, file_seed_cache ):
        
        with self._lock:
            
            self._file_seed_cache = file_seed_cache
            
        
    
    def SetGallerySeedLog( self, gallery_seed_log ):
        
        with self._lock:
            
            self._gallery_seed_log = gallery_seed_log
            
        
    
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
                
                self._WorkOnFiles()
                
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
                
                self._WorkOnGallery()
                
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
                
            
        
        with self._lock:
            
            self._gallery_status = ''
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IMPORT ] = GalleryImport

class MultipleGalleryImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_MULTIPLE_GALLERY_IMPORT
    SERIALISABLE_NAME = 'Multiple Gallery Import'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, gallery_identifier = None ):
        
        if gallery_identifier is None:
            
            gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART )
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._page_key = 'initialising page key'
        
        self._gallery_identifier = gallery_identifier
        
        self._highlighted_gallery_import_key = None
        
        new_options = HG.client_controller.new_options
        
        self._file_limit = HC.options[ 'gallery_file_limit' ]
        
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        self._tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
        
        self._gallery_imports = HydrusSerialisable.SerialisableList()
        
        self._gallery_import_keys_to_gallery_imports = {}
        
        self._status_dirty = True
        self._status_cache = None
        self._status_cache_generation_time = 0
        
        self._last_time_imports_changed = HydrusData.GetNowPrecise()
        
        self._last_pubbed_value_range = ( 0, 0 )
        self._next_pub_value_check_time = 0
        
        self._importers_repeating_job = None
        
    
    def _AddGalleryImport( self, gallery_import ):
        
        gallery_import.PublishToPage( False )
        gallery_import.Repage( self._page_key )
        
        self._gallery_imports.append( gallery_import )
        
        self._last_time_imports_changed = HydrusData.GetNowPrecise()
        
        gallery_import_key = gallery_import.GetGalleryImportKey()
        
        self._gallery_import_keys_to_gallery_imports[ gallery_import_key ] = gallery_import
        
        if len( self._gallery_imports ) == 1: # maybe turn this off as a option for advanced users
            
            self._highlighted_gallery_import_key = gallery_import_key
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_identifier = self._gallery_identifier.GetSerialisableTuple()
        
        if self._highlighted_gallery_import_key is None:
            
            serialisable_highlighted_gallery_import_key = self._highlighted_gallery_import_key
            
        else:
            
            serialisable_highlighted_gallery_import_key = self._highlighted_gallery_import_key.encode( 'hex' )
            
        
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        serialisable_gallery_imports = self._gallery_imports.GetSerialisableTuple()
        
        return ( serialisable_gallery_identifier, serialisable_highlighted_gallery_import_key, self._file_limit, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_imports )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_identifier, serialisable_highlighted_gallery_import_key, self._file_limit, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_imports ) = serialisable_info
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        
        if serialisable_highlighted_gallery_import_key is None:
            
            self._highlighted_gallery_import_key = None
            
        else:
            
            self._highlighted_gallery_import_key = serialisable_highlighted_gallery_import_key.decode( 'hex' )
            
        
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
        self._gallery_imports = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_imports )
        
        self._gallery_import_keys_to_gallery_imports = { gallery_import.GetGalleryImportKey() : gallery_import for gallery_import in self._gallery_imports }
        
    
    def _RegenerateStatus( self ):
        
        file_seed_caches = [ gallery_import.GetFileSeedCache() for gallery_import in self._gallery_imports ]
        
        self._status_cache = ClientImportFileSeeds.GenerateFileSeedCachesStatus( file_seed_caches )
        
        self._status_dirty = False
        self._status_cache_generation_time = HydrusData.GetNow()
        
    
    def _RemoveGalleryImport( self, gallery_import_key ):
        
        if gallery_import_key not in self._gallery_import_keys_to_gallery_imports:
            
            return
            
        
        gallery_import = self._gallery_import_keys_to_gallery_imports[ gallery_import_key ]
        
        gallery_import.PublishToPage( False )
        gallery_import.Repage( 'dead page key' )
        
        self._gallery_imports.remove( gallery_import )
        
        self._last_time_imports_changed = HydrusData.GetNowPrecise()
        
        del self._gallery_import_keys_to_gallery_imports[ gallery_import_key ]
        
    
    def _SetDirty( self ):
        
        self._status_dirty = True
        
    
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
            
        
        if version == 3:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, pending_queries, file_limit, gallery_paused, files_paused, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_seed_log, serialisable_file_seed_cache ) = old_serialisable_info
            
            ( current_query, current_query_num_new_urls, serialisable_current_gallery_stream_identifier, current_gallery_stream_identifier_page_index, serialisable_current_gallery_stream_identifier_found_urls, serialisable_pending_gallery_stream_identifiers ) = serialisable_current_query_stuff
            
            highlighted_gallery_import_key = None
            
            serialisable_highlighted_gallery_import_key = highlighted_gallery_import_key
            
            gallery_imports = HydrusSerialisable.SerialisableList()
            
            gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
            
            file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
            tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
            
            gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
            file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
            
            if len( file_seed_cache ) > 0:
                
                current_query = 'queue brought from old page'
                
                gallery_import = GalleryImport( current_query, gallery_identifier )
                
                gallery_import.PausePlayGallery()
                gallery_import.PausePlayFiles()
                
                gallery_import.SetFileLimit( file_limit )
                
                gallery_import.SetFileImportOptions( file_import_options )
                gallery_import.SetTagImportOptions( tag_import_options )
                
                gallery_import.SetFileSeedCache( file_seed_cache )
                gallery_import.SetGallerySeedLog( gallery_seed_log )
                
                gallery_imports.append( gallery_import )
                
            
            for query in pending_queries:
                
                pq_gallery_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( gallery_identifier )
                
                for pq_gallery_identifier in pq_gallery_identifiers:
                    
                    gallery_import = GalleryImport( 'updated stub: ' + query + ' (will not run, please re-queue)', gallery_identifier )
                    
                    gallery_import.PausePlayGallery()
                    gallery_import.PausePlayFiles()
                    
                    gallery_import.SetFileLimit( file_limit )
                    
                    gallery_import.SetFileImportOptions( file_import_options )
                    gallery_import.SetTagImportOptions( tag_import_options )
                    
                    gallery_imports.append( gallery_import )
                    
                
            
            serialisable_gallery_imports = gallery_imports.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_highlighted_gallery_import_key, file_limit, serialisable_file_import_options, serialisable_tag_import_options, serialisable_gallery_imports )
            
            return ( 4, new_serialisable_info )
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            return True in ( gallery_import.CurrentlyWorking() for gallery_import in self._gallery_imports )
            
        
    
    def GetFileLimit( self ):
        
        with self._lock:
            
            return self._file_limit
            
        
    
    def GetFileImportOptions( self ):
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetGalleryIdentifier( self ):
        
        with self._lock:
            
            return self._gallery_identifier
            
        
    
    def GetGalleryImports( self ):
        
        with self._lock:
            
            return list( self._gallery_imports )
            
        
    
    def GetHighlightedGalleryImport( self ):
        
        with self._lock:
            
            if self._highlighted_gallery_import_key is not None:
                
                if self._highlighted_gallery_import_key in self._gallery_import_keys_to_gallery_imports:
                    
                    return self._gallery_import_keys_to_gallery_imports[ self._highlighted_gallery_import_key ]
                    
                
                self._highlighted_gallery_import_key = None
                
            
            return None
            
        
    
    def GetLastTimeImportsChanged( self ):
        
        with self._lock:
            
            return self._last_time_imports_changed
            
        
    
    def GetNumGalleryImports( self ):
        
        with self._lock:
            
            return len( self._gallery_imports )
            
        
    
    def GetTagImportOptions( self ):
        
        with self._lock:
            
            return self._tag_import_options
            
        
    
    def GetTotalStatus( self ):
        
        with self._lock:
            
            if self._status_dirty:
                
                self._RegenerateStatus()
                
            
            return self._status_cache
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            total_value = 0
            total_range = 0
            
            for gallery_import in self._gallery_imports:
                
                ( value, range ) = gallery_import.GetValueRange()
                
                if value != range:
                    
                    total_value += value
                    total_range += range
                    
                
            
            return ( total_value, total_range )
            
        
    
    def PendQuery( self, query ):
        
        created_import = None
        
        with self._lock:
            
            gallery_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( self._gallery_identifier )
            
            for gallery_identifier in gallery_identifiers:
                
                gallery_import = GalleryImport( query, gallery_identifier )
                
                gallery_import.SetFileLimit( self._file_limit )
                
                gallery_import.SetFileImportOptions( self._file_import_options )
                gallery_import.SetTagImportOptions( self._tag_import_options )
                
                gallery_import.InitialiseFirstSearchPage()
                
                publish_to_page = False
                
                gallery_import.Start( self._page_key, publish_to_page )
                
                self._AddGalleryImport( gallery_import )
                
                if created_import is None:
                    
                    created_import = gallery_import
                    
                
            
            ClientImporting.WakeRepeatingJob( self._importers_repeating_job )
            
            self._SetDirty()
            
        
        return created_import
        
    
    def RemoveGalleryImport( self, gallery_import_key ):
        
        with self._lock:
            
            self._RemoveGalleryImport( gallery_import_key )
            
            self._SetDirty()
            
        
    
    def SetFileLimit( self, file_limit ):
        
        with self._lock:
            
            self._file_limit = file_limit
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetGalleryIdentifier( self, gallery_identifier ):
        
        with self._lock:
            
            self._gallery_identifier = gallery_identifier
            
        
    
    def SetHighlightedGalleryImport( self, highlighted_gallery_import ):
        
        with self._lock:
            
            if highlighted_gallery_import is None:
                
                self._highlighted_gallery_import_key = None
                
            else:
                
                self._highlighted_gallery_import_key = highlighted_gallery_import.GetGalleryImportKey()
                
                highlighted_gallery_import.PublishToPage( True )
                
            
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            self._tag_import_options = tag_import_options
            
        
    
    def Start( self, page_key ):
        
        with self._lock:
            
            self._page_key = page_key
            
        
        # set a 2s period so the page value/range is breddy snappy
        self._importers_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), 2.0, self.REPEATINGWorkOnImporters )
        
        for gallery_import in self._gallery_imports:
            
            publish_to_page = gallery_import.GetGalleryImportKey() == self._highlighted_gallery_import_key
            
            gallery_import.Start( page_key, publish_to_page )
            
        
    
    def REPEATINGWorkOnImporters( self ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( self._page_key ):
                
                self._importers_repeating_job.Cancel()
                
                return
                
            
            if not self._status_dirty: # if we think we are clean
                
                for gallery_import in self._gallery_imports:
                    
                    file_seed_cache = gallery_import.GetFileSeedCache()
                    
                    if file_seed_cache.GetStatusGenerationTime() > self._status_cache_generation_time: # has there has been an update?
                        
                        self._SetDirty()
                        
                        break
                        
                    
                
            
        
        if HydrusData.TimeHasPassed( self._next_pub_value_check_time ):
            
            self._next_pub_value_check_time = HydrusData.GetNow() + 5
            
            current_value_range = self.GetValueRange()
            
            if current_value_range != self._last_pubbed_value_range:
                
                self._last_pubbed_value_range = current_value_range
                
                HG.client_controller.pub( 'refresh_page_name', self._page_key )
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_MULTIPLE_GALLERY_IMPORT ] = MultipleGalleryImport
