import threading
import time
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.importing import ClientImportControl
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import TagImportOptionsLegacy
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingJobs

class SimpleDownloaderImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SIMPLE_DOWNLOADER_IMPORT
    SERIALISABLE_NAME = 'Simple Downloader Import'
    SERIALISABLE_VERSION = 5
    
    def __init__( self ):
        
        super().__init__()
        
        self._pending_jobs = []
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        self._file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        self._file_import_options.SetIsDefault( True )
        
        self._formula_name = 'all files linked by images in page'
        self._gallery_paused = False
        self._files_paused = False
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        self._page_key = b'initialising page key'
        self._downloader_key = HydrusData.GenerateKey()
        
        self._gallery_status = ''
        self._files_status = ''
        
        self._lock = threading.Lock()
        
        self._have_started = False
        
        self._files_network_job = None
        self._page_network_job = None
        
        self._files_repeating_job = None
        self._gallery_repeating_job = None
        
        self._last_serialisable_change_timestamp = 0
        
        CG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        CG.client_controller.sub( self, 'Wake', 'notify_global_page_import_pause_change' )
        
    
    def _DelayWork( self, time_delta, reason ):
        
        reason = HydrusText.GetFirstLine( reason )
        
        self._no_work_until = HydrusTime.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
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
        
        return ( serialisable_pending_jobs, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, self._formula_name, self._gallery_paused, self._files_paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_pending_jobs, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, self._formula_name, self._gallery_paused, self._files_paused ) = serialisable_info
        
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
        
    
    def _SerialisableChangeMade( self ):
        
        self._last_serialisable_change_timestamp = HydrusTime.GetNow()
        
    
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
            
        
    
    def _WorkOnFiles( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        def status_hook( text ):
            
            with self._lock:
                
                self._files_status = HydrusText.GetFirstLine( text )
                
            
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        note_import_options.SetIsDefault( True )
        
        try:
            
            did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, self._NetworkJobFactory, self._FileNetworkJobPresentationContextFactory, self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD, tag_import_options, note_import_options )
            
        except HydrusExceptions.NetworkException as e:
            
            delay = CG.client_controller.new_options.GetInteger( 'downloader_network_error_delay' )
            
            self._DelayWork( delay, str( e ) )
            
            file_seed.SetStatus( CC.STATUS_ERROR, str( e ) )
            
            HydrusData.PrintException( e )
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            file_seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        
        real_presentation_import_options = FileImportOptionsLegacy.GetRealPresentationImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
        
        if file_seed.ShouldPresent( real_presentation_import_options ):
            
            file_seed.PresentToPage( self._page_key )
            
            did_substantial_work = True
            
        
        with self._lock:
            
            self._files_status = ''
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _WorkOnGallery( self ):
        
        if len( self._pending_jobs ) > 0:
            
            with self._lock:
                
                job = self._pending_jobs[ 0 ]
                
                ( url, simple_downloader_formula ) = job
                
                self._gallery_status = 'checking ' + url
                
            
            try:
                
                error_occurred = False
                
                gallery_seed_status = CC.STATUS_ERROR
                parser_status = 'job not completed'
                
                gallery_seed = ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = False )
                
                try:
                    
                    network_job = self._NetworkJobFactory( 'GET', url )
                    
                    network_job.OverrideBandwidth( 30 )
                    
                    CG.client_controller.network_engine.AddJob( network_job )
                    
                    with self._PageNetworkJobPresentationContextFactory( network_job ):
                        
                        network_job.WaitUntilDone()
                        
                    
                    parsing_text = network_job.GetContentText()
                    
                    #
                    
                    parsing_context = {}
                    
                    parsing_context[ 'url' ] = url
                    
                    parsing_formula = simple_downloader_formula.GetFormula()
                    collapse_newlines = True
                    file_seeds = []
                    
                    for parsed_text in parsing_formula.Parse( parsing_context, parsing_text, collapse_newlines ):
                        
                        try:
                            
                            file_url = urllib.parse.urljoin( url, parsed_text )
                            
                            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, file_url )
                            
                            file_seed.SetReferralURL( url )
                            
                            file_seeds.append( file_seed )
                            
                        except Exception as e:
                            
                            continue
                            
                        
                    
                    num_new = self._file_seed_cache.AddFileSeeds( file_seeds )
                    
                    if num_new > 0:
                        
                        ClientImporting.WakeRepeatingJob( self._files_repeating_job )
                        
                    
                    parser_status = 'page checked OK with formula "' + simple_downloader_formula.GetName() + '" - ' + HydrusNumbers.ToHumanInt( num_new ) + ' new urls'
                    
                    num_already_in_file_seed_cache = len( file_seeds ) - num_new
                    
                    if num_already_in_file_seed_cache > 0:
                        
                        parser_status += ' (' + HydrusNumbers.ToHumanInt( num_already_in_file_seed_cache ) + ' already in queue)'
                        
                    
                    gallery_seed_status = CC.STATUS_SUCCESSFUL_AND_NEW
                    
                except HydrusExceptions.ShutdownException:
                    
                    gallery_seed_status = CC.STATUS_VETOED
                    parser_status = 'program is shutting down'
                    
                    return
                    
                except HydrusExceptions.NotFoundException:
                    
                    gallery_seed_status = CC.STATUS_VETOED
                    
                    error_occurred = True
                    
                    parser_status = 'page 404'
                    
                except HydrusExceptions.NetworkException as e:
                    
                    delay = CG.client_controller.new_options.GetInteger( 'downloader_network_error_delay' )
                    
                    self._DelayWork( delay, str( e ) )
                    
                    gallery_seed_status = CC.STATUS_ERROR
                    error_occurred = True
                    
                    parser_status = str( e )
                    
                    HydrusData.PrintException( e )
                    
                except Exception as e:
                    
                    gallery_seed_status = CC.STATUS_ERROR
                    
                    error_occurred = True
                    
                    parser_status = str( e )
                    
                finally:
                    
                    gallery_seed_note = parser_status
                    
                    gallery_seed.SetStatus( gallery_seed_status, note = gallery_seed_note )
                    
                    self._gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
                    
                
            finally:
                
                with self._lock:
                    
                    if job in self._pending_jobs:
                        
                        self._pending_jobs.remove( job )
                        
                    
                
            
            with self._lock:
                
                self._gallery_status = HydrusText.GetFirstLine( parser_status )
                
            
            if error_occurred:
                
                time.sleep( 5 )
                
            
            return True
            
        else:
            
            with self._lock:
                
                self._gallery_status = ''
                
            
            return False
            
        
    
    def AdvanceJob( self, job ):
        
        with self._lock:
            
            if job in self._pending_jobs:
                
                index = self._pending_jobs.index( job )
                
                if index - 1 >= 0:
                    
                    self._pending_jobs.remove( job )
                    
                    self._pending_jobs.insert( index - 1, job )
                    
                    self._SerialisableChangeMade()
                    
                
            
        
    
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
                    
                    self._SerialisableChangeMade()
                    
                
            
        
    
    def DeleteJob( self, job ):
        
        with self._lock:
            
            if job in self._pending_jobs:
                
                self._pending_jobs.remove( job )
                
                self._SerialisableChangeMade()
                
            
        
    
    def GetAPIInfoDict( self, simple ):
        
        with self._lock:
            
            d = {}
            
            d[ 'imports' ] = self._file_seed_cache.GetAPIInfoDict( simple )
            
            d[ 'gallery_log' ] = self._gallery_seed_log.GetAPIInfoDict( simple )
            
            d[ 'files_paused' ] = self._files_paused
            
            d[ 'gallery_paused' ] = self._gallery_paused
            
            return d
            
        
    
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
            
        
    
    def GetNumSeeds( self ):
        
        with self._lock:
            
            return len( self._file_seed_cache ) + len( self._gallery_seed_log )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            currently_working = self._gallery_repeating_job is not None and self._gallery_repeating_job.CurrentlyWorking()
            
            gallery_text = ClientImportControl.GenerateLiveStatusText( self._gallery_status, self._gallery_paused, currently_working, self._no_work_until, self._no_work_until_reason )
            
            currently_working = self._files_repeating_job is not None and self._files_repeating_job.CurrentlyWorking()
            
            file_text = ClientImportControl.GenerateLiveStatusText( self._files_status, self._files_paused, currently_working, self._no_work_until, self._no_work_until_reason )
            
            return ( list( self._pending_jobs ), gallery_text, file_text, self._gallery_paused, self._files_paused )
            
        
    
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
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def PausePlayQueue( self ):
        
        with self._lock:
            
            self._gallery_paused = not self._gallery_paused
            
            ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def PendJob( self, job ):
        
        with self._lock:
            
            if job not in self._pending_jobs:
                
                self._pending_jobs.append( job )
                
                ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetFileImportOptions( self, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy ):
        
        with self._lock:
            
            if file_import_options.DumpToString() != self._file_import_options.DumpToString():
                
                self._file_import_options = file_import_options
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetFormulaName( self, formula_name ):
        
        with self._lock:
            
            if formula_name != self._formula_name:
                
                self._formula_name = formula_name
                
                self._SerialisableChangeMade()
                
            
        
    
    def SetPendingJobs( self, jobs ):
        
        with self._lock:
            
            self._pending_jobs = jobs
            
            self._SerialisableChangeMade()
            
        
    
    def SetPendingJobsOrder( self, jobs ):
        
        with self._lock:
            
            # accept the re-order, but handle the situation where in the event before this we removed an item and the UI isn't synced yet
            
            my_jobs_fast = set( self._pending_jobs )
            
            self._pending_jobs = [ job for job in jobs if job in my_jobs_fast ]
            
            self._SerialisableChangeMade()
            
        
    
    def Start( self, page_key ):
        
        with self._lock:
            
            if self._have_started:
                
                return
                
            
            self._page_key = page_key
            
            self._files_repeating_job = CG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles )
            self._gallery_repeating_job = CG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnGallery )
            
            self._files_repeating_job.SetThreadSlotType( 'misc' )
            self._gallery_repeating_job.SetThreadSlotType( 'misc' )
            
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
                
            
        
    
    def CheckCanDoGalleryWork( self ):
        
        with self._lock:
            
            try:
                
                ClientImportControl.CheckImporterCanDoWorkBecauseStopped( self._page_key )
                
            except HydrusExceptions.VetoException:
                
                self._gallery_repeating_job.Cancel()
                
                raise
                
            
            if len( self._pending_jobs ) == 0:
                
                raise HydrusExceptions.VetoException()
                
            
            ClientImportControl.CheckImporterCanDoGalleryWorkBecausePaused( self._gallery_paused, None )
            
        
        return self.CheckCanDoNetworkWork()
        
    
    def REPEATINGWorkOnGallery( self ):
        
        while True:
            
            try:
                
                try:
                    
                    self.CheckCanDoGalleryWork()
                    
                except HydrusExceptions.VetoException as e:
                    
                    with self._lock:
                        
                        self._gallery_status = str( e )
                        
                    
                    break
                    
                
                self._WorkOnGallery()
                
                time.sleep( 1 )
                
                CG.client_controller.WaitUntilViewFree()
                
                self._SerialisableChangeMade()
                
            except Exception as e:
                
                with self._lock:
                    
                    self._gallery_status = 'stopping work: {}'.format( str( e ) )
                    
                
                HydrusData.ShowException( e )
                
                return
                
            
        
    
    def Wake( self ):
        
        ClientImporting.WakeRepeatingJob( self._files_repeating_job )
        ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SIMPLE_DOWNLOADER_IMPORT ] = SimpleDownloaderImport

class URLsImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT
    SERIALISABLE_NAME = 'URL Import'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, destination_location_context = None, destination_tag_import_options = None ):
        
        super().__init__()
        
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        self._file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        self._file_import_options.SetIsDefault( True )
        
        if destination_location_context is not None:
            
            self._file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD ).Duplicate()
            
            self._file_import_options.GetLocationImportOptions().SetDestinationLocationContext( destination_location_context )
            
        
        if destination_tag_import_options is not None:
            
            self._tag_import_options = destination_tag_import_options
            
        else:
            
            self._tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
            
        
        self._note_import_options = NoteImportOptions.NoteImportOptions()
        self._note_import_options.SetIsDefault( True )
        
        self._paused = False
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        self._page_key = b'initialising page key'
        self._downloader_key = HydrusData.GenerateKey()
        
        self._lock = threading.Lock()
        
        self._have_started = False
        
        self._files_status = ''
        self._gallery_status = ''
        
        self._files_network_job = None
        self._gallery_network_job = None
        
        self._files_repeating_job = None
        self._gallery_repeating_job = None
        
        self._last_serialisable_change_timestamp = 0
        
        CG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        CG.client_controller.sub( self, 'NotifyGallerySeedsUpdated', 'gallery_seed_log_gallery_seeds_updated' )
        CG.client_controller.sub( self, 'Wake', 'notify_global_page_import_pause_change' )
        
    
    def _DelayWork( self, time_delta, reason ):
        
        reason = HydrusText.GetFirstLine( reason )
        
        self._no_work_until = HydrusTime.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
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
        serialisable_note_import_options = self._note_import_options.GetSerialisableTuple()
        
        return ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, serialisable_tag_import_options, serialisable_note_import_options, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, serialisable_tag_import_options, serialisable_note_import_options, self._paused ) = serialisable_info
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        self._note_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_note_import_options )
        
    
    def _NetworkJobFactory( self, *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJobDownloader( self._downloader_key, *args, **kwargs )
        
        return network_job
        
    
    def _SerialisableChangeMade( self ):
        
        self._last_serialisable_change_timestamp = HydrusTime.GetNow()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_file_seed_cache, serialisable_file_import_options, paused ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, paused ) = old_serialisable_info
            
            tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
            
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, serialisable_tag_import_options, paused )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, serialisable_tag_import_options, paused ) = old_serialisable_info
            
            note_import_options = NoteImportOptions.NoteImportOptions()
            note_import_options.SetIsDefault( True )
            
            serialisable_note_import_options = note_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_import_options, serialisable_tag_import_options, serialisable_note_import_options, paused )
            
            return ( 4, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        url = file_seed.file_seed_data
        
        try:
            
            status_hook = lambda s: s # do nothing for now
            
            did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, self._NetworkJobFactory, self._FileNetworkJobPresentationContextFactory, self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD, self._tag_import_options, self._note_import_options )
            
            real_presentation_import_options = FileImportOptionsLegacy.GetRealPresentationImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
            
            if file_seed.ShouldPresent( real_presentation_import_options ):
                
                file_seed.PresentToPage( self._page_key )
                
                did_substantial_work = True
                
            
        except HydrusExceptions.NetworkException as e:
            
            delay = CG.client_controller.new_options.GetInteger( 'downloader_network_error_delay' )
            
            self._DelayWork( delay, str( e ) )
            
            file_seed.SetStatus( CC.STATUS_ERROR, str( e ) )
            
            HydrusData.PrintException( e )
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            file_seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        
        if did_substantial_work:
            
            time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _WorkOnGallery( self ):
        
        gallery_seed = self._gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
        
        if gallery_seed is None:
            
            return
            
        
        try:
            
            status_hook = lambda s: s
            title_hook = lambda s: s
            
            def file_seeds_callable( file_seeds ):
                
                return ClientImporting.UpdateFileSeedCacheWithFileSeeds( self._file_seed_cache, file_seeds )
                
            
            gallery_seed.WorkOnURL( 'download page', self._gallery_seed_log, file_seeds_callable, status_hook, title_hook, self._NetworkJobFactory, self._GalleryNetworkJobPresentationContextFactory, self._file_import_options )
            
        except HydrusExceptions.NetworkException as e:
            
            delay = CG.client_controller.new_options.GetInteger( 'downloader_network_error_delay' )
            
            self._DelayWork( delay, str( e ) )
            
            gallery_seed.SetStatus( CC.STATUS_ERROR, str( e ) )
            
            HydrusData.PrintException( e )
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            gallery_seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        
        time.sleep( 1 )
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._file_seed_cache.WorkToDo()
            
            return not finished and not self._paused
            
        
    
    def GetAPIInfoDict( self, simple ):
        
        with self._lock:
            
            d = {}
            
            d[ 'imports' ] = self._file_seed_cache.GetAPIInfoDict( simple )
            
            d[ 'gallery_log' ] = self._gallery_seed_log.GetAPIInfoDict( simple )
            
            d[ 'files_paused' ] = self._paused
            
            return d
            
        
    
    def GetFileImportOptions( self ) -> FileImportOptionsLegacy.FileImportOptionsLegacy:
        
        with self._lock:
            
            return self._file_import_options
            
        
    
    def GetFileSeedCache( self ):
        
        with self._lock:
            
            return self._file_seed_cache
            
        
    
    def GetGallerySeedLog( self ):
        
        with self._lock:
            
            return self._gallery_seed_log
            
        
    
    def GetNetworkJobs( self ):
        
        with self._lock:
            
            return ( self._files_network_job, self._gallery_network_job )
            
        
    
    def GetNoteImportOptions( self ) -> NoteImportOptions.NoteImportOptions:
        
        with self._lock:
            
            return self._note_import_options
            
        
    
    def GetNumSeeds( self ):
        
        with self._lock:
            
            return len( self._file_seed_cache ) + len( self._gallery_seed_log )
            
        
    
    def GetTagImportOptions( self ) -> TagImportOptionsLegacy.TagImportOptionsLegacy:
        
        with self._lock:
            
            return self._tag_import_options
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetValueRange()
            
        
    
    def HasSerialisableChangesSince( self, since_timestamp ):
        
        with self._lock:
            
            return self._last_serialisable_change_timestamp > since_timestamp
            
        
    
    def IsPaused( self ):
        
        with self._lock:
            
            return self._paused
            
        
    
    def NotifyFileSeedsUpdated( self, file_seed_cache_key, file_seeds ):
        
        if file_seed_cache_key == self._file_seed_cache.GetFileSeedCacheKey():
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def NotifyGallerySeedsUpdated( self, gallery_seed_log_key, gallery_seeds ):
        
        if gallery_seed_log_key == self._gallery_seed_log.GetGallerySeedLogKey():
            
            ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
            
            self._SerialisableChangeMade()
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            ClientImporting.WakeRepeatingJob( self._files_repeating_job )
            ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
            
            self._SerialisableChangeMade()
            
    
    def PendURLs( self, urls, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        with self._lock:
            
            urls = [ u for u in urls if len( u ) > 1 ] # > _1_ to take out the occasional whitespace
            
            file_seeds = []
            
            gallery_seeds = []
            
            for url in urls:
                
                try:
                    
                    url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( url )
                    
                except HydrusExceptions.URLClassException:
                    
                    continue
                    
                
                if url_class is None or url_class.GetURLType() in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
                    
                    file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
                    
                    file_seed.AddExternalFilterableTags( filterable_tags )
                    file_seed.AddExternalAdditionalServiceKeysToTags( additional_service_keys_to_tags )
                    
                    file_seeds.append( file_seed )
                    
                else:
                    
                    can_generate_more_pages = False
                    
                    gallery_seed = ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = can_generate_more_pages )
                    
                    gallery_seed.AddExternalFilterableTags( filterable_tags )
                    gallery_seed.AddExternalAdditionalServiceKeysToTags( additional_service_keys_to_tags )
                    
                    gallery_seeds.append( gallery_seed )
                    
                
            
            if len( gallery_seeds ) > 0:
                
                self._gallery_seed_log.AddGallerySeeds( gallery_seeds )
                
                ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
                
                self._SerialisableChangeMade()
                
            
            if len( file_seeds ) > 0:
                
                self._file_seed_cache.AddFileSeeds( file_seeds, dupe_try_again = True )
                
                ClientImporting.WakeRepeatingJob( self._files_repeating_job )
                
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
                
            
        
    
    def Start( self, page_key ):
        
        with self._lock:
            
            if self._have_started:
                
                return
                
            
            self._page_key = page_key
            
            self._files_repeating_job = CG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles )
            self._gallery_repeating_job = CG.client_controller.CallRepeating( ClientImporting.GetRepeatingJobInitialDelay(), ClientImporting.REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnGallery )
            
            self._files_repeating_job.SetThreadSlotType( 'misc' )
            self._gallery_repeating_job.SetThreadSlotType( 'misc' )
            
            self._have_started = True
            
        
    
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
                
            
        
        self.CheckCanDoNetworkWork()
        
    
    def CheckCanDoNetworkWork( self ):
        
        with self._lock:
            
            ClientImportControl.CheckCanDoNetworkWork( self._no_work_until, self._no_work_until_reason )
            
        
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
                
            
        
    
    def CheckCanDoGalleryWork( self ):
        
        with self._lock:
            
            try:
                
                ClientImportControl.CheckImporterCanDoWorkBecauseStopped( self._page_key )
                
            except HydrusExceptions.VetoException:
                
                self._gallery_repeating_job.Cancel()
                
                raise
                
            
            ClientImportControl.CheckImporterCanDoGalleryWorkBecausePaused( self._paused, self._gallery_seed_log )
            
        
        return self.CheckCanDoNetworkWork()
        
    
    def REPEATINGWorkOnGallery( self ):
        
        while True:
            
            try:
                
                try:
                    
                    self.CheckCanDoGalleryWork()
                    
                except HydrusExceptions.VetoException as e:
                    
                    with self._lock:
                        
                        self._gallery_status = str( e )
                        
                    
                    break
                    
                
                self._WorkOnGallery()
                
                time.sleep( 1 )
                
                CG.client_controller.WaitUntilViewFree()
                
                self._SerialisableChangeMade()
                
            except Exception as e:
                
                with self._lock:
                    
                    self._gallery_status = 'stopping work: {}'.format( str( e ) )
                    
                
                HydrusData.ShowException( e )
                
                return
                
            
        
    
    def Wake( self ):
        
        ClientImporting.WakeRepeatingJob( self._files_repeating_job )
        ClientImporting.WakeRepeatingJob( self._gallery_repeating_job )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT ] = URLsImport
