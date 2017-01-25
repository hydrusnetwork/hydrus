import Cookie
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusServerResources
import ServerFiles
import yaml

class HydrusResourceBusyCheck( HydrusServerResources.Resource ):
    
    def __init__( self ):
        
        HydrusServerResources.Resource.__init__( self )
        
        self._server_version_string = HC.service_string_lookup[ HC.SERVER_ADMIN ] + '/' + str( HC.NETWORK_VERSION )
        
    
    def render_GET( self, request ):
        
        request.setResponseCode( 200 )
        
        request.setHeader( 'Server', self._server_version_string )
        
        if HydrusGlobals.server_busy: return '1'
        else: return '0'
        
    
class HydrusResourceCommandAccessKey( HydrusServerResources.HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        registration_key = self._parseAccessKey( request )
        
        access_key = HydrusGlobals.server_controller.Read( 'access_key', registration_key )
        
        body = yaml.safe_dump( { 'access_key' : access_key } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandShutdown( HydrusServerResources.HydrusResourceCommand ):
    
    def _threadDoPOSTJob( self, request ):
        
        HydrusGlobals.server_controller.ShutdownFromServer()
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandAccessKeyVerification( HydrusServerResources.HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        verified = HydrusGlobals.server_controller.Read( 'verify_access_key', self._service_key, access_key )
        
        body = yaml.safe_dump( { 'verified' : verified } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandInit( HydrusServerResources.HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = HydrusGlobals.server_controller.Read( 'init' )
        
        body = yaml.safe_dump( { 'access_key' : access_key } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandSessionKey( HydrusServerResources.HydrusResourceCommand ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        session_manager = HydrusGlobals.server_controller.GetServerSessionManager()
        
        ( session_key, expires ) = session_manager.AddSession( self._service_key, access_key )
        
        now = HydrusData.GetNow()
        
        max_age = now - expires
        
        cookies = [ ( 'session_key', session_key.encode( 'hex' ), { 'max_age' : max_age, 'path' : '/' } ) ]
        
        response_context = HydrusServerResources.ResponseContext( 200, cookies = cookies )
        
        return response_context
        
    
class HydrusResourceCommandRestricted( HydrusServerResources.HydrusResourceCommand ):
    
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
        
        session_manager = HydrusGlobals.server_controller.GetServerSessionManager()
        
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
                
                HydrusGlobals.server_controller.pub( 'request_made', ( account.GetAccountKey(), num_bytes ) )
                
            
        
    
class HydrusResourceCommandRestrictedAccount( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = None
    POST_PERMISSION = HC.MANAGE_USERS
    
    def _threadDoGETJob( self, request ):
        
        account = request.hydrus_account
        
        body = yaml.safe_dump( { 'account' : account } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        admin_account = request.hydrus_account
        
        admin_account_key = admin_account.GetAccountKey()
        
        action = request.hydrus_args[ 'action' ]
        
        subject_identifiers = request.hydrus_args[ 'subject_identifiers' ]
        
        subject_account_keys = { HydrusGlobals.server_controller.Read( 'account_key_from_identifier', self._service_key, subject_identifier ) for subject_identifier in subject_identifiers }
        
        kwargs = request.hydrus_args # for things like expires, title, and so on
        
        HydrusGlobals.server_controller.WriteSynchronous( 'account', self._service_key, admin_account_key, action, subject_account_keys, kwargs )
        
        session_manager = HydrusGlobals.server_controller.GetServerSessionManager()
        
        session_manager.RefreshAccounts( self._service_key, subject_account_keys )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedAccountInfo( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        subject_identifier = request.hydrus_args[ 'subject_identifier' ]
        
        subject_account_key = HydrusGlobals.server_controller.Read( 'account_key_from_identifier', self._service_key, subject_identifier )
        
        account_info = HydrusGlobals.server_controller.Read( 'account_info', self._service_key, subject_account_key )
        
        body = yaml.safe_dump( { 'account_info' : account_info } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedAccountTypes( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        account_types = HydrusGlobals.server_controller.Read( 'account_types', self._service_key )
        
        body = yaml.safe_dump( { 'account_types' : account_types } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        edit_log = request.hydrus_args[ 'edit_log' ]
        
        HydrusGlobals.server_controller.WriteSynchronous( 'account_types', self._service_key, edit_log )
        
        session_manager = HydrusGlobals.server_controller.GetServerSessionManager()
        
        session_manager.RefreshAccounts( self._service_key )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedBackup( HydrusResourceCommandRestricted ):
    
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        def do_it():
            
            HydrusGlobals.server_busy = True
            
            HydrusGlobals.server_controller.WriteSynchronous( 'backup' )
            
            HydrusGlobals.server_busy = False
            
        
        HydrusGlobals.server_controller.CallToThread( do_it )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedIP( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        ( ip, timestamp ) = HydrusGlobals.server_controller.Read( 'ip', self._service_key, hash )
        
        body = yaml.safe_dump( { 'ip' : ip, 'timestamp' : timestamp } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedNews( HydrusResourceCommandRestricted ):
    
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        news = request.hydrus_args[ 'news' ]
        
        HydrusGlobals.server_controller.WriteSynchronous( 'news', self._service_key, news )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedNumPetitions( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        num_petitions = HydrusGlobals.server_controller.Read( 'num_petitions', self._service_key )
        
        body = yaml.safe_dump( { 'num_petitions' : num_petitions } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedPetition( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        petition = HydrusGlobals.server_controller.Read( 'petition', self._service_key )
        
        body = petition.DumpToNetworkString()
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRegistrationKeys( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        num = request.hydrus_args[ 'num' ]
        title = request.hydrus_args[ 'title' ]
        
        if 'lifetime' in request.hydrus_args: lifetime = request.hydrus_args[ 'lifetime' ]
        else: lifetime = None
        
        registration_keys = HydrusGlobals.server_controller.Read( 'registration_keys', self._service_key, num, title, lifetime )
        
        body = yaml.safe_dump( { 'registration_keys' : registration_keys } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRepositoryFile( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    POST_PERMISSION = HC.POST_DATA
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        # don't I need to check that we aren't stealing the file from another service?
        
        path = ServerFiles.GetFilePath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        account_key = account.GetAccountKey()
        
        file_dict = request.hydrus_args
        
        file_dict[ 'ip' ] = request.getClientIP()
        
        HydrusGlobals.server_controller.WriteSynchronous( 'file', self._service_key, account_key, file_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedRepositoryThumbnail( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        # don't I need to check that we aren't stealing the file from another service?
        
        path = ServerFiles.GetThumbnailPath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, path = path )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedServices( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        account_key = account.GetAccountKey()
        
        edit_log = request.hydrus_args[ 'edit_log' ]
        
        service_keys_to_access_keys = HydrusGlobals.server_controller.WriteSynchronous( 'services', account_key, edit_log )
        
        body = yaml.safe_dump( { 'service_keys_to_access_keys' : service_keys_to_access_keys } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedServicesInfo( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    POST_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        services_info = HydrusGlobals.server_controller.Read( 'services_info' )
        
        body = yaml.safe_dump( { 'services_info' : services_info } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedStats( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GENERAL_ADMIN
    
    def _threadDoGETJob( self, request ):
        
        stats = HydrusGlobals.server_controller.Read( 'stats', self._service_key )
        
        body = yaml.safe_dump( { 'stats' : stats } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedContentUpdate( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    POST_PERMISSION = HC.POST_DATA
    
    def _threadDoGETJob( self, request ):
        
        begin = request.hydrus_args[ 'begin' ]
        subindex = request.hydrus_args[ 'subindex' ]
        
        path = ServerFiles.GetContentUpdatePackagePath( self._service_key, begin, subindex )
        
        response_context = HydrusServerResources.ResponseContext( 200, path = path, is_json = True )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account = request.hydrus_account
        
        account_key = account.GetAccountKey()
        
        update = request.hydrus_args[ 'update' ]
        
        HydrusGlobals.server_controller.WriteSynchronous( 'update', self._service_key, account_key, update )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedImmediateContentUpdate( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.RESOLVE_PETITIONS
    
    def _threadDoGETJob( self, request ):
        
        content_update = HydrusGlobals.server_controller.Read( 'immediate_content_update', self._service_key )
        
        network_string = content_update.DumpToNetworkString()
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_JSON, body = network_string )
        
        return response_context
        
    
class HydrusResourceCommandRestrictedServiceUpdate( HydrusResourceCommandRestricted ):
    
    GET_PERMISSION = HC.GET_DATA
    
    def _threadDoGETJob( self, request ):
        
        begin = request.hydrus_args[ 'begin' ]
        
        path = ServerFiles.GetServiceUpdatePackagePath( self._service_key, begin )
        
        response_context = HydrusServerResources.ResponseContext( 200, path = path, is_json = True )
        
        return response_context
        
    
