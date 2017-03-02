import ClientLocalServerResources
import HydrusServer

class HydrusServiceBooru( HydrusServer.HydrusService ):
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( 'gallery', ClientLocalServerResources.HydrusResourceBooruGallery( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'page', ClientLocalServerResources.HydrusResourceBooruPage( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'file', ClientLocalServerResources.HydrusResourceBooruFile( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'thumbnail', ClientLocalServerResources.HydrusResourceBooruThumbnail( self._service, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'style.css', ClientLocalServerResources.local_booru_css )
        
        return root

class HydrusServiceLocal( HydrusServer.HydrusService ):
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( 'file', ClientLocalServerResources.HydrusResourceLocalFile( self._service, HydrusServer.LOCAL_DOMAIN ) )
        root.putChild( 'thumbnail', ClientLocalServerResources.HydrusResourceLocalThumbnail( self._service, HydrusServer.LOCAL_DOMAIN ) )
        
        return root
        
    
