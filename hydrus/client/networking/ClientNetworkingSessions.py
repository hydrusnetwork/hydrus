import collections.abc
import http.cookiejar
import pickle
import requests
import threading
import typing

from hydrus.core import HydrusData
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.networking import ClientNetworkingCurlCFFI
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingFunctions

try:
    
    import socket
    import socks
    
    SOCKS_PROXY_OK = True
    
except Exception as e:
    
    SOCKS_PROXY_OK = False
    

DOING_CURL_CFFI_TEST = False
CURL_CFFI_DEFINITION = ''
CURL_CFFI_HTTP_VERSION = -1

def AddCookieToSession( session, name, value, domain, path, expires, secure = False, rest = None ):
    
    version = 0
    port = None
    port_specified = False
    domain_specified = True
    domain_initial_dot = domain.startswith( '.' )
    path_specified = True
    discard = False
    comment = None
    comment_url = None
    
    if rest is None:
        
        rest = {}
        
    
    cookie = http.cookiejar.Cookie( version, name, value, port, port_specified, domain, domain_specified, domain_initial_dot, path, path_specified, secure, expires, discard, comment, comment_url, rest )
    
    AddCookieToSessionActualCookie( session, cookie )
    

def AddCookieToSessionActualCookie( session, cookie: http.cookiejar.Cookie ):
    
    AddCookiesToSessionActualCookies( session, [ cookie ] )
    

def AddCookiesToSessionActualCookies( session, list_of_cookies: list[ http.cookiejar.Cookie ] ):
    
    cookies = GetRequestsSessionCookieJar( session )
    
    for cookie in list_of_cookies:
        
        cookies.set_cookie( cookie )
        
    
    EnsureSessionCookiesAreSynced( session, cookies )
    

def CleanseHeadersForSession( ambiguous_session, headers: dict[ str, str ] ):
    
    if ClientNetworkingCurlCFFI.SessionIsCurlCFFI( ambiguous_session ):
        
        lower_to_actual = { key.lower() : key for key in headers.keys() }
        
        if 'user-agent' in lower_to_actual:
            
            del headers[ lower_to_actual[ 'user-agent' ] ]
            
        
    

def ClearExpiredCookies( ambiguous_session ):
    
    cookies = GetRequestsSessionCookieJar( ambiguous_session )
    
    cookies.clear_expired_cookies()
    
    EnsureSessionCookiesAreSynced( ambiguous_session, cookies )
    

def EnsureSessionCookiesAreSynced( ambiguous_session, requests_cookies: requests.sessions.RequestsCookieJar ):
    """
    User just altered the cookie jar. If this jar is actually some temp dupe, let's set it back.
    """
    
    if ClientNetworkingCurlCFFI.SessionIsCurlCFFI( ambiguous_session ):
        
        ClientNetworkingCurlCFFI.SetCURLCFFISessionCookiesWithRequestsCookieJar( ambiguous_session, requests_cookies )
        
    

