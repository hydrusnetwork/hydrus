import HydrusConstants as HC
import HydrusExceptions
import httplib
import threading
import time
import urlparse
import yaml

def AddHydrusCredentialsToHeaders( credentials, request_headers ):
    
    if credentials.HasAccessKey():
        
        access_key = credentials.GetAccessKey()
        
        if access_key != '': request_headers[ 'Hydrus-Key' ] = access_key.encode( 'hex' )
        
    else: raise Exception( 'No access key!' )
    
def AddHydrusSessionKeyToHeaders( service_identifier, request_headers ):

    session_manager = HC.app.GetManager( 'hydrus_sessions' )
    
    session_key = session_manager.GetSessionKey( service_identifier )
    
    request_headers[ 'Cookie' ] = 'session_key=' + session_key.encode( 'hex' )
    
def AddCookiesToHeaders( cookies, request_headers ):
    
    request_headers[ 'Cookie' ] = '; '.join( [ k + '=' + v for ( k, v ) in cookies.items() ] )
    
def CheckHydrusVersion( service_identifier, response_headers ):
    
    service_type = service_identifier.GetType()
    
    service_string = HC.service_string_lookup[ service_type ]
    
    if 'server' not in response_headers or service_string not in response_headers[ 'server' ]:
        
        HC.app.Write( 'service_updates', { service_identifier : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, HC.GetUnknownAccount() ) ] })
        
        raise HydrusExceptions.WrongServiceTypeException( 'Target was not a ' + service_string + '!' )
        
    
    server_header = response_headers[ 'server' ]
    
    ( service_string_gumpf, network_version ) = server_header.split( '/' )
    
    network_version = int( network_version )
    
    if network_version != HC.NETWORK_VERSION:
        
        if network_version > HC.NETWORK_VERSION: message = 'Your client is out of date; please download the latest release.'
        else: message = 'The server is out of date; please ask its admin to update to the latest release.'
        
        raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! The server\'s network version was ' + u( network_version ) + ', whereas your client\'s is ' + u( HC.NETWORK_VERSION ) + '! ' + message )
        
    
def ConvertHydrusGETArgsToQuery( request_args ):
    
    if 'subject_identifier' in request_args:
        
        subject_identifier = request_args[ 'subject_identifier' ]
        
        del request_args[ 'subject_identifier' ]
        
        data = subject_identifier.GetData()
        
        if subject_identifier.HasAccessKey(): request_args[ 'subject_access_key' ] = data.encode( 'hex' )
        elif subject_identifier.HasAccountId(): request_args[ 'subject_account_id' ] = data
        elif subject_identifier.HasHash(): request_args[ 'subject_hash' ] = data.encode( 'hex' )
        if subject_identifier.HasMapping():
            
            ( subject_hash, subject_tag ) = data
            
            request_args[ 'subject_hash' ] = subject_hash.encode( 'hex' )
            request_args[ 'subject_tag' ] = subject_tag.encode( 'hex' )
            
        
    
    if 'title' in request_args:
        
        request_args[ 'title' ] = request_args[ 'title' ].encode( 'hex' )
        
    
    query = '&'.join( [ key + '=' + HC.u( value ) for ( key, value ) in request_args.items() ] )
    
    return query
    
def DoHydrusBandwidth( service_identifier, method, command, size ):
    
    service_type = service_identifier.GetType()
    
    if ( service_type, method, command ) in HC.BANDWIDTH_CONSUMING_REQUESTS: HC.pubsub.pub( 'service_updates_delayed', { service_identifier : [ HC.ServiceUpdate( HC.SERVICE_UPDATE_REQUEST_MADE, size ) ] } )
    
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
    
class HTTPConnectionManager():
    
    def __init__( self ):
        
        self._connections = {}
        
        self._lock = threading.Lock()
        
        threading.Thread( target = self.MaintainConnections, name = 'Maintain Connections' ).start()
        
    
    def _DoRequest( self, location, method, path_and_query, request_headers, body, follow_redirects = True, report_hooks = [], response_to_path = False, num_redirects_permitted = 4, long_timeout = False ):
        
        connection = self._GetConnection( location, long_timeout )
        
        try:
            
            with connection.lock:
                
                ( parsed_response, redirect_info, size_of_response, response_headers, cookies ) = connection.Request( method, path_and_query, request_headers, body, report_hooks = report_hooks, response_to_path = response_to_path )
                
            
            if redirect_info is None or not follow_redirects: return ( parsed_response, size_of_response, response_headers, cookies )
            else:
                
                if num_redirects_permitted == 0: raise Exception( 'Too many redirects!' )
                
                ( new_method, new_url ) = redirect_info
                
                ( new_location, new_path, new_query ) = ParseURL( new_url )
                
                if new_location is None: new_location = location
                
                if new_query != '': new_path_and_query = new_path + '?' + new_query
                else: new_path_and_query = new_path
                
                return self._DoRequest( new_location, new_method, new_path_and_query, request_headers, body, report_hooks = report_hooks, response_to_path = response_to_path, num_redirects_permitted = num_redirects_permitted - 1 )
                
            
        except:
            
            time.sleep( 2 )
            
            raise
            
        
    
    def _GetConnection( self, location, long_timeout = False ):
        
        with self._lock:
            
            if long_timeout: return HTTPConnection( location, long_timeout )
            else:
                
                if location not in self._connections:
                    
                    connection = HTTPConnection( location )
                    
                    self._connections[ location ] = connection
                    
                
                return self._connections[ location ]
                
            
        
    
    def Request( self, method, url, request_headers = {}, body = '', return_everything = False, return_cookies = False, report_hooks = [], response_to_path = False, long_timeout = False ):
        
        ( location, path, query ) = ParseURL( url )
        
        if query != '': path_and_query = path + '?' + query
        else: path_and_query = path
        
        follow_redirects = not return_cookies
        
        ( response, size_of_response, response_headers, cookies ) = self._DoRequest( location, method, path_and_query, request_headers, body, follow_redirects = follow_redirects, report_hooks = report_hooks, response_to_path = response_to_path, long_timeout = long_timeout )
        
        if return_everything: return ( response, size_of_response, response_headers, cookies )
        elif return_cookies: return ( response, cookies )
        else: return response
        
    
    def MaintainConnections( self ):
        
        while True:
            
            if HC.shutdown: break
            
            with self._lock:
                
                connections_copy = dict( self._connections )
                
                for ( location, connection ) in connections_copy.items():
                    
                    with connection.lock:
                        
                        if connection.IsStale():
                            
                            del self._connections[ location ]
                        
                    
                
            
            time.sleep( 30 )
            
        
    
