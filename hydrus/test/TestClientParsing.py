import random
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions

from hydrus.client import ClientParsing

class TestStringConverter( unittest.TestCase ):
    
    def test_basics( self ):
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '123456789' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_REMOVE_TEXT_FROM_END, 1 ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '012345678' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_CLIP_TEXT_FROM_BEGINNING, 7 ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '0123456' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_CLIP_TEXT_FROM_END, 7 ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '3456789' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_PREPEND_TEXT, 'abc' ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc0123456789' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_APPEND_TEXT, 'xyz' ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '0123456789xyz' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_ENCODE, 'url percent encoding' ) ] )
        
        self.assertEqual( string_converter.Convert( '01234 56789' ), '01234%2056789' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_DECODE, 'url percent encoding' ) ] )
        
        self.assertEqual( string_converter.Convert( '01234%2056789' ), '01234 56789' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_ENCODE, 'unicode escape characters' ) ] )
        
        self.assertEqual( string_converter.Convert( '01234\u039456789' ), '01234\\u039456789' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_DECODE, 'unicode escape characters' ) ] )
        
        self.assertEqual( string_converter.Convert( '01234\\u039456789' ), '01234\u039456789' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_ENCODE, 'html entities' ) ] )
        
        self.assertEqual( string_converter.Convert( '01234&56789' ), '01234&amp;56789' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_DECODE, 'html entities' ) ] )
        
        self.assertEqual( string_converter.Convert( '01234&amp;56789' ), '01234&56789' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_ENCODE, 'hex' ) ] )
        
        self.assertEqual( string_converter.Convert( b'\xe5\xafW\xa6\x87\xf0\x89\x89O^\xce\xdeP\x04\x94X' ), 'e5af57a687f089894f5ecede50049458' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_ENCODE, 'base64' ) ] )
        
        self.assertEqual( string_converter.Convert( b'\xe5\xafW\xa6\x87\xf0\x89\x89O^\xce\xdeP\x04\x94X' ), '5a9XpofwiYlPXs7eUASUWA==' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_REVERSE, None ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '9876543210' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_REGEX_SUB, ( '\\d', 'd' ) ) ] )
        
        self.assertEqual( string_converter.Convert( 'abc123' ), 'abcddd' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_DATE_DECODE, ( '%Y-%m-%d %H:%M:%S', HC.TIMEZONE_GMT, 0 ) ) ] )
        
        self.assertEqual( string_converter.Convert( '1970-01-02 00:00:00' ), '86400' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_DATE_ENCODE, ( '%Y-%m-%d %H:%M:%S', 0 ) ) ] )
        
        self.assertEqual( string_converter.Convert( '86400' ), '1970-01-02 00:00:00' )
        
        #
        
        string_converter = ClientParsing.StringConverter( conversions = [ ( ClientParsing.STRING_CONVERSION_INTEGER_ADDITION, 5 ) ] )
        
        self.assertEqual( string_converter.Convert( '4' ), '9' )
        
    
    def test_compound( self ):
        
        conversions = []
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '123456789' )
        
        #
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_REMOVE_TEXT_FROM_END, 1 ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '12345678' )
        
        #
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_CLIP_TEXT_FROM_BEGINNING, 7 ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '1234567' )
        
        #
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_CLIP_TEXT_FROM_END, 6 ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '234567' )
        
        #
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_PREPEND_TEXT, 'abc' ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567' )
        
        #
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_APPEND_TEXT, 'x z' ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567x z' )
        
        #
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_ENCODE, 'url percent encoding' ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567x%20z' )
        
        #
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_DECODE, 'url percent encoding' ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567x z' )
        
        #
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_REVERSE, None ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'z x765432cba' )
        
        #
        
        conversions.append( ( ClientParsing.STRING_CONVERSION_REGEX_SUB, ( '\\d', 'd' ) ) )
        
        string_converter = ClientParsing.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'z xddddddcba' )
        
    
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
        
    
class TestStringSorter( unittest.TestCase ):
    
    def test_basics( self ):
        
        a = 'a 5'
        b = 'b 2'
        c = 'c 10'
        d = 'd 7'
        e = 'e'
        
        def do_sort_test( sorter, correct ):
            
            test_list = [ a, b, c, d, e ]
            
            for i in range( 20 ):
                
                random.shuffle( test_list )
                
                self.assertTrue( sorter.Sort( test_list ), correct )
                
            
        
        sorter = ClientParsing.StringSorter( sort_type = ClientParsing.CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC, asc = True, regex = None )
        correct = [ a, b, c, d, e ]
        
        do_sort_test( sorter, correct )
        
        sorter = ClientParsing.StringSorter( sort_type = ClientParsing.CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC, asc = False, regex = None )
        correct = [ e, d, c, b, a ]
        
        do_sort_test( sorter, correct )
        
        #
        
        sorter = ClientParsing.StringSorter( sort_type = ClientParsing.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT, asc = True, regex = None )
        correct = [ a, b, c, d, e ]
        
        do_sort_test( sorter, correct )
        
        sorter = ClientParsing.StringSorter( sort_type = ClientParsing.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT, asc = False, regex = None )
        correct = [ e, d, c, b, a ]
        
        do_sort_test( sorter, correct )
        
        #
        
        sorter = ClientParsing.StringSorter( sort_type = ClientParsing.CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC, asc = True, regex = '\\d+' )
        correct = [ c, b, a, d, e ]
        
        do_sort_test( sorter, correct )
        
        sorter = ClientParsing.StringSorter( sort_type = ClientParsing.CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC, asc = False, regex = '\\d+' )
        correct = [ d, a, b, c, e ]
        
        do_sort_test( sorter, correct )
        
        #
        
        sorter = ClientParsing.StringSorter( sort_type = ClientParsing.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT, asc = True, regex = '\\d+' )
        correct = [ b, a, d, c, e ]
        
        do_sort_test( sorter, correct )
        
        sorter = ClientParsing.StringSorter( sort_type = ClientParsing.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT, asc = False, regex = '\\d+' )
        correct = [ c, d, a, b, e ]
        
        do_sort_test( sorter, correct )
        
    
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
        
        conversions = [ ( ClientParsing.STRING_CONVERSION_APPEND_TEXT, 'abc' ) ]
        
        processing_steps.append( ClientParsing.StringConverter( conversions = conversions ) )
        
        processor.SetProcessingSteps( processing_steps )
        
        expected_result = [ '1abc', '123abc' ]
        
        self.assertEqual( processor.ProcessStrings( [ '1,a,2,3', 'test', '123' ] ), expected_result )
        
    
