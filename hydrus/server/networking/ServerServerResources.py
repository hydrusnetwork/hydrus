import http.cookies
import threading
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTemp
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworkVariableHandling
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.server import ServerFiles
from hydrus.server import ServerGlobals as SG

class HydrusResourceBusyCheck( HydrusServerResources.Resource ):
    
    def render_GET( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.setResponseCode( 200 )
        
        if HG.server_busy.locked():
            
            return b'1'
            
        else:
            
            return b'0'
            
        
    
class HydrusResourceHydrusNetwork( HydrusServerResources.HydrusResource ):
    
    BLOCKED_WHEN_BUSY = True
    
    def _callbackParseGETArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        parsed_request_args = HydrusNetworkVariableHandling.ParseHydrusNetworkGETArgs( request.args )
        
        request.parsed_request_args = parsed_request_args
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.content.seek( 0 )
        
        if not request.requestHeaders.hasHeader( 'Content-Type' ):
            
            parsed_request_args = HydrusNetworkVariableHandling.ParsedRequestArguments()
            
        else:
            
            content_types = request.requestHeaders.getRawHeaders( 'Content-Type' )
            
            content_type = content_types[0]
            
            try:
                
                mime = HC.mime_enum_lookup[ content_type ]
                
            except Exception as e:
                
                raise HydrusExceptions.BadRequestException( 'Did not recognise Content-Type header!' )
                
            
            total_bytes_read = 0
            
            if mime == HC.APPLICATION_JSON:
                
                json_string = request.content.read()
                
                total_bytes_read += len( json_string )
                
                parsed_request_args = HydrusNetworkVariableHandling.ParseNetworkBytesToParsedHydrusArgs( json_string )
                
            else:
                
                ( os_file_handle, temp_path ) = HydrusTemp.GetTempPath()
                
                request.temp_file_info = ( os_file_handle, temp_path )
                
                with open( temp_path, 'wb' ) as f:
                    
                    for block in HydrusPaths.ReadFileLikeAsBlocks( request.content ): 
                        
                        f.write( block )
                        
                        total_bytes_read += len( block )
                        
                    
                
                decompression_bombs_ok = self._DecompressionBombsOK( request )
                
                parsed_request_args = HydrusNetworkVariableHandling.ParseFileArguments( temp_path, decompression_bombs_ok )
                
            
            self._reportDataUsed( request, total_bytes_read )
            
        
        request.parsed_request_args = parsed_request_args
        
        return request
        
    
    def _checkService( self, request: HydrusServerRequest.HydrusRequest ):
        
        if self.BLOCKED_WHEN_BUSY and HG.server_busy.locked():
            
            raise HydrusExceptions.ServerBusyException( 'This server is busy, please try again later.' )
            
        
        return request
        
    
class HydrusResourceAccessKey( HydrusResourceHydrusNetwork ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        registration_key = request.parsed_request_args[ 'registration_key' ]
        
        access_key = SG.server_controller.Read( 'access_key', self._service_key, registration_key )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'access_key' : access_key } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceAccessKeyVerification( HydrusResourceHydrusNetwork ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        access_key = self._parseHydrusNetworkAccessKey( request )
        
        verified = SG.server_controller.Read( 'verify_access_key', self._service_key, access_key )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'verified' : verified } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceAutoCreateAccountTypes( HydrusResourceHydrusNetwork ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        account_types = SG.server_controller.Read( 'auto_create_account_types', self._service_key )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'account_types' : account_types } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAutoCreateRegistrationKey( HydrusResourceHydrusNetwork ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        account_type_key = request.parsed_request_args[ 'account_type_key' ]
        
        registration_key = SG.server_controller.Read( 'auto_create_registration_key', self._service_key, account_type_key )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'registration_key' : registration_key } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceShutdown( HydrusResourceHydrusNetwork ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        SG.server_controller.ShutdownFromServer()
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceSessionKey( HydrusResourceHydrusNetwork ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        access_key = self._parseHydrusNetworkAccessKey( request )
        
        ( session_key, expires ) = SG.server_controller.server_session_manager.AddSession( self._service_key, access_key )
        
        now = HydrusTime.GetNow()
        
        max_age = expires - now
        
        cookies = [ ( 'session_key', session_key.hex(), { 'max_age' : str( max_age ), 'path' : '/' } ) ]
        
        response_context = HydrusServerResources.ResponseContext( 200, cookies = cookies )
        
        return response_context
        
    
class HydrusResourceRestricted( HydrusResourceHydrusNetwork ):
    
    def _callbackCheckAccountRestrictions( self, request: HydrusServerRequest.HydrusRequest ):
        
        HydrusResourceHydrusNetwork._callbackCheckAccountRestrictions( self, request )
        
        self._checkAccount( request )
        
        self._checkAccountPermissions( request )
        
        return request
        
    
    def _callbackEstablishAccountFromHeader( self, request: HydrusServerRequest.HydrusRequest ):
        
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
                    
                
            except Exception as e:
                
                raise HydrusExceptions.BadRequestException( 'Problem parsing cookies for Session Cookie!' )
                
            
        
        if session_key is None:
            
            access_key = self._parseHydrusNetworkAccessKey( request, key_required = False )
            
            if access_key is None:
                
                raise HydrusExceptions.MissingCredentialsException( 'No credentials found in request!' )
                
            else:
                
                account = SG.server_controller.server_session_manager.GetAccountFromAccessKey( self._service_key, access_key )
                
            
        else:
            
            account = SG.server_controller.server_session_manager.GetAccount( self._service_key, session_key )
            
        
        request.hydrus_account = account
        
        return request
        
    
    def _checkAccount( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckFunctional()
        
        return request
        
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        raise NotImplementedError()
        
    
    def _checkBandwidth( self, request: HydrusServerRequest.HydrusRequest ):
        
        if not self._service.BandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This service has run out of bandwidth. Please try again later.' )
            
        
        if not SG.server_controller.ServerBandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This server has run out of bandwidth. Please try again later.' )
            
        
    
    def _reportDataUsed( self, request, num_bytes ):
        
        HydrusResourceHydrusNetwork._reportDataUsed( self, request, num_bytes )
        
        account = request.hydrus_account
        
        if account is not None:
            
            account.ReportDataUsed( num_bytes )
            
        
    
    def _reportRequestUsed( self, request: HydrusServerRequest.HydrusRequest ):
        
        HydrusResourceHydrusNetwork._reportRequestUsed( self, request )
        
        account = request.hydrus_account
        
        if account is not None:
            
            account.ReportRequestUsed()
            
        
    
class HydrusResourceRestrictedAccount( HydrusResourceRestricted ):
    
    def _checkAccount( self, request: HydrusServerRequest.HydrusRequest ):
        
        # you can always fetch your account (e.g. to be notified that you are banned!)
        
        return request
        
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        # you can always fetch your account
        
        pass
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        account = request.hydrus_account
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'account' : account } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedOptions( HydrusResourceRestricted ):
    
    def _checkAccount( self, request: HydrusServerRequest.HydrusRequest ):
        
        # you can always fetch the options
        
        return request
        
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        # you can always fetch the options
        
        pass
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        # originally I feched and dumped the serialisabledict here straight from the service
        # buuuut, of course if I update the tag filter object version, we can't just spit that out to the network and expect old clients to be ok
        # so now this is just 'get the primitives' request, and it comes back as a straight up JSON dict
        # anything serialisable can be its own request and can have separate deserialisation error handling
        
        if self._service.GetServiceType() in HC.REPOSITORIES:
            
            service_options = {
                'update_period' : self._service.GetUpdatePeriod(),
                'nullification_period' : self._service.GetNullificationPeriod()
            }
            
        else:
            
            service_options = {}
            
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'service_options' : service_options } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    

class HydrusResourceRestrictedOptionsModify( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_OPTIONS, HC.PERMISSION_ACTION_MODERATE )
        
    

class HydrusResourceRestrictedOptionsModifyNullificationPeriod( HydrusResourceRestrictedOptionsModify ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        nullification_period = request.parsed_request_args[ 'nullification_period' ]
        
        if nullification_period < HydrusNetwork.MIN_NULLIFICATION_PERIOD:
            
            raise HydrusExceptions.BadRequestException( 'The anonymisation period was too low. It needs to be at least {}.'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( HydrusNetwork.MIN_NULLIFICATION_PERIOD ) ) )
            
        
        if nullification_period > HydrusNetwork.MAX_NULLIFICATION_PERIOD:
            
            raise HydrusExceptions.BadRequestException( 'The anonymisation period was too high. It needs to be lower than {}.'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( HydrusNetwork.MAX_NULLIFICATION_PERIOD ) ) )
            
        
        old_nullification_period = self._service.GetNullificationPeriod()
        
        if old_nullification_period != nullification_period:
            
            self._service.SetNullificationPeriod( nullification_period )
            
            HydrusData.Print(
                'Account {} changed the anonymisation period from "{}" to "{}".'.format(
                    request.hydrus_account.GetAccountKey().hex(),
                    HydrusTime.TimeDeltaToPrettyTimeDelta( old_nullification_period ),
                    HydrusTime.TimeDeltaToPrettyTimeDelta( nullification_period )
                )
            )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceRestrictedOptionsModifyUpdatePeriod( HydrusResourceRestrictedOptionsModify ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        update_period = request.parsed_request_args[ 'update_period' ]
        
        if update_period < HydrusNetwork.MIN_UPDATE_PERIOD:
            
            raise HydrusExceptions.BadRequestException( 'The update period was too low. It needs to be at least {}.'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( HydrusNetwork.MIN_UPDATE_PERIOD ) ) )
            
        
        if update_period > HydrusNetwork.MAX_UPDATE_PERIOD:
            
            raise HydrusExceptions.BadRequestException( 'The update period was too high. It needs to be lower than {}.'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( HydrusNetwork.MAX_UPDATE_PERIOD ) ) )
            
        
        old_update_period = self._service.GetUpdatePeriod()
        
        if old_update_period != update_period:
            
            self._service.SetUpdatePeriod( update_period )
            
            HydrusData.Print(
                'Account {} changed the update period from "{}" to "{}".'.format(
                    request.hydrus_account.GetAccountKey().hex(),
                    HydrusTime.TimeDeltaToPrettyTimeDelta( old_update_period ),
                    HydrusTime.TimeDeltaToPrettyTimeDelta( update_period )
                )
            )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceRestrictedAccountModify( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE )
        
    
