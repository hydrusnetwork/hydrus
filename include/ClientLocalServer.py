from . import ClientLocalServerResources
from . import HydrusServer

class HydrusServiceBooru( HydrusServer.HydrusService ):
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( b'gallery', ClientLocalServerResources.HydrusResourceBooruGallery( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'page', ClientLocalServerResources.HydrusResourceBooruPage( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'file', ClientLocalServerResources.HydrusResourceBooruFile( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'thumbnail', ClientLocalServerResources.HydrusResourceBooruThumbnail( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( b'style.css', ClientLocalServerResources.local_booru_css )
        
        return root

class HydrusServiceLocal( HydrusServer.HydrusService ):
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( b'file', ClientLocalServerResources.HydrusResourceLocalFile( self._service, HydrusServer.LOCAL_DOMAIN ) )
        root.putChild( b'thumbnail', ClientLocalServerResources.HydrusResourceLocalThumbnail( self._service, HydrusServer.LOCAL_DOMAIN ) )
        
        return root
        
    
