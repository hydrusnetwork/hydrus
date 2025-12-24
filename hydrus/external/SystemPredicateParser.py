# made by prkc for Hydrus Network
# Licensed under the same terms as Hydrus Network
# hydev has changed a couple things here and there
# and now I'm writing a parse state object to de-brittle the params and pipeline a bit here

# The basic idea here is to take a system predicate written as text and parse it into a (predicate type, operator, value, unit)
# tuple. The exact structure of the operator, value and unit members depend on the type of the predicate.
# For example, system:width < 500 would become (Predicate.WIDTH, '<', 500).
# The parsers recognize multiple forms for various units and operators, but always normalize to a single canonical form,
# which is given in the comments beside the various enums below.
# Some or all of them can be None, depending on the predicate.
# The "parsing" is done with regex, which is hacky but good enough for this usecase.
# To extend the parser with additional predicates, first extend the Predicate, Value, Operators, Units enums if the
# already present options are not sufficient, then implement parsing for them in the corresponding parse_{unit,value,operator} funtions.
# Finally, add a new entry to the SYSTEM_PREDICATES dict describing the new predicate.
# Initially everything below is independent from other Hydrus code so there is some redundancy.
# It might be better to switch to already established Hydrus enums and constants where possible. 
# Errors are handled by throwing ValueErrors. The main function to call is parse_system_predicate.
# If this file is run by itself it will parse and print all the included examples. There are examples for each supported predicate type.

try:
    
    import dateparser
    
    DATEPARSER_OK = True
    
except:
    
    DATEPARSER_OK = False
    

import math
import re
import datetime
from enum import Enum, auto

from hydrus.core import HydrusExceptions

UNICODE_APPROX_EQUAL = '\u2248'
UNICODE_NOT_EQUAL = '\u2260'

# sort according to longest thing first to rid ourselves of ambiguity
operator_strings_and_results = sorted(
    [
        ( '=', '=' ),
        ( '==', '=' ),
        ( 'is', '=' ),
        ( UNICODE_NOT_EQUAL, UNICODE_NOT_EQUAL ),
        ( '!=', UNICODE_NOT_EQUAL ),
        ( 'is not', UNICODE_NOT_EQUAL ),
        ( 'isn\'t', UNICODE_NOT_EQUAL ),
        ( '<', '<' ),
        ( 'less than', '<' ),
        ( '>', '>' ),
        ( 'more than', '>' ),
        ( UNICODE_APPROX_EQUAL, UNICODE_APPROX_EQUAL ),
        ( '~=', UNICODE_APPROX_EQUAL ),
        ( 'about', UNICODE_APPROX_EQUAL ),
        ( 'is about', UNICODE_APPROX_EQUAL ),
    ],
    key = lambda a: -len( a[0] )
)

operator_strings_to_results = dict( operator_strings_and_results )

# Note this needs to be initialised here with all types that Hydrus supports.
FILETYPES = { }

def InitialiseFiletypes( str_to_enum ):
    for ( filetype_string, enum ) in str_to_enum.items():
        
        if isinstance( enum, int ):
            
            enum_tuple = (enum,)
            
        else:
            
            enum_tuple = tuple( enum )
            
        
        FILETYPES[ filetype_string ] = enum_tuple



NAMESPACE_SEPARATOR = ':'
SYSTEM_PREDICATE_PREFIX = 'system' + NAMESPACE_SEPARATOR


# This enum lists all the recognized predicate types.
class Predicate( Enum ):
    EVERYTHING = auto()
    INBOX = auto()
    ARCHIVE = auto()
    HAS_DURATION = auto()
    NO_DURATION = auto()
    HAS_FRAMERATE = auto()
    NO_FRAMERATE = auto()
    HAS_FRAMES = auto()
    NO_FRAMES = auto()
    HAS_WIDTH = auto()
    NO_WIDTH = auto()
    HAS_HEIGHT = auto()
    NO_HEIGHT = auto()
    HAS_URLS = auto()
    NO_URLS = auto()
    HAS_WORDS = auto()
    NO_WORDS = auto()
    BEST_QUALITY_OF_GROUP = auto()
    NOT_BEST_QUALITY_OF_GROUP = auto()
    HAS_AUDIO = auto()
    NO_AUDIO = auto()
    HAS_TRANSPARENCY = auto()
    NO_TRANSPARENCY = auto()
    HAS_EXIF = auto()
    NO_EXIF = auto()
    HAS_HUMAN_READABLE_EMBEDDED_METADATA = auto()
    NO_HUMAN_READABLE_EMBEDDED_METADATA = auto()
    HAS_ICC_PROFILE = auto()
    NO_ICC_PROFILE = auto()
    HAS_FORCED_FILETYPE = auto()
    NO_FORCED_FILETYPE = auto()
    HAS_TAGS = auto()
    UNTAGGED = auto()
    NUM_OF_TAGS = auto()
    NUM_OF_TAGS_WITH_NAMESPACE = auto()
    NUM_OF_URLS = auto()
    NUM_OF_WORDS = auto()
    HEIGHT = auto()
    WIDTH = auto()
    FILESIZE = auto()
    SIMILAR_TO_FILES = auto()
    SIMILAR_TO_DATA = auto()
    LIMIT = auto()
    FILETYPE = auto()
    HASH = auto()
    MOD_DATE = auto()
    ARCHIVED_DATE = auto()
    LAST_VIEWED_TIME = auto()
    TIME_IMPORTED = auto()
    DURATION = auto()
    FRAMERATE = auto()
    NUM_OF_FRAMES = auto()
    FILE_SERVICE = auto()
    NUM_FILE_RELS = auto()
    RATIO = auto()
    RATIO_SPECIAL = auto()
    NUM_PIXELS = auto()
    MEDIA_VIEWS = auto()
    PREVIEW_VIEWS = auto()
    ALL_VIEWS = auto()
    NEW_VIEWS = auto()
    MEDIA_VIEWTIME = auto()
    PREVIEW_VIEWTIME = auto()
    ALL_VIEWTIME = auto()
    NEW_VIEWTIME = auto()
    URL_REGEX = auto()
    NO_URL_REGEX = auto()
    URL = auto()
    NO_URL = auto()
    DOMAIN = auto()
    NO_DOMAIN = auto()
    URL_CLASS = auto()
    NO_URL_CLASS = auto()
    TAG_AS_NUMBER = auto()
    HAS_NOTES = auto()
    NO_NOTES = auto()
    NUM_NOTES = auto()
    HAS_NOTE_NAME = auto()
    NO_NOTE_NAME = auto()
    RATING_SPECIFIC_NUMERICAL = auto()
    RATING_SPECIFIC_LIKE_DISLIKE = auto()
    RATING_SPECIFIC_INCDEC = auto()
    HAS_RATING = auto()
    NO_RATING = auto()
    TAG_ADVANCED_INCLUSIVE = auto()
    TAG_ADVANCED_EXCLUSIVE = auto()
    RATING_ADVANCED = auto()


