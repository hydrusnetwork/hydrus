import base64
import calendar
import html
import re
import typing
import time
import urllib.parse

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags

STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING = 0
STRING_CONVERSION_REMOVE_TEXT_FROM_END = 1
STRING_CONVERSION_PREPEND_TEXT = 2
STRING_CONVERSION_APPEND_TEXT = 3
STRING_CONVERSION_ENCODE = 4
STRING_CONVERSION_DECODE = 5
STRING_CONVERSION_CLIP_TEXT_FROM_BEGINNING = 6
STRING_CONVERSION_CLIP_TEXT_FROM_END = 7
STRING_CONVERSION_REVERSE = 8
STRING_CONVERSION_REGEX_SUB = 9
STRING_CONVERSION_DATE_DECODE = 10
STRING_CONVERSION_INTEGER_ADDITION = 11
STRING_CONVERSION_DATE_ENCODE = 12

conversion_type_str_lookup = {}

conversion_type_str_lookup[ STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING ] = 'remove text from beginning of string'
conversion_type_str_lookup[ STRING_CONVERSION_REMOVE_TEXT_FROM_END ] = 'remove text from end of string'
conversion_type_str_lookup[ STRING_CONVERSION_PREPEND_TEXT ] = 'prepend text'
conversion_type_str_lookup[ STRING_CONVERSION_APPEND_TEXT ] = 'append text'
conversion_type_str_lookup[ STRING_CONVERSION_ENCODE ] = 'encode'
conversion_type_str_lookup[ STRING_CONVERSION_DECODE ] = 'decode'
conversion_type_str_lookup[ STRING_CONVERSION_CLIP_TEXT_FROM_BEGINNING ] = 'take the start of the string'
conversion_type_str_lookup[ STRING_CONVERSION_CLIP_TEXT_FROM_END ] = 'take the end of the string'
conversion_type_str_lookup[ STRING_CONVERSION_REVERSE ] = 'reverse text'
conversion_type_str_lookup[ STRING_CONVERSION_REGEX_SUB ] = 'regex substitution'
conversion_type_str_lookup[ STRING_CONVERSION_DATE_DECODE ] = 'datestring to timestamp'
conversion_type_str_lookup[ STRING_CONVERSION_INTEGER_ADDITION ] = 'integer addition'
conversion_type_str_lookup[ STRING_CONVERSION_DATE_ENCODE ] = 'timestamp to datestring'

