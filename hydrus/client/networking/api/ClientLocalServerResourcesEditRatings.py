from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientGlobals as CG
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources


class HydrusResourceClientAPIRestrictedEditRatings( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_EDIT_RATINGS )
        
    

class HydrusResourceClientAPIRestrictedEditRatingsSetRating( HydrusResourceClientAPIRestrictedEditRatings ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        rating_service_key = request.parsed_request_args.GetValue( 'rating_service_key', bytes )
        
        applicable_hashes = set( ClientLocalServerCore.ParseHashes( request ) )
        
        if len( applicable_hashes ) == 0:
            
            raise HydrusExceptions.BadRequestException( 'Did not find any hashes to apply the ratings to!' )
            
        
        if 'rating' not in request.parsed_request_args:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, you need to give a rating to set it to!' )
            
        
        rating = request.parsed_request_args[ 'rating' ]
        
        rating_service = CG.client_controller.services_manager.GetService( rating_service_key )
        
        rating_service_type = rating_service.GetServiceType()
        
        none_ok = True
        
        if rating_service_type == HC.LOCAL_RATING_LIKE:
            
            expecting_type = bool
            
        elif rating_service_type == HC.LOCAL_RATING_NUMERICAL:
            
            expecting_type = int
            
        elif rating_service_type == HC.LOCAL_RATING_INCDEC:
            
            expecting_type = int
            
            none_ok = False
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'That service is not a rating service!' )
            
        
        if rating is None:
            
            if not none_ok:
                
                raise HydrusExceptions.BadRequestException( 'Sorry, this service does not allow a null rating!' )
                
            
        elif not isinstance( rating, expecting_type ):
            
            raise HydrusExceptions.BadRequestException( 'Sorry, this service expects a "{}" rating!'.format( expecting_type.__name__ ) )
            
        
        rating_for_content_update = rating
        
        if rating_service_type == HC.LOCAL_RATING_LIKE:
            
            if isinstance( rating, bool ):
                
                rating_for_content_update = 1.0 if rating else 0.0
                
            
        elif rating_service_type == HC.LOCAL_RATING_NUMERICAL:
            
            if isinstance( rating, int ):
                
                rating_for_content_update = rating_service.ConvertStarsToRating( rating )
                
            
        elif rating_service_type == HC.LOCAL_RATING_INCDEC:
            
            if rating < 0:
                
                rating_for_content_update = 0
                
            
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( rating_for_content_update, applicable_hashes ) )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( rating_service_key, content_update )
        
        CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
