import collections
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
        
    
def ConvertURLIntoDomains( url ):
    
    domains = []
    
    parser_result = urlparse.urlparse( url )
    
    domain = parser_result.netloc
    
    while domain.count( '.' ) > 0:
        
        domains.append( domain )
        
        domain = '.'.join( domain.split( '.' )[1:] ) # i.e. strip off the leftmost subdomain maps.google.com -> google.com
        
    
    return domains
    
def RequestsGet( url, params = None, stream = False, headers = None ):
    
    if headers is None:
        
        headers = {}
        
    
    headers[ 'User-Agent' ] = 'hydrus/' + str( HC.NETWORK_VERSION )
    
    response = requests.get( url, params = params, stream = stream, headers = headers )
    
    RequestsCheckResponse( response )
    
    return response
    
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
        
        threading.Thread( target = self.DAEMONMaintainConnections, name = 'Maintain Connections' ).start()
        
    
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
        
    
class BandwidthManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_BANDWIDTH_MANAGER
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._global_bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        self._global_bandwidth_rules = HydrusNetworking.BandwidthRules()
        
        self._domains_to_bandwidth_trackers = collections.defaultdict( HydrusNetworking.BandwidthTracker )
        self._domains_to_bandwidth_rules = {}
        
    
    def _GetApplicableTrackersAndRules( self, url = None ):
        
        result = []
        
        if url is not None:
            
            domains = ConvertURLIntoDomains( url )
            
            for domain in domains:
                
                if domain in self._domains_to_bandwidth_rules:
                    
                    bandwidth_tracker = self._domains_to_bandwidth_trackers[ domain ]
                    
                    bandwidth_rules = self._domains_to_bandwidth_rules[ domain ]
                    
                    result.append( ( bandwidth_tracker, bandwidth_rules ) )
                    
                
            
        
        result.append( ( self._global_bandwidth_tracker, self._global_bandwidth_rules ) )
        
        return result
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_global_tracker = self._global_bandwidth_tracker.GetSerialisableTuple()
        serialisable_global_rules = self._global_bandwidth_rules.GetSerialisableTuple()
        
        all_serialisable_trackers = [ ( domain, tracker.GetSerialisableTuple() ) for ( domain, tracker ) in self._domains_to_bandwidth_trackers ]
        all_serialisable_rules = [ ( domain, rules.GetSerialisableTuple() ) for ( domain, rules ) in self._domains_to_bandwidth_rules ]
        
        return ( serialisable_global_tracker, serialisable_global_rules, all_serialisable_trackers, all_serialisable_rules )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_global_tracker, serialisable_global_rules, all_serialisable_trackers, all_serialisable_rules ) = serialisable_info
        
        self._global_bandwidth_tracker = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_global_tracker )
        self._global_bandwidth_rules = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_global_rules )
        
        for ( domain, serialisable_tracker ) in all_serialisable_trackers:
            
            self._domains_to_bandwidth_trackers[ domain ] = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tracker )
            
        
        for ( domain, serialisable_rules ) in all_serialisable_rules:
            
            self._domains_to_bandwidth_rules[ domain ] = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_rules )
            
        
    
    def CanStartGlobally( self ):
        
        return self.CanStartURL( None )
        
    
    def CanStartURL( self, url ):
        
        with self._lock:
            
            for ( bandwidth_tracker, bandwidth_rules ) in self._GetApplicableTrackersAndRules( url ):
                
                if not bandwidth_rules.CanStart( bandwidth_tracker ):
                    
                    return False
                    
                
            
            return True
            
        
        
    
    def GetEstimateInfo( self, domain = None ):
        
        with self._lock:
            
            # something that returns ( 'about a minute until you can request again', 60 )
            
            pass
            
        
    
    def GetDomainsAndTrackers( self ):
        
        with self._lock:
            
            result = list( self._domains_to_bandwidth_trackers.items() )
            
            result.sort()
            
            result.insert( 0, ( 'global', self._global_bandwidth_tracker ) )
            
            return result
            
        
    
    def ReportDataUsedGlobally( self, num_bytes ):
        
        self.ReportDataUsedURL( None, num_bytes )
        
    
    def ReportDataUsedURL( self, url, num_bytes ):
        
        with self._lock:
            
            for ( bandwidth_tracker, bandwidth_rules ) in self._GetApplicableTrackersAndRules( url ):
                
                bandwidth_tracker.ReportDataUsed( num_bytes )
                
            
        
    
    def ReportRequestUsedGlobally( self ):
        
        self.ReportRequestUsedURL( None )
        
    
    def ReportRequestUsedURL( self, url ):
        
        with self._lock:
            
            for ( bandwidth_tracker, bandwidth_rules ) in self._GetApplicableTrackersAndRules( url ):
                
                bandwidth_tracker.ReportRequestUsed()
                
            
        
    
    def SetRules( self, domain, bandwidth_rules ):
        
        with self._lock:
            
            if domain is None:
                
                self._global_bandwidth_rules = bandwidth_rules
                
            else:
                
                self._domains_to_bandwidth_rules[ domain ] = bandwidth_rules
                
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_BANDWIDTH_MANAGER ] = BandwidthManager