class HTTPConnection():
    
    read_block_size = 64 * 1024
    
    def __init__( self, location, long_timeout = False ):
        
        ( self._scheme, self._host, self._port ) = location
        
        if long_timeout: self._timeout = 600
        else: self._timeout = 30
        
        self.lock = threading.Lock()
        
        self._last_request_time = HC.GetNow()
        
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
        
        content_length = response.getheader( 'Content-Length' )
        
        if content_length is not None: content_length = int( content_length )
        
        data = ''
        
        next_block = response.read( self.read_block_size )
        
        while next_block != '':
            
            if HC.shutdown: raise Exception( 'Application is shutting down!' )
            
            data += next_block
            
            if content_length is not None and len( data ) > content_length:
                
                raise Exception( 'Response was longer than suggested!' )
                
            
            for hook in report_hooks: hook( content_length, len( data ) )
            
            next_block = response.read( self.read_block_size )
            
        
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
                
            elif content_type in HC.mime_enum_lookup and HC.mime_enum_lookup[ content_type ] == HC.APPLICATION_YAML:
                
                try: parsed_response = yaml.safe_load( data )
                except Exception as e: raise HydrusExceptions.NetworkVersionException( 'Failed to parse a response object!' + os.linesep + u( e ) )
                
            elif content_type == 'text/html':
                
                try: parsed_response = data.decode( 'utf-8' )
                except: parsed_response = data
                
            else: parsed_response = data
            
        
        return ( parsed_response, size_of_response )
        
    
    def _RefreshConnection( self ):
        
        if self._scheme == 'http': self._connection = httplib.HTTPConnection( self._host, self._port, timeout = self._timeout )
        elif self._scheme == 'https': self._connection = httplib.HTTPSConnection( self._host, self._port, timeout = self._timeout )
        
        try: self._connection.connect()
        except: raise Exception( 'Could not connect to ' + HC.u( self._host ) + '!' )
        
    
    def _WriteResponseToPath( self, response, report_hooks ):
        
        content_length = response.getheader( 'Content-Length' )
        
        if content_length is not None: content_length = int( content_length )
        
        temp_path = HC.GetTempPath()
        
        size_of_response = 0
        
        with open( temp_path, 'wb' ) as f:
            
            next_block = response.read( self.read_block_size )
            
            while next_block != '':
                
                if HC.shutdown: raise Exception( 'Application is shutting down!' )
                
                size_of_response += len( next_block )
                
                if content_length is not None and size_of_response > content_length:
                    
                    raise Exception( 'Response was longer than suggested!' )
                    
                
                f.write( next_block )
                
                for hook in report_hooks: hook( content_length, size_of_response )
                
                next_block = response.read( self.read_block_size )
                
            
        
        return ( temp_path, size_of_response )
        
    
    def IsStale( self ):
        
        time_since_last_request = HC.GetNow() - self._last_request_time
        
        return time_since_last_request > self._timeout
        
    
    def Request( self, method, path_and_query, request_headers, body, report_hooks = [], response_to_path = False ):
        
        if method == HC.GET: method_string = 'GET'
        elif method == HC.POST: method_string = 'POST'
        
        if 'User-Agent' not in request_headers: request_headers[ 'User-Agent' ] = 'hydrus/' + HC.u( HC.NETWORK_VERSION )
        
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
            
        
        if response.status == 200 and response_to_path:
            
            ( temp_path, size_of_response ) = self._WriteResponseToPath( response, report_hooks )
            
            parsed_response = temp_path
            
        else:
            
            ( parsed_response, size_of_response ) = self._ParseResponse( response, report_hooks )
            
        
        response_headers = { k : v for ( k, v ) in response.getheaders() if k != 'set-cookie' }
        
        cookies = self._ParseCookies( response.getheader( 'set-cookie' ) )
        
        self._last_request_time = HC.GetNow()
        
        if response.status == 200: return ( parsed_response, None, size_of_response, response_headers, cookies )
        elif response.status in ( 301, 302, 303, 307 ):
            
            location = response.getheader( 'Location' )
            
            if location is None: raise Exception( parsed_response )
            else:
                
                url = location
                
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
            elif response.status == 426: raise HydrusExceptions.NetworkVersionException( parsed_response )
            elif response.status in ( 500, 501, 502, 503 ): raise Exception( parsed_response )
            else: raise Exception( parsed_response )
            
        
    