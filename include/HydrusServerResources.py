import Cookie
import HydrusConstants as HC
import HydrusExceptions
import HydrusFileHandling
import HydrusImageHandling
import HydrusPaths
import HydrusSerialisable
import HydrusThreading
import os
import ServerFiles
import time
import traceback
import yaml
from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread
from twisted.web.server import NOT_DONE_YET
from twisted.web.resource import Resource
from twisted.web.static import File as FileResource, NoRangeStaticProducer
import HydrusData
import HydrusGlobals

CLIENT_ROOT_MESSAGE = '''<html>
    <head>
        <title>hydrus client</title>
    </head>
    <body>
        <p>This hydrus client uses software version ''' + str( HC.SOFTWARE_VERSION ) + ''' and network version ''' + str( HC.NETWORK_VERSION ) + '''.</p>
        <p>It only serves requests from 127.0.0.1.</p>
    </body>
</html>'''

ROOT_MESSAGE_BEGIN = '''<html>
    <head>
        <title>hydrus service</title>
    </head>
    <body>
        <p>This hydrus service uses software version ''' + str( HC.SOFTWARE_VERSION ) + ''' and network version ''' + str( HC.NETWORK_VERSION ) + '''.</p>
        <p>'''

ROOT_MESSAGE_END = '''</p>
    </body>
</html>'''

def ParseFileArguments( path ):
    
    HydrusImageHandling.ConvertToPngIfBmp( path )
    
    hash = HydrusFileHandling.GetHashFromPath( path )
    
    try:
        
        ( size, mime, width, height, duration, num_frames, num_words ) = HydrusFileHandling.GetFileInfo( path )
        
    except HydrusExceptions.SizeException:
        
        raise HydrusExceptions.ForbiddenException( 'File is of zero length!' )
        
    except HydrusExceptions.MimeException:
        
        raise HydrusExceptions.ForbiddenException( 'Filetype is not permitted!' )
        
    except Exception as e:
        
        raise HydrusExceptions.ForbiddenException( HydrusData.ToUnicode( e ) )
        
    
    args = {}
    
    args[ 'path' ] = path
    args[ 'hash' ] = hash
    args[ 'size' ] = size
    args[ 'mime' ] = mime
    
    if width is not None: args[ 'width' ] = width
    if height is not None: args[ 'height' ] = height
    if duration is not None: args[ 'duration' ] = duration
    if num_frames is not None: args[ 'num_frames' ] = num_frames
    if num_words is not None: args[ 'num_words' ] = num_words
    
    if mime in HC.IMAGES:
        
        try: thumbnail = HydrusFileHandling.GenerateThumbnail( path )
        except: raise HydrusExceptions.ForbiddenException( 'Could not generate thumbnail from that file.' )
        
        args[ 'thumbnail' ] = thumbnail
        
    
    return args
    
hydrus_favicon = FileResource( os.path.join( HC.STATIC_DIR, 'hydrus.ico' ), defaultType = 'image/x-icon' )
local_booru_css = FileResource( os.path.join( HC.STATIC_DIR, 'local_booru_style.css' ), defaultType = 'text/css' )

class HydrusDomain( object ):
    
    def __init__( self, local_only ):
        
        self._local_only = local_only
        
    
    def CheckValid( self, client_ip ):
        
        if self._local_only and client_ip != '127.0.0.1': raise HydrusExceptions.ForbiddenException( 'Only local access allowed!' )
        
    
