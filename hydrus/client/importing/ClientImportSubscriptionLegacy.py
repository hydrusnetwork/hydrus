import collections.abc
import random

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime
from hydrus.core.processes import HydrusThreading

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDownloading
from hydrus.client import ClientGlobals as CG
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing import ClientImportSubscriptions
from hydrus.client.importing import ClientImportSubscriptionQuery
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing.options import TagImportOptionsLegacy
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingJobs

# this object is no longer used, it exists only to update to the new objects below
class SubscriptionQueryLegacy( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LEGACY
    SERIALISABLE_NAME = 'Legacy Subscription Query'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, query = 'query text' ):
        
        super().__init__()
        
        self._query = query
        self._display_name = None
        self._check_now = False
        self._last_check_time = 0
        self._next_check_time = 0
        self._paused = False
        self._status = ClientImporting.CHECKER_STATUS_OK
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        self._tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy()
        
    
    def _GetExampleNetworkContexts( self, subscription_name ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        subscription_key = self.GetNetworkJobSubscriptionKey( subscription_name )
        
        if file_seed is None:
            
            return [ ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, subscription_key ), ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
            
        
        url = file_seed.file_seed_data
        
        try: # if the url is borked for some reason
            
            example_nj = ClientNetworkingJobs.NetworkJobSubscription( subscription_key, 'GET', url )
            example_network_contexts = example_nj.GetNetworkContexts()
            
        except Exception as e:
            
            return [ ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, subscription_key ), ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
            
        
        return example_network_contexts
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( self._query, self._display_name, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_tag_import_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._query, self._display_name, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_tag_import_options ) = serialisable_info
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_file_seed_cache ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache ) = old_serialisable_info
            
            display_name = None
            tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy()
            
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( query, display_name, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_tag_import_options )
            
            return ( 3, new_serialisable_info )
            
        
    
    def BandwidthOK( self, subscription_name ):
        
        example_network_contexts = self._GetExampleNetworkContexts( subscription_name )
        
        threshold = 90
        
        bandwidth_ok = CG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_network_contexts, threshold = threshold )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self.GetHumanName() + '" bandwidth/domain test. Bandwidth ok: {}'.format( bandwidth_ok ) )
            
        
        return bandwidth_ok
        
    
    def CanCheckNow( self ):
        
        return not self._check_now
        
    
    def CanRetryFailed( self ):
        
        return self._file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR ) > 0
        
    
    def CanRetryIgnored( self ):
        
        return self._file_seed_cache.GetFileSeedCount( CC.STATUS_VETOED ) > 0
        
    
    def CheckNow( self ):
        
        self._check_now = True
        self._paused = False
        
        self._next_check_time = 0
        self._status = ClientImporting.CHECKER_STATUS_OK
        
    
    def DomainOK( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            return True
            
        
        url = file_seed.file_seed_data
        
        domain_ok = CG.client_controller.network_engine.domain_manager.DomainOK( url )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self.GetHumanName() + '" domain test. Domain ok: {}'.format( domain_ok ) )
            
        
        return domain_ok
        
    
    def GetBandwidthWaitingEstimate( self, subscription_name ):
        
        example_network_contexts = self._GetExampleNetworkContexts( subscription_name )
        
        ( estimate, bandwidth_network_context ) = CG.client_controller.network_engine.bandwidth_manager.GetWaitingEstimateAndContext( example_network_contexts )
        
        return estimate
        
    
    def GetDisplayName( self ):
        
        return self._display_name
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def GetHumanName( self ):
        
        if self._display_name is None:
            
            return self._query
            
        else:
            
            return self._display_name
            
        
    
    def GetLastCheckTime( self ):
        
        return self._last_check_time
        
    
    def GetLatestAddedTime( self ):
        
        return self._file_seed_cache.GetStatus().GetLatestAddedTime()
        
    
    def GetNextCheckStatusString( self ):
        
        if self._check_now:
            
            return 'checking on dialog ok'
            
        elif self._status == ClientImporting.CHECKER_STATUS_DEAD:
            
            return 'dead, so not checking'
            
        else:
            
            if HydrusTime.TimeHasPassed( self._next_check_time ):
                
                s = 'imminent'
                
            else:
                
                s = HydrusTime.TimestampToPrettyTimeDelta( self._next_check_time )
                
            
            if self._paused:
                
                s = 'paused, but would be ' + s
                
            
            return s
            
        
    
    def GetNextWorkTime( self, subscription_name ):
        
        if self.IsPaused():
            
            return None
            
        
        work_times = set()
        
        if self.HasFileWorkToDo():
            
            try:
                
                file_bandwidth_estimate = self.GetBandwidthWaitingEstimate( subscription_name )
                
            except Exception as e:
                
                # this is tricky, but if there is a borked url in here causing trouble, we should let it run and error out immediately tbh
                
                file_bandwidth_estimate = 0
                
            
            if file_bandwidth_estimate == 0:
                
                work_times.add( 0 )
                
            else:
                
                file_work_time = HydrusTime.GetNow() + file_bandwidth_estimate
                
                work_times.add( file_work_time )
                
            
        
        if not self.IsDead():
            
            work_times.add( self._next_check_time )
            
        
        if len( work_times ) == 0:
            
            return None
            
        
        return min( work_times )
        
    
    def GetNetworkJobSubscriptionKey( self, subscription_name ):
        
        return subscription_name + ': ' + self.GetHumanName()
        
    
    def GetQueryText( self ):
        
        return self._query
        
    
    def GetTagImportOptions( self ):
        
        return self._tag_import_options
        
    
    def HasFileWorkToDo( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._query + '" HasFileWorkToDo test. Next import is ' + repr( file_seed ) + '.' )
            
        
        return file_seed is not None
        
    
    def IsDead( self ):
        
        return self._status == ClientImporting.CHECKER_STATUS_DEAD
        
    
    def IsInitialSync( self ):
        
        return self._last_check_time == 0
        
    
    def IsPaused( self ):
        
        return self._paused
        
    
    def IsSyncDue( self ):
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._query + '" IsSyncDue test. Paused/dead status is {}/{}, check time due is {}, and check_now is {}.'.format( self._paused, self.IsDead(), HydrusTime.TimeHasPassed( self._next_check_time ), self._check_now ) )
            
        
        if self._paused or self.IsDead():
            
            return False
            
        
        return HydrusTime.TimeHasPassed( self._next_check_time ) or self._check_now
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def RegisterSyncComplete( self, checker_options: ClientImportOptions.CheckerOptions ):
        
        self._last_check_time = HydrusTime.GetNow()
        
        self._check_now = False
        
        death_period = checker_options.GetDeathFileVelocityPeriod()
        
        compact_before_this_time = self._last_check_time - death_period
        
        if self._gallery_seed_log.CanCompact( compact_before_this_time ):
            
            self._gallery_seed_log.Compact( 100, compact_before_this_time )
            
        
        if self._file_seed_cache.CanCompact( compact_before_this_time ):
            
            self._file_seed_cache.Compact( 250, compact_before_this_time )
            
        
    
    def Reset( self ):
        
        self._last_check_time = 0
        self._next_check_time = 0
        self._status = ClientImporting.CHECKER_STATUS_OK
        self._paused = False
        
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
    
    def RetryFailed( self ):
        
        self._file_seed_cache.RetryFailed()    
        
    
    def RetryIgnored( self ):
        
        self._file_seed_cache.RetryIgnored()    
        
    
    def SetCheckNow( self, check_now ):
        
        self._check_now = check_now
        
    
    def SetDisplayName( self, display_name ):
        
        self._display_name = display_name
        
    
    def SetPaused( self, paused ):
        
        self._paused = paused
        
    
    def SetQueryAndSeeds( self, query, file_seed_cache, gallery_seed_log ):
        
        self._query = query
        self._file_seed_cache = file_seed_cache
        self._gallery_seed_log = gallery_seed_log
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options
        
    
    def UpdateNextCheckTime( self, checker_options: ClientImportOptions.CheckerOptions ):
        
        if self._check_now:
            
            self._next_check_time = 0
            
            self._status = ClientImporting.CHECKER_STATUS_OK
            
        else:
            
            if checker_options.IsDead( self._file_seed_cache, self._last_check_time ):
                
                self._status = ClientImporting.CHECKER_STATUS_DEAD
                
                if not self.HasFileWorkToDo():
                    
                    self._paused = True
                    
                
            
            self._next_check_time = checker_options.GetNextCheckTime( self._file_seed_cache, self._last_check_time )
            
        
    
    def ToTuple( self ):
        
        return ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LEGACY ] = SubscriptionQueryLegacy

