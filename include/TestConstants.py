import collections
import HydrusConstants as HC
import HydrusTags
import os
import random
import threading
import weakref
import wx
import HydrusData
import HydrusFileHandling

tinest_gif = '\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\xFF\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00\x3B'

class FakeHTTPConnectionManager():
    
    def __init__( self ):
        
        self._fake_responses = {}
        
    
    def Request( self, method, url, request_headers = None, body = '', return_everything = False, return_cookies = False, report_hooks = None, temp_path = None, long_timeout = False ):
        
        if request_headers is None: request_headers = {}
        if report_hooks is None: report_hooks = []
        
        ( response, size_of_response, response_headers, cookies ) = self._fake_responses[ ( method, url ) ]
        
        if temp_path is not None:
            
            with open( temp_path, 'wb' ) as f: f.write( response )
            
            response = 'path written to temporary path'
            
        
        if return_everything: return ( response, size_of_response, response_headers, cookies )
        elif return_cookies: return ( response, cookies )
        else: return response
        
    
    def SetResponse( self, method, url, response, size_of_response = 100, response_headers = None, cookies = None ):
        
        if response_headers is None: response_headers = {}
        if cookies is None: cookies = []
        
        self._fake_responses[ ( method, url ) ] = ( response, size_of_response, response_headers, cookies )
        
    
class FakeWebSessionManager():
    
    def GetCookies( self, *args, **kwargs ): return { 'session_cookie' : 'blah' }
    
class FakePubSub():
    
    def __init__( self ):
        
        self._pubsubs = collections.defaultdict( list )
        
        self._callables = []
        
        self._lock = threading.Lock()
        
        self._topics_to_objects = {}
        self._topics_to_method_names = {}
        
    
    def _GetCallables( self, topic ):
        
        callables = []
        
        if topic in self._topics_to_objects:
            
            try:
                
                objects = self._topics_to_objects[ topic ]
                
                for object in objects:
                    
                    method_names = self._topics_to_method_names[ topic ]
                    
                    for method_name in method_names:
                        
                        if hasattr( object, method_name ):
                            
                            try:
                                
                                callable = getattr( object, method_name )
                                
                                callables.append( callable )
                                
                            except wx.PyDeadObjectError: pass
                            except TypeError as e:
                                
                                if '_wxPyDeadObject' not in str( e ): raise
                                
                            
                        
                    
                
            except: pass
            
        
        return callables
        
    
    def ClearPubSubs( self ): self._pubsubs = collections.defaultdict( list )
    
    def GetPubSubs( self, topic ): return self._pubsubs[ topic ]
    
    def NoJobsQueued( self ): return True
    
    def WXProcessQueueItem( self ): pass
    
    def pub( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            self._pubsubs[ topic ].append( ( args, kwargs ) )
            
        
    
    def sub( self, object, method_name, topic ):
        
        if topic not in self._topics_to_objects: self._topics_to_objects[ topic ] = weakref.WeakSet()
        if topic not in self._topics_to_method_names: self._topics_to_method_names[ topic ] = set()
        
        self._topics_to_objects[ topic ].add( object )
        self._topics_to_method_names[ topic ].add( method_name )
        
    
    def WXpubimmediate( self, topic, *args, **kwargs ):
        
        with self._lock:
            
            callables = self._GetCallables( topic )
            
            for callable in callables: callable( *args, **kwargs )
            
        
    