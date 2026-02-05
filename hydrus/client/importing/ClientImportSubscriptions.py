import collections.abc
import random
import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing import ClientImportSubscriptionQuery
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import TagImportOptionsLegacy
from hydrus.client.networking import ClientNetworkingBandwidth
from hydrus.client.networking import ClientNetworkingGUG

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_NAME = 'Subscription'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, name, gug_key_and_name = None ):
        
        super().__init__( name )
        
        if gug_key_and_name is None:
            
            gug_key_and_name = ( HydrusData.GenerateKey(), 'unknown source' )
            
        
        self._gug_key_and_name = gug_key_and_name
        
        self._query_headers: list[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] = []
        
        new_options = CG.client_controller.new_options
        
        self._checker_options = new_options.GetDefaultSubscriptionCheckerOptions()
        
        if HC.options[ 'gallery_file_limit' ] is None:
            
            self._initial_file_limit = 100
            
        else:
            
            self._initial_file_limit = min( 100, HC.options[ 'gallery_file_limit' ] )
            
        
        self._periodic_file_limit = 100
        
        self._this_is_a_random_sample_sub = False
        
        self._paused = False
        
        self._file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        self._file_import_options.SetIsDefault( True )
        
        self._tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
        
        self._note_import_options = NoteImportOptions.NoteImportOptions()
        self._note_import_options.SetIsDefault( True )
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        self._show_a_popup_while_working = True
        self._publish_files_to_popup_button = True
        self._publish_files_to_page = False
        self._publish_label_override = None
        self._merge_query_publish_events = True
        
        self._have_made_an_initial_sync_bandwidth_notification = False
        self._file_error_count = 0
        
        self._stop_work_for_shutdown = False
        
    
    def _CanDoWorkNow( self ):
        
        p1 = not ( self._paused or CG.client_controller.new_options.GetBoolean( 'pause_subs_sync' ) or CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ) or CG.client_controller.subscriptions_manager.SubscriptionsArePausedForEditing() )
        p2 = not ( HG.started_shutdown or self._stop_work_for_shutdown )
        p3 = self._NoDelays()
        
        if HG.subscription_report_mode:
            
            message = 'Subscription "{}" CanDoWork check.'.format( self._name )
            message += '\n'
            message += 'Paused/Global/Network/Dialog Pause: {}/{}/{}/{}'.format( self._paused, CG.client_controller.new_options.GetBoolean( 'pause_subs_sync' ), CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ), CG.client_controller.subscriptions_manager.SubscriptionsArePausedForEditing() )
            message += '\n'
            message += 'Started/Sub shutdown: {}/{}'.format( HG.started_shutdown, self._stop_work_for_shutdown )
            message += '\n'
            message += 'No delays: {}'.format( self._NoDelays() )
            
            HydrusData.ShowText( message )
            
        
        return p1 and p2 and p3
        
    
    def _DealWithMissingQueryLogContainerError( self, query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader ):
        
        query_header.SetQueryLogContainerStatus( ClientImportSubscriptionQuery.LOG_CONTAINER_MISSING )
        
        self._paused = True
        
        HydrusData.ShowText( 'The subscription "{}"\'s "{}" query was missing database data! This could be a serious error! Please go to _manage subscriptions_ to reset the data, and you may want to contact hydrus dev. The sub has paused!'.format( self._name, query_header.GetHumanName() ) )
        
    
    def _DelayWork( self, time_delta, reason ):
        
        reason = HydrusText.GetFirstLine( reason )
        
        self._no_work_until = HydrusTime.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _GetPublishingLabel( self, query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader ):
        
        if self._publish_label_override is None:
            
            label = self._name
            
        else:
            
            label = self._publish_label_override
            
        
        if not self._merge_query_publish_events:
            
            label += ': ' + query_header.GetHumanName()
            
        
        return label
        
    
    def _GetQueryHeadersForProcessing( self ) -> list[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ]:
        
        query_headers = list( self._query_headers )
        
        if CG.client_controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
            
            random.shuffle( query_headers )
            
        else:
            
            def key( q ):
                
                return q.GetHumanName()
                
            
            query_headers.sort( key = key )
            
        
        return query_headers
        
    
    def _GetSerialisableInfo( self ):
        
        ( gug_key, gug_name ) = self._gug_key_and_name
        
        serialisable_gug_key_and_name = ( gug_key.hex(), gug_name )
        serialisable_query_headers = [ query_header.GetSerialisableTuple() for query_header in self._query_headers ]
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        serialisable_note_import_options = self._note_import_options.GetSerialisableTuple()
        
        return (
            serialisable_gug_key_and_name,
            serialisable_query_headers,
            serialisable_checker_options,
            self._initial_file_limit,
            self._periodic_file_limit,
            self._this_is_a_random_sample_sub,
            self._paused,
            serialisable_file_import_options,
            serialisable_tag_import_options,
            serialisable_note_import_options,
            self._no_work_until,
            self._no_work_until_reason,
            self._show_a_popup_while_working,
            self._publish_files_to_popup_button,
            self._publish_files_to_page,
            self._publish_label_override,
            self._merge_query_publish_events
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            serialisable_gug_key_and_name,
            serialisable_query_headers,
            serialisable_checker_options,
            self._initial_file_limit,
            self._periodic_file_limit,
            self._this_is_a_random_sample_sub,
            self._paused,
            serialisable_file_import_options,
            serialisable_tag_import_options,
            serialisable_note_import_options,
            self._no_work_until,
            self._no_work_until_reason,
            self._show_a_popup_while_working,
            self._publish_files_to_popup_button,
            self._publish_files_to_page,
            self._publish_label_override,
            self._merge_query_publish_events
            ) = serialisable_info
        
        ( serialisable_gug_key, gug_name ) = serialisable_gug_key_and_name
        
        self._gug_key_and_name = ( bytes.fromhex( serialisable_gug_key ), gug_name )
        self._query_headers = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_query ) for serialisable_query in serialisable_query_headers ]
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        self._note_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_note_import_options )
        
    
    def _NoDelays( self ):
        
        return HydrusTime.TimeHasPassed( self._no_work_until )
        
    
    def _ShowHitPeriodicFileLimitMessage( self, query_name: int, query_text: int, file_limit: int ):
        
        message = 'The query "{}" for subscription "{}" found {} new URLs without running into any it had seen before.'.format( query_name, self._name, file_limit )
        message += '\n\n'
        message += 'It is likely that a user probably uploaded a lot of files to that query in a short period, in which case there is now a gap in your subscription that you may wish to fill.'
        message += '\n\n'
        message += 'If you get many of these messages, one for every subscription query for the site, and the gap downloaders find no new files, then the site has changed URL format in a subtle way and the subscription checker was unable to recognise it (in which case, if the subscription appears to be working, you can ignore any more of these messages).'
        
        call = HydrusData.Call( CG.client_controller.pub, 'make_new_subscription_gap_downloader', self._gug_key_and_name, query_text, self._file_import_options.Duplicate(), self._tag_import_options.Duplicate(), self._note_import_options, file_limit * 5 )
        
        call.SetLabel( 'start a new downloader for this to fill in the gap!' )
        
        job_status = ClientThreading.JobStatus()
        
        job_status.SetStatusText( message )
        job_status.SetUserCallable( call )
        
        CG.client_controller.pub( 'message', job_status )
        
    
    def _SyncQueries( self, job_status: ClientThreading.JobStatus ):
        
        self._have_made_an_initial_sync_bandwidth_notification = False
        
        gug = CG.client_controller.network_engine.domain_manager.GetGUG( self._gug_key_and_name )
        
        if gug is None:
            
            self._paused = True
            
            HydrusData.ShowText( 'The subscription "{}" could not find a Gallery URL Generator for "{}"! The sub has paused!'.format( self._name, self._gug_key_and_name[1] ) )
            
            return
            
        
        try:
            
            gug.CheckFunctional()
            
        except HydrusExceptions.ParseException as e:
            
            self._paused = True
            
            message = 'The subscription "{}"\'s Gallery URL Generator, "{}" seems not to be functional! The sub has paused! The given reason was:'.format( self._name, self._gug_key_and_name[1] )
            message += '\n' * 2
            message += str( e )
            
            HydrusData.ShowText( message )
            
            return
            
        
        self._gug_key_and_name = gug.GetGUGKeyAndName() # just a refresher, to keep up with any changes
        
        query_headers = self._GetQueryHeadersForProcessing()
        
        query_headers = [ query_header for query_header in query_headers if query_header.IsSyncDue() ]
        
        num_queries = len( query_headers )
        
        for ( i, query_header ) in enumerate( query_headers ):
            
            status_prefix = f'synchronising ({HydrusNumbers.ValueRangeToPrettyString( i, num_queries )})'
            
            query_name = query_header.GetHumanName()
            
            if query_name != self._name:
                
                status_prefix += ' "' + query_name + '"'
                
            
            job_status.SetGauge( i, num_queries )
            
            try:
                
                query_log_container = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, query_header.GetQueryLogContainerName() )
                
            except HydrusExceptions.DBException as e:
                
                if isinstance( e.db_e, HydrusExceptions.DataMissing ):
                    
                    self._DealWithMissingQueryLogContainerError( query_header )
                    
                    break
                    
                else:
                    
                    raise
                    
                
            
            try:
                
                self._SyncQuery( job_status, gug, query_header, query_log_container, status_prefix )
                
            except HydrusExceptions.CancelledException:
                
                break
                
            finally:
                
                CG.client_controller.WriteSynchronous( 'serialisable', query_log_container )
                
            
        
    
    def _SyncQueriesCanDoWork( self ):
        
        result = True in ( query_header.IsSyncDue() for query_header in self._query_headers )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "{}" checking if any sync work due: {}'.format( self._name, result ) )
            
        
        return result
        
    
    def _SyncQuery(
        self,
        job_status: ClientThreading.JobStatus,
        gug: ClientNetworkingGUG.GalleryURLGenerator, # not actually correct for an ngug, but _whatever_
        query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader,
        query_log_container: ClientImportSubscriptionQuery.SubscriptionQueryLogContainer,
        status_prefix: str
        ):
        
        query_text = query_header.GetQueryText()
        query_name = query_header.GetHumanName()
        
        gallery_url_classes_to_special_stop_reasons = dict()
        
        file_seed_cache = query_log_container.GetFileSeedCache()
        gallery_seed_log = query_log_container.GetGallerySeedLog()
        
        this_is_initial_sync = query_header.IsInitialSync()
        num_master_file_seeds_at_start = file_seed_cache.GetApproxNumMasterFileSeeds()
        total_new_urls_for_this_sync = 0
        total_already_in_urls_for_this_sync = 0
        
        gallery_urls_seen_this_sync = set()
        
        if this_is_initial_sync:
            
            file_limit_for_this_sync = self._initial_file_limit
            
        else:
            
            file_limit_for_this_sync = self._periodic_file_limit
            
        
        file_seeds_to_add_in_this_sync = set()
        file_seeds_to_add_in_this_sync_ordered = []
        
        stop_reason = 'unknown stop reason'
        
        job_status.SetStatusText( status_prefix )
        
        initial_search_urls = gug.GenerateGalleryURLs( query_text )
        
        if len( initial_search_urls ) == 0:
            
            self._paused = True
            
            HydrusData.ShowText( 'The subscription "' + self._name + '"\'s Gallery URL Generator, "' + self._gug_key_and_name[1] + '" did not generate any URLs! The sub has paused!' )
            
            raise HydrusExceptions.CancelledException( 'Bad GUG.' )
            
        
        gallery_seeds = [ ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = True ) for url in initial_search_urls ]
        
        gallery_seed_log.AddGallerySeeds( gallery_seeds )
        
        try:
            
            while gallery_seed_log.WorkToDo():
                
                p1 = not self._CanDoWorkNow()
                ( login_ok, login_reason ) = query_header.GalleryLoginOK( CG.client_controller.network_engine, self._name )
                
                if p1 or not login_ok:
                    
                    if not login_ok:
                        
                        if not self._paused:
                            
                            message = 'Query "{}" for subscription "{}" seemed to have an invalid login. The reason was:'.format( query_header.GetHumanName(), self._name )
                            message += '\n' * 2
                            message += login_reason
                            message += '\n' * 2
                            message += 'The subscription has paused. Please see if you can fix the problem and then unpause. If the login script stopped because of missing cookies or similar, it may be broken. Please check out Hydrus Companion for a better login solution.'
                            
                            HydrusData.ShowText( message )
                            
                            self._DelayWork( 300, login_reason )
                            
                            self._paused = True
                            
                        
                    
                    raise HydrusExceptions.CancelledException( 'A problem, so stopping.' )
                    
                
                if job_status.IsCancelled():
                    
                    stop_reason = 'gallery parsing cancelled, likely by user'
                    
                    self._DelayWork( 600, stop_reason )
                    
                    raise HydrusExceptions.CancelledException( 'User cancelled.' )
                    
                
                gallery_seed = gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
                
                if gallery_seed is None:
                    
                    stop_reason = 'thought there was a page to check, but apparently there was not!'
                    
                    break
                    
                
                def status_hook( text ):
                    
                    job_status.SetStatusText( status_prefix + ': ' + HydrusText.GetFirstLine( text ) )
                    
                
                def title_hook( text ):
                    
                    pass
                    
                
                def file_seeds_callable( gallery_page_of_file_seeds ):
                    
                    num_file_seeds_in_this_page = len( gallery_page_of_file_seeds )
                    
                    # ok let's pause for a second to handle an unusual situation
                    
                    interesting_numbers = [ num_file_seeds_in_this_page ]
                    
                    if self._periodic_file_limit is not None:
                        
                        # if we are expecting to get many many files in a single sync, let's remember that!
                        interesting_numbers.append( self._periodic_file_limit )
                        
                    
                    largest_interesting_number = max( interesting_numbers )
                    
                    if largest_interesting_number > query_header.GetFileSeedCacheCompactionNumber():
                        
                        # if we are expecting to process a lot, we want to remember it for next time
                        
                        query_header.SetFileSeedCacheCompactionNumber( largest_interesting_number * 2 )
                        
                    
                    # ok, to work
                    
                    num_urls_added_in_this_call = 0
                    num_urls_already_in_file_seed_cache_in_this_call = 0
                    can_search_for_more_files = True
                    stop_reason = 'unknown stop reason'
                    current_contiguous_num_urls_already_in_file_seed_cache_in_this_call = 0
                    
                    for file_seed in gallery_page_of_file_seeds:
                        
                        if file_seed in file_seeds_to_add_in_this_sync:
                            
                            # this catches the occasional overflow when a new file is uploaded while gallery parsing is going on
                            # we don't want to count these 'seen before this run' urls in the 'caught up to last time' count
                            
                            continue
                            
                        
                        # When are we caught up? This is not a trivial problem. Tags are not always added when files are uploaded, so the order we find files is not completely reliable.
                        # Ideally, we want to search a _bit_ deeper than the first already-seen.
                        # And since we have a page of urls here and now, there is no point breaking early if there might be some new ones at the end.
                        # Current rule is "We are caught up if the final X contiguous files are 'already in'". X is 5 for now.
                        
                        if file_seed_cache.HasFileSeed( file_seed ):
                            
                            num_urls_already_in_file_seed_cache_in_this_call += 1
                            current_contiguous_num_urls_already_in_file_seed_cache_in_this_call += 1
                            
                            if current_contiguous_num_urls_already_in_file_seed_cache_in_this_call >= 100:
                                
                                can_search_for_more_files = False
                                stop_reason = 'saw 100 previously seen urls in a row, so assuming this is a large gallery'
                                
                                break
                                
                            
                        else:
                            
                            num_urls_added_in_this_call += 1
                            current_contiguous_num_urls_already_in_file_seed_cache_in_this_call = 0
                            
                            file_seeds_to_add_in_this_sync.add( file_seed )
                            file_seeds_to_add_in_this_sync_ordered.append( file_seed )
                            
                        
                        if file_limit_for_this_sync is not None:
                            
                            if total_new_urls_for_this_sync + num_urls_added_in_this_call >= file_limit_for_this_sync:
                                
                                # we have found enough new files this sync, so should stop adding files and new gallery pages
                                
                                if this_is_initial_sync:
                                    
                                    stop_reason = 'hit initial file limit'
                                    
                                else:
                                    
                                    if total_already_in_urls_for_this_sync + num_urls_already_in_file_seed_cache_in_this_call > 0:
                                        
                                        # this sync produced some knowns, so it is likely we have stepped through a mix of old and tagged-late new files
                                        # this is no reason to go crying to the user
                                        
                                        stop_reason = 'hit periodic file limit after seeing several already-seen files'
                                        
                                    else:
                                        
                                        # this page had all entirely new files
                                        
                                        if self._this_is_a_random_sample_sub:
                                            
                                            stop_reason = 'hit periodic file limit'
                                            
                                        else:
                                            
                                            do_periodic_message = True
                                            
                                            try:
                                                
                                                result = file_seed_cache.GetFirstFileSeed()
                                                
                                                if result is not None:
                                                    
                                                    # we check multiple url classes to better handle an NGUG that's hitting multiple sites
                                                    old_url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( result.file_seed_data )
                                                    new_url_classes = { CG.client_controller.network_engine.domain_manager.GetURLClass( file_seed.file_seed_data ) for file_seed in file_seeds_to_add_in_this_sync_ordered }
                                                    
                                                    # ok looks like the downloader switched url format. this is a small issue but not a problem the user needs to be informed of
                                                    if old_url_class not in new_url_classes:
                                                        
                                                        do_periodic_message = False
                                                        
                                                    
                                                
                                            except Exception as e:
                                                
                                                HydrusData.Print( 'While trying to compare subscription seed url classes, encountered this error:' )
                                                HydrusData.PrintException( e, do_wait = False )
                                                
                                            
                                            if do_periodic_message:
                                                
                                                self._ShowHitPeriodicFileLimitMessage( query_name, query_text, file_limit_for_this_sync )
                                                
                                                stop_reason = 'hit periodic file limit without seeing any already-seen files!'
                                                
                                            else:
                                                
                                                HydrusData.Print( f'The query "{query_name}" for subscription "{self._name}" found {file_limit_for_this_sync} new URLs without running into any it had seen before. I do not think this needs a gap downloader because the url class appears to have changed.' )
                                                
                                                stop_reason = 'hit periodic file limit after url class appeared to change. sub may spend some extra time catching up'
                                                
                                            
                                        
                                    
                                
                                can_search_for_more_files = False
                                
                                break
                                
                            
                        
                        if not this_is_initial_sync and num_urls_already_in_file_seed_cache_in_this_call > 0:
                            
                            # ok a couple odd situations to handle but with the same fundamental cause: we have a cache smaller than one gallery page
                            # we cannot rely on WE_HIT_OLD_GROUND_THRESHOLD in this case, since the end of the gallery page is incomparable to our cache
                            
                            # EXAMPLE 1: small initial file limit, which we don't want to overrun
                            
                            # if the user set 5 initial file limit but 100 periodic limit, then on the first few syncs, we'll want to notice that situation and not steamroll through that first five (or ~seven on third sync)
                            # if 'X' is new and get, 'A' is already in, and '-' is new and don't get, the page should be:
                            # XXXAAAAA----------------------------------
                            
                            # EXAMPLE 2: the pixiv situation, where a single gallery page may have hundreds of results (and/or multi-file results that will pad out the file cache with more items)
                            
                            # XXXXAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
                            # AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
                            # AAAAAAAAAAAAAAAAAAAA-----------------------------------
                            # -------------------------------------------------------
                            # ----------------------
                            
                            # Note there's another thing to consider, with Pixiv and other multi-file-per-post sites, where the AAAAA 'already in db' are separated in the file log by child posts
                            # I'm solving this with better culling tech
                            
                            num_already_in_urls_we_have_seen_so_far = total_already_in_urls_for_this_sync + num_urls_already_in_file_seed_cache_in_this_call
                            most_of_our_stuff = num_master_file_seeds_at_start * 0.95
                            
                            # If the sub has seen basically everything it started with, we are by definition caught up and should stop immediately!s
                            if num_already_in_urls_we_have_seen_so_far >= most_of_our_stuff:
                                
                                stop_reason = f'saw {HydrusNumbers.ToHumanInt(num_already_in_urls_we_have_seen_so_far)} already-seen files, which is so much of what I already knew about that I am assuming I caught up'
                                
                                can_search_for_more_files = False
                                
                                break
                                
                            
                        
                    
                    WE_HIT_OLD_GROUND_THRESHOLD = 5
                    
                    if can_search_for_more_files:
                        
                        if current_contiguous_num_urls_already_in_file_seed_cache_in_this_call >= WE_HIT_OLD_GROUND_THRESHOLD:
                            
                            # this gallery page has caught up to before, so it should not spawn any more gallery pages
                            
                            can_search_for_more_files = False
                            stop_reason = 'saw {} contiguous previously seen urls at end of page, so assuming we caught up'.format( HydrusNumbers.ToHumanInt( current_contiguous_num_urls_already_in_file_seed_cache_in_this_call ) )
                            
                        
                        if num_urls_added_in_this_call == 0:
                            
                            can_search_for_more_files = False
                            stop_reason = 'no new urls found'
                            
                        
                    
                    return ( num_urls_added_in_this_call, num_urls_already_in_file_seed_cache_in_this_call, can_search_for_more_files, stop_reason )
                    
                
                gallery_seed_url_class = CG.client_controller.network_engine.domain_manager.GetURLClass( gallery_seed.url )
                
                if gallery_seed_url_class in gallery_url_classes_to_special_stop_reasons:
                    
                    special_stop_reason = gallery_url_classes_to_special_stop_reasons[ gallery_seed_url_class ]
                    
                    gallery_seed.SetStatus( CC.STATUS_SKIPPED, note = special_stop_reason )
                    
                    continue
                    
                
                job_status.SetStatusText( status_prefix + ': found ' + HydrusNumbers.ToHumanInt( total_new_urls_for_this_sync ) + ' new urls, checking next page' )
                
                try:
                    
                    ( num_urls_added_in_this_call, num_urls_already_in_file_seed_cache_in_this_call, num_urls_total, result_404, added_new_gallery_pages, can_search_for_more_files, stop_reason ) = gallery_seed.WorkOnURL( 'subscription', gallery_seed_log, file_seeds_callable, status_hook, title_hook, query_header.GenerateNetworkJobFactory( self._name ), ClientImporting.GenerateMultiplePopupNetworkJobPresentationContextFactory( job_status ), self._file_import_options, gallery_urls_seen_before = gallery_urls_seen_this_sync )
                    
                except HydrusExceptions.CancelledException as e:
                    
                    stop_reason = 'gallery network job cancelled, likely by user'
                    
                    self._DelayWork( 600, stop_reason )
                    
                    raise HydrusExceptions.CancelledException( 'User cancelled.' )
                    
                except Exception as e:
                    
                    stop_reason = str( e )
                    
                    raise
                    
                
                # this url probably hit a 'caught up' limit
                # we don't want to hit any other urls of this type this sync
                if not can_search_for_more_files:
                    
                    special_stop_reason = f'previous {gallery_seed_url_class.GetName()} URL said: {stop_reason}'
                    
                    if gallery_seed_url_class is not None:
                        
                        gallery_url_classes_to_special_stop_reasons[ gallery_seed_url_class ] = special_stop_reason
                        
                    
                
                total_new_urls_for_this_sync += num_urls_added_in_this_call
                total_already_in_urls_for_this_sync += num_urls_already_in_file_seed_cache_in_this_call
                
                if file_limit_for_this_sync is not None and total_new_urls_for_this_sync >= file_limit_for_this_sync:
                    
                    break
                    
                
            
        finally:
            
            # now clean up any lingering gallery seeds
            
            while gallery_seed_log.WorkToDo():
                
                gallery_seed = gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
                
                if gallery_seed is None:
                    
                    break
                    
                
                gallery_seed.SetStatus( CC.STATUS_VETOED, note = stop_reason )
                
            
        
        file_seeds_to_add_in_this_sync_ordered.reverse()
        
        # 'first' urls are now at the end, so the file_seed_cache should stay roughly in oldest->newest order
        
        file_seed_cache.AddFileSeeds( file_seeds_to_add_in_this_sync_ordered )
        
        query_header.RegisterSyncComplete( self._checker_options, query_log_container )
        
        #
        
        if query_header.IsDead():
            
            if this_is_initial_sync:
                
                if len( file_seeds_to_add_in_this_sync_ordered ) == 0:
                    
                    HydrusData.ShowText( 'The query "{}" for subscription "{}" did not find any files on its first sync! Could the query text have a typo, like a missing underscore?'.format( query_name, self._name ) )
                    
                else:
                    
                    HydrusData.ShowText( 'The query "{}" for subscription "{}" performed its first sync ok, but the query seems to be already dead! Hydrus will get all the outstanding files, but it will not check for new ones in future. If you know this query has not had any uploads in a long time and just wanted to catch up on what was already there, then no worries.'.format( query_name, self._name ) )
                    
                
            else:
                
                death_file_velocity = self._checker_options.GetDeathFileVelocity()
                
                ( death_files_found, death_time_delta ) = death_file_velocity
                
                HydrusData.ShowText( 'The query "{}" for subscription "{}" found fewer than {} files in the last {}, so it appears to be dead!'.format( query_name, self._name, HydrusNumbers.ToHumanInt( death_files_found ), HydrusTime.TimeDeltaToPrettyTimeDelta( death_time_delta, no_bigger_than_days = True ) ) )
                
            
        else:
            
            if this_is_initial_sync:
                
                if not query_header.FileBandwidthOK( CG.client_controller.network_engine.bandwidth_manager, self._name ) and not self._have_made_an_initial_sync_bandwidth_notification:
                    
                    HydrusData.ShowText( 'FYI: The query "{}" for subscription "{}" performed its initial sync ok, but its downloader is short on bandwidth right now, so no files will be downloaded yet. The subscription will catch up in future as bandwidth becomes available. You can review the estimated time until bandwidth is available under the manage subscriptions dialog. If more queries are performing initial syncs in this run, they may be the same.'.format( query_name, self._name ) )
                    
                    self._have_made_an_initial_sync_bandwidth_notification = True
                    
                
            
        
    
    def _SyncQueryLogContainersCanDoWork( self ):
        
        result = True in ( query_header.WantsToResyncWithLogContainer() for query_header in self._query_headers )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "{}" checking if any log containers need to be resynced: {}'.format( self._name, result ) )
            
        
        return result
        
    
    def _SyncQueryLogContainers( self ):
        
        query_headers_to_do = [ query_header for query_header in self._query_headers if query_header.WantsToResyncWithLogContainer() ]
        
        for query_header in query_headers_to_do:
            
            try:
                
                query_log_container = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, query_header.GetQueryLogContainerName() )
                
            except HydrusExceptions.DBException as e:
                
                if isinstance( e.db_e, HydrusExceptions.DataMissing ):
                    
                    self._DealWithMissingQueryLogContainerError( query_header )
                    
                    break
                    
                else:
                    
                    raise
                    
                
            
            query_header.SyncToQueryLogContainer( self._checker_options, query_log_container )
            
            # don't need to save the container back, we made no changes
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            (
                serialisable_gug_key_and_name,
                serialisable_query_headers,
                serialisable_checker_options,
                initial_file_limit,
                periodic_file_limit,
                paused,
                serialisable_file_import_options,
                serialisable_tag_import_options,
                no_work_until,
                no_work_until_reason,
                show_a_popup_while_working,
                publish_files_to_popup_button,
                publish_files_to_page,
                publish_label_override,
                merge_query_publish_events
            ) = old_serialisable_info
            
            this_is_a_random_sample_sub = False
            
            new_serialisable_info = (
                serialisable_gug_key_and_name,
                serialisable_query_headers,
                serialisable_checker_options,
                initial_file_limit,
                periodic_file_limit,
                this_is_a_random_sample_sub,
                paused,
                serialisable_file_import_options,
                serialisable_tag_import_options,
                no_work_until,
                no_work_until_reason,
                show_a_popup_while_working,
                publish_files_to_popup_button,
                publish_files_to_page,
                publish_label_override,
                merge_query_publish_events
            )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            (
                serialisable_gug_key_and_name,
                serialisable_query_headers,
                serialisable_checker_options,
                initial_file_limit,
                periodic_file_limit,
                this_is_a_random_sample_sub,
                paused,
                serialisable_file_import_options,
                serialisable_tag_import_options,
                no_work_until,
                no_work_until_reason,
                show_a_popup_while_working,
                publish_files_to_popup_button,
                publish_files_to_page,
                publish_label_override,
                merge_query_publish_events
            ) = old_serialisable_info
            
            note_import_options = NoteImportOptions.NoteImportOptions()
            note_import_options.SetIsDefault( True )
            
            serialisable_note_import_options = note_import_options.GetSerialisableTuple()
            
            new_serialisable_info = (
                serialisable_gug_key_and_name,
                serialisable_query_headers,
                serialisable_checker_options,
                initial_file_limit,
                periodic_file_limit,
                this_is_a_random_sample_sub,
                paused,
                serialisable_file_import_options,
                serialisable_tag_import_options,
                serialisable_note_import_options,
                no_work_until,
                no_work_until_reason,
                show_a_popup_while_working,
                publish_files_to_popup_button,
                publish_files_to_page,
                publish_label_override,
                merge_query_publish_events
            )
            
            return ( 3, new_serialisable_info )
            
        
    
    def _WorkOnQueriesFiles( self, job_status: ClientThreading.JobStatus ):
        
        self._file_error_count = 0
        
        query_headers = self._GetQueryHeadersForProcessing()
        
        query_headers = [ query_header for query_header in query_headers if query_header.HasFileWorkToDo() ]
        
        num_queries = len( query_headers )
        
        for ( i, query_header ) in enumerate( query_headers ):
            
            query_name = query_header.GetHumanName()
            
            text_1 = f'syncing files ({HydrusNumbers.ValueRangeToPrettyString( i, num_queries )})'
            query_summary_name = self._name
            
            if query_name != self._name:
                
                text_1 += ' "' + query_name + '"'
                query_summary_name += ': ' + query_name
                
            
            job_status.SetStatusText( text_1 )
            job_status.SetGauge( i, num_queries )
            
            try:
                
                query_log_container = CG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, query_header.GetQueryLogContainerName() )
                
            except HydrusExceptions.DBException as e:
                
                if isinstance( e.db_e, HydrusExceptions.DataMissing ):
                    
                    self._DealWithMissingQueryLogContainerError( query_header )
                    
                    break
                    
                else:
                    
                    raise
                    
                
            
            try:
                
                self._WorkOnQueryFiles( job_status, query_header, query_log_container, query_summary_name )
                
            except HydrusExceptions.CancelledException:
                
                break
                
            finally:
                
                CG.client_controller.WriteSynchronous( 'serialisable', query_log_container )
                
            
        
        job_status.DeleteFiles()
        job_status.DeleteStatusText()
        job_status.DeleteStatusText( level = 2 )
        job_status.DeleteGauge()
        job_status.DeleteGauge( level = 2 )
        
    
    def _WorkOnQueriesFilesCanDoWork( self ):
        
        for query_header in self._query_headers:
            
            if not query_header.IsExpectingToWorkInFuture():
                
                continue
                
            
            if query_header.HasFileWorkToDo():
                
                bandwidth_ok = query_header.FileBandwidthOK( CG.client_controller.network_engine.bandwidth_manager, self._name )
                domain_ok = query_header.FileDomainOK( CG.client_controller.network_engine.domain_manager )
                
                if HG.subscription_report_mode:
                    
                    HydrusData.ShowText( 'Subscription "{}" checking if any file work due: True, bandwidth ok: {}, domain ok: {}'.format( self._name, bandwidth_ok, domain_ok ) )
                    
                
                if bandwidth_ok and domain_ok:
                    
                    return True
                    
                
                if not domain_ok:
                    
                    self._DelayWork( 3600, 'recent domain errors, will try again later' )
                    
                
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "{}" checking if any file work due: False'.format( self._name ) )
            
        
        return False
        
    
    def _WorkOnQueryFiles(
        self,
        job_status: ClientThreading.JobStatus,
        query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader,
        query_log_container: ClientImportSubscriptionQuery.SubscriptionQueryLogContainer,
        query_summary_name: str
        ):
        
        this_query_has_done_work = False
        
        query_name = query_header.GetHumanName()
        file_seed_cache = query_log_container.GetFileSeedCache()
        
        presentation_hashes = []
        presentation_hashes_fast = set()
        
        starting_num_urls = file_seed_cache.GetFileSeedCount()
        starting_num_unknown = file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
        starting_num_done = starting_num_urls - starting_num_unknown
        
        try:
            
            while True:
                
                file_seed = file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
                
                if file_seed is None:
                    
                    if HG.subscription_report_mode:
                        
                        HydrusData.ShowText( 'Query "' + query_name + '" can do no more file work due to running out of unknown urls.' )
                        
                    
                    break # not a cancel, a simple break to stop
                    
                
                if job_status.IsCancelled():
                    
                    self._DelayWork( 300, 'recently cancelled' )
                    
                    raise HydrusExceptions.CancelledException( 'User Cancelled!' )
                    
                
                p1 = not self._CanDoWorkNow()
                p3 = not query_header.FileDomainOK( CG.client_controller.network_engine.domain_manager )
                p4 = not query_header.FileBandwidthOK( CG.client_controller.network_engine.bandwidth_manager, self._name )
                ( login_ok, login_reason ) = query_header.FileLoginOK( CG.client_controller.network_engine, self._name )
                
                if p1 or p4 or not login_ok:
                    
                    if p3 and this_query_has_done_work:
                        
                        job_status.SetStatusText( 'domain had errors, will try again later', 2 )
                        
                        self._DelayWork( 3600, 'domain errors, will try again later' )
                        
                        time.sleep( 5 )
                        
                    
                    if p4 and this_query_has_done_work:
                        
                        job_status.SetStatusText( 'no more bandwidth to download files, will do some more later', 2 )
                        
                        time.sleep( 5 )
                        
                    
                    if not login_ok:
                        
                        if not self._paused:
                            
                            message = 'Query "{}" for subscription "{}" seemed to have an invalid login for one of its file imports. The reason was:'.format( query_header.GetHumanName(), self._name )
                            message += '\n' * 2
                            message += login_reason
                            message += '\n' * 2
                            message += 'The subscription has paused. Please see if you can fix the problem and then unpause. If the login script stopped because of missing cookies or similar, it may be broken. Please check out Hydrus Companion for a better login solution.'
                            
                            HydrusData.ShowText( message )
                            
                            self._DelayWork( 300, login_reason )
                            
                            self._paused = True
                            
                        
                    
                    raise HydrusExceptions.CancelledException( 'Stopping work early!' )
                    
                
                try:
                    
                    num_urls = file_seed_cache.GetFileSeedCount()
                    num_unknown = file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
                    num_done = num_urls - num_unknown
                    
                    # 4001/4003 is not as useful as 1/3
                    
                    human_num_urls = num_urls - starting_num_done
                    human_num_done = num_done - starting_num_done
                    
                    x_out_of_y = 'files ' + HydrusNumbers.ValueRangeToPrettyString( human_num_done, human_num_urls ) + ': '
                    
                    job_status.SetGauge( human_num_done, human_num_urls, level = 2 )
                    
                    def status_hook( text ):
                        
                        job_status.SetStatusText( x_out_of_y + HydrusText.GetFirstLine( text ), 2 )
                        
                    
                    file_seed.WorkOnURL( file_seed_cache, status_hook, query_header.GenerateNetworkJobFactory( self._name ), ClientImporting.GenerateMultiplePopupNetworkJobPresentationContextFactory( job_status ), self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_QUIET, self._tag_import_options, self._note_import_options )
                    
                    query_tag_import_options = query_header.GetTagImportOptions()
                    
                    if query_tag_import_options.HasAdditionalTags() and file_seed.status in CC.SUCCESSFUL_IMPORT_STATES:
                        
                        if file_seed.HasHash():
                            
                            hash = file_seed.GetHash()
                            
                            media_result = CG.client_controller.Read( 'media_result', hash )
                            
                            downloaded_tags = []
                            
                            content_update_package = query_tag_import_options.GetContentUpdatePackage( file_seed.status, media_result, downloaded_tags ) # additional tags
                            
                            if content_update_package.HasContent():
                                
                                CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                                
                            
                        
                    
                    real_presentation_import_options = FileImportOptionsLegacy.GetRealPresentationImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_LOUD )
                    
                    if file_seed.ShouldPresent( real_presentation_import_options ):
                        
                        hash = file_seed.GetHash()
                        
                        if hash not in presentation_hashes_fast:
                            
                            presentation_hashes.append( hash )
                            
                            presentation_hashes_fast.add( hash )
                            
                        
                    
                except HydrusExceptions.CancelledException as e:
                    
                    self._DelayWork( 300, str( e ) )
                    
                    break
                    
                except HydrusExceptions.VetoException as e:
                    
                    status = CC.STATUS_VETOED
                    
                    note = str( e )
                    
                    file_seed.SetStatus( status, note = note )
                    
                except HydrusExceptions.NotFoundException:
                    
                    status = CC.STATUS_VETOED
                    
                    note = '404'
                    
                    file_seed.SetStatus( status, note = note )
                    
                except Exception as e:
                    
                    status = CC.STATUS_ERROR
                    
                    job_status.SetStatusText( x_out_of_y + 'file failed', 2 )
                    
                    file_seed.SetStatus( status, exception = e )
                    
                    if isinstance( e, HydrusExceptions.DataMissing ):
                        
                        # DataMissing is a quick thing to avoid subscription abandons when lots of deleted files in e621 (or any other booru)
                        # this should be richer in any case in the new system
                        
                        pass
                        
                    else:
                        
                        self._file_error_count += 1
                        
                        time.sleep( 5 )
                        
                    
                    error_count_threshold = CG.client_controller.new_options.GetNoneableInteger( 'subscription_file_error_cancel_threshold' )
                    
                    if error_count_threshold is not None and self._file_error_count >= error_count_threshold:
                        
                        raise Exception( 'The subscription ' + self._name + ' encountered several errors when downloading files, so it abandoned its sync.' )
                        
                    
                
                this_query_has_done_work = True
                
                if len( presentation_hashes ) > 0:
                    
                    job_status.SetFiles( presentation_hashes, query_summary_name )
                    
                else:
                    
                    # although it is nice to have the file popup linger a little once a query is done, if the next query has 15 'already in db', it has outstayed its welcome
                    job_status.DeleteFiles()
                    
                
                time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
                
                CG.client_controller.WaitUntilViewFree()
                
            
        finally:
            
            query_header.UpdateFileStatus( query_log_container )
            
            if len( presentation_hashes ) > 0:
                
                publishing_label = self._GetPublishingLabel( query_header )
                
                ClientImporting.PublishPresentationHashes( publishing_label, presentation_hashes, self._publish_files_to_popup_button, self._publish_files_to_page )
                
            
        
    
    def CanCheckNow( self ):
        
        return True in ( query_header.CanCheckNow() for query_header in self._query_headers )
        
    
    def CanLowerCaseQueries( self ):
        
        return True in ( query_header.GetQueryText() != query_header.GetQueryText().lower() for query_header in self._query_headers )
        
    
    def CanReset( self ):
        
        return True in ( not query_header.IsInitialSync() for query_header in self._query_headers )
        
    
    def CanRetryFailed( self ):
        
        return True in ( query_header.CanRetryFailed() for query_header in self._query_headers )
        
    
    def CanRetryIgnored( self ):
        
        return True in ( query_header.CanRetryIgnored() for query_header in self._query_headers )
        
    
    def CanScrubDelay( self ):
        
        return not HydrusTime.TimeHasPassed( self._no_work_until )
        
    
    def CheckNow( self ):
        
        for query_header in self._query_headers:
            
            query_header.CheckNow()
            
        
        self.ScrubDelay()
        
    
    def DedupeQueryTexts( self, dedupe_query_texts: collections.abc.Iterable[ str ], enforce_case: bool = True ):
        
        if not enforce_case:
            
            dedupe_query_texts = { query_text.lower() for query_text in dedupe_query_texts }
            
        
        query_headers = list( self._query_headers )
        
        # order query headers by biggest first
        query_headers.sort( key = lambda q_h: q_h.GetFileSeedCacheStatus().GetFileSeedCount(), reverse = True )
        
        query_texts_seen = set()
        
        deduped_query_headers = []
        
        for query_header in query_headers:
            
            query_text = query_header.GetQueryText()
            
            if not enforce_case:
                
                query_text = query_text.lower()
                
            
            if query_text in dedupe_query_texts:
                
                if query_text in query_texts_seen:
                    
                    continue
                    
                
            
            query_texts_seen.add( query_text )
            
            deduped_query_headers.append( query_header )
            
        
        self._query_headers = deduped_query_headers
        
    
    def GetAllQueryLogContainerNames( self ) -> set[ str ]:
        
        names = { query_header.GetQueryLogContainerName() for query_header in self._query_headers }
        
        return names
        
    
    def GetBandwidthWaitingEstimateMinMax( self, bandwidth_manager: ClientNetworkingBandwidth.NetworkBandwidthManager ):
        
        if len( self._query_headers ) == 0:
            
            return ( 0, 0 )
            
        
        estimates = []
        
        for query_header in self._query_headers:
            
            estimate = query_header.GetBandwidthWaitingEstimate( bandwidth_manager, self._name )
            
            estimates.append( estimate )
            
        
        min_estimate = min( estimates )
        max_estimate = max( estimates )
        
        return ( min_estimate, max_estimate )
        
    
    def GetBestEarliestNextWorkTime( self ):
        
        next_work_times = set()
        
        for query_header in self._query_headers:
            
            next_work_time = query_header.GetNextWorkTime( CG.client_controller.network_engine.bandwidth_manager, self._name )
            
            if next_work_time is not None:
                
                next_work_times.add( next_work_time )
                
            
        
        if len( next_work_times ) == 0:
            
            return None
            
        
        best_next_work_time = min( next_work_times )
        
        if not HydrusTime.TimeHasPassed( self._no_work_until ):
            
            best_next_work_time = max( ( best_next_work_time, self._no_work_until ) )
            
        
        return best_next_work_time
        
    
    def GetCheckerOptions( self ):
        
        return self._checker_options
        
    
    def GetFileImportOptions( self ):
        
        return self._file_import_options
        
    
    def GetGUGKeyAndName( self ):
        
        return self._gug_key_and_name
        
    
    def GetQueryHeaders( self ) -> list[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ]:
        
        return self._query_headers
        
    
    def GetMergeable( self, potential_mergees ):
        
        mergeable = []
        unmergeable = []
        
        for subscription in potential_mergees:
            
            if subscription.GetGUGKeyAndName()[1] == self._gug_key_and_name[1]:
                
                mergeable.append( subscription )
                
            else:
                
                unmergeable.append( subscription )
                
            
        
        return ( mergeable, unmergeable )
        
    
    def GetNoteImportOptions( self ):
        
        return self._note_import_options
        
    
    def GetPresentationOptions( self ):
        
        return ( self._show_a_popup_while_working, self._publish_files_to_popup_button, self._publish_files_to_page, self._publish_label_override, self._merge_query_publish_events )
        
    
    def GetTagImportOptions( self ):
        
        return self._tag_import_options
        
    
    def HasQuerySearchTextFragment( self, search_text_fragment ):
        
        for query_header in self._query_headers:
            
            query_text = query_header.GetQueryText()
            
            if search_text_fragment in query_text:
                
                return True
                
            
        
        return False
        
    
    def IsExpectingToWorkInFuture( self ):
        
        if self._paused:
            
            return False
            
        
        result = True in ( query_header.IsExpectingToWorkInFuture() for query_header in self._query_headers )
        
        return result
        
    
    def IsPaused( self ):
        
        return self._paused
        
    
    def LowerCaseQueries( self ):
        
        for query_header in self._query_headers:
            
            query_text = query_header.GetQueryText()
            query_text_lower = query_text.lower()
            
            if query_text != query_text_lower:
                
                query_header.SetQueryText( query_text_lower )
                
            
        
    
    def Merge( self, mergees: collections.abc.Iterable[ "Subscription" ] ):
        
        unmerged = []
        merged = []
        
        for subscription in mergees:
            
            if subscription.GetGUGKeyAndName()[1] == self._gug_key_and_name[1]:
                
                self._query_headers.extend( subscription.GetQueryHeaders() )
                
                merged.append( subscription )
                
            else:
                
                unmerged.append( subscription )
                
            
        
        return ( merged, unmerged )
        
    
    def PauseResume( self ):
        
        self.SetPaused( not self._paused )
        
    
    def RemoveQueryTexts( self, removee_query_texts: collections.abc.Iterable[ str ], enforce_case: bool = True ):
        
        if not enforce_case:
            
            removee_query_texts = { query_text.lower() for query_text in removee_query_texts }
            
        
        if enforce_case:
            
            self._query_headers = [ query_header for query_header in self._query_headers if query_header.GetQueryText() not in removee_query_texts ]
            
        else:
            
            self._query_headers = [ query_header for query_header in self._query_headers if query_header.GetQueryText().lower() not in removee_query_texts ]
            
        
    
    def Separate( self, base_name, only_these_query_headers = None ):
        
        if only_these_query_headers is None:
            
            only_these_query_headers = set( self._query_headers )
            
        else:
            
            only_these_query_headers = set( only_these_query_headers )
            
        
        my_query_headers = self._query_headers
        
        self._query_headers = []
        
        base_sub = self.Duplicate()
        
        self._query_headers = my_query_headers
        
        subscriptions = []
        
        for query_header in my_query_headers:
            
            if query_header not in only_these_query_headers:
                
                continue
                
            
            subscription = base_sub.Duplicate()
            
            subscription.SetQueryHeaders( [ query_header ] )
            
            subscription.SetName( base_name + ': ' + query_header.GetHumanName() )
            
            subscriptions.append( subscription )
            
        
        self._query_headers = [ query_header for query_header in my_query_headers if query_header not in only_these_query_headers ]
        
        return subscriptions
        
    
    def SetCheckerOptions( self, checker_options: ClientImportOptions.CheckerOptions, names_to_query_log_containers = None ):
        
        changes_made = self._checker_options.GetSerialisableTuple() != checker_options.GetSerialisableTuple()
        
        self._checker_options = checker_options
        
        if changes_made:
            
            for query_header in self._query_headers:
                
                if names_to_query_log_containers is not None:
                    
                    name = query_header.GetQueryLogContainerName()
                    
                    if name in names_to_query_log_containers:
                        
                        query_log_container = names_to_query_log_containers[ name ]
                        
                        query_header.SyncToQueryLogContainer( checker_options, query_log_container )
                        
                        continue
                        
                    
                
                query_header.SetQueryLogContainerStatus( ClientImportSubscriptionQuery.LOG_CONTAINER_UNSYNCED, pretty_velocity_override = 'will recalculate when next fully loaded' )
                
            
        
    
    def SetFileImportOptions( self, file_import_options ):
        
        self._file_import_options = file_import_options.Duplicate()
        
    
    def SetPaused( self, value ):
        
        self._paused = value
        
    
    def SetPresentationOptions( self, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events ):
        
        self._show_a_popup_while_working = show_a_popup_while_working
        self._publish_files_to_popup_button = publish_files_to_popup_button
        self._publish_files_to_page = publish_files_to_page
        self._publish_label_override = publish_label_override
        self._merge_query_publish_events = merge_query_publish_events
        
    
    def SetQueryHeaders( self, query_headers: collections.abc.Iterable[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] ):
        
        self._query_headers = list( query_headers )
        
    
    def SetNoteImportOptions( self, note_import_options ):
        
        self._note_import_options = note_import_options.Duplicate()
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options.Duplicate()
        
    
    def SetThisIsARandomSampleSubscription( self, value: bool ):
        
        self._this_is_a_random_sample_sub = value
        
    
    def SetTuple( self, gug_key_and_name, checker_options: ClientImportOptions.CheckerOptions, initial_file_limit, periodic_file_limit, paused, file_import_options: FileImportOptionsLegacy.FileImportOptionsLegacy, tag_import_options: TagImportOptionsLegacy.TagImportOptionsLegacy, no_work_until ):
        
        self._gug_key_and_name = gug_key_and_name
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
        
    
    def StopWorkForShutdown( self ):
        
        self._stop_work_for_shutdown = True
        
    
    def Sync( self ):
        
        log_sync_work_to_do = self._SyncQueryLogContainersCanDoWork()
        
        if self._CanDoWorkNow() and log_sync_work_to_do:
            
            try:
                
                self._SyncQueryLogContainers()
                
            except HydrusExceptions.ShutdownException:
                
                HydrusData.Print( f'Exiting subscription "{self._name}" due to program shutdown.' )
                
                return
                
            except Exception as e:
                
                HydrusData.ShowText( f'The subscription "{self._name}" encountered an exception when trying to sync:' )
                HydrusData.ShowException( e )
                
                self._paused = True
                
                self._DelayWork( 300, 'error: {}'.format( repr( e ) ) )
                
                return
                
            
        
        sync_work_to_do = self._SyncQueriesCanDoWork()
        files_work_to_do = self._WorkOnQueriesFilesCanDoWork()
        
        if self._CanDoWorkNow() and ( sync_work_to_do or files_work_to_do ):
            
            job_status = ClientThreading.JobStatus( pausable = False, cancellable = True )
            
            try:
                
                job_status.SetStatusTitle( 'subscriptions - ' + self._name )
                
                if self._show_a_popup_while_working:
                    
                    CG.client_controller.pub( 'message', job_status )
                    
                
                # it is possible a query becomes due for a check while others are syncing, so we repeat this while watching for a stop signal
                while self._CanDoWorkNow() and self._SyncQueriesCanDoWork():
                    
                    self._SyncQueries( job_status )
                    
                
                real_file_import_options = FileImportOptionsLegacy.GetRealFileImportOptions( self._file_import_options, FileImportOptionsLegacy.IMPORT_TYPE_QUIET )
                
                real_file_import_options.GetLocationImportOptions().CheckReadyToImport()
                
                self._WorkOnQueriesFiles( job_status )
                
            except HydrusExceptions.NetworkException as e:
                
                delay = CG.client_controller.new_options.GetInteger( 'subscription_network_error_delay' )
                
                HydrusData.Print( f'The subscription "{self._name}" encountered an exception when trying to sync:' )
                
                HydrusData.Print( e )
                
                job_status.SetStatusText( 'Encountered a network error, will retry again later' )
                
                self._DelayWork( delay, 'network error: ' + str( e ) )
                
                time.sleep( 5 )
                
            except HydrusExceptions.ShutdownException:
                
                HydrusData.Print( f'Exiting subscription "{self._name}" due to program shutdown.' )
                
            except Exception as e:
                
                HydrusData.ShowText( f'The subscription "{self._name}" encountered an exception when trying to sync:' )
                HydrusData.ShowException( e )
                
                delay = CG.client_controller.new_options.GetInteger( 'subscription_other_error_delay' )
                
                self._DelayWork( delay, 'error: ' + str( e ) )
                
            finally:
                
                job_status.DeleteNetworkJob()
                
            
            if job_status.GetFiles() is not None:
                
                job_status.Finish()
                
            else:
                
                job_status.FinishAndDismiss()
                
            
        
    
    def ThisIsARandomSampleSubscription( self ) -> bool:
        
        return self._this_is_a_random_sample_sub
        
    
    def ToTuple( self ):
        
        return ( self._name, self._gug_key_and_name, self._query_headers, self._checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, self._file_import_options, self._tag_import_options, self._no_work_until, self._no_work_until_reason )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ] = Subscription

