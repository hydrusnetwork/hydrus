import ClientConstants as CC
import collections
import cPickle
import cStringIO
import HydrusConstants as HC
import HydrusExceptions
import HydrusNetwork
import HydrusNetworking
import HydrusPaths
import HydrusSerialisable
import errno
import httplib
import os
import random
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import socket
import socks
import ssl
import threading
import time
import traceback
import urllib
import urlparse
import yaml
import HydrusData
import itertools
import HydrusGlobals as HG

urllib3.disable_warnings( InsecureRequestWarning )

def AddHydrusCredentialsToHeaders( credentials, request_headers ):
    
    if credentials.HasAccessKey():
        
        access_key = credentials.GetAccessKey()
        
        request_headers[ 'Hydrus-Key' ] = access_key.encode( 'hex' )
        
    else:
        
        raise Exception( 'No access key!' )
        
    
def AddHydrusSessionKeyToHeaders( service_key, request_headers ):
    
    session_manager = HG.client_controller.GetClientSessionManager()
    
    session_key = session_manager.GetSessionKey( service_key )
    
    request_headers[ 'Cookie' ] = 'session_key=' + session_key.encode( 'hex' )
    
def AddCookiesToHeaders( cookies, request_headers ):
    
    request_headers[ 'Cookie' ] = '; '.join( [ k + '=' + v for ( k, v ) in cookies.items() ] )
    
def CheckHydrusVersion( service_key, service_type, response_headers ):
    
    service_string = HC.service_string_lookup[ service_type ]
    
    if 'server' not in response_headers or service_string not in response_headers[ 'server' ]:
        
        raise HydrusExceptions.WrongServiceTypeException( 'Target was not a ' + service_string + '!' )
        
    
    server_header = response_headers[ 'server' ]
    
    ( service_string_gumpf, network_version ) = server_header.split( '/' )
    
    network_version = int( network_version )
    
    if network_version != HC.NETWORK_VERSION:
        
        if network_version > HC.NETWORK_VERSION:
            
            message = 'Your client is out of date; please download the latest release.'
            
        else:
            
            message = 'The server is out of date; please ask its admin to update to the latest release.'
            
        
        raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! The server\'s network version was ' + str( network_version ) + ', whereas your client\'s is ' + str( HC.NETWORK_VERSION ) + '! ' + message )
        
    
def ConvertDomainIntoAllApplicableDomains( domain ):
    
    domains = []
    
    while domain.count( '.' ) > 0:
        
        # let's discard www.blah.com so we don't end up tracking it separately to blah.com--there's not much point!
        startswith_www = domain.count( '.' ) > 1 and domain.startswith( 'www' )
        
        if not startswith_www:
            
            domains.append( domain )
            
        
        domain = '.'.join( domain.split( '.' )[1:] ) # i.e. strip off the leftmost subdomain maps.google.com -> google.com
        
    
    return domains
    
def ConvertStatusCodeAndDataIntoExceptionInfo( status_code, data ):
    
    error_text = data
    
    if len( error_text ) > 1024:
        
        large_chunk = error_text[:4096]
        
        smaller_chunk = large_chunk[:256]
        
        HydrusData.DebugPrint( large_chunk )
        
        error_text = 'The server\'s error text was too long to display. The first part follows, while a larger chunk has been written to the log.'
        error_text += os.linesep
        error_text += smaller_chunk
        
    
    if status_code == 304:
        
        eclass = HydrusExceptions.NotModifiedException
        
    elif status_code == 401:
        
        eclass = HydrusExceptions.PermissionException
        
    elif status_code == 403:
        
        eclass = HydrusExceptions.ForbiddenException
        
    elif status_code == 404:
        
        eclass = HydrusExceptions.NotFoundException
        
    elif status_code == 419:
        
        eclass = HydrusExceptions.SessionException
        
    elif status_code == 426:
        
        eclass = HydrusExceptions.NetworkVersionException
        
    elif status_code >= 500:
        
        eclass = HydrusExceptions.ServerException
        
    else:
        
        eclass = HydrusExceptions.NetworkException
        
    
    e = eclass( error_text )
    
    return ( e, error_text )
    
def ConvertURLIntoDomain( url ):
    
    parser_result = urlparse.urlparse( url )
    
    domain = HydrusData.ToByteString( parser_result.netloc )
    
    return domain
    
def RequestsGet( url, params = None, stream = False, headers = None ):
    
    if headers is None:
        
        headers = {}
        
    
    headers[ 'User-Agent' ] = 'hydrus/' + str( HC.NETWORK_VERSION )
    
    response = requests.get( url, params = params, stream = stream, headers = headers )
    
    RequestsCheckResponse( response )
    
    return response
    
# this is an old redirect thing to figure out redirected gallery page destinations without hitting them now. note the allow_redirects param
def RequestsGetRedirectURL( url, session  = None ):
    
    if session is None:
        
        session = requests.Session()
        
    
    response = session.get( url, allow_redirects = False )
    
    if 'location' in response.headers:
        
        location_header = response.headers[ 'location' ]
        
        new_url = urlparse.urljoin( url, location_header )
        
        return new_url
        
    else:
        
        return url
        
    
def RequestsPost( url, data = None, files = None, headers = None ):
    
    if headers is None:
        
        headers = {}
        
    
    headers[ 'User-Agent' ] = 'hydrus/' + str( HC.NETWORK_VERSION )
    
    response = requests.post( url, data = data, files = files )
    
    RequestsCheckResponse( response )
    
    return response
    
def RequestsCheckResponse( response ):
    
    if not response.ok:
        
        error_text = response.content
        
        if len( error_text ) > 1024:
            
            large_chunk = error_text[:4096]
            
            smaller_chunk = large_chunk[:256]
            
            HydrusData.DebugPrint( large_chunk )
            
            error_text = 'The server\'s error text was too long to display. The first part follows, while a larger chunk has been written to the log.'
            error_text += os.linesep
            error_text += smaller_chunk
            
        
        if response.status_code == 304:
            
            eclass = HydrusExceptions.NotModifiedException
            
        elif response.status_code == 401:
            
            eclass = HydrusExceptions.PermissionException
            
        elif response.status_code == 403:
            
            eclass = HydrusExceptions.ForbiddenException
            
        elif response.status_code == 404:
            
            eclass = HydrusExceptions.NotFoundException
            
        elif response.status_code == 419:
            
            eclass = HydrusExceptions.SessionException
            
        elif response.status_code == 426:
            
            eclass = HydrusExceptions.NetworkVersionException
            
        elif response.status_code >= 500:
            
            eclass = HydrusExceptions.ServerException
            
        else:
            
            eclass = HydrusExceptions.NetworkException
            
        
        raise eclass( error_text )
        
    
def ParseURL( url ):
    
    try:
        
        if url.startswith( '//' ):
            
            url = url[2:]
            
        
        starts_http = url.startswith( 'http://' )
        starts_https = url.startswith( 'https://' )
        
        if not starts_http and not starts_https:
            
            url = 'http://' + url
            
        
        parse_result = urlparse.urlparse( url )
        
        scheme = parse_result.scheme
        hostname = parse_result.hostname
        port = parse_result.port
        
        if hostname is None: location = None
        else: location = ( scheme, hostname, port )
        
        path = parse_result.path
        
        # this happens when parsing 'index.html' rather than 'hostname/index.html' or '/index.html'
        if not path.startswith( '/' ):
            
            path = '/' + path
            
        
        query = parse_result.query
        
    except:
        
        raise Exception( 'Could not parse the URL: ' + HydrusData.ToUnicode( url ) )
        
    
    return ( location, path, query )
    
