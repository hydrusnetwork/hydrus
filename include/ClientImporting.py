import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDownloading
import ClientFiles
import ClientImportOptions
import ClientImportFileSeeds
import ClientImportGallerySeeds
import ClientNetworkingContexts
import ClientNetworkingJobs
import ClientParsing
import ClientPaths
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusFileHandling
import HydrusGlobals as HG
import HydrusPaths
import HydrusSerialisable
import HydrusThreading
import os
import random
import threading
import time
import traceback
import urlparse
import wx

CHECKER_STATUS_OK = 0
CHECKER_STATUS_DEAD = 1
CHECKER_STATUS_404 = 2

DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME = 0.1

REPEATING_JOB_TYPICAL_PERIOD = 30.0

def GenerateDownloaderNetworkJobFactory( page_key ):
    
    def network_job_factory( *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJobDownloader( page_key, *args, **kwargs )
        
        return network_job
        
    
    return network_job_factory
    
def GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key ):
    
    def network_job_presentation_context_factory( network_job ):
        
        def enter_call():
            
            job_key.SetVariable( 'popup_network_job', network_job )
            
        
        def exit_call():
            
            pass
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    return network_job_presentation_context_factory
    
def GenerateSinglePopupNetworkJobPresentationContextFactory( job_key ):
    
    def network_job_presentation_context_factory( network_job ):
        
        def enter_call():
            
            job_key.SetVariable( 'popup_network_job', network_job )
            
        
        def exit_call():
            
            job_key.DeleteVariable( 'popup_network_job' )
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    return network_job_presentation_context_factory
    
def GenerateSubscriptionNetworkJobFactory( subscription_key ):
    
    def network_job_factory( *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJobSubscription( subscription_key, *args, **kwargs )
        
        network_job.OverrideBandwidth( 30 )
        
        return network_job
        
    
    return network_job_factory
    
def GenerateWatcherNetworkJobFactory( watcher_key ):
    
    def network_job_factory( *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJobWatcherPage( watcher_key, *args, **kwargs )
        
        return network_job
        
    
    return network_job_factory
    
def GetRepeatingJobInitialDelay():
    
    return 0.5 + ( random.random() * 0.5 )
    
def PageImporterShouldStopWorking( page_key ):
    
    return HG.view_shutdown or not HG.client_controller.PageAlive( page_key )
    
def PublishPresentationHashes( name, hashes, publish_to_popup_button, publish_files_to_page ):
    
    if publish_to_popup_button:
        
        files_job_key = ClientThreading.JobKey()
        
        files_job_key.SetVariable( 'popup_files_mergable', True )
        files_job_key.SetVariable( 'popup_files', ( list( hashes ), name ) )
        
        HG.client_controller.pub( 'message', files_job_key )
        
    
    if publish_files_to_page:
        
        HG.client_controller.pub( 'imported_files_to_page', list( hashes ), name )
        
    
def THREADDownloadURL( job_key, url, url_string ):
    
    job_key.SetVariable( 'popup_title', url_string )
    job_key.SetVariable( 'popup_text_1', 'downloading and importing' )
    
    #
    
    file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
    
    def network_job_factory( *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJob( *args, **kwargs )
        
        network_job.OverrideBandwidth( 30 )
        
        return network_job
        
    
    network_job_presentation_context_factory = GenerateSinglePopupNetworkJobPresentationContextFactory( job_key )
    
    file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
    
    #
    
    try:
        
        file_seed.DownloadAndImportRawFile( url, file_import_options, network_job_factory, network_job_presentation_context_factory )
        
        status = file_seed.status
        
        if status in CC.SUCCESSFUL_IMPORT_STATES:
            
            if status == CC.STATUS_SUCCESSFUL_AND_NEW:
                
                job_key.SetVariable( 'popup_text_1', 'successful!' )
                
            elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                
                job_key.SetVariable( 'popup_text_1', 'was already in the database!' )
                
            
            hash = file_seed.GetHash()
            
            job_key.SetVariable( 'popup_files', ( [ hash ], 'download' ) )
            
        elif status == CC.STATUS_DELETED:
            
            job_key.SetVariable( 'popup_text_1', 'had already been deleted!' )
            
        
    finally:
        
        job_key.Finish()
        
    
def THREADDownloadURLs( job_key, urls, title ):
    
    job_key.SetVariable( 'popup_title', title )
    job_key.SetVariable( 'popup_text_1', 'initialising' )
    
    num_successful = 0
    num_redundant = 0
    num_deleted = 0
    num_failed = 0
    
    presentation_hashes = []
    presentation_hashes_fast = set()
    
    file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
    
    def network_job_factory( *args, **kwargs ):
        
        network_job = ClientNetworkingJobs.NetworkJob( *args, **kwargs )
        
        network_job.OverrideBandwidth()
        
        return network_job
        
    
    network_job_presentation_context_factory = GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key )
    
    for ( i, url ) in enumerate( urls ):
        
        ( i_paused, should_quit ) = job_key.WaitIfNeeded()
        
        if should_quit:
            
            break
            
        
        job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i + 1, len( urls ) ) )
        job_key.SetVariable( 'popup_gauge_1', ( i + 1, len( urls ) ) )
        
        file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
        
        try:
            
            file_seed.DownloadAndImportRawFile( url, file_import_options, network_job_factory, network_job_presentation_context_factory )
            
            status = file_seed.status
            
            if status in CC.SUCCESSFUL_IMPORT_STATES:
                
                if status == CC.STATUS_SUCCESSFUL_AND_NEW:
                    
                    num_successful += 1
                    
                elif status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                    
                    num_redundant += 1
                    
                
                hash = file_seed.GetHash()
                
                if hash not in presentation_hashes_fast:
                    
                    presentation_hashes.append( hash )
                    
                
                presentation_hashes_fast.add( hash )
                
            elif status == CC.STATUS_DELETED:
                
                num_deleted += 1
                
            
        except Exception as e:
            
            num_failed += 1
            
            HydrusData.Print( url + ' failed to import!' )
            HydrusData.PrintException( e )
            
        
    
    job_key.DeleteVariable( 'popup_network_job' )
    
    text_components = []
    
    if num_successful > 0:
        
        text_components.append( HydrusData.ToHumanInt( num_successful ) + ' successful' )
        
    
    if num_redundant > 0:
        
        text_components.append( HydrusData.ToHumanInt( num_redundant ) + ' already in db' )
        
    
    if num_deleted > 0:
        
        text_components.append( HydrusData.ToHumanInt( num_deleted ) + ' deleted' )
        
    
    if num_failed > 0:
        
        text_components.append( HydrusData.ToHumanInt( num_failed ) + ' failed (errors written to log)' )
        
    
    job_key.SetVariable( 'popup_text_1', ', '.join( text_components ) )
    
    if len( presentation_hashes ) > 0:
        
        job_key.SetVariable( 'popup_files', ( presentation_hashes, 'downloads' ) )
        
    
    job_key.DeleteVariable( 'popup_gauge_1' )
    
    job_key.Finish()
    
def UpdateFileSeedCacheWithAllParseResults( file_seed_cache, all_parse_results, source_url, max_new_urls_allowed = None ):
    
    new_file_seeds = []
    
    num_found = 0
    num_new = 0
    num_already_in = 0
    added_all_possible_urls = False
    
    for parse_results in all_parse_results:
        
        parsed_urls = ClientParsing.GetURLsFromParseResults( parse_results, ( HC.URL_TYPE_DESIRED, ), only_get_top_priority = True )
        
        for url in parsed_urls:
            
            num_found += 1
            
            if max_new_urls_allowed is not None and num_new == max_new_urls_allowed:
                
                continue
                
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.SetReferralURL( source_url )
            
            if file_seed_cache.HasFileSeed( file_seed ):
                
                num_already_in += 1
                
            else:
                
                num_new += 1
                
                file_seed.AddParseResults( parse_results )
                
                new_file_seeds.append( file_seed )
                
            
        
    
    file_seed_cache.AddFileSeeds( new_file_seeds )
    
    added_all_possible_urls == num_new + num_already_in == num_found
    
    return ( num_new, num_already_in, added_all_possible_urls )
    
def WakeRepeatingJob( job ):
    
    if job is not None:
        
        job.Wake()
        
    
class GalleryImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IMPORT
    SERIALISABLE_NAME = 'Gallery Import'
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
        
        self._tag_import_options = new_options.GetDefaultTagImportOptions( self._gallery_identifier )
        
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
        
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_options = self._tag_import_options.GetSerialisableTuple()
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        serialisable_current_query_stuff = ( self._current_query, self._current_query_num_new_urls, serialisable_current_gallery_stream_identifier, self._current_gallery_stream_identifier_page_index, serialisable_current_gallery_stream_identifier_found_urls, serialisable_pending_gallery_stream_identifiers )
        
        return ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, self._pending_queries, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_options, serialisable_tag_options, serialisable_gallery_seed_log, serialisable_file_seed_cache )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, self._pending_queries, self._file_limit, self._gallery_paused, self._files_paused, serialisable_file_options, serialisable_tag_options, serialisable_gallery_seed_log, serialisable_file_seed_cache ) = serialisable_info
        
        ( self._current_query, self._current_query_num_new_urls, serialisable_current_gallery_stream_identifier, self._current_gallery_stream_identifier_page_index, serialisable_current_gallery_stream_identifier_found_urls, serialisable_pending_gallery_stream_identifier ) = serialisable_current_query_stuff
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        
        self._gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_stream_identifier ) for serialisable_gallery_stream_identifier in serialisable_gallery_stream_identifiers ]
        
        if serialisable_current_gallery_stream_identifier is None:
            
            self._current_gallery_stream_identifier = None
            
        else:
            
            self._current_gallery_stream_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_current_gallery_stream_identifier )
            
        
        self._current_gallery_stream_identifier_found_urls = set( serialisable_current_gallery_stream_identifier_found_urls )
        
        self._pending_gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_pending_gallery_stream_identifier ) for serialisable_pending_gallery_stream_identifier in serialisable_pending_gallery_stream_identifier ]
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        
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
                    
                
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _SetGalleryStatus( self, status, timeout = None ):
        
        if HydrusData.TimeHasPassed( self._gallery_status_can_change_timestamp ):
            
            self._gallery_status = status
            
            if timeout is not None:
                
                self._gallery_status_can_change_timestamp = HydrusData.GetNow() + timeout
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, pending_queries, get_tags_if_url_recognised_and_file_redundant, file_limit, gallery_paused, files_paused, serialisable_file_options, serialisable_tag_options, serialisable_file_seed_cache ) = old_serialisable_info
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, pending_queries, file_limit, gallery_paused, files_paused, serialisable_file_options, serialisable_tag_options, serialisable_file_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, pending_queries, file_limit, gallery_paused, files_paused, serialisable_file_options, serialisable_tag_options, serialisable_file_seed_cache ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_current_query_stuff, pending_queries, file_limit, gallery_paused, files_paused, serialisable_file_options, serialisable_tag_options, serialisable_gallery_seed_log, serialisable_file_seed_cache )
            
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
                        
                    
                
                did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, GenerateDownloaderNetworkJobFactory( page_key ), self._FileNetworkJobPresentationContextFactory, self._file_import_options, self._tag_import_options )
                
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
            
            time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
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
            
        
        error_occured = False
        
        num_already_in_file_seed_cache = 0
        new_file_seeds = []
        
        try:
            
            try:
                
                gallery_url = gallery.GetGalleryPageURL( query, page_index )
                
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
                
            
            gallery_seed = ClientImportGallerySeeds.GallerySeed( gallery_url, can_generate_more_pages = False )
            
            gallery_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_NEW, note = status )
            
            self._gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
            
            if len( new_file_seeds ) > 0:
                
                WakeRepeatingJob( self._files_repeating_job )
                
            
        except Exception as e:
            
            if isinstance( e, HydrusExceptions.NotFoundException ):
                
                text = 'gallery 404'
                
            else:
                
                text = HydrusData.ToUnicode( e )
                
                HydrusData.DebugPrint( traceback.format_exc() )
                
            
            with self._lock:
                
                self._current_gallery_stream_identifier = None
                
                self._SetGalleryStatus( text, 5 )
                
            
            time.sleep( 5 )
            
        finally:
            
            wx.CallAfter( self._download_control_gallery_clear )
            
        
        with self._lock:
            
            status = query + ': ' + HydrusData.ToHumanInt( len( new_file_seeds ) ) + ' new urls found'
            
            if num_already_in_file_seed_cache > 0:
                
                status += ' (' + HydrusData.ToHumanInt( num_already_in_file_seed_cache ) + ' of last page already in queue)'
                
            
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
            
            WakeRepeatingJob( self._gallery_repeating_job )
            
        
    
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
            
            WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlayGallery( self ):
        
        with self._lock:
            
            self._gallery_paused = not self._gallery_paused
            
            WakeRepeatingJob( self._gallery_repeating_job )
            
        
    
    def PendQuery( self, query ):
        
        with self._lock:
            
            if query not in self._pending_queries:
                
                self._pending_queries.append( query )
                
                WakeRepeatingJob( self._gallery_repeating_job )
                
            
        
    
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
        
        self._files_repeating_job = HG.client_controller.CallRepeating( GetRepeatingJobInitialDelay(), REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles, page_key )
        self._gallery_repeating_job = HG.client_controller.CallRepeating( GetRepeatingJobInitialDelay(), REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnGallery, page_key )
        
    
    def REPEATINGWorkOnFiles( self, page_key ):
        
        with self._lock:
            
            if PageImporterShouldStopWorking( page_key ):
                
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
                
                if PageImporterShouldStopWorking( page_key ):
                    
                    self._files_repeating_job.Cancel()
                    
                    return
                    
                
                work_to_do = self._file_seed_cache.WorkToDo() and not ( self._files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                
            
        
    
    def REPEATINGWorkOnGallery( self, page_key ):
        
        with self._lock:
            
            if PageImporterShouldStopWorking( page_key ):
                
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
                
                if PageImporterShouldStopWorking( page_key ):
                    
                    self._gallery_repeating_job.Cancel()
                    
                    return
                    
                
                ok_to_work = not ( self._gallery_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_GALLERY_IMPORT ] = GalleryImport

class HDDImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_HDD_IMPORT
    SERIALISABLE_NAME = 'Local File Import'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, paths = None, file_import_options = None, paths_to_tags = None, delete_after_success = None ):
        
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
                    
                
                file_seeds.append( file_seed )
                
            
            self._file_seed_cache.AddFileSeeds( file_seeds )
            
        
        self._file_import_options = file_import_options
        self._paths_to_tags = paths_to_tags
        self._delete_after_success = delete_after_success
        
        self._current_action = ''
        self._paused = False
        
        self._lock = threading.Lock()
        
        self._files_repeating_job = None
        
        HG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_options = self._file_import_options.GetSerialisableTuple()
        serialisable_paths_to_tags = { path : { service_key.encode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in self._paths_to_tags.items() }
        
        return ( serialisable_file_seed_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_file_seed_cache, serialisable_options, serialisable_paths_to_tags, self._delete_after_success, self._paused ) = serialisable_info
        
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_options )
        self._paths_to_tags = { path : { service_key.decode( 'hex' ) : tags for ( service_key, tags ) in service_keys_to_tags.items() } for ( path, service_keys_to_tags ) in serialisable_paths_to_tags.items() }
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        path = file_seed.file_seed_data
        
        with self._lock:
            
            if path in self._paths_to_tags:
                
                service_keys_to_tags = self._paths_to_tags[ path ]
                
            else:
                
                service_keys_to_tags = {}
                
            
        
        try:
            
            if not os.path.exists( path ):
                
                raise Exception( 'Source file does not exist!' )
                
            
            with self._lock:
                
                self._current_action = 'importing'
                
            
            file_seed.ImportPath( self._file_import_options )
            
            did_substantial_work = True
            
            if file_seed.status in CC.SUCCESSFUL_IMPORT_STATES:
                
                hash = file_seed.GetHash()
                
                service_keys_to_content_updates = ClientData.ConvertServiceKeysToTagsToServiceKeysToContentUpdates( { hash }, service_keys_to_tags )
                
                if len( service_keys_to_content_updates ) > 0:
                    
                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                    
                    did_substantial_work = True
                    
                
                if file_seed.ShouldPresent( self._file_import_options ):
                    
                    file_seed.PresentToPage( page_key )
                    
                    did_substantial_work = True
                    
                
                if self._delete_after_success:
                    
                    try:
                        
                        ClientPaths.DeletePath( path )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'While attempting to delete ' + path + ', the following error occured:' )
                        HydrusData.ShowException( e )
                        
                    
                    txt_path = path + '.txt'
                    
                    if os.path.exists( txt_path ):
                        
                        try:
                            
                            ClientPaths.DeletePath( txt_path )
                            
                        except Exception as e:
                            
                            HydrusData.ShowText( 'While attempting to delete ' + txt_path + ', the following error occured:' )
                            HydrusData.ShowException( e )
                            
                        
                    
                
            
        except HydrusExceptions.VetoException as e:
            
            status = CC.STATUS_VETOED
            
            note = HydrusData.ToUnicode( e )
            
            file_seed.SetStatus( status, note = note )
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            file_seed.SetStatus( status, exception = e )
            
        finally:
            
            self._file_seed_cache.NotifyFileSeedsUpdated( ( file_seed, ) )
            
            with self._lock:
                
                self._current_action = ''
                
            
        
        if did_substantial_work:
            
            time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
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
            
            WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def Start( self, page_key ):
        
        self._files_repeating_job = HG.client_controller.CallRepeating( GetRepeatingJobInitialDelay(), REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles, page_key )
        
    
    def REPEATINGWorkOnFiles( self, page_key ):
        
        with self._lock:
            
            if PageImporterShouldStopWorking( page_key ):
                
                self._files_repeating_job.Cancel()
                
                return
                
            
            work_to_do = self._file_seed_cache.WorkToDo() and not ( self._paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
            
        
        while work_to_do:
            
            try:
                
                self._WorkOnFiles( page_key )
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if PageImporterShouldStopWorking( page_key ):
                    
                    self._files_repeating_job.Cancel()
                    
                    return
                    
                
                work_to_do = self._file_seed_cache.WorkToDo() and not ( self._paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                
            
        
    
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
            
            tag_import_options = HG.client_controller.new_options.GetDefaultTagImportOptions( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEFAULT ) )
            
        
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
                        
                        if os.path.exists( path ):
                            
                            ClientPaths.DeletePath( path )
                            
                        
                        txt_path = path + '.txt'
                        
                        if os.path.exists( txt_path ):
                            
                            ClientPaths.DeletePath( txt_path )
                            
                        
                        self._file_seed_cache.RemoveFileSeeds( ( file_seed, ) )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Import folder tried to delete ' + path + ', but could not:' )
                        
                        HydrusData.ShowException( e )
                        
                        HydrusData.ShowText( 'Import folder has been paused.' )
                        
                        self._paused = True
                        
                        return
                        
                    
                
            elif action == CC.IMPORT_FOLDER_MOVE:
                
                while True:
                    
                    file_seed = self._file_seed_cache.GetNextFileSeed( status )
                    
                    if file_seed is None or HG.view_shutdown:
                        
                        break
                        
                    
                    path = file_seed.file_seed_data
                    
                    try:
                        
                        dest_dir = self._action_locations[ status ]
                        
                        if not os.path.exists( dest_dir ):
                            
                            raise HydrusExceptions.DataMissing( 'The move location "' + dest_dir + '" does not exist!' )
                            
                        
                        if os.path.exists( path ):
                            
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
        
        filenames = os.listdir( HydrusData.ToUnicode( self._path ) )
        
        raw_paths = [ os.path.join( self._path, filename ) for filename in filenames ]
        
        all_paths = ClientFiles.GetAllPaths( raw_paths )
        
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
        serialisable_tag_service_keys_to_filename_tagging_options = [ ( service_key.encode( 'hex' ), filename_tagging_options.GetSerialisableTuple() ) for ( service_key, filename_tagging_options ) in self._tag_service_keys_to_filename_tagging_options.items() ]
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        # json turns int dict keys to strings
        action_pairs = self._actions.items()
        action_location_pairs = self._action_locations.items()
        
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
                
            
            if HydrusData.TimeHasPassed( time_to_save ):
                
                HG.client_controller.WriteSynchronous( 'serialisable', self )
                
                time_to_save = HydrusData.GetNow() + 600
                
            
            gauge_num_done = num_total_done + num_files_imported + 1
            
            job_key.SetVariable( 'popup_text_1', 'importing file ' + HydrusData.ConvertValueRangeToPrettyString( gauge_num_done, num_total ) )
            job_key.SetVariable( 'popup_gauge_1', ( gauge_num_done, num_total ) )
            
            path = file_seed.file_seed_data
            
            try:
                
                mime = HydrusFileHandling.GetMime( path )
                
                if mime in self._mimes:
                    
                    file_seed.ImportPath( self._file_import_options )
                    
                    hash = file_seed.GetHash()
                    
                    if file_seed.status in CC.SUCCESSFUL_IMPORT_STATES:
                        
                        downloaded_tags = []
                        
                        in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                        
                        service_keys_to_content_updates = self._tag_import_options.GetServiceKeysToContentUpdates( file_seed.status, in_inbox, hash, downloaded_tags ) # additional tags
                        
                        if len( service_keys_to_content_updates ) > 0:
                            
                            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                            
                        
                        service_keys_to_tags = {}
                        
                        for ( tag_service_key, filename_tagging_options ) in self._tag_service_keys_to_filename_tagging_options.items():
                            
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
                                
                            
                        
                    
                else:
                    
                    file_seed.SetStatus( CC.STATUS_VETOED )
                    
                
            except Exception as e:
                
                error_text = traceback.format_exc()
                
                HydrusData.Print( 'A file failed to import from import folder ' + self._name + ':' + path )
                
                file_seed.SetStatus( CC.STATUS_ERROR, exception = e )
                
            finally:
                
                did_work = True
                
            
            i += 1
            
            if i % 10 == 0:
                
                self._ActionPaths()
                
            
        
        if num_files_imported > 0:
            
            HydrusData.Print( 'Import folder ' + self._name + ' imported ' + HydrusData.ToHumanInt( num_files_imported ) + ' files.' )
            
            if len( presentation_hashes ) > 0:
                
                PublishPresentationHashes( self._name, presentation_hashes, self._publish_files_to_popup_button, self._publish_files_to_page )
                
            
        
        self._ActionPaths()
        
        return did_work
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._path, self._mimes, serialisable_file_import_options, serialisable_tag_import_options, serialisable_tag_service_keys_to_filename_tagging_options, action_pairs, action_location_pairs, self._period, self._check_regularly, serialisable_file_seed_cache, self._last_checked, self._paused, self._check_now, self._show_working_popup, self._publish_files_to_popup_button, self._publish_files_to_page ) = serialisable_info
        
        self._actions = dict( action_pairs )
        self._action_locations = dict( action_location_pairs )
        
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        self._tag_service_keys_to_filename_tagging_options = dict( [ ( encoded_service_key.decode( 'hex' ), HydrusSerialisable.CreateFromSerialisableTuple( serialisable_filename_tagging_options ) ) for ( encoded_service_key, serialisable_filename_tagging_options ) in serialisable_tag_service_keys_to_filename_tagging_options ] )
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
            
            txt_parse_tag_service_keys = [ service_key.decode( 'hex' ) for service_key in serialisable_txt_parse_tag_service_keys ]
            
            tag_service_keys_to_filename_tagging_options = {}
            
            for service_key in txt_parse_tag_service_keys:
                
                filename_tagging_options = ClientImportOptions.FilenameTaggingOptions()
                
                filename_tagging_options._load_from_neighbouring_txt_files = True
                
                tag_service_keys_to_filename_tagging_options[ service_key ] = filename_tagging_options
                
            
            serialisable_tag_service_keys_to_filename_tagging_options = [ ( service_key.encode( 'hex' ), filename_tagging_options.GetSerialisableTuple() ) for ( service_key, filename_tagging_options ) in tag_service_keys_to_filename_tagging_options.items() ]
            
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
        
        self._check_now = True
        
    
    def DoWork( self ):
        
        if HG.view_shutdown:
            
            return
            
        
        if HC.options[ 'pause_import_folders_sync' ] or self._paused:
            
            return
            
        
        if not os.path.exists( self._path ) or not os.path.isdir( self._path ):
            
            return
            
        
        pubbed_job_key = False
        
        job_key = ClientThreading.JobKey( pausable = False, cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'import folder - ' + self._name )
        
        due_by_check_now = self._check_now
        due_by_period = self._check_regularly and HydrusData.TimeHasPassed( self._last_checked + self._period )
        
        checked_folder = False
        
        if due_by_check_now or due_by_period:
            
            if not pubbed_job_key and self._show_working_popup:
                
                HG.client_controller.pub( 'message', job_key )
                
                pubbed_job_key = True
                
            
            self._CheckFolder( job_key )
            
            checked_folder = True
            
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        did_import_file_work = False
        
        if file_seed is not None:
            
            if not pubbed_job_key and self._show_working_popup:
                
                HG.client_controller.pub( 'message', job_key )
                
                pubbed_job_key = True
                
            
            did_import_file_work = self._ImportFiles( job_key )
            
        
        if checked_folder or did_import_file_work:
            
            HG.client_controller.WriteSynchronous( 'serialisable', self )
            
        
        job_key.Delete()
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def ToListBoxTuple( self ):
        
        return ( self._name, self._path, self._period )
        
    
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

