import http.cookies
import threading

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNetwork
from hydrus.core import HydrusNetworking
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusServerResources

from hydrus.server import ServerFiles

class HydrusResourceBusyCheck( HydrusServerResources.Resource ):
    
    def __init__( self ):
        
        HydrusServerResources.Resource.__init__( self )
        
        self._server_version_string = HC.service_string_lookup[ HC.SERVER_ADMIN ] + '/' + str( HC.NETWORK_VERSION )
        
    
    def render_GET( self, request ):
        
        request.setResponseCode( 200 )
        
        request.setHeader( 'Server', self._server_version_string )
        
        if HG.server_busy.locked():
            
            return b'1'
            
        else:
            
            return b'0'
            
        
    
class HydrusResourceHydrusNetwork( HydrusServerResources.HydrusResource ):
    
    BLOCKED_WHEN_BUSY = True
    
    def _callbackParseGETArgs( self, request ):
        
        parsed_request_args = HydrusNetwork.ParseHydrusNetworkGETArgs( request.args )
        
        request.parsed_request_args = parsed_request_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request ):
        
        request.content.seek( 0 )
        
        if not request.requestHeaders.hasHeader( 'Content-Type' ):
            
            parsed_request_args = HydrusNetworking.ParsedRequestArguments()
            
        else:
            
            content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
            
            content_type = content_types[0]
            
            try:
                
                mime = HC.mime_enum_lookup[ content_type ]
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'Did not recognise Content-Type header!' )
                
            
            total_bytes_read = 0
            
            if mime == HC.APPLICATION_JSON:
                
                json_string = request.content.read()
                
                total_bytes_read += len( json_string )
                
                parsed_request_args = HydrusNetwork.ParseNetworkBytesToParsedHydrusArgs( json_string )
                
            else:
                
                ( os_file_handle, temp_path ) = HydrusPaths.GetTempPath()
                
                request.temp_file_info = ( os_file_handle, temp_path )
                
                with open( temp_path, 'wb' ) as f:
                    
                    for block in HydrusPaths.ReadFileLikeAsBlocks( request.content ): 
                        
                        f.write( block )
                        
                        total_bytes_read += len( block )
                        
                    
                
                decompression_bombs_ok = self._DecompressionBombsOK( request )
                
                parsed_request_args = HydrusServerResources.ParseFileArguments( temp_path, decompression_bombs_ok )
                
            
            self._reportDataUsed( request, total_bytes_read )
            
        
        request.parsed_request_args = parsed_request_args
        
        return request
        
    
    def _checkService( self, request ):
        
        if self.BLOCKED_WHEN_BUSY and HG.server_busy.locked():
            
            raise HydrusExceptions.ServerBusyException( 'This server is busy, please try again later.' )
            
        
        return request
        
    
class HydrusResourceAccessKey( HydrusResourceHydrusNetwork ):
    
    def _threadDoGETJob( self, request ):
        
        registration_key = request.parsed_request_args[ 'registration_key' ]
        
        access_key = HG.server_controller.Read( 'access_key', self._service_key, registration_key )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'access_key' : access_key } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceShutdown( HydrusResourceHydrusNetwork ):
    
    def _threadDoPOSTJob( self, request ):
        
        HG.server_controller.ShutdownFromServer()
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceAccessKeyVerification( HydrusResourceHydrusNetwork ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseHydrusNetworkAccessKey( request )
        
        verified = HG.server_controller.Read( 'verify_access_key', self._service_key, access_key )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'verified' : verified } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceSessionKey( HydrusResourceHydrusNetwork ):
    
    def _threadDoGETJob( self, request ):
        
        access_key = self._parseHydrusNetworkAccessKey( request )
        
        ( session_key, expires ) = HG.server_controller.server_session_manager.AddSession( self._service_key, access_key )
        
        now = HydrusData.GetNow()
        
        max_age = expires - now
        
        cookies = [ ( 'session_key', session_key.hex(), { 'max_age' : str( max_age ), 'path' : '/' } ) ]
        
        response_context = HydrusServerResources.ResponseContext( 200, cookies = cookies )
        
        return response_context
        
    