def SerialiseSession( session ):
    
    # move this to the new sessionmanager
    
    cookies = session.cookies.copy()
    
    items = requests.utils.dict_from_cookiejar( cookies )
    
    # apply these to something serialisable
    
    # do the reverse, add_dict_to_cookiejar, to set them back again in a new session
    
def SetProxy( proxytype, host, port, username = None, password = None ):
    
    if proxytype == 'http': proxytype = socks.PROXY_TYPE_HTTP
    elif proxytype == 'socks4': proxytype = socks.PROXY_TYPE_SOCKS4
    elif proxytype == 'socks5': proxytype = socks.PROXY_TYPE_SOCKS5
    
    socks.setdefaultproxy( proxy_type = proxytype, addr = host, port = port, username = username, password = password )
    
    socks.wrapmodule( httplib )
    
def StreamResponseToFile( job_key, response, f ):
    
    if 'content-length' in response.headers:
        
        gauge_range = int( response.headers[ 'content-length' ] )
        
    else:
        
        gauge_range = None
        
    
    gauge_value = 0
    
    try:
        
        for chunk in response.iter_content( chunk_size = 65536 ):
            
            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
            
            if should_quit:
                
                raise HydrusExceptions.CancelledException()
                
            
            f.write( chunk )
            
            gauge_value += len( chunk )
            
            if gauge_range is None:
                
                text = 'downloading - ' + HydrusData.ConvertIntToBytes( gauge_value )
                
            else:
                
                text = 'downloading - '  + HydrusData.ConvertValueRangeToBytes( gauge_value, gauge_range )
                
            
            job_key.SetVariable( 'popup_download', ( text, gauge_value, gauge_range ) )
            
        
    finally:
        
        job_key.DeleteVariable( 'popup_download' )
        
    
class HTTPConnectionManager( object ):
    
    def __init__( self ):
        
        self._connections = {}
        
        self._lock = threading.Lock()
        
        HG.client_controller.CallToThreadLongRunning( self.DAEMONMaintainConnections )
        
    
    def _DoRequest( self, method, location, path, query, request_headers, body, follow_redirects = True, report_hooks = None, temp_path = None, hydrus_network = False, num_redirects_permitted = 4 ):
        
        if report_hooks is None: report_hooks = []
        
        connection = self._GetConnection( location, hydrus_network )
        
        try:
            
            if query == '':
                
                path_and_query = path
                
            else:
                
                path_and_query = path + '?' + query
                
            
            with connection.lock:
                
                ( parsed_response, redirect_info, size_of_response, response_headers, cookies ) = connection.Request( method, path_and_query, request_headers, body, report_hooks = report_hooks, temp_path = temp_path )
                
            
            if redirect_info is None or not follow_redirects:
                
                return ( parsed_response, size_of_response, response_headers, cookies )
                
            else:
                
                if num_redirects_permitted == 0:
                    
                    message = 'Too many redirects!'
                    message += os.linesep
                    message += 'Location was: ' + HydrusData.ToUnicode( location ) + ' and path and query was ' + path_and_query + '.'
                    message += os.linesep
                    message += 'Redirect info was: ' + HydrusData.ToUnicode( redirect_info )
                    
                    raise HydrusExceptions.RedirectionException( message )
                    
                
                ( new_method, new_url ) = redirect_info
                
                ( new_location, new_path, new_query ) = ParseURL( new_url )
                
                if new_location is None:
                    
                    new_location = location
                    
                
                if new_method == method and new_location == location and new_path == path and new_query == query:
                    
                    message = 'Encountered a circular redirect!'
                    message += os.linesep
                    message += 'Location was: ' + HydrusData.ToUnicode( location ) + ' and path and query was ' + path_and_query + '.'
                    message += os.linesep
                    message += 'Redirect info was: ' + HydrusData.ToUnicode( redirect_info )
                    
                    raise HydrusExceptions.RedirectionException( message )
                    
                
                return self._DoRequest( new_method, new_location, new_path, new_query, request_headers, body, follow_redirects = follow_redirects, report_hooks = report_hooks, temp_path = temp_path, num_redirects_permitted = num_redirects_permitted - 1 )
                
            
        except:
            
            time.sleep( 2 )
            
            raise
            
        
    
    def _GetConnection( self, location, hydrus_network ):
        
        with self._lock:
            
            if ( location, hydrus_network ) not in self._connections:
                
                connection = HTTPConnection( location, hydrus_network )
                
                self._connections[ ( location, hydrus_network ) ] = connection
                
            
            return self._connections[ ( location, hydrus_network ) ]
            
        
    
    def Request( self, method, url, request_headers = None, body = '', return_cookies = False, report_hooks = None, temp_path = None, hydrus_network = False ):
        
        if request_headers is None: request_headers = {}
        
        ( location, path, query ) = ParseURL( url )
        
        follow_redirects = not return_cookies
        
        ( response, size_of_response, response_headers, cookies ) = self._DoRequest( method, location, path, query, request_headers, body, follow_redirects = follow_redirects, report_hooks = report_hooks, temp_path = temp_path, hydrus_network = hydrus_network )
        
        if hydrus_network:
            
            return ( response, size_of_response, response_headers, cookies )
            
        elif return_cookies:
            
            return ( response, cookies )
            
        else:
            
            return response
            
        
    
    def DAEMONMaintainConnections( self ):
        
        while True:
            
            if HG.model_shutdown:
                
                break
                
            
            last_checked = 0
            
            if HydrusData.GetNow() - last_checked > 30:
                
                with self._lock:
                    
                    connections_copy = dict( self._connections )
                    
                    for ( ( location, hydrus_network ), connection ) in connections_copy.items():
                        
                        with connection.lock:
                            
                            if connection.IsStale():
                                
                                connection.Close()
                                
                                del self._connections[ ( location, hydrus_network ) ]
                                
                            
                        
                    
                
                last_checked = HydrusData.GetNow()
                
            
            time.sleep( 5 )
            
        
    