class NetworkEngine( object ):
    
    MAX_JOBS = 10 # turn this into an option
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._lock = threading.Lock()
        
        self._new_work_to_do = threading.Event()
        
        self._jobs_bandwidth_throttled = []
        self._jobs_login_throttled = []
        self._current_login_process = None
        self._jobs_ready_to_start = []
        self._jobs_downloading = []
        
        self._local_shutdown = False
        
        self._controller.CallToThread( self.MainLoop )
        
    
    def AddJob( self, job ):
        
        with self._lock:
            
            self._jobs_bandwidth_throttled.append( job )
            
        
        self._new_work_to_do.set()
        
    
    def MainLoop( self ):
        
        while not ( self._local_shutdown or self._controller.ModelIsShutdown() ):
            
            def ProcessBandwidthJob( job ):
                
                if job.IsDone():
                    
                    return False
                    
                elif job.IsAsleep():
                    
                    return True
                    
                elif not job.BandwidthOK():
                    
                    job.SetStatus( u'waiting on bandwidth\u2026' )
                    
                    job.Sleep( 5 )
                    
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
                            
                            self._controller.CallToThread( login_process.Start )
                            
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
                    
                    self._controller.CallToThread( job.Start )
                    
                    self._jobs_downloading.append( job )
                    
                    return False
                    
                else:
                    
                    return True
                    
                
            
            def ProcessDownloadingJob( job ):
                
                if job.IsDone():
                    
                    return False
                    
                else:
                    
                    return True
                    
                
            
            with self._lock:
                
                self._jobs_bandwidth_throttled = filter( ProcessBandwidthJob, self._jobs_bandwidth_throttled )
                
                self._jobs_login_throttled = filter( ProcessLoginJob, self._jobs_login_throttled )
                
                ProcessCurrentLoginJob()
                
                self._jobs_ready_to_start = filter( ProcessReadyJob, self._jobs_ready_to_start )
                
                self._jobs_downloading = filter( ProcessDownloadingJob, self._jobs_downloading )
                
            
            self._new_work_to_do.wait( 1 )
            
            self._new_work_to_do.clear()
            
        
    
    def Shutdown( self ):
        
        self._local_shutdown = True
        
    
