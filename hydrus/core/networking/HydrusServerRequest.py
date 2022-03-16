from twisted.web.server import Request

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData

class HydrusRequest( Request ):
    
    def __init__( self, *args, **kwargs ):
        
        Request.__init__( self, *args, **kwargs )
        
        self.start_time = HydrusData.GetNowPrecise()
        self.parsed_request_args = None
        self.hydrus_response_context = None
        self.hydrus_account = None
        self.client_api_permissions = None
        self.preferred_mime = HC.APPLICATION_JSON
        
    
    def IsGET( self ):
        
        return self.method == b'GET'
        
    
    def IsPOST( self ):
        
        return self.method == b'POST'
        
    
class HydrusRequestLogging( HydrusRequest ):
    
    def finish( self ):
        
        HydrusRequest.finish( self )
        
        host = self.getHost()
        
        if self.hydrus_response_context is not None:
            
            status_text = str( self.hydrus_response_context.GetStatusCode() )
            
        elif hasattr( self, 'code' ):
            
            status_text = str( self.code )
            
        else:
            
            status_text = '200'
            
        
        message = str( host.port ) + ' ' + str( self.method, 'utf-8' ) + ' ' + str( self.path, 'utf-8' ) + ' ' + status_text + ' in ' + HydrusData.TimeDeltaToPrettyTimeDelta( HydrusData.GetNowPrecise() - self.start_time )
        
        HydrusData.Print( message )
        
