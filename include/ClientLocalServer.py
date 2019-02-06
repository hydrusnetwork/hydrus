from . import ClientLocalServerResources
from . import HydrusServer
from twisted.web.resource import NoResource

class HydrusClientService( HydrusServer.HydrusService ):
    
    def __init__( self, service, allow_non_local_connections ):
        
        if allow_non_local_connections:
            
            self._client_requests_domain = HydrusServer.REMOTE_DOMAIN
            
        else:
            
            self._client_requests_domain = HydrusServer.LOCAL_DOMAIN
            
        
        HydrusServer.HydrusService.__init__( self, service )
        
    
class HydrusServiceBooru( HydrusClientService ):
    
    def _InitRoot( self ):
        
        root = HydrusClientService._InitRoot( self )
        
        root.putChild( b'gallery', ClientLocalServerResources.HydrusResourceBooruGallery( self._service, self._client_requests_domain ) )
        root.putChild( b'page', ClientLocalServerResources.HydrusResourceBooruPage( self._service, self._client_requests_domain ) )
        root.putChild( b'file', ClientLocalServerResources.HydrusResourceBooruFile( self._service, self._client_requests_domain ) )
        root.putChild( b'thumbnail', ClientLocalServerResources.HydrusResourceBooruThumbnail( self._service, self._client_requests_domain ) )
        root.putChild( b'style.css', ClientLocalServerResources.local_booru_css )
        
        return root
        
    
class HydrusServiceClientAPI( HydrusClientService ):
    
    def _InitRoot( self ):
        
        root = HydrusClientService._InitRoot( self )
        
        root.putChild( b'api_version', ClientLocalServerResources.HydrusResourceClientAPIVersion( self._service, self._client_requests_domain ) )
        root.putChild( b'request_new_permissions', ClientLocalServerResources.HydrusResourceClientAPIPermissionsRequest( self._service, self._client_requests_domain ) )
        root.putChild( b'verify_access_key', ClientLocalServerResources.HydrusResourceClientAPIVerify( self._service, self._client_requests_domain ) )
        
        add_urls = NoResource()
        
        root.putChild( b'add_urls', add_urls )
        
        add_urls.putChild( b'get_url_info', ClientLocalServerResources.HydrusResourceClientAPIRestrictedAddURLsGetURLParsingCapability( self._service, self._client_requests_domain ) )
        add_urls.putChild( b'add_url', ClientLocalServerResources.HydrusResourceClientAPIRestrictedAddURLsImportURL( self._service, self._client_requests_domain ) )
        
        return root
        
    