class SubscriptionLegacy( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_LEGACY
    SERIALISABLE_NAME = 'Legacy Subscription'
    SERIALISABLE_VERSION = 10
    
    def __init__( self, name, gug_key_and_name = None ):
        
        super().__init__( name )
        
        if gug_key_and_name is None:
            
            gug_key_and_name = ( HydrusData.GenerateKey(), 'unknown source' )
            
        
        self._gug_key_and_name = gug_key_and_name
        
        self._queries = []
        
        new_options = CG.client_controller.new_options
        
        self._checker_options = new_options.GetDefaultSubscriptionCheckerOptions()
        
        if HC.options[ 'gallery_file_limit' ] is None:
            
            self._initial_file_limit = 100
            
        else:
            
            self._initial_file_limit = min( 100, HC.options[ 'gallery_file_limit' ] )
            
        
        self._periodic_file_limit = 100
        self._paused = False
        
        self._file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        self._file_import_options.SetIsDefault( True )
        
        self._tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( is_default = True )
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        self._show_a_popup_while_working = True
        self._publish_files_to_popup_button = True
        self._publish_files_to_page = False
        self._publish_label_override = None
        self._merge_query_publish_events = True
        
    
    def _CanDoWorkNow( self ):
        
        p1 = not ( self._paused or CG.client_controller.new_options.GetBoolean( 'pause_subs_sync' ) or CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ) )
        p2 = not ( HG.started_shutdown or HydrusThreading.IsThreadShuttingDown() )
        p3 = self._NoDelays()
        
        if HG.subscription_report_mode:
            
            message = 'Subscription "{}" CanDoWork check.'.format( self._name )
            message += '\n'
            message += 'Paused/Global/Network Pause: {}/{}/{}'.format( self._paused, CG.client_controller.new_options.GetBoolean( 'pause_subs_sync' ), CG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ) )
            message += '\n'
            message += 'Started/Thread shutdown: {}/{}'.format( HG.started_shutdown, HydrusThreading.IsThreadShuttingDown() )
            message += '\n'
            message += 'No delays: {}'.format( self._NoDelays() )
            
            HydrusData.ShowText( message )
            
        
        return p1 and p2 and p3
        
    
    def _DelayWork( self, time_delta, reason ):
        
        if len( reason ) > 0:
            
            reason = reason.splitlines()[0]
            
        
        self._no_work_until = HydrusTime.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _GetPublishingLabel( self, query ):
        
        if self._publish_label_override is None:
            
            label = self._name
            
        else:
            
            label = self._publish_label_override
            
        
        if not self._merge_query_publish_events:
            
            label += ': ' + query.GetHumanName()
            
        
        return label
        
    
    def _GetQueriesForProcessing( self ) -> list[ SubscriptionQueryLegacy ]:
        
        queries = list( self._queries )
        
        if CG.client_controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
            
            random.shuffle( queries )
            
        else:
            
            def key( q ):
                
                return q.GetHumanName()
                
            
            queries.sort( key = key )
            
        
        return queries
        
    
    def _GetSerialisableInfo( self ):
        
        ( gug_key, gug_name ) = self._gug_key_and_name
        
        serialisable_gug_key_and_name = ( gug_key.hex(), gug_name )
        serialisable_queries = [ query.GetSerialisableTuple() for query in self._queries ]
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_import_options, serialisable_tag_import_options, self._no_work_until, self._no_work_until_reason, self._show_a_popup_while_working, self._publish_files_to_popup_button, self._publish_files_to_page, self._publish_label_override, self._merge_query_publish_events )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_import_options, serialisable_tag_import_options, self._no_work_until, self._no_work_until_reason, self._show_a_popup_while_working, self._publish_files_to_popup_button, self._publish_files_to_page, self._publish_label_override, self._merge_query_publish_events ) = serialisable_info
        
        ( serialisable_gug_key, gug_name ) = serialisable_gug_key_and_name
        
        self._gug_key_and_name = ( bytes.fromhex( serialisable_gug_key ), gug_name )
        self._queries = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_query ) for serialisable_query in serialisable_queries ]
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _GenerateNetworkJobFactory( self, query ):
        
        subscription_key = query.GetNetworkJobSubscriptionKey( self._name )
        
        def network_job_factory( *args, **kwargs ):
            
            network_job = ClientNetworkingJobs.NetworkJobSubscription( subscription_key, *args, **kwargs )
            
            network_job.OverrideBandwidth( 30 )
            
            return network_job
            
        
        return network_job_factory
        
    
    def _NoDelays( self ):
        
        return HydrusTime.TimeHasPassed( self._no_work_until )
        
    
    def _QueryFileLoginOK( self, query ):
        
        file_seed_cache = query.GetFileSeedCache()
        
        file_seed = file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            result = True
            
        else:
            
            nj = file_seed.GetExampleNetworkJob( self._GenerateNetworkJobFactory( query ) )
            
            nj.engine = CG.client_controller.network_engine
            
            if nj.CurrentlyNeedsLogin():
                
                try:
                    
                    nj.CheckCanLogin()
                    
                    result = True
                    
                except Exception as e:
                    
                    result = False
                    
                    if not self._paused:
                        
                        login_fail_reason = str( e )
                        
                        message = 'Query "' + query.GetHumanName() + '" for subscription "' + self._name + '" seemed to have an invalid login for one of its file imports. The reason was:'
                        message += '\n' * 2
                        message += login_fail_reason
                        message += '\n' * 2
                        message += 'The subscription has paused. Please see if you can fix the problem and then unpause. If the login script stopped because of missing cookies or similar, it may be broken. Please check out Hydrus Companion for a better login solution.'
                        
                        HydrusData.ShowText( message )
                        
                        self._DelayWork( 300, login_fail_reason )
                        
                        self._paused = True
                        
                    
                
            else:
                
                result = True
                
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + query.GetHumanName() + '" pre-work file login test. Login ok: ' + str( result ) + '.' )
            
        
        return result
        
    
    def _QuerySyncLoginOK( self, query ):
        
        gallery_seed_log = query.GetGallerySeedLog()
        
        gallery_seed = gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
        
        if gallery_seed is None:
            
            result = True
            
        else:
            
            nj = gallery_seed.GetExampleNetworkJob( self._GenerateNetworkJobFactory( query ) )
            
            nj.engine = CG.client_controller.network_engine
            
            if nj.CurrentlyNeedsLogin():
                
                try:
                    
                    nj.CheckCanLogin()
                    
                    result = True
                    
                except Exception as e:
                    
                    result = False
                    
                    if not self._paused:
                        
                        login_fail_reason = str( e )
                        
                        message = 'Query "' + query.GetHumanName() + '" for subscription "' + self._name + '" seemed to have an invalid login. The reason was:'
                        message += '\n' * 2
                        message += login_fail_reason
                        message += '\n' * 2
                        message += 'The subscription has paused. Please see if you can fix the problem and then unpause. If the login script stopped because of missing cookies or similar, it may be broken. Please check out Hydrus Companion for a better login solution.'
                        
                        HydrusData.ShowText( message )
                        
                        self._DelayWork( 300, login_fail_reason )
                        
                        self._paused = True
                        
                    
                
            else:
                
                result = True
                
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + query.GetHumanName() + '" pre-work sync login test. Login ok: ' + str( result ) + '.' )
            
        
        return result
        
    
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
            
            checker_options = ClientImportOptions.CheckerOptions( 5, period // 5, period * 10, ( 1, period * 10 ) )
            
            file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
            
            query = SubscriptionQueryLegacy( query )
            
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
            
        
        if version == 7:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events ) = old_serialisable_info
            
            gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
            
            ( gug_key, gug_name ) = ClientDownloading.ConvertGalleryIdentifierToGUGKeyAndName( gallery_identifier )
            
            serialisable_gug_key_and_name = ( gug_key.hex(), gug_name )
            
            new_serialisable_info = ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events ) = old_serialisable_info
            
            show_a_popup_while_working = True
            
            new_serialisable_info = ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events )
            
            return ( 9, new_serialisable_info )
            
        
        if version == 9:
            
            ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events ) = old_serialisable_info
            
            publish_label_override = None
            
            new_serialisable_info = ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events )
            
            return ( 10, new_serialisable_info )
            
        
    
    def AllPaused( self ):
        
        if self._paused:
            
            return True
            
        
        for query in self._queries:
            
            if not query.IsPaused():
                
                return False
                
            
        
        return True
        
    
    def CanCheckNow( self ):
        
        return True in ( query.CanCheckNow() for query in self._queries )
        
    
    def CanReset( self ):
        
        return True in ( not query.IsInitialSync() for query in self._queries )
        
    
    def CanRetryFailed( self ):
        
        return True in ( query.CanRetryFailed() for query in self._queries )
        
    
    def CanRetryIgnored( self ):
        
        return True in ( query.CanRetryIgnored() for query in self._queries )
        
    
    def CanScrubDelay( self ):
        
        return not HydrusTime.TimeHasPassed( self._no_work_until )
        
    
    def CheckNow( self ):
        
        for query in self._queries:
            
            query.CheckNow()
            
        
        self.ScrubDelay()
        
    
    def GetBandwidthWaitingEstimateMinMax( self ):
        
        if len( self._queries ) == 0:
            
            return ( 0, 0 )
            
        
        estimates = []
        
        for query in self._queries:
            
            estimate = query.GetBandwidthWaitingEstimate( self._name )
            
            estimates.append( estimate )
            
        
        min_estimate = min( estimates )
        max_estimate = max( estimates )
        
        return ( min_estimate, max_estimate )
        
    
    def GetBestEarliestNextWorkTime( self ):
        
        next_work_times = set()
        
        for query in self._queries:
            
            next_work_time = query.GetNextWorkTime( self._name )
            
            if next_work_time is not None:
                
                next_work_times.add( next_work_time )
                
            
        
        if len( next_work_times ) == 0:
            
            return None
            
        
        # if there are three queries due fifty seconds after our first one runs, we should wait that little bit longer
        LAUNCH_WINDOW = 15 * 60
        
        earliest_next_work_time = min( next_work_times )
        
        latest_nearby_next_work_time = max( ( work_time for work_time in next_work_times if work_time < earliest_next_work_time + LAUNCH_WINDOW ) )
        
        # but if we are expecting to launch it right now (e.g. check_now call), we won't wait
        if HydrusTime.TimeUntil( earliest_next_work_time ) < 60:
            
            best_next_work_time = earliest_next_work_time
            
        else:
            
            best_next_work_time = latest_nearby_next_work_time
            
        
        if not HydrusTime.TimeHasPassed( self._no_work_until ):
            
            best_next_work_time = max( ( best_next_work_time, self._no_work_until ) )
            
        
        return best_next_work_time
        
    
    def GetCheckerOptions( self ):
        
        return self._checker_options
        
    
    def GetGUGKeyAndName( self ):
        
        return self._gug_key_and_name
        
    
    def GetQueries( self ) -> list[ SubscriptionQueryLegacy ]:
        
        return self._queries
        
    
    def GetMergeable( self, potential_mergees ):
        
        mergeable = []
        unmergeable = []
        
        for subscription in potential_mergees:
            
            if subscription._gug_key_and_name[1] == self._gug_key_and_name[1]:
                
                mergeable.append( subscription )
                
            else:
                
                unmergeable.append( subscription )
                
            
        
        return ( mergeable, unmergeable )
        
    
    def GetPresentationOptions( self ):
        
        return ( self._show_a_popup_while_working, self._publish_files_to_popup_button, self._publish_files_to_page, self._publish_label_override, self._merge_query_publish_events )
        
    
    def GetTagImportOptions( self ):
        
        return self._tag_import_options
        
    
    def HasQuerySearchTextFragment( self, search_text_fragment ):
        
        for query in self._queries:
            
            query_text = query.GetQueryText()
            
            if search_text_fragment in query_text:
                
                return True
                
            
        
        return False
        
    
    def Merge( self, mergees ):
        
        for subscription in mergees:
            
            if subscription._gug_key_and_name[1] == self._gug_key_and_name[1]:
                
                my_new_queries = [ query.Duplicate() for query in subscription._queries ]
                
                self._queries.extend( my_new_queries )
                
            else:
                
                raise Exception( self._name + ' was told to merge an unmergeable subscription, ' + subscription.GetName() + '!' )
                
            
        
    
    def PauseResume( self ):
        
        self._paused = not self._paused
        
    
    def Reset( self ):
        
        for query in self._queries:
            
            query.Reset()
            
        
        self.ScrubDelay()
        
    
    def RetryFailed( self ):
        
        for query in self._queries:
            
            query.RetryFailed()
            
        
    
    def RetryIgnored( self ):
        
        for query in self._queries:
            
            query.RetryIgnored()
            
        
    
    def Separate( self, base_name, only_these_queries = None ):
        
        if only_these_queries is None:
            
            only_these_queries = set( self._queries )
            
        else:
            
            only_these_queries = set( only_these_queries )
            
        
        my_queries = self._queries
        
        self._queries = []
        
        base_sub = self.Duplicate()
        
        self._queries = my_queries
        
        subscriptions = []
        
        for query in my_queries:
            
            if query not in only_these_queries:
                
                continue
                
            
            subscription = base_sub.Duplicate()
            
            subscription._queries = [ query ]
            
            subscription.SetName( base_name + ': ' + query.GetHumanName() )
            
            subscriptions.append( subscription )
            
        
        self._queries = [ query for query in my_queries if query not in only_these_queries ]
        
        return subscriptions
        
    
    def SetCheckerOptions( self, checker_options ):
        
        self._checker_options = checker_options
        
        for query in self._queries:
            
            query.UpdateNextCheckTime( self._checker_options )
            
        
    
    def SetPresentationOptions( self, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events ):
        
        self._show_a_popup_while_working = show_a_popup_while_working
        self._publish_files_to_popup_button = publish_files_to_popup_button
        self._publish_files_to_page = publish_files_to_page
        self._publish_label_override = publish_label_override
        self._merge_query_publish_events = merge_query_publish_events
        
    
    def SetQueries( self, queries: collections.abc.Iterable[ SubscriptionQueryLegacy ] ):
        
        self._queries = list( queries )
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options.Duplicate()
        
    
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
        
    
    def ToTuple( self ):
        
        return ( self._name, self._gug_key_and_name, self._queries, self._checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, self._file_import_options, self._tag_import_options, self._no_work_until, self._no_work_until_reason )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_LEGACY ] = SubscriptionLegacy