class StringProcessingStep( HydrusSerialisable.SerialisableBase ):
    
    def _GetSerialisableInfo( self ):
        
        raise NotImplementedError()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        raise NotImplementedError()
        
    
    def MakesChanges( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def ToString( self, simple = False, with_type = False ) -> str:
        
        raise NotImplementedError()
        
    
class StringConverter( StringProcessingStep ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_STRING_CONVERTER
    SERIALISABLE_NAME = 'String Converter'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, conversions = None, example_string = None ):
        
        if conversions is None:
            
            conversions = []
            
        
        if example_string is None:
            
            example_string = 'example string'
            
        
        StringProcessingStep.__init__( self )
        
        self.conversions = conversions
        
        self.example_string = example_string
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self.conversions, self.example_string )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_conversions, self.example_string ) = serialisable_info
        
        self.conversions = []
        
        try: # I initialised this bad one time and broke a dialog on subsequent loads, fugg
            
            for ( conversion_type, data ) in serialisable_conversions:
                
                if isinstance( data, list ):
                    
                    data = tuple( data ) # convert from list to tuple thing
                    
                
                self.conversions.append( ( conversion_type, data ) )
                
            
        except:
            
            pass
            
        
    
    def Convert( self, s, max_steps_allowed = None ):
        
        for ( i, conversion ) in enumerate( self.conversions ):
            
            if max_steps_allowed is not None and i >= max_steps_allowed:
                
                return s
                
            
            try:
                
                ( conversion_type, data ) = conversion
                
                if conversion_type == STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING:
                    
                    num_chars = data
                    
                    s = s[ num_chars : ]
                    
                elif conversion_type == STRING_CONVERSION_REMOVE_TEXT_FROM_END:
                    
                    num_chars = data
                    
                    s = s[ : - num_chars ]
                    
                elif conversion_type == STRING_CONVERSION_CLIP_TEXT_FROM_BEGINNING:
                    
                    num_chars = data
                    
                    s = s[ : num_chars ]
                    
                elif conversion_type == STRING_CONVERSION_CLIP_TEXT_FROM_END:
                    
                    num_chars = data
                    
                    s = s[ - num_chars : ]
                    
                elif conversion_type == STRING_CONVERSION_PREPEND_TEXT:
                    
                    text = data
                    
                    s = text + s
                    
                elif conversion_type == STRING_CONVERSION_APPEND_TEXT:
                    
                    text = data
                    
                    s = s + text
                    
                elif conversion_type == STRING_CONVERSION_ENCODE:
                    
                    encode_type = data
                    
                    if encode_type == 'url percent encoding':
                        
                        s = urllib.parse.quote( s, safe = '' )
                        
                    elif encode_type == 'unicode escape characters':
                        
                        s = s.encode( 'unicode-escape' ).decode( 'utf-8' )
                        
                    elif encode_type == 'html entities':
                        
                        s = html.escape( s )
                        
                    else:
                        
                        # due to py3, this is now a bit of a pain
                        # _for now_, let's convert to bytes if not already and then spit out a str
                        
                        if isinstance( s, str ):
                            
                            s_bytes = bytes( s, 'utf-8' )
                            
                        else:
                            
                            s_bytes = s
                            
                        
                        if encode_type == 'hex':
                            
                            s = s_bytes.hex()
                            
                        elif encode_type == 'base64':
                            
                            s_bytes = base64.b64encode( s_bytes )
                            
                            s = str( s_bytes, 'utf-8' )
                            
                        
                    
                elif conversion_type == STRING_CONVERSION_DECODE:
                    
                    encode_type = data
                    
                    if encode_type == 'url percent encoding':
                        
                        s = urllib.parse.unquote( s )
                        
                    elif encode_type == 'unicode escape characters':
                        
                        s = s.encode( 'utf-8' ).decode( 'unicode-escape' )
                        
                    elif encode_type == 'html entities':
                        
                        s = html.unescape( s )
                        
                    
                    # the old 'hex' and 'base64' are now deprecated, no-ops
                    
                elif conversion_type == STRING_CONVERSION_REVERSE:
                    
                    s = s[::-1]
                    
                elif conversion_type == STRING_CONVERSION_REGEX_SUB:
                    
                    ( pattern, repl ) = data
                    
                    s = re.sub( pattern, repl, s )
                    
                elif conversion_type == STRING_CONVERSION_DATE_DECODE:
                    
                    ( phrase, timezone, timezone_offset ) = data
                    
                    struct_time = time.strptime( s, phrase )
                    
                    if timezone == HC.TIMEZONE_GMT:
                        
                        # the given struct is in GMT, so calendar.timegm is appropriate here
                        
                        timestamp = int( calendar.timegm( struct_time ) )
                        
                    elif timezone == HC.TIMEZONE_LOCAL:
                        
                        # the given struct is in local time, so time.mktime is correct
                        
                        try:
                            
                            timestamp = int( time.mktime( struct_time ) )
                            
                        except:
                            
                            timestamp = HydrusData.GetNow()
                            
                        
                    elif timezone == HC.TIMEZONE_OFFSET:
                        
                        # the given struct is in server time, which is the same as GMT minus an offset
                        # if we are 7200 seconds ahead, the correct GMT timestamp needs to be 7200 smaller
                        
                        timestamp = int( calendar.timegm( struct_time ) ) - timezone_offset
                        
                    
                    s = str( timestamp )
                    
                elif conversion_type == STRING_CONVERSION_DATE_ENCODE:
                    
                    ( phrase, timezone ) = data
                    
                    try:
                        
                        timestamp = int( s )
                        
                    except:
                        
                        raise Exception( '"{}" was not an integer!'.format( s ) )
                        
                    
                    if timezone == HC.TIMEZONE_GMT:
                        
                        # user wants a UTC string, so we need UTC struct
                        
                        struct_time = time.gmtime( timestamp )
                        
                    elif timezone == HC.TIMEZONE_LOCAL:
                        
                        # user wants a local string, so we need localtime
                        
                        struct_time = time.localtime( timestamp )
                        
                    
                    s = time.strftime( phrase, struct_time )
                    
                elif conversion_type == STRING_CONVERSION_INTEGER_ADDITION:
                    
                    delta = data
                    
                    s = str( int( s ) + int( delta ) )
                    
                
            except Exception as e:
                
                raise HydrusExceptions.StringConvertException( 'ERROR: Could not apply "' + self.ConversionToString( conversion ) + '" to string "' + repr( s ) + '":' + str( e ) )
                
            
        
        return s
        
    
    def GetConversions( self ):
        
        return list( self.conversions )
        
    
    def GetConversionStrings( self ):
        
        return [ self.ConversionToString( conversion ) for conversion in self.conversions ]
        
    
    def MakesChanges( self ):
        
        return len( self.conversions ) > 0
        
    
    def ToString( self, simple = False, with_type = False ) -> str:
        
        num_rules = len( self.conversions )
        
        if num_rules == 0:
            
            if simple:
                
                label = 'no changes'
                
            else:
                
                label = 'no string conversions'
                
            
        else:
            
            if simple:
                
                label = '{} changes'.format( HydrusData.ToHumanInt( num_rules ) )
                
            else:
                
                label = ', '.join( self.GetConversionStrings() )
                
            
        
        if with_type:
            
            label = 'CONVERT: {}'.format( label )
            
        
        return label
        
    
    @staticmethod
    def ConversionToString( conversion ):
        
        ( conversion_type, data ) = conversion
        
        if conversion_type == STRING_CONVERSION_REMOVE_TEXT_FROM_BEGINNING:
            
            return 'remove the first ' + HydrusData.ToHumanInt( data ) + ' characters'
            
        elif conversion_type == STRING_CONVERSION_REMOVE_TEXT_FROM_END:
            
            return 'remove the last ' + HydrusData.ToHumanInt( data ) + ' characters'
            
        elif conversion_type == STRING_CONVERSION_CLIP_TEXT_FROM_BEGINNING:
            
            return 'take the first ' + HydrusData.ToHumanInt( data ) + ' characters'
            
        elif conversion_type == STRING_CONVERSION_CLIP_TEXT_FROM_END:
            
            return 'take the last ' + HydrusData.ToHumanInt( data ) + ' characters'
            
        elif conversion_type == STRING_CONVERSION_PREPEND_TEXT:
            
            return 'prepend with "' + data + '"'
            
        elif conversion_type == STRING_CONVERSION_APPEND_TEXT:
            
            return 'append with "' + data + '"'
            
        elif conversion_type == STRING_CONVERSION_ENCODE:
            
            return 'encode to ' + data
            
        elif conversion_type == STRING_CONVERSION_DECODE:
            
            if data in ( 'hex', 'base64' ):
                
                return 'deprecated {} decode, now a no-op, can be deleted'.format( data )
                
            
            return 'decode from ' + data
            
        elif conversion_type == STRING_CONVERSION_REVERSE:
            
            return conversion_type_str_lookup[ STRING_CONVERSION_REVERSE ]
            
        elif conversion_type == STRING_CONVERSION_REGEX_SUB:
            
            return 'regex substitution: ' + str( data )
            
        elif conversion_type == STRING_CONVERSION_DATE_DECODE:
            
            return 'datestring to timestamp: ' + repr( data )
            
        elif conversion_type == STRING_CONVERSION_DATE_ENCODE:
            
            return 'timestamp to datestring: ' + repr( data )
            
        elif conversion_type == STRING_CONVERSION_INTEGER_ADDITION:
            
            return 'integer addition: add ' + str( data )
            
        else:
            
            return 'unknown conversion'
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_STRING_CONVERTER ] = StringConverter

