import os
import json
import random
import unittest

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientStrings
from hydrus.client import ClientTime
from hydrus.client.parsing import ClientParsing

class DummyFormula( ClientParsing.ParseFormula ):
    
    def __init__( self, result: list[ str ] ):
        
        super().__init__( name = 'dummy formula' )
        
        self._result = result
        
    
    def _GetSerialisableInfo( self ):
        
        return None
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        pass
        
    
    def _ParseRawTexts( self, parsing_context, parsing_text, collapse_newlines: bool ):
        
        return self._result
        
    
    def ToPrettyString( self ):
        
        if self._name == '':
            
            t = ''
            
        else:
            
            t = f'{self._name}: '
            
        
        return t + 'test'
        
    
    def ToPrettyMultilineString( self ):
        
        if self._name == '':
            
            t = ''
            
        else:
            
            t = f'{self._name}: '
            
        
        return t + 'test' + '\n' + 'returns what you give it'
        
    

class TestParseFormulaJSON( unittest.TestCase ):
    
    def test_json_formula_index( self ):
        
        j_text = json.dumps(
            {
                "posts" : [
                    1,
                    2,
                    3
                ]
            }
        )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM, 1 )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        self.assertEqual( formula.Parse( {}, j_text, True ), [ "2" ] )
        
    
    def test_json_formula_items( self ):
        
        j_text = json.dumps(
            {
                "posts" : [
                    1,
                    2,
                    3
                ]
            }
        )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        self.assertEqual( formula.Parse( {}, j_text, True ), [ "1", "2", "3" ] )
        
    
    def test_json_formula_key( self ):
        
        j_text = json.dumps(
            {
                "posts" : [
                    {
                        'a' : 'blah1',
                        'id' : 123
                    },
                    {
                        'a' : 'blah2',
                        'id' : 456
                    },
                    {
                        'a' : 'blah7',
                        'id' : 789
                    }
                ]
            }
        )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'id', example_string = 'id' ) )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        self.assertEqual( formula.Parse( {}, j_text, True ), [ "123", "456", "789" ] )
        
    
    def test_json_formula_pull_json( self ):
        
        j_text = json.dumps(
            {
                "posts" : [
                    {
                        'a' : 'blah1',
                        'id' : 123
                    },
                    {
                        'a' : 'blah2',
                        'id' : 456
                    },
                    {
                        'a' : 'blah7',
                        'id' : 789
                    }
                ]
            }
        )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_JSON
        )
        
        result = formula.Parse( {}, j_text, True )
        
        result_loaded = [ json.loads( r ) for r in result ]
        
        self.assertEqual( result_loaded, [ {"a": "blah1", "id": 123}, {"a": "blah2", "id": 456}, {"a": "blah7", "id": 789} ] )
        
    
    def test_json_formula_dict_keys( self ):
        
        j_text = json.dumps(
            {
                "posts" : [
                    {
                        'a' : 'blah1',
                        'id' : 123
                    },
                    {
                        'a' : 'blah2',
                        'id' : 456
                    },
                    {
                        'a_test' : 'blah7',
                        'id_test' : 789
                    }
                ]
            }
        )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM, 2 )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_DICT_KEYS
        )
        
        self.assertEqual( set( formula.Parse( {}, j_text, True ) ), { 'a_test', 'id_test' } )
        
    
    def test_json_formula_ascend( self ):
        
        j_text = json.dumps(
            {
                "posts" : [
                    {
                        'a' : 'blah1',
                        'id' : 123
                    },
                    {
                        'a' : 'blah2',
                        'id' : 456
                    },
                    {
                        'b' : 'blah7',
                        'id' : 789
                    }
                ]
            }
        )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'a', example_string = 'a' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ASCEND, 1 ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'id', example_string = 'id' ) )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        self.assertEqual( formula.Parse( {}, j_text, True ), [ '123', '456' ] )
        
    
    def test_json_formula_ascend_double( self ):
        
        j_text = json.dumps(
            {
                "posts" : [
                    {
                        "info" : {
                            'a' : 'blah1',
                            'id' : 123
                        },
                        'actual_value' : 'hello a'
                    },
                    {
                        "info" : {
                            'b' : 'blah1',
                            'id' : 123
                        },
                        'actual_value' : 'hello b'
                    },
                ]
            }
        )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'info', example_string = 'info' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'a', example_string = 'a' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ASCEND, 2 ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'actual_value', example_string = 'actual_value' ) )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        self.assertEqual( formula.Parse( {}, j_text, True ), [ 'hello a' ] )
        
    
    def test_json_formula_value_string( self ):
        
        j_text = json.dumps(
            {
                "posts" : [
                    {
                        'a' : 'blah1',
                        'id' : 123
                    },
                    {
                        'a' : 'blah2',
                        'id' : 456
                    },
                    {
                        'b' : 'blah7',
                        'id' : 789
                    }
                ]
            }
        )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'posts', example_string = 'posts' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'a', example_string = 'a' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_TEST_STRING_ITEMS, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'blah2', example_string = 'blah2' ) )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        self.assertEqual( formula.Parse( {}, j_text, True ), [ 'blah2' ] )
        
    
    def test_json_formula_value_and_ascend( self ):
        
        j_text = json.dumps(
            {
                "raw_text": {
                    "text": "can we do that thing?",
                    "facets": [
                        {
                            "type": "tag",
                            "indices": [
                                21,
                                47
                            ],
                            "original": "blue_hair"
                        },
                        {
                            "type": "tag",
                            "indices": [
                                12,
                                91
                            ],
                            "original": "skirt"
                        },
                        {
                            "type": "media",
                            "indices": [
                                96,
                                119
                            ],
                            "original" : "whatever",
                            "id": "123456"
                        }
                    ]
                }
            }
        )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'raw_text', example_string = 'raw_text' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'facets', example_string = 'facets' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'type', example_string = 'type' ) ),
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        self.assertEqual( formula.Parse( {}, j_text, True ), [ 'tag', 'tag', 'media' ] )
        
        formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'raw_text', example_string = 'raw_text' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'facets', example_string = 'facets' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ALL_ITEMS, None ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'type', example_string = 'type' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_TEST_STRING_ITEMS, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'tag', example_string = 'tag' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_ASCEND, 1 ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'original', example_string = 'original' ) )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        self.assertEqual( formula.Parse( {}, j_text, True ), [ 'blue_hair', 'skirt' ] )
        
    