class NetworkJobPresentationContext( object ):
    
    def __init__( self, enter_call, exit_call ):
        
        self._enter_call = enter_call
        self._exit_call = exit_call
        
    
    def __enter__( self ):
        
        self._enter_call()
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self._exit_call()
        
    
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
        
        self._parser_status = ''
        self._current_action = ''
        
        self._download_control_file_set = None
        self._download_control_file_clear = None
        self._download_control_page_set = None
        self._download_control_page_clear = None
        
        self._lock = threading.Lock()
        
        self._files_repeating_job = None
        self._queue_repeating_job = None
        
        HG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        
    
    def _FileNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                if self._download_control_file_set is not None:
                    
                    wx.CallAfter( self._download_control_file_set, network_job )
                    
                
            
        
        def exit_call():
            
            with self._lock:
                
                if self._download_control_file_clear is not None:
                    
                    wx.CallAfter( self._download_control_file_clear )
                    
                
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_pending_jobs = [ ( url, simple_downloader_formula.GetSerialisableTuple() ) for ( url, simple_downloader_formula ) in self._pending_jobs ]
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        
        return ( serialisable_pending_jobs, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_options, self._formula_name, self._queue_paused, self._files_paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_pending_jobs, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_options, self._formula_name, self._queue_paused, self._files_paused ) = serialisable_info
        
        self._pending_jobs = [ ( url, HydrusSerialisable.CreateFromSerialisableTuple( serialisable_simple_downloader_formula ) ) for ( url, serialisable_simple_downloader_formula ) in serialisable_pending_jobs ]
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        
    
    def _PageNetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                if self._download_control_page_set is not None:
                    
                    wx.CallAfter( self._download_control_page_set, network_job )
                    
                
            
        
        def exit_call():
            
            with self._lock:
                
                if self._download_control_page_clear is not None:
                    
                    wx.CallAfter( self._download_control_page_clear )
                    
                
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( pending_page_urls, serialisable_file_seed_cache, serialisable_file_options, download_image_links, download_unlinked_images, paused ) = old_serialisable_info
            
            queue_paused = paused
            files_paused = paused
            
            new_serialisable_info = ( pending_page_urls, serialisable_file_seed_cache, serialisable_file_options, download_image_links, download_unlinked_images, queue_paused, files_paused )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( pending_page_urls, serialisable_file_seed_cache, serialisable_file_options, download_image_links, download_unlinked_images, queue_paused, files_paused ) = old_serialisable_info
            
            pending_jobs = []
            
            new_serialisable_info = ( pending_jobs, serialisable_file_seed_cache, serialisable_file_options, queue_paused, files_paused )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( pending_jobs, serialisable_file_seed_cache, serialisable_file_options, queue_paused, files_paused ) = old_serialisable_info
            
            pending_jobs = []
            
            formula_name = 'all files linked by images in page'
            
            new_serialisable_info = ( pending_jobs, serialisable_file_seed_cache, serialisable_file_options, formula_name, queue_paused, files_paused )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( pending_jobs, serialisable_file_seed_cache, serialisable_file_options, formula_name, queue_paused, files_paused ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( pending_jobs, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_options, formula_name, queue_paused, files_paused )
            
            return ( 5, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        file_url = file_seed.file_seed_data
        
        try:
            
            def status_hook( text ):
                
                with self._lock:
                    
                    self._current_action = text
                    
                
            
            tag_import_options = HG.client_controller.network_engine.domain_manager.GetDefaultTagImportOptionsForURL( file_seed.file_seed_data )
            
            did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, GenerateDownloaderNetworkJobFactory( page_key ), self._FileNetworkJobPresentationContextFactory, self._file_import_options, tag_import_options )
            
            if file_seed.ShouldPresent( self._file_import_options ):
                
                file_seed.PresentToPage( page_key )
                
                did_substantial_work = True
                
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            file_seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            self._file_seed_cache.NotifyFileSeedsUpdated( ( file_seed, ) )
            
            with self._lock:
                
                self._current_action = ''
                
            
        
        if did_substantial_work:
            
            time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def _WorkOnQueue( self, page_key ):
        
        if len( self._pending_jobs ) > 0:
            
            with self._lock:
                
                ( url, simple_downloader_formula ) = self._pending_jobs.pop( 0 )
                
                self._parser_status = 'checking ' + url
                
            
            error_occurred = False
            
            try:
                
                network_job = ClientNetworkingJobs.NetworkJobDownloader( page_key, 'GET', url )
                
                network_job.OverrideBandwidth( 30 )
                
                HG.client_controller.network_engine.AddJob( network_job )
                
                with self._PageNetworkJobPresentationContextFactory( network_job ):
                    
                    network_job.WaitUntilDone()
                    
                
                data = network_job.GetContent()
                
                #
                
                parsing_context = {}
                
                parsing_context[ 'url' ] = url
                
                parsing_formula = simple_downloader_formula.GetFormula()
                
                file_seeds = []
                
                for parsed_text in parsing_formula.Parse( parsing_context, data ):
                    
                    try:
                        
                        file_url = urlparse.urljoin( url, parsed_text )
                        
                        file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, file_url )
                        
                        file_seed.SetReferralURL( url )
                        
                        file_seeds.append( file_seed )
                        
                    except:
                        
                        continue
                        
                    
                
                num_new = self._file_seed_cache.AddFileSeeds( file_seeds )
                
                if num_new > 0:
                    
                    WakeRepeatingJob( self._files_repeating_job )
                    
                
                parser_status = 'page checked OK with formula "' + simple_downloader_formula.GetName() + '" - ' + HydrusData.ToHumanInt( num_new ) + ' new urls'
                
                num_already_in_file_seed_cache = len( file_seeds ) - num_new
                
                if num_already_in_file_seed_cache > 0:
                    
                    parser_status += ' (' + HydrusData.ToHumanInt( num_already_in_file_seed_cache ) + ' already in queue)'
                    
                
                gallery_seed = ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = False )
                
                gallery_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_NEW, note = parser_status )
                
                self._gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
                
            except HydrusExceptions.ShutdownException:
                
                return
                
            except HydrusExceptions.NotFoundException:
                
                error_occurred = True
                
                parser_status = 'page 404'
                
            except Exception as e:
                
                error_occurred = True
                
                parser_status = HydrusData.ToUnicode( e )
                
            
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
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( list( self._pending_jobs ), self._parser_status, self._current_action, self._queue_paused, self._files_paused )
            
        
    
    def GetValueRange( self ):
        
        with self._lock:
            
            return self._file_seed_cache.GetValueRange()
            
        
    
    def NotifyFileSeedsUpdated( self, file_seed_cache_key, file_seeds ):
        
        if file_seed_cache_key == self._file_seed_cache.GetFileSeedCacheKey():
            
            WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlayFiles( self ):
        
        with self._lock:
            
            self._files_paused = not self._files_paused
            
            WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlayQueue( self ):
        
        with self._lock:
            
            self._queue_paused = not self._queue_paused
            
            WakeRepeatingJob( self._queue_repeating_job )
            
        
    
    def PendJob( self, job ):
        
        with self._lock:
            
            if job not in self._pending_jobs:
                
                self._pending_jobs.append( job )
                
                WakeRepeatingJob( self._queue_repeating_job )
                
            
        
    
    def SetDownloadControlFile( self, download_control ):
        
        with self._lock:
            
            self._download_control_file_set = download_control.SetNetworkJob
            self._download_control_file_clear = download_control.ClearNetworkJob
            
        
    
    def SetDownloadControlPage( self, download_control ):
        
        with self._lock:
            
            self._download_control_page_set = download_control.SetNetworkJob
            self._download_control_page_clear = download_control.ClearNetworkJob
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def SetFormulaName( self, formula_name ):
        
        with self._lock:
            
            self._formula_name = formula_name
            
        
    
    def Start( self, page_key ):
        
        self._files_repeating_job = HG.client_controller.CallRepeating( GetRepeatingJobInitialDelay(), REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles, page_key )
        self._queue_repeating_job = HG.client_controller.CallRepeating( GetRepeatingJobInitialDelay(), REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnQueue, page_key )
        
    
    def REPEATINGWorkOnFiles( self, page_key ):
        
        with self._lock:
            
            if PageImporterShouldStopWorking( page_key ):
                
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
                
                if PageImporterShouldStopWorking( page_key ):
                    
                    self._files_repeating_job.Cancel()
                    
                    return
                    
                
                work_to_do = self._file_seed_cache.WorkToDo() and not ( self._files_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                
            
        
    
    def REPEATINGWorkOnQueue( self, page_key ):
        
        with self._lock:
            
            if PageImporterShouldStopWorking( page_key ):
                
                self._queue_repeating_job.Cancel()
                
                return
                
            
            ok_to_work = not ( self._queue_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
            
        
        while ok_to_work:
            
            try:
                
                did_work = self._WorkOnQueue( page_key )
                
                if did_work:
                    
                    time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
                    
                else:
                    
                    return
                    
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if PageImporterShouldStopWorking( page_key ):
                    
                    self._queue_repeating_job.Cancel()
                    
                    return
                    
                
                ok_to_work = not ( self._queue_paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SIMPLE_DOWNLOADER_IMPORT ] = SimpleDownloaderImport

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_NAME = 'Subscription'
    SERIALISABLE_VERSION = 6
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART )
        
        self._gallery_stream_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( self._gallery_identifier )
        
        self._queries = []
        
        new_options = HG.client_controller.new_options
        
        self._checker_options = ClientDefaults.GetDefaultCheckerOptions( 'artist subscription' )
        
        if HC.options[ 'gallery_file_limit' ] is None:
            
            self._initial_file_limit = 200
            
        else:
            
            self._initial_file_limit = min( 200, HC.options[ 'gallery_file_limit' ] )
            
        
        self._periodic_file_limit = 50
        self._paused = False
        
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'quiet' )
        
        new_options = HG.client_controller.new_options
        
        self._tag_import_options = new_options.GetDefaultTagImportOptions( self._gallery_identifier )
        
        self._last_gallery_page_hit_timestamp = 0
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        self._publish_files_to_popup_button = True
        self._publish_files_to_page = False
        self._merge_query_publish_events = True
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusData.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _GetExampleNetworkContexts( self, query ):
        
        file_seed_cache = query.GetFileSeedCache()
        
        file_seed = file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return [ ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, self._GetNetworkJobSubscriptionKey( query ) ), ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
            
        
        url = file_seed.file_seed_data
        
        example_nj = ClientNetworkingJobs.NetworkJobSubscription( self._GetNetworkJobSubscriptionKey( query ), 'GET', url )
        example_network_contexts = example_nj.GetNetworkContexts()
        
        return example_network_contexts
        
    
    def _GetNetworkJobSubscriptionKey( self, query ):
        
        query_text = query.GetQueryText()
        
        return self._name + ': ' + query_text
        
    
    def _GetQueriesForProcessing( self ):
        
        queries = list( self._queries )
        
        if HG.client_controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
            
            random.shuffle( queries )
            
        else:
            
            def key( q ):
                
                return q.GetQueryText()
                
            
            queries.sort( key = key )
            
        
        return queries
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_identifier = self._gallery_identifier.GetSerialisableTuple()
        serialisable_gallery_stream_identifiers = [ gallery_stream_identifier.GetSerialisableTuple() for gallery_stream_identifier in self._gallery_stream_identifiers ]
        serialisable_queries = [ query.GetSerialisableTuple() for query in self._queries ]
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_options, serialisable_tag_options, self._no_work_until, self._no_work_until_reason, self._publish_files_to_popup_button, self._publish_files_to_page, self._merge_query_publish_events )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_options, serialisable_tag_options, self._no_work_until, self._no_work_until_reason, self._publish_files_to_popup_button, self._publish_files_to_page, self._merge_query_publish_events ) = serialisable_info
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        self._gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_stream_identifier ) for serialisable_gallery_stream_identifier in serialisable_gallery_stream_identifiers ]
        self._queries = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_query ) for serialisable_query in serialisable_queries ]
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_options )
        
    
    def _NoDelays( self ):
        
        return HydrusData.TimeHasPassed( self._no_work_until )
        
    
    def _QueryBandwidthIsOK( self, query ):
        
        example_network_contexts = self._GetExampleNetworkContexts( query )
        
        # just a little padding here
        expected_requests = 3
        expected_bytes = 1048576
        threshold = 90
        
        result = HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_network_contexts, expected_requests = expected_requests, expected_bytes = expected_bytes, threshold = threshold )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + query.GetQueryText() + '" pre-work bandwidth test. Bandwidth ok: ' + str( result ) + '.' )
            
        
        return result
        
    
    def _ShowHitPeriodicFileLimitMessage( self, query_text ):
        
        message = 'When syncing, the query "' + query_text + '" for subscription "' + self._name + '" hit its periodic file limit!'
        message += os.linesep * 2
        message += 'This may be because the query has not run in a while--so the backlog of files has built up--or that the site has changed how it presents file urls on its gallery pages (and so the subscription thinks it is seeing new files when it truly is not).'
        message += os.linesep * 2
        message += 'If the former is true, you might want to fill in the gap with a manual download page, but if the latter is true, the maintainer for the download parser (hydrus dev or whoever), would be interested in knowing this information so they can roll out a fix.'
        
        HydrusData.ShowText( message )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, last_error, serialisable_file_seed_cache ) = old_serialisable_info
            
            check_now = False
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, check_now, last_error, serialisable_file_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, check_now, last_error, serialisable_file_seed_cache ) = old_serialisable_info
            
            no_work_until = 0
            no_work_until_reason = ''
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, check_now, last_error, no_work_until, no_work_until_reason, serialisable_file_seed_cache )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, last_checked, check_now, last_error, no_work_until, no_work_until_reason, serialisable_file_seed_cache ) = old_serialisable_info
            
            checker_options = ClientImportOptions.CheckerOptions( 5, period / 5, period * 10, ( 1, period * 10 ) )
            
            file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
            
            query = SubscriptionQuery( query )
            
            query._file_seed_cache = file_seed_cache
            query._last_check_time = last_checked
            
            query.UpdateNextCheckTime( checker_options )
            
            queries = [ query ]
            
            serialisable_queries = [ query.GetSerialisableTuple() for query in queries ]
            serialisable_checker_options = checker_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, no_work_until, no_work_until_reason )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, no_work_until, no_work_until_reason ) = old_serialisable_info
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, no_work_until, no_work_until_reason )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, no_work_until, no_work_until_reason ) = old_serialisable_info
            
            publish_files_to_popup_button = True
            publish_files_to_page = False
            merge_query_publish_events = True
            
            new_serialisable_info = new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_options, serialisable_tag_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events )
            
            return ( 6, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, job_key ):
        
        try:
            
            gallery = ClientDownloading.GetGallery( self._gallery_identifier )
            
        except Exception as e:
            
            HydrusData.PrintException( e )
            
            self._DelayWork( HC.UPDATE_DURATION, 'gallery would not load' )
            
            self._paused = True
            
            HydrusData.ShowText( 'The subscription ' + self._name + ' could not load its gallery! It has been paused and the full error has been written to the log!' )
            
            return
            
        
        error_count = 0
        
        all_presentation_hashes = []
        all_presentation_hashes_fast = set()
        
        queries = self._GetQueriesForProcessing()
        
        for query in queries:
            
            this_query_has_done_work = False
            
            query_text = query.GetQueryText()
            file_seed_cache = query.GetFileSeedCache()
            
            def network_job_factory( method, url, **kwargs ):
                
                network_job = ClientNetworkingJobs.NetworkJobSubscription( self._GetNetworkJobSubscriptionKey( query ), method, url, **kwargs )
                
                network_job.OverrideBandwidth( 30 )
                
                job_key.SetVariable( 'popup_network_job', network_job )
                
                return network_job
                
            
            gallery.SetNetworkJobFactory( network_job_factory )
            
            text_1 = 'downloading files'
            query_summary_name = self._name
            
            if query_text != self._name:
                
                text_1 += ' for "' + query_text + '"'
                query_summary_name += ': ' + query_text
                
            
            job_key.SetVariable( 'popup_text_1', text_1 )
            
            presentation_hashes = []
            presentation_hashes_fast = set()
            
            while True:
                
                num_urls = file_seed_cache.GetFileSeedCount()
                num_unknown = file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
                num_done = num_urls - num_unknown
                
                file_seed = file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
                
                if file_seed is None:
                    
                    if HG.subscription_report_mode:
                        
                        HydrusData.ShowText( 'Query "' + query_text + '" can do no more file work due to running out of unknown urls.' )
                        
                    
                    break
                    
                
                if job_key.IsCancelled():
                    
                    self._DelayWork( 300, 'recently cancelled' )
                    
                    break
                    
                
                p1 = HC.options[ 'pause_subs_sync' ]
                p3 = HG.view_shutdown
                p4 = not self._QueryBandwidthIsOK( query )
                
                if p1 or p3 or p4:
                    
                    if p4 and this_query_has_done_work:
                        
                        job_key.SetVariable( 'popup_text_2', 'no more bandwidth to download files, will do some more later' )
                        
                        time.sleep( 5 )
                        
                    
                    break
                    
                
                try:
                    
                    x_out_of_y = 'file ' + HydrusData.ConvertValueRangeToPrettyString( num_done, num_urls ) + ': '
                    
                    job_key.SetVariable( 'popup_gauge_2', ( num_done, num_urls ) )
                    
                    if file_seed.WorksInNewSystem():
                        
                        def status_hook( text ):
                            
                            job_key.SetVariable( 'popup_text_2', x_out_of_y + text )
                            
                            
                        
                        file_seed.WorkOnURL( file_seed_cache, status_hook, GenerateSubscriptionNetworkJobFactory( self._GetNetworkJobSubscriptionKey( query ) ), GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key ), self._file_import_options, self._tag_import_options )
                        
                        if file_seed.ShouldPresent( self._file_import_options ):
                            
                            hash = file_seed.GetHash()
                            
                            if hash not in presentation_hashes_fast:
                                
                                if hash not in all_presentation_hashes_fast:
                                    
                                    all_presentation_hashes.append( hash )
                                    
                                    all_presentation_hashes_fast.add( hash )
                                    
                                
                                presentation_hashes.append( hash )
                                
                                presentation_hashes_fast.add( hash )
                                
                            
                        
                    else:
                        
                        job_key.SetVariable( 'popup_text_2', x_out_of_y + 'checking url status' )
                        
                        ( should_download_metadata, should_download_file ) = file_seed.PredictPreImportStatus( self._file_import_options, self._tag_import_options )
                        
                        status = file_seed.status
                        url = file_seed.file_seed_data
                        
                        if status == CC.STATUS_SUCCESSFUL_BUT_REDUNDANT:
                            
                            if self._tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB() and self._tag_import_options.WorthFetchingTags():
                                
                                job_key.SetVariable( 'popup_text_2', x_out_of_y + 'found file in db, fetching tags' )
                                
                                downloaded_tags = gallery.GetTags( url )
                                
                                file_seed.AddTags( downloaded_tags )
                                
                            
                        elif status == CC.STATUS_UNKNOWN:
                            
                            ( os_file_handle, temp_path ) = ClientPaths.GetTempPath()
                            
                            try:
                                
                                job_key.SetVariable( 'popup_text_2', x_out_of_y + 'downloading file' )
                                
                                if self._tag_import_options.WorthFetchingTags():
                                    
                                    downloaded_tags = gallery.GetFileAndTags( temp_path, url )
                                    
                                    file_seed.AddTags( downloaded_tags )
                                    
                                else:
                                    
                                    gallery.GetFile( temp_path, url )
                                    
                                
                                file_seed.CheckPreFetchMetadata( self._tag_import_options )
                                
                                job_key.SetVariable( 'popup_text_2', x_out_of_y + 'importing file' )
                                
                                file_seed.Import( temp_path, self._file_import_options )
                                
                                hash = file_seed.GetHash()
                                
                                if hash not in presentation_hashes_fast:
                                    
                                    if file_seed.ShouldPresent( self._file_import_options ):
                                        
                                        if hash not in all_presentation_hashes_fast:
                                            
                                            all_presentation_hashes.append( hash )
                                            
                                            all_presentation_hashes_fast.add( hash )
                                            
                                        
                                        presentation_hashes.append( hash )
                                        
                                        presentation_hashes_fast.add( hash )
                                        
                                    
                                
                            finally:
                                
                                HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
                                
                            
                        
                        file_seed.WriteContentUpdates( self._tag_import_options )
                        
                    
                except HydrusExceptions.CancelledException as e:
                    
                    self._DelayWork( 300, HydrusData.ToUnicode( e ) )
                    
                    break
                    
                except HydrusExceptions.VetoException as e:
                    
                    status = CC.STATUS_VETOED
                    
                    note = HydrusData.ToUnicode( e )
                    
                    file_seed.SetStatus( status, note = note )
                    
                except HydrusExceptions.NotFoundException:
                    
                    status = CC.STATUS_VETOED
                    
                    note = '404'
                    
                    file_seed.SetStatus( status, note = note )
                    
                except Exception as e:
                    
                    status = CC.STATUS_ERROR
                    
                    job_key.SetVariable( 'popup_text_2', x_out_of_y + 'file failed' )
                    
                    file_seed.SetStatus( status, exception = e )
                    
                    if isinstance( e, HydrusExceptions.DataMissing ):
                        
                        # DataMissing is a quick thing to avoid subscription abandons when lots of deleted files in e621 (or any other booru)
                        # this should be richer in any case in the new system
                        
                        pass
                        
                    else:
                        
                        error_count += 1
                        
                        time.sleep( 10 )
                        
                    
                    if error_count > 4:
                        
                        raise Exception( 'The subscription ' + self._name + ' encountered several errors when downloading files, so it abandoned its sync.' )
                        
                    
                
                this_query_has_done_work = True
                
                if len( presentation_hashes ) > 0:
                    
                    job_key.SetVariable( 'popup_files', ( list( presentation_hashes ), query_summary_name ) )
                    
                
                time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
                
                HG.client_controller.WaitUntilViewFree()
                
            
            if not self._merge_query_publish_events and len( presentation_hashes ) > 0:
                
                PublishPresentationHashes( query_summary_name, presentation_hashes, self._publish_files_to_popup_button, self._publish_files_to_page )
                
            
        
        if self._merge_query_publish_events and len( all_presentation_hashes ) > 0:
            
            PublishPresentationHashes( self._name, all_presentation_hashes, self._publish_files_to_popup_button, self._publish_files_to_page )
            
        
        job_key.DeleteVariable( 'popup_files' )
        job_key.DeleteVariable( 'popup_text_1' )
        job_key.DeleteVariable( 'popup_text_2' )
        job_key.DeleteVariable( 'popup_gauge_2' )
        
    
    def _WorkOnFilesCanDoWork( self ):
        
        for query in self._queries:
            
            if query.CanWorkOnFiles():
                
                if self._QueryBandwidthIsOK( query ):
                    
                    return True
                    
                
            
        
        return False
        
    
    def _SyncQuery( self, job_key ):
        
        have_made_an_initial_sync_bandwidth_notification = False
        
        queries = self._GetQueriesForProcessing()
        
        for query in queries:
            
            can_sync = query.CanSync()
            
            if HG.subscription_report_mode:
                
                HydrusData.ShowText( 'Query "' + query.GetQueryText() + '" started. Current can_sync is ' + str( can_sync ) + '.' )
                
            
            if not can_sync:
                
                continue
                
            
            done_first_page = False
            
            query_text = query.GetQueryText()
            file_seed_cache = query.GetFileSeedCache()
            
            this_is_initial_sync = query.IsInitialSync()
            total_new_urls = 0
            
            file_seeds_to_add = set()
            file_seeds_to_add_ordered = []
            
            prefix = 'synchronising'
            
            if query_text != self._name:
                
                prefix += ' "' + query_text + '"'
                
            
            job_key.SetVariable( 'popup_text_1', prefix )
            
            for gallery_stream_identifier in self._gallery_stream_identifiers:
                
                if this_is_initial_sync:
                    
                    if self._initial_file_limit is not None and total_new_urls + 1 > self._initial_file_limit:
                        
                        break
                        
                    
                else:
                    
                    if self._periodic_file_limit is not None and total_new_urls + 1 > self._periodic_file_limit:
                        
                        self._ShowHitPeriodicFileLimitMessage( query_text )
                        
                        break
                        
                    
                
                p1 = HC.options[ 'pause_subs_sync' ]
                p2 = job_key.IsCancelled()
                p3 = HG.view_shutdown
                
                if p1 or p2 or p3:
                    
                    break
                    
                
                try:
                    
                    gallery = ClientDownloading.GetGallery( gallery_stream_identifier )
                    
                except Exception as e:
                    
                    HydrusData.PrintException( e )
                    
                    self._DelayWork( HC.UPDATE_DURATION, 'gallery would not load' )
                    
                    self._paused = True
                    
                    HydrusData.ShowText( 'The subscription ' + self._name + ' could not load its gallery! It has been paused and the full error has been written to the log!' )
                    
                    return
                    
                
                def network_job_factory( method, url, **kwargs ):
                    
                    network_job = ClientNetworkingJobs.NetworkJobSubscription( self._GetNetworkJobSubscriptionKey( query ), method, url, **kwargs )
                    
                    job_key.SetVariable( 'popup_network_job', network_job )
                    
                    network_job.OverrideBandwidth( 30 )
                    
                    return network_job
                    
                
                gallery.SetNetworkJobFactory( network_job_factory )
                
                page_index = 0
                num_existing_urls = 0
                keep_checking = True
                
                while keep_checking:
                    
                    new_urls_this_page = 0
                    
                    try:
                        
                        p1 = HC.options[ 'pause_subs_sync' ]
                        p2 = HG.view_shutdown
                        
                        if p1 or p2:
                            
                            return
                            
                        
                        if job_key.IsCancelled():
                            
                            raise HydrusExceptions.CancelledException( 'gallery parsing cancelled, likely by user' )
                            
                        
                        next_gallery_page_hit_timestamp = self._last_gallery_page_hit_timestamp + HG.client_controller.new_options.GetInteger( 'gallery_page_wait_period_subscriptions' )
                        
                        if not HydrusData.TimeHasPassed( next_gallery_page_hit_timestamp ):
                            
                            if not done_first_page:
                                
                                page_check_status = 'checking first page ' + HydrusData.TimestampToPrettyTimeDelta( next_gallery_page_hit_timestamp )
                                
                            else:
                                
                                page_check_status = HydrusData.ToHumanInt( total_new_urls ) + ' new urls found, checking next page ' + HydrusData.TimestampToPrettyTimeDelta( next_gallery_page_hit_timestamp )
                                
                            
                            job_key.SetVariable( 'popup_text_1', prefix + ': ' + page_check_status )
                            
                            time.sleep( 1 )
                            
                            continue
                            
                        
                        job_key.SetVariable( 'popup_text_1', prefix + ': found ' + HydrusData.ToHumanInt( total_new_urls ) + ' new urls, checking next page' )
                        
                        try:
                            
                            gallery_url = gallery.GetGalleryPageURL( query_text, page_index )
                            
                            ( page_of_file_seeds, definitely_no_more_pages ) = gallery.GetPage( gallery_url )
                            
                        finally:
                            
                            self._last_gallery_page_hit_timestamp = HydrusData.GetNow()
                            
                        
                        done_first_page = True
                        
                        page_index += 1
                        
                        if definitely_no_more_pages:
                            
                            keep_checking = False
                            
                        
                        for file_seed in page_of_file_seeds:
                            
                            if this_is_initial_sync:
                                
                                if self._initial_file_limit is not None and total_new_urls + 1 > self._initial_file_limit:
                                    
                                    keep_checking = False
                                    
                                    break
                                    
                                
                            else:
                                
                                if self._periodic_file_limit is not None and total_new_urls + 1 > self._periodic_file_limit:
                                    
                                    self._ShowHitPeriodicFileLimitMessage( query_text )
                                    
                                    keep_checking = False
                                    
                                    break
                                    
                                
                            
                            if file_seed in file_seeds_to_add:
                                
                                # this catches the occasional overflow when a new file is uploaded while gallery parsing is going on
                                
                                continue
                                
                            
                            if file_seed_cache.HasFileSeed( file_seed ):
                                
                                num_existing_urls += 1
                                
                                if num_existing_urls > 5:
                                    
                                    keep_checking = False
                                    
                                    break
                                    
                                
                            else:
                                
                                file_seeds_to_add.add( file_seed )
                                file_seeds_to_add_ordered.append( file_seed )
                                
                                new_urls_this_page += 1
                                total_new_urls += 1
                                
                            
                        
                        if new_urls_this_page == 0:
                            
                            keep_checking = False
                            
                        
                        status = 'checked OK - found ' + HydrusData.ToUnicode( new_urls_this_page ) + ' new urls'
                        
                        gallery_seed = ClientImportGallerySeeds.GallerySeed( gallery_url, can_generate_more_pages = False )
                        
                        gallery_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_NEW, note = status )
                        
                        gallery_seed_log = query.GetGallerySeedLog()
                        
                        gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
                        
                    except HydrusExceptions.CancelledException as e:
                        
                        self._DelayWork( 300, HydrusData.ToUnicode( e ) )
                        
                        break
                        
                    except HydrusExceptions.NotFoundException:
                        
                        # paheal now 404s when no results, so just naturally break
                        
                        break
                        
                    
                
            
            file_seeds_to_add_ordered.reverse()
            
            # 'first' urls are now at the end, so the file_seed_cache should stay roughly in oldest->newest order
            
            file_seed_cache.AddFileSeeds( file_seeds_to_add_ordered )
            
            query.RegisterSyncComplete()
            query.UpdateNextCheckTime( self._checker_options )
            
            if query.IsDead():
                
                if this_is_initial_sync:
                    
                    HydrusData.ShowText( 'The query "' + query_text + '" for subscription "' + self._name + '" did not find any files on its first sync! Could the query text have a typo, like a missing underscore?' )
                    
                else:
                    
                    HydrusData.ShowText( 'The query "' + query_text + '" for subscription "' + self._name + '" appears to be dead!' )
                    
                
            else:
                
                if this_is_initial_sync:
                    
                    if not self._QueryBandwidthIsOK( query ) and not have_made_an_initial_sync_bandwidth_notification:
                        
                        HydrusData.ShowText( 'FYI: The query "' + query_text + '" for subscription "' + self._name + '" performed its initial sync ok, but that domain is short on bandwidth right now, so no files will be downloaded yet. The subscription will catch up in future as bandwidth becomes available. You can review the estimated time until bandwidth is available under the manage subscriptions dialog. If more queries are performing initial syncs in this run, they may be the same.' )
                        
                        have_made_an_initial_sync_bandwidth_notification = True
                        
                    
                
            
        
    
    def _SyncQueryCanDoWork( self ):
        
        return True in ( query.CanSync() for query in self._queries )
        
    
    def CanCheckNow( self ):
        
        return True in ( query.CanCheckNow() for query in self._queries )
        
    
    def CanCompact( self ):
        
        return True in ( query.CanCompact( self._checker_options ) for query in self._queries )
        
    
    def CanReset( self ):
        
        return True in ( not query.IsInitialSync() for query in self._queries )
        
    
    def CanRetryFailures( self ):
        
        return True in ( query.CanRetryFailed() for query in self._queries )
        
    
    def CanRetryIgnored( self ):
        
        return True in ( query.CanRetryIgnored() for query in self._queries )
        
    
    def CanScrubDelay( self ):
        
        return not HydrusData.TimeHasPassed( self._no_work_until )
        
    
    def CheckNow( self ):
        
        for query in self._queries:
            
            query.CheckNow()
            
        
        self.ScrubDelay()
        
    
    def Compact( self ):
        
        for query in self._queries:
            
            query.Compact( self._checker_options )
            
        
    
    def GetBandwidthWaitingEstimate( self, query ):
        
        example_network_contexts = self._GetExampleNetworkContexts( query )
        
        estimate = HG.client_controller.network_engine.bandwidth_manager.GetWaitingEstimate( example_network_contexts )
        
        return estimate
        
    
    def GetBandwidthWaitingEstimateMinMax( self ):
        
        if len( self._queries ) == 0:
            
            return ( 0, 0 )
            
        
        estimates = []
        
        for query in self._queries:
            
            example_network_contexts = self._GetExampleNetworkContexts( query )
            
            estimate = HG.client_controller.network_engine.bandwidth_manager.GetWaitingEstimate( example_network_contexts )
            
            estimates.append( estimate )
            
        
        min_estimate = min( estimates )
        max_estimate = max( estimates )
        
        return ( min_estimate, max_estimate )
        
    
    def GetGalleryIdentifier( self ):
        
        return self._gallery_identifier
        
    
    def GetQueries( self ):
        
        return self._queries
        
    
    def GetPresentationOptions( self ):
        
        return ( self._publish_files_to_popup_button, self._publish_files_to_page, self._merge_query_publish_events )
        
    
    def GetTagImportOptions( self ):
        
        return self._tag_import_options
        
    
    def HasQuerySearchText( self, search_text ):
        
        for query in self._queries:
            
            query_text = query.GetQueryText()
            
            if search_text in query_text:
                
                return True
                
            
        
        return False
        
    
    def Merge( self, potential_mergee_subscriptions ):
        
        unmergable_subscriptions = []
        
        for subscription in potential_mergee_subscriptions:
            
            if subscription._gallery_identifier == self._gallery_identifier:
                
                my_new_queries = [ query.Duplicate() for query in subscription._queries ]
                
                self._queries.extend( my_new_queries )
                
            else:
                
                unmergable_subscriptions.append( subscription )
                
            
        
        return unmergable_subscriptions
        
    
    def PauseResume( self ):
        
        self._paused = not self._paused
        
    
    def Reset( self ):
        
        for query in self._queries:
            
            query.Reset()
            
        
        self.ScrubDelay()
        
    
    def RetryFailures( self ):
        
        for query in self._queries:
            
            query.RetryFailures()
            
        
    
    def RetryIgnored( self ):
        
        for query in self._queries:
            
            query.RetryIgnored()
            
        
    
    def ReviveDead( self ):
        
        for query in self._queries:
            
            if query.IsDead():
                
                query.CheckNow()
                
            
        
    
    def Separate( self, base_name, only_these_queries = None ):
        
        if only_these_queries is None:
            
            only_these_queries = set( self._queries )
            
        else:
            
            only_these_queries = set( only_these_queries )
            
        
        subscriptions = []
        
        for query in self._queries:
            
            if query not in only_these_queries:
                
                continue
                
            
            subscription = self.Duplicate()
            
            subscription._queries = [ query.Duplicate() ]
            
            subscription.SetName( base_name + ': ' + query.GetQueryText() )
            
            subscriptions.append( subscription )
            
        
        self._queries = [ query for query in self._queries if query not in only_these_queries ]
        
        return subscriptions
        
    
    def SetCheckerOptions( self, checker_options ):
        
        self._checker_options = checker_options
        
        for query in self._queries:
            
            query.UpdateNextCheckTime( self._checker_options )
            
        
    
    def SetPresentationOptions( self, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events ):
        
        self._publish_files_to_popup_button = publish_files_to_popup_button
        self._publish_files_to_page = publish_files_to_page
        self._merge_query_publish_events = merge_query_publish_events
        
    
    def SetTuple( self, gallery_identifier, gallery_stream_identifiers, queries, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, no_work_until ):
        
        self._gallery_identifier = gallery_identifier
        self._gallery_stream_identifiers = gallery_stream_identifiers
        self._queries = queries
        self._checker_options = checker_options
        self._initial_file_limit = initial_file_limit
        self._periodic_file_limit = periodic_file_limit
        self._paused = paused
        
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        
        self._no_work_until = no_work_until
        
    
    def ScrubDelay( self ):
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
    
    def Sync( self ):
        
        p1 = not self._paused
        p2 = not HG.view_shutdown
        p3 = self._NoDelays()
        p4 = self._SyncQueryCanDoWork()
        p5 = self._WorkOnFilesCanDoWork()
        
        if HG.subscription_report_mode:
            
            message = 'Subscription "' + self._name + '" entered sync.'
            message += os.linesep
            message += 'Unpaused: ' + str( p1 )
            message += os.linesep
            message += 'No delays: ' + str( p3 )
            message += os.linesep
            message += 'Sync can do work: ' + str( p4 )
            message += os.linesep
            message += 'Files can do work: ' + str( p5 )
            
            HydrusData.ShowText( message )
            
        
        if p1 and p2 and p3 and ( p4 or p5 ):
            
            job_key = ClientThreading.JobKey( pausable = False, cancellable = True )
            
            try:
                
                job_key.SetVariable( 'popup_title', 'subscriptions - ' + self._name )
                
                HG.client_controller.pub( 'message', job_key )
                
                self._SyncQuery( job_key )
                
                self._WorkOnFiles( job_key )
                
            except HydrusExceptions.NetworkException as e:
                
                if isinstance( e, HydrusExceptions.NetworkInfrastructureException ):
                    
                    delay = 3600
                    
                else:
                    
                    delay = HC.UPDATE_DURATION
                    
                
                HydrusData.Print( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.PrintException( e )
                
                job_key.SetVariable( 'popup_text_1', 'Encountered a network error, will retry again later' )
                
                self._DelayWork( delay, 'network error: ' + HydrusData.ToUnicode( e ) )
                
                time.sleep( 5 )
                
            except Exception as e:
                
                HydrusData.ShowText( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.ShowException( e )
                
                self._DelayWork( HC.UPDATE_DURATION, 'error: ' + HydrusData.ToUnicode( e ) )
                
            finally:
                
                job_key.DeleteVariable( 'popup_network_job' )
                
            
            HG.client_controller.WriteSynchronous( 'serialisable', self )
            
            if job_key.HasVariable( 'popup_files' ):
                
                job_key.Finish()
                
            else:
                
                job_key.Delete()
                
            
        
    
    def ToTuple( self ):
        
        return ( self._name, self._gallery_identifier, self._gallery_stream_identifiers, self._queries, self._checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, self._file_import_options, self._tag_import_options, self._no_work_until, self._no_work_until_reason )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ] = Subscription

class SubscriptionQuery( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY
    SERIALISABLE_NAME = 'Subscription Query'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, query = 'query text' ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._query = query
        self._check_now = False
        self._last_check_time = 0
        self._next_check_time = 0
        self._paused = False
        self._status = CHECKER_STATUS_OK
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        
        return ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_gallery_seed_log, serialisable_file_seed_cache )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_gallery_seed_log, serialisable_file_seed_cache ) = serialisable_info
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_file_seed_cache ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
    
    def CanWorkOnFiles( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._query + '" CanWorkOnFiles test. Next import is ' + repr( file_seed ) + '.' )
            
        
        return file_seed is not None
        
    
    def CanCheckNow( self ):
        
        return not self._check_now
        
    
    def CanCompact( self, checker_options ):
        
        death_period = checker_options.GetDeathFileVelocityPeriod()
        
        compact_before_this_source_time = self._last_check_time - ( death_period * 2 )
        
        return self._file_seed_cache.CanCompact( compact_before_this_source_time )
        
    
    def CanRetryFailed( self ):
        
        return self._file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR ) > 0
        
    
    def CanRetryIgnored( self ):
        
        return self._file_seed_cache.GetFileSeedCount( CC.STATUS_VETOED ) > 0
        
    
    def CanSync( self ):
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._query + '" CanSync test. Paused status is ' + str( self._paused ) + ' and check time due is ' + str( HydrusData.TimeHasPassed( self._next_check_time ) ) + ' and check_now is ' + str( self._check_now ) + '.' )
            
        
        if self._paused:
            
            return False
            
        
        return HydrusData.TimeHasPassed( self._next_check_time ) or self._check_now
        
    
    def CheckNow( self ):
        
        self._check_now = True
        self._paused = False
        
        self._next_check_time = 0
        self._status = CHECKER_STATUS_OK
        
    
    def Compact( self, checker_options ):
        
        death_period = checker_options.GetDeathFileVelocityPeriod()
        
        compact_before_this_time = self._last_check_time - ( death_period * 2 )
        
        return self._file_seed_cache.Compact( compact_before_this_time )
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def GetLastChecked( self ):
        
        return self._last_check_time
        
    
    def GetLatestAddedTime( self ):
        
        return self._file_seed_cache.GetLatestAddedTime()
        
    
    def GetNextCheckStatusString( self ):
        
        if self._check_now:
            
            return 'checking on dialog ok'
            
        elif self._status == CHECKER_STATUS_DEAD:
            
            return 'dead, so not checking'
            
        else:
            
            if HydrusData.TimeHasPassed( self._next_check_time ):
                
                s = 'imminent'
                
            else:
                
                s = HydrusData.TimestampToPrettyTimeDelta( self._next_check_time )
                
            
            if self._paused:
                
                s = 'paused, but would be ' + s
                
            
            return s
            
        
    
    def GetNumURLsAndFailed( self ):
        
        return ( self._file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN ), len( self._file_seed_cache ), self._file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR ) )
        
    
    def GetQueryText( self ):
        
        return self._query
        
    
    def IsDead( self ):
        
        return self._status == CHECKER_STATUS_DEAD
        
    
    def IsInitialSync( self ):
        
        return self._last_check_time == 0
        
    
    def IsPaused( self ):
        
        return self._paused
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def RegisterSyncComplete( self ):
        
        self._last_check_time = HydrusData.GetNow()
        
        self._check_now = False
        
    
    def Reset( self ):
        
        self._last_check_time = 0
        self._next_check_time = 0
        self._status = CHECKER_STATUS_OK
        self._paused = False
        
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
    
    def RetryFailures( self ):
        
        self._file_seed_cache.RetryFailures()    
        
    
    def RetryIgnored( self ):
        
        self._file_seed_cache.RetryIgnored()    
        
    
    def SetCheckNow( self, check_now ):
        
        self._check_now = check_now
        
    
    def SetPaused( self, paused ):
        
        self._paused = paused
        
    
    def SetQueryAndSeeds( self, query, file_seed_cache, gallery_seed_log ):
        
        self._query = query
        self._file_seed_cache = file_seed_cache
        self._gallery_seed_log = gallery_seed_log
        
    
    def UpdateNextCheckTime( self, checker_options ):
        
        if self._check_now:
            
            self._next_check_time = 0
            
            self._status = CHECKER_STATUS_OK
            
        else:
            
            if checker_options.IsDead( self._file_seed_cache, self._last_check_time ):
                
                self._status = CHECKER_STATUS_DEAD
                
                self._paused = True
                
            
            last_next_check_time = self._next_check_time
            
            self._next_check_time = checker_options.GetNextCheckTime( self._file_seed_cache, self._last_check_time, last_next_check_time )
            
        
    
    def ToTuple( self ):
        
        return ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY ] = SubscriptionQuery