class HTTPConnection( object ):
    
    def __init__( self, location, hydrus_network ):
        
        ( self._scheme, self._host, self._port ) = location
        
        self._hydrus_network = hydrus_network
        
        self._timeout = 30
        
        self.lock = threading.Lock()
        
        self._last_request_time = HydrusData.GetNow()
        
        self._connection = None
        
        self._RefreshConnection()
        
    
    def _DealWithResponse( self, method, response, parsed_response, size_of_response ):
        
        response_headers = { k : v for ( k, v ) in response.getheaders() if k != 'set-cookie' }
        
        cookies = self._ParseCookies( response.getheader( 'set-cookie' ) )
        
        self._last_request_time = HydrusData.GetNow()
        
        if response.status == 200:
            
            return ( parsed_response, None, size_of_response, response_headers, cookies )
            
        elif response.status in ( 301, 302, 303, 307 ):
            
            location = response.getheader( 'Location' )
            
            if location is None:
                
                raise Exception( 'Received an invalid redirection response.' )
                
            else:
                
                url = location
                
                if ', ' in url:
                    
                    url = url.split( ', ' )[0]
                    
                elif ' ' in url:
                    
                    # some booru is giving daft redirect responses
                    HydrusData.Print( url )
                    url = urllib.quote( HydrusData.ToByteString( url ), safe = '/?=&' )
                    HydrusData.Print( url )
                    
                
                if not url.startswith( self._scheme ):
                    
                    # assume it is like 'index.php' or '/index.php', rather than 'http://blah.com/index.php'
                    
                    if url.startswith( '//' ):
                        
                        url = self._scheme + ':' + url
                        
                    else:
                        
                        if not url.startswith( '/' ):
                            
                            url = '/' + url
                            
                        
                        url = self._scheme + '://' + self._host + url
                        
                    
                
                if response.status in ( 301, 307 ):
                    
                    # 301: moved permanently, repeat request
                    # 307: moved temporarily, repeat request
                    
                    redirect_info = ( method, url )
                    
                elif response.status in ( 302, 303 ):
                    
                    # 302: moved temporarily, repeat request (except everyone treats it like 303 for no good fucking reason)
                    # 303: thanks, now go here with GET
                    
                    redirect_info = ( HC.GET, url )
                    
                
                return ( parsed_response, redirect_info, size_of_response, response_headers, cookies )
                
            
        elif response.status == 304: raise HydrusExceptions.NotModifiedException()
        else:
            
            if response.status == 401: raise HydrusExceptions.PermissionException( parsed_response )
            elif response.status == 403: raise HydrusExceptions.ForbiddenException( parsed_response )
            elif response.status == 404: raise HydrusExceptions.NotFoundException( parsed_response )
            elif response.status == 419: raise HydrusExceptions.SessionException( parsed_response )
            elif response.status == 426: raise HydrusExceptions.NetworkVersionException( parsed_response )
            elif response.status == 509: raise HydrusExceptions.BandwidthException( parsed_response )
            elif response.status in ( 500, 501, 502, 503 ):
                
                server_header = response.getheader( 'Server' )
                
                if server_header is not None and 'hydrus' in server_header:
                    
                    hydrus_service = True
                    
                else:
                    
                    hydrus_service = False
                    
                
                if response.status == 503 and hydrus_service:
                    
                    raise HydrusExceptions.ServerBusyException( 'Server is busy, please try again later.' )
                    
                else:
                    
                    raise HydrusExceptions.ServerException( parsed_response )
                    
                
            else:
                
                raise HydrusExceptions.NetworkException( parsed_response )
                
            
        
    
    def _SendRequestGetResponse( self, method, path_and_query, request_headers, body, report_hooks = None, temp_path = None, attempt_number = 1 ):
        
        if report_hooks is None:
            
            report_hooks = []
            
        
        if 'User-Agent' not in request_headers:
            
            request_headers[ 'User-Agent' ] = 'hydrus/' + str( HC.NETWORK_VERSION )
            
        
        if 'Accept' not in request_headers:
            
            request_headers[ 'Accept' ] = '*/*'
            
        
        path_and_query = HydrusData.ToByteString( path_and_query )
        
        request_headers = { str( k ) : str( v ) for ( k, v ) in request_headers.items() }
        
        ( response, attempt_number ) = self._GetInitialResponse( method, path_and_query, request_headers, body, attempt_number = attempt_number )
        
        try:
            
            ( parsed_response, size_of_response ) = self._ReadResponse( method, response, report_hooks, temp_path )
            
            return ( response, parsed_response, size_of_response )
            
        except HydrusExceptions.ShouldReattemptNetworkException:
            
            if method == HC.GET:
                
                self._RefreshConnection()
                
                return self._SendRequestGetResponse( method, path_and_query, request_headers, body, report_hooks = report_hooks, temp_path = temp_path, attempt_number = attempt_number + 1 )
                
            else:
                
                raise
                
            
        
    
    def _GetInitialResponse( self, method, path_and_query, request_headers, body, attempt_number = 1 ):
        
        if method == HC.GET: method_string = 'GET'
        elif method == HC.POST: method_string = 'POST'
        
        try:
            
            self._connection.request( method_string, path_and_query, headers = request_headers, body = body )
            
            return ( self._connection.getresponse(), attempt_number )
            
        except ( httplib.CannotSendRequest, httplib.BadStatusLine ):
            
            # for some reason, we can't send a request on the current connection, so let's make a new one and try again!
            
            time.sleep( 1 )
            
            if attempt_number <= 3:
                
                self._RefreshConnection()
                
                return self._GetInitialResponse( method, path_and_query, request_headers, body, attempt_number = attempt_number + 1 )
                
            else:
                
                raise
                
            
        except socket.error as e:
            
            if HC.PLATFORM_WINDOWS:
                
                access_errors = [ errno.EACCES, errno.WSAEACCES ]
                connection_reset_errors = [ errno.ECONNRESET, errno.WSAECONNRESET ]
                
            else:
                
                access_errors = [ errno.EACCES ]
                connection_reset_errors = [ errno.ECONNRESET ]
                
            
            if e.errno in access_errors:
                
                text = 'The hydrus client did not have permission to make a connection to ' + HydrusData.ToUnicode( self._host )
                
                if self._port is not None:
                    
                    text += ' on port ' + HydrusData.ToUnicode( self._port )
                    
                
                text += '. This is usually due to a firewall stopping it.'
                
                raise HydrusExceptions.FirewallException( text )
                
            elif e.errno in connection_reset_errors:
                
                time.sleep( 5 )
                
                if attempt_number <= 3:
                    
                    self._RefreshConnection()
                    
                    return self._GetInitialResponse( method, path_and_query, request_headers, body, attempt_number = attempt_number + 1 )
                    
                else:
                    
                    text = 'The hydrus client\'s connection to ' + HydrusData.ToUnicode( self._host ) + ' kept on being reset by the remote host, so the attempt was abandoned.'
                    
                    raise HydrusExceptions.NetworkException( text )
                    
                
            else:
                
                raise
                
            
        except ssl.SSLEOFError:
            
            time.sleep( 5 )
            
            if attempt_number <= 3:
                
                self._RefreshConnection()
                
                return self._GetInitialResponse( method_string, path_and_query, request_headers, body, attempt_number = attempt_number + 1 )
                
            else:
                
                text = 'The hydrus client\'s ssl connection to ' + HydrusData.ToUnicode( self._host ) + ' kept terminating abruptly, so the attempt was abandoned.'
                
                raise HydrusExceptions.NetworkException( text )
                
            
        
    
    def _ReadResponse( self, method, response, report_hooks, temp_path = None ):
        
        # in general, don't want to resend POSTs
        if method == HC.GET:
            
            recoverable_exc = HydrusExceptions.ShouldReattemptNetworkException
            
        else:
            
            recoverable_exc = HydrusExceptions.NetworkException
            
        
        try:
            
            if response.status == 200 and temp_path is not None:
                
                size_of_response = self._WriteResponseToPath( response, temp_path, report_hooks )
                
                parsed_response = 'response written to temporary file'
                
            else:
                
                ( parsed_response, size_of_response ) = self._ParseResponse( response, report_hooks )
                
            
        except socket.timeout as e:
            
            raise recoverable_exc( 'Connection timed out during response read.' )
            
        except socket.error as e:
            
            if HC.PLATFORM_WINDOWS:
                
                connection_reset_errors = [ errno.ECONNRESET, errno.WSAECONNRESET ]
                
            else:
                
                connection_reset_errors = [ errno.ECONNRESET ]
                
            
            if e.errno in connection_reset_errors:
                
                raise recoverable_exc( 'Connection reset by remote host.' )
                
            else:
                
                raise
                
            
        except ssl.SSLEOFError:
            
            raise recoverable_exc( 'Secure connection terminated abruptly.' )
            
        
        return ( parsed_response, size_of_response )
        
    
    def _ParseCookies( self, raw_cookies_string ):
        
        cookies = {}
        
        if raw_cookies_string is not None:
            
            raw_cookie_strings = raw_cookies_string.split( ', ' )
            
            for raw_cookie_string in raw_cookie_strings:
                
                try:
                    
                    # HSID=AYQEVnDKrdst; Domain=.foo.com; Path=/; Expires=Wed, 13 Jan 2021 22:23:01 GMT; HttpOnly
                    
                    if ';' in raw_cookie_string: ( raw_cookie_string, gumpf ) = raw_cookie_string.split( ';', 1 )
                    
                    ( cookie_name, cookie_value ) = raw_cookie_string.split( '=' )
                    
                    cookies[ cookie_name ] = cookie_value
                    
                except Exception as e: pass
                
            
        
        return cookies
        
    
    def _ParseResponse( self, response, report_hooks ):
        
        server_header = response.getheader( 'Server' )
        
        if server_header is not None and 'hydrus' in server_header:
            
            hydrus_service = True
            
        else:
            
            hydrus_service = False
            
        
        content_length = response.getheader( 'Content-Length' )
        
        if content_length is not None:
            
            content_length = int( content_length )
            
            for hook in report_hooks:
                
                hook( content_length, 0 )
                
            
        
        data = ''
        
        for block in HydrusPaths.ReadFileLikeAsBlocks( response ):
            
            if HG.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application is shutting down!' )
                
            
            data += block
            
            if content_length is not None:
                
                for hook in report_hooks:
                    
                    hook( content_length, len( data ) )
                    
                
                if len( data ) > content_length:
                    
                    raise Exception( 'Response was longer than suggested!' )
                    
                
            
        
        size_of_response = len( data )
        
        content_type = response.getheader( 'Content-Type' )
        
        if content_type is None: parsed_response = data
        else:
            
            if '; ' in content_type: ( mime_string, additional_info ) = content_type.split( '; ', 1 )
            else: ( mime_string, additional_info ) = ( content_type, '' )
            
            if 'charset=' in additional_info:
        
                # this does utf-8, ISO-8859-4, whatever
                
                ( gumpf, charset ) = additional_info.split( '=' )
                
                try: parsed_response = data.decode( charset )
                except: parsed_response = data
                
            elif content_type == 'application/json':
                
                if hydrus_service:
                    
                    parsed_response = HydrusNetwork.ParseBodyString( data )
                    
                else:
                    
                    parsed_response = data
                    
                
            elif content_type == 'text/html':
                
                try: parsed_response = data.decode( 'utf-8' )
                except: parsed_response = data
                
            else: parsed_response = data
            
        
        return ( parsed_response, size_of_response )
        
    
    def _RefreshConnection( self ):
        
        if self._scheme == 'http':
            
            self._connection = httplib.HTTPConnection( self._host, self._port, timeout = self._timeout )
            
        elif self._scheme == 'https':
            
            new_options = HG.client_controller.GetNewOptions()
            
            if self._hydrus_network or not new_options.GetBoolean( 'verify_regular_https' ):
                
                # this negotiates decent encryption but won't check hostname or the certificate
                
                context = ssl.SSLContext( ssl.PROTOCOL_SSLv23 )
                
                context.options |= ssl.OP_NO_SSLv2
                context.options |= ssl.OP_NO_SSLv3
                
                self._connection = httplib.HTTPSConnection( self._host, self._port, timeout = self._timeout, context = context )
                
            else:
                
                context = ssl._create_default_https_context( cafile = requests.certs.where() )
                
                self._connection = httplib.HTTPSConnection( self._host, self._port, timeout = self._timeout, context = context )
                
            
        
        try:
            
            self._connection.connect()
            
        except Exception as e:
            
            text = 'Could not connect to ' + HydrusData.ToUnicode( self._host ) + ':'
            text += os.linesep * 2
            text += HydrusData.ToUnicode( e )
            
            raise HydrusExceptions.NetworkException( text )
            
        
    
    def _WriteResponseToPath( self, response, temp_path, report_hooks ):
        
        content_length = response.getheader( 'Content-Length' )
        
        if content_length is not None: content_length = int( content_length )
        
        size_of_response = 0
        
        with open( temp_path, 'wb' ) as f:
            
            for block in HydrusPaths.ReadFileLikeAsBlocks( response ):
                
                if HG.model_shutdown:
                    
                    raise HydrusExceptions.ShutdownException( 'Application is shutting down!' )
                    
                
                size_of_response += len( block )
                
                if content_length is not None and size_of_response > content_length:
                    
                    raise Exception( 'Response was longer than suggested!' )
                    
                
                f.write( block )
                
                for hook in report_hooks:
                    
                    if content_length is not None:
                        
                        hook( content_length, size_of_response )
                        
                    
                
            
        
        return size_of_response
        
    
    def Close( self ):
        
        if self._connection is not None:
            
            self._connection.close()
            
        
    
    def IsStale( self ):
        
        time_since_last_request = HydrusData.GetNow() - self._last_request_time
        
        return time_since_last_request > self._timeout
        
    
    def Request( self, method, path_and_query, request_headers, body, report_hooks = None, temp_path = None ):
        
        ( response, parsed_response, size_of_response ) = self._SendRequestGetResponse( method, path_and_query, request_headers, body, report_hooks = report_hooks, temp_path = temp_path )
        
        return self._DealWithResponse( method, response, parsed_response, size_of_response )
        
    
class NetworkBandwidthManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_BANDWIDTH_MANAGER
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._network_contexts_to_bandwidth_trackers = collections.defaultdict( HydrusNetworking.BandwidthTracker )
        self._network_contexts_to_bandwidth_rules = collections.defaultdict( HydrusNetworking.BandwidthRules )
        
        for context_type in [ CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_HYDRUS, CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_DOWNLOADER, CC.NETWORK_CONTEXT_DOWNLOADER_QUERY, CC.NETWORK_CONTEXT_SUBSCRIPTION, CC.NETWORK_CONTEXT_THREAD_WATCHER_THREAD ]:
            
            self._network_contexts_to_bandwidth_rules[ NetworkContext( context_type ) ] = HydrusNetworking.BandwidthRules()
            
        
    
    def _CanStartRequest( self, network_contexts ):
        
        for network_context in network_contexts:
            
            bandwidth_rules = self._GetRules( network_context )
            
            bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
            
            if not bandwidth_rules.CanStartRequest( bandwidth_tracker ):
                
                return False
                
            
        
        return True
        
    
    def _GetRules( self, network_context ):
        
        if network_context not in self._network_contexts_to_bandwidth_rules:
            
            network_context = NetworkContext( network_context.context_type ) # i.e. the default
            
        
        return self._network_contexts_to_bandwidth_rules[ network_context ]
        
    
    def _GetSerialisableInfo( self ):
        
        # note this discards ephemeral network contexts, which have page_key-specific identifiers and are temporary, not meant to be hung onto forever, and are generally invisible to the user
        all_serialisable_trackers = [ ( network_context.GetSerialisableTuple(), tracker.GetSerialisableTuple() ) for ( network_context, tracker ) in self._network_contexts_to_bandwidth_trackers.items() if not network_context.IsEphemeral() ]
        all_serialisable_rules = [ ( network_context.GetSerialisableTuple(), rules.GetSerialisableTuple() ) for ( network_context, rules ) in self._network_contexts_to_bandwidth_rules.items() ]
        
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
            
            self._network_contexts_to_bandwidth_rules[ network_context ] = rules
            
        
    
    def _ReportRequestUsed( self, network_contexts ):
        
        for network_context in network_contexts:
            
            self._network_contexts_to_bandwidth_trackers[ network_context ].ReportRequestUsed()
            
        
        self._SetDirty()
        
    
    def _SetDirty( self ):
        
        self._dirty = True
        
    
    def CanContinueDownload( self, network_contexts ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
                
                if not bandwidth_rules.CanContinueDownload( bandwidth_tracker ):
                    
                    return False
                    
                
            
            return True
            
        
    
    def CanDoWork( self, network_contexts, expected_requests = 3, expected_bytes = 1048576 ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
                
                if not bandwidth_rules.CanDoWork( bandwidth_tracker, expected_requests, expected_bytes ):
                    
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
                
                if network_context in self._network_contexts_to_bandwidth_trackers:
                    
                    del self._network_contexts_to_bandwidth_trackers[ network_context ]
                    
                    if network_context == GLOBAL_NETWORK_CONTEXT:
                        
                        # just to reset it, so we have a 0 global context at all times
                        self._network_contexts_to_bandwidth_trackers[ GLOBAL_NETWORK_CONTEXT ] = HydrusNetworking.BandwidthTracker()
                        
                    
                
            
            self._SetDirty()
            
        
    
    def GetDefaultRules( self ):
        
        with self._lock:
            
            result = []
            
            for ( network_context, bandwidth_rules ) in self._network_contexts_to_bandwidth_rules.items():
                
                if network_context.IsDefault():
                    
                    result.append( ( network_context, bandwidth_rules ) )
                    
                
            
            return result
            
        
    
    def GetNetworkContextsForUser( self, history_time_delta_threshold = None ):
        
        with self._lock:
            
            result = set()
            
            for ( network_context, bandwidth_rules ) in self._network_contexts_to_bandwidth_rules.items():
                
                if network_context.IsDefault() or network_context.IsEphemeral():
                    
                    continue
                    
                
                # if a context has rules but no activity, list it so the user can edit the rules if needed
                # in case they set too restrictive rules on an old context and now can't get it up again with activity because of the rules!
                
                if network_context not in self._network_contexts_to_bandwidth_trackers or self._network_contexts_to_bandwidth_trackers[ network_context ].GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None ) == 0:
                    
                    result.add( network_context )
                    
                
            
            for ( network_context, bandwidth_tracker ) in self._network_contexts_to_bandwidth_trackers.items():
                
                if network_context.IsDefault() or network_context.IsEphemeral():
                    
                    continue
                    
                
                if network_context != GLOBAL_NETWORK_CONTEXT and history_time_delta_threshold is not None:
                    
                    if bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, history_time_delta_threshold ) == 0:
                        
                        continue
                        
                    
                
                result.add( network_context )
                
            
            return result
            
        
    
    def GetRules( self, network_context ):
        
        with self._lock:
            
            return self._GetRules( network_context )
            
        
    
    def GetTracker( self, network_context ):
        
        with self._lock:
            
            if network_context in self._network_contexts_to_bandwidth_trackers:
                
                return self._network_contexts_to_bandwidth_trackers[ network_context ]
                
            else:
                
                return HydrusNetworking.BandwidthTracker()
                
            
        
    
    def GetWaitingEstimate( self, network_contexts ):
        
        with self._lock:
            
            estimates = []
            
            for network_context in network_contexts:
                
                bandwidth_rules = self._GetRules( network_context )
                
                bandwidth_tracker = self._network_contexts_to_bandwidth_trackers[ network_context ]
                
                estimates.append( bandwidth_rules.GetWaitingEstimate( bandwidth_tracker ) )
                
            
            if len( estimates ) == 0:
                
                return 0
                
            else:
                
                return max( estimates )
                
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def ReportDataUsed( self, network_contexts, num_bytes ):
        
        with self._lock:
            
            for network_context in network_contexts:
                
                self._network_contexts_to_bandwidth_trackers[ network_context ].ReportDataUsed( num_bytes )
                
            
            self._SetDirty()
            
        
    
    def ReportRequestUsed( self, network_contexts ):
        
        with self._lock:
            
            self._ReportRequestUsed( network_contexts )
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetRules( self, network_context, bandwidth_rules ):
        
        with self._lock:
            
            if len( bandwidth_rules.GetRules() ) == 0:
                
                if network_context in self._network_contexts_to_bandwidth_rules:
                    
                    del self._network_contexts_to_bandwidth_rules[ network_context ]
                    
                
            else:
                
                self._network_contexts_to_bandwidth_rules[ network_context ] = bandwidth_rules
                
            
            self._SetDirty()
            
        
    
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

class NetworkContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT
    SERIALISABLE_VERSION = 2
    
    def __init__( self, context_type = None, context_data = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.context_type = context_type
        self.context_data = context_data
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self.context_type, self.context_data ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        return self.ToUnicode()
        
    
    def _GetSerialisableInfo( self ):
        
        if self.context_data is None:
            
            serialisable_context_data = self.context_data
            
        else:
            
            if self.context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_SUBSCRIPTION ):
                
                serialisable_context_data = self.context_data
                
            else:
                
                serialisable_context_data = self.context_data.encode( 'hex' )
                
            
        
        return ( self.context_type, serialisable_context_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.context_type, serialisable_context_data ) = serialisable_info
        
        if serialisable_context_data is None:
            
            self.context_data = serialisable_context_data
            
        else:
            
            if self.context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_SUBSCRIPTION ):
                
                self.context_data = serialisable_context_data
                
            else:
                
                self.context_data = serialisable_context_data.decode( 'hex' )
                
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( context_type, serialisable_context_data ) = old_serialisable_info
            
            if serialisable_context_data is not None:
                
                # unicode subscription names were erroring on the hex call
                if context_type in ( CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_SUBSCRIPTION ):
                    
                    context_data = serialisable_context_data.decode( 'hex' )
                    
                    serialisable_context_data = context_data
                    
                
            
            new_serialisable_info = ( context_type, serialisable_context_data )
            
            return ( 2, new_serialisable_info )
            
        
    
    def IsDefault( self ):
        
        return self.context_data is None and self.context_type != CC.NETWORK_CONTEXT_GLOBAL
        
    
    def IsEphemeral( self ):
        
        return self.context_type in ( CC.NETWORK_CONTEXT_DOWNLOADER_QUERY, CC.NETWORK_CONTEXT_THREAD_WATCHER_THREAD )
        
    
    def ToUnicode( self ):
        
        if self.context_data is None:
            
            if self.context_type == CC.NETWORK_CONTEXT_GLOBAL:
                
                return 'global'
                
            else:
                
                return CC.network_context_type_string_lookup[ self.context_type ] + ' default'
                
            
        else:
            
            return CC.network_context_type_string_lookup[ self.context_type ] + ': ' + HydrusData.ToUnicode( self.context_data )
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_CONTEXT ] = NetworkContext