class TestParseFormulaZipper( unittest.TestCase ):
    
    def test_complex_unicode( self ):
        
        a = 'test \u2014\u201D test'
        b = 'test \u2019\u201C test'
        
        formulae = [
            DummyFormula( [ a ] ),
            DummyFormula( [ b ] )
        ]
        
        pfc = ClientParsing.ParseFormulaZipper( formulae = formulae, sub_phrase = '\\1 \\2' )
        
        result = pfc.Parse( {}, 'gumpf', False )
        
        self.assertEqual( result, [ '{} {}'.format( a, b ) ])
        
    

class TestParseFormulaNested( unittest.TestCase ):
    
    def test_complex_unicode( self ):
        
        import html
        import json
        
        payload = { 'test' : [1,'"yo"',3] }
        
        json_payload = json.dumps( payload )
        
        parsing_text = f'<div><muh_tag buried-json-data="{html.escape( json_payload )}">hello!</muh_tag></div>'
        
        main_formula = ClientParsing.ParseFormulaHTML(
            tag_rules = [ ClientParsing.ParseRuleHTML( rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING, tag_name = 'muh_tag' ) ],
            content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE,
            attribute_to_fetch = 'buried-json-data'
        )
        
        sub_formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'test', example_string = 'test' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM, 1 )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        pfn = ClientParsing.ParseFormulaNested( main_formula, sub_formula )
        
        result = pfn.Parse( {}, parsing_text, True )
        
        self.assertEqual( result, [ '"yo"' ] )
        
        #
        
        payload = '<div><muh_tag quantity="&gt;implying">hello</muh_tag></div>'
        
        data = {
            'test' : [
                'hello',
                payload,
                'some_other_thing'
            ]
        }
        
        parsing_text = json.dumps( data )
        
        main_formula = ClientParsing.ParseFormulaJSON(
            parse_rules = [
                ( ClientParsing.JSON_PARSE_RULE_TYPE_DICT_KEY, ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = 'test', example_string = 'test' ) ),
                ( ClientParsing.JSON_PARSE_RULE_TYPE_INDEXED_ITEM, 1 )
            ],
            content_to_fetch = ClientParsing.JSON_CONTENT_STRING
        )
        
        sub_formula = ClientParsing.ParseFormulaHTML(
            tag_rules = [ ClientParsing.ParseRuleHTML( rule_type = ClientParsing.HTML_RULE_TYPE_DESCENDING, tag_name = 'muh_tag' ) ],
            content_to_fetch = ClientParsing.HTML_CONTENT_ATTRIBUTE,
            attribute_to_fetch = 'quantity'
        )
        
        pfn = ClientParsing.ParseFormulaNested( main_formula, sub_formula )
        
        result = pfn.Parse( {}, parsing_text, True )
        
        self.assertEqual( result, [ '>implying' ] )
        
    

