import HydrusConstants as HC
import HydrusExceptions
import HydrusNetwork
import HydrusPaths
import HydrusSerialisable
import errno
import httplib
import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import socket
import socks
import ssl
import threading
import time
import urllib
import urlparse
import yaml
import HydrusData
import itertools
import HydrusGlobals

requests.packages.urllib3.disable_warnings( InsecureRequestWarning )

def AddHydrusCredentialsToHeaders( credentials, request_headers ):
    
    if credentials.HasAccessKey():
        
        access_key = credentials.GetAccessKey()
        
        request_headers[ 'Hydrus-Key' ] = access_key.encode( 'hex' )
        
    else:
        
        raise Exception( 'No access key!' )
        
    
def AddHydrusSessionKeyToHeaders( service_key, request_headers ):
    
    session_manager = HydrusGlobals.client_controller.GetClientSessionManager()
    
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
        
    
def RequestsGet( url, params = None, stream = False, headers = None ):
    
    if headers is None:
        
        headers = {}
        
    
    headers[ 'User-Agent' ] = 'hydrus/' + str( HC.NETWORK_VERSION )
    
    response = requests.get( url, params = params, stream = stream, headers = headers )
    
    RequestsCheckResponse( response )
    
    return response
    
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
            
        else:
            
            eclass = HydrusExceptions.NetworkException
            
        
        raise eclass( error_text )
        
    
def ParseURL( url ):
    
    try:
        
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
            
            if HydrusGlobals.model_shutdown:
                
                break
                
            
            last_checked = 0
            
            if HydrusData.GetNow() - last_checked > 30:
                
                with self._lock:
                    
                    connections_copy = dict( self._connections )
                    
                    for ( ( location, hydrus_network ), connection ) in connections_copy.items():
                        
                        with connection.lock:
                            
                            if connection.IsStale():
                                
                                del self._connections[ ( location, hydrus_network ) ]
                            
                        
                    
                
                last_checked = HydrusData.GetNow()
                
            
            time.sleep( 1 )
            
        
    
class HTTPConnection( object ):
    
    def __init__( self, location, hydrus_network ):
        
        ( self._scheme, self._host, self._port ) = location
        
        self._hydrus_network = hydrus_network
        
        self._timeout = 30
        
        self.lock = threading.Lock()
        
        self._last_request_time = HydrusData.GetNow()
        
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
                    
                    if url.startswith( '/' ): slash_sep = ''
                    else: slash_sep = '/'
                    
                    url = self._scheme + '://' + self._host + slash_sep + url
                    
                
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
                    
                    raise Exception( parsed_response )
                    
                
            else: raise Exception( parsed_response )
            
        
    
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
            
            if HydrusGlobals.model_shutdown:
                
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
        
        if self._scheme == 'http': self._connection = httplib.HTTPConnection( self._host, self._port, timeout = self._timeout )
        elif self._scheme == 'https':
            
            new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            if self._hydrus_network or not new_options.GetBoolean( 'verify_regular_https' ):
                
                # this negotiates decent encryption but won't check hostname or the certificate
                
                context = ssl.SSLContext( ssl.PROTOCOL_SSLv23 )
                context.options |= ssl.OP_NO_SSLv2
                context.options |= ssl.OP_NO_SSLv3
                
                self._connection = httplib.HTTPSConnection( self._host, self._port, timeout = self._timeout, context = context )
                
            else:
                
                self._connection = httplib.HTTPSConnection( self._host, self._port, timeout = self._timeout )
                
            
        
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
                
                if HydrusGlobals.model_shutdown:
                    
                    raise HydrusExceptions.ShutdownException( 'Application is shutting down!' )
                    
                
                size_of_response += len( block )
                
                if content_length is not None and size_of_response > content_length:
                    
                    raise Exception( 'Response was longer than suggested!' )
                    
                
                f.write( block )
                
                for hook in report_hooks:
                    
                    if content_length is not None:
                        
                        hook( content_length, size_of_response )
                        
                    
                
            
        
        return size_of_response
        
    
    def IsStale( self ):
        
        time_since_last_request = HydrusData.GetNow() - self._last_request_time
        
        return time_since_last_request > self._timeout
        
    
    def Request( self, method, path_and_query, request_headers, body, report_hooks = None, temp_path = None ):
        
        ( response, parsed_response, size_of_response ) = self._SendRequestGetResponse( method, path_and_query, request_headers, body, report_hooks = report_hooks, temp_path = temp_path )
        
        return self._DealWithResponse( method, response, parsed_response, size_of_response )
        
    
    
