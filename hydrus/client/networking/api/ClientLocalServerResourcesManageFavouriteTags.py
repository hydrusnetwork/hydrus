from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientGlobals as CG
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources

class HydrusResourceClientAPIRestrictedManageFavouriteTags( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS )
        
    

class HydrusResourceClientAPIRestrictedManageFavouriteTagsGetFavouriteTags( HydrusResourceClientAPIRestrictedManageFavouriteTags ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        favourite_tags = CG.client_controller.new_options.GetStringList( 'favourite_tags' )
        
        body_dict = {
            'favourite_tags': favourite_tags
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext(
            200,
            mime = request.preferred_mime,
            body = body
        )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageFavouriteTagsSetFavouriteTags( HydrusResourceClientAPIRestrictedManageFavouriteTags ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        favourite_tags = CG.client_controller.new_options.GetStringList( 'favourite_tags' )
        
        if 'set' in request.parsed_request_args:
            
            set_tags = request.parsed_request_args.GetValue( 'set', list, expected_list_type = str )
            
            set_tags = HydrusTags.CleanTags( set_tags )
            
            favourite_tags = set_tags
            
        else:
            
            add_tags = request.parsed_request_args.GetValue( 'add', list, expected_list_type = str, default_value = [] )
            
            remove_tags = request.parsed_request_args.GetValue( 'remove', list, expected_list_type = str, default_value = [] )
            
            add_tags = HydrusTags.CleanTags( add_tags )
            
            remove_tags = HydrusTags.CleanTags( remove_tags )
            
            favourite_tags = set( favourite_tags )
            
            favourite_tags.update( add_tags )
            
            favourite_tags.difference_update( remove_tags )
            
        
        favourite_tags = sorted( favourite_tags, key = HydrusText.HumanTextSortKey )
        
        CG.client_controller.new_options.SetStringList( 'favourite_tags', favourite_tags )
        
        CG.client_controller.pub( 'notify_new_favourite_tags' )
        
        body_dict = {
            'favourite_tags' : favourite_tags
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