# This enum lists the possible value formats a predicate can have (if it has a value).
# Parsing for each of these options is implemented in parse_value
class Value( Enum ):
    NATURAL = auto()  # An int that holds a non-negative value
    SHA256_HASHLIST_WITH_DISTANCE = auto()  # A 2-tuple, where the first part is a set of potential hashes (as strings), the second part is a non-negative integer
    SIMILAR_TO_HASHLIST_WITH_DISTANCE = auto()  # A 3-tuple, where the first two parts are potential pixel and perceptual hashes (as strings), the second part is a non-negative integer
    HASHLIST_WITH_ALGORITHM = auto()  # A 2-tuple, where the first part is a set of potential hashes (as strings), the second part is one of 'sha256', 'md5', 'sha1', 'sha512'
    FILETYPE_LIST = auto()  # A set of file types using the enum set in InitialiseFiletypes as defined in FILETYPES
    # Either a tuple of 4 non-negative integers: (years, months, days, hours) where the latter is < 24 OR
    # a datetime.datetime object. For the latter, only the YYYY-MM-DD format is accepted.
    # dateutils has a function to try to guess and parse arbitrary date formats but I didn't use it here since it would be an additional dependency.
    DATE_OR_TIME_INTERVAL = auto()
    TIME_TO_MSEC = auto()  # A hours, minutes, seconds, milliseconds that converts into ms integer
    ANY_STRING = auto()  # A string (accepts any string so can't use units after this since it consumes the entire remaining part of the input)
    TIME_INTERVAL = auto()  # A tuple of 4 non-negative integers: (days, hours, minutes, seconds) where hours < 24, minutes < 60, seconds < 60
    INTEGER = auto()  # An integer
    RATIO = auto()  # A tuple of 2 ints, both non-negative
    RATIO_SPECIAL = auto() # 1:1
    RATING_SERVICE_NAME_AND_NUMERICAL_VALUE = auto() # my favourites 3/5
    RATING_SERVICE_NAME_AND_LIKE_DISLIKE = auto() # my favourites like
    RATING_SERVICE_NAME_AND_INCDEC = auto() # my favourites 3/5
    NAMESPACE_AND_NUM_TAGS = auto()
    TAG_ADVANCED_TAG = auto() # ': "tag"'
    RATING_ADVANCED = auto() # complicated, but usually something like 'all inc/dec ratings rated'


# Possible operator formats
# Implemented in parse_operator
class Operators( Enum ):
    RELATIONAL = auto()  # One of '=', '<', '>', UNICODE_APPROX_EQUAL ('≈') (takes '~=' too)
    VIEWS_RELATIONAL = auto() # media, preview, client api, and a RELATIONAL
    RELATIONAL_EXACT = auto() # Like RELATIONAL but without the approximately equal operator
    RELATIONAL_TIME = auto()  # One of '=', '<', '>', UNICODE_APPROX_EQUAL ('≈') (takes '~=' too), and the various 'since', 'before', 'the day of', 'the month of' time-based analogues
    RELATIONAL_FOR_RATING_SERVICE = auto()  # RELATIONAL, but in the middle of a 'service_name = 4/5' kind of thing
    EQUAL = auto()  # One of '=' or '!='
    EQUAL_NOT_CONSUMING = auto()  # One of '=' or '!=', doesn't consume this text so later things can look at it
    FILESERVICE_STATUS = auto()  # One of 'is not currently in', 'is currently in', 'is not pending to', 'is pending to'
    TAG_RELATIONAL = auto()  # A tuple of a string (a potential tag name) and a relational operator (as a string)
    ONLY_EQUAL = auto()  # None (meaning =, since thats the only accepted operator)
    RATIO_OPERATORS = auto()  # One of '=', 'wider than','taller than', UNICODE_APPROX_EQUAL ('≈') (takes '~=' too)
    RATIO_OPERATORS_SPECIAL = auto() # 'square', 'portrait', 'landscape'
    TAG_ADVANCED_GUBBINS = auto() # service, ignoring siblings/parents, CDPP status


# Possible unit formats
# Implemented in parse_unit
class Units( Enum ):
    FILESIZE = auto()  # One of 'B', 'KB', 'MB', 'GB'
    FILE_RELATIONSHIP_TYPE = auto()  # One of 'not related/false positive', 'duplicates', 'alternates', 'potential duplicates'
    PIXELS_OR_NONE = auto()  # Always None (meaning pixels)
    PIXELS = auto()  # One of 'pixels', 'kilopixels', 'megapixels'
    FPS_OR_NONE = auto() # 'fps'