class NetworkJob( object ):
    
    def __init__( self, method, url, body = None, referral_url = None, temp_path = None ):
        
        self._lock = threading.Lock()
        
        self._method = method
        self._url = url
        self._body = body
        self._referral_url = referral_url
        self._temp_path = temp_path
        
        self._bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self._wake_time = 0
        
        self._stream_io = cStringIO.StringIO()
        
        self._has_error = False
        self._error_exception = None
        self._error_text = None
        
        self._is_done = False
        self._is_cancelled = False
        self._bandwidth_override = False
        
        self._status_code = None
        
        self._status_text = u'initialising\u2026'
        self._num_bytes_read = 0
        self._num_bytes_to_read = None
        
    
    def _BandwidthOK( self ):
        
        raise NotImplementedError()
        
    
    def _CanLogin( self ):
        
        raise NotImplementedError()
        
    
    def _GenerateLoginProcess( self ):
        
        raise NotImplementedError()
        
    
    def _GetSession( self ):
        
        raise NotImplementedError()
        
    
    def _ImmediateBandwidthOK( self ):
        
        raise NotImplementedError()
        
    
    def _IsCancelled( self ):
        
        if self._is_cancelled:
            
            return True
            
        
        if HG.client_controller.ModelIsShutdown():
            
            return True
            
        
        return False
        
    
    def _NeedsLogin( self ):
        
        raise NotImplementedError()
        
    
    def _ReadResponse( self, response, stream_dest ):
        
        if 'content-length' in response.headers:
            
            self._num_bytes_to_read = int( response.headers[ 'content-length' ] )
            
        
        try:
            
            for chunk in response.iter_content( chunk_size = 8192 ):
                
                if self._IsCancelled():
                    
                    return
                    
                
                stream_dest.write( chunk )
                
                chunk_length = len( chunk )
                
                self._num_bytes_read += chunk_length
                
                self._ReportDataUsed( chunk_length )
                self._WaitOnImmediateBandwidth()
                
            
        finally:
            
            num_bytes_used = self._num_bytes_read
            
            if self._body is not None:
                
                num_bytes_used += len( self._body )
                
            
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        self._bandwidth_tracker.ReportDataUsed( num_bytes )
        
    
    def _ReportRequestUsed( self ):
        
        self._bandwidth_tracker.ReportRequestUsed()
        
    
    def _SetCancelled( self ):
        
        self._is_cancelled = True
        
        self._SetDone()
        
    
    def _SetError( self, e, error ):
        
        self._has_error = True
        self._error_exception = e
        self._error_text = error
        
        self._SetDone()
        
    
    def _SetDone( self ):
        
        self._is_done = True
        
    
    def _WaitOnImmediateBandwidth( self ):
        
        while not self._ImmediateBandwidthOK() and not self._IsCancelled():
            
            time.sleep( 0.5 )
            
        
    
    def BandwidthOK( self ):
        
        with self._lock:
            
            if self._bandwidth_override:
                
                return True
                
            else:
                
                return self._BandwidthOK()
                
            
        
    
    def Cancel( self ):
        
        with self._lock:
            
            self._status_text = 'cancelled!'
            
            self._SetCancelled()
            
        
    
    def GenerateLoginProcess( self ):
        
        with self._lock:
            
            return self._GenerateLoginProcess()
            
        
    
    def GetContent( self ):
        
        with self._lock:
            
            self._stream_io.seek( 0 )
            
            return self._stream_io.read()
            
        
    
    def GetErrorException( self ):
        
        with self._lock:
            
            return self._error_exception
            
        
    
    def GetErrorText( self ):
        
        with self._lock:
            
            return self._error_text
            
        
    
    def GetStatus( self ):
        
        with self._lock:
            
            return ( self._status_text, self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), self._num_bytes_read, self._num_bytes_to_read )
            
        
    
    def HasError( self ):
        
        with self._lock:
            
            return self._has_error
            
        
    
    def IsAsleep( self ):
        
        with self._lock:
            
            return HydrusData.TimeHasPassed( self._wake_time )
            
        
    
    def IsCancelled( self ):
        
        with self._lock:
            
            return self._IsCancelled()
            
        
    
    def IsDone( self ):
        
        with self._lock:
            
            return self._is_done
            
        
    
    def NeedsLogin( self ):
        
        with self._lock:
            
            self._NeedsLogin()
            
        
    
    def OverrideBandwidth( self ):
        
        with self._lock:
            
            self._bandwidth_override = True
            
        
    
    def SetStatus( self, text ):
        
        with self._lock:
            
            self._status_text = text
            
        
    
    def Sleep( self, seconds ):
        
        with self._lock:
            
            self._wake_time = HydrusData.GetNow() + seconds
            
        
    
    def Start( self ):
        
        try:
            
            with self._lock:
                
                self._ReportRequestUsed()
                
                session = self._GetSession()
                
                method = self._method
                url = self._url
                data = self._body
                
                headers = {}
                
                if self._referral_url is not None:
                    
                    headers = { 'referer' : self._referral_url }
                    
                
                self._status_text = u'sending request\u2026'
                
            
            response = session.request( method, url, data = data, headers = headers, stream = True )
            
            with self._lock:
                
                if self._body is not None:
                    
                    self._ReportDataUsed( len( self._body ) )
                    
                
                self._status_code = response.status_code
                
            
            if response.ok:
                
                with self._lock:
                    
                    self._status_text = u'downloading\u2026'
                    
                
                if self._temp_path is None:
                    
                    self._ReadResponse( response, self._stream_io )
                    
                else:
                    
                    with open( self._temp_path, 'rb' ) as f:
                        
                        self._ReadResponse( response, f )
                        
                    
                
                with self._lock:
                    
                    self._status_text = 'done!'
                    
                
            else:
                
                with self._lock:
                    
                    self._status_text = '404 - Not Found' # ConvertStatusCodeIntoEnglish( response.status_code )
                    
                
                self._ReadResponse( response, self._stream_io )
                
                with self._lock:
                    
                    self._stream_io.seek( 0 )
                    
                    data = self._stream_io.read()
                    
                    ( e, error_text ) = ( HydrusExceptions.NotFoundException( 'wew' ), 'Bunch of html that was returned or whatever.' ) # ConvertStatusCodeAndDataIntoExceptionInfo( response.status_code, data )
                    
                    self._SetError( e, error_text )
                    
                
            
        except Exception as e:
            
            with self._lock:
                
                self._status_text = 'unexpected error!'
                
                trace = traceback.format_exc()
                
                self._SetError( e, trace )
                
            
        finally:
            
            with self._lock:
                
                self._SetDone()
                
            
        
    
