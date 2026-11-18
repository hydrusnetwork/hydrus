from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources
from hydrus.core import HydrusExceptions

class HydrusResourceClientAPIRestrictedManagePages( ClientLocalServerResources.HydrusResourceClientAPIRestricted ):
    
    def _CheckAPIPermissions( self, request: HydrusServerRequest.HydrusRequest ):
        
        request.client_api_permissions.CheckPermission( ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES )
        
    

class HydrusResourceClientAPIRestrictedManagePagesAddFiles( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it( page_key, media_results ):
            
            page = CG.client_controller.gui.GetPageFromPageKey( page_key )
            
            from hydrus.client.gui.pages import ClientGUIPages
            
            if page is None:
                
                raise HydrusExceptions.DataMissing()
                
            
            if not isinstance( page, ClientGUIPages.Page ):
                
                raise HydrusExceptions.BadRequestException( 'That page key was not for a normal media page!' )
                
            
            page.AddMediaResults( media_results )
            
        
        if 'page_key' not in request.parsed_request_args:
            
            raise HydrusExceptions.BadRequestException( 'You need a page key for this request!' )
            
        
        page_key = request.parsed_request_args.GetValue( 'page_key', bytes )
        
        hashes = ClientLocalServerCore.ParseHashes( request )
        
        media_results = CG.client_controller.Read( 'media_results', hashes, sorted = True )
        
        try:
            
            CG.client_controller.CallBlockingToQtTLW( do_it, page_key, media_results )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that page!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePagesClosePage( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it( page_key ):
            
            CG.client_controller.gui.ClosePage( page_key )
            
        
        page_key = request.parsed_request_args.GetValue( 'page_key', bytes )
        
        try:
            
            CG.client_controller.CallBlockingToQtTLW( do_it, page_key )
            
        except HydrusExceptions.DataMissing:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that page!' )
            
        return HydrusServerResources.ResponseContext( 200 )
        
    
class HydrusResourceClientAPIRestrictedManagePagesFocusPage( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it( page_key ):
            
            return CG.client_controller.gui.ShowPage( page_key )
            
        
        page_key = request.parsed_request_args.GetValue( 'page_key', bytes )
        
        try:
            
            CG.client_controller.CallBlockingToQtTLW( do_it, page_key )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that page!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    
class HydrusResourceClientAPIRestrictedManagePagesGetPages( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it():
            
            return CG.client_controller.gui.GetCurrentSessionPageAPIInfoDict()
            
        
        page_info_dict = CG.client_controller.CallBlockingToQtTLW( do_it )
        
        body_dict = { 'pages' : page_info_dict }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePagesGetPageInfo( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it( page_key, simple ):
            
            return CG.client_controller.gui.GetPageAPIInfoDict( page_key, simple )
            
        
        page_key = request.parsed_request_args.GetValue( 'page_key', bytes )
        
        simple = request.parsed_request_args.GetValue( 'simple', bool, default_value = True )
        
        page_info_dict = CG.client_controller.CallBlockingToQtTLW( do_it, page_key, simple )
        
        if page_info_dict is None:
            
            raise HydrusExceptions.NotFoundException( 'Did not find a page for "{}"!'.format( page_key.hex() ) )
            
        
        body_dict = { 'page_info' : page_info_dict }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePagesRefreshPage( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it( page_key ):
            
            return CG.client_controller.gui.RefreshPage( page_key )
            
        
        page_key = request.parsed_request_args.GetValue( 'page_key', bytes )
        
        try:
            
            CG.client_controller.CallBlockingToQtTLW( do_it, page_key )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( 'Could not find that page!' )
            
        
        response_context = HydrusServerResources.ResponseContext( 200 )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePagesGetMediaViewers( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        def do_it():
            
            return CG.client_controller.gui.GetMediaViewersAPIInfo()
            
        
        media_viewers_info = CG.client_controller.CallBlockingToQtTLW( do_it )
        
        body_dict = {
            'media_viewers': media_viewers_info
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    

class HydrusResourceClientAPIRestrictedManagePagesNewPage( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoPOSTJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        page_type = request.parsed_request_args.GetValue( 'page_type', int )
        page_name = request.parsed_request_args.GetValueOrNone( 'page_name', str )
        page_of_pages_key = request.parsed_request_args.GetValueOrNone( 'page_of_pages_key', bytes )
        focus_page = request.parsed_request_args.GetValue( 'focus_page', bool, default_value = True )
        tags = request.parsed_request_args.GetValue( 'tags', list, default_value = [] )
        file_service_key = request.parsed_request_args.GetValueOrNone( 'file_service_key', bytes )
        tag_service_key = request.parsed_request_args.GetValueOrNone( 'tag_service_key', bytes )
        hashes = ClientLocalServerCore.ParseHashes( request, optional = True )
        service_key = request.parsed_request_args.GetValueOrNone( 'service_key', bytes )
        paths = request.parsed_request_args.GetValue( 'paths', list, default_value = [] )
        delete_after_success = request.parsed_request_args.GetValue( 'delete_after_success', bool, default_value = False )
        
        file_sort_type = request.parsed_request_args.GetValueOrNone( 'file_sort_type', int )
        file_sort_asc = request.parsed_request_args.GetValue( 'file_sort_asc', bool, default_value = True )
        file_sort_namespaces = request.parsed_request_args.GetValueOrNone( 'file_sort_namespaces', list )
        collect_namespaces = request.parsed_request_args.GetValueOrNone( 'collect_namespaces', list )
        system_hash_locked = request.parsed_request_args.GetValueOrNone( 'system_hash_locked', bool )
        urls = request.parsed_request_args.GetValue( 'urls', list, default_value = [] )
        url = request.parsed_request_args.GetValueOrNone( 'url', str )
        
        if file_sort_type is not None and file_sort_namespaces is not None:
            
            raise HydrusExceptions.BadRequestException( 'Provide either file_sort_type (system sort) or file_sort_namespaces (namespace sort), not both!' )
            
        
        if file_sort_type is not None and file_sort_type not in CC.SYSTEM_SORT_TYPES:
            
            raise HydrusExceptions.BadRequestException( 'Sorry, did not understand that sort type!' )
            
        
        if tag_service_key is not None:
            
            ClientLocalServerCore.CheckTagService( tag_service_key )
            
        
        if system_hash_locked is not None and system_hash_locked and ( hashes is None or len( hashes ) == 0 ):
            
            raise HydrusExceptions.BadRequestException( 'system_hash_locked requires hashes to be provided!' )
            
        
        if len( tags ) > 0:
            
            predicates = ClientLocalServerCore.ParseClientAPISearchPredicates( request )
            
        else:
            
            predicates = []
            
        
        from hydrus.client.gui.pages import ClientGUINewPageAPI
        
        try:
            
            ( page_key, returned_page_type, returned_page_name ) = CG.client_controller.CallBlockingToQtTLW( ClientGUINewPageAPI.MakeNewPageFromAPI, page_type, page_name, page_of_pages_key, focus_page, predicates, file_service_key, tag_service_key, hashes, service_key, paths, delete_after_success, file_sort_type, file_sort_asc, file_sort_namespaces, collect_namespaces, system_hash_locked, urls, url )
            
        except HydrusExceptions.DataMissing as e:
            
            raise HydrusExceptions.NotFoundException( str( e ) )
            
        
        body_dict = {
            'page_key' : page_key.hex(),
            'page_type' : returned_page_type,
            'page_name' : returned_page_name
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