# All system predicates
# A predicate is described by a 4-tuple of (predicate type, operator format, value format, unit format) (use None if some are not applicable)
# The keys are regexes matching the predicate names as written by the user.
# The parser will also automatically accept _ instead of space in the predicate names, always use space in this dict.
SYSTEM_PREDICATES = {
    'everything': (Predicate.EVERYTHING, None, None, None),
    'inbox': (Predicate.INBOX, None, None, None),
    'archived?$': (Predicate.ARCHIVE, None, None, None), # $ so as not to clash with system:archive(d) date
    'has duration': (Predicate.HAS_DURATION, None, None, None),
    'no duration': (Predicate.NO_DURATION, None, None, None),
    'has framerate': (Predicate.HAS_FRAMERATE, None, None, None),
    'no framerate': (Predicate.NO_FRAMERATE, None, None, None),
    'has frames': (Predicate.HAS_FRAMES, None, None, None),
    'no frames': (Predicate.NO_FRAMES, None, None, None),
    'has width': (Predicate.HAS_WIDTH, None, None, None),
    'no width': (Predicate.NO_WIDTH, None, None, None),
    'has height': (Predicate.HAS_HEIGHT, None, None, None),
    'no height': (Predicate.NO_HEIGHT, None, None, None),
    'has notes': (Predicate.HAS_NOTES, None, None, None),
    'no notes': (Predicate.NO_NOTES, None, None, None),
    'has urls': (Predicate.HAS_URLS, None, None, None),
    'no urls': (Predicate.NO_URLS, None, None, None),
    'has words': (Predicate.HAS_WORDS, None, None, None),
    'no words': (Predicate.NO_WORDS, None, None, None),
    '(is the )?best quality( file)? of( its)?( duplicate)? group': (Predicate.BEST_QUALITY_OF_GROUP, None, None, None),
    '(((is )?not)|(isn\'t))( the)? best quality( file)? of( its)?( duplicate)? group': (Predicate.NOT_BEST_QUALITY_OF_GROUP, None, None, None),
    'has audio': (Predicate.HAS_AUDIO, None, None, None),
    'no audio': (Predicate.NO_AUDIO, None, None, None),
    'has (transparency|alpha)': (Predicate.HAS_TRANSPARENCY, None, None, None),
    'no (transparency|alpha)': (Predicate.NO_TRANSPARENCY, None, None, None),
    'has exif': (Predicate.HAS_EXIF, None, None, None),
    'no exif': (Predicate.NO_EXIF, None, None, None),
    'has.*embedded.*metadata': (Predicate.HAS_HUMAN_READABLE_EMBEDDED_METADATA, None, None, None),
    'no.*embedded.*metadata': (Predicate.NO_HUMAN_READABLE_EMBEDDED_METADATA, None, None, None),
    'has icc profile': (Predicate.HAS_ICC_PROFILE, None, None, None),
    'no icc profile': (Predicate.NO_ICC_PROFILE, None, None, None),
    'has forced filetype': (Predicate.HAS_FORCED_FILETYPE, None, None, None),
    'no forced filetype': (Predicate.NO_FORCED_FILETYPE, None, None, None),
    'has tags': (Predicate.HAS_TAGS, None, None, None),
    'untagged|no tags': (Predicate.UNTAGGED, None, None, None),
    'num(ber)?( of)? tags': (Predicate.NUM_OF_TAGS, Operators.RELATIONAL, Value.NATURAL, None),
    r'num(ber)?( of)? (?=[^\s].* tags)': (Predicate.NUM_OF_TAGS_WITH_NAMESPACE, None, Value.NAMESPACE_AND_NUM_TAGS, None),
    'num(ber)?( of)? urls': (Predicate.NUM_OF_URLS, Operators.RELATIONAL, Value.NATURAL, None),
    'num(ber)?( of)? words': (Predicate.NUM_OF_WORDS, Operators.RELATIONAL_EXACT, Value.NATURAL, None),
    'height': (Predicate.HEIGHT, Operators.RELATIONAL, Value.NATURAL, Units.PIXELS_OR_NONE),
    'width': (Predicate.WIDTH, Operators.RELATIONAL, Value.NATURAL, Units.PIXELS_OR_NONE),
    'file ?size': (Predicate.FILESIZE, Operators.RELATIONAL, Value.NATURAL, Units.FILESIZE),
    'similar to(?! data)( files)?': (Predicate.SIMILAR_TO_FILES, None, Value.SHA256_HASHLIST_WITH_DISTANCE, None),
    'similar to data': (Predicate.SIMILAR_TO_DATA, None, Value.SIMILAR_TO_HASHLIST_WITH_DISTANCE, None),
    'limit': (Predicate.LIMIT, Operators.ONLY_EQUAL, Value.NATURAL, None),
    'file ?type': (Predicate.FILETYPE, Operators.EQUAL, Value.FILETYPE_LIST, None),
    r'hash( \(?(md5|sha1|sha512)\)?)?': (Predicate.HASH, Operators.EQUAL, Value.HASHLIST_WITH_ALGORITHM, None),
    'archived? (date|time)|(date|time) archived|archived.': (Predicate.ARCHIVED_DATE, Operators.RELATIONAL_TIME, Value.DATE_OR_TIME_INTERVAL, None),
    'modified (date|time)|(date|time) modified|modified': (Predicate.MOD_DATE, Operators.RELATIONAL_TIME, Value.DATE_OR_TIME_INTERVAL, None),
    'last view(ed)? (date|time)|(date|time) last viewed|last viewed': (Predicate.LAST_VIEWED_TIME, Operators.RELATIONAL_TIME, Value.DATE_OR_TIME_INTERVAL, None),
    'import(ed)? (date|time)|(date|time) imported|imported': (Predicate.TIME_IMPORTED, Operators.RELATIONAL_TIME, Value.DATE_OR_TIME_INTERVAL, None),
    'duration': (Predicate.DURATION, Operators.RELATIONAL, Value.TIME_TO_MSEC, None),
    'framerate': (Predicate.FRAMERATE, Operators.RELATIONAL, Value.NATURAL, Units.FPS_OR_NONE),
    'num(ber)?( of)? frames': (Predicate.NUM_OF_FRAMES, Operators.RELATIONAL, Value.NATURAL, None),
    'file service': (Predicate.FILE_SERVICE, Operators.FILESERVICE_STATUS, Value.ANY_STRING, None),
    'num(ber)?( of)? file relationships': (Predicate.NUM_FILE_RELS, Operators.RELATIONAL, Value.NATURAL, Units.FILE_RELATIONSHIP_TYPE),
    r'ratio(?=.*\d)': (Predicate.RATIO, Operators.RATIO_OPERATORS, Value.RATIO, None),
    r'ratio(?!.*\d)': (Predicate.RATIO_SPECIAL, Operators.RATIO_OPERATORS_SPECIAL, None, None),
    'num(ber)?( of)? pixels': (Predicate.NUM_PIXELS, Operators.RELATIONAL, Value.NATURAL, Units.PIXELS),
    'media views': (Predicate.MEDIA_VIEWS, Operators.RELATIONAL, Value.NATURAL, None),
    'preview views': (Predicate.PREVIEW_VIEWS, Operators.RELATIONAL, Value.NATURAL, None),
    'all views': (Predicate.ALL_VIEWS, Operators.RELATIONAL, Value.NATURAL, None),
    '^views (in )?': (Predicate.NEW_VIEWS, Operators.VIEWS_RELATIONAL, Value.NATURAL, None ),
    'media viewtime': (Predicate.MEDIA_VIEWTIME, Operators.RELATIONAL, Value.TIME_INTERVAL, None),
    'preview viewtime': (Predicate.PREVIEW_VIEWTIME, Operators.RELATIONAL, Value.TIME_INTERVAL, None),
    'all viewtime': (Predicate.ALL_VIEWTIME, Operators.RELATIONAL, Value.TIME_INTERVAL, None),
    '^viewtime (in )?': (Predicate.NEW_VIEWTIME, Operators.VIEWS_RELATIONAL, Value.TIME_INTERVAL, None ),
    'has (a )?url matching regex': (Predicate.URL_REGEX, None, Value.ANY_STRING, None),
    '(does not|doesn\'t) have (a )?url matching regex': (Predicate.NO_URL_REGEX, None, Value.ANY_STRING, None),
    'has url:? (?=http)': (Predicate.URL, None, Value.ANY_STRING, None),
    '(does not|doesn\'t) have url:? (?=http)': (Predicate.NO_URL, None, Value.ANY_STRING, None),
    'has (an? )?(url with )?domain': (Predicate.DOMAIN, None, Value.ANY_STRING, None),
    '(does not|doesn\'t) have (an? )?(url with )?domain': (Predicate.NO_DOMAIN, None, Value.ANY_STRING, None),
    'has (an? )?url with (url )?class': (Predicate.URL_CLASS, None, Value.ANY_STRING, None),
    '(does not|doesn\'t) have (an? )?url with (url )?class': (Predicate.NO_URL_CLASS, None, Value.ANY_STRING, None),
    'tag as number': (Predicate.TAG_AS_NUMBER, Operators.TAG_RELATIONAL, Value.INTEGER, None),
    'has notes?$': (Predicate.HAS_NOTES, None, None, None),
    '((has )?no|does not have( a)?|doesn\'t have) notes?$': (Predicate.NO_NOTES, None, None, None),
    'num(ber)?( of)? notes?': (Predicate.NUM_NOTES, Operators.RELATIONAL_EXACT, Value.NATURAL, None),
    '(has (a )?)?note (with name|named)': (Predicate.HAS_NOTE_NAME, None, Value.ANY_STRING, None),
    '((has )?no|does not have( a)?|doesn\'t have( a)?) note (with name|named)': (Predicate.NO_NOTE_NAME, None, Value.ANY_STRING, None),
    'has( a)? (rating|count)( for)?': (Predicate.HAS_RATING, None, Value.ANY_STRING, None ),
    '((has )?no|does not have( a)?|doesn\'t have( a)?) (rating|count)( for)?': (Predicate.NO_RATING, None, Value.ANY_STRING, None ),
    r'(rating|count)( for)?(?=.+?\d+/\d+$)': (Predicate.RATING_SPECIFIC_NUMERICAL, Operators.RELATIONAL_FOR_RATING_SERVICE, Value.RATING_SERVICE_NAME_AND_NUMERICAL_VALUE, None ),
    '(rating|count)( for)?(?=.+?(like|dislike)$)': (Predicate.RATING_SPECIFIC_LIKE_DISLIKE, None, Value.RATING_SERVICE_NAME_AND_LIKE_DISLIKE, None ),
    r'(rating|count)( for)?(?=.+?[^/]\d+$)': (Predicate.RATING_SPECIFIC_INCDEC, Operators.RELATIONAL_FOR_RATING_SERVICE, Value.RATING_SERVICE_NAME_AND_INCDEC, None ),
    r'has tag': (Predicate.TAG_ADVANCED_INCLUSIVE, Operators.TAG_ADVANCED_GUBBINS, Value.TAG_ADVANCED_TAG, None ),
    r'does not have tag': (Predicate.TAG_ADVANCED_EXCLUSIVE, Operators.TAG_ADVANCED_GUBBINS, Value.TAG_ADVANCED_TAG, None ),
    r'(all|any|only).+rated': (Predicate.RATING_ADVANCED, None, Value.RATING_ADVANCED, None ),
}