class HydrusResourceRestricted( HydrusResourceHydrusNetwork ):
    
    def _callbackCheckAccountRestrictions( self, request ):
        
        HydrusResourceHydrusNetwork._callbackCheckAccountRestrictions( self, request )
        
        self._checkAccount( request )
        
        self._checkAccountPermissions( request )
        
        return request
        
    
    def _callbackEstablishAccountFromHeader( self, request ):
        
        session_key = None
        
        if request.requestHeaders.hasHeader( 'Cookie' ):
            
            cookie_texts = request.requestHeaders.getRawHeaders( 'Cookie' )
            
            cookie_text = cookie_texts[0]
            
            try:
                
                cookies = http.cookies.SimpleCookie( cookie_text )
                
                if 'session_key' in cookies:
                    
                    # Morsel, for real, ha ha ha
                    morsel = cookies[ 'session_key' ]
                    
                    session_key_hex = morsel.value
                    
                    session_key = bytes.fromhex( session_key_hex )
                    
                
            except:
                
                raise HydrusExceptions.BadRequestException( 'Problem parsing cookies for Session Cookie!' )
                
            
        
        if session_key is None:
            
            access_key = self._parseHydrusNetworkAccessKey( request, key_required = False )
            
            if access_key is None:
                
                raise HydrusExceptions.MissingCredentialsException( 'No credentials found in request!' )
                
            else:
                
                account = HG.server_controller.server_session_manager.GetAccountFromAccessKey( self._service_key, access_key )
                
            
        else:
            
            account = HG.server_controller.server_session_manager.GetAccount( self._service_key, session_key )
            
        
        request.hydrus_account = account
        
        return request
        
    
    def _checkAccount( self, request ):
        
        request.hydrus_account.CheckFunctional()
        
        return request
        
    
    def _checkAccountPermissions( self, request ):
        
        raise NotImplementedError()
        
    
    def _checkBandwidth( self, request ):
        
        if not self._service.BandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This service has run out of bandwidth. Please try again later.' )
            
        
        if not HG.server_controller.ServerBandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This server has run out of bandwidth. Please try again later.' )
            
        
    
    def _reportDataUsed( self, request, num_bytes ):
        
        HydrusResourceHydrusNetwork._reportDataUsed( self, request, num_bytes )
        
        account = request.hydrus_account
        
        if account is not None:
            
            account.ReportDataUsed( num_bytes )
            
        
    
    def _reportRequestUsed( self, request ):
        
        HydrusResourceHydrusNetwork._reportRequestUsed( self, request )
        
        account = request.hydrus_account
        
        if account is not None:
            
            account.ReportRequestUsed()
            
        
    
class HydrusResourceRestrictedAccount( HydrusResourceRestricted ):
    
    def _checkAccount( self, request ):
        
        # you can always fetch your account (e.g. to be notified that you are banned!)
        
        return request
        
    
    def _checkAccountPermissions( self, request ):
        
        # you can always fetch your account
        
        pass
        
    
    def _threadDoGETJob( self, request ):
        
        account = request.hydrus_account
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'account' : account } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountInfo( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoGETJob( self, request ):
        
        subject_identifier = request.parsed_request_args[ 'subject_identifier' ]
        
        if subject_identifier.HasAccountKey():
            
            subject_account_key = subject_identifier.GetData()
            
        else:
            
            raise HydrusExceptions.MissingCredentialsException( 'I was expecting an account key, but did not get one!' )
            
        
        subject_account = HG.server_controller.Read( 'account', self._service_key, subject_account_key )
        
        account_info = HG.server_controller.Read( 'account_info', self._service_key, request.hydrus_account, subject_account )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'account_info' : account_info } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountOtherAccount( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoGETJob( self, request ):
        
        subject_identifier = request.parsed_request_args[ 'subject_identifier' ]
        
        other_account = HG.server_controller.Read( 'other_accounts', self._service_key, request.hydrus_account, subject_identifier )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'other_account' : other_account } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        pass
        
    
