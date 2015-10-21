import HydrusConstants as HC
import HydrusExceptions
import HydrusSerialisable
import httplib
import os
import socks
import threading
import time
import urllib
import urlparse
import yaml
import HydrusData
import itertools
import HydrusGlobals

def AddHydrusCredentialsToHeaders( credentials, request_headers ):
    
    if credentials.HasAccessKey():
        
        access_key = credentials.GetAccessKey()
        
        if access_key != '': request_headers[ 'Hydrus-Key' ] = access_key.encode( 'hex' )
        
    else: raise Exception( 'No access key!' )
    
def AddHydrusSessionKeyToHeaders( service_key, request_headers ):
    
    session_manager = HydrusGlobals.client_controller.GetManager( 'hydrus_sessions' )
    
    session_key = session_manager.GetSessionKey( service_key )
    
    request_headers[ 'Cookie' ] = 'session_key=' + session_key.encode( 'hex' )
    
def AddCookiesToHeaders( cookies, request_headers ):
    
    request_headers[ 'Cookie' ] = '; '.join( [ k + '=' + v for ( k, v ) in cookies.items() ] )
    
def CheckHydrusVersion( service_key, service_type, response_headers ):
    
    service_string = HC.service_string_lookup[ service_type ]
    
    if 'server' not in response_headers or service_string not in response_headers[ 'server' ]:
        
        HydrusGlobals.client_controller.Write( 'service_updates', { service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, HydrusData.GetUnknownAccount() ) ] })
        
        raise HydrusExceptions.WrongServiceTypeException( 'Target was not a ' + service_string + '!' )
        
    
    server_header = response_headers[ 'server' ]
    
    ( service_string_gumpf, network_version ) = server_header.split( '/' )
    
    network_version = int( network_version )
    
    if network_version != HC.NETWORK_VERSION:
        
        if network_version > HC.NETWORK_VERSION: message = 'Your client is out of date; please download the latest release.'
        else: message = 'The server is out of date; please ask its admin to update to the latest release.'
        
        raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! The server\'s network version was ' + HydrusData.ToString( network_version ) + ', whereas your client\'s is ' + HydrusData.ToString( HC.NETWORK_VERSION ) + '! ' + message )
        
    
def ConvertHydrusGETArgsToQuery( request_args ):
    
    if 'subject_identifier' in request_args:
        
        subject_identifier = request_args[ 'subject_identifier' ]
        
        del request_args[ 'subject_identifier' ]
        
        if subject_identifier.HasAccountKey():
            
            account_key = subject_identifier.GetData()
            
            request_args[ 'subject_account_key' ] = account_key.encode( 'hex' )
            
        elif subject_identifier.HasContent():
            
            content = subject_identifier.GetData()
            
            content_type = content.GetContentType()
            content_data = content.GetContent()
            
            if content_type == HC.CONTENT_TYPE_FILES:
                
                hash = content_data[0]
                
                request_args[ 'subject_hash' ] = hash.encode( 'hex' )
                
            elif content_type == HC.CONTENT_TYPE_MAPPING:
                
                ( tag, hash ) = content_data
                
                request_args[ 'subject_hash' ] = hash.encode( 'hex' )
                request_args[ 'subject_tag' ] = tag.encode( 'hex' )
                
            
        
    
    if 'title' in request_args:
        
        request_args[ 'title' ] = request_args[ 'title' ].encode( 'hex' )
        
    
    query = '&'.join( [ key + '=' + HydrusData.ToString( value ) for ( key, value ) in request_args.items() ] )
    
    return query
    
def ParseURL( url ):
    
    try:
        
        starts_http = url.startswith( 'http://' )
        starts_https = url.startswith( 'https://' )
        
        if not starts_http and not starts_https: url = 'http://' + url
        
        parse_result = urlparse.urlparse( url )
        
        scheme = parse_result.scheme
        hostname = parse_result.hostname
        port = parse_result.port
        
        if hostname is None: location = None
        else: location = ( scheme, hostname, port )
        
        path = parse_result.path
        
        # this happens when parsing 'index.html' rather than 'hostname/index.html' or '/index.html'
        if not path.startswith( '/' ): path = '/' + path
        
        query = parse_result.query
        
    except: raise Exception( 'Could not parse that URL' )
    
    return ( location, path, query )
    
