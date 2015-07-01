import locale

try: locale.setlocale( locale.LC_ALL, '' )
except: pass

from include import HydrusConstants as HC
from include import ClientConstants as CC
from include import HydrusGlobals
from include import ClientDefaults
from include import HydrusNetworking
from include import HydrusSessions
from include import HydrusTags
from include import TestClientConstants
from include import TestClientDaemons
from include import TestClientDownloading
from include import TestConstants
from include import TestDialogs
from include import TestDB
from include import TestFunctions
from include import TestHydrusEncryption
from include import TestHydrusImageHandling
from include import TestHydrusNATPunch
from include import TestHydrusServer
from include import TestHydrusSessions
from include import TestHydrusTags
import collections
import os
import sys
import threading
import time
import unittest
import wx
from twisted.internet import reactor
from include import ClientCaches
from include import ClientData
from include import HydrusData

only_run = None

class App( wx.App ):
    
    def OnInit( self ):
        
        def show_text( text ): pass
        
        HydrusData.ShowText = show_text
        
        self._http = HydrusNetworking.HTTPConnectionManager()
        
        self._reads = {}
        
        self._reads[ 'hydrus_sessions' ] = []
        self._reads[ 'local_booru_share_keys' ] = []
        self._reads[ 'messaging_sessions' ] = []
        self._reads[ 'tag_censorship' ] = []
        self._reads[ 'options' ] = ClientDefaults.GetClientDefaultOptions()
        
        services = []
        services.append( ClientData.Service( CC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, CC.LOCAL_BOORU_SERVICE_KEY, { 'max_monthly_data' : None, 'used_monthly_data' : 0 } ) )
        services.append( ClientData.Service( CC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE, CC.LOCAL_FILE_SERVICE_KEY, {} ) )
        services.append( ClientData.Service( CC.LOCAL_TAG_SERVICE_KEY, HC.LOCAL_TAG, CC.LOCAL_TAG_SERVICE_KEY, {} ) )
        self._reads[ 'services' ] = services
        
        self._reads[ 'sessions' ] = []
        self._reads[ 'tag_parents' ] = {}
        self._reads[ 'tag_siblings' ] = {}
        self._reads[ 'web_sessions' ] = {}
        
        HC.options = ClientDefaults.GetClientDefaultOptions()
        HydrusGlobals.pubsub = TestConstants.FakePubSub()
        
        self._writes = collections.defaultdict( list )
        
        self._managers = {}
        
        self._services_manager = ClientData.ServicesManager()
        
        self._managers[ 'hydrus_sessions' ] = HydrusSessions.HydrusSessionManagerClient()
        self._managers[ 'tag_censorship' ] = HydrusTags.TagCensorshipManager()
        self._managers[ 'tag_siblings' ] = HydrusTags.TagSiblingsManager()
        self._managers[ 'tag_parents' ] = HydrusTags.TagParentsManager()
        self._managers[ 'undo' ] = ClientData.UndoManager()
        self._managers[ 'web_sessions' ] = TestConstants.FakeWebSessionManager()
        self._managers[ 'restricted_services_sessions' ] = HydrusSessions.HydrusSessionManagerServer()
        self._managers[ 'messaging_sessions' ] = HydrusSessions.HydrusMessagingSessionManagerServer()
        self._managers[ 'local_booru' ] = ClientCaches.LocalBooruCache()
        
        self._cookies = {}
        
        suites = []
        
        if only_run is None: run_all = True
        else: run_all = False
        
        if run_all or only_run == 'cc': suites.append( unittest.TestLoader().loadTestsFromModule( TestClientConstants ) )
        if run_all or only_run == 'daemons': suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDaemons ) )
        if run_all or only_run == 'dialogs': suites.append( unittest.TestLoader().loadTestsFromModule( TestDialogs ) )
        if run_all or only_run == 'db': suites.append( unittest.TestLoader().loadTestsFromModule( TestDB ) )
        if run_all or only_run == 'downloading': suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDownloading ) )
        if run_all or only_run == 'encryption': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusEncryption ) )
        if run_all or only_run == 'functions': suites.append( unittest.TestLoader().loadTestsFromModule( TestFunctions ) )
        if run_all or only_run == 'image': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusImageHandling ) )
        if run_all or only_run == 'nat': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusNATPunch ) )
        if run_all or only_run == 'server': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusServer ) )
        if run_all or only_run == 'sessions': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusSessions ) )
        if run_all or only_run == 'tags': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusTags ) )
        
        suite = unittest.TestSuite( suites )
        
        threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
        
        runner = unittest.TextTestRunner( verbosity = 1 )
        
        runner.run( suite )
        
        reactor.callFromThread( reactor.stop )
        
        return True
        
    
    def DoHTTP( self, *args, **kwargs ): return self._http.Request( *args, **kwargs )
    
    def GetHTTP( self ): return self._http
    
    def GetOptions( self ):
        
        return HC.options
        
    
    def GetManager( self, manager_type ): return self._managers[ manager_type ]
    
    def GetServicesManager( self ):
        
        return self._services_manager
        
    
    def GetWrite( self, name ):
        
        write = self._writes[ name ]
        
        del self._writes[ name ]
        
        return write
        
    
    def Read( self, name, *args, **kwargs ): return self._reads[ name ]
    
    def ResetIdleTimer( self ): pass
    
    def SetHTTP( self, http ): self._http = http
    
    def SetRead( self, name, value ): self._reads[ name ] = value
    
    def SetWebCookies( self, name, value ): self._cookies[ name ] = value
    
    def Write( self, name, *args, **kwargs ):
        
        self._writes[ name ].append( ( args, kwargs ) )
        
    
    def WriteSynchronous( self, name, *args, **kwargs ):
        
        self._writes[ name ].append( ( args, kwargs ) )
        
        if name == 'import_file':
            
            ( path, ) = args
            
            with open( path, 'rb' ) as f: file = f.read()
            
            if file == 'blarg': raise Exception( 'File failed to import for some reason!' )
            else: return ( CC.STATUS_SUCCESSFUL, 'hash' )
        
    
if __name__ == '__main__':
    
    args = sys.argv[1:]
    
    if len( args ) > 0:
        
        only_run = args[0]
        
    else: only_run = None
    
    old_pubsub = HydrusGlobals.pubsub
    
    app = App()
    
    HydrusGlobals.shutdown = True
    
    HydrusGlobals.pubsub.WXpubimmediate( 'shutdown' )
    
    old_pubsub.WXpubimmediate( 'shutdown' )
    
    raw_input()