def ConvertLegacySubscriptionToNew( legacy_subscription: SubscriptionLegacy ):
    
    (
        name,
        gug_key_and_name,
        queries,
        checker_options,
        initial_file_limit,
        periodic_file_limit,
        paused,
        file_import_options,
        tag_import_options,
        no_work_until,
        no_work_until_reason
        ) = legacy_subscription.ToTuple()
    
    subscription = ClientImportSubscriptions.Subscription( name )
    
    subscription.SetTuple(
        gug_key_and_name,
        checker_options,
        initial_file_limit,
        periodic_file_limit,
        paused,
        file_import_options,
        tag_import_options,
        no_work_until
        )
    
    (
        show_a_popup_while_working,
        publish_files_to_popup_button,
        publish_files_to_page,
        publish_label_override,
        merge_query_publish_events
        ) = legacy_subscription.GetPresentationOptions()
    
    subscription.SetPresentationOptions(
        show_a_popup_while_working,
        publish_files_to_popup_button,
        publish_files_to_page,
        publish_label_override,
        merge_query_publish_events
    )
    
    query_headers = []
    query_log_containers = []
    
    for query in queries:
        
        query_header = ClientImportSubscriptionQuery.SubscriptionQueryHeader()
        
        ( query_text, check_now, last_check_time, next_check_time, query_paused, status ) = query.ToTuple()
        
        query_header.SetQueryText( query_text )
        query_header.SetDisplayName( query.GetDisplayName() )
        query_header.SetCheckNow( check_now )
        query_header.SetLastCheckTime( last_check_time )
        query_header.SetNextCheckTime( next_check_time )
        query_header.SetPaused( query_paused )
        query_header.SetCheckerStatus( status )
        query_header.SetTagImportOptions( query.GetTagImportOptions() )
        
        query_log_container = ClientImportSubscriptionQuery.SubscriptionQueryLogContainer( query_header.GetQueryLogContainerName() )
        
        query_log_container.SetGallerySeedLog( query.GetGallerySeedLog() )
        query_log_container.SetFileSeedCache( query.GetFileSeedCache() )
        
        query_header.SyncToQueryLogContainer( checker_options, query_log_container )
        
        query_headers.append( query_header )
        query_log_containers.append( query_log_container )
        
    
    subscription.SetQueryHeaders( query_headers )
    
    return ( subscription, query_log_containers )
    
