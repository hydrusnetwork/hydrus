import ClientConstants as CC
import ClientDownloading
import ClientImporting
import ClientImportFileSeeds
import ClientImportGallerySeeds
import ClientImportOptions
import ClientNetworkingContexts
import ClientNetworkingJobs
import ClientPaths
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusPaths
import HydrusSerialisable
import os
import random
import time

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_NAME = 'Subscription'
    SERIALISABLE_VERSION = 7
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._gallery_identifier = ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_DEVIANT_ART )
        
        self._gallery_stream_identifiers = ClientDownloading.GetGalleryStreamIdentifiers( self._gallery_identifier )
        
        self._queries = []
        
        new_options = HG.client_controller.new_options
        
        self._checker_options = HG.client_controller.new_options.GetDefaultSubscriptionCheckerOptions()
        
        if HC.options[ 'gallery_file_limit' ] is None:
            
            self._initial_file_limit = 100
            
        else:
            
            self._initial_file_limit = min( 100, HC.options[ 'gallery_file_limit' ] )
            
        
        self._periodic_file_limit = 100
        self._paused = False
        
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'quiet' )
        
        new_options = HG.client_controller.new_options
        
        self._tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
        
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
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_import_options, serialisable_tag_import_options, self._no_work_until, self._no_work_until_reason, self._publish_files_to_popup_button, self._publish_files_to_page, self._merge_query_publish_events )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_import_options, serialisable_tag_import_options, self._no_work_until, self._no_work_until_reason, self._publish_files_to_popup_button, self._publish_files_to_page, self._merge_query_publish_events ) = serialisable_info
        
        self._gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
        self._gallery_stream_identifiers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_stream_identifier ) for serialisable_gallery_stream_identifier in serialisable_gallery_stream_identifiers ]
        self._queries = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_query ) for serialisable_query in serialisable_queries ]
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _GenerateNetworkJobFactory( self, query ):
        
        subscription_key = self._GetNetworkJobSubscriptionKey( query )
        
        def network_job_factory( *args, **kwargs ):
            
            network_job = ClientNetworkingJobs.NetworkJobSubscription( subscription_key, *args, **kwargs )
            
            network_job.OverrideBandwidth( 30 )
            
            return network_job
            
        
        return network_job_factory
        
    
    def _NoDelays( self ):
        
        return HydrusData.TimeHasPassed( self._no_work_until )
        
    
    def _QueryBandwidthIsOK( self, query ):
        
        example_network_contexts = self._GetExampleNetworkContexts( query )
        
        threshold = 90
        
        result = HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_network_contexts, threshold = threshold )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + query.GetQueryText() + '" pre-work bandwidth test. Bandwidth ok: ' + str( result ) + '.' )
            
        
        return result
        
    
    def _ShowHitPeriodicFileLimitMessage( self, query_text ):
        
        message = 'The query "' + query_text + '" for subscription "' + self._name + '" hit its periodic file limit.'
        
        HydrusData.ShowText( message )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, last_error, serialisable_file_seed_cache ) = old_serialisable_info
            
            check_now = False
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, check_now, last_error, serialisable_file_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, check_now, last_error, serialisable_file_seed_cache ) = old_serialisable_info
            
            no_work_until = 0
            no_work_until_reason = ''
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, check_now, last_error, no_work_until, no_work_until_reason, serialisable_file_seed_cache )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, check_now, last_error, no_work_until, no_work_until_reason, serialisable_file_seed_cache ) = old_serialisable_info
            
            checker_options = ClientImportOptions.CheckerOptions( 5, period / 5, period * 10, ( 1, period * 10 ) )
            
            file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
            
            query = SubscriptionQuery( query )
            
            query._file_seed_cache = file_seed_cache
            query._last_check_time = last_checked
            
            query.UpdateNextCheckTime( checker_options )
            
            queries = [ query ]
            
            serialisable_queries = [ query.GetSerialisableTuple() for query in queries ]
            serialisable_checker_options = checker_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason ) = old_serialisable_info
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason ) = old_serialisable_info
            
            publish_files_to_popup_button = True
            publish_files_to_page = False
            merge_query_publish_events = True
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events ) = old_serialisable_info
            
            if initial_file_limit is None or initial_file_limit > 1000:
                
                initial_file_limit = 1000
                
            
            if periodic_file_limit is None or periodic_file_limit > 1000:
                
                periodic_file_limit = 1000
                
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events )
            
            return ( 7, new_serialisable_info )
            
        
    
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
                            
                            
                        
                        file_seed.WorkOnURL( file_seed_cache, status_hook, self._GenerateNetworkJobFactory( query ), ClientImporting.GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key ), self._file_import_options, self._tag_import_options )
                        
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
                    
                
                time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
                
                HG.client_controller.WaitUntilViewFree()
                
            
            if not self._merge_query_publish_events and len( presentation_hashes ) > 0:
                
                ClientImporting.PublishPresentationHashes( query_summary_name, presentation_hashes, self._publish_files_to_popup_button, self._publish_files_to_page )
                
            
        
        if self._merge_query_publish_events and len( all_presentation_hashes ) > 0:
            
            ClientImporting.PublishPresentationHashes( self._name, all_presentation_hashes, self._publish_files_to_popup_button, self._publish_files_to_page )
            
        
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
            gallery_seed_log = query.GetGallerySeedLog()
            
            this_is_initial_sync = query.IsInitialSync()
            total_new_urls_for_this_sync = 0
            
            gallery_urls_seen_this_sync = set()
            
            if this_is_initial_sync:
                
                file_limit_for_this_sync = self._initial_file_limit
                
            else:
                
                file_limit_for_this_sync = self._periodic_file_limit
                
            
            file_seeds_to_add = set()
            file_seeds_to_add_ordered = []
            
            prefix = 'synchronising'
            
            if query_text != self._name:
                
                prefix += ' "' + query_text + '"'
                
            
            job_key.SetVariable( 'popup_text_1', prefix )
            
            for gallery_stream_identifier in self._gallery_stream_identifiers:
                
                if file_limit_for_this_sync is not None and total_new_urls_for_this_sync >= file_limit_for_this_sync:
                    
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
                    
                
                first_gallery_url = gallery.GetGalleryPageURL( query_text, 0 )
                
                gallery_seed = ClientImportGallerySeeds.GallerySeed( first_gallery_url, can_generate_more_pages = True )
                
                if gallery_seed.WorksInNewSystem():
                    
                    def status_hook( text ):
                        
                        job_key.SetVariable( 'popup_text_1', prefix + ': ' + text )
                        
                    
                    def title_hook( text ):
                        
                        pass
                        
                    
                    gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
                    
                    num_existing_urls_this_stream = 0
                    
                    stop_reason = 'unknown stop reason'
                    
                    keep_checking = True
                    
                    try:
                        
                        while keep_checking and gallery_seed_log.WorkToDo():
                            
                            p1 = HC.options[ 'pause_subs_sync' ]
                            p2 = HG.view_shutdown
                            
                            if p1 or p2:
                                
                                return
                                
                            
                            if job_key.IsCancelled():
                                
                                stop_reason = 'gallery parsing cancelled, likely by user'
                                
                                self._DelayWork( 600, stop_reason )
                                
                                return
                                
                            
                            gallery_seed = gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
                            
                            if gallery_seed is None:
                                
                                stop_reason = 'thought there was a page to check, but apparently there was not!'
                                
                                break
                                
                            
                            job_key.SetVariable( 'popup_text_1', prefix + ': found ' + HydrusData.ToHumanInt( total_new_urls_for_this_sync ) + ' new urls, checking next page' )
                            
                            def file_seeds_callable( file_seeds ):
                                
                                num_urls_added = 0
                                num_urls_already_in_file_seed_cache = 0
                                can_add_more_file_urls = True
                                stop_reason = 'no known stop reason'
                                
                                for file_seed in file_seeds:
                                    
                                    if file_limit_for_this_sync is not None and total_new_urls_for_this_sync + num_urls_added >= file_limit_for_this_sync:
                                        
                                        if this_is_initial_sync:
                                            
                                            stop_reason = 'hit initial file limit'
                                            
                                        else:
                                            
                                            self._ShowHitPeriodicFileLimitMessage( query_text )
                                            
                                            stop_reason = 'hit periodic file limit'
                                            
                                        
                                        can_add_more_file_urls = False
                                        
                                        break
                                        
                                    
                                    if file_seed in file_seeds_to_add:
                                        
                                        # this catches the occasional overflow when a new file is uploaded while gallery parsing is going on
                                        
                                        continue
                                        
                                    
                                    if file_seed_cache.HasFileSeed( file_seed ):
                                        
                                        num_urls_already_in_file_seed_cache += 1
                                        
                                        WE_HIT_OLD_GROUND_THRESHOLD = 5
                                        
                                        if num_urls_already_in_file_seed_cache >= WE_HIT_OLD_GROUND_THRESHOLD:
                                            
                                            can_add_more_file_urls = False
                                            
                                            stop_reason = 'saw ' + HydrusData.ToHumanInt( WE_HIT_OLD_GROUND_THRESHOLD ) + ' previously seen urls, so assuming we caught up'
                                            
                                            break
                                            
                                        
                                    else:
                                        
                                        num_urls_added += 1
                                        
                                        file_seeds_to_add.add( file_seed )
                                        file_seeds_to_add_ordered.append( file_seed )
                                        
                                    
                                
                                return ( num_urls_added, num_urls_already_in_file_seed_cache, can_add_more_file_urls, stop_reason )
                                
                            
                            try:
                                
                                ( num_urls_added, num_urls_already_in_file_seed_cache, num_urls_total, result_404, can_add_more_file_urls, stop_reason ) = gallery_seed.WorkOnURL( 'subscription', gallery_seed_log, file_seeds_callable, status_hook, title_hook, self._GenerateNetworkJobFactory( query ), ClientImporting.GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key ), self._file_import_options, gallery_urls_seen_before = gallery_urls_seen_this_sync )
                                
                            except HydrusExceptions.CancelledException as e:
                                
                                stop_reason = 'gallery network job cancelled, likely by user'
                                
                                self._DelayWork( 600, stop_reason )
                                
                                return
                                
                            except Exception as e:
                                
                                stop_reason = HydrusData.ToUnicode( e )
                                
                                raise
                                
                            finally:
                                
                                done_first_page = True
                                
                            
                            keep_checking = can_add_more_file_urls
                            
                            num_existing_urls_this_stream += num_urls_already_in_file_seed_cache
                            
                            WE_HIT_OLD_GROUND_TOTAL_THRESHOLD = 15
                            
                            if num_existing_urls_this_stream >= WE_HIT_OLD_GROUND_TOTAL_THRESHOLD:
                                
                                keep_checking = False
                                stop_reason = 'saw ' + HydrusData.ToHumanInt( WE_HIT_OLD_GROUND_TOTAL_THRESHOLD ) + ' previously seen urls in the whole sync, so assuming we caught up'
                                
                            
                            total_new_urls_for_this_sync += num_urls_added
                            
                        
                    finally:
                        
                        while gallery_seed_log.WorkToDo():
                            
                            gallery_seed = gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
                            
                            if gallery_seed is None:
                                
                                break
                                
                            
                            gallery_seed.SetStatus( CC.STATUS_VETOED, note = stop_reason )
                            
                        
                    
                else:
                    
                    def network_job_factory( method, url, **kwargs ):
                        
                        network_job = ClientNetworkingJobs.NetworkJobSubscription( self._GetNetworkJobSubscriptionKey( query ), method, url, **kwargs )
                        
                        job_key.SetVariable( 'popup_network_job', network_job )
                        
                        network_job.SetGalleryToken( 'subscription' )
                        
                        network_job.OverrideBandwidth( 30 )
                        
                        return network_job
                        
                    
                    gallery.SetNetworkJobFactory( network_job_factory )
                    
                    page_index = 0
                    num_existing_urls_this_stream = 0
                    keep_checking = True
                    
                    while keep_checking:
                        
                        new_urls_this_page = 0
                        
                        p1 = HC.options[ 'pause_subs_sync' ]
                        p2 = HG.view_shutdown
                        
                        if p1 or p2:
                            
                            return
                            
                        
                        if job_key.IsCancelled():
                            
                            raise HydrusExceptions.CancelledException( 'gallery parsing cancelled, likely by user' )
                            
                        
                        job_key.SetVariable( 'popup_text_1', prefix + ': found ' + HydrusData.ToHumanInt( total_new_urls_for_this_sync ) + ' new urls, checking next page' )
                        
                        gallery_url = gallery.GetGalleryPageURL( query_text, page_index )
                        
                        try:
                            
                            gallery_seed = ClientImportGallerySeeds.GallerySeed( gallery_url, can_generate_more_pages = False )
                            
                            gallery_seed_log.AddGallerySeeds( ( gallery_seed, ) )
                            
                            ( page_of_file_seeds, definitely_no_more_pages ) = gallery.GetPage( gallery_url )
                            
                            done_first_page = True
                            
                            page_index += 1
                            
                            if definitely_no_more_pages:
                                
                                keep_checking = False
                                
                            
                            for file_seed in page_of_file_seeds:
                                
                                if file_limit_for_this_sync is not None and total_new_urls_for_this_sync >= file_limit_for_this_sync:
                                    
                                    if not this_is_initial_sync:
                                        
                                        self._ShowHitPeriodicFileLimitMessage( query_text )
                                        
                                    
                                    keep_checking = False
                                    
                                    break
                                    
                                
                                if file_seed in file_seeds_to_add:
                                    
                                    # this catches the occasional overflow when a new file is uploaded while gallery parsing is going on
                                    
                                    continue
                                    
                                
                                if file_seed_cache.HasFileSeed( file_seed ):
                                    
                                    num_existing_urls_this_stream += 1
                                    
                                    if num_existing_urls_this_stream > 5:
                                        
                                        keep_checking = False
                                        
                                        break
                                        
                                    
                                else:
                                    
                                    file_seeds_to_add.add( file_seed )
                                    file_seeds_to_add_ordered.append( file_seed )
                                    
                                    new_urls_this_page += 1
                                    total_new_urls_for_this_sync += 1
                                    
                                
                            
                            if new_urls_this_page == 0:
                                
                                keep_checking = False
                                
                            
                            gallery_seed_status = CC.STATUS_SUCCESSFUL_AND_NEW
                            gallery_seed_note = 'checked OK - found ' + HydrusData.ToUnicode( new_urls_this_page ) + ' new urls'
                            
                        except HydrusExceptions.CancelledException as e:
                            
                            gallery_seed_status = CC.STATUS_VETOED
                            gallery_seed_note = HydrusData.ToUnicode( e )
                            
                            self._DelayWork( 600, gallery_seed_note )
                            
                            return
                            
                        except HydrusExceptions.NotFoundException:
                            
                            gallery_seed_status = CC.STATUS_VETOED
                            gallery_seed_note = '404'
                            
                            # paheal now 404s when no results, so just naturally break
                            
                            break
                            
                        except Exception as e:
                            
                            gallery_seed_status = CC.STATUS_ERROR
                            gallery_seed_note = HydrusData.ToUnicode( e )
                            
                            raise
                            
                        finally:
                            
                            gallery_seed.SetStatus( gallery_seed_status, note = gallery_seed_note )
                            
                            gallery_seed_log.NotifyGallerySeedsUpdated( ( gallery_seed, ) )
                            
                        
                    
                
            
            file_seeds_to_add_ordered.reverse()
            
            # 'first' urls are now at the end, so the file_seed_cache should stay roughly in oldest->newest order
            
            file_seed_cache.AddFileSeeds( file_seeds_to_add_ordered )
            
            query.RegisterSyncComplete()
            query.UpdateNextCheckTime( self._checker_options )
            
            if query.CanCompact( self._checker_options ):
                
                query.Compact( self._checker_options )
                
            
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
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options.Duplicate()
        
    
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
        self._status = ClientImporting.CHECKER_STATUS_OK
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
        
        return self._file_seed_cache.CanCompact( compact_before_this_source_time ) or self._gallery_seed_log.CanCompact( compact_before_this_source_time )
        
    
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
        self._status = ClientImporting.CHECKER_STATUS_OK
        
    
    def Compact( self, checker_options ):
        
        death_period = checker_options.GetDeathFileVelocityPeriod()
        
        compact_before_this_time = self._last_check_time - ( death_period * 2 )
        
        self._file_seed_cache.Compact( compact_before_this_time )
        self._gallery_seed_log.Compact( compact_before_this_time )
        
    
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
            
        elif self._status == ClientImporting.CHECKER_STATUS_DEAD:
            
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
        
        return self._status == ClientImporting.CHECKER_STATUS_DEAD
        
    
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
        self._status = ClientImporting.CHECKER_STATUS_OK
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
            
            self._status = ClientImporting.CHECKER_STATUS_OK
            
        else:
            
            if checker_options.IsDead( self._file_seed_cache, self._last_check_time ):
                
                self._status = ClientImporting.CHECKER_STATUS_DEAD
                
                self._paused = True
                
            
            last_next_check_time = self._next_check_time
            
            self._next_check_time = checker_options.GetNextCheckTime( self._file_seed_cache, self._last_check_time, last_next_check_time )
            
        
    
    def ToTuple( self ):
        
        return ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY ] = SubscriptionQuery
