from hydrus.core import HydrusSerialisable

# this object is no longer used
class SubscriptionQueryLegacy( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LEGACY
    SERIALISABLE_NAME = 'Legacy Subscription Query'
    SERIALISABLE_VERSION = 3
    
    def __init__( self ):
        
        super().__init__()
        
    
    def _GetSerialisableInfo( self ):
        
        return tuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info: object, trusted: bool, serialisable_type_whitelist: set[ int ] ):
        
        pass
        
    
    def _UpdateSerialisableInfo( self, version: int, old_serialisable_info: object, trusted: bool ):
        
        return ( self.SERIALISABLE_VERSION, tuple() )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY_LEGACY ] = SubscriptionQueryLegacy

class SubscriptionLegacy( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_LEGACY
    SERIALISABLE_NAME = 'Legacy Subscription'
    SERIALISABLE_VERSION = 10
    
    def __init__( self, name ):
        
        super().__init__( name )
        
    
    def _GetSerialisableInfo( self ):
        
        return tuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info: object, trusted: bool, serialisable_type_whitelist: set[ int ] ):
        
        pass
        
    
    def _UpdateSerialisableInfo( self, version: int, old_serialisable_info: object, trusted: bool ):
        
        return ( self.SERIALISABLE_VERSION, tuple() )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_LEGACY ] = SubscriptionLegacy
