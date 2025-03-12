from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientTime
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources

class HydrusResourceClientAPIRestrictedEditTimes( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_EDIT_TIMES )
        
    

class HydrusResourceClientAPIRestrictedEditTimesSetTime( HydrusResourceClientAPIRestrictedEditTimes ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        hashes = ClientLocalServerCore.ParseHashes( request )
        
        if len( hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any hashes to apply the times to!' )
            
        
        media_results = CG.client_controller.Read( 'media_results', hashes )
        
        if 'timestamp' in request.parsed_request_args:
            
            timestamp = request.parsed_request_args.GetValueOrNone( 'timestamp', float )
            
            timestamp_ms = HydrusTime.MillisecondiseS( timestamp )
            
        elif 'timestamp_ms' in request.parsed_request_args:
            
            timestamp_ms = request.parsed_request_args.GetValueOrNone( 'timestamp_ms', int )
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, you have to specify a timestamp, even if you want to send "null"!' )
            
        
        location = None
        
        timestamp_type = request.parsed_request_args.GetValue( 'timestamp_type', int )
        
        if timestamp_type is None:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, you have to specify the timestamp type!' )
            
        
        if timestamp_type == HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            domain = request.parsed_request_args.GetValue( 'domain', str )
            
            if domain == 'local':
                
                timestamp_type = HC.TIMESTAMP_TYPE_MODIFIED_FILE
                
            else:
                
                location = domain
                
            
        elif timestamp_type == HC.TIMESTAMP_TYPE_LAST_VIEWED:
            
            canvas_type = request.parsed_request_args.GetValueOrNone( 'canvas_type', int )
            
            if canvas_type is None:
                
                canvas_type = CC.CANVAS_MEDIA_VIEWER
                
            
            if canvas_type not in ( CC.CANVAS_MEDIA_VIEWER, CC.CANVAS_PREVIEW, CC.CANVAS_CLIENT_API ):
                
                raise HydrusExceptions.BadRequestException( 'Sorry, the canvas type needs to be either 0, 1, or 4!' )
                
            
            location = canvas_type
            
        elif timestamp_type in ( HC.TIMESTAMP_TYPE_IMPORTED, HC.TIMESTAMP_TYPE_DELETED, HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED ):
            
            file_service_key = request.parsed_request_args.GetValue( 'file_service_key', bytes )
            
            if not CG.client_controller.services_manager.ServiceExists( file_service_key ):
                
                raise HydrusExceptions.BadRequestException( 'Sorry, do not know that service!' )
                
            
            if CG.client_controller.services_manager.GetServiceType( file_service_key ) not in HC.REAL_FILE_SERVICES:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, you have to specify a file service service key!' )
                
            
            location = file_service_key
            
        elif timestamp_type in ( HC.TIMESTAMP_TYPE_MODIFIED_FILE, HC.TIMESTAMP_TYPE_ARCHIVED ):
            
            pass # simple; no additional location data
            
        else:
            
            raise HydrusExceptions.BadRequestException( f'Sorry, do not understand that timestamp type "{timestamp_type}"!' )
            
        
        if timestamp_type != HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN:
            
            if timestamp_ms is None:
                
                raise HydrusExceptions.BadRequestException( f'Sorry, you can only delete web domain timestamps (type 0) for now! You sent ({timestamp_type})!' )
                
            else:
                
                timestamp_data_stub = ClientTime.TimestampData( timestamp_type = timestamp_type, location = location )
                
                for media_result in media_results:
                    
                    result = media_result.GetTimesManager().GetTimestampMSFromStub( timestamp_data_stub )
                    
                    if result is None:
                        
                        raise HydrusExceptions.BadRequestException( f'Sorry, if the timestamp type is other than 0 (web domain), then you cannot add new timestamps, only edit existing ones. I did not see the given timestamp type ({timestamp_data_stub.ToString()}) on one of the files you sent, specifically: {media_result.GetHash().hex()}' )
                        
                    
                
            
        
        timestamp_data = ClientTime.TimestampData( timestamp_type = timestamp_type, location = location, timestamp_ms = timestamp_ms )
        
        if timestamp_ms is None:
            
            action = HC.CONTENT_UPDATE_DELETE
            
        else:
            
            action = HC.CONTENT_UPDATE_SET
            
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, action, ( hashes, timestamp_data ) ) ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_updates )
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
