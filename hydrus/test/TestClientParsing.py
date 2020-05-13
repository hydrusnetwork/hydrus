from hydrus.core import HydrusConstants as HC
from hydrus.client import ClientParsing
import unittest

class TestStringConverter( unittest.TestCase ):
    
    def test_basics( self ):
        
        transformations = []
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_BEGINNING, 1 ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '123456789' )
        
        #
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_REMOVE_TEXT_FROM_END, 1 ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '12345678' )
        
        #
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_BEGINNING, 7 ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '1234567' )
        
        #
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_CLIP_TEXT_FROM_END, 6 ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '234567' )
        
        #
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_PREPEND_TEXT, 'abc' ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567' )
        
        #
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT, 'x z' ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567x z' )
        
        #
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_ENCODE, 'url percent encoding' ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567x%20z' )
        
        #
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_DECODE, 'url percent encoding' ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567x z' )
        
        #
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_REVERSE, None ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'z x765432cba' )
        
        #
        
        transformations.append( ( ClientParsing.STRING_TRANSFORMATION_REGEX_SUB, ( '\\d', 'd' ) ) )
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'z xddddddcba' )
        
        #
        
        transformations = [ ( ClientParsing.STRING_TRANSFORMATION_DATE_DECODE, ( '%Y-%m-%d %H:%M:%S', HC.TIMEZONE_GMT, 0 ) ) ]
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '1970-01-02 00:00:00' ), '86400' )
        
        #
        
        transformations = [ ( ClientParsing.STRING_TRANSFORMATION_DATE_ENCODE, ( '%Y-%m-%d %H:%M:%S', 0 ) ) ]
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '86400' ), '1970-01-02 00:00:00' )
        
        #
        
        transformations = [ ( ClientParsing.STRING_TRANSFORMATION_INTEGER_ADDITION, 5 ) ]
        
        string_converter = ClientParsing.StringConverter( transformations = transformations )
        
        self.assertEqual( string_converter.Convert( '4' ), '9' )
        
    
class TestStringMatch( unittest.TestCase ):
    
    def test_basics( self ):
        
        all_string_match = ClientParsing.StringMatch()
        
        self.assertTrue( all_string_match.Matches( '123' ) )
        self.assertTrue( all_string_match.Matches( 'abc' ) )
        self.assertTrue( all_string_match.Matches( 'abc123' ) )
        
        #
        
        min_string_match = ClientParsing.StringMatch( min_chars = 4 )
        
        self.assertFalse( min_string_match.Matches( '123' ) )
        self.assertFalse( min_string_match.Matches( 'abc' ) )
        self.assertTrue( min_string_match.Matches( 'abc123' ) )
        
        #
        
        max_string_match = ClientParsing.StringMatch( max_chars = 4 )
        
        self.assertTrue( max_string_match.Matches( '123' ) )
        self.assertTrue( max_string_match.Matches( 'abc' ) )
        self.assertFalse( max_string_match.Matches( 'abc123' ) )
        
        #
        
        min_max_string_match = ClientParsing.StringMatch( min_chars = 4, max_chars = 10 )
        
        self.assertFalse( min_max_string_match.Matches( '123' ) )
        self.assertFalse( min_max_string_match.Matches( 'abc' ) )
        self.assertTrue( min_max_string_match.Matches( 'abc123' ) )
        
        #
        
        alpha_string_match = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.ALPHA )
        
        self.assertFalse( alpha_string_match.Matches( '123' ) )
        self.assertTrue( alpha_string_match.Matches( 'abc' ) )
        self.assertFalse( alpha_string_match.Matches( 'abc123' ) )
        
        #
        
        alphanum_string_match = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.ALPHANUMERIC )
        
        self.assertTrue( alphanum_string_match.Matches( '123' ) )
        self.assertTrue( alphanum_string_match.Matches( 'abc' ) )
        self.assertTrue( alphanum_string_match.Matches( 'abc123' ) )
        
        #
        
        num_string_match = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC )
        
        self.assertTrue( num_string_match.Matches( '123' ) )
        self.assertFalse( num_string_match.Matches( 'abc' ) )
        self.assertFalse( num_string_match.Matches( 'abc123' ) )
        
        #
        
        fixed_string_match = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FIXED, match_value = '123' )
        
        self.assertTrue( fixed_string_match.Matches( '123' ) )
        self.assertFalse( fixed_string_match.Matches( 'abc' ) )
        self.assertFalse( fixed_string_match.Matches( 'abc123' ) )
        
        #
        
        re_string_match = ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_REGEX, match_value = '\\d' )
        
        self.assertTrue( re_string_match.Matches( '123' ) )
        self.assertFalse( re_string_match.Matches( 'abc' ) )
        self.assertTrue( re_string_match.Matches( 'abc123' ) )
        
    
class TestStringSplitter( unittest.TestCase ):
    
    def test_basics( self ):
        
        splitter = ClientParsing.StringSplitter( separator = ', ' )
        
        self.assertTrue( splitter.Split( '123' ), [ '123' ] )
        self.assertTrue( splitter.Split( '1,2,3' ), [ '1,2,3' ] )
        self.assertTrue( splitter.Split( '1, 2, 3' ), [ '1', '2', '3' ] )
        
        splitter = ClientParsing.StringSplitter( separator = ', ', max_splits = 2 )
        
        self.assertTrue( splitter.Split( '123' ), [ '123' ] )
        self.assertTrue( splitter.Split( '1,2,3' ), [ '1,2,3' ] )
        self.assertTrue( splitter.Split( '1, 2, 3, 4' ), [ '1', '2', '3,4' ] )
        
    

class TestStringProcessor( unittest.TestCase ):
    
    def test_basics( self ):
        
        processor = ClientParsing.StringProcessor()
        
        self.assertEqual( processor.ProcessStrings( [] ), [] )
        self.assertEqual( processor.ProcessStrings( [ 'test' ] ), [ 'test' ] )
        self.assertEqual( processor.ProcessStrings( [ 'test', 'test', '', 'test2' ] ), [ 'test', 'test', '', 'test2' ] )
        
        processing_steps = []
        
        processing_steps.append( ClientParsing.StringSplitter( separator = ',', max_splits = 2 ) )
        
        processing_steps.append( ClientParsing.StringMatch( match_type = ClientParsing.STRING_MATCH_FLEXIBLE, match_value = ClientParsing.NUMERIC ) )
        
        transformations = [ ( ClientParsing.STRING_TRANSFORMATION_APPEND_TEXT, 'abc' ) ]
        
        processing_steps.append( ClientParsing.StringConverter( transformations = transformations ) )
        
        processor.SetProcessingSteps( processing_steps )
        
        expected_result = [ '1abc', '123abc' ]
        
        self.assertEqual( processor.ProcessStrings( [ '1,a,2,3', 'test', '123' ] ), expected_result )
        
    