def string_looks_like_date( string ):
    
    # this sucks but it will do for now
    
    test_words = [ 'year', 'month', 'day', 'hour', 'second', 'ago' ]
    
    return True not in ( word in string for word in test_words )
    

class SystemPredParseResult( object ):
    
    def __init__( self, text: str ):
        
        self.original_text = text.strip()
        self.original_text_lower = self.original_text.lower()
        
        if self.original_text_lower.startswith( SYSTEM_PREDICATE_PREFIX ):
            
            self.subtag_text = self.original_text[ len( SYSTEM_PREDICATE_PREFIX ) ]
            self.subtag_text_lower = self.original_text_lower[ len( SYSTEM_PREDICATE_PREFIX ): ]
            
        else:
            
            self.subtag_text = self.original_text
            self.subtag_text_lower = self.original_text_lower
            
        
        self.text_remainder = self.subtag_text_lower
        
        self.pred_type = None
        self.operator = None
        self.value = None
        self.unit = None
        
    
    def CheckBasics( self ):
        
        if self.original_text_lower.startswith( '-' ):
            
            raise ValueError( "System predicate can't start with negation" )
            
        
        if not self.original_text_lower.startswith( SYSTEM_PREDICATE_PREFIX ):
            
            raise ValueError( "Not a system predicate!" )
            
        
    

# Parsing is just finding a matching predicate name,
# then trying to parse it by consuming the input string.
# The parse_* functions consume some of the string and return a (remaining part of the string, parsed value) tuple.
def parse_system_predicate( string: str ):
    
    parse_result = SystemPredParseResult( string )
    
    parse_result.CheckBasics()
    
    for pred_regex in SYSTEM_PREDICATES:
        
        match = re.match( pred_regex.replace( ' ', '([_ ]+)' ) + ":?", parse_result.subtag_text_lower )
        
        if match:
            
            # TODO: Keep pushing on parse_result
            # I've crammed this 'parse_result' in here, with the intention that future iterations of this will work on that workspace rather than passing around a bunch of variables
            # there's plenty I still haven't done and this looks uglier in places
            # A part of this will be re-examining if and how much we still want to do 'text_remainder', with the stripping away of the thing being parsed, or if that is only appropriate for some pred types
            # good example is 'has blah', where it'd be nice to recognise that as a special case and deliver our 'NumberTest( > 0 )' in a quicker step
            # see the new 'ratings_advanced' bit for an example of where I mostly want to go
            #
            # we could have ways of breaking the pred into 'here's pertinent operator text' and such and saving that back to the parse result. maybe with an extra step or maybe every time from the subtag_text
            # we could also push for more NumberTests in system preds in general and harmonising a bunch of that
            # since hydrus predicates have a general complicated multitype '_value' variable and don't split unit/op/value, I suspect we should move to a separate parsing route for each type, sharing code where we can, and migrate this 'parse unit' stuff to smaller subroutines
            #
            # TODO: It would probably be a good idea to write a 'ParseNumberTest' at some point, for those preds that use them
            # iirc we do some silly stuff in the caller atm to convert from op+value to numbertest, so let's embed it in here instead when reasonable
            # at the same time, I believe we can then get +/- absolute and percentage stuff working. this is the 'is about', unicode_approx_equal, result, which then passes an 'extra_value' on to the numbertest or whatever
            
            parse_result.text_remainder = parse_result.text_remainder[ len( match[ 0 ] ): ]
            
            ( predicate_type, operator_format, value_format, unit_format ) = SYSTEM_PREDICATES[ pred_regex ]
            
            parse_operator( parse_result, operator_format )
            parse_value( parse_result, value_format )
            ( parse_result.text_remainder, parse_result.unit ) = parse_unit( parse_result.text_remainder, unit_format )
            
            if len( parse_result.text_remainder ) > 0:
                
                raise ValueError( "Unrecognized characters at the end of the predicate: " + string )
                
            
            return ( predicate_type, parse_result.operator, parse_result.value, parse_result.unit )
            
        
    
    raise ValueError( "Unknown system predicate!" )
    

def parse_unit( string: str, spec ):
    
    string = string.strip()
    
    if spec is None:
        return string, None
    elif spec == Units.FILESIZE:
        match = re.match( 'b|byte|bytes', string )
        if match: return string[ len( match[ 0 ] ): ], 'B'
        match = re.match( 'kb|kilobytes|kilobyte', string )
        if match: return string[ len( match[ 0 ] ): ], 'KB'
        match = re.match( 'mb|megabytes|megabyte', string )
        if match: return string[ len( match[ 0 ] ): ], 'MB'
        match = re.match( 'gb|gigabytes|gigabyte', string )
        if match: return string[ len( match[ 0 ] ): ], 'GB'
        raise ValueError( "Invalid unit, expected a filesize" )
    elif spec == Units.FILE_RELATIONSHIP_TYPE:
        match = re.match( 'duplicates', string )
        if match: return string[ len( match[ 0 ] ): ], 'duplicates'
        match = re.match( 'alternates', string )
        if match: return string[ len( match[ 0 ] ): ], 'alternates'
        match = re.match( '(not related/false positives?)|not related|(false positives?)', string )
        if match: return string[ len( match[ 0 ] ): ], 'not related/false positive'
        match = re.match( 'potential duplicates', string )
        if match: return string[ len( match[ 0 ] ): ], 'potential duplicates'
        raise ValueError( "Invalid unit, expected a file relationship" )
    elif spec == Units.PIXELS_OR_NONE:
        if not string:
            return string, None
        else:
            match = re.match( '(pixels?)|px', string )
            if match: return string[ len( match[ 0 ] ): ], None
        raise ValueError( "Invalid unit, expected no unit or pixels" )
    elif spec == Units.PIXELS:
        match = re.match( 'px|pixels|pixel', string )
        if match: return string[ len( match[ 0 ] ): ], 'pixels'
        match = re.match( 'kpx|kilopixels|kilopixel', string )
        if match: return string[ len( match[ 0 ] ): ], 'kilopixels'
        match = re.match( 'mpx|megapixels|megapixel', string )
        if match: return string[ len( match[ 0 ] ): ], 'megapixels'
        raise ValueError( "Invalid unit, expected pixels" )
    elif spec == Units.FPS_OR_NONE:
        
        if not string:
            return string, None
        else:
            match = re.match( 'fps', string )
            if match: return string[ len( match[ 0 ] ): ], None
        raise ValueError( "Invalid unit, expected no unit or fps" )
        
    
    raise ValueError( "Invalid unit specification" )
    

