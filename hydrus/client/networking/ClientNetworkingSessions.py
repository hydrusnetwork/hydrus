import collections.abc
import pickle
import requests
import threading

from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingFunctions

try:
    
    import socket
    import socks
    
    SOCKS_PROXY_OK = True
    
except:
    
    SOCKS_PROXY_OK = False
    
class NetworkSessionManagerSessionContainer( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_SESSION_CONTAINER
    SERIALISABLE_NAME = 'Session Manager Session Container'
    SERIALISABLE_VERSION = 2
    
    POOL_CONNECTION_TIMEOUT = 5 * 60
    SESSION_TIMEOUT = 45 * 60
    
    def __init__( self, name, network_context = None, session = None ):
        
        if network_context is None:
            
            network_context = ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT
            
        
        super().__init__( name )
        
        self.network_context = network_context
        self.session = session
        self.last_touched_time = HydrusTime.GetNow()
        
        self.pool_is_cleared = True
        self.printed_connection_pool_error = False
        
    
    def _InitialiseEmptySession( self ):
        
        self.session = requests.Session()
        
        if self.network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
            
            self.session.verify = False
            
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_network_context = self.network_context.GetSerialisableTuple()
        
        self.session.cookies.clear_session_cookies()
        
        pickled_cookies_hex = pickle.dumps( self.session.cookies ).hex()
        
        return ( serialisable_network_context, pickled_cookies_hex )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_network_context, pickled_cookies_hex ) = serialisable_info
        
        self.network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
        
        self._InitialiseEmptySession()
        
        try:
            
            cookies = pickle.loads( bytes.fromhex( pickled_cookies_hex ) )
            
            self.session.cookies = cookies
            
        except:
            
            HydrusData.Print( "Could not load and set cookies for session {}".format( self.network_context ) )
            
        
        self.session.cookies.clear_session_cookies()
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_network_context, pickled_session_hex ) = old_serialisable_info
            
            try:
                
                session = pickle.loads( bytes.fromhex( pickled_session_hex ) )
                
            except:
                
                session = requests.Session()
                
            
            pickled_cookies_hex = pickle.dumps( session.cookies ).hex()
            
            new_serialisable_info = ( serialisable_network_context, pickled_cookies_hex )
            
            return ( 2, new_serialisable_info )
            
        
    
    def MaintainConnectionPool( self ):
        
        if not self.pool_is_cleared and HydrusTime.TimeHasPassed( self.last_touched_time + self.POOL_CONNECTION_TIMEOUT ):
            
            try:
                
                my_session_adapters = list( self.session.adapters.values() )
                
                for adapter in my_session_adapters:
                    
                    poolmanager = getattr( adapter, 'poolmanager', None )
                    
                    if poolmanager is not None:
                        
                        poolmanager.clear()
                        
                    
                
                self.pool_is_cleared = True
                
            except Exception as e:
                
                if not self.printed_connection_pool_error:
                    
                    self.printed_connection_pool_error = True
                    
                    HydrusData.Print( 'There was a problem clearing the connection pool. The full error should follow. To stop spam, this message will only show one time per program boot. The error may happen again, silently.' )
                    HydrusData.PrintException( e, do_wait = False )
                    
                
            
        
    
    def PrepareForNewWork( self ):
        
        self.last_touched_time = HydrusTime.GetNow()
        self.pool_is_cleared = False
        
        my_session_cookies = self.session.cookies
        
        if HydrusTime.TimeHasPassed( self.last_touched_time + self.SESSION_TIMEOUT ):
            
            my_session_cookies.clear_session_cookies()
            
        
        my_session_cookies.clear_expired_cookies()
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER_SESSION_CONTAINER ] = NetworkSessionManagerSessionContainer

class NetworkSessionManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER
    SERIALISABLE_NAME = 'Session Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        super().__init__()
        
        self._dirty = False
        self._dirty_session_container_names = set()
        self._deletee_session_container_names = set()
        
        self._lock = threading.Lock()
        
        self._session_container_names = set()
        
        self._session_container_names_to_session_containers = {}
        self._network_contexts_to_session_containers = {}
        
        self._proxies_dict = {}
        
        self._ReinitialiseProxies()
        
        CG.client_controller.sub( self, 'ReinitialiseProxies', 'notify_new_options' )
        CG.client_controller.sub( self, 'MaintainConnectionPools', 'memory_maintenance_pulse' )
        
    
    def _GetSerialisableInfo( self ):
        
        return sorted( self._session_container_names )
        
    
    def _GetSessionNetworkContext( self, network_context ):
        
        # just in case one of these slips through somehow
        if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
            
            second_level_domain = ClientNetworkingFunctions.ConvertDomainIntoSecondLevelDomain( network_context.context_data )
            
            network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, second_level_domain )
            
        
        return network_context
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._session_container_names = set( serialisable_info )
        
    
    def _InitialiseSessionContainer( self, network_context ):
        
        session = requests.Session()
        
        if network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
            
            session.verify = False
            
        
        session_container_name = HydrusData.GenerateKey().hex()
        
        session_container = NetworkSessionManagerSessionContainer( session_container_name, network_context = network_context, session = session )
        
        self._session_container_names_to_session_containers[ session_container_name ] = session_container
        self._network_contexts_to_session_containers[ network_context ] = session_container
        
        self._session_container_names.add( session_container_name )
        self._dirty_session_container_names.add( session_container_name )
        
        self._SetDirty()
        
    
    def _ReinitialiseProxies( self ):
        
        self._proxies_dict = {}
        
        http_proxy = CG.client_controller.new_options.GetNoneableString( 'http_proxy' )
        https_proxy = CG.client_controller.new_options.GetNoneableString( 'https_proxy' )
        no_proxy = CG.client_controller.new_options.GetNoneableString( 'no_proxy' )
        
        if http_proxy is not None:
            
            self._proxies_dict[ 'http' ] = http_proxy
            
        
        if https_proxy is not None:
            
            self._proxies_dict[ 'https' ] = https_proxy
            
        
        if ( http_proxy is not None or https_proxy is not None ) and no_proxy is not None:
            
            self._proxies_dict[ 'no_proxy' ] = no_proxy
            
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def ClearSession( self, network_context ):
        
        with self._lock:
            
            network_context = self._GetSessionNetworkContext( network_context )
            
            if network_context in self._network_contexts_to_session_containers:
                
                session_container = self._network_contexts_to_session_containers[ network_context ]
                
                del self._network_contexts_to_session_containers[ network_context ]
                
                session_container_name = session_container.GetName()
                
                if session_container_name in self._session_container_names_to_session_containers:
                    
                    del self._session_container_names_to_session_containers[ session_container_name ]
                    
                
                self._session_container_names.discard( session_container_name )
                self._dirty_session_container_names.discard( session_container_name )
                self._deletee_session_container_names.add( session_container_name )
                
                self._SetDirty()
                
            
        
    
    def GetDeleteeSessionNames( self ):
        
        with self._lock:
            
            return set( self._deletee_session_container_names )
            
        
    
    def GetDirtySessionContainers( self ):
        
        with self._lock:
            
            return [ self._session_container_names_to_session_containers[ session_container_name ] for session_container_name in self._dirty_session_container_names ]
            
        
    
    def GetNetworkContexts( self ):
        
        with self._lock:
            
            return list( self._network_contexts_to_session_containers.keys() )
            
        
    
    def GetSession( self, network_context ):
        
        with self._lock:
            
            network_context = self._GetSessionNetworkContext( network_context )
            
            if network_context not in self._network_contexts_to_session_containers:
                
                self._InitialiseSessionContainer( network_context )
                
            
            session_container = self._network_contexts_to_session_containers[ network_context ]
            
            session_container.PrepareForNewWork()
            
            session = session_container.session
            
            if session.proxies != self._proxies_dict:
                
                session.proxies = dict( self._proxies_dict )
                
            
            #
            
            # tumblr can't into ssl for some reason, and the data subdomain they use has weird cert properties, looking like amazon S3
            # perhaps it is inward-facing somehow? whatever the case, let's just say fuck it for tumblr
            
            if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN and network_context.context_data == 'tumblr.com':
                
                session.verify = False
                
            
            if not CG.client_controller.new_options.GetBoolean( 'verify_regular_https' ):
                
                session.verify = False
                
            
            return session
            
        
    
    def GetSessionForDomain( self, domain ):
        
        network_context = ClientNetworkingContexts.NetworkContext( context_type = CC.NETWORK_CONTEXT_DOMAIN, context_data = domain )
        
        return self.GetSession( network_context )
        
    
    def HasDirtySessionContainers( self ):
        
        with self._lock:
            
            return len( self._dirty_session_container_names ) > 0 or len( self._deletee_session_container_names ) > 0
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def MaintainConnectionPools( self ):
        
        for session_container in self._network_contexts_to_session_containers.values():
            
            session_container.MaintainConnectionPool()
            
        
    
    def ReinitialiseProxies( self ):
        
        with self._lock:
            
            self._ReinitialiseProxies()
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            self._dirty_session_container_names = set()
            self._deletee_session_container_names = set()
            
        
    
    def SetDirty( self ):
        
        with self._lock:
            
            self._SetDirty()
            
        
    
    def SetSessionContainers( self, session_containers: collections.abc.Collection[ NetworkSessionManagerSessionContainer ], set_all_sessions_dirty = False ):
        
        with self._lock:
            
            self._session_container_names_to_session_containers = {}
            self._network_contexts_to_session_containers = {}
            
            self._session_container_names = set()
            self._dirty_session_container_names = set()
            self._deletee_session_container_names = set()
            
            for session_container in session_containers:
                
                session_container_name = session_container.GetName()
                
                self._session_container_names_to_session_containers[ session_container_name ] = session_container
                self._network_contexts_to_session_containers[ session_container.network_context ] = session_container
                
                self._session_container_names.add( session_container_name )
                
                if set_all_sessions_dirty:
                    
                    self._dirty_session_container_names.add( session_container_name )
                    
                
            
        
    
    def SetSessionDirty( self, network_context: ClientNetworkingContexts.NetworkContext ):
        
        with self._lock:
            
            network_context = self._GetSessionNetworkContext( network_context )
            
            if network_context in self._network_contexts_to_session_containers:
                
                self._dirty_session_container_names.add( self._network_contexts_to_session_containers[ network_context ].GetName() )
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER ] = NetworkSessionManager