class HydrusResourceRestrictedAccountTypes( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        if request.IsGET():
            
            request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
            
        elif request.IsPOST():
            
            request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_MODERATE )
            
        
    
    def _threadDoGETJob( self, request ):
        
        account_types = HG.server_controller.Read( 'account_types', self._service_key, request.hydrus_account )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'account_types' : account_types } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        account_types = request.parsed_request_args[ 'account_types' ]
        deletee_account_type_keys_to_new_account_type_keys = request.parsed_request_args[ 'deletee_account_type_keys_to_new_account_type_keys' ]
        
        HG.server_controller.WriteSynchronous( 'account_types', self._service_key, request.hydrus_account, account_types, deletee_account_type_keys_to_new_account_type_keys )
        
        HG.server_controller.server_session_manager.RefreshAccounts( self._service_key )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedBackup( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request ):
        
        HG.server_controller.Write( 'backup' )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedIP( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoGETJob( self, request ):
        
        hash = request.parsed_request_args[ 'hash' ]
        
        ( ip, timestamp ) = HG.server_controller.Read( 'ip', self._service_key, request.hydrus_account, hash )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'ip' : ip, 'timestamp' : timestamp } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedLockOn( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request ):
        
        locked = HG.server_busy.acquire( False ) # pylint: disable=E1111
        
        if not locked:
            
            raise HydrusExceptions.BadRequestException( 'The server was already locked!' )
            
        
        HG.server_controller.db.PauseAndDisconnect( True )
        
        # shut down db, wait until it is done?
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedLockOff( HydrusResourceRestricted ):
    
    BLOCKED_WHEN_BUSY = False
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request ):
        
        try:
            
            HG.server_busy.release()
            
        except threading.ThreadError:
            
            raise HydrusExceptions.BadRequestException( 'The server is not busy!' )
            
        
        HG.server_controller.db.PauseAndDisconnect( False )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedNumPetitions( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        # further permissions checked in the db
        
        request.hydrus_account.CheckAtLeastOnePermission( [ ( content_type, HC.PERMISSION_ACTION_MODERATE ) for content_type in HC.REPOSITORY_CONTENT_TYPES ] )
        
    
    def _threadDoGETJob( self, request ):
        
        petition_count_info = HG.server_controller.Read( 'num_petitions', self._service_key, request.hydrus_account )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'num_petitions' : petition_count_info } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedPetition( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        content_type = request.parsed_request_args[ 'content_type' ]
        
        request.hydrus_account.CheckPermission( content_type, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoGETJob( self, request ):
        
        content_type = request.parsed_request_args[ 'content_type' ]
        status = request.parsed_request_args[ 'status' ]
        
        petition = HG.server_controller.Read( 'petition', self._service_key, request.hydrus_account, content_type, status )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'petition' : petition } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedRegistrationKeys( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
        
    
    def _threadDoGETJob( self, request ):
        
        num = request.parsed_request_args[ 'num' ]
        account_type_key = request.parsed_request_args[ 'account_type_key' ]
        
        if 'expires' in request.parsed_request_args:
            
            expires = request.parsed_request_args[ 'expires' ]
            
        else:
            
            expires = None
            
        
        registration_keys = HG.server_controller.Read( 'registration_keys', self._service_key, request.hydrus_account, num, account_type_key, expires )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'registration_keys' : registration_keys } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedRepositoryFile( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        # everyone with a functional account can read files
        
        if request.IsPOST():
            
            request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_CREATE )
            
        
    
    def _DecompressionBombsOK( self, request ):
        
        if request.hydrus_account is None:
            
            return False
            
        else:
            
            return request.hydrus_account.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
            
        
    
    def _threadDoGETJob( self, request ):
        
        self._checkBandwidth( request )
        
        # no permission check as any functional account can get files
        
        hash = request.parsed_request_args[ 'hash' ]
        
        ( valid, mime ) = HG.server_controller.Read( 'service_has_file', self._service_key, hash )
        
        if not valid:
            
            raise HydrusExceptions.NotFoundException( 'File not found on this service!' )
            
        
        path = ServerFiles.GetFilePath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        file_dict = request.parsed_request_args
        
        if self._service.LogUploaderIPs():
            
            file_dict[ 'ip' ] = request.getClientIP()
            
        
        timestamp = self._service.GetMetadata().GetNextUpdateBegin() + 1
        
        HG.server_controller.WriteSynchronous( 'file', self._service, request.hydrus_account, file_dict, timestamp )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedRepositoryThumbnail( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        # everyone with a functional account can read thumbs
        
        pass
        
    
    def _threadDoGETJob( self, request ):
        
        self._checkBandwidth( request )
        
        # no permission check as any functional account can get thumbnails
        
        hash = request.parsed_request_args[ 'hash' ]
        
        ( valid, mime ) = HG.server_controller.Read( 'service_has_file', self._service_key, hash )
        
        if not valid:
            
            raise HydrusExceptions.NotFoundException( 'Thumbnail not found on this service!' )
            
        
        if mime not in HC.MIMES_WITH_THUMBNAILS:
            
            raise HydrusExceptions.NotFoundException( 'That mime should not have a thumbnail!' )
            
        
        path = ServerFiles.GetThumbnailPath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_OCTET_STREAM, path = path )
        
        return response_context
        
    
class HydrusResourceRestrictedServices( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoGETJob( self, request ):
        
        services = HG.server_controller.Read( 'services_from_account', request.hydrus_account )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'services' : services } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        services = request.parsed_request_args[ 'services' ]
        
        unique_ports = { service.GetPort() for service in services }
        
        if len( unique_ports ) < len( services ):
            
            raise HydrusExceptions.BadRequestException( 'It looks like some of those services share ports! Please give them unique ports!' )
            
        
        with HG.dirty_object_lock:
            
            HG.server_controller.SetServices( services )
            
            service_keys_to_access_keys = HG.server_controller.WriteSynchronous( 'services', request.hydrus_account, services )
            
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'service_keys_to_access_keys' : service_keys_to_access_keys } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedUpdate( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        # everyone with a functional account can read updates
        
        if request.IsPOST():
            
            # further permissions checked in the db
            
            request.hydrus_account.CheckAtLeastOnePermission( [ ( content_type, HC.PERMISSION_ACTION_PETITION ) for content_type in HC.REPOSITORY_CONTENT_TYPES ] )
            
        
    
    def _threadDoGETJob( self, request ):
        
        self._checkBandwidth( request )
        
        # no permissions check as any functional account can get updates
        
        update_hash = request.parsed_request_args[ 'update_hash' ]
        
        if not self._service.HasUpdateHash( update_hash ):
            
            raise HydrusExceptions.NotFoundException( 'This update hash does not exist on this service!' )
            
        
        path = ServerFiles.GetFilePath( update_hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_OCTET_STREAM, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request ):
        
        client_to_server_update = request.parsed_request_args[ 'client_to_server_update' ]
        
        timestamp = self._service.GetMetadata().GetNextUpdateBegin() + 1
        
        HG.server_controller.WriteSynchronous( 'update', self._service_key, request.hydrus_account, client_to_server_update, timestamp )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedImmediateUpdate( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckAtLeastOnePermission( [ ( content_type, HC.PERMISSION_ACTION_MODERATE ) for content_type in HC.REPOSITORY_CONTENT_TYPES ] )
        
    
    def _threadDoGETJob( self, request ):
        
        updates = HG.server_controller.Read( 'immediate_update', self._service_key, request.hydrus_account )
        
        updates = HydrusSerialisable.SerialisableList( updates )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'updates' : updates } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedMetadataUpdate( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        pass # everyone with a functional account can get metadata slices
        
    
    def _threadDoGETJob( self, request ):
        
        since = request.parsed_request_args[ 'since' ]
        
        metadata_slice = self._service.GetMetadataSlice( since )
        
        body = HydrusNetwork.DumpHydrusArgsToNetworkBytes( { 'metadata_slice' : metadata_slice } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedVacuum( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request ):
        
        HG.server_controller.Write( 'vacuum' )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
