from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientGlobals as CG
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources

class HydrusResourceClientAPIRestrictedManageServices( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    pass
    

class HydrusResourceClientAPIRestrictedManageServicesPendingContentJobs( HydrusResourceClientAPIRestrictedManageServices ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_COMMIT_PENDING )
        
    

class HydrusResourceClientAPIRestrictedManageServicesPendingCounts( HydrusResourceClientAPIRestrictedManageServicesPendingContentJobs ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        info_type_to_str_lookup = {
            HC.SERVICE_INFO_NUM_PENDING_MAPPINGS : 'pending_tag_mappings',
            HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS : 'petitioned_tag_mappings',
            HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS : 'pending_tag_siblings',
            HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS : 'petitioned_tag_siblings',
            HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS : 'pending_tag_parents',
            HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS : 'petitioned_tag_parents',
            HC.SERVICE_INFO_NUM_PENDING_FILES : 'pending_files',
            HC.SERVICE_INFO_NUM_PETITIONED_FILES : 'petitioned_files',
        }
        
        service_keys_to_info_types_to_counts = CG.client_controller.Read( 'nums_pending' )
        
        body_dict = {
            'pending_counts' : { service_key.hex() : { info_type_to_str_lookup[ info_type ] : count for ( info_type, count ) in info_types_to_counts.items() } for ( service_key, info_types_to_counts ) in service_keys_to_info_types_to_counts.items() },
            'services' : ClientLocalServerCore.GetServicesDict()
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageServicesCommitPending( HydrusResourceClientAPIRestrictedManageServicesPendingContentJobs ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        service_key = request.parsed_request_args.GetValue( 'service_key', bytes )
        
        ClientLocalServerCore.CheckUploadableService( service_key )
        
        def do_it():
            
            if CG.client_controller.gui.IsCurrentlyUploadingPending( service_key ):
                
                raise HydrusExceptions.ConflictException( 'Upload is already running.' )
                
            
            result = CG.client_controller.gui.UploadPending( service_key )
            
            if not result:
                
                raise HydrusExceptions.UnprocessableEntity( 'Sorry, could not start for some complex reason--check the client!' )
                
            
        
        CG.client_controller.CallBlockingToQt( CG.client_controller.gui, do_it )
        
        body_dict = {}
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManageServicesForgetPending( HydrusResourceClientAPIRestrictedManageServicesPendingContentJobs ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        service_key = request.parsed_request_args.GetValue( 'service_key', bytes )
        
        ClientLocalServerCore.CheckUploadableService( service_key )
        
        CG.client_controller.WriteSynchronous( 'delete_pending', service_key )
        
        body_dict = {}
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
