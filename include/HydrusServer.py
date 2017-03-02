import HydrusConstants as HC
import HydrusServerResources
import traceback
from twisted.web.server import Request, Site
from twisted.web.resource import Resource
import HydrusData
import time

LOCAL_DOMAIN = HydrusServerResources.HydrusDomain( True )
REMOTE_DOMAIN = HydrusServerResources.HydrusDomain( False )

class HydrusRequest( Request ):
    
    def __init__( self, *args, **kwargs ):
        
        Request.__init__( self, *args, **kwargs )
        
        self.start_time = time.clock()
        self.is_hydrus_client = True
        self.hydrus_args = None
        self.hydrus_response_context = None
        self.hydrus_request_data_usage = 0
        
    
    def finish( self ):
        
        Request.finish( self )
        
        host = self.getHost()
        
        if self.hydrus_response_context is not None:
            
            status_text = HydrusData.ToUnicode( self.hydrus_response_context.GetStatusCode() )
            
        elif hasattr( self, 'code' ):
            
            status_text = str( self.code )
            
        else:
            
            status_text = '200'
            
        
        message = str( host.port ) + ' ' + HydrusData.ToUnicode( self.method ) + ' ' + HydrusData.ToUnicode( self.path ) + ' ' + status_text + ' in ' + HydrusData.ConvertTimeDeltaToPrettyString( time.clock() - self.start_time )
        
        HydrusData.Print( message )
        
    
class HydrusService( Site ):
    
    def __init__( self, service ):
        
        self._service = service
        
        root = self._InitRoot()
        
        Site.__init__( self, root )
        
        self.requestFactory = HydrusRequest
        
    
    def _InitRoot( self ):
        
        root = Resource()
        
        root.putChild( '', HydrusServerResources.HydrusResourceWelcome( self._service, REMOTE_DOMAIN ) )
        root.putChild( 'favicon.ico', HydrusServerResources.hydrus_favicon )
        
        return root
        
    