class TestContentParser( unittest.TestCase ):
    
    def test_mappings( self ):
        
        parsing_context = {}
        parsing_text = 'test parsing text'
        
        name = 'test content parser'
        
        # none
        
        dummy_formula = DummyFormula( [ 'character:lara croft', 'double pistols' ] )
        
        additional_info = None
        
        content_parser = ClientParsing.ContentParser( name = name, content_type = HC.CONTENT_TYPE_MAPPINGS, formula = dummy_formula, additional_info = additional_info )
        
        self.assertEqual( content_parser.Parse( parsing_context, parsing_text ).GetTags(), { 'character:lara croft', 'double pistols' } )
        
        # ''
        
        additional_info = ''
        
        content_parser = ClientParsing.ContentParser( name = name, content_type = HC.CONTENT_TYPE_MAPPINGS, formula = dummy_formula, additional_info = additional_info )
        
        self.assertEqual( content_parser.Parse( parsing_context, parsing_text ).GetTags(), { ':character:lara croft', 'double pistols' } )
        
        # character
        
        additional_info = 'character'
        
        content_parser = ClientParsing.ContentParser( name = name, content_type = HC.CONTENT_TYPE_MAPPINGS, formula = dummy_formula, additional_info = additional_info )
        
        self.assertEqual( content_parser.Parse( parsing_context, parsing_text ).GetTags(), { 'character:character:lara croft', 'character:double pistols' } )
        
        # series
        
        additional_info = 'series'
        
        content_parser = ClientParsing.ContentParser( name = name, content_type = HC.CONTENT_TYPE_MAPPINGS, formula = dummy_formula, additional_info = additional_info )
        
        self.assertEqual( content_parser.Parse( parsing_context, parsing_text ).GetTags(), { 'series:character:lara croft', 'series:double pistols' } )
        
    

