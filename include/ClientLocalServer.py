import ClientLocalServerResources
import HydrusServer

class HydrusServiceBooru( HydrusServer.HydrusService ):
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( 'gallery', ClientLocalServerResources.HydrusResourceCommandBooruGallery( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'page', ClientLocalServerResources.HydrusResourceCommandBooruPage( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'file', ClientLocalServerResources.HydrusResourceCommandBooruFile( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'thumbnail', ClientLocalServerResources.HydrusResourceCommandBooruThumbnail( self._service_key, self._service_type, HydrusServer.REMOTE_DOMAIN ) )
        root.putChild( 'style.css', ClientLocalServerResources.local_booru_css )
        
        return root

class HydrusServiceLocal( HydrusServer.HydrusService ):
    
    def _InitRoot( self ):
        
        root = HydrusServer.HydrusService._InitRoot( self )
        
        root.putChild( 'file', ClientLocalServerResources.HydrusResourceCommandLocalFile( self._service_key, self._service_type, HydrusServer.LOCAL_DOMAIN ) )
        root.putChild( 'thumbnail', ClientLocalServerResources.HydrusResourceCommandLocalThumbnail( self._service_key, self._service_type, HydrusServer.LOCAL_DOMAIN ) )
        
        return root
        
    