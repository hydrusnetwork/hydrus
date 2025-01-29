from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientAPI
from hydrus.client import ClientGlobals as CG
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources


class HydrusResourceClientAPIRestrictedEditFileViewingStatistics( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_EDIT_TIMES )
        
    

class HydrusResourceClientAPIRestrictedEditFileViewingStatisticsIncrementFileViewingStatistics( HydrusResourceClientAPIRestrictedEditFileViewingStatistics ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if not CG.client_controller.new_options.GetBoolean( 'file_viewing_statistics_active' ):
            
            raise HydrusExceptions.InsufficientCredentialsException( 'Sorry, the user has disabled file viewing statistics on this client!' )
            
        
        canvas_type = request.parsed_request_args.GetValue( 'canvas_type', int )
        
        if canvas_type not in ( CC.CANVAS_MEDIA_VIEWER, CC.CANVAS_PREVIEW, CC.CANVAS_CLIENT_API ):
            
            raise HydrusExceptions.BadRequestException( 'Sorry, the canvas type needs to be either 0, 1, or 4!' )
            
        
        if 'timestamp' in request.parsed_request_args:
            
            timestamp = request.parsed_request_args.GetValueOrNone( 'timestamp', float )
            
            view_timestamp_ms = HydrusTime.MillisecondiseS( timestamp )
            
        elif 'timestamp_ms' in request.parsed_request_args:
            
            view_timestamp_ms = request.parsed_request_args.GetValueOrNone( 'timestamp_ms', int )
            
        else:
            
            view_timestamp_ms = HydrusTime.GetNowMS()
            
        
        views_delta = request.parsed_request_args.GetValue( 'views', int, default_value = 1 )
        
        viewtime_float = request.parsed_request_args.GetValue( 'viewtime', float )
        
        if views_delta < 0:
            
            raise HydrusExceptions.BadRequestException( 'Views cannot be a negative number!' )
            
        
        if viewtime_float < 0:
            
            raise HydrusExceptions.BadRequestException( 'Viewtime cannot be a negative number!' )
            
        
        viewtime_delta_ms = int( viewtime_float * 1000 )
        
        applicable_hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        if len( applicable_hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any hashes to apply the viewtime statistics to!' )
            
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, ( hash, canvas_type, view_timestamp_ms, views_delta, viewtime_delta_ms ) ) for hash in applicable_hashes ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_updates )
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedEditFileViewingStatisticsSetFileViewingStatistics( HydrusResourceClientAPIRestrictedEditFileViewingStatistics ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if not CG.client_controller.new_options.GetBoolean( 'file_viewing_statistics_active' ):
            
            raise HydrusExceptions.InsufficientCredentialsException( 'Sorry, the user has disabled file viewing statistics on this client!' )
            
        
        canvas_type = request.parsed_request_args.GetValue( 'canvas_type', int )
        
        if canvas_type not in ( CC.CANVAS_MEDIA_VIEWER, CC.CANVAS_PREVIEW, CC.CANVAS_CLIENT_API ):
            
            raise HydrusExceptions.BadRequestException( 'Sorry, the canvas type needs to be either 0, 1, or 4!' )
            
        
        if 'timestamp' in request.parsed_request_args:
            
            timestamp = request.parsed_request_args.GetValueOrNone( 'timestamp', float )
            
            view_timestamp_ms = HydrusTime.MillisecondiseS( timestamp )
            
        elif 'timestamp_ms' in request.parsed_request_args:
            
            view_timestamp_ms = request.parsed_request_args.GetValueOrNone( 'timestamp_ms', int )
            
        else:
            
            view_timestamp_ms = None
            
        
        views = request.parsed_request_args.GetValue( 'views', int )
        
        viewtime_float = request.parsed_request_args.GetValue( 'viewtime', float )
        
        if views < 0:
            
            raise HydrusExceptions.BadRequestException( 'Views cannot be a negative number!' )
            
        
        if viewtime_float < 0:
            
            raise HydrusExceptions.BadRequestException( 'Viewtime cannot be a negative number!' )
            
        
        viewtime_ms = int( viewtime_float * 1000 )
        
        applicable_hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        if len( applicable_hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any hashes to apply the viewtime statistics to!' )
            
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_SET, ( hash, canvas_type, view_timestamp_ms, views, viewtime_ms ) ) for hash in applicable_hashes ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_updates )
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