class TestStringConverter( unittest.TestCase ):
    
    def test_basics( self ):
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '123456789' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_END, 1 ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '012345678' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_CLIP_TEXT_FROM_BEGINNING, 7 ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '0123456' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_CLIP_TEXT_FROM_END, 7 ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '3456789' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_PREPEND_TEXT, 'abc' ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc0123456789' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_APPEND_TEXT, 'xyz' ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '0123456789xyz' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_APPEND_RANDOM, ( 'a', 5 ) ) ] )
        
        self.assertEqual( string_converter.Convert( 'bbbbb' ), 'bbbbbaaaaa' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_URL_PERCENT ) ] )
        
        self.assertEqual( string_converter.Convert( '01234 56789' ), '01234%2056789' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_DECODE, ClientStrings.ENCODING_TYPE_URL_PERCENT ) ] )
        
        self.assertEqual( string_converter.Convert( '01234%2056789' ), '01234 56789' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_UNICODE_ESCAPE ) ] )
        
        self.assertEqual( string_converter.Convert( '01234\u039456789' ), '01234\\u039456789' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_DECODE, ClientStrings.ENCODING_TYPE_UNICODE_ESCAPE ) ] )
        
        self.assertEqual( string_converter.Convert( '01234\\u039456789' ), '01234\u039456789' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_HTML_ENTITIES ) ] )
        
        self.assertEqual( string_converter.Convert( '01234&56789' ), '01234&amp;56789' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_DECODE, ClientStrings.ENCODING_TYPE_HTML_ENTITIES ) ] )
        
        self.assertEqual( string_converter.Convert( '01234&amp;56789' ), '01234&56789' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_HEX_UTF8 ) ] )
        
        self.assertEqual( string_converter.Convert( 'hello world' ), '68656c6c6f20776f726c64' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_BASE64_UTF8 ) ] )
        
        self.assertEqual( string_converter.Convert( 'hello world' ), 'aGVsbG8gd29ybGQ=' )
        self.assertEqual( string_converter.Convert( '\uffff' ), '77+/' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_BASE64URL_UTF8 ) ] )
        
        self.assertEqual( string_converter.Convert( 'hello world' ), 'aGVsbG8gd29ybGQ' ) # never outputs '=' padding
        self.assertEqual( string_converter.Convert( '\uffff' ), '77-_' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_DECODE, ClientStrings.ENCODING_TYPE_HEX_UTF8 ) ] )
        
        self.assertEqual( string_converter.Convert( '68656c6c6f20776f726c64' ), 'hello world' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_DECODE, ClientStrings.ENCODING_TYPE_BASE64_UTF8 ) ] )
        
        self.assertEqual( string_converter.Convert( 'aGVsbG8gd29ybGQ=' ), 'hello world' )
        self.assertEqual( string_converter.Convert( 'aGVsbG8gd29ybGQ' ), 'hello world' )
        self.assertEqual( string_converter.Convert( '77+/' ), '\uffff' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_DECODE, ClientStrings.ENCODING_TYPE_BASE64URL_UTF8 ) ] )
        
        self.assertEqual( string_converter.Convert( 'aGVsbG8gd29ybGQ=' ), 'hello world' )
        self.assertEqual( string_converter.Convert( 'aGVsbG8gd29ybGQ' ), 'hello world' )
        self.assertEqual( string_converter.Convert( '77-_' ), '\uffff' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REVERSE, None ) ] )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '9876543210' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_REGEX_SUB, ( '\\d', 'd' ) ) ] )
        
        self.assertEqual( string_converter.Convert( 'abc123' ), 'abcddd' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_DATE_DECODE, ( '%Y-%m-%d %H:%M:%S', HC.TIMEZONE_UTC, 0 ) ) ] )
        
        self.assertEqual( string_converter.Convert( '1970-01-02 00:00:00' ), '86400' )
        
        #
        
        if ClientTime.DATEPARSER_OK:
            
            string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_DATEPARSER_DECODE, None ) ] )
            
            self.assertEqual( string_converter.Convert( '1970-01-02 00:00:00 UTC' ), '86400' )
            self.assertEqual( string_converter.Convert( 'January 12, 2012 10:00 PM EST' ), '1326423600' )
            
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_DATE_ENCODE, ( '%Y-%m-%d %H:%M:%S', 0 ) ) ] )
        
        self.assertEqual( string_converter.Convert( '86400' ), '1970-01-02 00:00:00' )
        
        #
        
        string_converter = ClientStrings.StringConverter( conversions = [ ( ClientStrings.STRING_CONVERSION_INTEGER_ADDITION, 5 ) ] )
        
        self.assertEqual( string_converter.Convert( '4' ), '9' )
        
    
    def test_compound( self ):
        
        conversions = []
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING, 1 ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '123456789' )
        
        #
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_REMOVE_TEXT_FROM_END, 1 ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '12345678' )
        
        #
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_CLIP_TEXT_FROM_BEGINNING, 7 ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '1234567' )
        
        #
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_CLIP_TEXT_FROM_END, 6 ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), '234567' )
        
        #
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_PREPEND_TEXT, 'abc' ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567' )
        
        #
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_APPEND_TEXT, 'x z' ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567x z' )
        
        #
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_ENCODE, ClientStrings.ENCODING_TYPE_URL_PERCENT ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567x%20z' )
        
        #
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_DECODE, ClientStrings.ENCODING_TYPE_URL_PERCENT ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'abc234567x z' )
        
        #
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_REVERSE, None ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'z x765432cba' )
        
        #
        
        conversions.append( ( ClientStrings.STRING_CONVERSION_REGEX_SUB, ( '\\d', 'd' ) ) )
        
        string_converter = ClientStrings.StringConverter( conversions = conversions )
        
        self.assertEqual( string_converter.Convert( '0123456789' ), 'z xddddddcba' )
        
    

