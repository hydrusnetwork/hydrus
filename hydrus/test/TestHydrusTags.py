import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusTags
from hydrus.core import HydrusGlobals as HG

class TestHydrusTags( unittest.TestCase ):
    
    def test_cleaning_and_combining( self ):
        
        self.assertEqual( HydrusTags.CleanTag( ' test ' ), 'test' )
        self.assertEqual( HydrusTags.CleanTag( ' character:test ' ), 'character:test' )
        self.assertEqual( HydrusTags.CleanTag( ' character : test ' ), 'character:test' )
        
        self.assertEqual( HydrusTags.CleanTag( ':p' ), '::p' )
        
        self.assertEqual( HydrusTags.CombineTag( '', ':p' ), '::p' )
        self.assertEqual( HydrusTags.CombineTag( '', '::p' ), ':::p' )
        
        self.assertEqual( HydrusTags.CombineTag( '', 'unnamespace:withcolon' ), ':unnamespace:withcolon' )
        
    