def parse_value( parse_result: SystemPredParseResult, spec ):
    
    string = parse_result.text_remainder
    
    string = string.strip()
    
    if spec is None:
        
        return
        
    elif spec in ( Value.NATURAL, Value.INTEGER ):
        
        # 'has urls', 'has words'
        if string.startswith( 'has' ) or string.startswith( 'no' ):
            
            parse_result.text_remainder = ''
            parse_result.value = 0
            
            return
            
        
        match = re.match( '-?[0-9,]+', string )
        
        if match:
            
            rest_of_string = string[ len( match[ 0 ] ): ]
            
            value_text = match[ 0 ]
            
            value_text = value_text.replace( ',', '' )
            
            value = int( value_text )
            
            if spec == Value.NATURAL and value < 0:
                
                raise ValueError( "Invalid value, expected a positive integer!" )
                
            
            parse_result.text_remainder = rest_of_string
            parse_result.value = value
            
            return
            
        
        if spec == Value.NATURAL:
            
            raise ValueError( "Invalid value, expected a natural number" )
            
        else:
            
            raise ValueError( "Invalid value, expected an integer" )
            
        
    elif spec == Value.SHA256_HASHLIST_WITH_DISTANCE:
        
        match = re.match( r'(?P<hashes>([0-9a-f]{4}[0-9a-f]+(\s|,)*)+)(with\s+)?(distance\s+)?(of\s+)?(?P<distance>0|([1-9][0-9]*))?', string )
        
        if match:
            
            hashes = set( hsh.strip() for hsh in re.sub( r'\s', ' ', match[ 'hashes' ].replace( ',', ' ' ) ).split( ' ' ) if len( hsh ) > 0 )
            
            d = match.groupdict()
            
            if 'distance' in d and d[ 'distance' ] is not None:
                
                distance = int( match[ 'distance' ] )
                
            else:
                
                distance = 4
                
            
            parse_result.text_remainder = string[ len( match[ 0 ] ): ]
            parse_result.value = (hashes, distance)
            
            return
            
        
        raise ValueError( "Invalid value, expected a list of hashes with distance" )
        
    elif spec == Value.SIMILAR_TO_HASHLIST_WITH_DISTANCE:
        
        match = re.match( r'(?P<hashes>([0-9a-f]{4}[0-9a-f]+(\s|,)*)+)(with\s+)?(distance\s+)?(of\s+)?(?P<distance>0|([1-9][0-9]*))?', string )
        
        if match:
            
            hashes = set( hsh.strip() for hsh in re.sub( r'\s', ' ', match[ 'hashes' ].replace( ',', ' ' ) ).split( ' ' ) if len( hsh ) > 0 )
            pixel_hashes = { hash for hash in hashes if len( hash ) == 64 }
            perceptual_hashes = { hash for hash in hashes if len( hash ) == 16 }
            
            d = match.groupdict()
            
            if 'distance' in d and d[ 'distance' ] is not None:
                
                distance = int( match[ 'distance' ] )
                
            else:
                
                distance = 8
                
            
            parse_result.text_remainder = string[ len( match[ 0 ] ): ]
            parse_result.value = (pixel_hashes, perceptual_hashes, distance)
            
            return
            
        
        raise ValueError( "Invalid value, expected a list of hashes with distance" )
    
    elif spec == Value.HASHLIST_WITH_ALGORITHM:
        
        # hydev KISS hijack here, instead of clever regex to capture algorithm in all sorts of situations, let's just grab the hex we see and scan the rest for non-hex phrases mate
        # old pattern: match = re.match( r'(?P<hashes>([0-9a-f]+(\s|,)*)+)((with\s+)?algorithm)?\s*(?P<algorithm>sha256|sha512|md5|sha1|)', string )
        
        algorithm = 'sha256'
        
        for possible_algorithm in ( 'md5', 'sha1', 'sha512' ):
            
            if possible_algorithm in parse_result.original_text_lower: # original text lower--it will be gone from text_remainder by now
                
                algorithm = possible_algorithm
                
                break
                
            
        
        # {8} here to make sure we are looking at proper hash hex and not some short 'a' or 'de' word
        match = re.search( r'(?P<hashes>([0-9a-f]{8}[0-9a-f]+(\s|,)*)+)', string )
        
        if match:
            
            hashes = set( hsh.strip() for hsh in re.sub( r'\s', ' ', match[ 'hashes' ].replace( ',', ' ' ) ).split( ' ' ) if len( hsh ) > 0 )
            
            
            parse_result.text_remainder = string[ match.endpos : ]
            parse_result.value = (hashes, algorithm)
            
            return
            
        
        raise ValueError( "Invalid value, expected a list of hashes and perhaps an algorithm" )
        
    
    elif spec == Value.FILETYPE_LIST:
        
        valid_values = sorted( FILETYPES.keys(), key = lambda k: len( k ), reverse = True )
        ftype_regex = '(' + '|'.join( [ '(' + val + ')' for val in valid_values ] ) + ')'
        match = re.match( '(' + ftype_regex + r'(\s|,)+)*' + ftype_regex, string )
        
        if match:
            
            found_ftypes_all = re.sub( r'\s', ' ', match[ 0 ].replace( ',', '|' ) ).split( '|' )
            found_ftypes_good = [ ]
            for ftype in found_ftypes_all:
                ftype = ftype.strip()
                if len( ftype ) > 0 and ftype in FILETYPES:
                    found_ftypes_good.extend( FILETYPES[ ftype ] )
            
            
            parse_result.text_remainder = string[ len( match[ 0 ] ): ]
            parse_result.value = set( found_ftypes_good )
            
            return
            
        
        raise ValueError( "Invalid value, expected a list of file types" )
        
    elif spec == Value.DATE_OR_TIME_INTERVAL:
        
        if DATEPARSER_OK:
            
            dt = dateparser.parse( string )
            
            if not string_looks_like_date( string ):
                
                # a time delta
                now = dateparser.parse( 'now' ) # lol, that's how you get around cross-library timezone headaches
                
                time_delta = now - dt
                
                # this sucked a lot, and then I decided to eventually switch the whole system to days/seconds, just like datetime's time_delta
                # if a user wants to put in 365 days, knowing what inaccuracy that implies, then they can. we just can't reliably deliver leap-year accuracy on long durations
                
                years = 0
                months = 0
                days = time_delta.days
                
                hours = round( time_delta.seconds / 3600 )
                
                if years + months + days + hours == 0:
                    
                    parse_result.text_remainder = ''
                    parse_result.value = dt
                    
                    return
                    
                
                parse_result.text_remainder = ''
                parse_result.value = ( years, months, days, hours )
                
                return
                
            else:
                
                parse_result.text_remainder = ''
                parse_result.value = dt
                
                return
                
            
        else:
            
            match = re.match( r'((?P<year>0|([1-9][0-9]*))\s*(years|year))?\s*((?P<month>0|([1-9][0-9]*))\s*(months|month))?\s*((?P<day>0|([1-9][0-9]*))\s*(days|day))?\s*((?P<hour>0|([1-9][0-9]*))\s*(hours|hour|h))?', string )
            if match and (match.group( 'year' ) or match.group( 'month' ) or match.group( 'day' ) or match.group( 'hour' )):
                years = int( match.group( 'year' ) ) if match.group( 'year' ) else 0
                months = int( match.group( 'month' ) ) if match.group( 'month' ) else 0
                days = int( match.group( 'day' ) ) if match.group( 'day' ) else 0
                hours = int( match.group( 'hour' ) ) if match.group( 'hour' ) else 0
                
                string_result = string[ len( match[ 0 ] ): ]
                
                if string_result == 'ago':
                    
                    string_result = ''
                    
                
                parse_result.text_remainder = string_result
                parse_result.value = ( years, months, days, hours )
                
                return
                
            
            match = re.match( r'(?P<year>[0-9][0-9][0-9][0-9])-(?P<month>[0-9][0-9]?)-(?P<day>[0-9][0-9]?)', string )
            
            if match:
                
                # good expansion here would be to parse a full date with 08:20am kind of thing, but we'll wait for better datetime parsing library for that I think!
                
                parse_result.text_remainder = string[ len( match[ 0 ] ): ]
                parse_result.value = datetime.datetime( int( match.group( 'year' ) ), int( match.group( 'month' ) ), int( match.group( 'day' ) ) )
                
                return
                
            
            raise ValueError( "Invalid value, expected a date or a time interval" )
            
        
    elif spec == Value.TIME_TO_MSEC:
        
        # 'has duration'
        if string.startswith( 'has' ) or string.startswith( 'no' ):
            
            parse_result.text_remainder = ''
            parse_result.value = 0
            
            return
            
        
        pattern = r'((?P<hour>0|([1-9][0-9]*))\s*(hours|hour|hr|h))?\s*'
        pattern += r'((?P<min>0|([1-9][0-9]*))\s*(minutes|minute|mins|m$|m\s|m(?=\d)))?\s*'
        pattern += r'((?P<sec>0|([1-9][0-9]*))\s*(seconds|second|secs|sec|s))?\s*'
        pattern += r'((?P<msec>0|([1-9][0-9]*))\s*(milliseconds|millisecond|msecs|msec|ms))?'
        
        match = re.match( pattern, string )
        
        if match and True in ( match.group( t_name ) is not None for t_name in ( 'hour', 'min', 'sec', 'msec' ) ):
            
            ms_delta = 0
            
            for ( t_name, ms_multiplier ) in [
                ( 'hour', 3600 * 1000 ),
                ( 'min', 60 * 1000 ),
                ( 'sec', 1000 ),
                ( 'msec', 1 )
            ]:
                
                result = match.group( t_name )
                
                if result is not None:
                    
                    ms_delta += int( result ) * ms_multiplier
                    
                
            
            parse_result.text_remainder = string[ len( match[ 0 ] ): ]
            parse_result.value = ms_delta
            
            return
            
        
        raise ValueError( "Invalid value, expected a duration" )
        
    elif spec == Value.ANY_STRING:
        
        if parse_result.pred_type in ( Predicate.URL_REGEX, Predicate.URL_CLASS, Predicate.NO_URL_REGEX, Predicate.NO_URL_REGEX ):
            
            # special case; previously we parsed the whole thing without the initial '.lower()' call. now we can be a bit cleverer
            
            try:
                
                index = parse_result.original_text.find( string )
                
                original_string = parse_result.original_text[ index + len( string ) ]
                
                string = original_string
                
            except:
                
                pass
                
            
        
        parse_result.text_remainder = ''
        parse_result.value = string
        
        return
        
    elif spec == Value.TIME_INTERVAL:
        
        match = re.match( r'((?P<day>0|([1-9][0-9]*))\s*(days|day))?\s*((?P<hour>0|([1-9][0-9]*))\s*(hours|hour|h))?\s*((?P<minute>0|([1-9][0-9]*))\s*(minutes|minute|mins|min))?\s*((?P<second>0|([1-9][0-9]*))\s*(seconds|second|secs|sec|s))?', string )
        
        if match and (match.group( 'day' ) or match.group( 'hour' ) or match.group( 'minute' ) or match.group( 'second' )):
            
            days = int( match.group( 'day' ) ) if match.group( 'day' ) else 0
            hours = int( match.group( 'hour' ) ) if match.group( 'hour' ) else 0
            minutes = int( match.group( 'minute' ) ) if match.group( 'minute' ) else 0
            seconds = int( match.group( 'second' ) ) if match.group( 'second' ) else 0
            minutes += math.floor( seconds / 60 )
            seconds = seconds % 60
            hours += math.floor( minutes / 60 )
            minutes = minutes % 60
            days += math.floor( hours / 24 )
            hours = hours % 24
            
            parse_result.text_remainder = string[ len( match[ 0 ] ): ]
            parse_result.value = (days, hours, minutes, seconds)
            
            return
            
        
        raise ValueError( "Invalid value, expected a time interval" )
    
    elif spec == Value.RATIO:
        
        match = re.match( r'(?P<first>0|([1-9][0-9]*)):(?P<second>0|([1-9][0-9]*))', string )
        
        if match:
            
            parse_result.text_remainder = string[ len( match[ 0 ] ): ]
            parse_result.value = ( int( match[ 'first' ] ), int( match[ 'second' ] ) )
            
            return
            
        
        raise ValueError( "Invalid value, expected a ratio" )
        
    elif spec == Value.RATING_SERVICE_NAME_AND_NUMERICAL_VALUE:
        
        # 'my favourites 3/5' (no operator here)
        
        match = re.match( r'(?P<name>.+?)\s+(?P<num>\d+)/(?P<den>\d+)$', string )
        
        if match:
            
            service_name = match[ 'name' ]
            numerator = int( match[ 'num' ] )
            denominator = int( match[ 'den' ] )
            
            if numerator < 0 or numerator > denominator:
                
                raise ValueError( 'Invalid value, rating value was out of bounds')
                
            
            parse_result.text_remainder = ''
            parse_result.value = ( numerator, service_name )
            
            return
            
        
        raise ValueError( "Invalid value, expected a numerical rating" )
        
    elif spec == Value.RATING_SERVICE_NAME_AND_LIKE_DISLIKE:
        
        # 'tag this later = like' (maybe operator here)
        # 'tag this later like'
        
        # check dislike first lol
        if string.endswith( 'dislike' ):
            
            value = 0.0
            
            string = string[ : -len( 'dislike' ) ]
            
        elif string.endswith( 'like' ):
            
            value = 1.0
            
            string = string[ : -len( 'like' ) ]
            
        else:
            
            raise ValueError( 'Invalid value, expected like/dislike' )
            
        
        string = string.strip()
        
        for ( operator_string, result ) in operator_strings_and_results:
            
            if string.endswith( operator_string ):
                
                string = string[ : -len( operator_string ) ]
                
                string = string.strip()
                
                break
                
            
        
        service_name = string
        
        parse_result.text_remainder = ''
        parse_result.value = ( value, service_name )
        
        return
        
    elif spec == Value.RATING_SERVICE_NAME_AND_INCDEC:
        
        # 'I'm cooooollecting counter 123' (no operator here)
        
        match = re.match( r'(?P<name>.+?)\s+(?P<num>\d+)$', string )
        
        if match:
            
            service_name = match[ 'name' ]
            value = int( match[ 'num' ] )
            
            parse_result.text_remainder = ''
            parse_result.value = ( value, service_name )
            
            return
            
        
        raise ValueError( "Invalid value, expected an inc/dec rating" )
        
    elif spec == Value.NAMESPACE_AND_NUM_TAGS:
        
        # 'character tags > 4'
        match = re.match( r'(?P<namespace>.+) tags (?P<operator>.+?)\s?(?P<num>\d+)\s*$', string )
        
        if match:
            
            namespace = match[ 'namespace' ]
            operator_string = match[ 'operator' ]
            num = int( match[ 'num' ] )
            
            if namespace == 'unnamespaced':
                
                namespace = ''
            
            
            ( gubbins, operator ) = parse_operator_relational( operator_string, Operators.RELATIONAL )
            
            parse_result.text_remainder = ''
            parse_result.value = ( namespace, operator, num )
            
            return
            
        
    elif spec == Value.TAG_ADVANCED_TAG:
        
        # ' "tag"' with quotes ideally, but let's try to handle things if not
        
        regex_that_groups_a_thing_inside_quotes = r'^[^"]*"(?P<tag>.+)"[^"]*$'
        
        if re.match( regex_that_groups_a_thing_inside_quotes, string ) is not None:
            
            match = re.match( regex_that_groups_a_thing_inside_quotes, string )
            
            raw_tag = match.group( 'tag' )
            
        else:
            
            raw_tag = string
            
        
        from hydrus.core import HydrusTags
        
        tag = HydrusTags.CleanTag( raw_tag )
        
        try:
            
            HydrusTags.CheckTagNotEmpty( tag )
            
        except:
            
            tag = 'invalid tag'
            
        
        parse_result.text_remainder = ''
        parse_result.value = tag
        
        return
        
    elif spec == Value.RATING_ADVANCED:
        
        from hydrus.core import HydrusConstants as HC
        from hydrus.client import ClientServices
        
        # this is newer code, we'll use the original string mate. upper case to handle service names too
        # 'all|any|only (rating gubbins) (not) rated'
        # 'only (rating gubbins) (amongst (other rating gubbins)) rated'
        
        subtag_workspace = parse_result.subtag_text_lower.strip()
        
        logical_operator = HC.LOGICAL_OPERATOR_ALL
        
        for ( possible_logical_operator_str, possible_logical_operator ) in (
            ( 'all', HC.LOGICAL_OPERATOR_ALL ),
            ( 'any', HC.LOGICAL_OPERATOR_ANY ),
            ( 'only', HC.LOGICAL_OPERATOR_ONLY ),
        ):
            
            if subtag_workspace.startswith( possible_logical_operator_str ):
                
                subtag_workspace = subtag_workspace[ len( possible_logical_operator_str ) : ].strip()
                logical_operator = possible_logical_operator
                
                break
                
            
        
        rated = True
        
        for ( possible_rated_str, possible_rated ) in (
            ( 'not rated', False ),
            ( 'rated', True ),
        ):
            
            if subtag_workspace.endswith( possible_rated_str ):
                
                subtag_workspace = subtag_workspace[ : - len( possible_rated_str ) ].strip()
                rated = possible_rated
                
                break
                
            
        
        if logical_operator == HC.LOGICAL_OPERATOR_ONLY:
            
            if '(amongst' in subtag_workspace:
                
                ( subtag_workspace, service_specifier_secondary_text ) = subtag_workspace.split( '(amongst', 1 )
                
                subtag_workspace = subtag_workspace.strip()
                service_specifier_secondary_text = service_specifier_secondary_text.strip()
                
                if service_specifier_secondary_text.endswith( ')' ):
                    
                    service_specifier_secondary_text = service_specifier_secondary_text[:-1]
                    
                    service_specifier_secondary_text = service_specifier_secondary_text.strip()
                    
                
                service_specifier_secondary = parse_service_specifier( service_specifier_secondary_text )
                
            else:
                
                service_specifier_secondary = ClientServices.ServiceSpecifier( service_types = HC.LOCAL_RATINGS_SERVICES )
                
            
        else:
            
            service_specifier_secondary = ClientServices.ServiceSpecifier()
            
        
        service_specifier_primary = parse_service_specifier( subtag_workspace )
        
        parse_result.text_remainder = ''
        parse_result.value = ( logical_operator, service_specifier_primary, service_specifier_secondary, rated )
        
        return
        
    
    raise ValueError( "Invalid value specification" )
    

