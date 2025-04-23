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
        
    
    def test_latin_ok( self ):
        
        self.assertEqual( HydrusTags.CleanTag( 'Hello world!(){}[]*/-+' ), 'hello world!(){}[]*/-+' )
        
        self.assertEqual( HydrusTags.CleanTag( 'naïve Déjà vu' ), 'naïve déjà vu' )
        
    
    def test_latin_ok_zwj_zwnj( self ):
        
        self.assertEqual( HydrusTags.CleanTag( 'Hello world!\u200C(){}\u200D[]*/-+' ), 'hello world!(){}[]*/-+' )
        
        self.assertEqual( HydrusTags.CleanTag( 'naï\u200Cve Déjà \u200Dvu' ), 'naïve déjà vu' )
        
        self.assertEqual( HydrusTags.CleanTag( ' \u200C\u200D ' ), '' )
        
    
    def test_control_garbage( self ):
        
        self.assertEqual( HydrusTags.CleanTag( 't\u0000est' ), 'test' )
        self.assertEqual( HydrusTags.CleanTag( 't\u0001est' ), 'test' )
        self.assertEqual( HydrusTags.CleanTag( 't\u009Fest' ), 'test' )
        self.assertEqual( HydrusTags.CleanTag( 't\nest' ), 'test' )
        self.assertEqual( HydrusTags.CleanTag( 't\test' ), 'test' )
        self.assertEqual( HydrusTags.CleanTag( 't\rest' ), 'test' )
        
    
    def test_format_stuff( self ):
        
        self.assertEqual( HydrusTags.CleanTag( 't\u200De\u200Cs\u200Bt\u200E' ), 'test' )
        
    
    def test_private_and_surrogates( self ):
        
        self.assertEqual( HydrusTags.CleanTag( 't\uE000e\U000F0000s\uD834t' ), 'test' )
        
    
    def test_emoji_ZWJ( self ):
        
        # this makes 'family' through the magical power of 'graphemes', which are not codepoints
        self.assertEqual( HydrusTags.CleanTag( '👨\u200D👩\u200D👦\u200D👧' ), '👨\u200D👩\u200D👦\u200D👧' )
        
    
    def test_hangul_detection( self ):
        
        self.assertEqual( HydrusTags.CleanTag( 'test\u3164' ), 'test' )
        self.assertEqual( HydrusTags.CleanTag( 'te:s:t\u3164' ), 'te:s:t' )
        self.assertEqual( HydrusTags.CleanTag( '한글\u3164' ), '한글\u3164' )
        
    
    def test_surrogate_garbage( self ):
        
        # note this is a dangerous string bro and the debugger will freak out if you inspect it
        self.assertEqual( HydrusText.CleanseImportText( 'test \ud83d\ude1c' ), 'test \U0001f61c' )
        
    