GLOBAL_NETWORK_CONTEXT = NetworkContext( CC.NETWORK_CONTEXT_GLOBAL )

class NetworkEngine( object ):
    
    MAX_JOBS = 10 # turn this into an option
    
    def __init__( self, controller, bandwidth_manager, session_manager, login_manager ):
        
        self.controller = controller
        
        self.bandwidth_manager = bandwidth_manager
        self.session_manager = session_manager
        self.login_manager = login_manager
        
        self.bandwidth_manager.engine = self
        self.session_manager.engine = self
        self.login_manager.engine = self
        
        self._lock = threading.Lock()
        
        self._new_work_to_do = threading.Event()
        
        self._jobs_bandwidth_throttled = []
        self._jobs_login_throttled = []
        self._current_login_process = None
        self._jobs_ready_to_start = []
        self._jobs_downloading = []
        
        self._is_running = False
        self._is_shutdown = False
        self._local_shutdown = False
        
    
    def AddJob( self, job ):
        
        with self._lock:
            
            job.engine = self
            
            self._jobs_bandwidth_throttled.append( job )
            
        
        self._new_work_to_do.set()
        
    
    def IsRunning( self ):
        
        with self._lock:
            
            return self._is_running
            
        
    
    def IsShutdown( self ):
        
        with self._lock:
            
            return self._is_shutdown
            
        
    
    def MainLoop( self ):
        
        def ProcessBandwidthJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif not job.BandwidthOK():
                
                return True
                
            else:
                
                self._jobs_login_throttled.append( job )
                
                return False
                
            
        
        def ProcessLoginJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif job.IsAsleep():
                
                return True
                
            elif job.NeedsLogin():
                
                if job.CanLogin():
                    
                    if self._current_login_process is None:
                        
                        login_process = job.GenerateLoginProcess()
                        
                        self.controller.CallToThread( login_process.Start )
                        
                        self._current_login_process = login_process
                        
                        job.SetStatus( u'logging in\u2026' )
                        
                    else:
                        
                        job.SetStatus( u'waiting on login\u2026' )
                        
                        job.Sleep( 5 )
                        
                    
                else:
                    
                    job.SetStatus( 'unable to login!' )
                    
                    job.Sleep( 15 )
                    
                
                return True
                
            else:
                
                self._jobs_ready_to_start.append( job )
                
                return False
                
            
        
        def ProcessCurrentLoginJob():
            
            if self._current_login_process is not None:
                
                if self._current_login_process.IsDone():
                    
                    self._current_login_process = None
                    
                
            
        
        def ProcessReadyJob( job ):
            
            if job.IsDone():
                
                return False
                
            elif len( self._jobs_downloading ) < self.MAX_JOBS:
                
                self.controller.CallToThread( job.Start )
                
                self._jobs_downloading.append( job )
                
                return False
                
            else:
                
                job.SetStatus( u'waiting for download slot\u2026' )
                
                return True
                
            
        
        def ProcessDownloadingJob( job ):
            
            if job.IsDone():
                
                return False
                
            else:
                
                return True
                
            
        
        self._is_running = True
        
        while not ( self._local_shutdown or self.controller.ModelIsShutdown() ):
            
            with self._lock:
                
                self._jobs_bandwidth_throttled = filter( ProcessBandwidthJob, self._jobs_bandwidth_throttled )
                
                self._jobs_login_throttled = filter( ProcessLoginJob, self._jobs_login_throttled )
                
                ProcessCurrentLoginJob()
                
                self._jobs_ready_to_start = filter( ProcessReadyJob, self._jobs_ready_to_start )
                
                self._jobs_downloading = filter( ProcessDownloadingJob, self._jobs_downloading )
                
            
            # we want to catch the rollover of the second for bandwidth jobs
            
            now_with_subsecond = time.time()
            subsecond_part = now_with_subsecond % 1
            
            time_until_next_second = 1.0 - subsecond_part
            
            self._new_work_to_do.wait( time_until_next_second )
            
            self._new_work_to_do.clear()
            
        
        self._is_running = False
        
        self._is_shutdown = True
        
    
    def Shutdown( self ):
        
        self._local_shutdown = True
        
        self._new_work_to_do.set()
        
    