STRING_MATCH_FIXED = 0
STRING_MATCH_FLEXIBLE = 1
STRING_MATCH_REGEX = 2
STRING_MATCH_ANY = 3

ALPHA = 0
ALPHANUMERIC = 1
NUMERIC = 2

class StringMatch( StringProcessingStep ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_STRING_MATCH
    SERIALISABLE_NAME = 'String Match'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, match_type = STRING_MATCH_ANY, match_value = '', min_chars = None, max_chars = None, example_string = 'example string' ):
        
        StringProcessingStep.__init__( self )
        
        self._match_type = match_type
        self._match_value = match_value
        
        self._min_chars = min_chars
        self._max_chars = max_chars
        
        self._example_string = example_string
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._match_type, self._match_value, self._min_chars, self._max_chars, self._example_string )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._match_type, self._match_value, self._min_chars, self._max_chars, self._example_string ) = serialisable_info
        
    
    def GetExampleString( self ):
        
        return self._example_string
        
    
    def MakesChanges( self ) -> bool:
        
        if self._min_chars is not None or self._max_chars is not None:
            
            return True
            
        
        if self._match_type != STRING_MATCH_ANY:
            
            return True
            
        
        return False
        
    
    def Matches( self, text ):
        
        try:
            
            self.Test( text )
            
            return True
            
        except HydrusExceptions.StringMatchException:
            
            return False
            
        
    
    def SetMaxChars( self, max_chars ):
        
        self._max_chars = max_chars
        
    
    def SetMinChars( self, min_chars ):
        
        self._min_chars = min_chars
        
    
    def Test( self, text ):
        
        if isinstance( text, bytes ):
            
            raise HydrusExceptions.StringMatchException( 'Got a bytes value in a string match!' )
            
        
        text_len = len( text )
        
        presentation_text = '"{}"'.format( text )
        
        if self._min_chars is not None and text_len < self._min_chars:
            
            raise HydrusExceptions.StringMatchException( presentation_text + ' had fewer than ' + HydrusData.ToHumanInt( self._min_chars ) + ' characters' )
            
        
        if self._max_chars is not None and text_len > self._max_chars:
            
            raise HydrusExceptions.StringMatchException( presentation_text + ' had more than ' + HydrusData.ToHumanInt( self._max_chars ) + ' characters' )
            
        
        if self._match_type == STRING_MATCH_FIXED:
            
            if text != self._match_value:
                
                raise HydrusExceptions.StringMatchException( presentation_text + ' did not exactly match "' + self._match_value + '"' )
                
            
        elif self._match_type in ( STRING_MATCH_FLEXIBLE, STRING_MATCH_REGEX ):
            
            if self._match_type == STRING_MATCH_FLEXIBLE:
                
                if self._match_value == ALPHA:
                    
                    r = '^[a-zA-Z]+$'
                    fail_reason = ' had non-alpha characters'
                    
                elif self._match_value == ALPHANUMERIC:
                    
                    r = '^[a-zA-Z\\d]+$'
                    fail_reason = ' had non-alphanumeric characters'
                    
                elif self._match_value == NUMERIC:
                    
                    r = '^\\d+$'
                    fail_reason = ' had non-numeric characters'
                    
                
            elif self._match_type == STRING_MATCH_REGEX:
                
                r = self._match_value
                
                fail_reason = ' did not match "' + r + '"'
                
            
            try:
                
                result = re.search( r, text )
                
            except Exception as e:
                
                raise HydrusExceptions.StringMatchException( 'That regex did not work! ' + str( e ) )
                
            
            if result is None:
                
                raise HydrusExceptions.StringMatchException( presentation_text + fail_reason )
                
            
        elif self._match_type == STRING_MATCH_ANY:
            
            pass
            
        
    
    def ToTuple( self ):
        
        return ( self._match_type, self._match_value, self._min_chars, self._max_chars, self._example_string )
        
    
    def ToString( self, simple = False, with_type = False ) -> str:
        
        if simple:
            
            return 'filter'
            
        
        result = ''
        
        if self._min_chars is None:
            
            if self._max_chars is None:
                
                result += 'any number of '
                
            else:
                
                result += 'at most ' + str( self._max_chars ) + ' '
                
            
        else:
            
            if self._max_chars is None:
                
                result += 'at least ' + str( self._min_chars ) + ' '
                
            else:
                
                result += 'between ' + str( self._min_chars ) + ' and ' + str( self._max_chars ) + ' '
                
            
        
        show_example = True
        
        if self._match_type == STRING_MATCH_ANY:
            
            result += 'characters'
            
            show_example = False
            
        elif self._match_type == STRING_MATCH_FIXED:
            
            result = self._match_value
            
            show_example = False
            
        elif self._match_type == STRING_MATCH_FLEXIBLE:
            
            if self._match_value == ALPHA:
                
                result += 'alphabetical characters'
                
            elif self._match_value == ALPHANUMERIC:
                
                result += 'alphanumeric characters'
                
            elif self._match_value == NUMERIC:
                
                result += 'numeric characters'
                
            
        elif self._match_type == STRING_MATCH_REGEX:
            
            result += 'characters, matching regex "' + self._match_value + '"'
            
        
        if show_example:
            
            result += ', such as "' + self._example_string + '"'
            
        
        if with_type:
            
            result = 'MATCH: {}'.format( result )
            
        
        return result
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_STRING_MATCH ] = StringMatch

