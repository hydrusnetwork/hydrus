import collections
import ClientConstants as CC
import HydrusConstants as HC
import HydrusGlobals as HG
import HydrusTags
import os
import random
import threading
import weakref
import HydrusData
import HydrusThreading
import wx

DB_DIR = None

tiniest_gif = '\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\xFF\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00\x3B'

LOCAL_RATING_LIKE_SERVICE_KEY = HydrusData.GenerateKey()
LOCAL_RATING_NUMERICAL_SERVICE_KEY = HydrusData.GenerateKey()

def ConvertServiceKeysToContentUpdatesToComparable( service_keys_to_content_updates ):
    
    comparable_dict = {}
    
    for ( service_key, content_updates ) in service_keys_to_content_updates.items():
        
        comparable_dict[ service_key ] = set( content_updates )
        
    
    return comparable_dict
    
class MockController( object ):
    
    def __init__( self ):
        
        self.model_is_shutdown = False
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        return HG.test_controller.CallToThread( callable, *args, **kwargs )
        
    
    def ModelIsShutdown( self ):
        
        return self.model_is_shutdown or HG.test_controller.ModelIsShutdown()
        
    
class FakeHTTPConnectionManager():
    
    def __init__( self ):
        
        self._fake_responses = {}
        
    
    def Request( self, method, url, request_headers = None, body = '', return_cookies = False, report_hooks = None, temp_path = None, hydrus_network = False ):
        
        if request_headers is None: request_headers = {}
        if report_hooks is None: report_hooks = []
        
        ( response, size_of_response, response_headers, cookies ) = self._fake_responses[ ( method, url ) ]
        
        if temp_path is not None:
            
            with open( temp_path, 'wb' ) as f: f.write( response )
            
            response = 'path written to temporary path'
            
        
        if hydrus_network: return ( response, size_of_response, response_headers, cookies )
        elif return_cookies: return ( response, cookies )
        else: return response
        
    
    def RequestHydrus( self, method, url, request_headers = None, body = '', report_hooks = None, temp_path = None ):
        
        pass
        
    
    def SetResponse( self, method, url, response, size_of_response = 100, response_headers = None, cookies = None ):
        
        if response_headers is None: response_headers = {}
        if cookies is None: cookies = []
        
        self._fake_responses[ ( method, url ) ] = ( response, size_of_response, response_headers, cookies )
        
    
class FakeWebSessionManager():
    
    def EnsureLoggedIn( self, name ):
        
        pass
        
    
    def GetCookies( self, *args, **kwargs ):
        
        return { 'session_cookie' : 'blah' }
        
    
class TestFrame( wx.Frame ):
    
    def __init__( self ):
        
        wx.Frame.__init__( self, None )
        
    
    def SetPanel( self, panel ):
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Fit()
        
        self.Show()
        
    
