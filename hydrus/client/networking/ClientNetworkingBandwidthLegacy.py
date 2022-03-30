import collections

from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client.networking import ClientNetworkingBandwidth

class NetworkBandwidthManagerLegacy( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_LEGACY
    SERIALISABLE_NAME = 'Legacy Bandwidth Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._network_contexts_to_bandwidth_trackers = collections.defaultdict( HydrusNetworking.BandwidthTracker )
        self._network_contexts_to_bandwidth_rules = collections.defaultdict( HydrusNetworking.BandwidthRules )
        
    
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
            
        
    
    def GetData( self ):
        
        return ( self._network_contexts_to_bandwidth_trackers, self._network_contexts_to_bandwidth_rules )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_LEGACY ] = NetworkBandwidthManagerLegacy

def ConvertLegacyToNewBandwidth( legacy_bandwidth_manager: NetworkBandwidthManagerLegacy ):
    
    tracker_containers = []
    
    ( network_contexts_to_bandwidth_trackers, network_contexts_to_bandwidth_rules ) = legacy_bandwidth_manager.GetData()
    
    for ( network_context, bandwidth_tracker ) in network_contexts_to_bandwidth_trackers.items():
        
        tracker_container_name = HydrusData.GenerateKey().hex()
        
        tracker_container = ClientNetworkingBandwidth.NetworkBandwidthManagerTrackerContainer( tracker_container_name, network_context = network_context, bandwidth_tracker = bandwidth_tracker )
        
        tracker_containers.append( tracker_container )
        
    
    bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
    
    for ( network_context, bandwidth_rules ) in network_contexts_to_bandwidth_rules.items():
        
        bandwidth_manager.SetRules( network_context, bandwidth_rules )
        
    
    bandwidth_manager.SetTrackerContainers( tracker_containers, set_all_trackers_dirty = True )
    
    bandwidth_manager.SetDirty()
    
    return bandwidth_manager
    