class HydrusResourceRestrictedAccountInfo( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        subject_account_key = request.parsed_request_args[ 'subject_account_key' ]
        
        subject_account = SG.server_controller.Read( 'account', self._service_key, subject_account_key )
        
        account_info = SG.server_controller.Read( 'account_info', self._service_key, request.hydrus_account, subject_account )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'account_info' : account_info } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountKeyFromContent( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        subject_content = request.parsed_request_args[ 'subject_content' ]
        
        subject_account_key = SG.server_controller.Read( 'account_key_from_content', self._service_key, subject_content )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'subject_account_key' : subject_account_key } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountModifyAccountType( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        subject_account_key = request.parsed_request_args[ 'subject_account_key' ]
        
        if 'account_type_key' not in request.parsed_request_args:
            
            raise HydrusExceptions.BadRequestException( 'I was expecting an account type key, but did not get one!' )
            
        
        account_type_key = request.parsed_request_args[ 'account_type_key' ]
        
        SG.server_controller.WriteSynchronous( 'modify_account_account_type', self._service_key, request.hydrus_account, subject_account_key, account_type_key )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountModifyBan( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        subject_account_key = request.parsed_request_args[ 'subject_account_key' ]
        
        if 'reason' not in request.parsed_request_args:
            
            raise HydrusExceptions.BadRequestException( 'I was expecting a reason for the ban, but did not get one!' )
            
        
        if 'expires' not in request.parsed_request_args:
            
            raise HydrusExceptions.BadRequestException( 'I was expecting a new expiration timestamp, but did not get one!' )
            
        
        reason = request.parsed_request_args[ 'reason' ]
        
        if not isinstance( reason, str ):
            
            raise HydrusExceptions.BadRequestException( 'The given ban reason was not a string!' )
            
        
        expires = request.parsed_request_args[ 'expires' ]
        
        expires_is_none = expires is None
        expires_is_positive_integer = isinstance( expires, int ) and expires > 0
        
        expires_is_valid = expires_is_none or expires_is_positive_integer
        
        if not expires_is_valid:
            
            raise HydrusExceptions.BadRequestException( 'The given expiration timestamp was not null or an integer!' )
            
        
        SG.server_controller.WriteSynchronous( 'modify_account_ban', self._service_key, request.hydrus_account, subject_account_key, reason, expires )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceRestrictedAccountModifyDeleteAllContent( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        subject_account_key = request.parsed_request_args[ 'subject_account_key' ]
        
        everything_was_deleted = SG.server_controller.WriteSynchronous( 'modify_account_delete_all_content', self._service_key, request.hydrus_account, subject_account_key )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'everything_was_deleted' : everything_was_deleted } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountModifyExpires( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if 'subject_account_key' in request.parsed_request_args:
            
            subject_account_key = request.parsed_request_args[ 'subject_account_key' ]
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'I was expecting an account id, but did not get one!' )
            
        
        if 'expires' not in request.parsed_request_args:
            
            raise HydrusExceptions.BadRequestException( 'I was expecting a new expiration timestamp, but did not get one!' )
            
        
        expires = request.parsed_request_args[ 'expires' ]
        
        expires_is_none = expires is None
        expires_is_positive_integer = isinstance( expires, int ) and expires > 0
        
        expires_is_valid = expires_is_none or expires_is_positive_integer
        
        if not expires_is_valid:
            
            raise HydrusExceptions.BadRequestException( 'The given expiration timestamp was not None or an integer!' )
            
        
        SG.server_controller.WriteSynchronous( 'modify_account_expires', self._service_key, request.hydrus_account, subject_account_key, expires )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountModifySetMessage( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if 'subject_account_key' in request.parsed_request_args:
            
            subject_account_key = request.parsed_request_args[ 'subject_account_key' ]
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'I was expecting an account id, but did not get one!' )
            
        
        if 'message' not in request.parsed_request_args:
            
            raise HydrusExceptions.BadRequestException( 'I was expecting a new message, but did not get one!' )
            
        
        message = request.parsed_request_args[ 'message' ]
        
        if not isinstance( message, str ):
            
            raise HydrusExceptions.BadRequestException( 'The given message was not a string!' )
            
        
        SG.server_controller.WriteSynchronous( 'modify_account_set_message', self._service_key, request.hydrus_account, subject_account_key, message )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountModifyUnban( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if 'subject_account_key' in request.parsed_request_args:
            
            subject_account_key = request.parsed_request_args[ 'subject_account_key' ]
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'I was expecting an account id, but did not get one!' )
            
        
        SG.server_controller.WriteSynchronous( 'modify_account_unban', self._service_key, request.hydrus_account, subject_account_key )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountOtherAccount( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        subject_account_key = None
        
        if 'subject_identifier' in request.parsed_request_args:
            
            subject_identifier = request.parsed_request_args[ 'subject_identifier' ]
            
            if subject_identifier.HasAccountKey():
                
                subject_account_key = subject_identifier.GetAccountKey()
                
            elif subject_identifier.HasContent():
                
                subject_content = subject_identifier.GetContent()
                
                subject_account_key = SG.server_controller.Read( 'account_key_from_content', self._service_key, subject_content )
                
            else:
                
                raise HydrusExceptions.BadRequestException( 'The subject\'s account identifier did not include an account id or content!' )
                
            
        
        if 'subject_account_key' in request.parsed_request_args:
            
            subject_account_key = request.parsed_request_args[ 'subject_account_key' ]
            
        
        if subject_account_key is None:
            
            raise HydrusExceptions.BadRequestException( 'I was expecting an account id, but did not get one!' )
            
        
        try:
            
            subject_account = SG.server_controller.Read( 'account', self._service_key, subject_account_key )
            
        except HydrusExceptions.InsufficientCredentialsException as e:
            
            raise HydrusExceptions.NotFoundException( e )
            
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'account' : subject_account } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedIP( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hash = request.parsed_request_args[ 'hash' ]
        
        ( ip, timestamp ) = SG.server_controller.Read( 'ip', self._service_key, request.hydrus_account, hash )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'ip' : ip, 'timestamp' : timestamp } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAllAccounts( HydrusResourceRestrictedAccountModify ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        accounts = SG.server_controller.Read( 'all_accounts', self._service_key, request.hydrus_account )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'accounts' : accounts } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedAccountTypes( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        if request.IsGET():
            
            request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
            
        elif request.IsPOST():
            
            request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNT_TYPES, HC.PERMISSION_ACTION_MODERATE )
            
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        account_types = SG.server_controller.Read( 'account_types', self._service_key, request.hydrus_account )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'account_types' : account_types } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        account_types = request.parsed_request_args[ 'account_types' ]
        deletee_account_type_keys_to_new_account_type_keys = request.parsed_request_args[ 'deletee_account_type_keys_to_new_account_type_keys' ]
        
        SG.server_controller.WriteSynchronous( 'account_types', self._service_key, request.hydrus_account, account_types, deletee_account_type_keys_to_new_account_type_keys )
        
        SG.server_controller.server_session_manager.RefreshAccounts( self._service_key )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedBackup( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        SG.server_controller.Write( 'backup' )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedLockOn( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        locked = HG.server_busy.acquire( False ) # pylint: disable=E1111
        
        if not locked:
            
            raise HydrusExceptions.BadRequestException( 'The server was already locked!' )
            
        
        SG.server_controller.db.PauseAndDisconnect( True )
        
        TIME_BLOCK = 0.25
        
        for i in range( int( 5 / TIME_BLOCK ) ):
            
            if not SG.server_controller.db.IsConnected():
                
                break
                
            
            time.sleep( TIME_BLOCK )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedLockOff( HydrusResourceRestricted ):
    
    BLOCKED_WHEN_BUSY = False
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        try:
            
            HG.server_busy.release()
            
        except threading.ThreadError:
            
            raise HydrusExceptions.BadRequestException( 'The server is not busy!' )
            
        
        SG.server_controller.db.PauseAndDisconnect( False )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedMaintenanceRegenServiceInfo( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_OPTIONS, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        SG.server_controller.WriteSynchronous( 'maintenance_regen_service_info', self._service_key )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedNumPetitions( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        # further permissions checked in the db
        
        request.hydrus_account.CheckAtLeastOnePermission( [ ( content_type, HC.PERMISSION_ACTION_MODERATE ) for content_type in HC.SERVICE_TYPES_TO_CONTENT_TYPES[ self._service.GetServiceType() ] ] )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        subject_account_key = request.parsed_request_args.GetValueOrNone( 'subject_account_key', bytes )
        
        petition_count_info = SG.server_controller.Read( 'num_petitions', self._service_key, request.hydrus_account, subject_account_key = subject_account_key )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'num_petitions' : petition_count_info } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    

class HydrusResourceRestrictedPetition( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        content_type = request.parsed_request_args[ 'content_type' ]
        
        request.hydrus_account.CheckPermission( content_type, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        content_type = request.parsed_request_args[ 'content_type' ]
        status = request.parsed_request_args[ 'status' ]
        subject_account_key = request.parsed_request_args.GetValueOrNone( 'subject_account_key', bytes )
        reason = request.parsed_request_args.GetValueOrNone( 'reason', str )
        
        if subject_account_key is None or reason is None:
            
            petitions_summary = SG.server_controller.Read( 'petitions_summary', self._service_key, request.hydrus_account, content_type, status, limit = 1, subject_account_key = subject_account_key )
            
            if len( petitions_summary ) == 0:
                
                if subject_account_key is None and reason is None:
                    
                    raise HydrusExceptions.NotFoundException( f'Sorry, no petitions were found!' )
                    
                elif subject_account_key is None:
                    
                    raise HydrusExceptions.NotFoundException( f'Sorry, no petitions were found for the given reason {reason}!' )
                    
                else:
                    
                    raise HydrusExceptions.NotFoundException( 'Sorry, no petitions were found for the given account_key {}!'.format( subject_account_key.hex() ) )
                    
                
            
            petition_header = petitions_summary[0]
            
            subject_account_key = petition_header.account_key
            reason = petition_header.reason
            
        
        petition = SG.server_controller.Read( 'petition', self._service_key, request.hydrus_account, content_type, status, subject_account_key, reason )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'petition' : petition } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    

class HydrusResourceRestrictedPetitionsSummary( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        content_type = request.parsed_request_args[ 'content_type' ]
        
        request.hydrus_account.CheckPermission( content_type, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        content_type = request.parsed_request_args.GetValue( 'content_type', int )
        status = request.parsed_request_args.GetValue( 'status', int )
        num = request.parsed_request_args.GetValue( 'num', int )
        
        subject_account_key = request.parsed_request_args.GetValueOrNone( 'subject_account_key', bytes )
        reason = request.parsed_request_args.GetValueOrNone( 'reason', str )
        
        petitions_summary = SG.server_controller.Read( 'petitions_summary', self._service_key, request.hydrus_account, content_type, status, num, subject_account_key = subject_account_key, reason = reason )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'petitions_summary' : petitions_summary } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    

class HydrusResourceRestrictedRegistrationKeys( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        num = request.parsed_request_args[ 'num' ]
        account_type_key = request.parsed_request_args[ 'account_type_key' ]
        
        if 'expires' in request.parsed_request_args:
            
            expires = request.parsed_request_args[ 'expires' ]
            
        else:
            
            expires = None
            
        
        registration_keys = SG.server_controller.Read( 'registration_keys', self._service_key, request.hydrus_account, num, account_type_key, expires )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'registration_keys' : registration_keys } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedRepositoryFile( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        # everyone with a functional account can read files
        
        if request.IsPOST():
            
            request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_FILES, HC.PERMISSION_ACTION_CREATE )
            
        
    
    def _DecompressionBombsOK( self, request: HydrusServerRequest.HydrusRequest ):
        
        if request.hydrus_account is None:
            
            return False
            
        else:
            
            return request.hydrus_account.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_CREATE )
            
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._checkBandwidth( request )
        
        # no permission check as any functional account can get files
        
        hash = request.parsed_request_args[ 'hash' ]
        
        ( valid, mime ) = SG.server_controller.Read( 'service_has_file', self._service_key, hash )
        
        if not valid:
            
            raise HydrusExceptions.NotFoundException( 'File not found on this service!' )
            
        
        path = ServerFiles.GetFilePath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = mime, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        file_dict = request.parsed_request_args
        
        if self._service.LogUploaderIPs():
            
            file_dict[ 'ip' ] = request.getClientIP()
            
        
        timestamp = self._service.GetMetadata().GetNextUpdateBegin() + 1
        
        SG.server_controller.WriteSynchronous( 'file', self._service, request.hydrus_account, file_dict, timestamp )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceRestrictedRepositoryThumbnail( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        # everyone with a functional account can read thumbs
        
        pass
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._checkBandwidth( request )
        
        # no permission check as any functional account can get thumbnails
        
        hash = request.parsed_request_args[ 'hash' ]
        
        ( valid, mime ) = SG.server_controller.Read( 'service_has_file', self._service_key, hash )
        
        if not valid:
            
            raise HydrusExceptions.NotFoundException( 'Thumbnail not found on this service!' )
            
        
        if mime not in HC.MIMES_WITH_THUMBNAILS:
            
            raise HydrusExceptions.NotFoundException( 'That mime should not have a thumbnail!' )
            
        
        path = ServerFiles.GetThumbnailPath( hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_OCTET_STREAM, path = path )
        
        return response_context
        
    
class HydrusResourceRestrictedServiceInfo( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        # you can always fetch the service info
        
        pass
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        service_info = SG.server_controller.Read( 'service_info', self._service_key )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'service_info' : list( service_info.items() ) } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
class HydrusResourceRestrictedServices( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        services = SG.server_controller.Read( 'services_from_account', request.hydrus_account )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'services' : services } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        services = request.parsed_request_args[ 'services' ]
        
        unique_ports = { service.GetPort() for service in services }
        
        if len( unique_ports ) < len( services ):
            
            raise HydrusExceptions.BadRequestException( 'It looks like some of those services share ports! Please give them unique ports!' )
            
        
        with HG.dirty_object_lock:
            
            SG.server_controller.SetServices( services )
            
            service_keys_to_access_keys = SG.server_controller.WriteSynchronous( 'services', request.hydrus_account, services )
            
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'service_keys_to_access_keys' : service_keys_to_access_keys } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    

class HydrusResourceRestrictedTagFilter( HydrusResourceRestricted ):
    
    def _checkAccount( self, request: HydrusServerRequest.HydrusRequest ):
        
        if request.IsPOST():
            
            return HydrusResourceRestricted._checkAccount( self, request )
            
        else:
            
            # you can always fetch the tag filter
            
            return request
            
        
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        if request.IsPOST():
            
            request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_OPTIONS, HC.PERMISSION_ACTION_MODERATE )
            
        else:
            
            # you can always fetch the tag filter
            
            pass
            
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        tag_filter = self._service.GetTagFilter()
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'tag_filter' : tag_filter } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        tag_filter = request.parsed_request_args[ 'tag_filter' ]
        
        old_tag_filter = self._service.GetTagFilter()
        
        if old_tag_filter != tag_filter:
            
            self._service.SetTagFilter( tag_filter )
            
            summary_text = tag_filter.GetChangesSummaryText( old_tag_filter )
            
            HydrusData.Print(
                'Account {} changed the tag filter. Rule changes are:{}{}.'.format(
                    request.hydrus_account.GetAccountKey().hex(),
                    '\n',
                    summary_text
                )
            )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceRestrictedUpdate( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        # everyone with a functional account can read updates
        
        if request.IsPOST():
            
            # further permissions checked in the db
            
            request.hydrus_account.CheckAtLeastOnePermission( [ ( content_type, HC.PERMISSION_ACTION_PETITION ) for content_type in HC.SERVICE_TYPES_TO_CONTENT_TYPES[ self._service.GetServiceType() ] ] )
            
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        self._checkBandwidth( request )
        
        # no permissions check as any functional account can get updates
        
        update_hash = request.parsed_request_args[ 'update_hash' ]
        
        if not self._service.HasUpdateHash( update_hash ):
            
            raise HydrusExceptions.NotFoundException( 'This update hash does not exist on this service!' )
            
        
        path = ServerFiles.GetFilePath( update_hash )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.APPLICATION_OCTET_STREAM, path = path )
        
        return response_context
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        client_to_server_update = request.parsed_request_args[ 'client_to_server_update' ]
        
        if isinstance( self._service, HydrusNetwork.ServerServiceRepositoryTag ):
            
            client_to_server_update.ApplyTagFilterToPendingMappings( self._service.GetTagFilter() )
            
        
        timestamp = self._service.GetMetadata().GetNextUpdateBegin() + 1
        
        SG.server_controller.WriteSynchronous( 'update', self._service_key, request.hydrus_account, client_to_server_update, timestamp )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceRestrictedImmediateUpdate( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckAtLeastOnePermission( [ ( content_type, HC.PERMISSION_ACTION_MODERATE ) for content_type in HC.SERVICE_TYPES_TO_CONTENT_TYPES[ self._service.GetServiceType() ] ] )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        updates = SG.server_controller.Read( 'immediate_update', self._service_key, request.hydrus_account )
        
        updates = HydrusSerialisable.SerialisableList( updates )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'updates' : updates } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    

class HydrusResourceRestrictedMetadataUpdate( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        pass # everyone with a functional account can get metadata slices
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        since = request.parsed_request_args[ 'since' ]
        
        metadata_slice = self._service.GetMetadataSlice( since )
        
        body = HydrusNetworkVariableHandling.DumpHydrusArgsToNetworkBytes( { 'metadata_slice' : metadata_slice } )
        
        response_context = HydrusServerResources.ResponseContext( 200, body = body )
        
        return response_context
        
    

class HydrusResourceRestrictedRestartServices( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        SG.server_controller.CallLater( 1.0, SG.server_controller.RestartServices )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceRestrictedVacuum( HydrusResourceRestricted ):
    
    def _checkAccountPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.hydrus_account.CheckPermission( HC.CONTENT_TYPE_SERVICES, HC.PERMISSION_ACTION_MODERATE )
        
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        SG.server_controller.Write( 'vacuum' )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