class TestStringJoiner( unittest.TestCase ):
    
    def test_basics( self ):
        
        texts = [
            'ab',
            'cd',
            'ef',
            'gh',
            'ij'
        ]
        
        #
        
        joiner = ClientStrings.StringJoiner( joiner = '', join_tuple_size = None )
        self.assertEqual( joiner.Join( texts ), [ 'abcdefghij' ] )
        self.assertEqual( joiner.ToString(), 'joining all strings using ""' )
        
        joiner = ClientStrings.StringJoiner( joiner = ',', join_tuple_size = None )
        self.assertEqual( joiner.Join( texts ), [ 'ab,cd,ef,gh,ij' ] )
        self.assertEqual( joiner.ToString(), 'joining all strings using ","' )
        
        joiner = ClientStrings.StringJoiner( joiner = '--', join_tuple_size = 2 )
        self.assertEqual( joiner.Join( texts ), [ 'ab--cd', 'ef--gh' ] )
        self.assertEqual( joiner.ToString(), 'joining every 2 strings using "--"' )
        
        joiner = ClientStrings.StringJoiner( joiner = r'\n', join_tuple_size = None )
        self.assertEqual( joiner.Join( texts ), [ 'ab\ncd\nef\ngh\nij' ] )
        self.assertEqual( joiner.ToString(), 'joining all strings using "\\n"' )
        
        joiner = ClientStrings.StringJoiner( joiner = '\\\\', join_tuple_size = None )
        self.assertEqual( joiner.Join( texts ), [ 'ab\\cd\\ef\\gh\\ij' ] )
        self.assertEqual( joiner.ToString(), 'joining all strings using "\\\\"' )
        
    
class TestStringMatch( unittest.TestCase ):
    
    def test_basics( self ):
        
        all_string_match = ClientStrings.StringMatch()
        
        self.assertTrue( all_string_match.Matches( '123' ) )
        self.assertTrue( all_string_match.Matches( 'abc' ) )
        self.assertTrue( all_string_match.Matches( 'abc123' ) )
        
        #
        
        min_string_match = ClientStrings.StringMatch( min_chars = 4 )
        
        self.assertFalse( min_string_match.Matches( '123' ) )
        self.assertFalse( min_string_match.Matches( 'abc' ) )
        self.assertTrue( min_string_match.Matches( 'abc123' ) )
        
        #
        
        max_string_match = ClientStrings.StringMatch( max_chars = 4 )
        
        self.assertTrue( max_string_match.Matches( '123' ) )
        self.assertTrue( max_string_match.Matches( 'abc' ) )
        self.assertFalse( max_string_match.Matches( 'abc123' ) )
        
        #
        
        min_max_string_match = ClientStrings.StringMatch( min_chars = 4, max_chars = 10 )
        
        self.assertFalse( min_max_string_match.Matches( '123' ) )
        self.assertFalse( min_max_string_match.Matches( 'abc' ) )
        self.assertTrue( min_max_string_match.Matches( 'abc123' ) )
        
        #
        
        alpha_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.FLEXIBLE_MATCH_ALPHA )
        
        self.assertFalse( alpha_string_match.Matches( '123' ) )
        self.assertTrue( alpha_string_match.Matches( 'abc' ) )
        self.assertFalse( alpha_string_match.Matches( 'abc123' ) )
        
        #
        
        alphanum_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.FLEXIBLE_MATCH_ALPHANUMERIC )
        
        self.assertTrue( alphanum_string_match.Matches( '123' ) )
        self.assertTrue( alphanum_string_match.Matches( 'abc' ) )
        self.assertTrue( alphanum_string_match.Matches( 'abc123' ) )
        self.assertFalse( alphanum_string_match.Matches( 'abc123@' ) )
        
        #
        
        num_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.FLEXIBLE_MATCH_NUMERIC )
        
        self.assertTrue( num_string_match.Matches( '123' ) )
        self.assertFalse( num_string_match.Matches( 'abc' ) )
        self.assertFalse( num_string_match.Matches( 'abc123' ) )
        
        #
        
        hex_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.FLEXIBLE_MATCH_HEX )
        
        self.assertTrue( hex_string_match.Matches( '123' ) )
        self.assertTrue( hex_string_match.Matches( 'abc' ) )
        self.assertTrue( hex_string_match.Matches( 'abc123' ) )
        self.assertFalse( hex_string_match.Matches( 'abc123z' ) )
        
        #
        
        base64_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.FLEXIBLE_MATCH_BASE64 )
        
        self.assertTrue( base64_string_match.Matches( '123' ) )
        self.assertTrue( base64_string_match.Matches( 'abc' ) )
        self.assertTrue( base64_string_match.Matches( 'abc123+/' ) )
        self.assertTrue( base64_string_match.Matches( 'abc123+/=' ) )
        self.assertFalse( base64_string_match.Matches( 'abc123+]' ) )
        
        #
        
        base64_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.FLEXIBLE_MATCH_BASE64_URL_ENCODED )
        
        self.assertTrue( base64_string_match.Matches( '123' ) )
        self.assertTrue( base64_string_match.Matches( 'abc' ) )
        self.assertTrue( base64_string_match.Matches( 'abc123%2B%2F' ) )
        self.assertTrue( base64_string_match.Matches( 'abc123%2B%2F%3D' ) )
        self.assertFalse( base64_string_match.Matches( 'abc123%2B]' ) )
        
        #
        
        base64_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.FLEXIBLE_MATCH_BASE64URL )
        
        self.assertTrue( base64_string_match.Matches( '123' ) )
        self.assertTrue( base64_string_match.Matches( 'abc' ) )
        self.assertTrue( base64_string_match.Matches( 'abc123-' ) )
        self.assertTrue( base64_string_match.Matches( 'abc123_=' ) )
        self.assertFalse( base64_string_match.Matches( 'abc123+]' ) )
        
        #
        
        fixed_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FIXED, match_value = '123' )
        
        self.assertTrue( fixed_string_match.Matches( '123' ) )
        self.assertFalse( fixed_string_match.Matches( 'abc' ) )
        self.assertFalse( fixed_string_match.Matches( 'abc123' ) )
        
        #
        
        re_string_match = ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_REGEX, match_value = '\\d' )
        
        self.assertTrue( re_string_match.Matches( '123' ) )
        self.assertFalse( re_string_match.Matches( 'abc' ) )
        self.assertTrue( re_string_match.Matches( 'abc123' ) )
        
    