def GetRequestsSessionCookieJar( ambiguous_session ) -> requests.sessions.RequestsCookieJar:
    
    if ClientNetworkingCurlCFFI.SessionIsCurlCFFI( ambiguous_session ):
        
        return ClientNetworkingCurlCFFI.GetRequestsCookiesFromCurlCFFISession( ambiguous_session )
        
    else:
        
        return ambiguous_session.cookies
        
    

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
        
        if session is None:
            
            session = self._CreateEmptySession()
            
        
        self.session = session
        self.last_touched_time = HydrusTime.GetNow()
        
        self.pool_is_cleared = True
        self.printed_connection_pool_error = False
        
    
    def _CreateEmptySession( self ):
        
        if DOING_CURL_CFFI_TEST:
            
            if CURL_CFFI_DEFINITION == '' or CURL_CFFI_HTTP_VERSION == -1:
                
                raise Exception( 'The curl cffi test was engaged without correct initialisation??' )
                
            
            session = ClientNetworkingCurlCFFI.CreateCurlCFFISession( CURL_CFFI_DEFINITION, CURL_CFFI_HTTP_VERSION )
            
        else:
            
            session = requests.Session()
            
        
        if self.network_context.context_type == CC.NETWORK_CONTEXT_HYDRUS:
            
            session.verify = False
            
        
        return session
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_network_context = self.network_context.GetSerialisableTuple()
        
        cookies = GetRequestsSessionCookieJar( self.session )
        
        cookies.clear_session_cookies()
        
        pickled_cookies_hex = pickle.dumps( cookies ).hex()
        
        return ( serialisable_network_context, pickled_cookies_hex )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_network_context, pickled_cookies_hex ) = serialisable_info
        
        self.network_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_network_context )
        
        self.session = self._CreateEmptySession()
        
        # TODO: Replace with actual http.cookiejar inspection/reconstruction
        # since we now know how what we are dealing with, we could replace this pickling with actual iteration of http.cookie objects if we were careful, even to the specific fields
        
        try:
            
            cookies = typing.cast( requests.sessions.RequestsCookieJar, pickle.loads( bytes.fromhex( pickled_cookies_hex ) ) )
            
            cookies.clear_session_cookies()
            
            if ClientNetworkingCurlCFFI.SessionIsCurlCFFI( self.session ):
                
                ClientNetworkingCurlCFFI.SetCURLCFFISessionCookiesWithRequestsCookieJar( self.session, cookies )
                
            else:
                
                self.session.cookies = cookies
                
            
        except Exception as e:
            
            HydrusData.Print( "Could not load and set cookies for session {}".format( self.network_context ) )
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_network_context, pickled_session_hex ) = old_serialisable_info
            
            try:
                
                session = pickle.loads( bytes.fromhex( pickled_session_hex ) )
                
            except Exception as e:
                
                session = requests.Session()
                
            
            cookies = GetRequestsSessionCookieJar( session )
            
            pickled_cookies_hex = pickle.dumps( cookies ).hex()
            
            new_serialisable_info = ( serialisable_network_context, pickled_cookies_hex )
            
            return ( 2, new_serialisable_info )
            
        
    
    def MaintainConnectionPool( self ):
        
        if ClientNetworkingCurlCFFI.SessionIsCurlCFFI( self.session ):
            
            return
            
        
        if not self.pool_is_cleared and HydrusTime.TimeHasPassed( self.last_touched_time + self.POOL_CONNECTION_TIMEOUT ):
            
            try:
                
                my_session_adapters = list( self.session.adapters.values() )
                
                for adapter in my_session_adapters:
                    
                    poolmanager = getattr( adapter, 'poolmanager', None )
                    
                    if poolmanager is not None:
                        
                        poolmanager.clear()
                        
                    
                
                self.pool_is_cleared = True
                self.last_touched_time = HydrusTime.GetNow()
                
            except Exception as e:
                
                if not self.printed_connection_pool_error:
                    
                    self.printed_connection_pool_error = True
                    
                    HydrusData.Print( 'There was a problem clearing the connection pool. The full error should follow. To stop spam, this message will only show one time per program boot. The error may happen again, silently.' )
                    HydrusData.PrintException( e, do_wait = False )
                    
                
            
        
    
    def PrepareForNewWork( self ):
        
        if HydrusTime.TimeHasPassed( self.last_touched_time + self.SESSION_TIMEOUT ):
            
            cookies = GetRequestsSessionCookieJar( self.session )
            
            cookies.clear_session_cookies()
            
            EnsureSessionCookiesAreSynced( self.session, cookies )
            
        
        ClearExpiredCookies( self.session )
        
        self.last_touched_time = HydrusTime.GetNow()
        self.pool_is_cleared = False
        
    
    def ReinitialiseSession( self ):
        """
        The server just rewangled the network connection settings on this domain, so we need to regen while preserving gubbins.
        """
        
        old_session = self.session
        
        new_session = self._CreateEmptySession()
        
        cookies = GetRequestsSessionCookieJar( old_session )
        
        AddCookiesToSessionActualCookies( new_session, [ cookie for cookie in cookies ] )
        
        new_session.verify = old_session.verify
        new_session.proxies = old_session.proxies
        
        self.session = new_session
        
    

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
        
        self._session_container_names_to_session_containers: dict[ str, NetworkSessionManagerSessionContainer ] = {}
        self._network_contexts_to_session_containers: dict[ ClientNetworkingContexts.NetworkContext, NetworkSessionManagerSessionContainer ] = {}
        
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
            
        
        # a failsafe to handle tldextract
        # if we have previously put session info in a larger, higher-level bucket, we'll use (keep using) that instead
        if network_context.context_type == CC.NETWORK_CONTEXT_DOMAIN:
            
            larger_umbrella_domain = network_context.context_data
            
            while larger_umbrella_domain.count( '.' ) > 1:
                
                larger_umbrella_domain = ClientNetworkingFunctions.ConvertDomainIntoNextLevelDomain( larger_umbrella_domain )
                
                larger_umbrella_network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, larger_umbrella_domain ) 
                
                if larger_umbrella_network_context in self._network_contexts_to_session_containers:
                    
                    return larger_umbrella_network_context
                    
                
            
        
        return network_context
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._session_container_names = set( serialisable_info )
        
    
    def _InitialiseSessionContainer( self, network_context ):
        
        session_container_name = HydrusData.GenerateKey().hex()
        
        session_container = NetworkSessionManagerSessionContainer( session_container_name, network_context = network_context )
        
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
            
        
    
    def ReinitialiseSessions( self ):
        
        # TODO: This could take a list of network contexts, optionally, so you could filter it just to those with changes
        with self._lock:
            
            for session_container in self._network_contexts_to_session_containers.values():
                
                session_container.ReinitialiseSession()
                
            
        
    
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