class NetworkJobWeb( NetworkJob ):
    
    def _BandwidthOK( self ):
        
        bandwidth_manager = HG.client_controller.GetBandwidthManager()
        
        return bandwidth_manager.CanStartURL( self._url )
        
    
    def _CanLogin( self ):
        
        # ask login engine if it is possible to login at this time (i.e. if our login details seem to be valid--a bad login will invalidate the form/details until the user can re-verify, hence stopping all bad requests from spamming a changed login form)
        
        pass
        
    
    def _GenerateLoginProcess( self ):
        
        pass
        
        # talk to login engine, figure out an object to handle this that will follow the script and report status back to the network engine
        
    
    def _GetSession( self ):
        
        pass # fetch the regular session from the sessionmanager
        
    
    def _ImmediateBandwidthOK( self ):
        
        bandwidth_manager = HG.client_controller.GetBandwidthManager()
        
        return bandwidth_manager.CanContinueURL( self._url )
        
    
    def _NeedsLogin( self ):
        
        # consult login engine, ask if I need login (it will consult its records and the current session)
        
        pass
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        NetworkJob._ReportDataUsed( self, num_bytes )
        
        bandwidth_manager = HG.client_controller.GetBandwidthManager()
        
        bandwidth_manager.ReportDataUsedURL( self._url, num_bytes )
        
    
    def _ReportRequestUsed( self ):
        
        NetworkJob._ReportRequestUsed( self )
        
        bandwidth_manager = HG.client_controller.GetBandwidthManager()
        
        bandwidth_manager.ReportRequestUsedURL( self._url )
        
    
class NetworkJobWebLogin( NetworkJobWeb ):
    
    def _BandwidthOK( self ):
        
        return True
        
    
    def _ImmediateBandwidthOK( self ):
        
        return True
        
    
    def _NeedsLogin( self ):
        
        return False
        
    
class NetworkJobHydrus( NetworkJob ):
    
    def __init__( self, service_key, method, url, body = None, temp_path = None ):
        
        NetworkJob.__init__( self, method, url, body, temp_path = temp_path )
        
        self._service_key = service_key
        
    
    def _BandwidthOK( self ):
        
        bandwidth_manager = HG.client_controller.GetBandwidthManager()
        
        if not bandwidth_manager.CanStartGlobally():
            
            return False
            
        else:
            
            service = HG.client_controller.GetServicesManager().GetService( self._service_key )
            
            return service.BandwidthOK()
            
        
    
    def _CanLogin( self ):
        
        # ask service if account is valid
        
        pass
        
    
    def _GenerateLoginProcess( self ):
        
        pass
        
        # talk to service, figure out a login-process compatible object to handle the session gen
        
    
    def _GetSession( self ):
        
        pass # fetch the hydrus (ssl verify=False) session, which should have the keys as cookies, right?
        # this will ultimately be a job for the login engine step, earlier
        
    
    def _ImmediateBandwidthOK( self ):
        
        bandwidth_manager = HG.client_controller.GetBandwidthManager()
        
        service = HG.client_controller.GetServicesManager().GetService( self._service_key )
        
        return bandwidth_manager.CanContinueGlobally() and service.CanContinue()
        
    
    def _NeedsLogin( self ):
        
        # consult service, ask if I need a session key
        
        pass
        
    
    def _ReportDataUsed( self, num_bytes ):
        
        NetworkJob._ReportDataUsed( self, num_bytes )
        
        bandwidth_manager = HG.client_controller.GetBandwidthManager()
        
        bandwidth_manager.ReportDataUsedGlobally( num_bytes )
        
        service = HG.client_controller.GetServicesManager().GetService( self._service_key )
        
        return service.ReportDataUsed( num_bytes )
        
    
    def _ReportRequestUsed( self ):
        
        NetworkJob._ReportRequestUsed( self )
        
        bandwidth_manager = HG.client_controller.GetBandwidthManager()
        
        bandwidth_manager.ReportRequestUsedGlobally()
        
        service = HG.client_controller.GetServicesManager().GetService( self._service_key )
        
        return service.ReportRequestUsed()
        
    
class NetworkJobHydrusLogin( NetworkJobHydrus ):
    
    def _BandwidthOK( self ):
        
        return True
        
    
    def _ImmediateBandwidthOK( self ):
        
        return True
        
    
    def _NeedsLogin( self ):
        
        return False
        
    