class HydrusResourceBusyCheck( Resource ):
    
    def __init__( self ):
        
        Resource.__init__( self )
        
        self._server_version_string = HC.service_string_lookup[ HC.SERVER_ADMIN ] + '/' + str( HC.NETWORK_VERSION )
        
    
    def render_GET( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        if HydrusGlobals.server_busy: return '1'
        else: return '0'
        
    
class HydrusResourceWelcome( Resource ):
    
    def __init__( self, service_type, message ):
        
        Resource.__init__( self )
        
        if service_type == HC.LOCAL_FILE: body = CLIENT_ROOT_MESSAGE
        else: body = ROOT_MESSAGE_BEGIN + message + ROOT_MESSAGE_END
        
        self._body = HydrusData.ToByteString( body )
        
        self._server_version_string = HC.service_string_lookup[ service_type ] + '/' + str( HC.NETWORK_VERSION )
        
    
    def render_GET( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        return self._body
        
    
class HydrusResourceCommand( Resource ):
    
    def __init__( self, service_key, service_type, domain ):
        
        Resource.__init__( self )
        
        self._service_key = service_key
        self._service_type = service_type
        self._domain = domain
        
        self._server_version_string = HC.service_string_lookup[ service_type ] + '/' + str( HC.NETWORK_VERSION )
        
    
    def _checkServerBusy( self ):
        
        if HydrusGlobals.server_busy:
            
            raise HydrusExceptions.ServerBusyException( 'This server is busy, please try again later.' )
            
        
    
    def _callbackCheckRestrictions( self, request ):
        
        self._checkServerBusy()
        
        self._checkUserAgent( request )
        
        self._domain.CheckValid( request.getClientIP() )
        
        return request
        
    
    def _callbackParseGETArgs( self, request ):
        
        hydrus_args = {}
        
        for name in request.args:
            
            values = request.args[ name ]
            
            value = values[0]
            
            if name in ( 'begin', 'expires', 'lifetime', 'num', 'service_type', 'service_port', 'since', 'subindex', 'timespan' ):
                
                try: hydrus_args[ name ] = int( value )
                except: raise HydrusExceptions.ForbiddenException( 'I was expecting to parse \'' + name + '\' as an integer, but it failed.' )
                
            elif name in ( 'access_key', 'title', 'subject_account_key', 'contact_key', 'hash', 'subject_hash', 'subject_tag', 'message_key', 'share_key' ):
                
                try: hydrus_args[ name ] = value.decode( 'hex' )
                except: raise HydrusExceptions.ForbiddenException( 'I was expecting to parse \'' + name + '\' as a hex-encoded string, but it failed.' )
                
            
        
        if 'subject_account_key' in hydrus_args:
            
            hydrus_args[ 'subject_identifier' ] = HydrusData.AccountIdentifier( account_key = hydrus_args[ 'subject_account_key' ] )
            
        elif 'subject_hash' in hydrus_args:
            
            hash = hydrus_args[ 'subject_hash' ]
            
            if 'subject_tag' in hydrus_args:
                
                tag = hydrus_args[ 'subject_tag' ]
                
                content = HydrusData.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) )
                
            else:
                
                content = HydrusData.Content( HC.CONTENT_TYPE_FILES, [ hash ] )
                
            
            hydrus_args[ 'subject_identifier' ] = HydrusData.AccountIdentifier( content = content )
            
        
        request.hydrus_args = hydrus_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request ):
        
        request.content.seek( 0 )
        
        if not request.requestHeaders.hasHeader( 'Content-Type' ):
            
            hydrus_args = {}
            
        else:
            
            content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
            
            content_type = content_types[0]
            
            try: mime = HC.mime_enum_lookup[ content_type ]
            except: raise HydrusExceptions.ForbiddenException( 'Did not recognise Content-Type header!' )
            
            if mime == HC.APPLICATION_YAML:
                
                yaml_string = request.content.read()
                
                request.hydrus_request_data_usage += len( yaml_string )
                
                hydrus_args = yaml.safe_load( yaml_string )
                
            elif mime == HC.APPLICATION_JSON:
                
                json_string = request.content.read()
                
                request.hydrus_request_data_usage += len( json_string )
                
                hydrus_args = HydrusSerialisable.CreateFromNetworkString( json_string )
                
            else:
                
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                request.temp_file_info = ( os_file_handle, temp_path )
                
                with open( temp_path, 'wb' ) as f:
                    
                    for block in HydrusPaths.ReadFileLikeAsBlocks( request.content ): 
                        
                        f.write( block )
                        
                        request.hydrus_request_data_usage += len( block )
                        
                    
                
                hydrus_args = ParseFileArguments( temp_path )
                
            
        
        request.hydrus_args = hydrus_args
        
        return request
        
    
    def _callbackRenderResponseContext( self, request ):
        
        self._CleanUpTempFile( request )
        
        response_context = request.hydrus_response_context
        
        status_code = response_context.GetStatusCode()
        
        request.setResponseCode( status_code )
        
        for ( k, v, kwargs ) in response_context.GetCookies(): request.addCookie( k, v, **kwargs )
        
        do_finish = True
        
        if response_context.HasBody():
            
            ( mime, body ) = response_context.GetMimeBody()
            
            content_type = HC.mime_string_lookup[ mime ]
            
            content_length = len( body )
            
            request.setHeader( 'Content-Type', content_type )
            request.setHeader( 'Content-Length', str( content_length ) )
            
            request.write( HydrusData.ToByteString( body ) )
            
        elif response_context.HasPath():
            
            path = response_context.GetPath()
            
            info = os.lstat( path )
            
            size = info[6]
            
            if response_context.IsJSON():
                
                mime = HC.APPLICATION_JSON
                
                content_type = HC.mime_string_lookup[ mime ]
                
            else:
                
                mime = HydrusFileHandling.GetMime( path )
                
                ( base, filename ) = os.path.split( path )
                
                content_type = HC.mime_string_lookup[ mime ] + '; ' + filename
                
            
            content_length = size
            
            # can't be unicode!
            request.setHeader( 'Content-Type', str( content_type ) )
            request.setHeader( 'Content-Length', str( content_length ) )
            
            request.setHeader( 'Expires', time.strftime( '%a, %d %b %Y %H:%M:%S GMT', time.gmtime( time.time() + 86400 * 365 ) ) )
            request.setHeader( 'Cache-Control', str( 86400 * 365  ) )
            
            fileObject = open( path, 'rb' )
            
            producer = NoRangeStaticProducer( request, fileObject )
            
            producer.start()
            
            do_finish = False
            
        else:
            
            content_length = 0
            
            request.setHeader( 'Content-Length', str( content_length ) )
            
        
        request.hydrus_request_data_usage += content_length
        
        self._recordDataUsage( request )
        
        if do_finish: request.finish()
        
    
    def _callbackDoGETJob( self, request ):
        
        def wrap_thread_result( response_context ):
            
            request.hydrus_response_context = response_context
            
            return request
            
        
        d = deferToThread( self._threadDoGETJob, request )
        
        d.addCallback( wrap_thread_result )
        
        return d
        
    
    def _callbackDoPOSTJob( self, request ):
        
        def wrap_thread_result( response_context ):
            
            request.hydrus_response_context = response_context
            
            return request
            
        
        d = deferToThread( self._threadDoPOSTJob, request )
        
        d.addCallback( wrap_thread_result )
        
        return d
        
    
    def _checkUserAgent( self, request ):
        
        request.is_hydrus_user_agent = False
        
        if request.requestHeaders.hasHeader( 'User-Agent' ):
            
            user_agent_texts = request.requestHeaders.getRawHeaders( 'User-Agent' )
            
            user_agent_text = user_agent_texts[0]
            
            try:
                
                user_agents = user_agent_text.split( ' ' )
                
            except: return # crazy user agent string, so just assume not a hydrus client
            
            for user_agent in user_agents:
                
                if '/' in user_agent:
                    
                    ( client, network_version ) = user_agent.split( '/', 1 )
                    
                    if client == 'hydrus':
                        
                        request.is_hydrus_user_agent = True
                        
                        network_version = int( network_version )
                        
                        if network_version == HC.NETWORK_VERSION: return
                        else:
                            
                            if network_version < HC.NETWORK_VERSION: message = 'Your client is out of date; please download the latest release.'
                            else: message = 'This server is out of date; please ask its admin to update to the latest release.'
                            
                            raise HydrusExceptions.NetworkVersionException( 'Network version mismatch! This server\'s network version is ' + str( HC.NETWORK_VERSION ) + ', whereas your client\'s is ' + str( network_version ) + '! ' + message )
                            
                        
                    
                
            
        
    
    def _errbackHandleEmergencyError( self, failure, request ):
        
        try: self._CleanUpTempFile( request )
        except: pass
        
        try: print( failure.getTraceback() )
        except: pass
        
        try: request.write( failure.getTraceback() )
        except: pass
        
        request.finish()
        
    
    def _errbackHandleProcessingError( self, failure, request ):
        
        self._CleanUpTempFile( request )
        
        do_yaml = True
        
        try:
            
            # the error may have occured before user agent was set up!
            if not request.is_hydrus_user_agent: do_yaml = False
            
        except: pass
        
        if do_yaml:
            
            default_mime = HC.APPLICATION_YAML
            default_encoding = lambda x: yaml.safe_dump( HydrusData.ToUnicode( x ) )
            
        else:
            
            default_mime = HC.TEXT_HTML
            default_encoding = lambda x: HydrusData.ToByteString( x )
            
        
        if failure.type == KeyError: response_context = ResponseContext( 403, mime = default_mime, body = default_encoding( 'It appears one or more parameters required for that request were missing:' + os.linesep + failure.getTraceback() ) )
        elif failure.type == HydrusExceptions.PermissionException: response_context = ResponseContext( 401, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.ForbiddenException: response_context = ResponseContext( 403, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.NotFoundException: response_context = ResponseContext( 404, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.NetworkVersionException: response_context = ResponseContext( 426, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.ServerBusyException: response_context = ResponseContext( 503, mime = default_mime, body = default_encoding( failure.value ) )
        elif failure.type == HydrusExceptions.SessionException: response_context = ResponseContext( 419, mime = default_mime, body = default_encoding( failure.value ) )
        else:
            
            print( failure.getTraceback() )
            
            response_context = ResponseContext( 500, mime = default_mime, body = default_encoding( 'The repository encountered an error it could not handle! Here is a dump of what happened, which will also be written to your client.log file. If it persists, please forward it to hydrus.admin@gmail.com:' + os.linesep * 2 + failure.getTraceback() ) )
            
        
        request.hydrus_response_context = response_context
        
        return request
        
    
    def _parseAccessKey( self, request ):
        
        if not request.requestHeaders.hasHeader( 'Hydrus-Key' ): raise HydrusExceptions.PermissionException( 'No hydrus key header found!' )
        
        hex_keys = request.requestHeaders.getRawHeaders( 'Hydrus-Key' )
        
        hex_key = hex_keys[0]
        
        try: access_key = hex_key.decode( 'hex' )
        except: raise HydrusExceptions.ForbiddenException( 'Could not parse the hydrus key!' )
        
        return access_key
        
    
    def _recordDataUsage( self, request ): pass
    
    def _threadDoGETJob( self, request ): raise HydrusExceptions.NotFoundException( 'This service does not support that request!' )
    
    def _threadDoPOSTJob( self, request ): raise HydrusExceptions.NotFoundException( 'This service does not support that request!' )
    
    def _CleanUpTempFile( self, request ):
        
        if hasattr( request, 'temp_file_info' ):
            
            ( os_file_handle, temp_path ) = request.temp_file_info
            
            HydrusPaths.CleanUpTempPath( os_file_handle, temp_path )
            
            del request.temp_file_info
            
        
    
    def render_GET( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        d = defer.Deferred()
        
        d.addCallback( self._callbackCheckRestrictions )
        
        d.addCallback( self._callbackParseGETArgs )
        
        d.addCallback( self._callbackDoGETJob )
        
        d.addErrback( self._errbackHandleProcessingError, request )
        
        d.addCallback( self._callbackRenderResponseContext )
        
        d.addErrback( self._errbackHandleEmergencyError, request )
        
        reactor.callLater( 0, d.callback, request )
        
        return NOT_DONE_YET
        
    
    def render_POST( self, request ):
        
        request.setHeader( 'Server', self._server_version_string )
        
        d = defer.Deferred()
        
        d.addCallback( self._callbackCheckRestrictions )
        
        d.addCallback( self._callbackParsePOSTArgs )
        
        d.addCallback( self._callbackDoPOSTJob )
        
        d.addErrback( self._errbackHandleProcessingError, request )
        
        d.addCallback( self._callbackRenderResponseContext )
        
        d.addErrback( self._errbackHandleEmergencyError, request )
        
        reactor.callLater( 0, d.callback, request )
        
        return NOT_DONE_YET
        
    
class HydrusResourceCommandAccessKey( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        registration_key = self._parseAccessKey( request )
        
        access_key = HydrusGlobals.controller.Read( 'access_key', registration_key )
        
        body = yaml.safe_dump( { 'access_key' : access_key } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandShutdown( HydrusResourceCommand ):
    
    def _threadDoPOSTJob( self, request ):
        
        HydrusGlobals.controller.ShutdownFromServer()
        
        response_context = ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandAccessKeyVerification( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        verified = HydrusGlobals.controller.Read( 'verify_access_key', self._service_key, access_key )
        
        body = yaml.safe_dump( { 'verified' : verified } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandInit( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = HydrusGlobals.controller.Read( 'init' )
        
        body = yaml.safe_dump( { 'access_key' : access_key } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandSessionKey( HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        session_manager = HydrusGlobals.controller.GetManager( 'restricted_services_sessions' )
        
        ( session_key, expires ) = session_manager.AddSession( self._service_key, access_key )
        
        now = HydrusData.GetNow()
        
        max_age = now - expires
        
        cookies = [ ( 'session_key', session_key.encode( 'hex' ), { 'max_age' : max_age, 'path' : '/' } ) ]
        
        response_context = ResponseContext( 200, cookies = cookies )
        
        return response_context
        
    
class HydrusResourceCommandRestricted( HydrusResourceCommand ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _callbackCheckRestrictions( self, request ):
        
        self._checkServerBusy()
        
        self._checkUserAgent( request )
        
        self._domain.CheckValid( request.getClientIP() )
        
        self._checkSession( request )
        
        self._checkPermission( request )
        
        return request
        
    
    def _checkPermission( self, request ):
        
        account = request.hydrus_account
        
        method = request.method
        
        permission = None
        
        if method == 'GET': permission = self.GET_PERMISSION
        elif method == 'POST': permission = self.POST_PERMISSION
        
        if permission is not None: account.CheckPermission( permission )
        
        return request
        
    
    def _checkSession( self, request ):
        
        if not request.requestHeaders.hasHeader( 'Cookie' ): raise HydrusExceptions.PermissionException( 'No cookies found!' )
        
        cookie_texts = request.requestHeaders.getRawHeaders( 'Cookie' )
        
        cookie_text = cookie_texts[0]
        
        try:
            
            cookies = Cookie.SimpleCookie( cookie_text )
            
            if 'session_key' not in cookies: session_key = None
            else: session_key = cookies[ 'session_key' ].value.decode( 'hex' )
            
        except: raise Exception( 'Problem parsing cookies!' )
        
        session_manager = HydrusGlobals.controller.GetManager( 'restricted_services_sessions' )
        
        account = session_manager.GetAccount( self._service_key, session_key )
        
        request.hydrus_account = account
        
        return request
        
    
    def _recordDataUsage( self, request ):
        
        path = request.path[1:] # /account -> account
        
        if request.method == 'GET': method = HC.GET
        else: method = HC.POST
        
        if ( self._service_type, method, path ) in HC.BANDWIDTH_CONSUMING_REQUESTS:
            
            account = request.hydrus_account
            
            if account is not None:
                
                num_bytes = request.hydrus_request_data_usage
                
                account.RequestMade( num_bytes )
                
                HydrusGlobals.controller.pub( 'request_made', ( account.GetAccountKey(), num_bytes ) )
                
            
        
    
class HydrusResourceCommandRestrictedAccount( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = None
    POST_PERMISSION = HC.MANAGE_USERS
    
    def _threadDoGETJob( self, request ):
        
        account = request.hydrus_account
        
        body = yaml.safe_dump( { 'account' : account } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        admin_account = request.hydrus_account
        
        admin_account_key = admin_account.GetAccountKey()
        
        action = request.hydrus_args[ 'action' ]
        
        subject_identifiers = request.hydrus_args[ 'subject_identifiers' ]
        
        subject_account_keys = { HydrusGlobals.controller.Read( 'account_key_from_identifier', self._service_key, subject_identifier ) for subject_identifier in subject_identifiers }
        
        kwargs = request.hydrus_args # for things like expires, title, and so on
        
        HydrusGlobals.controller.WriteSynchronous( 'account', self._service_key, admin_account_key, action, subject_account_keys, kwargs )
        
        session_manager = HydrusGlobals.controller.GetManager( 'restricted_services_sessions' )
        
        session_manager.RefreshAccounts( self._service_key, subject_account_keys )
        
        response_context = ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedAccountInfo( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        subject_identifier = request.hydrus_args[ 'subject_identifier' ]
        
        subject_account_key = HydrusGlobals.controller.Read( 'account_key_from_identifier', self._service_key, subject_identifier )
        
        account_info = HydrusGlobals.controller.Read( 'account_info', self._service_key, subject_account_key )
        
        body = yaml.safe_dump( { 'account_info' : account_info } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedAccountTypes( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        account_types = HydrusGlobals.controller.Read( 'account_types', self._service_key )
        
        body = yaml.safe_dump( { 'account_types' : account_types } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        edit_log = request.hydrus_args[ 'edit_log' ]
        
        HydrusGlobals.controller.WriteSynchronous( 'account_types', self._service_key, edit_log )
        
        response_context = ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedBackup( HydrusResourceCommandRestricted ):
    
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        def do_it():
            
            HydrusGlobals.server_busy = True
            
            HydrusGlobals.controller.WriteSynchronous( 'backup' )
            
            HydrusGlobals.server_busy = False
            
        
        HydrusGlobals.controller.CallToThread( do_it )
        
        response_context = ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedIP( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        ( ip, timestamp ) = HydrusGlobals.controller.Read( 'ip', self._service_key, hash )
        
        body = yaml.safe_dump( { 'ip' : ip, 'timestamp' : timestamp } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedNews( HydrusResourceCommandRestricted ):
    
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        news = request.hydrus_args[ 'news' ]
        
        HydrusGlobals.controller.WriteSynchronous( 'news', self._service_key, news )
        
        response_context = ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedNumPetitions( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        num_petitions = HydrusGlobals.controller.Read( 'num_petitions', self._service_key )
        
        body = yaml.safe_dump( { 'num_petitions' : num_petitions } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedPetition( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        petition = HydrusGlobals.controller.Read( 'petition', self._service_key )
        
        body = petition.DumpToNetworkString()
        
        response_context = ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRegistrationKeys( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        num = request.hydrus_args[ 'num' ]
        title = request.hydrus_args[ 'title' ]
        
        if 'lifetime' in request.hydrus_args: lifetime = request.hydrus_args[ 'lifetime' ]
        else: lifetime = None
        
        registration_keys = HydrusGlobals.controller.Read( 'registration_keys', self._service_key, num, title, lifetime )
        
        body = yaml.safe_dump( { 'registration_keys' : registration_keys } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRepositoryFile( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    POST_PERMISSION = HC.POST_DATA
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        # don't I need to check that we aren't stealing the file from another service?
        
        path = ServerFiles.GetPath( 'file', hash )
        
        response_context = ResponseContext( 200, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        account_key = account.GetAccountKey()
        
        file_dict = request.hydrus_args
        
        file_dict[ 'ip' ] = request.getClientIP()
        
        HydrusGlobals.controller.WriteSynchronous( 'file', self._service_key, account_key, file_dict )
        
        response_context = ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRepositoryThumbnail( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        # don't I need to check that we aren't stealing the file from another service?
        
        path = ServerFiles.GetPath( 'thumbnail', hash )
        
        response_context = ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedServices( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        account_key = account.GetAccountKey()
        
        edit_log = request.hydrus_args[ 'edit_log' ]
        
        service_keys_to_access_keys = HydrusGlobals.controller.WriteSynchronous( 'services', account_key, edit_log )
        
        body = yaml.safe_dump( { 'service_keys_to_access_keys' : service_keys_to_access_keys } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedServicesInfo( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        services_info = HydrusGlobals.controller.Read( 'services_info' )
        
        body = yaml.safe_dump( { 'services_info' : services_info } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedStats( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        stats = HydrusGlobals.controller.Read( 'stats', self._service_key )
        
        body = yaml.safe_dump( { 'stats' : stats } )
        
        response_context = ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedContentUpdate( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    POST_PERMISSION = HC.POST_DATA
    
    def _threadDoGETJob( self, request ):
        
        begin = request.hydrus_args[ 'begin' ]
        subindex = request.hydrus_args[ 'subindex' ]
        
        path = ServerFiles.GetContentUpdatePackagePath( self._service_key, begin, subindex )
        
        response_context = ResponseContext( 200, path = path, is_json = True )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        account_key = account.GetAccountKey()
        
        update = request.hydrus_args[ 'update' ]
        
        HydrusGlobals.controller.WriteSynchronous( 'update', self._service_key, account_key, update )
        
        response_context = ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedImmediateContentUpdate( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        content_update = HydrusGlobals.controller.Read( 'immediate_content_update', self._service_key )
        
        network_string = content_update.DumpToNetworkString()
        
        response_context = ResponseContext( 200, mime = HC.APPLICATION_JSON, body = network_string )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedServiceUpdate( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    
    def _threadDoGETJob( self, request ):
        
        begin = request.hydrus_args[ 'begin' ]
        
        path = ServerFiles.GetServiceUpdatePackagePath( self._service_key, begin )
        
        response_context = ResponseContext( 200, path = path, is_json = True )
        
        return response_context
        
    
class ResponseContext( object ):
    
    def __init__( self, status_code, mime = HC.APPLICATION_YAML, body = None, path = None, is_json = False, cookies = None ):
        
        if cookies is None: cookies = []
        
        self._status_code = status_code
        self._mime = mime
        self._body = body
        self._path = path
        self._is_json = is_json
        self._cookies = cookies
        
    
    def GetCookies( self ): return self._cookies
    
    def GetLength( self ): return len( self._body )
    
    def GetMimeBody( self ): return ( self._mime, self._body )
    
    def GetPath( self ): return self._path
    
    def GetStatusCode( self ): return self._status_code
    
    def HasBody( self ): return self._body is not None
    
    def HasPath( self ): return self._path is not None
    
    def IsJSON( self ): return self._is_json
    