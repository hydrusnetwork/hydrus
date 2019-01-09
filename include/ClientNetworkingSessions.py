import pickle
from . import ClientConstants as CC
from . import ClientNetworkingContexts
from . import ClientNetworkingDomain
from . import HydrusData
from . import HydrusSerialisable
from . import HydrusGlobals as HG
import requests
import threading

try:
    
    import socket
    import socks
    
    SOCKS_PROXY_OK = True
    
except:
    
    SOCKS_PROXY_OK = False
    

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
        
        self._proxies_dict = {}
        
        self._Reinitialise()
        
        HG.client_controller.sub( self, 'Reinitialise', 'notify_new_options' )
        
    
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
        
        serialisable_network_contexts_to_sessions = [ ( network_context.GetSerialisableTuple(), pickle.dumps( session ).hex() ) for ( network_context, session ) in list(self._network_contexts_to_sessions.items()) ]
        
        return serialisable_network_contexts_to_sessions
        
    
    def _GetSessionNetworkContext( self, network_context ):
        
        # just in case one of these slips through somehow
        if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
            
            second_level_domain = ClientNetworkingDomain.ConvertDomainIntoSecondLevelDomain( network_context.context_data )
            
            network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, second_level_domain )
            
        
        return network_context
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_network_contexts_to_sessions = serialisable_info
        
        for ( serialisable_network_context, pickled_session_hex ) in serialisable_network_contexts_to_sessions:
            
            network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
            
            try:
                
                session = pickle.loads( bytes.fromhex( pickled_session_hex ) )
                
            except:
                
                # new version of requests uses a diff format, wew
                
                continue
                
            
            session.cookies.clear_session_cookies()
            
            self._network_contexts_to_sessions[ network_context ] = session
            
        
    
    def _Reinitialise( self ):
        
        self._proxies_dict = {}
        
        http_proxy = HG.client_controller.new_options.GetNoneableString( 'http_proxy' )
        https_proxy = HG.client_controller.new_options.GetNoneableString( 'https_proxy' )
        
        if http_proxy is not None:
            
            self._proxies_dict[ 'http' ] = http_proxy
            
        
        if https_proxy is not None:
            
            self._proxies_dict[ 'https' ] = https_proxy
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def ClearSession( self, network_context ):
        
        with self._lock:
            
            network_context = self._GetSessionNetworkContext( network_context )
            
            if network_context in self._network_contexts_to_sessions:
                
                del self._network_contexts_to_sessions[ network_context ]
                
                self._SetDirty()
                
            
        
    
    def GetNetworkContexts( self ):
        
        with self._lock:
            
            return list(self._network_contexts_to_sessions.keys())
            
        
    
    def GetSession( self, network_context ):
        
        with self._lock:
            
            network_context = self._GetSessionNetworkContext( network_context )
            
            if network_context not in self._network_contexts_to_sessions:
                
                self._network_contexts_to_sessions[ network_context ] = self._GenerateSession( network_context )
                
            
            session = self._network_contexts_to_sessions[ network_context ]
            
            if session.proxies != self._proxies_dict:
                
                session.proxies = dict( self._proxies_dict )
                
            
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
            
        
    
    def GetSessionForDomain( self, domain ):
        
        network_context = ClientNetworkingContexts.NetworkContext( context_type = CC.NETWORK_CONTEXT_DOMAIN, context_data = domain )
        
        return self.GetSession( network_context )
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def Reinitialise( self ):
        
        with self._lock:
            
            self._Reinitialise()
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER ] = NetworkSessionManager
