import os
import random
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusThreading

from hydrus.client import ClientData
from hydrus.client import ClientThreading
from hydrus.client import ClientConstants as CC
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing import ClientImportSubscriptionQuery
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.importing.options import TagImportOptions
from hydrus.client.networking import ClientNetworkingBandwidth
from hydrus.client.networking import ClientNetworkingDomain

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_NAME = 'Subscription'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name, gug_key_and_name = None ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        if gug_key_and_name is None:
            
            gug_key_and_name = ( HydrusData.GenerateKey(), 'unknown source' )
            
        
        self._gug_key_and_name = gug_key_and_name
        
        self._query_headers: typing.List[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] = []
        
        new_options = HG.client_controller.new_options
        
        self._checker_options = new_options.GetDefaultSubscriptionCheckerOptions()
        
        if HC.options[ 'gallery_file_limit' ] is None:
            
            self._initial_file_limit = 100
            
        else:
            
            self._initial_file_limit = min( 100, HC.options[ 'gallery_file_limit' ] )
            
        
        self._periodic_file_limit = 100
        
        self._this_is_a_random_sample_sub = False
        
        self._paused = False
        
        self._file_import_options = new_options.GetDefaultFileImportOptions( 'quiet' )
        self._tag_import_options = TagImportOptions.TagImportOptions( is_default = True )
        
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
        
        p1 = not ( self._paused or HG.client_controller.options[ 'pause_subs_sync' ] or HG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ) or HG.client_controller.subscriptions_manager.SubscriptionsArePausedForEditing() )
        p2 = not ( HG.view_shutdown or self._stop_work_for_shutdown )
        p3 = self._NoDelays()
        
        if HG.subscription_report_mode:
            
            message = 'Subscription "{}" CanDoWork check.'.format( self._name )
            message += os.linesep
            message += 'Paused/Global/Network/Dialog Pause: {}/{}/{}/{}'.format( self._paused, HG.client_controller.options[ 'pause_subs_sync' ], HG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ), HG.client_controller.subscriptions_manager.SubscriptionsArePausedForEditing() )
            message += os.linesep
            message += 'View/Sub shutdown: {}/{}'.format( HG.view_shutdown, self._stop_work_for_shutdown )
            message += os.linesep
            message += 'No delays: {}'.format( self._NoDelays() )
            
            HydrusData.ShowText( message )
            
        
        return p1 and p2 and p3
        
    
    def _DealWithMissingQueryLogContainerError( self, query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader ):
        
        query_header.SetQueryLogContainerStatus( ClientImportSubscriptionQuery.LOG_CONTAINER_MISSING )
        
        self._paused = True
        
        HydrusData.ShowText( 'The subscription "{}"\'s "{}" query was missing database data! This could be a serious error! Please go to _manage subscriptions_ to reset the data, and you may want to contact hydrus dev. The sub has paused!'.format( self._name, query_header.GetHumanName() ) )
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusData.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _GetPublishingLabel( self, query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader ):
        
        if self._publish_label_override is None:
            
            label = self._name
            
        else:
            
            label = self._publish_label_override
            
        
        if not self._merge_query_publish_events:
            
            label += ': ' + query_header.GetHumanName()
            
        
        return label
        
    
    def _GetQueryHeadersForProcessing( self ) -> typing.List[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ]:
        
        query_headers = list( self._query_headers )
        
        if HG.client_controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
            
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
        
    
    def _NoDelays( self ):
        
        return HydrusData.TimeHasPassed( self._no_work_until )
        
    
    def _ShowHitPeriodicFileLimitMessage( self, query_name: int, query_text: int, file_limit: int ):
        
        message = 'The query "{}" for subscription "{}" found {} new URLs without running into any it had seen before.'.format( query_name, self._name, file_limit )
        message += os.linesep
        message += 'Either a user uploaded a lot of files to that query in a short period, in which case there is a gap in your subscription you may wish to fill, or the site has just changed its URL format, in which case you may see several of these messages for this site over the coming weeks, and you should ignore them.'
        
        call = HydrusData.Call( HG.client_controller.pub, 'make_new_subscription_gap_downloader', self._gug_key_and_name, query_text, self._file_import_options.Duplicate(), self._tag_import_options.Duplicate(), file_limit * 5 )
        
        call.SetLabel( 'start a new downloader for this to fill in the gap!' )
        
        job_key = ClientThreading.JobKey()
        
        job_key.SetVariable( 'popup_text_1', message )
        job_key.SetUserCallable( call )
        
        HG.client_controller.pub( 'message', job_key )
        
    
    def _SyncQueries( self, job_key ):
        
        self._have_made_an_initial_sync_bandwidth_notification = False
        
        gug = HG.client_controller.network_engine.domain_manager.GetGUG( self._gug_key_and_name )
        
        if gug is None:
            
            self._paused = True
            
            HydrusData.ShowText( 'The subscription "{}" could not find a Gallery URL Generator for "{}"! The sub has paused!'.format( self._name, self._gug_key_and_name[1] ) )
            
            return
            
        
        try:
            
            gug.CheckFunctional()
            
        except HydrusExceptions.ParseException as e:
            
            self._paused = True
            
            message = 'The subscription "{}"\'s Gallery URL Generator, "{}" seems not to be functional! The sub has paused! The given reason was:'.format( self._name, self._gug_key_and_name[1] )
            message += os.linesep * 2
            message += str( e )
            
            HydrusData.ShowText( message )
            
            return
            
        
        self._gug_key_and_name = gug.GetGUGKeyAndName() # just a refresher, to keep up with any changes
        
        query_headers = self._GetQueryHeadersForProcessing()
        
        query_headers = [ query_header for query_header in query_headers if query_header.IsSyncDue() ]
        
        num_queries = len( query_headers )
        
        for ( i, query_header ) in enumerate( query_headers ):
            
            status_prefix = 'synchronising'
            
            query_name = query_header.GetHumanName()
            
            if query_name != self._name:
                
                status_prefix += ' "' + query_name + '"'
                
            
            status_prefix += ' (' + HydrusData.ConvertValueRangeToPrettyString( i + 1, num_queries ) + ')'
            
            try:
                
                query_log_container = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, query_header.GetQueryLogContainerName() )
                
            except HydrusExceptions.DBException as e:
                
                if isinstance( e.db_e, HydrusExceptions.DataMissing ):
                    
                    self._DealWithMissingQueryLogContainerError( query_header )
                    
                    break
                    
                else:
                    
                    raise
                    
                
            
            try:
                
                self._SyncQuery( job_key, gug, query_header, query_log_container, status_prefix )
                
            except HydrusExceptions.CancelledException:
                
                break
                
            finally:
                
                HG.client_controller.WriteSynchronous( 'serialisable', query_log_container )
                
            
        
    
    def _SyncQueriesCanDoWork( self ):
        
        result = True in ( query_header.IsSyncDue() for query_header in self._query_headers )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "{}" checking if any sync work due: {}'.format( self._name, result ) )
            
        
        return result
        
    
    def _SyncQuery(
        self,
        job_key: ClientThreading.JobKey,
        gug: ClientNetworkingDomain.GalleryURLGenerator, # not actually correct for an ngug, but _whatever_
        query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader,
        query_log_container: ClientImportSubscriptionQuery.SubscriptionQueryLogContainer,
        status_prefix: str
        ):
        
        query_text = query_header.GetQueryText()
        query_name = query_header.GetHumanName()
        
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
        
        job_key.SetVariable( 'popup_text_1', status_prefix )
        
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
                ( login_ok, login_reason ) = query_header.GalleryLoginOK( HG.client_controller.network_engine, self._name )
                
                if p1 or not login_ok:
                    
                    if not login_ok:
                        
                        if not self._paused:
                            
                            message = 'Query "{}" for subscription "{}" seemed to have an invalid login. The reason was:'.format( query_header.GetHumanName(), self._name )
                            message += os.linesep * 2
                            message += login_reason
                            message += os.linesep * 2
                            message += 'The subscription has paused. Please see if you can fix the problem and then unpause. Hydrus dev would like feedback on this process.'
                            
                            HydrusData.ShowText( message )
                            
                            self._DelayWork( 300, login_reason )
                            
                            self._paused = True
                            
                        
                    
                    raise HydrusExceptions.CancelledException( 'A problem, so stopping.' )
                    
                
                if job_key.IsCancelled():
                    
                    stop_reason = 'gallery parsing cancelled, likely by user'
                    
                    self._DelayWork( 600, stop_reason )
                    
                    raise HydrusExceptions.CancelledException( 'User cancelled.' )
                    
                
                gallery_seed = gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
                
                if gallery_seed is None:
                    
                    stop_reason = 'thought there was a page to check, but apparently there was not!'
                    
                    break
                    
                
                def status_hook( text ):
                    
                    if len( text ) > 0:
                        
                        text = text.splitlines()[0]
                        
                    
                    job_key.SetVariable( 'popup_text_1', status_prefix + ': ' + text )
                    
                
                def title_hook( text ):
                    
                    pass
                    
                
                def file_seeds_callable( gallery_page_of_file_seeds ):
                    
                    num_urls_added = 0
                    num_urls_already_in_file_seed_cache = 0
                    can_search_for_more_files = True
                    stop_reason = 'unknown stop reason'
                    current_contiguous_num_urls_already_in_file_seed_cache = 0
                    num_file_seeds_in_this_page = len( gallery_page_of_file_seeds )
                    
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
                            
                            num_urls_already_in_file_seed_cache += 1
                            current_contiguous_num_urls_already_in_file_seed_cache += 1
                            
                            if current_contiguous_num_urls_already_in_file_seed_cache >= 100:
                                
                                can_search_for_more_files = False
                                stop_reason = 'saw 100 previously seen urls in a row, so assuming this is a large gallery'
                                
                                break
                                
                            
                        else:
                            
                            num_urls_added += 1
                            current_contiguous_num_urls_already_in_file_seed_cache = 0
                            
                            file_seeds_to_add_in_this_sync.add( file_seed )
                            file_seeds_to_add_in_this_sync_ordered.append( file_seed )
                            
                        
                        if file_limit_for_this_sync is not None:
                            
                            if total_new_urls_for_this_sync + num_urls_added >= file_limit_for_this_sync:
                                
                                # we have found enough new files this sync, so should stop adding files and new gallery pages
                                
                                if this_is_initial_sync:
                                    
                                    stop_reason = 'hit initial file limit'
                                    
                                else:
                                    
                                    if total_already_in_urls_for_this_sync + num_urls_already_in_file_seed_cache > 0:
                                        
                                        # this sync produced some knowns, so it is likely we have stepped through a mix of old and tagged-late new files
                                        # this is no reason to go crying to the user
                                        
                                        stop_reason = 'hit periodic file limit after seeing several already-seen files'
                                        
                                    else:
                                        
                                        # this page had all entirely new files
                                        
                                        if self._this_is_a_random_sample_sub:
                                            
                                            stop_reason = 'hit periodic file limit'
                                            
                                        else:
                                            
                                            self._ShowHitPeriodicFileLimitMessage( query_name, query_text, file_limit_for_this_sync )
                                            
                                            stop_reason = 'hit periodic file limit without seeing any already-seen files!'
                                            
                                        
                                    
                                
                                can_search_for_more_files = False
                                
                                break
                                
                            
                        
                        if not this_is_initial_sync:
                            
                            # ok, there are a couple of situations where we don't want to go steamroll past a certain point:
                            
                            # if the user set 5 initial file limit but 100 periodic limit, then on the first few syncs, we'll want to notice that situation and not steamroll through that first five (or ~seven on third sync)
                            # if 'X' is new and get, 'A' is already in, and '-' is new and don't get, the page should be:
                            # XXXAAAAA----------------------------------
                            
                            # the pixiv situation, where a single gallery page may have hundreds of results (and/or multi-file results that will pad out the file cache with more items)
                            # super large gallery pages interfere with the compaction system, adding results that were removed again and making WE_HIT_OLD_GROUND_THRESHOLD test not work correct
                            # similar to above:
                            # XXXXAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
                            # AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
                            # AAAAAAAAAAAAAAAAAAAA-----------------------------------
                            # -------------------------------------------------------
                            # ----------------------
                            
                            # I had specific logic targeting both these cases, but in making those, I make the num_master_file_seeds_at_start, which is actually the better thing to test
                            # If the sub has seen basically everything it started with, we are by definition caught up and should stop immediately!
                            
                            excuse_the_odd_deleted_file_coefficient = 0.95
                            
                            # we found all the 'A's
                            we_have_seen_everything_we_already_got = total_already_in_urls_for_this_sync + num_urls_already_in_file_seed_cache >= num_master_file_seeds_at_start * excuse_the_odd_deleted_file_coefficient
                            
                            if we_have_seen_everything_we_already_got:
                                
                                stop_reason = 'saw everything I had previously (probably large gallery page or small recent initial sync), so assuming I caught up'
                                
                                can_search_for_more_files = False
                                
                                break
                                
                            
                        
                    
                    WE_HIT_OLD_GROUND_THRESHOLD = 5
                    
                    if can_search_for_more_files:
                        
                        if current_contiguous_num_urls_already_in_file_seed_cache >= WE_HIT_OLD_GROUND_THRESHOLD:
                            
                            # this gallery page has caught up to before, so it should not spawn any more gallery pages
                            
                            can_search_for_more_files = False
                            stop_reason = 'saw {} contiguous previously seen urls at end of page, so assuming we caught up'.format( HydrusData.ToHumanInt( current_contiguous_num_urls_already_in_file_seed_cache ) )
                            
                        
                        if num_urls_added == 0:
                            
                            can_search_for_more_files = False
                            stop_reason = 'no new urls found'
                            
                        
                    
                    return ( num_urls_added, num_urls_already_in_file_seed_cache, can_search_for_more_files, stop_reason )
                    
                
                job_key.SetVariable( 'popup_text_1', status_prefix + ': found ' + HydrusData.ToHumanInt( total_new_urls_for_this_sync ) + ' new urls, checking next page' )
                
                try:
                    
                    ( num_urls_added, num_urls_already_in_file_seed_cache, num_urls_total, result_404, added_new_gallery_pages, stop_reason ) = gallery_seed.WorkOnURL( 'subscription', gallery_seed_log, file_seeds_callable, status_hook, title_hook, query_header.GenerateNetworkJobFactory( self._name ), ClientImporting.GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key ), self._file_import_options, gallery_urls_seen_before = gallery_urls_seen_this_sync )
                    
                except HydrusExceptions.CancelledException as e:
                    
                    stop_reason = 'gallery network job cancelled, likely by user'
                    
                    self._DelayWork( 600, stop_reason )
                    
                    raise HydrusExceptions.CancelledException( 'User cancelled.' )
                    
                except Exception as e:
                    
                    stop_reason = str( e )
                    
                    raise
                    
                
                total_new_urls_for_this_sync += num_urls_added
                total_already_in_urls_for_this_sync += num_urls_already_in_file_seed_cache
                
                if file_limit_for_this_sync is not None and total_new_urls_for_this_sync >= file_limit_for_this_sync:
                    
                    # we have found enough new files this sync, so stop and cancel any outstanding gallery urls
                    
                    if this_is_initial_sync:
                        
                        stop_reason = 'hit initial file limit'
                        
                    else:
                        
                        stop_reason = 'hit periodic file limit'
                        
                    
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
                
                HydrusData.ShowText( 'The query "{}" for subscription "{}" did not find any files on its first sync! Could the query text have a typo, like a missing underscore?'.format( query_name, self._name ) )
                
            else:
                
                death_file_velocity = self._checker_options.GetDeathFileVelocity()
                
                ( death_files_found, death_time_delta ) = death_file_velocity
                
                HydrusData.ShowText( 'The query "{}" for subscription "{}" found fewer than {} files in the last {}, so it appears to be dead!'.format( query_name, self._name, HydrusData.ToHumanInt( death_files_found ), HydrusData.TimeDeltaToPrettyTimeDelta( death_time_delta ) ) )
                
            
        else:
            
            if this_is_initial_sync:
                
                if not query_header.FileBandwidthOK( HG.client_controller.network_engine.bandwidth_manager, self._name ) and not self._have_made_an_initial_sync_bandwidth_notification:
                    
                    HydrusData.ShowText( 'FYI: The query "{}" for subscription "{}" performed its initial sync ok, but it is short on bandwidth right now, so no files will be downloaded yet. The subscription will catch up in future as bandwidth becomes available. You can review the estimated time until bandwidth is available under the manage subscriptions dialog. If more queries are performing initial syncs in this run, they may be the same.'.format( query_name, self._name ) )
                    
                    self._have_made_an_initial_sync_bandwidth_notification = True
                    
                
            
        
    
    def _SyncQueryLogContainersCanDoWork( self ):
        
        result = True in ( query_header.WantsToResyncWithLogContainer() for query_header in self._query_headers )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "{}" checking if any log containers need to be resynced: {}'.format( self._name, result ) )
            
        
        return result
        
    
    def _SyncQueryLogContainers( self ):
        
        query_headers_to_do = [ query_header for query_header in self._query_headers if query_header.WantsToResyncWithLogContainer() ]
        
        for query_header in self._query_headers:
            
            if not query_header.WantsToResyncWithLogContainer():
                
                continue
                
            
            try:
                
                query_log_container = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, query_header.GetQueryLogContainerName() )
                
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
            
        
    
    def _WorkOnQueriesFiles( self, job_key ):
        
        self._file_error_count = 0
        
        query_headers = self._GetQueryHeadersForProcessing()
        
        query_headers = [ query_header for query_header in query_headers if query_header.HasFileWorkToDo() ]
        
        num_queries = len( query_headers )
        
        for ( i, query_header ) in enumerate( query_headers ):
            
            query_name = query_header.GetHumanName()
            
            text_1 = 'downloading files'
            query_summary_name = self._name
            
            if query_name != self._name:
                
                text_1 += ' for "' + query_name + '"'
                query_summary_name += ': ' + query_name
                
            
            text_1 += ' (' + HydrusData.ConvertValueRangeToPrettyString( i + 1, num_queries ) + ')'
            
            job_key.SetVariable( 'popup_text_1', text_1 )
            
            try:
                
                query_log_container = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LOG_CONTAINER, query_header.GetQueryLogContainerName() )
                
            except HydrusExceptions.DBException as e:
                
                if isinstance( e.db_e, HydrusExceptions.DataMissing ):
                    
                    self._DealWithMissingQueryLogContainerError( query_header )
                    
                    break
                    
                else:
                    
                    raise
                    
                
            
            try:
                
                self._WorkOnQueryFiles( job_key, query_header, query_log_container, query_summary_name )
                
            except HydrusExceptions.CancelledException:
                
                break
                
            finally:
                
                HG.client_controller.WriteSynchronous( 'serialisable', query_log_container )
                
            
        
        job_key.DeleteVariable( 'popup_files' )
        job_key.DeleteVariable( 'popup_text_1' )
        job_key.DeleteVariable( 'popup_text_2' )
        job_key.DeleteVariable( 'popup_gauge_2' )
        
    
    def _WorkOnQueriesFilesCanDoWork( self ):
        
        for query_header in self._query_headers:
            
            if not query_header.IsExpectingToWorkInFuture():
                
                continue
                
            
            if query_header.HasFileWorkToDo():
                
                bandwidth_ok = query_header.FileBandwidthOK( HG.client_controller.network_engine.bandwidth_manager, self._name )
                domain_ok = query_header.FileDomainOK( HG.client_controller.network_engine.domain_manager )
                
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
        job_key: ClientThreading.JobKey,
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
                        
                    
                    break
                    
                
                if job_key.IsCancelled():
                    
                    self._DelayWork( 300, 'recently cancelled' )
                    
                    break
                    
                
                p1 = not self._CanDoWorkNow()
                p3 = not query_header.FileDomainOK( HG.client_controller.network_engine.domain_manager )
                p4 = not query_header.FileBandwidthOK( HG.client_controller.network_engine.bandwidth_manager, self._name )
                ( login_ok, login_reason ) = query_header.FileLoginOK( HG.client_controller.network_engine, self._name )
                
                if p1 or p4 or not login_ok:
                    
                    if p3 and this_query_has_done_work:
                        
                        job_key.SetVariable( 'popup_text_2', 'domain had errors, will try again later' )
                        
                        self._DelayWork( 3600, 'domain errors, will try again later' )
                        
                        time.sleep( 5 )
                        
                    
                    if p4 and this_query_has_done_work:
                        
                        job_key.SetVariable( 'popup_text_2', 'no more bandwidth to download files, will do some more later' )
                        
                        time.sleep( 5 )
                        
                    
                    if not login_ok:
                        
                        if not self._paused:
                            
                            message = 'Query "{}" for subscription "{}" seemed to have an invalid login for one of its file imports. The reason was:'.format( query_header.GetHumanName(), self._name )
                            message += os.linesep * 2
                            message += login_reason
                            message += os.linesep * 2
                            message += 'The subscription has paused. Please see if you can fix the problem and then unpause. Hydrus dev would like feedback on this process.'
                            
                            HydrusData.ShowText( message )
                            
                            self._DelayWork( 300, login_reason )
                            
                            self._paused = True
                            
                        
                    
                    break
                    
                
                try:
                    
                    num_urls = file_seed_cache.GetFileSeedCount()
                    num_unknown = file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
                    num_done = num_urls - num_unknown
                    
                    # 4001/4003 is not as useful as 1/3
                    
                    human_num_urls = num_urls - starting_num_done
                    human_num_done = num_done - starting_num_done
                    
                    x_out_of_y = 'file ' + HydrusData.ConvertValueRangeToPrettyString( human_num_done + 1, human_num_urls ) + ': '
                    
                    job_key.SetVariable( 'popup_gauge_2', ( human_num_done, human_num_urls ) )
                    
                    def status_hook( text ):
                        
                        if len( text ) > 0:
                            
                            text = text.splitlines()[0]
                            
                        
                        job_key.SetVariable( 'popup_text_2', x_out_of_y + text )
                        
                    
                    file_seed.WorkOnURL( file_seed_cache, status_hook, query_header.GenerateNetworkJobFactory( self._name ), ClientImporting.GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key ), self._file_import_options, self._tag_import_options )
                    
                    query_tag_import_options = query_header.GetTagImportOptions()
                    
                    if query_tag_import_options.HasAdditionalTags() and file_seed.status in CC.SUCCESSFUL_IMPORT_STATES:
                        
                        if file_seed.HasHash():
                            
                            hash = file_seed.GetHash()
                            
                            media_result = HG.client_controller.Read( 'media_result', hash )
                            
                            downloaded_tags = []
                            
                            service_keys_to_content_updates = query_tag_import_options.GetServiceKeysToContentUpdates( file_seed.status, media_result, downloaded_tags ) # additional tags
                            
                            if len( service_keys_to_content_updates ) > 0:
                                
                                HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                                
                            
                        
                    
                    if file_seed.ShouldPresent( self._file_import_options.GetPresentationImportOptions() ):
                        
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
                    
                    job_key.SetVariable( 'popup_text_2', x_out_of_y + 'file failed' )
                    
                    file_seed.SetStatus( status, exception = e )
                    
                    if isinstance( e, HydrusExceptions.DataMissing ):
                        
                        # DataMissing is a quick thing to avoid subscription abandons when lots of deleted files in e621 (or any other booru)
                        # this should be richer in any case in the new system
                        
                        pass
                        
                    else:
                        
                        self._file_error_count += 1
                        
                        time.sleep( 5 )
                        
                    
                    error_count_threshold = HG.client_controller.new_options.GetNoneableInteger( 'subscription_file_error_cancel_threshold' )
                    
                    if error_count_threshold is not None and self._file_error_count >= error_count_threshold:
                        
                        raise Exception( 'The subscription ' + self._name + ' encountered several errors when downloading files, so it abandoned its sync.' )
                        
                    
                
                this_query_has_done_work = True
                
                if len( presentation_hashes ) > 0:
                    
                    job_key.SetVariable( 'popup_files', ( list( presentation_hashes ), query_summary_name ) )
                    
                else:
                    
                    # although it is nice to have the file popup linger a little once a query is done, if the next query has 15 'already in db', it has outstayed its welcome
                    job_key.DeleteVariable( 'popup_files' )
                    
                
                time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
                
                HG.client_controller.WaitUntilViewFree()
                
            
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
        
        return not HydrusData.TimeHasPassed( self._no_work_until )
        
    
    def CheckNow( self ):
        
        for query_header in self._query_headers:
            
            query_header.CheckNow()
            
        
        self.ScrubDelay()
        
    
    def DedupeQueryTexts( self, dedupe_query_texts: typing.Iterable[ str ], enforce_case: bool = True ):
        
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
        
    
    def GetAllQueryLogContainerNames( self ) -> typing.Set[ str ]:
        
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
            
            next_work_time = query_header.GetNextWorkTime( HG.client_controller.network_engine.bandwidth_manager, self._name )
            
            if next_work_time is not None:
                
                next_work_times.add( next_work_time )
                
            
        
        if len( next_work_times ) == 0:
            
            return None
            
        
        best_next_work_time = min( next_work_times )
        
        if not HydrusData.TimeHasPassed( self._no_work_until ):
            
            best_next_work_time = max( ( best_next_work_time, self._no_work_until ) )
            
        
        return best_next_work_time
        
    
    def GetCheckerOptions( self ):
        
        return self._checker_options
        
    
    def GetGUGKeyAndName( self ):
        
        return self._gug_key_and_name
        
    
    def GetQueryHeaders( self ) -> typing.List[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ]:
        
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
        
    
    def LowerCaseQueries( self ):
        
        for query_header in self._query_headers:
            
            query_text = query_header.GetQueryText()
            query_text_lower = query_text.lower()
            
            if query_text != query_text_lower:
                
                query_header.SetQueryText( query_text_lower )
                
            
        
    
    def Merge( self, mergees: typing.Iterable[ "Subscription" ] ):
        
        unmerged = []
        
        for subscription in mergees:
            
            if subscription.GetGUGKeyAndName()[1] == self._gug_key_and_name[1]:
                
                self._query_headers.extend( subscription.GetQueryHeaders() )
                
                subscription.SetQueryHeaders( [] )
                
            else:
                
                unmerged.append( subscription )
                
            
        
        return unmerged
        
    
    def PauseResume( self ):
        
        self._paused = not self._paused
        
    
    def RemoveQueryTexts( self, removee_query_texts: typing.Iterable[ str ], enforce_case: bool = True ):
        
        if not enforce_case:
            
            removee_query_texts = { query_text.lower() for query_text in removee_query_texts }
            
        
        if enforce_case:
            
            self._query_headers = [ query_header for query_header in self._query_headers if query_header.GetQueryText() not in removee_query_texts ]
            
        else:
            
            self._query_headers = [ query_header for query_header in self._query_headers if query_header.GetQueryText().lower() not in removee_query_texts ]
            
        
    
    def Reset( self ):
        
        for query_header in self._query_headers:
            
            query_header.Reset()
            
        
        self.ScrubDelay()
        
    
    def RetryFailed( self ):
        
        for query_header in self._query_headers:
            
            query_header.RetryFailed()
            
        
    
    def RetryIgnored( self, ignored_regex = None ):
        
        for query_header in self._query_headers:
            
            query_header.RetryIgnored( ignored_regex = ignored_regex )
            
        
    
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
                        
                    
                
                query_header.SetQueryLogContainerStatus( ClientImportSubscriptionQuery.LOG_CONTAINER_UNSYNCED, pretty_velocity_override = 'will recalculate on next run' )
                
            
        
    
    def SetPresentationOptions( self, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events ):
        
        self._show_a_popup_while_working = show_a_popup_while_working
        self._publish_files_to_popup_button = publish_files_to_popup_button
        self._publish_files_to_page = publish_files_to_page
        self._publish_label_override = publish_label_override
        self._merge_query_publish_events = merge_query_publish_events
        
    
    def SetQueryHeaders( self, query_headers: typing.Iterable[ ClientImportSubscriptionQuery.SubscriptionQueryHeader ] ):
        
        self._query_headers = list( query_headers )
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options.Duplicate()
        
    
    def SetThisIsARandomSampleSubscription( self, value: bool ):
        
        self._this_is_a_random_sample_sub = value
        
    
    def SetTuple( self, gug_key_and_name, checker_options: ClientImportOptions.CheckerOptions, initial_file_limit, periodic_file_limit, paused, file_import_options: FileImportOptions.FileImportOptions, tag_import_options: TagImportOptions.TagImportOptions, no_work_until ):
        
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
                
            except Exception as e:
                
                HydrusData.ShowText( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.ShowException( e )
                
                self._paused = True
                
                self._DelayWork( 300, 'error: {}'.format( str( e ) ) )
                
                return
                
            
        
        sync_work_to_do = self._SyncQueriesCanDoWork()
        files_work_to_do = self._WorkOnQueriesFilesCanDoWork()
        
        if self._CanDoWorkNow() and ( sync_work_to_do or files_work_to_do ):
            
            job_key = ClientThreading.JobKey( pausable = False, cancellable = True )
            
            try:
                
                job_key.SetStatusTitle( 'subscriptions - ' + self._name )
                
                if self._show_a_popup_while_working:
                    
                    HG.client_controller.pub( 'message', job_key )
                    
                
                # it is possible a query becomes due for a check while others are syncing, so we repeat this while watching for a stop signal
                while self._CanDoWorkNow() and self._SyncQueriesCanDoWork():
                    
                    self._SyncQueries( job_key )
                    
                
                self._WorkOnQueriesFiles( job_key )
                
            except HydrusExceptions.NetworkException as e:
                
                delay = HG.client_controller.new_options.GetInteger( 'subscription_network_error_delay' )
                
                HydrusData.Print( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                
                HydrusData.Print( e )
                
                job_key.SetVariable( 'popup_text_1', 'Encountered a network error, will retry again later' )
                
                self._DelayWork( delay, 'network error: ' + str( e ) )
                
                time.sleep( 5 )
                
            except Exception as e:
                
                HydrusData.ShowText( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.ShowException( e )
                
                delay = HG.client_controller.new_options.GetInteger( 'subscription_other_error_delay' )
                
                self._DelayWork( delay, 'error: ' + str( e ) )
                
            finally:
                
                job_key.DeleteNetworkJob()
                
            
            if job_key.HasVariable( 'popup_files' ):
                
                job_key.Finish()
                
            else:
                
                job_key.Delete()
                
            
        
    
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
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
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
    
    def __init__( self, controller, subscription ):
        
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
            
        
    
class SubscriptionsManager( object ):
    
    def __init__( self, controller, subscriptions: typing.List[ Subscription ] ):
        
        self._controller = controller
        
        self._names_to_subscriptions = { subscription.GetName() : subscription for subscription in subscriptions }
        self._names_to_running_subscription_info = {}
        self._names_that_cannot_run = set()
        self._names_to_next_work_time = {}
        
        self._lock = threading.Lock()
        
        self._shutdown = False
        self._mainloop_finished = False
        
        self._pause_subscriptions_for_editing = False
        
        self._wake_event = threading.Event()
        
        self._big_pauser = HydrusData.BigJobPauser( wait_time = 0.8 )
        
        self._controller.sub( self, 'Shutdown', 'shutdown' )
        self._controller.sub( self, 'Wake', 'notify_network_traffic_unpaused' )
        
    
    def _ClearFinishedSubscriptions( self ):
        
        done_some = False
        
        for ( name, ( job, subscription ) ) in list( self._names_to_running_subscription_info.items() ):
            
            if job.IsDone():
                
                self._UpdateSubscriptionInfo( subscription, just_finished_work = True )
                
                del self._names_to_running_subscription_info[ name ]
                
                done_some = True
                
            
        
    
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
        
        p1 = HG.client_controller.options[ 'pause_subs_sync' ] or self._pause_subscriptions_for_editing
        p2 = HG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
        p3 = HG.view_shutdown
        
        if p1 or p2 or p3:
            
            return None
            
        
        max_simultaneous_subscriptions = HG.client_controller.new_options.GetInteger( 'max_simultaneous_subscriptions' )
        
        if len( self._names_to_running_subscription_info ) >= max_simultaneous_subscriptions:
            
            return None
            
        
        possible_names = set( self._names_to_subscriptions.keys() )
        possible_names.difference_update( set( self._names_to_running_subscription_info.keys() ) )
        possible_names.difference_update( self._names_that_cannot_run )
        
        # just a couple of seconds for calculation and human breathing room
        SUB_WORK_DELAY_BUFFER = 3
        
        names_not_due = { name for ( name, next_work_time ) in self._names_to_next_work_time.items() if not HydrusData.TimeHasPassed( next_work_time + SUB_WORK_DELAY_BUFFER ) }
        
        possible_names.difference_update( names_not_due )
        
        if len( possible_names ) == 0:
            
            return None
            
        
        possible_names = list( possible_names )
        
        if HG.client_controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
            
            subscription_name = random.choice( possible_names )
            
        else:
            
            possible_names.sort()
            
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
                
                p1 = HG.client_controller.options[ 'pause_subs_sync' ] or self._pause_subscriptions_for_editing
                p2 = HG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
                
                stopped_because_pause = p1 or p2
                
                if just_finished_work and not stopped_because_pause:
                    
                    # even with the new data format, we don't want to have a load/save cycle repeating _too_ much, just to stop any weird cascades
                    # this sets min resolution of a single sub repeat cycle
                    BUFFER_TIME = 120
                    
                    next_work_time = max( next_work_time, HydrusData.GetNow() + BUFFER_TIME )
                    
                
                self._names_to_next_work_time[ name ] = next_work_time
                
            
        
    
    def GetSubscriptions( self ) -> typing.List[ Subscription ]:
        
        with self._lock:
            
            return list( self._names_to_subscriptions.values() )
            
        
    
    def IsShutdown( self ):
        
        return self._mainloop_finished
        
    
    def MainLoop( self ):
        
        try:
            
            self._wake_event.wait( 3 )
            
            while not ( HG.view_shutdown or self._shutdown ):
                
                with self._lock:
                    
                    subscription = self._GetSubscriptionReadyToGo()
                    
                    if subscription is not None:
                        
                        job = SubscriptionJob( self._controller, subscription )
                        
                        HG.client_controller.CallToThread( job.Work )
                        
                        self._names_to_running_subscription_info[ subscription.GetName() ] = ( job, subscription )
                        
                    
                    self._ClearFinishedSubscriptions()
                    
                    wait_time = self._GetMainLoopWaitTime()
                    
                
                self._big_pauser.Pause()
                
                self._wake_event.wait( wait_time )
                
                self._wake_event.clear()
                
            
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
                    
                
            
            self._mainloop_finished = True
            
        
    
    def ResumeSubscriptionsAfterEditing( self ):
        
        with self._lock:
            
            self._pause_subscriptions_for_editing = False
            
        
    
    def PauseSubscriptionsForEditing( self ):
        
        with self._lock:
            
            self._pause_subscriptions_for_editing = True
            
        
    
    def SetSubscriptions( self, subscriptions ):
        
        with self._lock:
            
            self._names_to_subscriptions = { subscription.GetName() : subscription for subscription in subscriptions }
            
            self._names_that_cannot_run = set()
            self._names_to_next_work_time = {}
            
            for subscription in subscriptions:
                
                self._UpdateSubscriptionInfo( subscription )
                
            
            self._wake_event.set()
            
        
    
    def ShowSnapshot( self ):
        
        with self._lock:
            
            sub_names = sorted( self._names_to_subscriptions.keys() )
            
            running = sorted( self._names_to_running_subscription_info.keys() )
            
            cannot_run = sorted( self._names_that_cannot_run )
            
            next_times = sorted( self._names_to_next_work_time.items(), key = lambda n_nwt_tuple: n_nwt_tuple[1] )
            
            message = '{} subs: {}'.format( HydrusData.ToHumanInt( len( self._names_to_subscriptions ) ), ', '.join( sub_names ) )
            message += os.linesep * 2
            message += '{} running: {}'.format( HydrusData.ToHumanInt( len( self._names_to_running_subscription_info ) ), ', '.join( running ) )
            message += os.linesep * 2
            message += '{} not runnable: {}'.format( HydrusData.ToHumanInt( len( self._names_that_cannot_run ) ), ', '.join( cannot_run ) )
            message += os.linesep * 2
            message += '{} next times: {}'.format( HydrusData.ToHumanInt( len( self._names_to_next_work_time ) ), ', '.join( ( '{}: {}'.format( name, ClientData.TimestampToPrettyTimeDelta( next_work_time ) ) for ( name, next_work_time ) in next_times ) ) )
            
            HydrusData.ShowText( message )
            
        
    
    def Shutdown( self ):
        
        self._shutdown = True
        
        self.PauseSubscriptionsForEditing()
        
        self._wake_event.set()
        
    
    def Start( self ):
        
        self._controller.CallToThreadLongRunning( self.MainLoop )
        
    
    def SubscriptionsArePausedForEditing( self ):
        
        with self._lock:
            
            return self._pause_subscriptions_for_editing
            
        
    
    def SubscriptionsRunning( self ):
        
        with self._lock:
            
            self._ClearFinishedSubscriptions()
            
            return len( self._names_to_running_subscription_info ) > 0
            
        
    
    def Wake( self ):
        
        self._wake_event.set()
        
    
