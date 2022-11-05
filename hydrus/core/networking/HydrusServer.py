from twisted.web.http import _GenericHTTPChannelProtocol, HTTPChannel
from twisted.web.server import Site
from twisted.web.server import Request
from twisted.web.resource import Resource

from hydrus.core import HydrusConstants as HC
from hydrus.core.networking import HydrusServerRequest
from hydrus.core.networking import HydrusServerResources

LOCAL_DOMAIN = HydrusServerResources.HydrusDomain( True )
REMOTE_DOMAIN = HydrusServerResources.HydrusDomain( False )

class FatHTTPChannel( HTTPChannel ):
    
    MAX_LENGTH = 2 * 1048576
    totalHeadersSize = 2 * 1048576 # :^)
    
class HydrusService( Site ):
    
    def __init__( self, service ):
        
        self._service = service
        
        service_type = self._service.GetServiceType()
        
        if service_type == HC.CLIENT_API_SERVICE:
            
            self._server_version_string = '{}/{} ({})'.format( HC.service_string_lookup[ service_type ], str( HC.CLIENT_API_VERSION ), str( HC.SOFTWARE_VERSION ) )
            
        else:
            
            self._server_version_string = '{}/{}'.format( HC.service_string_lookup[ service_type ], str( HC.NETWORK_VERSION ) )
            
        
        root = self._InitRoot()
        
        Site.__init__( self, root )
        
        self.protocol = self._ProtocolFactory
        
        if service.LogsRequests():
            
            self.requestFactory = HydrusServerRequest.HydrusRequestLogging
            
        else:
            
            self.requestFactory = HydrusServerRequest.HydrusRequest
            
        
    
    def _InitRoot( self ):
        
        root = Resource()
        
        root.putChild( b'', HydrusServerResources.HydrusResourceWelcome( self._service, REMOTE_DOMAIN ) )
        root.putChild( b'favicon.ico', HydrusServerResources.hydrus_favicon )
        root.putChild( b'robots.txt', HydrusServerResources.HydrusResourceRobotsTXT( self._service, REMOTE_DOMAIN ) )
        
        return root
        
    
    def _ProtocolFactory( self ):
        
        return _GenericHTTPChannelProtocol( FatHTTPChannel() )
        
    
    def getResourceFor( self, request: Request ):
        
        request.setHeader( 'Server', self._server_version_string )
        request.setHeader( 'Hydrus-Server', self._server_version_string )
        
        return Site.getResourceFor( self, request )
