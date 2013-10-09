from include import ClientConstants as CC
from include import HydrusConstants as HC
from include import HydrusTags
from include import TestClientConstants
from include import TestClientDaemons
from include import TestConstants
from include import TestDialogs
from include import TestDB
from include import TestFunctions
from include import TestHydrusDownloading
from include import TestServer
from include import TestHydrusTags
import collections
import os
import unittest
import wx

class App( wx.App ):
    
    def OnInit( self ):
        
        HC.app = self
        
        self._reads = {}
        
        self._reads[ 'options' ] = CC.CLIENT_DEFAULT_OPTIONS
        self._reads[ 'namespace_blacklists' ] = []
        self._reads[ 'tag_parents' ] = {}
        self._reads[ 'tag_service_precedence' ] = []
        self._reads[ 'tag_siblings' ] = {}
        
        HC.options = CC.CLIENT_DEFAULT_OPTIONS
        
        self._writes = collections.defaultdict( list )
        
        self._namespace_blacklists_manager = HydrusTags.NamespaceBlacklistsManager()
        self._tag_parents_manager = HydrusTags.TagParentsManager()
        self._tag_siblings_manager = HydrusTags.TagSiblingsManager()
        
        self._cookies = {}
        
        suites = []
        
        suites.append( unittest.TestLoader().loadTestsFromModule( TestClientConstants ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDaemons ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestDialogs ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestDB ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestFunctions ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusDownloading ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestServer ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusTags ) )
        
        suite = unittest.TestSuite( suites )
        
        runner = unittest.TextTestRunner( verbosity = 1 )
        
        runner.run( suite )
        
        return True
        
    
    def GetNamespaceBlacklistsManager( self ): return self._namespace_blacklists_manager
    def GetTagParentsManager( self ): return self._tag_parents_manager
    def GetTagSiblingsManager( self ): return self._tag_siblings_manager
    
    def GetWebCookies( self, name ): return self._cookies[ name ]
    
    def GetWrite( self, name ):
        
        write = self._writes[ name ]
        
        del self._writes[ name ]
        
        return write
        
    
    def Read( self, name ): return self._reads[ name ]
    
    def ReadDaemon( self, name ): return self.Read( name )
    
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
    
    app = App()
    
    raw_input()
    
    HC.shutdown = True
    
    HC.pubsub.pubimmediate( 'shutdown' )