LOG_CONTAINER_SYNCED = 0
LOG_CONTAINER_UNSYNCED = 1
LOG_CONTAINER_MISSING = 2

class SubscriptionContainer( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_CONTAINER
    SERIALISABLE_NAME = 'Subscription with all data'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self.subscription = Subscription( 'default' )
        self.query_log_containers = HydrusSerialisable.SerialisableList()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_subscription = self.subscription.GetSerialisableTuple()
        serialisable_query_log_containers = self.query_log_containers.GetSerialisableTuple()
        
        return ( serialisable_subscription, serialisable_query_log_containers )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_subscription, serialisable_query_log_containers ) = serialisable_info
        
        self.subscription = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_subscription )
        self.query_log_containers = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_query_log_containers )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_CONTAINER ] = SubscriptionContainer

class SubscriptionJob( object ):
    
    def __init__( self, controller: "CG.ClientController.Controller", subscription: Subscription ):
        
        self._controller = controller
        self._subscription = subscription
        self._job_done = threading.Event()
        
    
    def _DoWork( self ):
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "{}" about to start.'.format( self._subscription.GetName() ) )
            
        
        self._subscription.Sync()
        
        self._controller.WriteSynchronous( 'serialisable', self._subscription )
        
    
    def IsDone( self ):
        
        return self._job_done.is_set()
        
    
    def Work( self ):
        
        try:
            
            self._DoWork()
            
        finally:
            
            self._job_done.set()
            
        
    

class SubscriptionsManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller, subscriptions: list[ Subscription ] ):
        
        super().__init__( controller, 10 )
        
        self._names_to_subscriptions = { subscription.GetName() : subscription for subscription in subscriptions }
        self._names_to_running_subscription_info = {}
        self._names_that_cannot_run = set()
        self._names_to_next_work_time = {}
        
        self._pause_subscriptions_for_editing = False
        
        self._big_pauser = HydrusThreading.BigJobPauser( wait_time = 0.8 )
        
        self._controller.sub( self, 'Wake', 'notify_network_traffic_unpaused' )
        
    
    def _ClearFinishedSubscriptions( self ):
        
        for ( name, ( job, subscription ) ) in list( self._names_to_running_subscription_info.items() ):
            
            if job.IsDone():
                
                self._UpdateSubscriptionInfo( subscription, just_finished_work = True )
                
                del self._names_to_running_subscription_info[ name ]
                
            
        
    
    def _GetMainLoopWaitTime( self ):
        
        if self._shutdown:
            
            return 0.1
            
        
        if len( self._names_to_running_subscription_info ) > 0:
            
            return 0.5
            
        else:
            
            subscription = self._GetSubscriptionReadyToGo()
            
            if subscription is not None:
                
                return 0.5
                
            else:
                
                return 5
                
            
        
    
    def _GetSubscriptionReadyToGo( self ):
        
        p1 = CG.client_controller.new_options.GetBoolean( 'pause_subs_sync' ) or self._pause_subscriptions_for_editing
        p2 = CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
        p3 = HG.started_shutdown
        
        if p1 or p2 or p3:
            
            return None
            
        
        max_simultaneous_subscriptions = CG.client_controller.new_options.GetInteger( 'max_simultaneous_subscriptions' )
        
        if len( self._names_to_running_subscription_info ) >= max_simultaneous_subscriptions:
            
            return None
            
        
        possible_names = set( self._names_to_subscriptions.keys() )
        possible_names.difference_update( set( self._names_to_running_subscription_info.keys() ) )
        possible_names.difference_update( self._names_that_cannot_run )
        
        # just a couple of seconds for calculation and human breathing room
        SUB_WORK_DELAY_BUFFER = 3
        
        names_not_due = { name for ( name, next_work_time ) in self._names_to_next_work_time.items() if not HydrusTime.TimeHasPassed( next_work_time + SUB_WORK_DELAY_BUFFER ) }
        
        possible_names.difference_update( names_not_due )
        
        if len( possible_names ) == 0:
            
            return None
            
        
        possible_names = list( possible_names )
        
        if CG.client_controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
            
            subscription_name = random.choice( possible_names )
            
        else:
            
            HydrusText.HumanTextSort( possible_names )
            
            subscription_name = possible_names.pop( 0 )
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription manager selected "{}" to start.'.format( subscription_name ) )
            
        
        return self._names_to_subscriptions[ subscription_name ]
        
    
    def _UpdateSubscriptionInfo( self, subscription: Subscription, just_finished_work = False ):
        
        name = subscription.GetName()
        
        if name in self._names_that_cannot_run:
            
            self._names_that_cannot_run.discard( name )
            
        
        if name in self._names_to_next_work_time:
            
            del self._names_to_next_work_time[ name ]
            
        
        if not subscription.IsExpectingToWorkInFuture():
            
            self._names_that_cannot_run.add( name )
            
        else:
            
            next_work_time = subscription.GetBestEarliestNextWorkTime()
            
            if next_work_time is None:
                
                self._names_that_cannot_run.add( name )
                
            else:
                
                p1 = CG.client_controller.new_options.GetBoolean( 'pause_subs_sync' ) or self._pause_subscriptions_for_editing
                p2 = CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
                
                stopped_because_pause = p1 or p2
                
                if just_finished_work and not stopped_because_pause:
                    
                    # even with the new data format, we don't want to have a load/save cycle repeating _too_ much, just to stop any weird cascades
                    # this sets min resolution of a single sub repeat cycle
                    BUFFER_TIME = 120
                    
                    next_work_time = max( next_work_time, HydrusTime.GetNow() + BUFFER_TIME )
                    
                
                self._names_to_next_work_time[ name ] = next_work_time
                
            
        
    
    def GetName( self ) -> str:
        
        return 'subscriptions'
        
    
    def GetSubscriptions( self ) -> list[ Subscription ]:
        
        with self._lock:
            
            return list( self._names_to_subscriptions.values() )
            
        
    
    def _DoMainLoop( self ):
        
        try:
            
            while True:
                
                with self._lock:
                    
                    self._CheckShutdown()
                    
                    subscription = self._GetSubscriptionReadyToGo()
                    
                    if subscription is not None:
                        
                        job = SubscriptionJob( self._controller, subscription )
                        
                        CG.client_controller.CallToThread( job.Work )
                        
                        self._names_to_running_subscription_info[ subscription.GetName() ] = ( job, subscription )
                        
                    
                    self._ClearFinishedSubscriptions()
                    
                    wait_time = self._GetMainLoopWaitTime()
                    
                
                self._big_pauser.Pause()
                
                self._wake_from_work_sleep_event.wait( wait_time )
                
                self._wake_from_work_sleep_event.clear()
                self._wake_from_idle_sleep_event.clear()
                
            
        finally:
            
            self.PauseSubscriptionsForEditing()
            
            with self._lock:
                
                for ( job, subscription ) in self._names_to_running_subscription_info.values():
                    
                    subscription.StopWorkForShutdown()
                    
                
            
            while not HG.model_shutdown:
                
                with self._lock:
                    
                    self._ClearFinishedSubscriptions()
                    
                    if len( self._names_to_running_subscription_info ) == 0:
                        
                        break
                        
                    
                    time.sleep( 0.1 )
                    
                
            
        
    
    def PauseSubscriptionsForEditing( self ):
        
        with self._lock:
            
            self._pause_subscriptions_for_editing = True
            
        
    
    def ResumeSubscriptionsAfterEditing( self ):
        
        with self._lock:
            
            self._pause_subscriptions_for_editing = False
            
        
    
    def SetSubscriptions( self, subscriptions ):
        
        with self._lock:
            
            self._names_to_subscriptions = { subscription.GetName() : subscription for subscription in subscriptions }
            
            self._names_that_cannot_run = set()
            self._names_to_next_work_time = {}
            
            for subscription in subscriptions:
                
                self._UpdateSubscriptionInfo( subscription )
                
            
        
        self.Wake()
        
    
    def ShowSnapshot( self ):
        
        with self._lock:
            
            sub_names = sorted( self._names_to_subscriptions.keys() )
            
            running = sorted( self._names_to_running_subscription_info.keys() )
            
            cannot_run = sorted( self._names_that_cannot_run )
            
            next_times = sorted( self._names_to_next_work_time.items(), key = lambda n_nwt_tuple: n_nwt_tuple[1] )
            
            message = '{} subs: {}'.format( HydrusNumbers.ToHumanInt( len( self._names_to_subscriptions ) ), ', '.join( sub_names ) )
            message += '\n' * 2
            message += '{} running: {}'.format( HydrusNumbers.ToHumanInt( len( self._names_to_running_subscription_info ) ), ', '.join( running ) )
            message += '\n' * 2
            message += '{} not runnable: {}'.format( HydrusNumbers.ToHumanInt( len( self._names_that_cannot_run ) ), ', '.join( cannot_run ) )
            message += '\n' * 2
            message += '{} next times: {}'.format( HydrusNumbers.ToHumanInt( len( self._names_to_next_work_time ) ), ', '.join( ( '{}: {}'.format( name, HydrusTime.TimestampToPrettyTimeDelta( next_work_time ) ) for ( name, next_work_time ) in next_times ) ) )
            
            HydrusData.ShowText( message )
            
        
    
    def Shutdown( self ):
        
        self.PauseSubscriptionsForEditing()
        
        super().Shutdown()
        
    
    def SubscriptionsArePausedForEditing( self ):
        
        with self._lock:
            
            return self._pause_subscriptions_for_editing
            
        
    
    def SubscriptionsRunning( self ):
        
        with self._lock:
            
            self._ClearFinishedSubscriptions()
            
            return len( self._names_to_running_subscription_info ) > 0
            
        
    
