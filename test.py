#!/usr/bin/env python2

import locale

try: locale.setlocale( locale.LC_ALL, '' )
except: pass

from include import HydrusConstants as HC
from include import ClientConstants as CC
from include import HydrusGlobals
from include import ClientDefaults
from include import ClientNetworking
from include import ClientServices
from include import HydrusPubSub
from include import HydrusSessions
from include import HydrusTags
from include import HydrusThreading
from include import TestClientConstants
from include import TestClientDaemons
from include import TestClientDownloading
from include import TestClientListBoxes
from include import TestConstants
from include import TestDialogs
from include import TestDB
from include import TestFunctions
from include import TestClientImageHandling
from include import TestHydrusNATPunch
from include import TestHydrusSerialisable
from include import TestHydrusServer
from include import TestHydrusSessions
from include import TestHydrusTags
import collections
import os
import random
import shutil
import sys
import tempfile
import threading
import time
import unittest
import wx
from twisted.internet import reactor
from include import ClientCaches
from include import ClientData
from include import HydrusData
from include import HydrusPaths

only_run = None

class Controller( object ):
    
    def __init__( self ):
        
        self._db_dir = tempfile.mkdtemp()
        
        TestConstants.DB_DIR = self._db_dir
        
        self._server_files_dir = os.path.join( self._db_dir, 'server_files' )
        self._updates_dir = os.path.join( self._db_dir, 'test_updates' )
        
        client_files_default = os.path.join( self._db_dir, 'client_files' )
        
        HydrusPaths.MakeSureDirectoryExists( self._server_files_dir )
        HydrusPaths.MakeSureDirectoryExists( self._updates_dir )
        HydrusPaths.MakeSureDirectoryExists( client_files_default )
        
        HydrusGlobals.controller = self
        HydrusGlobals.client_controller = self
        HydrusGlobals.server_controller = self
        HydrusGlobals.test_controller = self
        
        self._pubsub = HydrusPubSub.HydrusPubSub( self )
        
        self._new_options = ClientData.ClientOptions( self._db_dir )
        
        def show_text( text ): pass
        
        HydrusData.ShowText = show_text
        
        self._http = ClientNetworking.HTTPConnectionManager()
        
        self._call_to_threads = []
        
        self._reads = {}
        
        self._reads[ 'hydrus_sessions' ] = []
        self._reads[ 'local_booru_share_keys' ] = []
        self._reads[ 'messaging_sessions' ] = []
        self._reads[ 'tag_censorship' ] = []
        self._reads[ 'options' ] = ClientDefaults.GetClientDefaultOptions()
        
        services = []
        
        services.append( ClientServices.GenerateService( CC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, CC.LOCAL_BOORU_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HC.COMBINED_LOCAL_FILE, CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( CC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE_DOMAIN, CC.LOCAL_FILE_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( CC.TRASH_SERVICE_KEY, HC.LOCAL_FILE_TRASH_DOMAIN, CC.LOCAL_FILE_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( CC.LOCAL_TAG_SERVICE_KEY, HC.LOCAL_TAG, CC.LOCAL_TAG_SERVICE_KEY ) )
        
        self._reads[ 'services' ] = services
        
        client_files_locations = {}
        
        for prefix in HydrusData.IterateHexPrefixes():
            
            for c in ( 'f', 't', 'r' ):
                
                client_files_locations[ c + prefix ] = client_files_default
                
            
        
        self._reads[ 'client_files_locations' ] = client_files_locations
        
        self._reads[ 'sessions' ] = []
        self._reads[ 'tag_parents' ] = {}
        self._reads[ 'tag_siblings' ] = {}
        self._reads[ 'web_sessions' ] = {}
        
        HC.options = ClientDefaults.GetClientDefaultOptions()
        
        self._writes = collections.defaultdict( list )
        
        self._managers = {}
        
        self._services_manager = ClientCaches.ServicesManager( self )
        self._client_files_manager = ClientCaches.ClientFilesManager( self )
        self._client_session_manager = ClientCaches.HydrusSessionManager( self )
        
        self._managers[ 'tag_censorship' ] = ClientCaches.TagCensorshipManager( self )
        self._managers[ 'tag_siblings' ] = ClientCaches.TagSiblingsManager( self )
        self._managers[ 'tag_parents' ] = ClientCaches.TagParentsManager( self )
        self._managers[ 'undo' ] = ClientCaches.UndoManager( self )
        self._managers[ 'web_sessions' ] = TestConstants.FakeWebSessionManager()
        self._server_session_manager = HydrusSessions.HydrusSessionManagerServer()
        self._managers[ 'local_booru' ] = ClientCaches.LocalBooruCache( self )
        
        self._cookies = {}
        
    
    def _GetCallToThread( self ):
        
        for call_to_thread in self._call_to_threads:
            
            if not call_to_thread.CurrentlyWorking():
                
                return call_to_thread
                
            
        
        if len( self._call_to_threads ) > 100:
            
            raise Exception( 'Too many call to threads!' )
            
        
        call_to_thread = HydrusThreading.THREADCallToThread( self )
        
        self._call_to_threads.append( call_to_thread )
        
        call_to_thread.start()
        
        return call_to_thread
        
    
    def _SetupWx( self ):
        
        self.locale = wx.Locale( wx.LANGUAGE_DEFAULT ) # Very important to init this here and keep it non garbage collected
        
        CC.GlobalBMPs.STATICInitialise()
        
    
    def pub( self, topic, *args, **kwargs ):
        
        pass
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        self._pubsub.pubimmediate( topic, *args, **kwargs )
        
    
    def sub( self, object, method_name, topic ):
        
        self._pubsub.sub( object, method_name, topic )
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        call_to_thread = self._GetCallToThread()
        
        call_to_thread.put( callable, *args, **kwargs )
        
    
    def DoHTTP( self, *args, **kwargs ): return self._http.Request( *args, **kwargs )
    
    def GetClientFilesManager( self ):
        
        return self._client_files_manager
        
    
    def GetClientSessionManager( self ):
        
        return self._client_session_manager
        
    
    def GetFilesDir( self ):
        
        return self._server_files_dir
        
    
    def GetHTTP( self ): return self._http
    
    def GetNewOptions( self ):
        
        return self._new_options
        
    
    def GetOptions( self ):
        
        return HC.options
        
    
    def GetManager( self, manager_type ): return self._managers[ manager_type ]
    
    def GetServicesManager( self ):
        
        return self._services_manager
        
    
    def GetServerSessionManager( self ):
        
        return self._server_session_manager
        
    
    def GetWrite( self, name ):
        
        write = self._writes[ name ]
        
        del self._writes[ name ]
        
        return write
        
    
    def IsFirstStart( self ):
        
        return True
        
    
    def ModelIsShutdown( self ):
        
        return HydrusGlobals.model_shutdown
        
    
    def Read( self, name, *args, **kwargs ):
        
        return self._reads[ name ]
        
    
    def RequestMade( self, num_bytes ):
        
        pass
        
    
    def ResetIdleTimer( self ): pass
    
    def Run( self ):
        
        self._SetupWx()
        
        suites = []
        
        if only_run is None: run_all = True
        else: run_all = False
        
        if run_all or only_run == 'daemons': suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDaemons ) )
        if run_all or only_run == 'data':
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientConstants ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestFunctions ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusSerialisable ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusSessions ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusTags ) )
        if run_all or only_run == 'db': suites.append( unittest.TestLoader().loadTestsFromModule( TestDB ) )
        if run_all or only_run == 'downloading': suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDownloading ) )
        if run_all or only_run == 'gui':
            suites.append( unittest.TestLoader().loadTestsFromModule( TestDialogs ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientListBoxes ) )
        if run_all or only_run == 'image': suites.append( unittest.TestLoader().loadTestsFromModule( TestClientImageHandling ) )
        if run_all or only_run == 'nat': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusNATPunch ) )
        if run_all or only_run == 'server': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusServer ) )
        
        suite = unittest.TestSuite( suites )
        
        runner = unittest.TextTestRunner( verbosity = 1 )
        
        runner.run( suite )
        
    
    def SetHTTP( self, http ): self._http = http
    
    def SetRead( self, name, value ): self._reads[ name ] = value
    
    def SetWebCookies( self, name, value ): self._cookies[ name ] = value
    
    def TidyUp( self ):
        
        time.sleep( 2 )
        
        HydrusPaths.DeletePath( self._db_dir )
        
    
    def ViewIsShutdown( self ):
        
        return HydrusGlobals.view_shutdown
        
    
    def Write( self, name, *args, **kwargs ):
        
        self._writes[ name ].append( ( args, kwargs ) )
        
    
    def WriteSynchronous( self, name, *args, **kwargs ):
        
        self._writes[ name ].append( ( args, kwargs ) )
        
        if name == 'import_file':
            
            ( path, ) = args
            
            with open( path, 'rb' ) as f: file = f.read()
            
            if file == 'blarg': raise Exception( 'File failed to import for some reason!' )
            else: return ( CC.STATUS_SUCCESSFUL, '0123456789abcdef'.decode( 'hex' ) )
            
        
    
if __name__ == '__main__':
    
    args = sys.argv[1:]
    
    if len( args ) > 0:
        
        only_run = args[0]
        
    else: only_run = None
    
    try:
        
        threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
        
        app = wx.App()
        
        controller = Controller()
        
        try:
            
            win = wx.Frame( None )
            
            def do_it():
                
                controller.Run()
                
                win.Destroy()
                
            
            wx.CallAfter( do_it )
            app.MainLoop()
            
        except:
            
            import traceback
            
            HydrusData.DebugPrint( traceback.format_exc() )
            
        finally:
            
            HydrusGlobals.view_shutdown = True
            
            controller.pubimmediate( 'wake_daemons' )
            
            HydrusGlobals.model_shutdown = True
            
            controller.pubimmediate( 'wake_daemons' )
            
            controller.TidyUp()
            
        
    except:
        
        import traceback
        
        HydrusData.DebugPrint( traceback.format_exc() )
        
    finally:
        
        reactor.callFromThread( reactor.stop )
        
        print( 'This was version ' + str( HC.SOFTWARE_VERSION ) )
        
        raw_input()
        
