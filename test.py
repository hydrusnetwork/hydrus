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
import unittest
import wx

only_run = None

class App( wx.App ):
    
    def OnInit( self ):
        
        HC.app = self
        
        self._reads = {}
        
        self._reads[ 'options' ] = CC.CLIENT_DEFAULT_OPTIONS
        self._reads[ 'namespace_blacklists' ] = []
        self._reads[ 'tag_parents' ] = {}
        self._reads[ 'tag_service_precedence' ] = []
        self._reads[ 'tag_siblings' ] = {}
        self._reads[ 'hydrus_sessions' ] = []
        self._reads[ 'sessions' ] = []
        
        HC.options = CC.CLIENT_DEFAULT_OPTIONS
        
        self._writes = collections.defaultdict( list )
        
        self._namespace_blacklists_manager = HydrusTags.NamespaceBlacklistsManager()
        self._tag_parents_manager = HydrusTags.TagParentsManager()
        self._tag_siblings_manager = HydrusTags.TagSiblingsManager()
        
        self._client_session_manager = HydrusSessions.HydrusSessionManagerClient()
        self._server_session_manager = HydrusSessions.HydrusSessionManagerServer()
        
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
        
        runner = unittest.TextTestRunner( verbosity = 1 )
        
        runner.run( suite )
        
        return True
        
    
    def GetNamespaceBlacklistsManager( self ): return self._namespace_blacklists_manager
    
    def GetSessionKey( self, service_identifier ): return self._client_session_manager.GetSessionKey( service_identifier )
    
    def GetSessionManager( self ): return self._server_session_manager
    
    def GetTagParentsManager( self ): return self._tag_parents_manager
    def GetTagSiblingsManager( self ): return self._tag_siblings_manager
    
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