class StringSlicer( StringProcessingStep ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_STRING_SLICER
    SERIALISABLE_NAME = 'String Selector/Slicer'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, index_start: typing.Optional[ int ] = None, index_end: typing.Optional[ int ] = None ):
        
        StringProcessingStep.__init__( self )
        
        self._index_start = index_start
        self._index_end = index_end
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._index_start, self._index_end )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._index_start, self._index_end ) = serialisable_info
        
    
    def GetIndexStartEnd( self ) -> typing.Tuple[ typing.Optional[ int ], typing.Optional[ int ] ]:
        
        return ( self._index_start, self._index_end )
        
    
    def MakesChanges( self ) -> bool:
        
        return self._index_start is not None or self._index_end is not None
        
    
    def SelectsNothingEver( self ) -> bool:
        
        if self._index_end == 0:
            
            return True
            
        
        if self._index_start is None or self._index_end is None:
            
            return False
            
        
        both_positive = self._index_start >= 0 and self._index_end >= 0
        both_negative = self._index_start < 0 and self._index_end < 0
        
        if both_positive or both_negative:
            
            if self._index_start >= self._index_end:
                
                return True
                
            
        
        return False
        
    
    def SelectsOne( self ) -> bool:
        
        if self.SelectsNothingEver():
            
            return False
            
        
        if self._index_start == -1 and self._index_end is None:
            
            return True
            
        
        if self._index_start is None or self._index_end is None:
            
            return False
            
        
        both_positive = self._index_start >= 0 and self._index_end >= 0
        both_negative = self._index_start < 0 and self._index_end < 0
        
        return ( both_positive or both_negative ) and self._index_start == self._index_end - 1
        
    
    def Slice( self, texts: typing.Sequence[ str ] ) -> typing.List[ str ]:
        
        try:
            
            if self._index_start is None and self._index_end is None:
                
                return list( texts )
                
            elif self._index_end is None:
                
                return texts[ self._index_start : ]
                
            elif self._index_start is None:
                
                return texts[ : self._index_end ]
                
            else:
                
                return texts[ self._index_start : self._index_end ]
                
            
        except IndexError as e:
            
            return []
            
        
    
    def ToString( self, simple = False, with_type = False ) -> str:
        
        if simple:
            
            return 'selector/slicer'
            
        
        if self.SelectsNothingEver():
            
            result = 'selecting nothing'
            
        elif self.SelectsOne():
            
            result = 'selecting the {} string'.format( HydrusData.ConvertIndexToPrettyOrdinalString( self._index_start ) )
            
        elif self._index_start is None and self._index_end is None:
            
            result = 'selecting everything'
            
        elif self._index_end is None:
            
            result = 'selecting the {} string and onwards'.format( HydrusData.ConvertIndexToPrettyOrdinalString( self._index_start ) )
            
        elif self._index_start is None:
            
            result = 'selecting up to and including the {} string'.format( HydrusData.ConvertIndexToPrettyOrdinalString( self._index_end - 1 ) )
            
        else:
            
            result = 'selecting the {} string up to and including the {} string'.format( HydrusData.ConvertIndexToPrettyOrdinalString( self._index_start ), HydrusData.ConvertIndexToPrettyOrdinalString( self._index_end - 1 ) )
            
        
        if with_type:
            
            if self.SelectsOne():
                
                result = 'SELECT: {}'.format( result )
                
            else:
                
                result = 'SLICE: {}'.format( result )
                
            
        
        return result
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_STRING_SLICER ] = StringSlicer