class NetworkJob( object ):
    
    MAX_CONNECTION_ATTEMPTS = 5
    
    def __init__( self, method, url, body = None, referral_url = None, temp_path = None, for_login = False ):
        
        if HG.network_report_mode:
            
            HydrusData.ShowText( 'Network Job: ' + method + ' ' + url )
            
        
        self.engine = None
        
        self._lock = threading.Lock()
        
        self._method = method
        self._url = url
        self._body = body
        self._referral_url = referral_url
        self._temp_path = temp_path
        self._for_login = for_login
        
        self._creation_time = HydrusData.GetNow()
        
        self._bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self._wake_time = 0
        
        self._stream_io = cStringIO.StringIO()
        
        self._error_exception = None
        self._error_text = None
        
        self._is_done = False
        self._is_cancelled = False
        self._bandwidth_manual_override = False
        
        self._last_time_ongoing_bandwidth_failed = 0
        
        self._status_text = u'initialising\u2026'
        self._num_bytes_read = 0
        self._num_bytes_to_read = 1
        
        self._network_contexts = self._GenerateNetworkContexts()
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = []
        
        network_contexts.append( GLOBAL_NETWORK_CONTEXT )
        
        domain = ConvertURLIntoDomain( self._url )
        domains = ConvertDomainIntoAllApplicableDomains( domain )
        
        network_contexts.extend( ( NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, domain ) for domain in domains ) )
        
        return network_contexts
        
    
    def _SendRequestAndGetResponse( self ):
        
        with self._lock:
            
            session = self._GetSession()
            
            method = self._method
            url = self._url
            data = self._body
            
            headers = {}
            
            if self._referral_url is not None:
                
                headers = { 'referer' : self._referral_url }
                
            
        
        connection_successful = False
        connection_attempts = 1
        
        while not connection_successful:
            
            try:
                
                with self._lock:
                    
                    self._status_text = u'sending request\u2026'
                    
                
                timeout = HG.client_controller.GetNewOptions().GetInteger( 'network_timeout' )
                
                response = session.request( method, url, data = data, headers = headers, stream = True, timeout = timeout )
                
                connection_successful = True
                
            except requests.exceptions.ConnectionError, requests.exceptions.Timeout:
                
                connection_attempts += 1
                
                if connection_attempts > self.MAX_CONNECTION_ATTEMPTS:
                    
                    raise HydrusExceptions.NetworkException( 'Could not connect!' )
                    
                
                with self._lock:
                    
                    self._status_text = u'connection failed--retrying'
                    
                
                time.sleep( 3 )
                
            
        
        return response
        
    
    def _GetSession( self ):
        
        session_network_context = self._GetSessionNetworkContext()
        
        return self.engine.session_manager.GetSession( session_network_context )
        
    
    def _GetSessionNetworkContext( self ):
        
        return self._network_contexts[-1]
        
    
    def _IsCancelled( self ):
        
        if self._is_cancelled:
            
            return True
            
        
        if self.engine.controller.ModelIsShutdown():
            
            return True
            
        
        return False
        
    
    def _IsDone( self ):
        
        if self._is_done:
            
            return True
            
        
        if self.engine.controller.ModelIsShutdown():
            
            return True
            
        
        return False
        
    
    def _ObeysBandwidth( self ):
        
        return not ( self._bandwidth_manual_override or self._for_login )
        
    
    def _OngoingBandwidthOK( self ):
        
        now = HydrusData.GetNow()
        
        if now == self._last_time_ongoing_bandwidth_failed: # it won't have changed, so no point spending any cpu checking
            
            return False
            
        else:
            
            result = self.engine.bandwidth_manager.CanContinueDownload( self._network_contexts )
            
            if not result:
                
                self._last_time_ongoing_bandwidth_failed = now
                
            
            return result
            
        
    
    def _ReadResponse( self, response, stream_dest ):
        
        with self._lock:
            
            if 'content-length' in response.headers:
            
                self._num_bytes_to_read = int( response.headers[ 'content-length' ] )
                
            else:
                
                self._num_bytes_to_read = None
                
            
        
        for chunk in response.iter_content( chunk_size = 65536 ):
            
            if self._IsCancelled():
                
                return
                
            
            stream_dest.write( chunk )
            
            chunk_length = len( chunk )
            
            with self._lock:
                
                self._num_bytes_read += chunk_length
                
            
            self._ReportDataUsed( chunk_length )
            self._WaitOnOngoingBandwidth()
            
        
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        self._bandwidth_tracker.ReportDataUsed( num_bytes )
        
        self.engine.bandwidth_manager.ReportDataUsed( self._network_contexts, num_bytes )
        
    
    def _SetCancelled( self ):
        
        self._is_cancelled = True
        
        self._SetDone()
        
    
    def _SetError( self, e, error ):
        
        self._error_exception = e
        self._error_text = error
        
        self._SetDone()
        
    
    def _SetDone( self ):
        
        self._is_done = True
        
    
    def _Sleep( self, seconds ):
        
        self._wake_time = HydrusData.GetNow() + seconds
        
    
    def _WaitOnOngoingBandwidth( self ):
        
        while not self._OngoingBandwidthOK() and not self._IsCancelled():
            
            time.sleep( 0.1 )
            
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            if self._ObeysBandwidth():
                
                result = self.engine.bandwidth_manager.TryToStartRequest( self._network_contexts )
                
                if result:
                    
                    self._bandwidth_tracker.ReportRequestUsed()
                    
                else:
                    
                    waiting_duration = self.engine.bandwidth_manager.GetWaitingEstimate( self._network_contexts )
                    
                    if waiting_duration < 2:
                        
                        self._status_text = u'bandwidth free imminently\u2026'
                        
                    else:
                        
                        pending_timestamp = HydrusData.GetNow() + waiting_duration
                        
                        waiting_str = HydrusData.ConvertTimestampToPrettyPending( pending_timestamp )
                        
                        self._status_text = u'bandwidth free ' + waiting_str + u'\u2026'
                        
                    
                    if waiting_duration > 1200:
                        
                        self._Sleep( 30 )
                        
                    elif waiting_duration > 120:
                        
                        self._Sleep( 10 )
                        
                    elif waiting_duration > 10:
                        
                        self._Sleep( 1 )
                        
                    
                
                return result
                
            else:
                
                self._bandwidth_tracker.ReportRequestUsed()
                
                self.engine.bandwidth_manager.ReportRequestUsed( self._network_contexts )
                
                return True
                
            
        
    
    def Cancel( self ):
        
        with self._lock:
            
            self._status_text = 'cancelled!'
            
            self._SetCancelled()
            
        
    
    def CanLogin( self ):
        
        with self._lock:
            
            if self._for_login:
                
                raise Exception( 'Login jobs should not be asked if they can login!' )
                
            else:
                
                return self.engine.login_manager.CanLogin( self._network_contexts )
                
            
        
    
    def GenerateLoginProcess( self ):
        
        with self._lock:
            
            if self._for_login:
                
                raise Exception( 'Login jobs should not be asked to generate login processes!' )
                
            else:
                
                return self.engine.login_manager.GenerateLoginProcess( self._network_contexts )
                
            
        
    
    def GetContent( self ):
        
        with self._lock:
            
            self._stream_io.seek( 0 )
            
            return self._stream_io.read()
            
        
    
    def GetCreationTime( self ):
        
        with self._lock:
            
            return self._creation_time
            
        
    
    def GetErrorException( self ):
        
        with self._lock:
            
            return self._error_exception
            
        
    
    def GetErrorText( self ):
        
        with self._lock:
            
            return self._error_text
            
        
    
    def GetNetworkContexts( self ):
        
        with self._lock:
            
            return list( self._network_contexts )
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._status_text, self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), self._num_bytes_read, self._num_bytes_to_read )
            
        
    
    def HasError( self ):
        
        with self._lock:
            
            return self._error_exception is not None
            
        
    
    def IsAsleep( self ):
        
        with self._lock:
            
            return not HydrusData.TimeHasPassed( self._wake_time )
            
        
    
    def IsCancelled( self ):
        
        with self._lock:
            
            return self._IsCancelled()
            
        
    
    def IsDone( self ):
        
        with self._lock:
            
            return self._IsDone()
            
        
    
    def NeedsLogin( self ):
        
        with self._lock:
            
            if self._for_login:
                
                return False
                
            else:
                
                result = self.engine.login_manager.NeedsLogin( self._network_contexts )
                
                if result:
                    
                    self._status_text = u'waiting on login\u2026'
                    
                
                return result
                
            
        
    
    def NoEngineYet( self ):
        
        return self.engine is None
        
    
    def ObeysBandwidth( self ):
        
        return self._ObeysBandwidth()
        
    
    def OverrideBandwidth( self ):
        
        with self._lock:
            
            self._bandwidth_manual_override = True
            
            self._wake_time = 0
            
        
    
    def SetStatus( self, text ):
        
        with self._lock:
            
            self._status_text = text
            
        
    
    def Sleep( self, seconds ):
        
        with self._lock:
            
            self._Sleep( seconds )
            
        
    
    def Start( self ):
        
        try:
            
            response = self._SendRequestAndGetResponse()
            
            with self._lock:
                
                if self._body is not None:
                    
                    self._ReportDataUsed( len( self._body ) )
                    
                
            
            if response.ok:
                
                with self._lock:
                    
                    self._status_text = u'downloading\u2026'
                    
                
                if self._temp_path is None:
                    
                    self._ReadResponse( response, self._stream_io )
                    
                else:
                    
                    with open( self._temp_path, 'wb' ) as f:
                        
                        self._ReadResponse( response, f )
                        
                    
                
                with self._lock:
                    
                    self._status_text = 'done!'
                    
                
            else:
                
                with self._lock:
                    
                    self._status_text = str( response.status_code ) + ' - ' + str( response.reason )
                    
                
                self._ReadResponse( response, self._stream_io )
                
                with self._lock:
                    
                    self._stream_io.seek( 0 )
                    
                    data = self._stream_io.read()
                    
                    ( e, error_text ) = ConvertStatusCodeAndDataIntoExceptionInfo( response.status_code, data )
                    
                    self._SetError( e, error_text )
                    
                
            
        except Exception as e:
            
            with self._lock:
                
                self._status_text = 'unexpected error!'
                
                trace = traceback.format_exc()
                
                HydrusData.Print( trace )
                
                self._SetError( e, trace )
                
            
        finally:
            
            with self._lock:
                
                self._SetDone()
                
            
        
    
