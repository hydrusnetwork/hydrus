import pickle

from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable

from hydrus.client.networking import ClientNetworkingSessions

class NetworkSessionManagerLegacy( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_LEGACY
    SERIALISABLE_NAME = 'Legacy Session Manager'
    SERIALISABLE_VERSION = 1
    
    SESSION_TIMEOUT = 60 * 60
    
    def __init__( self ):
        
        super().__init__()
        
        self._network_contexts_to_sessions = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_network_contexts_to_sessions = [ ( network_context.GetSerialisableTuple(), pickle.dumps( session ).hex() ) for ( network_context, session ) in list(self._network_contexts_to_sessions.items()) ]
        
        return serialisable_network_contexts_to_sessions
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_network_contexts_to_sessions = serialisable_info
        
        for ( serialisable_network_context, pickled_session_hex ) in serialisable_network_contexts_to_sessions:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            
            try:
                
                session = pickle.loads( bytes.fromhex( pickled_session_hex ) )
                
            except Exception as e:
                
                # new version of requests uses a diff format, wew
                
                continue
                
            
            session.cookies.clear_session_cookies()
            
            self._network_contexts_to_sessions[ network_context ] = session
            
        
    
    def GetData( self ):
        
        return self._network_contexts_to_sessions
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_LEGACY ] = NetworkSessionManagerLegacy

def ConvertLegacyToNewSessions( legacy_session_manager: NetworkSessionManagerLegacy ):
    
    session_containers = []
    
    network_contexts_to_sessions = legacy_session_manager.GetData()
    
    for ( network_context, session ) in network_contexts_to_sessions.items():
        
        session_container_name = HydrusData.GenerateKey().hex()
        
        session_container = ClientNetworkingSessions.NetworkSessionManagerSessionContainer( session_container_name, network_context = network_context, session = session )
        
        session_containers.append( session_container )
        
    
    session_manager = ClientNetworkingSessions.NetworkSessionManager()
    
    session_manager.SetSessionContainers( session_containers, set_all_sessions_dirty = True )
    
    session_manager.SetDirty()
    
    return session_manager
    