CONTENT_PARSER_SORT_TYPE_NONE = 0
CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC = 1
CONTENT_PARSER_SORT_TYPE_HUMAN_SORT = 2
CONTENT_PARSER_SORT_TYPE_REVERSE = 3

sort_str_enum = {
    CONTENT_PARSER_SORT_TYPE_NONE : 'no sorting',
    CONTENT_PARSER_SORT_TYPE_LEXICOGRAPHIC : 'strict lexicographic',
    CONTENT_PARSER_SORT_TYPE_HUMAN_SORT : 'human sort',
    CONTENT_PARSER_SORT_TYPE_REVERSE : 'reverse'
}

class StringSorter( StringProcessingStep ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_STRING_SORTER
    SERIALISABLE_NAME = 'String Sorter'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, sort_type: int = CONTENT_PARSER_SORT_TYPE_HUMAN_SORT, asc: bool = False, regex: typing.Optional[ str ] = None ):
        
        StringProcessingStep.__init__( self )
        
        self._sort_type = sort_type
        self._asc = asc
        self._regex = regex
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._sort_type, self._asc, self._regex )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._sort_type, self._asc, self._regex ) = serialisable_info
        
    
    def GetAscending( self ) -> bool:
        
        return self._asc
        
    
    def GetRegex( self ) -> typing.Optional[ str ]:
        
        return self._regex
        
    
    def GetSortType( self ) -> int:
        
        return self._sort_type
        
    
    def MakesChanges( self ) -> bool:
        
        return True
        
    
    def Sort( self, texts: typing.Sequence[ str ] ) -> typing.List[ str ]:
        
        try:
            
            texts = list( texts )
            
            if self._sort_type == CONTENT_PARSER_SORT_TYPE_REVERSE:
                
                texts.reverse()
                
            else:
                
                data_convert = lambda d_s: d_s
                invalid_data_convert_texts = []
                
                if self._regex is not None:
                    
                    re_job = re.compile( self._regex )
                    
                    def d( d_s ):
                        
                        m = re_job.search( d_s )
                        
                        if m is None:
                            
                            return ''
                            
                        else:
                            
                            return m.group()
                            
                        
                    
                    data_convert = d
                    
                    invalid_data_convert_texts = [ text for text in texts if data_convert( text ) == '' ]
                    texts = [ text for text in texts if data_convert( text ) != '' ]
                    
                
                sort_convert = lambda s: s
                
                if self._sort_type == CONTENT_PARSER_SORT_TYPE_HUMAN_SORT:
                    
                    sort_convert = HydrusData.HumanTextSortKey
                    
                
                key = lambda k_s: sort_convert( data_convert( k_s ) )
                
                reverse = not self._asc
                
                texts.sort( key = key, reverse = reverse )
                
                invalid_data_convert_texts.sort( key = sort_convert, reverse = reverse )
                
                texts.extend( invalid_data_convert_texts )
                
            
            return texts
            
        except Exception as e:
            
            raise HydrusExceptions.StringSortException( e )
            
        
    
    def ToString( self, simple = False, with_type = False ) -> str:
        
        if simple:
            
            return 'sorter'
            
        
        result = 'sorting {} ({})'.format( sort_str_enum[ self._sort_type ], 'ascending' if self._asc else 'descending' )
        
        if self._regex is not None:
            
            result = '{} (with regex)'.format( result )
            
        
        if with_type:
            
            result = 'SORT: {}'.format( result )
            
        
        return result
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_STRING_SORTER ] = StringSorter

