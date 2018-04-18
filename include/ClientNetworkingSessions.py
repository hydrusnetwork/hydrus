import cPickle
import ClientConstants as CC
import ClientNetworkingContexts
import ClientNetworkingDomain
import HydrusData
import HydrusSerialisable
import requests
import threading

class NetworkSessionManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER
    SERIALISABLE_NAME = 'Session Manager'
    SERIALISABLE_VERSION = 1
    
    SESSION_TIMEOUT = 60 * 60
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._network_contexts_to_sessions = {}
        
        self._network_contexts_to_session_timeouts = {}
        
    
    def _CleanSessionCookies( self, network_context, session ):
        
        if network_context not in self._network_contexts_to_session_timeouts:
            
            self._network_contexts_to_session_timeouts[ network_context ] = 0
            
        
        if HydrusData.TimeHasPassed( self._network_contexts_to_session_timeouts[ network_context ] ):
            
            session.cookies.clear_session_cookies()
            
        
        self._network_contexts_to_session_timeouts[ network_context ] = HydrusData.GetNow() + self.SESSION_TIMEOUT
        
        session.cookies.clear_expired_cookies()
        
    
    def _GenerateSession( self, network_context ):
        
        session = requests.Session()
        
        if network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
            
            session.verify = False
            
        
        return session
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_network_contexts_to_sessions = [ ( network_context.GetSerialisableTuple(), cPickle.dumps( session ) ) for ( network_context, session ) in self._network_contexts_to_sessions.items() ]
        
        return serialisable_network_contexts_to_sessions
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_network_contexts_to_sessions = serialisable_info
        
        for ( serialisable_network_context, pickled_session ) in serialisable_network_contexts_to_sessions:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            session = cPickle.loads( str( pickled_session ) )
            
            session.cookies.clear_session_cookies()
            
            self._network_contexts_to_sessions[ network_context ] = session
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def ClearSession( self, network_context ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_sessions:
                
                del self._network_contexts_to_sessions[ network_context ]
                
                self._SetDirty()
                
            
        
    
    def GetNetworkContexts( self ):
        
        with self._lock:
            
            return self._network_contexts_to_sessions.keys()
            
        
    
    def GetSession( self, network_context ):
        
        with self._lock:
            
            # just in case one of these slips through somehow
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                second_level_domain = ClientNetworkingDomain.ConvertDomainIntoSecondLevelDomain( network_context.context_data )
                
                network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, second_level_domain )
                
            
            if network_context not in self._network_contexts_to_sessions:
                
                self._network_contexts_to_sessions[ network_context ] = self._GenerateSession( network_context )
                
            
            session = self._network_contexts_to_sessions[ network_context ]
            
            #
            
            self._CleanSessionCookies( network_context, session )
            
            #
            
            # tumblr can't into ssl for some reason, and the data subdomain they use has weird cert properties, looking like amazon S3
            # perhaps it is inward-facing somehow? whatever the case, let's just say fuck it for tumblr
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN and network_context.context_data == 'tumblr.com':
                
                session.verify = False
                
            
            #
            
            self._SetDirty()
            
            return session
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER ] = NetworkSessionManager
