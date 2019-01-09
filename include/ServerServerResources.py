import http.cookies
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetwork
from . import HydrusSerialisable
from . import HydrusServerResources
from . import ServerFiles

class HydrusResourceBusyCheck( HydrusServerResources.Resource ):
    
    def __init__( self ):
        
        HydrusServerResources.Resource.__init__( self )
        
        self._server_version_string = HC.service_string_lookup[ HC.SERVER_ADMIN ] + '/' + str( HC.NETWORK_VERSION )
        
    
    def render_GET( self, request ):
        
        request.setResponseCode( 200 )
        
        request.setHeader( 'Server', self._server_version_string )
        
        if HG.server_busy: return '1'
        else: return '0'
        
    
class HydrusResourceAccessKey( HydrusServerResources.HydrusResource ):
    
    def _threadDoGETJob( self, request ):
        
        registration_key = request.hydrus_args[ 'registration_key' ]
        
        access_key = HG.server_controller.Read( 'access_key', self._service_key, registration_key )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'access_key' : access_key } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceShutdown( HydrusServerResources.HydrusResource ):
    
    def _threadDoPOSTJob( self, request ):
        
        HG.server_controller.ShutdownFromServer()
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceAccessKeyVerification( HydrusServerResources.HydrusResource ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        verified = HG.server_controller.Read( 'verify_access_key', self._service_key, access_key )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'verified' : verified } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceSessionKey( HydrusServerResources.HydrusResource ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseAccessKey( request )
        
        ( session_key, expires ) = HG.server_controller.server_session_manager.AddSession( self._service_key, access_key )
        
        now = HydrusData.GetNow()
        
        max_age = expires - now
        
        cookies = [ ( 'session_key', session_key.hex(), { 'max_age' : max_age, 'path' : '/' } ) ]
        
        response_context = HydrusServerResources.ResponseContext( 200, cookies = cookies )
        
        return response_context
        
    
class HydrusResourceRestricted( HydrusServerResources.HydrusResource ):
    
    def _callbackCheckRestrictions( self, request ):
        
        HydrusServerResources.HydrusResource._callbackCheckRestrictions( self, request )
        
        self._checkSession( request )
        
        self._checkAccount( request )
        
        return request
        
    
    def _checkAccount( self, request ):
        
        request.hydrus_account.CheckFunctional()
        
        return request
        
    
    def _checkBandwidth( self, request ):
        
        if not self._service.BandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This service has run out of bandwidth. Please try again later.' )
            
        
        if not HG.server_controller.ServerBandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This server has run out of bandwidth. Please try again later.' )
            
        
    
    def _checkSession( self, request ):
        
        if not request.requestHeaders.hasHeader( 'Cookie' ):
            
            raise HydrusExceptions.PermissionException( 'No cookies found!' )
            
        
        cookie_texts = request.requestHeaders.getRawHeaders( 'Cookie' )
        
        cookie_text = cookie_texts[0]
        
        try:
            
            cookies = http.cookies.SimpleCookie( cookie_text )
            
            if 'session_key' not in cookies:
                
                session_key = None
                
            else:
                
                # Morsel, for real, ha ha ha
                morsel = cookies[ 'session_key' ]
                
                session_key_hex = morsel.value
                
                session_key = bytes.fromhex( session_key_hex )
                
            
        except:
            
            raise Exception( 'Problem parsing cookies!' )
            
        
        account = HG.server_controller.server_session_manager.GetAccount( self._service_key, session_key )
        
        request.hydrus_account = account
        
        return request
        
    
    def _reportDataUsed( self, request, num_bytes ):
        
        HydrusServerResources.HydrusResource._reportDataUsed( self, request, num_bytes )
        
        account = request.hydrus_account
        
        if account is not None:
            
            account.ReportDataUsed( num_bytes )
            
        
    
    def _reportRequestUsed( self, request ):
        
        HydrusServerResources.HydrusResource._reportRequestUsed( self, request )
        
        account = request.hydrus_account
        
        if account is not None:
            
            account.ReportRequestUsed()
            
        
    
class HydrusResourceRestrictedAccount( HydrusResourceRestricted ):
    
    def _checkAccount( self, request ):
        
        # you can always fetch your account (e.g. to be notified that you are banned!)
        
        return request
        
    
    def _threadDoGETJob( self, request ):
        
        account = request.hydrus_account
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'account' : account } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountInfo( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        subject_identifier = request.hydrus_args[ 'subject_identifier' ]
        
        if subject_identifier.HasAccountKey():
            
            subject_account_key = subject_identifier.GetData()
            
        else:
            
            raise HydrusExceptions.PermissionException( 'I was expecting an account key, but did not get one!' )
            
        
        subject_account = HG.server_controller.Read( 'account', self._service_key, subject_account_key )
        
        account_info = HG.server_controller.Read( 'account_info', self._service_key, request.hydrus_account, subject_account )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'account_info' : account_info } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountModification( HydrusResourceRestricted ):
    
    def _threadDoPOSTJob( self, request ):
        
        action = request.hydrus_args[ 'action' ]
        
        subject_accounts = request.hydrus_args[ 'accounts' ]
        
        kwargs = request.hydrus_args # for things like expires, title, and so on
        
        with HG.dirty_object_lock:
            
            HG.server_controller.WriteSynchronous( 'account_modification', self._service_key, request.hydrus_account, action, subject_accounts, **kwargs )
            
            HG.server_controller.server_session_manager.UpdateAccounts( self._service_key, subject_accounts )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountTypes( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        account_types = HG.server_controller.Read( 'account_types', self._service_key, request.hydrus_account )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'account_types' : account_types } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account_types = request.hydrus_args[ 'account_types' ]
        deletee_account_type_keys_to_new_account_type_keys = request.hydrus_args[ 'deletee_account_type_keys_to_new_account_type_keys' ]
        
        HG.server_controller.WriteSynchronous( 'account_types', self._service_key, request.hydrus_account, account_types, deletee_account_type_keys_to_new_account_type_keys )
        
        HG.server_controller.server_session_manager.RefreshAccounts( self._service_key )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedBackup( HydrusResourceRestricted ):
    
    def _threadDoPOSTJob( self, request ):
        
        # check permission here since this is an asynchronous job
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_OVERRULE )
        
        HG.server_controller.Write( 'backup' )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedIP( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        hash = request.hydrus_args[ 'hash' ]
        
        ( ip, timestamp ) = HG.server_controller.Read( 'ip', self._service_key, request.hydrus_account, hash )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'ip' : ip, 'timestamp' : timestamp } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedNumPetitions( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        petition_count_info = HG.server_controller.Read( 'num_petitions', self._service_key, request.hydrus_account )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'num_petitions' : petition_count_info } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedPetition( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        content_type = request.hydrus_args[ 'content_type' ]
        status = request.hydrus_args[ 'status' ]
        
        petition = HG.server_controller.Read( 'petition', self._service_key, request.hydrus_account, content_type, status )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'petition' : petition } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedRegistrationKeys( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        num = request.hydrus_args[ 'num' ]
        account_type_key = request.hydrus_args[ 'account_type_key' ]
        
        if 'expires' in request.hydrus_args:
            
            expires = request.hydrus_args[ 'expires' ]
            
        else:
            
            expires = None
            
        
        registration_keys = HG.server_controller.Read( 'registration_keys', self._service_key, request.hydrus_account, num, account_type_key, expires )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'registration_keys' : registration_keys } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedRepositoryFile( HydrusResourceRestricted ):
    
    def _DecompressionBombsOK( self, request ):
        
        return request.hydrus_account.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
        
    
    def _threadDoGETJob( self, request ):
        
        self._checkBandwidth( request )
        
        # no permission check as any functional account can get files
        
        hash = request.hydrus_args[ 'hash' ]
        
        ( valid, mime ) = HG.server_controller.Read( 'service_has_file', self._service_key, hash )
        
        if not valid:
            
            raise HydrusExceptions.NotFoundException( 'File not found on this service!' )
            
        
        path = ServerFiles.GetFilePath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        file_dict = request.hydrus_args
        
        if self._service.LogUploaderIPs():
            
            file_dict[ 'ip' ] = request.getClientIP()
            
        
        HG.server_controller.WriteSynchronous( 'file', self._service, request.hydrus_account, file_dict )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedRepositoryThumbnail( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        self._checkBandwidth( request )
        
        # no permission check as any functional account can get thumbnails
        
        hash = request.hydrus_args[ 'hash' ]
        
        ( valid, mime ) = HG.server_controller.Read( 'service_has_file', self._service_key, hash )
        
        if not valid:
            
            raise HydrusExceptions.NotFoundException( 'Thumbnail not found on this service!' )
            
        
        if mime not in HC.MIMES_WITH_THUMBNAILS:
            
            raise HydrusExceptions.NotFoundException( 'That mime should not have a thumbnail!' )
            
        
        path = ServerFiles.GetThumbnailPath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_OCTET_STREAM, path = path )
        
        return response_context
        
    