class StringSplitter( StringProcessingStep ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_STRING_SPLITTER
    SERIALISABLE_NAME = 'String Splitter'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, separator: str = ',', max_splits: typing.Optional[ int ] = None ):
        
        StringProcessingStep.__init__( self )
        
        self._separator = separator
        self._max_splits = max_splits
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._separator, self._max_splits )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._separator, self._max_splits ) = serialisable_info
        
    
    def GetMaxSplits( self ):
        
        return self._max_splits
        
    
    def GetSeparator( self ):
        
        return self._separator
        
    
    def MakesChanges( self ) -> bool:
        
        return True
        
    
    def Split( self, text: str ) -> typing.List[ str ]:
        
        if isinstance( text, bytes ):
            
            raise HydrusExceptions.StringSplitterException( 'Got a bytes value in a string splitter!' )
            
        
        try:
            
            if self._max_splits is None:
                
                results = text.split( self._separator )
                
            else:
                
                results = text.split( self._separator, self._max_splits )
                
            
        except Exception as e:
            
            raise HydrusExceptions.StringSplitterException( 'Problem when splitting text: {}'.format( e ) )
            
        
        return [ result for result in results if result != '' ]
        
    
    def ToString( self, simple = False, with_type = False ) -> str:
        
        if simple:
            
            return 'splitter'
            
        
        result = 'splitting by "{}"'.format( self._separator )
        
        if self._max_splits is not None:
            
            result = '{}, at most {} times'.format( result, HydrusData.ToHumanInt( self._max_splits ) )
            
        
        if with_type:
            
            result = 'SPLIT: {}'.format( result )
            
        
        return result
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_STRING_SPLITTER ] = StringSplitter

