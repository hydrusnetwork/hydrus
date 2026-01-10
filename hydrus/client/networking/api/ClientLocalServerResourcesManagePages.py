from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

from hydrus.client import ClientAPI
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
        
    

class HydrusResourceClientAPIRestrictedManagePagesGetMediaViewer( HydrusResourceClientAPIRestrictedManagePages ):
    
    def _threadDoGETJob( self, request: HydrusServerRequest.HydrusRequest ):
        
        from hydrus.core import HydrusConstants as HC
        
        def do_it():
            
            return CG.client_controller.gui.GetMediaViewerInfo()
            
        
        file_info = CG.client_controller.CallBlockingToQtTLW( do_it )
        
        if file_info is None:
            
            raise HydrusExceptions.NotFoundException( 'No media viewer is currently open or no file is being viewed!' )
            
        
        media_viewer_file = {
            'hash': file_info[ 'hash' ].hex(),
            'size': file_info[ 'size' ],
            'mime': HC.mime_string_lookup.get( file_info[ 'mime' ], 'unknown' ),
            'width': file_info[ 'width' ],
            'height': file_info[ 'height' ],
            'duration': file_info[ 'duration' ],
            'num_frames': file_info[ 'num_frames' ],
            'has_audio': file_info[ 'has_audio' ],
            'is_inbox': file_info[ 'is_inbox' ],
            'has_exif': file_info[ 'has_exif' ],
            'has_icc_profile': file_info[ 'has_icc_profile' ],
            'has_transparency': file_info[ 'has_transparency' ],
            'blurhash': file_info[ 'blurhash' ],
            'pixel_hash': file_info[ 'pixel_hash' ].hex() if file_info[ 'pixel_hash' ] is not None else None,
            'has_notes': file_info[ 'has_notes' ],
            'urls': file_info[ 'urls' ]
        }
        
        body_dict = {
            'media_viewer_file': media_viewer_file
        }
        
        body = ClientLocalServerCore.Dumps( body_dict, request.preferred_mime )
        
        response_context = HydrusServerResources.ResponseContext( 200, mime = request.preferred_mime, body = body )
        
        return response_context
        
    
