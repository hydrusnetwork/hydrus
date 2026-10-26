from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable

# no longer used, leaving a stub
class NetworkSessionManagerLegacy( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_LEGACY
    SERIALISABLE_NAME = 'Legacy Session Manager'
    SERIALISABLE_VERSION = 1
    
    SESSION_TIMEOUT = 60 * 60
    
    def __init__( self ):
        
        super().__init__()
        
        self._network_contexts_to_sessions = {}
        
    
    def _GetSerialisableInfo( self ):
        
        return []
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info: object, serialisable_type_whitelist: set[ int ] | None ):
        
        HydrusData.Print( 'Encountered an old NetworkSessionManagerLegacy initialising its data. You can ignore this message.' )
        
    
    def GetData( self ):
        
        return self._network_contexts_to_sessions
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_LEGACY ] = NetworkSessionManagerLegacy