class StringTagFilter( StringProcessingStep ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_STRING_TAG_FILTER
    SERIALISABLE_NAME = 'String Tag Filter'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, tag_filter = None, example_string = 'blue eyes' ):
        
        StringProcessingStep.__init__( self )
        
        if tag_filter is None:
            
            tag_filter = HydrusTags.TagFilter()
            
        
        self._tag_filter = tag_filter
        
        self._example_string = example_string
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_tag_filter = self._tag_filter.GetSerialisableTuple()
        
        return ( serialisable_tag_filter, self._example_string )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_tag_filter, self._example_string ) = serialisable_info
        
        self._tag_filter = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_filter )
        
    
    def ConvertAndFilter( self, tag_texts ):
        
        tags = HydrusTags.CleanTags( tag_texts )
        
        tags = self._tag_filter.Filter( tags, apply_unnamespaced_rules_to_namespaced_tags = True )
        
        tags = sorted( tags, key = HydrusTags.ConvertTagToSortable )
        
        return tags
        
    
    def GetExampleString( self ) -> str:
        
        return self._example_string
        
    
    def GetTagFilter( self ) -> HydrusTags.TagFilter:
        
        return self._tag_filter
        
    
    def MakesChanges( self ) -> bool:
        
        # it always scans for valid tags
        
        return True
        
    
    def Matches( self, text ):
        
        try:
            
            self.Test( text )
            
            return True
            
        except HydrusExceptions.StringMatchException:
            
            return False
            
        
    
    def Test( self, text ):
        
        if isinstance( text, bytes ):
            
            raise HydrusExceptions.StringMatchException( 'Got a bytes value in a string match!' )
            
        
        presentation_text = '"{}"'.format( text )
        
        try:
            
            tags = HydrusTags.CleanTags( [ text ] )
            
            if len( tags ) == 0:
                
                raise Exception()
                
            else:
                
                tag = list( tags )[0]
                
            
        except:
            
            raise HydrusExceptions.StringMatchException( '{} was not a valid tag!'.format( presentation_text ) )
            
        
        if not self._tag_filter.TagOK( tag, apply_unnamespaced_rules_to_namespaced_tags = True ):
            
            raise HydrusExceptions.StringMatchException( '{} did not pass the tag filter!'.format( presentation_text ) )
            
        
    
    def ToString( self, simple = False, with_type = False ) -> str:
        
        if simple:
            
            return 'tag filter'
            
        
        result = '{}, such as {}'.format( self._tag_filter.ToPermittedString(), self._example_string )
        
        if with_type:
            
            result = 'TAG FILTER: {}'.format( result )
            
        
        return result
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_STRING_TAG_FILTER ] = StringTagFilter