def parse_service_specifier( text: str ):
    
    from hydrus.client import ClientGlobals as CG
    from hydrus.client import ClientServices
    from hydrus.core import HydrusConstants as HC
    
    # 'ratings'
    # like/dislike ratings, numerical ratings
    # service_name, service_name, service_name
    
    if text in ( 'rating', 'ratings' ):
        
        return ClientServices.ServiceSpecifier( service_types = HC.LOCAL_RATINGS_SERVICES )
        
    else:
        
        if ',' in text:
            
            separate_guys = text.split( ',' )
            
        else:
            
            separate_guys = [ text ]
            
        
        separate_guys = [ guy.strip() for guy in separate_guys ]
        
        short_service_type_strings_to_service_types = { name : service_type for ( service_type, name ) in HC.service_string_lookup_short.items() }
        
        if True in ( guy in short_service_type_strings_to_service_types for guy in separate_guys ):
            
            service_type_strings = separate_guys
            service_types = set()
            
            for service_type_string in service_type_strings:
                
                if service_type_string not in short_service_type_strings_to_service_types:
                    
                    raise ValueError( 'Unknown service type!' )
                    
                
                service_types.add( short_service_type_strings_to_service_types[ service_type_string ] )
                
            
            service_specifier = ClientServices.ServiceSpecifier( service_types = service_types )
            
        else:
            
            service_names = separate_guys
            service_keys = set()
            
            for service_name in service_names:
                
                try:
                    
                    service_key = CG.client_controller.services_manager.GetServiceKeyFromName( HC.LOCAL_RATINGS_SERVICES, service_name )
                    
                except HydrusExceptions.DataMissing:
                    
                    raise ValueError( f'Sorry, did not find a service called "{service_name}"!' )
                    
                
                service_keys.add( service_key )
                
            
            service_specifier = ClientServices.ServiceSpecifier( service_keys = service_keys )
            
        
        return service_specifier
        
    

