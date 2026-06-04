from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIPages
from hydrus.client.gui.pages import ClientGUIPagesCore
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.networking.api import ClientLocalServerResources
from hydrus.client.media import ClientMediaCollect
from hydrus.client.media import ClientMediaSort
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchTagContext
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
            
        
        def do_it( page_type, page_name, page_of_pages_key, focus_page, predicates, file_service_key, tag_service_key, hashes, service_key, paths, delete_after_success, file_sort_type, file_sort_asc, file_sort_namespaces, collect_namespaces, system_hash_locked, urls, url ):
            
            root_notebook = CG.client_controller.gui.GetTopLevelNotebook()
            
            if page_of_pages_key is not None:
                
                target_notebook = root_notebook.GetPageFromPageKey( page_of_pages_key )
                
                if target_notebook is None or not isinstance( target_notebook, ClientGUIPages.PagesNotebook ):
                    
                    raise HydrusExceptions.NotFoundException( 'Could not find a page of pages with that key!' )
                    
            else:
                
                target_notebook = root_notebook
                
            
            if page_type == ClientGUIPagesCore.PAGE_TYPE_QUERY:
                
                if file_service_key is not None:
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( file_service_key )
                    
                else:
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
                    
                
                if tag_service_key is None:
                    
                    tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
                    
                
                tag_context = ClientSearchTagContext.TagContext( service_key = tag_service_key )
                
                file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context, predicates = predicates )
                
                page_manager = ClientGUIPageManager.CreatePageManagerQuery( page_name or 'files', file_search_context )
                
                if file_sort_namespaces is not None:
                    
                    sort_order = CC.SORT_ASC if file_sort_asc else CC.SORT_DESC
                    
                    media_sort = ClientMediaSort.MediaSort(
                        sort_type = ( 'namespaces', ( tuple( file_sort_namespaces ), ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) ),
                        sort_order = sort_order
                    )
                    
                    page_manager.SetVariable( 'media_sort', media_sort )
                    
                elif file_sort_type is not None:
                    
                    sort_order = CC.SORT_ASC if file_sort_asc else CC.SORT_DESC
                    
                    media_sort = ClientMediaSort.MediaSort(
                        sort_type = ( 'system', file_sort_type ),
                        sort_order = sort_order
                    )
                    
                    page_manager.SetVariable( 'media_sort', media_sort )
                    
                
                if collect_namespaces is not None:
                    
                    media_collect = ClientMediaCollect.MediaCollect(
                        namespaces = collect_namespaces,
                        collect_unmatched = True
                    )
                    
                    page_manager.SetVariable( 'media_collect', media_collect )
                    
                
                if system_hash_locked is not None and system_hash_locked:
                    
                    page_manager.SetVariable( 'system_hash_locked', True )
                    page_manager.SetVariable( 'system_hash_locked_syncs_new', True )
                    page_manager.SetVariable( 'system_hash_locked_syncs_removes', True )
                    
                
                page = target_notebook.NewPage( page_manager, initial_hashes = hashes or [], select_page = False )
                
            elif page_type == ClientGUIPagesCore.PAGE_TYPE_PAGE_OF_PAGES:
                
                page = target_notebook.NewPagesNotebook( name = page_name or 'pages', give_it_a_blank_page = False, select_page = False )
                
            elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_MULTIPLE_GALLERY:
                
                page_manager = ClientGUIPageManager.CreatePageManagerImportGallery( page_name = page_name )
                
                page = target_notebook.NewPage( page_manager, select_page = False )
                
            elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_SIMPLE_DOWNLOADER:
                
                page_manager = ClientGUIPageManager.CreatePageManagerImportSimpleDownloader()
                
                page = target_notebook.NewPage( page_manager, select_page = False )
                
            elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_URLS:
                
                page_manager = ClientGUIPageManager.CreatePageManagerImportURLs( page_name = page_name )
                
                if len( urls ) > 0:
                    
                    from hydrus.client.importing import ClientImportSimpleURLs
                    
                    urls_import: ClientImportSimpleURLs.URLsImport = page_manager.GetVariable( 'urls_import' )
                    urls_import.PendURLs( urls )
                    
                
                page = target_notebook.NewPage( page_manager, select_page = False )
                
            elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_MULTIPLE_WATCHER:
                
                page_manager = ClientGUIPageManager.CreatePageManagerImportMultipleWatcher( page_name = page_name, url = url )
                
                page = target_notebook.NewPage( page_manager, select_page = False )
                
            elif page_type == ClientGUIPagesCore.PAGE_TYPE_DUPLICATE_FILTER:
                
                if file_service_key is not None:
                    
                    location_context = ClientLocation.LocationContext.STATICCreateSimple( file_service_key )
                    
                else:
                    
                    location_context = None
                    
                
                page_manager = ClientGUIPageManager.CreatePageManagerDuplicateFilter( page_name = page_name, location_context = location_context )
                
                page = target_notebook.NewPage( page_manager, select_page = False )
                
            elif page_type == ClientGUIPagesCore.PAGE_TYPE_PETITIONS:
                
                if service_key is None:
                    
                    raise HydrusExceptions.BadRequestException( 'Petitions page requires a service_key!' )
                    
                
                page_manager = ClientGUIPageManager.CreatePageManagerPetitions( service_key )
                
                page = target_notebook.NewPage( page_manager, select_page = False )
                
            elif page_type == ClientGUIPagesCore.PAGE_TYPE_IMPORT_HDD:
                
                from hydrus.client.importing.options import ImportOptionsContainer
                
                import_options_container = ImportOptionsContainer.ImportOptionsContainer()
                
                page_manager = ClientGUIPageManager.CreatePageManagerImportHDD(
                    paths = paths,
                    import_options_container = import_options_container,
                    metadata_routers = [],
                    paths_to_additional_service_keys_to_tags = {},
                    delete_after_success = delete_after_success
                )
                
                page = target_notebook.NewPage( page_manager, select_page = False )
                
            else:
                
                raise HydrusExceptions.BadRequestException( 'Unrecognised or unsupported page type!' )
                
            
            if focus_page:
                
                CG.client_controller.gui.ShowPage( page.GetPageKey() )
                
                if hasattr( page, 'SetMediaFocus' ):
                    
                    page.SetMediaFocus()
                    
                
            
            return ( page.GetPageKey(), page.GetPageManager().GetType(), page.GetName() )
            
        
        try:
            
            ( page_key, returned_page_type, returned_page_name ) = CG.client_controller.CallBlockingToQtTLW( do_it, page_type, page_name, page_of_pages_key, focus_page, predicates, file_service_key, tag_service_key, hashes, service_key, paths, delete_after_success, file_sort_type, file_sort_asc, file_sort_namespaces, collect_namespaces, system_hash_locked, urls, url )
            
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
        
    