class StringProcessor( StringProcessingStep ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_STRING_PROCESSOR
    SERIALISABLE_NAME = 'String Processor'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        StringProcessingStep.__init__( self )
        
        self._processing_steps = []
        
    
    def _GetSerialisableInfo( self ):
        
        return HydrusSerialisable.SerialisableList( self._processing_steps ).GetSerialisableTuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_processing_steps = serialisable_info
        
        self._processing_steps = list( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_processing_steps ) )
        
    
    def GetProcessingSteps( self ):
        
        return list( self._processing_steps )
        
    
    def GetProcessingStrings( self ):
        
        proc_strings = []
        
        for processing_step in self._processing_steps:
            
            if isinstance( processing_step, StringConverter ):
                
                proc_strings.extend( processing_step.GetConversionStrings() )
                
            else:
                
                proc_strings.append( processing_step.ToString() )
                
            
        
        return proc_strings
        
    
    def MakesChanges( self ) -> bool:
        
        return True in ( step.MakesChanges() for step in self._processing_steps )
        
    
    def ProcessStrings( self, starting_strings: typing.Iterable[ str ], max_steps_allowed = None, no_slicing = False ) -> typing.List[ str ]:
        
        current_strings = list( starting_strings )
        
        for ( i, processing_step ) in enumerate( self._processing_steps ):
            
            if max_steps_allowed is not None and i >= max_steps_allowed:
                
                break
                
            
            if isinstance( processing_step, StringSorter ):
                
                try:
                    
                    next_strings = processing_step.Sort( current_strings )
                    
                except HydrusExceptions.StringSortException:
                    
                    next_strings = current_strings
                    
                
            elif isinstance( processing_step, StringSlicer ):
                
                if no_slicing:
                    
                    next_strings = current_strings
                    
                else:
                    
                    try:
                        
                        next_strings = processing_step.Slice( current_strings )
                        
                    except:
                        
                        next_strings = current_strings
                        
                    
                
            elif isinstance( processing_step, StringTagFilter ):
                
                try:
                    
                    next_strings = processing_step.ConvertAndFilter( current_strings )
                    
                except:
                    
                    next_strings = current_strings
                    
                
            else:
                
                next_strings = []
                
                for current_string in current_strings:
                    
                    if isinstance( processing_step, StringConverter ):
                        
                        if isinstance( current_string, bytes ):
                            
                            continue
                            
                        
                        try:
                            
                            next_string = processing_step.Convert( current_string )
                            
                            next_strings.append( next_string )
                            
                        except HydrusExceptions.StringConvertException:
                            
                            continue
                            
                        
                    elif isinstance( processing_step, StringMatch ):
                        
                        try:
                            
                            if processing_step.Matches( current_string ):
                                
                                next_strings.append( current_string )
                                
                            
                        except HydrusExceptions.StringMatchException:
                            
                            continue
                            
                        
                    elif isinstance( processing_step, StringSplitter ):
                        
                        if isinstance( current_string, bytes ):
                            
                            continue
                            
                        
                        try:
                            
                            split_strings = processing_step.Split( current_string )
                            
                            next_strings.extend( split_strings )
                            
                        except HydrusExceptions.StringSplitterException:
                            
                            continue
                            
                        
                    
                
            
            current_strings = next_strings
            
        
        return current_strings
        
    
    def SetProcessingSteps( self, processing_steps: typing.List[ StringProcessingStep ] ):
        
        self._processing_steps = list( processing_steps )
        
    
    def ToString( self, simple = False, with_type = False  ) -> str:
        
        if len( self._processing_steps ) == 0:
            
            return 'no string processing'
            
        else:
            
            components = []
            
            if True in ( isinstance( ps, StringConverter ) for ps in self._processing_steps ):
                
                components.append( 'conversion' )
                
            
            if True in ( isinstance( ps, StringMatch ) for ps in self._processing_steps ):
                
                components.append( 'filtering' )
                
            
            if True in ( isinstance( ps, StringSplitter ) for ps in self._processing_steps ):
                
                components.append( 'splitting' )
                
            
            if True in ( isinstance( ps, StringSorter ) for ps in self._processing_steps ):
                
                components.append( 'sorting' )
                
            
            if True in ( isinstance( ps, StringSlicer ) for ps in self._processing_steps ):
                
                components.append( 'selecting/slicing' )
                
            
            return 'some {}'.format( ', '.join( components ) )
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_STRING_PROCESSOR ] = StringProcessor