def parse_operator( parse_result: SystemPredParseResult, spec ):
    
    string = parse_result.text_remainder
    
    while string.startswith( ':' ) or string.startswith( ' ' ):
        
        string = string.strip()
        
        if string.startswith( ':' ):
            
            string = string[ 1 : ]
            
        
    
    if spec is None:
        
        return
        
    elif spec == Operators.VIEWS_RELATIONAL:
        
        desired_canvas_types = []
        
        for possible_canvas_type in [ 'media', 'preview', 'client api' ]:
            
            if possible_canvas_type in string:
                
                desired_canvas_types.append( possible_canvas_type )
                
                string = string.replace( possible_canvas_type, '' )
                
            
        
        string = re.sub( '^[, ]+', '', string )
        
        ( string, relational_op ) = parse_operator_relational( string, Operators.RELATIONAL )
        
        parse_result.text_remainder = string
        parse_result.operator = ( desired_canvas_types, relational_op )
        
        return
        
    elif spec in ( Operators.RELATIONAL, Operators.RELATIONAL_EXACT, Operators.RELATIONAL_TIME ):
        
        ( parse_result.text_remainder, parse_result.operator ) = parse_operator_relational( string, spec )
        
        return
        
    elif spec == Operators.RELATIONAL_FOR_RATING_SERVICE:
        
        # "favourites service name > 3/5"
        # since service name can be all sorts of gubbins, we'll work backwards and KISS
        match = re.match( r'(?P<first>.*?)(?P<second>(dislike|like|\d+/\d+|\d+))$', string )
        
        if match:
            
            without_value_string_raw = match[ 'first' ]
            
            without_value_string = without_value_string_raw.strip()
            
            for ( operator_string, possible_operator ) in operator_strings_and_results:
                
                if without_value_string.endswith( operator_string ):
                    
                    if possible_operator == UNICODE_NOT_EQUAL:
                        
                        raise ValueError( 'Invalid rating operator--cannot select "is not"' )
                        
                    
                    service_name = without_value_string[ : -len( operator_string) ]
                    
                    value = match[ 'second' ]
                    
                    parsing_string = f'{service_name} {value}'
                    
                    parse_result.text_remainder = parsing_string
                    parse_result.operator = possible_operator
                    
                    return
                    
                
            
        
        raise ValueError( "Invalid rating operator" )
        
    elif spec == Operators.EQUAL:
        
        for ( possible_operator_str, possible_operator ) in [
            ( '==', '=' ),
            ( UNICODE_NOT_EQUAL, '!=' ),
            ( '!=', '!=' ),
            ( '=', '=' ),
            ( 'is not', '!=' ),
            ( 'isn\'t', '!=' ),
            ( 'is', '=' ),
        ]:
            
            if string.startswith( possible_operator_str ):
                
                parse_result.text_remainder = string[ len( possible_operator_str ) : ]
                parse_result.operator = possible_operator
                
                return
                
            
        
        raise ValueError( "Invalid equality operator" )
        
    elif spec == Operators.FILESERVICE_STATUS:
        
        for ( re_pattern, possible_operator ) in [
            ( '(is )?currently in', 'is currently in' ),
            ( '((is )?not currently in)|isn\'t currently in', 'is not currently in' ),
            ( '(is )?pending to', 'is pending to' ),
            ( '((is )?not pending to)|isn\'t pending to', 'is not pending to' ),
        ]:
            
            match = re.match( re_pattern, string )
            
            if match:
                
                parse_result.text_remainder = string[ len( match[ 0 ] ) : ]
                parse_result.operator = possible_operator
                
                return
                
            
        
        raise ValueError( "Invalid operator, expected a file service relationship" )
        
    elif spec == Operators.TAG_RELATIONAL:
        
        # note this is in the correct order, also, to eliminate = vs == ambiguity
        all_operators_piped = '|'.join( ( s_r[0] for s_r in operator_strings_and_results ) )
        
        match = re.match( r'(?P<namespace>.*)\s+' + f'(?P<op>({all_operators_piped}))', string )
        
        if match:
            
            namespace = match[ 'namespace' ]
            
            if namespace == 'any namespace':
                
                namespace = '*'
                
            
            if namespace == 'unnamespaced':
                
                namespace = ''
                
            
            op_string = match[ 'op' ]
            
            op = operator_strings_to_results.get( op_string, UNICODE_APPROX_EQUAL )
            
            if op not in ( '<', '>', UNICODE_APPROX_EQUAL ):
                
                op = UNICODE_APPROX_EQUAL
                
            
            parse_result.text_remainder = string[ len( match[ 0 ] ): ]
            parse_result.operator = ( namespace, op )
            
            return
            
        
        raise ValueError( "Invalid operator, expected a tag followed by a relational operator" )
        
    elif spec == Operators.ONLY_EQUAL:
        
        for possible_operator_str in [ '==', '=', 'is' ]:
            
            if string.startswith( possible_operator_str ):
                
                parse_result.text_remainder = string[ len( possible_operator_str ) : ]
                parse_result.operator = '='
                
                return
                
            
        
        raise ValueError( "Invalid equality operator" )
        
    elif spec == Operators.RATIO_OPERATORS:
        
        for ( possible_operator_str, possible_operator ) in [
            ( 'wider than', 'wider than' ),
            ( 'taller than', 'taller than' ),
            ( 'is wider than', 'wider than' ),
            ( 'is taller than', 'taller than' ),
            ( '==', '=' ),
            ( '=', '=' ),
            ( 'is', '=' ),
            ( '~=', UNICODE_APPROX_EQUAL ),
            ( UNICODE_APPROX_EQUAL, UNICODE_APPROX_EQUAL ),
        ]:
            
            if string.startswith( possible_operator_str ):
                
                parse_result.text_remainder = string[ len( possible_operator_str ) : ]
                parse_result.operator = possible_operator
                
                return
                
            
        
        raise ValueError( "Invalid ratio operator" )
        
    elif spec == Operators.RATIO_OPERATORS_SPECIAL:
        
        for ( possible_operator_str, possible_operator ) in [
            ( 'square', '=' ),
            ( 'portrait', 'taller than' ),
            ( 'landscape', 'wider than' ),
        ]:
            
            if possible_operator_str in string:
                
                parse_result.text_remainder = ''
                parse_result.operator = possible_operator
                parse_result.value = ( 1, 1 )
                
                return
                
            
        
    elif spec == Operators.TAG_ADVANCED_GUBBINS:
        
        # a combination of these optional phrases:
        # in "service",
        # ignoring siblings/parents,
        # with status in [CDPP list]
        # all separated by commas
        
        # 'split by all the colons that are non-capturing followed by pairs of ", allowing for non-" before, inbetween, and after'
        regex_that_matches_a_colon_not_in_quotes = r'\:(?=(?:[^"]*"[^"]*")*[^"]*$)'
        regex_that_matches_a_comma_not_in_quotes = r',(?=(?:[^"]*"[^"]*")*[^"]*$)'
        
        if re.search( regex_that_matches_a_colon_not_in_quotes, string ) is None:
            
            if re.search( regex_that_matches_a_comma_not_in_quotes, string ) is None:
                
                # unusual situation of 'system:has tag "blah"', or just 'system:has tag: "blah"' that the above parser eats the colon of
                
                ( gubbins, tag ) = ( '', string )
                
            else:
                
                raise Exception( 'Did not see a tag in the predicate string!' )
                
            
        else:
            
            result = re.split( regex_that_matches_a_colon_not_in_quotes, string, 1 )
            
            ( gubbins, tag ) = result
            
        
        components = re.split( regex_that_matches_a_comma_not_in_quotes, gubbins )
        
        from hydrus.client.metadata import ClientTags
        from hydrus.core import HydrusConstants as HC
        
        service_key = None
        tag_display_type = ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL
        statuses = []
        
        for component in components:
            
            regex_that_groups_a_thing_inside_quotes = r'^[^"]*"(?P<name>.+)"[^"]*$'
            
            if re.match( regex_that_groups_a_thing_inside_quotes, component ) is not None: # this one first, in order to catch the service sensibly called "current pending ignoring siblings"
                
                from hydrus.client import ClientGlobals as CG
                from hydrus.core import HydrusExceptions
                
                match = re.match( regex_that_groups_a_thing_inside_quotes, component )
                
                name = match.group( 'name' )
                
                try:
                    
                    service_key = CG.client_controller.services_manager.GetServiceKeyFromName( HC.ALL_TAG_SERVICES, name )
                    
                except HydrusExceptions.DataMissing:
                    
                    raise Exception( f'Sorry, did not find a service called "{name}"!' )
                    
                
            elif 'siblings' in component or 'parents' in component:
                
                tag_display_type = ClientTags.TAG_DISPLAY_STORAGE
                
            else:
                
                for ( status, s ) in HC.content_status_string_lookup.items():
                    
                    if s in component:
                        
                        statuses.append( status )
                        
                    
                
            
        
        if len( statuses ) == 0:
            
            statuses = [ HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ]
            
        
        parse_result.text_remainder = tag
        parse_result.operator = ( service_key, tag_display_type, tuple( sorted( statuses ) ) )
        
        return
        
    
    raise ValueError( "Invalid operator specification" )
    

