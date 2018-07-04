import collections
import ClientConstants as CC
import ClientOptions
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
        
        self.new_options = ClientOptions.ClientOptions()
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        return HG.test_controller.CallToThread( callable, *args, **kwargs )
        
    
    def JustWokeFromSleep( self ):
        
        return False
        
    
    def ModelIsShutdown( self ):
        
        return self.model_is_shutdown or HG.test_controller.ModelIsShutdown()
        
    
class MockServicesManager( object ):
    
    def __init__( self, services ):
        
        self._service_keys_to_services = { service.GetServiceKey() : service for service in services }
        
    
    def GetName( self, service_key ):
        
        return self._service_keys_to_services[ service_key ].GetName()
        
    
    def GetService( self, service_key ):
        
        return self._service_keys_to_services[ service_key ]
        
    
    def ServiceExists( self, service_key ):
        
        return service_key in self._service_keys_to_services
        
    
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
        
        vbox.Add( panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Fit()
        
        self.Show()
        
    
