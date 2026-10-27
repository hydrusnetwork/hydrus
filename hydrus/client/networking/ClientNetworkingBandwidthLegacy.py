from hydrus.core import HydrusSerialisable

class NetworkBandwidthManagerLegacy( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_LEGACY
    SERIALISABLE_NAME = 'Legacy Bandwidth Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
    
    def _GetSerialisableInfo( self ):
        
        return tuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info: object, trusted: bool, serialisable_type_whitelist: set[ int ] | None ):
        
        pass
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER_LEGACY ] = NetworkBandwidthManagerLegacy