def parse_operator_relational( string: str, spec ):
    
    exact = spec == Operators.RELATIONAL_EXACT
    
    ops = [ '=', '<', '>' ]
    
    if spec == Operators.RELATIONAL_TIME:
        
        re_result = re.search( r'\d.*', string )
        
        if re_result:
            
            op_string = string[ : re_result.start() ]
            string_result = re_result.group()
            
            looks_like_date = string_looks_like_date( string_result )
            invert_ops = not looks_like_date
            
            if 'month' in op_string and looks_like_date:
                
                return ( string_result, UNICODE_APPROX_EQUAL )
                
            elif 'around' in op_string and not looks_like_date:
                
                return ( string_result, UNICODE_APPROX_EQUAL )
                
            elif 'day' in op_string and looks_like_date:
                
                return ( string_result, '=' )
                
            elif 'since' in op_string:
                
                return ( string_result, '<' if invert_ops else '>' )
                
            elif 'before' in op_string:
                
                return ( string_result, '>' if invert_ops else '<' )
                
            
        
    
    if not exact:
        ops = ops + [ UNICODE_NOT_EQUAL, UNICODE_APPROX_EQUAL ]
    if string.startswith( '==' ): return string[ 2: ], '='
    if not exact:
        if string.startswith( '!=' ): return string[ 2: ], UNICODE_NOT_EQUAL
        if string.startswith( 'is not' ): return string[ 6: ], UNICODE_NOT_EQUAL
        if string.startswith( 'isn\'t' ): return string[ 5: ], UNICODE_NOT_EQUAL
        if string.startswith( '~=' ): return string[ 2: ], UNICODE_APPROX_EQUAL
    for op in ops:
        if string.startswith( op ): return string[ len( op ): ], op
    if string.startswith( 'is' ): return string[ 2: ], '='
    
    # TODO: Ok one thing it would be nice to do is checking this state in _some other place_ and then returning the 'numbertest( > 0 )' in one go
    if string.startswith( 'has' ): return string, '>'
    if string.startswith( 'no' ): return string, '='
    
    raise ValueError( "Invalid relational operator" )
    