class NetworkJobDownloader( NetworkJob ):
    
    def __init__( self, downloader_key, method, url, body = None, referral_url = None, temp_path = None, for_login = False ):
        
        self._downloader_key = downloader_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path, for_login = for_login )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER, self._downloader_key ) )
        
        return network_contexts
        
    
    def _GetSessionNetworkContext( self ):
        
        return self._network_contexts[-2] # the domain one
        
    
class NetworkJobDownloaderQuery( NetworkJobDownloader ):
    
    def __init__( self, downloader_page_key, downloader_key, method, url, body = None, referral_url = None, temp_path = None, for_login = False ):
        
        self._downloader_page_key = downloader_page_key
        
        NetworkJobDownloader.__init__( self, downloader_key, method, url, body = body, referral_url = referral_url, temp_path = temp_path, for_login = for_login )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_QUERY, self._downloader_page_key ) )
        
        return network_contexts
        
    
    def _GetSessionNetworkContext( self ):
        
        return self._network_contexts[-3] # the domain one
        
    
class NetworkJobDownloaderQueryTemporary( NetworkJob ):
    
    def __init__( self, downloader_page_key, method, url, body = None, referral_url = None, temp_path = None, for_login = False ):
        
        self._downloader_page_key = downloader_page_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path, for_login = for_login )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_DOWNLOADER_QUERY, self._downloader_page_key ) )
        
        return network_contexts
        
    
    def _GetSessionNetworkContext( self ):
        
        return self._network_contexts[-2] # the domain one
        
    
class NetworkJobSubscription( NetworkJobDownloader ):
    
    def __init__( self, subscription_key, downloader_key, method, url, body = None, referral_url = None, temp_path = None, for_login = False ):
        
        self._subscription_key = subscription_key
        
        NetworkJobDownloader.__init__( self, downloader_key, method, url, body = body, referral_url = referral_url, temp_path = temp_path, for_login = for_login )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, self._subscription_key ) )
        
        return network_contexts
        
    
    def _GetSessionNetworkContext( self ):
        
        return self._network_contexts[-3] # the domain one
        
    
class NetworkJobSubscriptionTemporary( NetworkJob ):
    
    def __init__( self, subscription_key, method, url, body = None, referral_url = None, temp_path = None, for_login = False ):
        
        self._subscription_key = subscription_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path, for_login = for_login )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, self._subscription_key ) )
        
        return network_contexts
        
    
    def _GetSessionNetworkContext( self ):
        
        return self._network_contexts[-2] # the domain one
        
    
class NetworkJobHydrus( NetworkJob ):
    
    def __init__( self, service_key, method, url, body = None, referral_url = None, temp_path = None, for_login = False ):
        
        self._service_key = service_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path, for_login = for_login )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key ) )
        
        return network_contexts
        
    
class NetworkJobThreadWatcher( NetworkJob ):
    
    def __init__( self, thread_key, method, url, body = None, referral_url = None, temp_path = None, for_login = False ):
        
        self._thread_key = thread_key
        
        NetworkJob.__init__( self, method, url, body = body, referral_url = referral_url, temp_path = temp_path, for_login = for_login )
        
    
    def _GenerateNetworkContexts( self ):
        
        network_contexts = NetworkJob._GenerateNetworkContexts( self )
        
        network_contexts.append( NetworkContext( CC.NETWORK_CONTEXT_THREAD_WATCHER_THREAD, self._thread_key ) )
        
        return network_contexts
        
    
    def _GetSessionNetworkContext( self ):
        
        return self._network_contexts[-2] # the domain one
        
    
class NetworkLoginManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._lock = threading.Lock()
        
        self._network_contexts_to_logins = {}
        
        # a login has:
          # a network_context it works for (PRIMARY KEY)
          # a login script
          # rules to check validity in cookies in a current session (fold that into the login script, which may have several stages of this)
          # current user/pass/whatever
          # current script validity
          # current credentials validity
          # recent error? some way of dealing with 'domain is currently down, so try again later'
        
        # so, we fetch all the logins, ask them for the network contexts so we can set up the dict
        
    
    def _GetSerialisableInfo( self ):
        
        return {}
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._network_contexts_to_logins = {}
        
    
    def CanLogin( self, network_contexts ):
        
        # look them up in our structure
        # if they have a login, is it valid?
          # valid means we have tested credentials and it hasn't been invalidated by a parsing error or similar
          # I think this just means saying Login.CanLogin( credentials )
        
        return False
        
    
    def GenerateLoginProcess( self, network_contexts ):
        
        # look up the logins
          # login_process = Login.GenerateLoginProcess
          # say CallToThread( login_process.start, engine, credentials )
          # return login_process
          # the login can update itself if there are problems. it should also inform the user
        
        raise NotImplementedError()
        
    
    def NeedsLogin( self, network_contexts ):
        
        # look up the network contexts in our structure
            # if they have a login, see if they match the 'is logged in' predicates
        # otherwise:
        
        return False
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_LOGIN_MANAGER ] = NetworkLoginManager

class NetworkSessionManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self.engine = None
        
        self._dirty = False
        
        self._lock = threading.Lock()
        
        self._network_contexts_to_sessions = {}
        
    
    def _GenerateSession( self, network_context ):
        
        session = requests.Session()
        
        session.headers.update( { 'User-Agent' : 'hydrus/' + str( HC.NETWORK_VERSION ) } )
        
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
                
            
        
    
    def GetSession( self, network_context ):
        
        with self._lock:
            
            if network_context not in self._network_contexts_to_sessions:
                
                self._network_contexts_to_sessions[ network_context ] = self._GenerateSession( network_context )
                
            
            self._SetDirty()
            
            return self._network_contexts_to_sessions[ network_context ]
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NETWORK_SESSION_MANAGER ] = NetworkSessionManager