def SetProxy( proxytype, host, port, username = None, password = None ):
    
    if proxytype == 'http': proxytype = socks.PROXY_TYPE_HTTP
    elif proxytype == 'socks4': proxytype = socks.PROXY_TYPE_SOCKS4
    elif proxytype == 'socks5': proxytype = socks.PROXY_TYPE_SOCKS5
    
    socks.setdefaultproxy( proxytype = proxytype, addr = host, port = port, username = username, password = password )
    
    socks.wrapmodule( httplib )
    
class HTTPConnectionManager( object ):
    
    def __init__( self ):
        
        self._connections = {}
        
        self._lock = threading.Lock()
        
        threading.Thread( target = self.DAEMONMaintainConnections, name = 'Maintain Connections' ).start()
        
    
    def _DoRequest( self, method, location, path, query, request_headers, body, follow_redirects = True, report_hooks = None, temp_path = None, num_redirects_permitted = 4 ):
        
        if report_hooks is None: report_hooks = []
        
        connection = self._GetConnection( location )
        
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
                
                if num_redirects_permitted == 0: raise Exception( 'Too many redirects!' )
                
                ( new_method, new_url ) = redirect_info
                
                ( new_location, new_path, new_query ) = ParseURL( new_url )
                
                if new_location is None: new_location = location
                
                return self._DoRequest( new_method, new_location, new_path, new_query, request_headers, body, follow_redirects = follow_redirects, report_hooks = report_hooks, temp_path = temp_path, num_redirects_permitted = num_redirects_permitted - 1 )
                
            
        except:
            
            time.sleep( 2 )
            
            raise
            
        
    
    def _GetConnection( self, location ):
        
        with self._lock:
            
            if location not in self._connections:
                
                connection = HTTPConnection( location )
                
                self._connections[ location ] = connection
                
            
            return self._connections[ location ]
            
        
    
    def Request( self, method, url, request_headers = None, body = '', return_everything = False, return_cookies = False, report_hooks = None, temp_path = None ):
        
        if request_headers is None: request_headers = {}
        
        ( location, path, query ) = ParseURL( url )
        
        follow_redirects = not return_cookies
        
        ( response, size_of_response, response_headers, cookies ) = self._DoRequest( method, location, path, query, request_headers, body, follow_redirects = follow_redirects, report_hooks = report_hooks, temp_path = temp_path )
        
        if return_everything:
            
            return ( response, size_of_response, response_headers, cookies )
            
        elif return_cookies:
            
            return ( response, cookies )
            
        else:
            
            return response
            
        
    
    def DAEMONMaintainConnections( self ):
        
        while True:
            
            if HydrusGlobals.model_shutdown: break
            
            last_checked = 0
            
            if HydrusData.GetNow() - last_checked > 30:
                
                with self._lock:
                    
                    connections_copy = dict( self._connections )
                    
                    for ( location, connection ) in connections_copy.items():
                        
                        with connection.lock:
                            
                            if connection.IsStale():
                                
                                del self._connections[ location ]
                            
                        
                    
                
                last_checked = HydrusData.GetNow()
                
            
            time.sleep( 1 )
            
        
    