class HydrusResourceRestrictedServices( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        services = HG.server_controller.Read( 'services_from_account', request.hydrus_account )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'services' : services } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        services = request.hydrus_args[ 'services' ]
        
        unique_ports = { service.GetPort() for service in services }
        
        if len( unique_ports ) < len( services ):
            
            raise HydrusExceptions.PermissionException( 'It looks like some of those services share ports! Please give them unique ports!' )
            
        
        with HG.dirty_object_lock:
            
            service_keys_to_access_keys = HG.server_controller.WriteSynchronous( 'services', request.hydrus_account, services )
            
            HG.server_controller.SetServices( services )
            
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'service_keys_to_access_keys' : service_keys_to_access_keys } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedUpdate( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        self._checkBandwidth( request )
        
        # no permissions check as any functional account can get updates
        
        update_hash = request.hydrus_args[ 'update_hash' ]
        
        if not self._service.HasUpdateHash( update_hash ):
            
            raise HydrusExceptions.NotFoundException( 'This update hash does not exist on this service!' )
            
        
        path = ServerFiles.GetFilePath( update_hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_OCTET_STREAM, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        client_to_server_update = request.hydrus_args[ 'client_to_server_update' ]
        
        HG.server_controller.WriteSynchronous( 'update', self._service_key, request.hydrus_account, client_to_server_update )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedImmediateUpdate( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        updates = HG.server_controller.Read( 'immediate_update', self._service_key, request.hydrus_account )
        
        updates = HydrusSerialisable.SerialisableList( updates )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'updates' : updates } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedMetadataUpdate( HydrusResourceRestricted ):
    
    def _threadDoGETJob( self, request ):
        
        # no permissions check as any functional account can get metadata slices
        
        since = request.hydrus_args[ 'since' ]
        
        metadata_slice = self._service.GetMetadataSlice( since )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'metadata_slice' : metadata_slice } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
