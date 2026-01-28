import collections
import collections.abc
import threading

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.networking import ClientNetworkingContexts

class NetworkBandwidthManagerTrackerContainer( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_TRACKER_CONTAINER
    SERIALISABLE_NAME = 'Bandwidth Manager Tracker Container'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name, network_context = None, bandwidth_tracker = None ):
        
        if network_context is None:
            
            network_context = ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT
            
        
        if bandwidth_tracker is None:
            
            bandwidth_tracker = HydrusNetworking.BandwidthTracker()
            
        
        super().__init__( name )
        
        self.network_context = network_context
        self.bandwidth_tracker = bandwidth_tracker
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_network_context = self.network_context.GetSerialisableTuple()
        serialisable_bandwidth_tracker = self.bandwidth_tracker.GetSerialisableTuple()
        
        return ( serialisable_network_context, serialisable_bandwidth_tracker )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_network_context, serialisable_bandwidth_tracker ) = serialisable_info
        
        self.network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
        self.bandwidth_tracker = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_bandwidth_tracker )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_TRACKER_CONTAINER ] = NetworkBandwidthManagerTrackerContainer

class NetworkBandwidthManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER
    SERIALISABLE_NAME = 'Bandwidth Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._last_pages_gallery_query_timestamps = collections.defaultdict( lambda: 0 )
        self._last_subscriptions_gallery_query_timestamps = collections.defaultdict( lambda: 0 )
        self._last_watchers_query_timestamps = collections.defaultdict( lambda: 0 )
        
        self._tracker_container_names_to_tracker_containers = {}
        self._network_contexts_to_tracker_containers = {}
        
        self._tracker_container_names = set()
        self._dirty_tracker_container_names = set()
        self._deletee_tracker_container_names = set()
        
        self._my_bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self._network_contexts_to_bandwidth_rules = collections.defaultdict( HydrusNetworking.BandwidthRules )
        
        for context_type in [ CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_HYDRUS, CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, CC.NETWORK_CONTEXT_SUBSCRIPTION, CC.NETWORK_CONTEXT_WATCHER_PAGE ]:
            
            self._network_contexts_to_bandwidth_rules[ ClientNetworkingContexts.NetworkContext( context_type ) ] = HydrusNetworking.BandwidthRules()
            
        
    
    def _CanStartRequest( self, network_contexts ):
        
        for network_context in network_contexts:
            
            bandwidth_rules = self._GetRules( network_context )
            
            bandwidth_tracker = self._GetTracker( network_context )
            
            if not bandwidth_rules.CanStartRequest( bandwidth_tracker ):
                
                return False
                
            
        
        return True
        
    
    def _GetRules( self, network_context ):
        
        if network_context not in self._network_contexts_to_bandwidth_rules:
            
            network_context = ClientNetworkingContexts.NetworkContext( network_context.context_type ) # i.e. the default
            
        
        return self._network_contexts_to_bandwidth_rules[ network_context ]
        
    
    def _GetSerialisableInfo( self ):
        
        all_tracker_container_names = sorted( self._tracker_container_names )
        all_serialisable_rules = [ ( network_context.GetSerialisableTuple(), rules.GetSerialisableTuple() ) for ( network_context, rules ) in list(self._network_contexts_to_bandwidth_rules.items()) ]
        
        return ( all_tracker_container_names, all_serialisable_rules )
        
    
    def _GetTracker( self, network_context: ClientNetworkingContexts.NetworkContext, making_it_dirty = False ):
        
        if network_context not in self._network_contexts_to_tracker_containers:
            
            bandwidth_tracker = HydrusNetworking.BandwidthTracker()
            
            tracker_container_name = HydrusData.GenerateKey().hex()
            
            tracker_container = NetworkBandwidthManagerTrackerContainer( tracker_container_name, network_context = network_context, bandwidth_tracker = bandwidth_tracker )
            
            self._tracker_container_names_to_tracker_containers[ tracker_container_name ] = tracker_container
            self._network_contexts_to_tracker_containers[ network_context ] = tracker_container
            
            # note this discards ephemeral network contexts, which have temporary identifiers that are generally invisible to the user
            
            if not network_context.IsEphemeral():
                
                self._tracker_container_names.add( tracker_container_name )
                self._dirty_tracker_container_names.add( tracker_container_name )
                
            
            self._SetDirty()
            
        
        tracker_container = self._network_contexts_to_tracker_containers[ network_context ]
        
        if making_it_dirty and not network_context.IsEphemeral():
            
            self._dirty_tracker_container_names.add( tracker_container.GetName() )
            
        
        return tracker_container.bandwidth_tracker
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( all_tracker_container_names, all_serialisable_rules ) = serialisable_info
        
        self._tracker_container_names = set( all_tracker_container_names )
        
        for ( serialisable_network_context, serialisable_rules ) in all_serialisable_rules:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            rules = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_rules )
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOWNLOADER: # no longer use this
                
                continue
                
            
            self._network_contexts_to_bandwidth_rules[ network_context ] = rules
            
        
    
    def _ReportDataUsed( self, network_contexts, num_bytes ):
        
        for network_context in network_contexts:
            
            bandwidth_tracker = self._GetTracker( network_context, making_it_dirty = True )
            
            bandwidth_tracker.ReportDataUsed( num_bytes )
            
        
        self._my_bandwidth_tracker.ReportDataUsed( num_bytes )
        
    
    def _ReportRequestUsed( self, network_contexts ):
        
        for network_context in network_contexts:
            
            bandwidth_tracker = self._GetTracker( network_context, making_it_dirty = True )
            
            bandwidth_tracker.ReportRequestUsed()
            
        
        self._my_bandwidth_tracker.ReportRequestUsed()
        
    
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
                
                bandwidth_tracker = self._GetTracker( network_context )
                
                if not bandwidth_rules.CanContinueDownload( bandwidth_tracker ):
                    
                    return False
                    
                
            
            return True
            
        
    
    def CanDoWork( self, network_contexts, expected_requests = 1, expected_bytes = 1048576, threshold = 30 ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._GetTracker( network_context )
                
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
                
                if network_context in self._network_contexts_to_tracker_containers:
                    
                    tracker_container = self._network_contexts_to_tracker_containers[ network_context ]
                    
                    del self._network_contexts_to_tracker_containers[ network_context ]
                    
                    tracker_container_name = tracker_container.GetName()
                    
                    if tracker_container_name in self._tracker_container_names_to_tracker_containers:
                        
                        del self._tracker_container_names_to_tracker_containers[ tracker_container_name ]
                        
                    
                    self._tracker_container_names.discard( tracker_container_name )
                    self._dirty_tracker_container_names.discard( tracker_container_name )
                    self._deletee_tracker_container_names.add( tracker_container_name )
                    
                
                if network_context == ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT:
                    
                    # just to reset it and have it in the system, so we have a 0 global context at all times
                    self._GetTracker( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
                    
                
            
            self._SetDirty()
            
        
    
    def GetBandwidthStringsAndGaugeTuples( self, network_context ):
        
        with self._lock:
            
            bandwidth_rules = self._GetRules( network_context )
            
            bandwidth_tracker = self._GetTracker( network_context )
            
            return bandwidth_rules.GetBandwidthStringsAndGaugeTuples( bandwidth_tracker )
            
        
    
    def GetCurrentMonthSummary( self, network_context ):
        
        with self._lock:
            
            bandwidth_tracker = self._GetTracker( network_context )
            
            return bandwidth_tracker.GetCurrentMonthSummary()
            
        
    
    def GetDefaultRules( self ):
        
        with self._lock:
            
            result = []
            
            for ( network_context, bandwidth_rules ) in self._network_contexts_to_bandwidth_rules.items():
                
                if network_context.IsDefault():
                    
                    result.append( ( network_context, bandwidth_rules ) )
                    
                
            
            return result
            
        
    
    def GetDeleteeTrackerNames( self ):
        
        with self._lock:
            
            return set( self._deletee_tracker_container_names )
            
        
    
    def GetDirtyTrackerContainers( self ):
        
        with self._lock:
            
            return [ self._tracker_container_names_to_tracker_containers[ tracker_container_name ] for tracker_container_name in self._dirty_tracker_container_names ]
            
        
    
    def GetMySessionTracker( self ):
        
        with self._lock:
            
            return self._my_bandwidth_tracker
            
        
    
    def GetNetworkContextsForUser( self, history_time_delta_threshold = None ):
        
        with self._lock:
            
            result = set()
            
            for tracker_container in self._network_contexts_to_tracker_containers.values():
                
                network_context = tracker_container.network_context
                
                if network_context.IsDefault() or network_context.IsEphemeral():
                    
                    continue
                    
                
                bandwidth_tracker = tracker_container.bandwidth_tracker
                
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
            
            if network_context in self._network_contexts_to_tracker_containers:
                
                return self._GetTracker( network_context )
                
            else:
                
                return HydrusNetworking.BandwidthTracker()
                
            
        
    
    def GetWaitingEstimateAndContext( self, network_contexts ):
        
        with self._lock:
            
            estimates = []
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._GetTracker( network_context )
                
                estimates.append( ( bandwidth_rules.GetWaitingEstimate( bandwidth_tracker ), network_context ) )
                
            
            estimates.sort( key = lambda pair: -pair[0] ) # biggest first
            
            if len( estimates ) == 0:
                
                return ( 0, ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
                
            else:
                
                return estimates[0]
                
            
        
    
    def HasDirtyTrackerContainers( self ):
        
        with self._lock:
            
            return len( self._dirty_tracker_container_names ) > 0 or len( self._deletee_tracker_container_names ) > 0
            
        
    
    def HasRules( self, network_context ):
        
        with self._lock:
            
            return network_context in self._network_contexts_to_bandwidth_rules
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def ReportDataUsed( self, network_contexts, num_bytes ):
        
        with self._lock:
            
            self._ReportDataUsed( network_contexts, num_bytes )
            
        
    
    def ReportRequestUsed( self, network_contexts ):
        
        with self._lock:
            
            self._ReportRequestUsed( network_contexts )
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            self._dirty_tracker_container_names = set()
            self._deletee_tracker_container_names = set()
            
        
    
    def SetDirty( self ):
        
        with self._lock:
            
            self._SetDirty()
            
        
    
    def SetRules( self, network_context, bandwidth_rules ):
        
        with self._lock:
            
            if len( bandwidth_rules.GetRules() ) == 0 and not network_context.IsDefault():
                
                if network_context in self._network_contexts_to_bandwidth_rules:
                    
                    del self._network_contexts_to_bandwidth_rules[ network_context ]
                    
                
            else:
                
                self._network_contexts_to_bandwidth_rules[ network_context ] = bandwidth_rules
                
            
            self._SetDirty()
            
        
    
    def SetTrackerContainers( self, tracker_containers: collections.abc.Collection[ NetworkBandwidthManagerTrackerContainer ], set_all_trackers_dirty = False ):
        
        with self._lock:
            
            self._tracker_container_names_to_tracker_containers = {}
            self._network_contexts_to_tracker_containers = {}
            
            self._tracker_container_names = set()
            self._dirty_tracker_container_names = set()
            self._deletee_tracker_container_names = set()
            
            for tracker_container in tracker_containers:
                
                tracker_container_name = tracker_container.GetName()
                network_context = tracker_container.network_context
                
                self._tracker_container_names_to_tracker_containers[ tracker_container_name ] = tracker_container
                self._network_contexts_to_tracker_containers[ network_context ] = tracker_container
                
                if not network_context.IsEphemeral():
                    
                    self._tracker_container_names.add( tracker_container_name )
                    
                    if set_all_trackers_dirty:
                        
                        self._dirty_tracker_container_names.add( tracker_container_name )
                        
                    
                
            
        
    
    def TryToConsumeAGalleryToken( self, second_level_domain, query_type ):
        
        with self._lock:
            
            if query_type == 'download page':
                
                timestamps_dict = self._last_pages_gallery_query_timestamps
                
                delay = CG.client_controller.new_options.GetInteger( 'gallery_page_wait_period_pages' )
                
            elif query_type == 'subscription':
                
                timestamps_dict = self._last_subscriptions_gallery_query_timestamps
                
                delay = CG.client_controller.new_options.GetInteger( 'gallery_page_wait_period_subscriptions' )
                
            elif query_type == 'watcher':
                
                timestamps_dict = self._last_watchers_query_timestamps
                
                delay = CG.client_controller.new_options.GetInteger( 'watcher_page_wait_period' )
                
            else:
                
                raise NotImplementedError( 'Unknown query type' )
                
            
            next_timestamp = timestamps_dict[ second_level_domain ] + delay
            
            if HydrusTime.TimeHasPassed( next_timestamp ):
                
                timestamps_dict[ second_level_domain ] = HydrusTime.GetNow()
                
                return ( True, 0 )
                
            else:
                
                return ( False, next_timestamp )
                
            
        
    
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
