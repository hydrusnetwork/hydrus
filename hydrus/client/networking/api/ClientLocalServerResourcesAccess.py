from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusStaticDir
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientGlobals as CG
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources

class HydrusResourceClientAPIPermissionsRequest( ClientLocalServerResources.HydrusResourceClientAPI ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        if not ClientAPI.api_request_dialog_open:
            
            raise HydrusExceptions.ConflictException( 'The permission registration dialog is not open. Please open it under "review services" in the hydrus client.' )
            
        
        name = request.parsed_request_args.GetValue( 'name', str )
        
        permits_everything = request.parsed_request_args.GetValue( 'permits_everything', bool, default_value = False )
        
        basic_permissions = request.parsed_request_args.GetValue( 'basic_permissions', list, expected_list_type = int, default_value = [] )
        
        basic_permissions = [ int( value ) for value in basic_permissions ]
        
        api_permissions = ClientAPI.APIPermissions( name = name, permits_everything = permits_everything, basic_permissions = basic_permissions )
        
        ClientAPI.last_api_permissions_request = api_permissions
        
        access_key = api_permissions.GetAccessKey()
        
        body_dict = {}
        
        body_dict[ 'access_key' ] = access_key.hex()
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIVersion( ClientLocalServerResources.HydrusResourceClientAPI ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        body_dict = {}
        
        body_dict[ 'version' ] = HC.CLIENT_API_VERSION
        body_dict[ 'hydrus_version' ] = HC.SOFTWARE_VERSION
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedAccount( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        pass
        
    
class HydrusResourceClientAPIRestrictedAccountSessionKey( HydrusResourceClientAPIRestrictedAccount ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        new_session_key = CG.client_controller.client_api_manager.GenerateSessionKey( request.client_api_permissions.GetAccessKey() )
        
        body_dict = {}
        
        body_dict[ 'session_key' ] = new_session_key.hex()
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedAccountVerify( HydrusResourceClientAPIRestrictedAccount ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        api_permissions = request.client_api_permissions
        
        permits_everything = api_permissions.PermitsEverything()
        
        if permits_everything:
            
            basic_permissions = ClientAPI.ALLOWED_PERMISSIONS
            
        else:
            
            basic_permissions = api_permissions.GetBasicPermissions()
            
        
        human_description = api_permissions.ToHumanString()
        
        body_dict = {}
        
        body_dict[ 'name' ] = api_permissions.GetName()
        body_dict[ 'permits_everything' ] = api_permissions.PermitsEverything()
        body_dict[ 'basic_permissions' ] = sorted( basic_permissions ) # set->list for json
        body_dict[ 'human_description' ] = human_description
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedGetService( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckAtLeastOnePermission(
            (
                ClientAPI.CLIENT_API_PERMISSION_ADD_FILES,
                ClientAPI.CLIENT_API_PERMISSION_EDIT_RATINGS,
                ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS,
                ClientAPI.CLIENT_API_PERMISSION_ADD_NOTES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_FILE_RELATIONSHIPS,
                ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES
            )
        )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        allowed_service_types = {
            HC.LOCAL_TAG,
            HC.TAG_REPOSITORY,
            HC.LOCAL_FILE_DOMAIN,
            HC.LOCAL_FILE_UPDATE_DOMAIN,
            HC.FILE_REPOSITORY,
            HC.HYDRUS_LOCAL_FILE_STORAGE,
            HC.COMBINED_LOCAL_FILE_DOMAINS,
            HC.COMBINED_FILE,
            HC.COMBINED_TAG,
            HC.LOCAL_RATING_LIKE,
            HC.LOCAL_RATING_NUMERICAL,
            HC.LOCAL_RATING_INCDEC,
            HC.LOCAL_FILE_TRASH_DOMAIN
        }
        
        if 'service_key' in request.parsed_request_args:
            
            service_key = request.parsed_request_args.GetValue( 'service_key', bytes )
            
        elif 'service_name' in request.parsed_request_args:
            
            service_name = request.parsed_request_args.GetValue( 'service_name', str )
            
            try:
                
                service_key = CG.client_controller.services_manager.GetServiceKeyFromName( allowed_service_types, service_name )
                
            except HydrusExceptions.DataMissing:
                
                raise HydrusExceptions.NotFoundException( 'Sorry, did not find a service with name "{}"!'.format( service_name ) )
                
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, you need to give a service_key or service_name!' )
            
        
        try:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
        except HydrusExceptions.DataMissing:
            
            raise HydrusExceptions.NotFoundException( 'Sorry, did not find a service with key "{}"!'.format( service_key.hex() ) )
            
        
        if service.GetServiceType() not in allowed_service_types:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, for now, you cannot ask about this service!' )
            
        
        body_dict = {
            'service' : {
                'name' : service.GetName(),
                'type' : service.GetServiceType(),
                'type_pretty' : HC.service_string_lookup[ service.GetServiceType() ],
                'service_key' : service.GetServiceKey().hex()
            }
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedGetServices( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckAtLeastOnePermission(
            (
                ClientAPI.CLIENT_API_PERMISSION_ADD_FILES,
                ClientAPI.CLIENT_API_PERMISSION_EDIT_RATINGS,
                ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS,
                ClientAPI.CLIENT_API_PERMISSION_ADD_NOTES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_FILE_RELATIONSHIPS,
                ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES
            )
        )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        jobs = [
            ( ( HC.LOCAL_TAG, ), 'local_tags' ),
            ( ( HC.TAG_REPOSITORY, ), 'tag_repositories' ),
            ( ( HC.LOCAL_FILE_DOMAIN, ), 'local_files' ),
            ( ( HC.LOCAL_FILE_UPDATE_DOMAIN, ), 'local_updates' ),
            ( ( HC.FILE_REPOSITORY, ), 'file_repositories' ),
            ( ( HC.HYDRUS_LOCAL_FILE_STORAGE, ), 'all_local_files' ), # legacy, so not 'hydrus_local_file_storage'
            ( ( HC.COMBINED_LOCAL_FILE_DOMAINS, ), 'all_local_media' ),
            ( ( HC.COMBINED_FILE, ), 'all_known_files' ),
            ( ( HC.COMBINED_TAG, ), 'all_known_tags' ),
            ( ( HC.LOCAL_FILE_TRASH_DOMAIN, ), 'trash' )
        ]
        
        body_dict = {}
        
        for ( service_types, name ) in jobs:
            
            services = CG.client_controller.services_manager.GetServices( service_types )
            
            services_list = []
            
            for service in services:
                
                service_dict = {
                    'name' : service.GetName(),
                    'type' : service.GetServiceType(),
                    'type_pretty' : HC.service_string_lookup[ service.GetServiceType() ],
                    'service_key' : service.GetServiceKey().hex()
                }
                
                services_list.append( service_dict )
                
            
            body_dict[ name ] = services_list
            
        
        body_dict[ 'services' ] = ClientLocalServerCore.GetServicesDict()
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedGetServiceRatingSVG( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckAtLeastOnePermission(
            (
                ClientAPI.CLIENT_API_PERMISSION_ADD_FILES,
                ClientAPI.CLIENT_API_PERMISSION_EDIT_RATINGS,
                ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS,
                ClientAPI.CLIENT_API_PERMISSION_ADD_NOTES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES,
                ClientAPI.CLIENT_API_PERMISSION_MANAGE_FILE_RELATIONSHIPS,
                ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES
            )
        )
        
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        allowed_service_types = {
            HC.LOCAL_RATING_LIKE,
            HC.LOCAL_RATING_NUMERICAL,
        }
        
        if 'service_key' in request.parsed_request_args:
            
            service_key = request.parsed_request_args.GetValue( 'service_key', bytes )
            
        elif 'service_name' in request.parsed_request_args:
            
            service_name = request.parsed_request_args.GetValue( 'service_name', str )
            
            try:
                
                service_key = CG.client_controller.services_manager.GetServiceKeyFromName( allowed_service_types, service_name )
                
            except HydrusExceptions.DataMissing:
                
                raise HydrusExceptions.NotFoundException( 'Sorry, did not find a service with name "{}"!'.format( service_name ) )
                
            
        else:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, you need to give a service_key or service_name!' )
            
        
        try:
            
            service = CG.client_controller.services_manager.GetService( service_key )
            
        except HydrusExceptions.DataMissing:
            
            raise HydrusExceptions.NotFoundException( 'Sorry, did not find a service with key "{}"!'.format( service_key.hex() ) )
            
        
        if service.GetServiceType() not in allowed_service_types:
            
            raise HydrusExceptions.BadRequestException( 'This type of service cannot have a SVG associated with it!' )
            
        
        try:
            
            star_type = service.GetStarType()
            
            if star_type.HasRatingSVG():
                
                svg_name = star_type.GetRatingSVG()
                
                svg_path = HydrusStaticDir.GetRatingSVGPath( svg_name )
                
                with open( svg_path, 'rb' ) as f:
                    
                    svg_content = f.read()
                    
                
            else:
                
                raise HydrusExceptions.NotFoundException( 'Rating service "{}" does not use a SVG icon!'.format( service.GetName() ) )
                
            
        except HydrusExceptions.NotFoundException:
            
            raise
            
        except Exception as e:
            
            raise HydrusExceptions.ServerException( 'There was a problem getting the SVG file for rating service "{}"! Error follows: {}'.format( service.GetName(), str(e) ) )
            
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = HC.IMAGE_SVG, body = svg_content )
        
        return response_context
        
    
