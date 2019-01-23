import collections
from . import ClientConstants as CC
from . import ClientNetworkingContexts
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusNetworking
from . import HydrusThreading
from . import HydrusSerialisable
import threading

class NetworkBandwidthManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER
    SERIALISABLE_NAME = 'Bandwidth Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._last_pages_gallery_query_timestamps = collections.defaultdict( lambda: 0 )
        self._last_subscriptions_gallery_query_timestamps = collections.defaultdict( lambda: 0 )
        self._last_watchers_query_timestamps = collections.defaultdict( lambda: 0 )
        
        self._network_contexts_to_bandwidth_trackers = collections.defaultdict( HydrusNetworking.BandwidthTracker )
        self._network_contexts_to_bandwidth_rules = collections.defaultdict( HydrusNetworking.BandwidthRules )
        
        for context_type in [ CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_HYDRUS, CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, CC.NETWORK_CONTEXT_SUBSCRIPTION, CC.NETWORK_CONTEXT_WATCHER_PAGE ]:
            
            self._network_contexts_to_bandwidth_rules[ ClientNetworkingContexts.NetworkContext( context_type ) ] = HydrusNetworking.BandwidthRules()
            
        
    
    def _CanStartRequest( self, network_contexts ):
        
        for network_context in network_contexts:
            
            bandwidth_rules = self._GetRules( network_context )
            
            bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
            
            if not bandwidth_rules.CanStartRequest( bandwidth_tracker ):
                
                return False
                
            
        
        return True
        
    
    def _GetRules( self, network_context ):
        
        if network_context not in self._network_contexts_to_bandwidth_rules:
            
            network_context = ClientNetworkingContexts.NetworkContext( network_context.context_type ) # i.e. the default
            
        
        return self._network_contexts_to_bandwidth_rules[ network_context ]
        
    
    def _GetSerialisableInfo( self ):
        
        # note this discards ephemeral network contexts, which have temporary identifiers that are generally invisible to the user
        all_serialisable_trackers = [ ( network_context.GetSerialisableTuple(), tracker.GetSerialisableTuple() ) for ( network_context, tracker ) in list(self._network_contexts_to_bandwidth_trackers.items()) if not network_context.IsEphemeral() ]
        all_serialisable_rules = [ ( network_context.GetSerialisableTuple(), rules.GetSerialisableTuple() ) for ( network_context, rules ) in list(self._network_contexts_to_bandwidth_rules.items()) ]
        
        return ( all_serialisable_trackers, all_serialisable_rules )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( all_serialisable_trackers, all_serialisable_rules ) = serialisable_info
        
        for ( serialisable_network_context, serialisable_tracker ) in all_serialisable_trackers:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            tracker = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tracker )
            
            self._network_contexts_to_bandwidth_trackers[ network_context ] = tracker
            
        
        for ( serialisable_network_context, serialisable_rules ) in all_serialisable_rules:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            rules = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_rules )
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOWNLOADER: # no longer use this
                
                continue
                
            
            self._network_contexts_to_bandwidth_rules[ network_context ] = rules
            
        
    
    def _ReportRequestUsed( self, network_contexts ):
        
        for network_context in network_contexts:
            
            self._network_contexts_to_bandwidth_trackers[ network_context ].ReportRequestUsed()
            
        
        self._SetDirty()
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def AlreadyHaveExactlyTheseBandwidthRules( self, network_context, bandwidth_rules ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_bandwidth_rules:
                
                if self._network_contexts_to_bandwidth_rules[ network_context ].GetSerialisableTuple() == bandwidth_rules.GetSerialisableTuple():
                    
                    return True
                    
                
            
        
        return False
        
    
    def AutoAddDomainMetadatas( self, domain_metadatas ):
        
        for domain_metadata in domain_metadatas:
            
            if not domain_metadata.HasBandwidthRules():
                
                return
                
            
            with self._lock:
                
                domain = domain_metadata.GetDomain()
                
                network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain )
                
                bandwidth_rules = domain_metadata.GetBandwidthRules()
                
                self._network_contexts_to_bandwidth_rules[ network_context ] = bandwidth_rules
                
            
        
    
    def CanContinueDownload( self, network_contexts ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
                
                if not bandwidth_rules.CanContinueDownload( bandwidth_tracker ):
                    
                    return False
                    
                
            
            return True
            
        
    
    def CanDoWork( self, network_contexts, expected_requests = 1, expected_bytes = 1048576, threshold = 30 ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
                
                if not bandwidth_rules.CanDoWork( bandwidth_tracker, expected_requests = expected_requests, expected_bytes = expected_bytes, threshold = threshold ):
                    
                    return False
                    
                
            
            return True
            
        
    
    def CanStartRequest( self, network_contexts ):
        
        with self._lock:
            
            return self._CanStartRequest( network_contexts )
            
        
    
    def DeleteRules( self, network_context ):
        
        with self._lock:
            
            if network_context.context_data is None:
                
                return # can't delete 'default' network contexts
                
            else:
                
                if network_context in self._network_contexts_to_bandwidth_rules:
                    
                    del self._network_contexts_to_bandwidth_rules[ network_context ]
                    
                
            
            self._SetDirty()
            
        
    
    def DeleteHistory( self, network_contexts ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                if network_context in self._network_contexts_to_bandwidth_trackers:
                    
                    del self._network_contexts_to_bandwidth_trackers[ network_context ]
                    
                    if network_context == ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT:
                        
                        # just to reset it, so we have a 0 global context at all times
                        self._network_contexts_to_bandwidth_trackers[ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ] = HydrusNetworking.BandwidthTracker()
                        
                    
                
            
            self._SetDirty()
            
        
    
    def GetDefaultRules( self ):
        
        with self._lock:
            
            result = []
            
            for ( network_context, bandwidth_rules ) in list(self._network_contexts_to_bandwidth_rules.items()):
                
                if network_context.IsDefault():
                    
                    result.append( ( network_context, bandwidth_rules ) )
                    
                
            
            return result
            
        
    
    def GetCurrentMonthSummary( self, network_context ):
        
        with self._lock:
            
            bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
            
            return bandwidth_tracker.GetCurrentMonthSummary()
            
        
    
    def GetBandwidthStringsAndGaugeTuples( self, network_context ):
        
        with self._lock:
            
            bandwidth_rules = self._GetRules( network_context )
            
            bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
            
            return bandwidth_rules.GetBandwidthStringsAndGaugeTuples( bandwidth_tracker )
            
        
    
    def GetNetworkContextsForUser( self, history_time_delta_threshold = None ):
        
        with self._lock:
            
            result = set()
            
            for ( network_context, bandwidth_tracker ) in list(self._network_contexts_to_bandwidth_trackers.items()):
                
                if network_context.IsDefault() or network_context.IsEphemeral():
                    
                    continue
                    
                
                if network_context != ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT and history_time_delta_threshold is not None:
                    
                    if bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, history_time_delta_threshold ) == 0:
                        
                        continue
                        
                    
                
                result.add( network_context )
                
            
            return result
            
        
    
    def GetRules( self, network_context ):
        
        with self._lock:
            
            return self._GetRules( network_context )
            
        
    
    def GetTracker( self, network_context ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_bandwidth_trackers:
                
                return self._network_contexts_to_bandwidth_trackers[ network_context ]
                
            else:
                
                return HydrusNetworking.BandwidthTracker()
                
            
        
    
    def GetWaitingEstimateAndContext( self, network_contexts ):
        
        with self._lock:
            
            estimates = []
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
                
                estimates.append( ( bandwidth_rules.GetWaitingEstimate( bandwidth_tracker ), network_context ) )
                
            
            estimates.sort( key = lambda pair: -pair[0] ) # biggest first
            
            if len( estimates ) == 0:
                
                return ( 0, ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
                
            else:
                
                return estimates[0]
                
            
        
    
    def HasRules( self, network_context ):
        
        with self._lock:
            
            return network_context in self._network_contexts_to_bandwidth_rules
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def ReportDataUsed( self, network_contexts, num_bytes ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                self._network_contexts_to_bandwidth_trackers[ network_context ].ReportDataUsed( num_bytes )
                
            
            self._SetDirty()
            
        
    
    def ReportRequestUsed( self, network_contexts ):
        
        with self._lock:
            
            self._ReportRequestUsed( network_contexts )
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetRules( self, network_context, bandwidth_rules ):
        
        with self._lock:
            
            if len( bandwidth_rules.GetRules() ) == 0:
                
                if network_context in self._network_contexts_to_bandwidth_rules:
                    
                    del self._network_contexts_to_bandwidth_rules[ network_context ]
                    
                
            else:
                
                self._network_contexts_to_bandwidth_rules[ network_context ] = bandwidth_rules
                
            
            self._SetDirty()
            
        
    
    def TryToConsumeAGalleryToken( self, second_level_domain, query_type ):
        
        with self._lock:
            
            if query_type == 'download page':
                
                timestamps_dict = self._last_pages_gallery_query_timestamps
                
                delay = HG.client_controller.new_options.GetInteger( 'gallery_page_wait_period_pages' )
                
            elif query_type == 'subscription':
                
                timestamps_dict = self._last_subscriptions_gallery_query_timestamps
                
                delay = HG.client_controller.new_options.GetInteger( 'gallery_page_wait_period_subscriptions' )
                
            elif query_type == 'watcher':
                
                timestamps_dict = self._last_watchers_query_timestamps
                
                delay = HG.client_controller.new_options.GetInteger( 'watcher_page_wait_period' )
                
            
            next_timestamp = timestamps_dict[ second_level_domain ] + delay
            
            if HydrusData.TimeHasPassed( next_timestamp ):
                
                timestamps_dict[ second_level_domain ] = HydrusData.GetNow()
                
                return ( True, 0 )
                
            else:
                
                return ( False, next_timestamp )
                
            
            raise NotImplementedError( 'Unknown query type' )
            
        
    
    def TryToStartRequest( self, network_contexts ):
        
        # this wraps canstart and reportrequest in one transaction to stop 5/1 rq/s happening due to race condition
        
        with self._lock:
            
            if not self._CanStartRequest( network_contexts ):
                
                return False
                
            
            self._ReportRequestUsed( network_contexts )
            
            return True
            
        
    
    def UsesDefaultRules( self, network_context ):
        
        with self._lock:
            
            return network_context not in self._network_contexts_to_bandwidth_rules
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER ] = NetworkBandwidthManager
