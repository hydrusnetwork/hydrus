import ClientConstants
import collections
import HydrusConstants as HC
import HydrusTags
import os
import random
import threading

tinest_gif = '\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\xFF\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00\x3B'

def GenerateClientServiceIdentifier( service_type ):
    
    if service_type == HC.LOCAL_TAG: return HC.LOCAL_TAG_SERVICE_IDENTIFIER
    elif service_type == HC.LOCAL_FILE: return HC.LOCAL_FILE_SERVICE_IDENTIFIER
    else:
        
        service_key = os.urandom( 32 )
        service_name = random.sample( 'abcdefghijklmnopqrstuvwxyz ', 12 )
        
        return HC.ClientServiceIdentifier( service_key, service_type, service_name )
        
    
class FakeHTTPConnectionManager():
    
    def __init__( self ):
        
        self._fake_responses = {}
        
    
    def Request( self, method, url, request_headers = {}, body = '', return_everything = False, return_cookies = False, report_hooks = [], response_to_path = False, long_timeout = False ):
        
        ( response, size_of_response, response_headers, cookies ) = self._fake_responses[ ( method, url ) ]
        
        if response_to_path:
            
            temp_path = HC.GetTempPath()
            
            with open( temp_path, 'wb' ) as f: f.write( response )
            
            response = temp_path
            
        
        if return_everything: return ( response, size_of_response, response_headers, cookies )
        elif return_cookies: return ( response, cookies )
        else: return response
        
    
    def SetResponse( self, method, url, response, size_of_response = 100, response_headers = {}, cookies = [] ):
        
        self._fake_responses[ ( method, url ) ] = ( response, size_of_response, response_headers, cookies )
        
    
class FakeWebSessionManager():
    
    def GetCookies( self, *args, **kwargs ): return { 'session_cookie' : 'blah' }
    
class FakePubSub():
    
    def __init__( self ):
        
        self._pubsubs = collections.defaultdict( list )
        
        self._lock = threading.Lock()
        
    
    def ClearPubSubs( self ): self._pubsubs = collections.defaultdict( list )
    
    def GetPubSubs( self, topic ): return self._pubsubs[ topic ]
    
    def NotBusy( self ): return True
    
    def WXProcessQueueItem( self ): pass
    
    def pub( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            self._pubsubs[ topic ].append( ( args, kwargs ) )
            
        
    
    def sub( self, object, method_name, topic ): pass
    
    def WXpubimmediate( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            self._pubsubs[ topic ].append( ( args, kwargs ) )
            
        
    