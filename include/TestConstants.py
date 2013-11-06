import ClientConstants
import HydrusConstants as HC
import HydrusTags
import os
import random
import urlparse

tinest_gif = '\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\xFF\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00\x3B'

def GenerateClientServiceIdentifier( service_type ):
    
    if service_type == HC.LOCAL_TAG: return HC.LOCAL_TAG_SERVICE_IDENTIFIER
    elif service_type == HC.LOCAL_FILE: return HC.LOCAL_FILE_SERVICE_IDENTIFIER
    else:
        
        service_key = os.urandom( 32 )
        service_name = random.sample( 'abcdefghijklmnopqrstuvwxyz ', 12 )
        
        return HC.ClientServiceIdentifier( service_key, service_type, service_name )
        
    
class FakeHTTPConnection():
    
    def __init__( self, url = '', scheme = 'http', host = '', port = None, service_identifier = None, accept_cookies = False ):
        
        self._url = url
        self._scheme = scheme
        self._host = host
        self._port = port
        self._service_identifier = service_identifier
        self._accept_cookies = accept_cookies
        
        self._responses = {}
        self._cookies = {}
        
    
    def close( self ): pass
    
    def connect( self ): pass
    
    def AddReportHook( self, hook ): pass
    
    def ClearReportHooks( self ): pass
    
    def GetCookies( self ): return self._cookies
    
    def geturl( self, url, headers = {}, is_redirect = False, follow_redirects = True, response_to_path = False ):
        
        parse_result = urlparse.urlparse( url )
        
        request = parse_result.path
        
        query = parse_result.query
        
        if query != '': request += '?' + query
        
        response = self.request( 'GET', request, headers = headers, is_redirect = is_redirect, follow_redirects = follow_redirects, response_to_path = response_to_path )
        
        return response
        
    
    def request( self, request_type, request, headers = {}, body = None, is_redirect = False, follow_redirects = True, response_to_path = False ):
        
        response = self._responses[ ( request_type, request ) ]
        
        if issubclass( type( response ), Exception ): raise response
        else:
            
            if response_to_path:
                
                temp_path = HC.GetTempPath()
                
                with open( temp_path, 'wb' ) as f: f.write( response )
                
                response = temp_path
                
            
            return response
            
        
    
    def SetCookie( self, key, value ): self._cookies[ key ] = value
    
    def SetResponse( self, request_type, request, response ): self._responses[ ( request_type, request ) ] = response
    
class FakeHTTPConnectionManager():
    
    def __init__( self ):
        
        self._fake_connections = {}
        
    
    def GetConnection( self, url = '', scheme = 'http', host = '', port = None, service_identifier = None, accept_cookies = False ):
        
        args = ( url, scheme, host, port, service_identifier, accept_cookies )
        
        return self._fake_connections[ args ]
        
    
    def SetConnection( self, connection, url = '', scheme = 'http', host = '', port = None, service_identifier = None, accept_cookies = False ):
        
        args = ( url, scheme, host, port, service_identifier, accept_cookies )
        
        self._fake_connections[ args ] = connection
        
    
fake_http_connection_manager = FakeHTTPConnectionManager()