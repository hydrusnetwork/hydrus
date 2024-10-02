import unittest

from hydrus.core import HydrusTags
from hydrus.core import HydrusText

class TestHydrusTags( unittest.TestCase ):
    
    def test_cleaning_and_combining( self ):
        
        self.assertEqual( HydrusTags.CleanTag( ' test ' ), 'test' )
        self.assertEqual( HydrusTags.CleanTag( ' character:test ' ), 'character:test' )
        self.assertEqual( HydrusTags.CleanTag( ' character : test ' ), 'character:test' )
        
        self.assertEqual( HydrusTags.CleanTag( ':p' ), '::p' )
        
        self.assertEqual( HydrusTags.CombineTag( '', ':p' ), '::p' )
        self.assertEqual( HydrusTags.CombineTag( '', '::p' ), ':::p' )
        
        self.assertEqual( HydrusTags.CombineTag( '', 'unnamespace:withcolon' ), ':unnamespace:withcolon' )
        
        # note this is a dangerous string bro and the debugger will freak out if you inspect it
        self.assertEqual( HydrusText.CleanseImportText( 'test \ud83d\ude1c' ), 'test \U0001f61c' )
        
    
