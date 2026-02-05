from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientGlobals as CG
from hydrus.client.networking.api import ClientLocalServerCore

class HydrusResourceClientAPI( HydrusServerResources.HydrusResource ):
    
    BLOCKED_WHEN_BUSY = True
    
    def _callbackParseGETArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        parsed_request_args = ClientLocalServerCore.ParseClientAPIGETArgs( request.args )
        
        request.parsed_request_args = parsed_request_args
        
        requested_response_mime = ClientLocalServerCore.ParseRequestedResponseMime( request )
        
        if requested_response_mime == HC.APPLICATION_CBOR and not ClientLocalServerCore.CBOR_AVAILABLE:
            
            raise HydrusExceptions.NotAcceptable( 'Sorry, this service does not support CBOR!' )
            
        
        request.preferred_mime = requested_response_mime
        
        return request
        
    
    def _callbackParsePOSTArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        ( parsed_request_args, total_bytes_read ) = ClientLocalServerCore.ParseClientAPIPOSTArgs( request )
        
        self._reportDataUsed( request, total_bytes_read )
        
        request.parsed_request_args = parsed_request_args
        
        requested_response_mime = ClientLocalServerCore.ParseRequestedResponseMime( request )
        
        if requested_response_mime == HC.APPLICATION_CBOR and not ClientLocalServerCore.CBOR_AVAILABLE:
            
            raise HydrusExceptions.NotAcceptable( 'Sorry, this service does not support CBOR!' )
            
        
        request.preferred_mime = requested_response_mime
        
        return request
        
    
    def _reportDataUsed( self, request, num_bytes ):
        
        self._service.ReportDataUsed( num_bytes )
        
    
    def _reportRequestStarted( self, request: HydrusServerRequest.HydrusRequest ):
        
        HydrusServerResources.HydrusResource._reportRequestStarted( self, request )
        
        CG.client_controller.ResetIdleTimerFromClientAPI()
        
    
    def _checkService( self, request: HydrusServerRequest.HydrusRequest ):
        
        HydrusServerResources.HydrusResource._checkService( self, request )
        
        if self.BLOCKED_WHEN_BUSY and HG.client_busy.locked():
            
            raise HydrusExceptions.ServerBusyException( 'This server is busy, please try again later.' )
            
        
        if not self._service.BandwidthOK():
            
            raise HydrusExceptions.BandwidthException( 'This service has run out of bandwidth. Please try again later.' )
            
        
    

class HydrusResourceClientAPIRestricted( HydrusResourceClientAPI ):
    
    def _callbackCheckAccountRestrictions( self, request: HydrusServerRequest.HydrusRequest ):
        
        HydrusResourceClientAPI._callbackCheckAccountRestrictions( self, request )
        
        self._CheckAPIPermissions( request )
        
        return request
        
    
    def _callbackEstablishAccountFromHeader( self, request: HydrusServerRequest.HydrusRequest ):
        
        access_key = self._ParseClientAPIAccessKey( request, 'header' )
        
        if access_key is not None:
            
            self._EstablishAPIPermissions( request, access_key )
            
        
        return request
        
    
    def _callbackEstablishAccountFromArgs( self, request: HydrusServerRequest.HydrusRequest ):
        
        if request.client_api_permissions is None:
            
            access_key = self._ParseClientAPIAccessKey( request, 'args' )
            
            if access_key is not None:
                
                self._EstablishAPIPermissions( request, access_key )
                
            
        
        if request.client_api_permissions is None:
            
            raise HydrusExceptions.MissingCredentialsException( 'No access key or session key provided!' )
            
        
        return request
        
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        raise NotImplementedError()
        
    
    def _EstablishAPIPermissions( self, request, access_key ):
        
        try:
            
            api_permissions = CG.client_controller.client_api_manager.GetPermissions( access_key )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.InsufficientCredentialsException( str( e ) )
            
        
        request.client_api_permissions = api_permissions
        
    
    def _ParseClientAPIKey( self, request, source, name_of_key ):
        
        key = None
        
        if source == 'header':
            
            if request.requestHeaders.hasHeader( name_of_key ):
                
                key_texts = request.requestHeaders.getRawHeaders( name_of_key )
                
                key_text = key_texts[0]
                
                try:
                    
                    key = bytes.fromhex( key_text )
                    
                except Exception as e:
                    
                    raise HydrusExceptions.BadRequestException( 'Problem parsing {}!'.format( name_of_key ) )
                    
                
            
        elif source == 'args':
            
            if name_of_key in request.parsed_request_args:
                
                key = request.parsed_request_args.GetValue( name_of_key, bytes )
                
            
        
        return key
        
    
    def _ParseClientAPIAccessKey( self, request, source ):
        
        access_key = self._ParseClientAPIKey( request, source, 'Hydrus-Client-API-Access-Key' )
        
        if access_key is None:
            
            session_key = self._ParseClientAPIKey( request, source, 'Hydrus-Client-API-Session-Key' )
            
            if session_key is None:
                
                return None
                
            
            try:
                
                access_key = CG.client_controller.client_api_manager.GetAccessKey( session_key )
                
            except HydrusExceptions.DataMissing as e:
                
                raise HydrusExceptions.SessionException( str( e ) )
                
            
        
        return access_key
        
    