class HTTPConnection( object ):
    
    def __init__( self, location ):
        
        ( self._scheme, self._host, self._port ) = location
        
        self._timeout = 30
        
        self.lock = threading.Lock()
        
        self._last_request_time = HydrusData.GetNow()
        
        self._RefreshConnection()
        
    
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
        
        for block in HydrusData.ReadFileLikeAsBlocks( response ):
            
            if HydrusGlobals.model_shutdown: raise Exception( 'Application is shutting down!' )
            
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
                
            elif content_type == 'application/x-yaml':
                
                try: parsed_response = yaml.safe_load( data )
                except yaml.error.YAMLError as e:
                    
                    raise HydrusExceptions.NetworkVersionException( 'Failed to parse a response object!' + os.linesep + HydrusData.ToString( e ) )
                    
                
            elif content_type == 'application/json':
                
                if hydrus_service:
                    
                    parsed_response = HydrusSerialisable.CreateFromNetworkString( data )
                    
                else:
                    
                    parsed_response = data
                    
                
            elif content_type == 'text/html':
                
                try: parsed_response = data.decode( 'utf-8' )
                except: parsed_response = data
                
            else: parsed_response = data
            
        
        return ( parsed_response, size_of_response )
        
    
    def _RefreshConnection( self ):
        
        if self._scheme == 'http': self._connection = httplib.HTTPConnection( self._host, self._port, timeout = self._timeout )
        elif self._scheme == 'https': self._connection = httplib.HTTPSConnection( self._host, self._port, timeout = self._timeout )
        
        try:
            
            self._connection.connect()
            
        except Exception as e:
            
            text = 'Could not connect to ' + HydrusData.ToString( self._host ) + ':'
            text += os.linesep * 2
            text += HydrusData.ToString( e )
            
            raise Exception( text )
            
        
    
    def _WriteResponseToPath( self, response, temp_path, report_hooks ):
        
        content_length = response.getheader( 'Content-Length' )
        
        if content_length is not None: content_length = int( content_length )
        
        size_of_response = 0
        
        with open( temp_path, 'wb' ) as f:
            
            for block in HydrusData.ReadFileLikeAsBlocks( response ):
                
                if HydrusGlobals.model_shutdown: raise Exception( 'Application is shutting down!' )
                
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
        
        if report_hooks is None: report_hooks = []
        
        if method == HC.GET: method_string = 'GET'
        elif method == HC.POST: method_string = 'POST'
        
        if 'User-Agent' not in request_headers: request_headers[ 'User-Agent' ] = 'hydrus/' + HydrusData.ToString( HC.NETWORK_VERSION )
        
        # it is important to only send str, not unicode, to httplib
        # it uses += to extend the message body, which propagates the unicode (and thus fails) when
        # you try to push non-ascii bytes as the body (e.g. during a file upload!)
        
        method_string = str( method_string )
        path_and_query = str( path_and_query )
        
        request_headers = { str( k ) : str( v ) for ( k, v ) in request_headers.items() }
        
        try:
            
            self._connection.request( method_string, path_and_query, headers = request_headers, body = body )
            
            response = self._connection.getresponse()
            
        except ( httplib.CannotSendRequest, httplib.BadStatusLine ):
            
            # for some reason, we can't send a request on the current connection, so let's make a new one and try again!
            
            self._RefreshConnection()
            
            self._connection.request( method_string, path_and_query, headers = request_headers, body = body )
            
            response = self._connection.getresponse()
            
        
        if response.status == 200 and temp_path is not None:
            
            size_of_response = self._WriteResponseToPath( response, temp_path, report_hooks )
            
            parsed_response = 'response written to temporary file'
            
        else:
            
            ( parsed_response, size_of_response ) = self._ParseResponse( response, report_hooks )
            
        
        response_headers = { k : v for ( k, v ) in response.getheaders() if k != 'set-cookie' }
        
        cookies = self._ParseCookies( response.getheader( 'set-cookie' ) )
        
        self._last_request_time = HydrusData.GetNow()
        
        if response.status == 200: return ( parsed_response, None, size_of_response, response_headers, cookies )
        elif response.status in ( 301, 302, 303, 307 ):
            
            location = response.getheader( 'Location' )
            
            if location is None: raise Exception( 'Received an invalid redirection response.' )
            else:
                
                url = location
                
                if ' ' in url:
                    
                    # some booru is giving daft redirect responses
                    print( url )
                    url = urllib.quote( url.encode( 'utf-8' ), safe = '/?=&' )
                    print( url )
                    
                
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
            
        
    
    