from . import ClientConstants as CC
from . import ClientDownloading
from . import ClientNetworkingJobs
from . import ClientImporting
from . import ClientImportFileSeeds
from . import ClientImportGallerySeeds
from . import ClientImportOptions
from . import ClientTags
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
import os
import threading
import time
import urllib.parse

class SimpleDownloaderImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SIMPLE_DOWNLOADER_IMPORT
    SERIALISABLE_NAME = 'Simple Downloader Import'
    SERIALISABLE_VERSION = 5
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        self._pending_jobs = []
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        self._file_import_options = file_import_options
        self._formula_name = 'all files linked by images in page'
        self._queue_paused = False
        self._files_paused = False
        
        self._downloader_key = HydrusData.GenerateKey()
        
        self._parser_status = ''
        self._current_action = ''
        
        self._lock = threading.Lock()
        
        self._files_network_job = None
        self._page_network_job = None
        
        self._files_repeating_job = None
        self._queue_repeating_job = None
        
        HG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        
    
    def _FileNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                self._files_network_job = network_job
                
            
        
        def exit_call():
            
            with self._lock:
                
                self._files_network_job = None
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_pending_jobs = [ ( url, simple_downloader_formula.GetSerialisableTuple() ) for ( url, simple_downloader_formula ) in self._pending_jobs ]
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        
        return ( serialisable_pending_jobs, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, self._formula_name, self._queue_paused, self._files_paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_pending_jobs, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, self._formula_name, self._queue_paused, self._files_paused ) = serialisable_info
        
        self._pending_jobs = [ ( url, HydrusSerialisable.CreateFromSerialisableTuple( serialisable_simple_downloader_formula ) ) for ( url, serialisable_simple_downloader_formula ) in serialisable_pending_jobs ]
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        
    
    def _NetworkJobFactory( self, *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJobDownloader( self._downloader_key, *args, **kwargs )
        
        return network_job
        
    
    def _PageNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                self._page_network_job = network_job
                
            
        
        def exit_call():
            
            with self._lock:
                
                self._page_network_job = None
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( pending_page_urls, serialisable_file_seed_cache, serialisable_file_import_options, download_image_links, download_unlinked_images, paused ) = old_serialisable_info
            
            queue_paused = paused
            files_paused = paused
            
            new_serialisable_info = ( pending_page_urls, serialisable_file_seed_cache, serialisable_file_import_options, download_image_links, download_unlinked_images, queue_paused, files_paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( pending_page_urls, serialisable_file_seed_cache, serialisable_file_import_options, download_image_links, download_unlinked_images, queue_paused, files_paused ) = old_serialisable_info
            
            pending_jobs = []
            
            new_serialisable_info = ( pending_jobs, serialisable_file_seed_cache, serialisable_file_import_options, queue_paused, files_paused )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( pending_jobs, serialisable_file_seed_cache, serialisable_file_import_options, queue_paused, files_paused ) = old_serialisable_info
            
            pending_jobs = []
            
            formula_name = 'all files linked by images in page'
            
            new_serialisable_info = ( pending_jobs, serialisable_file_seed_cache, serialisable_file_import_options, formula_name, queue_paused, files_paused )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( pending_jobs, serialisable_file_seed_cache, serialisable_file_import_options, formula_name, queue_paused, files_paused ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( pending_jobs, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, formula_name, queue_paused, files_paused )
            
            return ( 5, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        def status_hook( text ):
            
            with self._lock:
                
                self._current_action = text
                
            
        
        tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
        
        did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, self._NetworkJobFactory, self._FileNetworkJobPresentationContextFactory, self._file_import_options, tag_import_options )
        
        if file_seed.ShouldPresent( self._file_import_options ):
            
            file_seed.PresentToPage( page_key )
            
            did_substantial_work = True
            
        
        with self._lock:
            
            self._current_action = ''
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _WorkOnQueue( self, page_key ):
        
        if len( self._pending_jobs ) > 0:
            
            with self._lock:
                
                ( url, simple_downloader_formula ) = self._pending_jobs.pop( 0 )
                
                self._parser_status = 'checking ' + url
                
            
            error_occurred = False
            
            try:
                
                gallery_seed = ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = False )
                
                self._gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
                
                network_job = self._NetworkJobFactory( 'GET', url )
                
                network_job.OverrideBandwidth( 30 )
                
                HG.client_controller.network_engine.AddJob( network_job )
                
                with self._PageNetworkJobPresentationContextFactory( network_job ):
                    
                    network_job.WaitUntilDone()
                    
                
                parsing_text = network_job.GetContentText()
                
                #
                
                parsing_context = {}
                
                parsing_context[ 'url' ] = url
                
                parsing_formula = simple_downloader_formula.GetFormula()
                
                file_seeds = []
                
                for parsed_text in parsing_formula.Parse( parsing_context, parsing_text ):
                    
                    try:
                        
                        file_url = urllib.parse.urljoin( url, parsed_text )
                        
                        file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, file_url )
                        
                        file_seed.SetReferralURL( url )
                        
                        file_seeds.append( file_seed )
                        
                    except:
                        
                        continue
                        
                    
                
                num_new = self._file_seed_cache.AddFileSeeds( file_seeds )
                
                if num_new > 0:
                    
                    ClientImporting.WakeRepeatingJob( self._files_repeating_job )
                    
                
                parser_status = 'page checked OK with formula "' + simple_downloader_formula.GetName() + '" - ' + HydrusData.ToHumanInt( num_new ) + ' new urls'
                
                num_already_in_file_seed_cache = len( file_seeds ) - num_new
                
                if num_already_in_file_seed_cache > 0:
                    
                    parser_status += ' (' + HydrusData.ToHumanInt( num_already_in_file_seed_cache ) + ' already in queue)'
                    
                
                gallery_seed_status = CC.STATUS_SUCCESSFUL_AND_NEW
                
            except HydrusExceptions.ShutdownException:
                
                gallery_seed_status = CC.STATUS_VETOED
                parser_status = 'program is shutting down'
                
                return
                
            except HydrusExceptions.NotFoundException:
                
                gallery_seed_status = CC.STATUS_VETOED
                
                error_occurred = True
                
                parser_status = 'page 404'
                
            except Exception as e:
                
                gallery_seed_status = CC.STATUS_ERROR
                
                error_occurred = True
                
                parser_status = str( e )
                
            finally:
                
                gallery_seed_note = parser_status
                
                gallery_seed.SetStatus( gallery_seed_status, note = gallery_seed_note )
                
                self._gallery_seed_log.NotifyGallerySeedsUpdated( ( gallery_seed, ) )
                
            
            with self._lock:
                
                self._parser_status = parser_status
                
            
            if error_occurred:
                
                time.sleep( 5 )
                
            
            return True
            
        else:
            
            with self._lock:
                
                self._parser_status = ''
                
            
            return False
            
        
    
    def AdvanceJob( self, job ):
        
        with self._lock:
            
            if job in self._pending_jobs:
                
                index = self._pending_jobs.index( job )
                
                if index - 1 >= 0:
                    
                    self._pending_jobs.remove( job )
                    
                    self._pending_jobs.insert( index - 1, job )
                    
                
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._file_seed_cache.WorkToDo() or len( self._pending_jobs ) > 0
            
            return not finished and not self._files_paused
            
        
    
    def DelayJob( self, job ):
        
        with self._lock:
            
            if job in self._pending_jobs:
                
                index = self._pending_jobs.index( job )
                
                if index + 1 < len( self._pending_jobs ):
                    
                    self._pending_jobs.remove( job )
                    
                    self._pending_jobs.insert( index + 1, job )
                    
                
            
        
    
    def DeleteJob( self, job ):
        
        with self._lock:
            
            if job in self._pending_jobs:
                
                self._pending_jobs.remove( job )
                
            
        
    
    def GetFileSeedCache( self ):
        
        with self._lock:
            
            return self._file_seed_cache
            
        
    
    def GetFileImportOptions( self ):
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetFormulaName( self ):
        
        with self._lock:
            
            return self._formula_name
            
        
    
    def GetGallerySeedLog( self ):
        
        with self._lock:
            
            return self._gallery_seed_log
            
        
    
    def GetNetworkJobs( self ):
        
        with self._lock:
            
            return ( self._files_network_job, self._page_network_job )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( list( self._pending_jobs ), self._parser_status, self._current_action, self._queue_paused, self._files_paused )
            
        
    
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
            
        
    
    def PausePlayQueue( self ):
        
        with self._lock:
            
            self._queue_paused = not self._queue_paused
            
            ClientImporting.WakeRepeatingJob( self._queue_repeating_job )
            
        
    
    def PendJob( self, job ):
        
        with self._lock:
            
            if job not in self._pending_jobs:
                
                self._pending_jobs.append( job )
                
                ClientImporting.WakeRepeatingJob( self._queue_repeating_job )
                
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetFormulaName( self, formula_name ):
        
        with self._lock:
            
            self._formula_name = formula_name
            
        
    
    def Start( self, page_key ):
        
        self._files_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles, page_key )
        self._queue_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnQueue, page_key )
        
        self._files_repeating_job.SetThreadSlotType( 'misc' )
        self._queue_repeating_job.SetThreadSlotType( 'misc' )
        
    
    def REPEATINGWorkOnFiles( self, page_key ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( page_key ):
                
                self._files_repeating_job.Cancel()
                
                return
                
            
            files_paused = self._files_paused or HG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' )
            
            work_to_do = self._file_seed_cache.WorkToDo() and not ( files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
            network_engine_good = not HG.client_controller.network_engine.IsBusy()
            
            ok_to_work = work_to_do and network_engine_good
            
        
        while ok_to_work:
            
            try:
                
                self._WorkOnFiles( page_key )
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if ClientImporting.PageImporterShouldStopWorking( page_key ):
                    
                    self._files_repeating_job.Cancel()
                    
                    return
                    
                
                files_paused = self._files_paused or HG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' )
                
                work_to_do = self._file_seed_cache.WorkToDo() and not ( files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                network_engine_good = not HG.client_controller.network_engine.IsBusy()
                
                ok_to_work = work_to_do and network_engine_good
                
            
        
    
    def REPEATINGWorkOnQueue( self, page_key ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( page_key ):
                
                self._queue_repeating_job.Cancel()
                
                return
                
            
            queue_paused = self._queue_paused or HG.client_controller.new_options.GetBoolean( 'pause_all_gallery_searches' )
            
            queue_good = not queue_paused
            page_shown = not HG.client_controller.PageClosedButNotDestroyed( page_key )
            network_engine_good = not HG.client_controller.network_engine.IsBusy()
            
            ok_to_work = queue_good and page_shown and network_engine_good
            
        
        while ok_to_work:
            
            try:
                
                did_work = self._WorkOnQueue( page_key )
                
                if did_work:
                    
                    time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
                    
                else:
                    
                    return
                    
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if ClientImporting.PageImporterShouldStopWorking( page_key ):
                    
                    self._queue_repeating_job.Cancel()
                    
                    return
                    
                
                queue_paused = self._queue_paused or HG.client_controller.new_options.GetBoolean( 'pause_all_gallery_searches' )
                
                queue_good = not queue_paused
                page_shown = not HG.client_controller.PageClosedButNotDestroyed( page_key )
                network_engine_good = not HG.client_controller.network_engine.IsBusy()
                
                ok_to_work = queue_good and page_shown and network_engine_good
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SIMPLE_DOWNLOADER_IMPORT ] = SimpleDownloaderImport

class URLsImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT
    SERIALISABLE_NAME = 'URL Import'
    SERIALISABLE_VERSION = 3
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        self._tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
        self._paused = False
        
        self._downloader_key = HydrusData.GenerateKey()
        
        self._lock = threading.Lock()
        
        self._files_network_job = None
        self._gallery_network_job = None
        
        self._files_repeating_job = None
        self._gallery_repeating_job = None
        
        HG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        HG.client_controller.sub( self, 'NotifyGallerySeedsUpdated', 'gallery_seed_log_gallery_seeds_updated' )
        
    
    def _FileNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                self._files_network_job = network_job
                
            
        
        def exit_call():
            
            with self._lock:
                
                self._files_network_job = None
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _GalleryNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                self._gallery_network_job = network_job
                
            
        
        def exit_call():
            
            with self._lock:
                
                self._gallery_network_job = None
                
            
        
        return ClientImporting.NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, serialisable_tag_import_options, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, serialisable_tag_import_options, self._paused ) = serialisable_info
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _NetworkJobFactory( self, *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJobDownloader( self._downloader_key, *args, **kwargs )
        
        return network_job
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_file_seed_cache, serialisable_file_import_options, paused ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, paused ) = old_serialisable_info
            
            tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
            
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, serialisable_tag_import_options, paused )
            
            return ( 3, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        url = file_seed.file_seed_data
        
        try:
            
            status_hook = lambda s: s # do nothing for now
            
            did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, self._NetworkJobFactory, self._FileNetworkJobPresentationContextFactory, self._file_import_options, self._tag_import_options )
            
            if file_seed.ShouldPresent( self._file_import_options ):
                
                file_seed.PresentToPage( page_key )
                
                did_substantial_work = True
                
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            file_seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _WorkOnGallery( self, page_key ):
        
        gallery_seed = self._gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
        
        if gallery_seed is None:
            
            return
            
        
        try:
            
            status_hook = lambda s: s
            title_hook = lambda s: s
            
            def file_seeds_callable( file_seeds ):
                
                return ClientImporting.UpdateFileSeedCacheWithFileSeeds( self._file_seed_cache, file_seeds )
                
            
            gallery_seed.WorkOnURL( 'download page', self._gallery_seed_log, file_seeds_callable, status_hook, title_hook, self._NetworkJobFactory, self._GalleryNetworkJobPresentationContextFactory, self._file_import_options )
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            gallery_seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        
        time.sleep( 1 )
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._file_seed_cache.WorkToDo()
            
            return not finished and not self._paused
            
        
    
    def GetFileSeedCache( self ):
        
        with self._lock:
            
            return self._file_seed_cache
            
        
    
    def GetGallerySeedLog( self ):
        
        with self._lock:
            
            return self._gallery_seed_log
            
        
    
    def GetNetworkJobs( self ):
        
        with self._lock:
            
            return ( self._files_network_job, self._gallery_network_job )
            
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return ( self._file_import_options, self._tag_import_options )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._file_seed_cache.GetStatus(), self._paused )
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetValueRange()
            
        
    
    def IsPaused( self ):
        
        with self._lock:
            
            return self._paused
            
        
    
    def NotifyFileSeedsUpdated( self, file_seed_cache_key, file_seeds ):
        
        if file_seed_cache_key == self._file_seed_cache.GetFileSeedCacheKey():
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def NotifyGallerySeedsUpdated( self, gallery_seed_log_key, gallery_seeds ):
        
        if gallery_seed_log_key == self._gallery_seed_log.GetGallerySeedLogKey():
            
            ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
            
        
    
    def PendURLs( self, urls, service_keys_to_tags = None ):
        
        if service_keys_to_tags is None:
            
            service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        with self._lock:
            
            urls = [u for u in urls if len( u ) > 1] # > _1_ to take out the occasional whitespace
            
            file_seeds = []
            
            gallery_seeds = []
            
            for url in urls:
                
                url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( url )
                
                if url_class is None or url_class.GetURLType() in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
                    
                    file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
                    
                    file_seed.SetFixedServiceKeysToTags( service_keys_to_tags )
                    
                    file_seeds.append( file_seed )
                    
                else:
                    
                    can_generate_more_pages = False
                    
                    gallery_seed = ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = can_generate_more_pages )
                    
                    gallery_seed.SetFixedServiceKeysToTags( service_keys_to_tags )
                    
                    gallery_seeds.append( gallery_seed )
                    
                
            
            if len( gallery_seeds ) > 0:
                
                self._gallery_seed_log.AddGallerySeeds( gallery_seeds )
                
                ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
                
            
            if len( file_seeds ) > 0:
                
                self._file_seed_cache.AddFileSeeds( file_seeds )
                
                ClientImporting.WakeRepeatingJob( self._files_repeating_job )
                
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        with self._lock:
            
            self._tag_import_options = tag_import_options
            
        
    
    def Start( self, page_key ):
        
        self._files_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles, page_key )
        self._gallery_repeating_job = HG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnGallery, page_key )
        
        self._files_repeating_job.SetThreadSlotType( 'misc' )
        self._gallery_repeating_job.SetThreadSlotType( 'misc' )
        
    
    def REPEATINGWorkOnFiles( self, page_key ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( page_key ):
                
                self._files_repeating_job.Cancel()
                
                return
                
            
            files_paused = self._paused or HG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' )
            
            work_to_do = self._file_seed_cache.WorkToDo() and not ( files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
            network_engine_good = not HG.client_controller.network_engine.IsBusy()
            
            ok_to_work = work_to_do and network_engine_good
            
        
        while ok_to_work:
            
            try:
                
                self._WorkOnFiles( page_key )
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if ClientImporting.PageImporterShouldStopWorking( page_key ):
                    
                    self._files_repeating_job.Cancel()
                    
                    return
                    
                
                files_paused = self._paused or HG.client_controller.new_options.GetBoolean( 'pause_all_file_queues' )
                
                work_to_do = self._file_seed_cache.WorkToDo() and not ( files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                network_engine_good = not HG.client_controller.network_engine.IsBusy()
                
                ok_to_work = work_to_do and network_engine_good
                
            
        
    
    def REPEATINGWorkOnGallery( self, page_key ):
        
        with self._lock:
            
            if ClientImporting.PageImporterShouldStopWorking( page_key ):
                
                self._gallery_repeating_job.Cancel()
                
                return
                
            
            gallery_paused = self._paused or HG.client_controller.new_options.GetBoolean( 'pause_all_gallery_searches' )
            
            work_to_do = self._gallery_seed_log.WorkToDo() and not ( gallery_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
            network_engine_good = not HG.client_controller.network_engine.IsBusy()
            
            ok_to_work = work_to_do and network_engine_good
            
        
        while ok_to_work:
            
            try:
                
                self._WorkOnGallery( page_key )
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if ClientImporting.PageImporterShouldStopWorking( page_key ):
                    
                    self._gallery_repeating_job.Cancel()
                    
                    return
                    
                
                gallery_paused = self._paused or HG.client_controller.new_options.GetBoolean( 'pause_all_gallery_searches' )
                
                work_to_do = self._gallery_seed_log.WorkToDo() and not ( gallery_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                network_engine_good = not HG.client_controller.network_engine.IsBusy()
                
                ok_to_work = work_to_do and network_engine_good
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT ] = URLsImport