class URLsImport( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT
    SERIALISABLE_NAME = 'URL Import'
    SERIALISABLE_VERSION = 2
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        self._file_import_options = file_import_options
        self._paused = False
        
        self._download_control_file_set = None
        self._download_control_file_clear = None
        
        self._lock = threading.Lock()
        
        self._files_repeating_job = None
        
        HG.client_controller.sub( self, 'NotifyFileSeedsUpdated', 'file_seed_cache_file_seeds_updated' )
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_file_options = self._file_import_options.GetSerialisableTuple()
        
        return ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_options, self._paused )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_options, self._paused ) = serialisable_info
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_options )
        
    
    def _NetworkJobPresentationContextFactory( self, network_job ):
        
        def enter_call():
            
            with self._lock:
                
                if self._download_control_file_set is not None:
                    
                    wx.CallAfter( self._download_control_file_set, network_job )
                    
                
            
        
        def exit_call():
            
            with self._lock:
                
                if self._download_control_file_clear is not None:
                    
                    wx.CallAfter( self._download_control_file_clear )
                    
                
            
        
        return NetworkJobPresentationContext( enter_call, exit_call )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_file_seed_cache, serialisable_file_options, paused ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_file_options, paused )
            
            return ( 2, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, page_key ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return
            
        
        did_substantial_work = False
        
        url = file_seed.file_seed_data
        
        try:
            
            ( url_type, match_name, can_parse ) = HG.client_controller.network_engine.domain_manager.GetURLParseCapability( url )
            
            if url_type in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE ) and not can_parse:
                
                # here is where we will _in some way_ add this to the gallery log, which will have to be actioned itself in some way m8
                # or maybe the url should be assigned there as soon as it is entered, and this whole importer should have workongalleryurls?
                # think about this
                
                message = 'This URL was recognised as a "' + match_name + '" but this URL class does not yet have a parsing script linked to it!'
                message += os.linesep * 2
                message += 'Since this URL cannot be parsed, a downloader cannot be created for it! Please check your url class links under the \'networking\' menu.'
                
                raise HydrusExceptions.ParseException( message )
                
            
            status_hook = lambda s: s # do nothing for now
            
            if url_type in ( HC.URL_TYPE_POST, HC.URL_TYPE_FILE, HC.URL_TYPE_UNKNOWN ):
                
                tag_import_options = HG.client_controller.network_engine.domain_manager.GetDefaultTagImportOptionsForURL( url )
                
                did_substantial_work = file_seed.WorkOnURL( self._file_seed_cache, status_hook, GenerateDownloaderNetworkJobFactory( page_key ), self._NetworkJobPresentationContextFactory, self._file_import_options, tag_import_options )
                
                if file_seed.ShouldPresent( self._file_import_options ):
                    
                    file_seed.PresentToPage( page_key )
                    
                    did_substantial_work = True
                    
                
            elif url_type in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE ):
                
                raise NotImplementedError( 'Unfortunately, galleries and watchable urls do not work here yet!' )
                
            
        except Exception as e:
            
            status = CC.STATUS_ERROR
            
            file_seed.SetStatus( status, exception = e )
            
            time.sleep( 3 )
            
        finally:
            
            self._file_seed_cache.NotifyFileSeedsUpdated( ( file_seed, ) )
            
        
        if did_substantial_work:
            
            time.sleep( DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
            
        
    
    def CurrentlyWorking( self ):
        
        with self._lock:
            
            finished = not self._file_seed_cache.WorkToDo()
            
            return not finished and not self._paused
            
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def GetOptions( self ):
        
        with self._lock:
            
            return self._file_import_options
            
        
    
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
            
            WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PausePlay( self ):
        
        with self._lock:
            
            self._paused = not self._paused
            
            WakeRepeatingJob( self._files_repeating_job )
            
        
    
    def PendURLs( self, urls ):
        
        with self._lock:
            
            urls = filter( lambda u: len( u ) > 1, urls ) # > _1_ to take out the occasional whitespace
            
            file_seeds = [ ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url ) for url in urls ]
            
            if len( file_seeds ) > 0:
                
                self._file_seed_cache.AddFileSeeds( file_seeds )
                
                WakeRepeatingJob( self._files_repeating_job )
                
            
        
    
    def SetDownloadControlFile( self, download_control ):
        
        with self._lock:
            
            self._download_control_file_set = download_control.SetNetworkJob
            self._download_control_file_clear = download_control.ClearNetworkJob
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        with self._lock:
            
            self._file_import_options = file_import_options
            
        
    
    def Start( self, page_key ):
        
        self._files_repeating_job = HG.client_controller.CallRepeating( GetRepeatingJobInitialDelay(), REPEATING_JOB_TYPICAL_PERIOD, self.REPEATINGWorkOnFiles, page_key )
        
    
    def REPEATINGWorkOnFiles( self, page_key ):
        
        with self._lock:
            
            if PageImporterShouldStopWorking( page_key ):
                
                self._files_repeating_job.Cancel()
                
                return
                
            
            work_to_do = self._file_seed_cache.WorkToDo() and not ( self._paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
            
        
        while work_to_do:
            
            try:
                
                self._WorkOnFiles( page_key )
                
                HG.client_controller.WaitUntilViewFree()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
            with self._lock:
                
                if PageImporterShouldStopWorking( page_key ):
                    
                    self._files_repeating_job.Cancel()
                    
                    return
                    
                
                work_to_do = self._file_seed_cache.WorkToDo() and not ( self._paused or HG.client_controller.PageClosedButNotDestroyed( page_key ) )
                
            
        
    
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_URLS_IMPORT ] = URLsImport
