from include import HydrusConstants as HC
from include import HydrusTags
from include import TestConstants
from include import TestDialogs
from include import TestDB
from include import TestFunctions
from include import TestHydrusTags
import os
import unittest
import wx

class App( wx.App ):
    
    def OnInit( self ):
        
        HC.app = self
        
        self._reads = {}
        
        self._reads[ 'options' ] = {}
        self._reads[ 'tag_parents' ] = {}
        self._reads[ 'tag_service_precedence' ] = []
        self._reads[ 'tag_siblings' ] = {}
        
        self._tag_parents_manager = HydrusTags.TagParentsManager()
        self._tag_siblings_manager = HydrusTags.TagSiblingsManager()
        
        suites = []
        
        suites.append( unittest.TestLoader().loadTestsFromModule( TestDialogs ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestDB ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestFunctions ) )
        suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusTags ) )
        
        suite = unittest.TestSuite( suites )
        
        runner = unittest.TextTestRunner( verbosity = 1 )
        
        runner.run( suite )
        
        return True
        
    
    def GetTagParentsManager( self ): return self._tag_parents_manager
    def GetTagSiblingsManager( self ): return self._tag_siblings_manager
    
    def Read( self, name ): return self._reads[ name ]
    
    def SetRead( self, name, value ): self._reads[ name ] = value
    
if __name__ == '__main__':
    
    app = App()
    
    raw_input()
    