class TestStringSlicer( unittest.TestCase ):
    
    def test_basics( self ):
        
        a = 'a ' + os.urandom( 8 ).hex()
        b = 'b ' + os.urandom( 8 ).hex()
        c = 'c ' + os.urandom( 8 ).hex()
        d = 'd ' + os.urandom( 8 ).hex()
        e = 'e ' + os.urandom( 8 ).hex()
        f = 'f ' + os.urandom( 8 ).hex()
        g = 'g ' + os.urandom( 8 ).hex()
        h = 'h ' + os.urandom( 8 ).hex()
        i = 'i ' + os.urandom( 8 ).hex()
        j = 'j ' + os.urandom( 8 ).hex()
        
        test_list = [ a, b, c, d, e, f, g, h, i, j ]
        
        #
        
        slicer = ClientStrings.StringSlicer( index_start = 0, index_end = 1 )
        self.assertEqual( slicer.Slice( test_list ), [ a ] )
        self.assertEqual( slicer.ToString(), 'selecting the 1st string' )
        
        slicer = ClientStrings.StringSlicer( index_start = 3, index_end = 4 )
        self.assertEqual( slicer.Slice( test_list ), [ d ] )
        self.assertEqual( slicer.ToString(), 'selecting the 4th string' )
        
        slicer = ClientStrings.StringSlicer( index_start = -3, index_end = -2 )
        self.assertEqual( slicer.Slice( test_list ), [ h ] )
        self.assertEqual( slicer.ToString(), 'selecting the 3rd from last string' )
        
        slicer = ClientStrings.StringSlicer( index_start = -1 )
        self.assertEqual( slicer.Slice( test_list ), [ j ] )
        self.assertEqual( slicer.ToString(), 'selecting the last string' )
        
        slicer = ClientStrings.StringSlicer( index_start = 15, index_end = 16 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting the 16th string' )
        
        slicer = ClientStrings.StringSlicer( index_start = -15, index_end = -14 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting the 15th from last string' )
        
        #
        
        slicer = ClientStrings.StringSlicer( index_start = 0 )
        self.assertEqual( slicer.Slice( test_list ), test_list )
        self.assertEqual( slicer.ToString(), 'selecting the 1st string and onwards' )
        
        slicer = ClientStrings.StringSlicer( index_start = 3 )
        self.assertEqual( slicer.Slice( test_list ), [ d, e, f, g, h, i, j ] )
        self.assertEqual( slicer.ToString(), 'selecting the 4th string and onwards' )
        
        slicer = ClientStrings.StringSlicer( index_start = -3 )
        self.assertEqual( slicer.Slice( test_list ), [ h, i, j ] )
        self.assertEqual( slicer.ToString(), 'selecting the 3rd from last string and onwards' )
        
        slicer = ClientStrings.StringSlicer( index_start = 15 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting the 16th string and onwards' )
        
        slicer = ClientStrings.StringSlicer( index_start = -15 )
        self.assertEqual( slicer.Slice( test_list ), test_list )
        self.assertEqual( slicer.ToString(), 'selecting the 15th from last string and onwards' )
        
        #
        
        slicer = ClientStrings.StringSlicer( index_end = 0 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting nothing' )
        
        slicer = ClientStrings.StringSlicer( index_end = 3 )
        self.assertEqual( slicer.Slice( test_list ), [ a, b, c ] )
        self.assertEqual( slicer.ToString(), 'selecting up to and including the 3rd string' )
        
        slicer = ClientStrings.StringSlicer( index_end = -3 )
        self.assertEqual( slicer.Slice( test_list ), [ a, b, c, d, e, f, g ] )
        self.assertEqual( slicer.ToString(), 'selecting up to and including the 4th from last string' )
        
        slicer = ClientStrings.StringSlicer( index_end = 15 )
        self.assertEqual( slicer.Slice( test_list ), test_list )
        self.assertEqual( slicer.ToString(), 'selecting up to and including the 15th string' )
        
        slicer = ClientStrings.StringSlicer( index_end = -15 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting up to and including the 16th from last string' )
        
        #
        
        slicer = ClientStrings.StringSlicer( index_start = 0, index_end = 5 )
        self.assertEqual( slicer.Slice( test_list ), [ a, b, c, d, e ] )
        self.assertEqual( slicer.ToString(), 'selecting the 1st string up to and including the 5th string' )
        
        slicer = ClientStrings.StringSlicer( index_start = 3, index_end = 5 )
        self.assertEqual( slicer.Slice( test_list ), [ d, e ] )
        self.assertEqual( slicer.ToString(), 'selecting the 4th string up to and including the 5th string' )
        
        slicer = ClientStrings.StringSlicer( index_start = -5, index_end = -3 )
        self.assertEqual( slicer.Slice( test_list ), [ f, g ] )
        self.assertEqual( slicer.ToString(), 'selecting the 5th from last string up to and including the 4th from last string' )
        
        slicer = ClientStrings.StringSlicer( index_start = 3, index_end = -3 )
        self.assertEqual( slicer.Slice( test_list ), [ d, e, f, g ] )
        self.assertEqual( slicer.ToString(), 'selecting the 4th string up to and including the 4th from last string' )
        
        #
        
        slicer = ClientStrings.StringSlicer( index_start = 3, index_end = 3 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting nothing' )
        
        slicer = ClientStrings.StringSlicer( index_start = 5, index_end = 3 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting nothing' )
        
        slicer = ClientStrings.StringSlicer( index_start = -3, index_end = -3 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting nothing' )
        
        slicer = ClientStrings.StringSlicer( index_start = -3, index_end = -5 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting nothing' )
        
        #
        
        slicer = ClientStrings.StringSlicer( index_start = 15, index_end = 20 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting the 16th string up to and including the 20th string' )
        
        slicer = ClientStrings.StringSlicer( index_start = -15, index_end = -12 )
        self.assertEqual( slicer.Slice( test_list ), [] )
        self.assertEqual( slicer.ToString(), 'selecting the 15th from last string up to and including the 13th from last string' )
        
    
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
                
                self.assertEqual( sorter.Sort( test_list ), correct )
                
            
        
        sorter = ClientStrings.StringSorter( sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC, asc = True, regex = None )
        correct = [ a, b, c, d, e ]
        
        do_sort_test( sorter, correct )
        
        sorter = ClientStrings.StringSorter( sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC, asc = False, regex = None )
        correct = [ e, d, c, b, a ]
        
        do_sort_test( sorter, correct )
        
        #
        
        sorter = ClientStrings.StringSorter( sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT, asc = True, regex = None )
        correct = [ a, b, c, d, e ]
        
        do_sort_test( sorter, correct )
        
        sorter = ClientStrings.StringSorter( sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT, asc = False, regex = None )
        correct = [ e, d, c, b, a ]
        
        do_sort_test( sorter, correct )
        
        #
        
        sorter = ClientStrings.StringSorter( sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC, asc = True, regex = '\\d+' )
        correct = [ c, b, a, d, e ]
        
        do_sort_test( sorter, correct )
        
        sorter = ClientStrings.StringSorter( sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC, asc = False, regex = '\\d+' )
        correct = [ d, a, b, c, e ]
        
        do_sort_test( sorter, correct )
        
        #
        
        sorter = ClientStrings.StringSorter( sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT, asc = True, regex = '\\d+' )
        correct = [ b, a, d, c, e ]
        
        do_sort_test( sorter, correct )
        
        sorter = ClientStrings.StringSorter( sort_type = ClientStrings.CONTENT_PARSER_SORT_TYPE_HUMAN_SORT, asc = False, regex = '\\d+' )
        correct = [ c, d, a, b, e ]
        
        do_sort_test( sorter, correct )
        
    
class TestStringSplitter( unittest.TestCase ):
    
    def test_basics( self ):
        
        splitter = ClientStrings.StringSplitter( separator = ', ' )
        
        self.assertEqual( splitter.Split( '123' ), [ '123' ] )
        self.assertEqual( splitter.Split( '1,2,3' ), [ '1,2,3' ] )
        self.assertEqual( splitter.Split( '1, 2, 3' ), [ '1', '2', '3' ] )
        
        splitter = ClientStrings.StringSplitter( separator = ', ', max_splits = 2 )
        
        self.assertEqual( splitter.Split( '123' ), [ '123' ] )
        self.assertEqual( splitter.Split( '1,2,3' ), [ '1,2,3' ] )
        self.assertEqual( splitter.Split( '1, 2, 3, 4' ), [ '1', '2', '3, 4' ] )
        
        splitter = ClientStrings.StringSplitter( separator = r'\n' )
        
        self.assertEqual( splitter.Split( '1\n2' ), [ '1', '2' ] )
        
        splitter = ClientStrings.StringSplitter( separator = '\\\\' )
        
        self.assertEqual( splitter.Split( '1\\2' ), [ '1', '2' ] )
        
    
class TestStringProcessor( unittest.TestCase ):
    
    def test_basics( self ):
        
        processor = ClientStrings.StringProcessor()
        
        self.assertEqual( processor.ProcessStrings( [] ), [] )
        self.assertEqual( processor.ProcessStrings( [ 'test' ] ), [ 'test' ] )
        self.assertEqual( processor.ProcessStrings( [ 'test', 'test', '', 'test2' ] ), [ 'test', 'test', '', 'test2' ] )
        
        processing_steps = []
        
        processing_steps.append( ClientStrings.StringSplitter( separator = ',', max_splits = 2 ) )
        
        processing_steps.append( ClientStrings.StringMatch( match_type = ClientStrings.STRING_MATCH_FLEXIBLE, match_value = ClientStrings.FLEXIBLE_MATCH_NUMERIC ) )
        
        conversions = [ ( ClientStrings.STRING_CONVERSION_APPEND_TEXT, 'abc' ) ]
        
        processing_steps.append( ClientStrings.StringConverter( conversions = conversions ) )
        
        processor.SetProcessingSteps( processing_steps )
        
        expected_result = [ '1abc', '123abc' ]
        
        self.assertEqual( processor.ProcessStrings( [ '1,a,2,3', 'test', '123' ] ), expected_result )
        
    
