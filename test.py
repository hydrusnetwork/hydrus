from include import ClientConstants as CC
from include import HydrusConstants as HC
from include import HydrusSessions
from include import HydrusTags
from include import TestClientConstants
from include import TestClientDaemons
from include import TestConstants
from include import TestDialogs
from include import TestDB
from include import TestFunctions
from include import TestHydrusDownloading
from include import TestHydrusEncryption
from include import TestHydrusServer
from include import TestHydrusSessions
from include import TestHydrusTags
import collections
import os
import sys
import threading
import unittest
import wx
from twisted.internet import reactor

only_run = None

class App( wx.App ):
    
    def OnInit( self ):
        
        HC.app = self
        
        self._reads = {}
        
        self._reads[ 'hydrus_sessions' ] = []
        self._reads[ 'messaging_sessions' ] = []
        self._reads[ 'namespace_blacklists' ] = []
        self._reads[ 'options' ] = CC.CLIENT_DEFAULT_OPTIONS
        self._reads[ 'sessions' ] = []
        self._reads[ 'tag_parents' ] = {}
        self._reads[ 'tag_service_precedence' ] = []
        self._reads[ 'tag_siblings' ] = {}
        self._reads[ 'web_sessions' ] = {}
        
        HC.options = CC.CLIENT_DEFAULT_OPTIONS
        
        self._writes = collections.defaultdict( list )
        
        self._managers = {}
        
        self._managers[ 'hydrus_sessions' ] = HydrusSessions.HydrusSessionManagerClient()
        self._managers[ 'namespace_blacklists' ] = HydrusTags.NamespaceBlacklistsManager()
        self._managers[ 'tag_parents' ] = HydrusTags.TagParentsManager()
        self._managers[ 'tag_siblings' ] = HydrusTags.TagSiblingsManager()
        self._managers[ 'undo' ] = CC.UndoManager()
        self._managers[ 'web_sessions' ] = HydrusSessions.WebSessionManagerClient()
        
        self._managers[ 'restricted_services_sessions' ] = HydrusSessions.HydrusSessionManagerServer()
        self._managers[ 'messaging_sessions' ] = HydrusSessions.HydrusMessagingSessionManagerServer()
        
        self._cookies = {}
        
        suites = []
        
        if only_run is None: run_all = True
        else: run_all = False
        
        if run_all or only_run == 'cc': suites.append( unittest.TestLoader().loadTestsFromModule( TestClientConstants ) )
        if run_all or only_run == 'daemons': suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDaemons ) )
        if run_all or only_run == 'dialogs': suites.append( unittest.TestLoader().loadTestsFromModule( TestDialogs ) )
        if run_all or only_run == 'db': suites.append( unittest.TestLoader().loadTestsFromModule( TestDB ) )
        if run_all or only_run == 'encryption': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusEncryption ) )
        if run_all or only_run == 'functions': suites.append( unittest.TestLoader().loadTestsFromModule( TestFunctions ) )
        if run_all or only_run == 'downloading': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusDownloading ) )
        if run_all or only_run == 'server': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusServer ) )
        if run_all or only_run == 'sessions': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusSessions ) )
        if run_all or only_run == 'tags': suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusTags ) )
        
        suite = unittest.TestSuite( suites )
        
        if run_all or only_run == 'server':
            
            threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
            
        
        runner = unittest.TextTestRunner( verbosity = 1 )
        
        runner.run( suite )
        
        if run_all or only_run == 'server':
            
            reactor.callFromThread( reactor.stop )
            
        
        return True
        
    
    def GetManager( self, type ): return self._managers[ type ]
    
    def GetWebCookies( self, name ): return self._cookies[ name ]
    
    def GetWrite( self, name ):
        
        write = self._writes[ name ]
        
        del self._writes[ name ]
        
        return write
        
    
    def Read( self, name, *args, **kwargs ): return self._reads[ name ]
    
    def ReadDaemon( self, name, *args, **kwargs ): return self.Read( name )
    
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
            else: return ( 'successful', 'hash' )
        
    
if __name__ == '__main__':
    
    args = sys.argv[1:]
    
    if len( args ) > 0:
        
        only_run = args[0]
        
    else: only_run = None
    
    app = App()
    
    raw_input()
    
    HC.shutdown = True
    
    HC.pubsub.WXpubimmediate( 'shutdown' )
