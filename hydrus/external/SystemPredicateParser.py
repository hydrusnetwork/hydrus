# made by prkc for Hydrus Network
# Licensed under the same terms as Hydrus Network
# hydev has changed a couple things here and there

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
    MEDIA_VIEWTIME = auto()
    PREVIEW_VIEWTIME = auto()
    ALL_VIEWTIME = auto()
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
    TIME_SEC_MSEC = auto()  # A tuple of two non-negative integers: (seconds, milliseconds) where the latter is <1000
    ANY_STRING = auto()  # A string (accepts any string so can't use units after this since it consumes the entire remaining part of the input)
    TIME_INTERVAL = auto()  # A tuple of 4 non-negative integers: (days, hours, minutes, seconds) where hours < 24, minutes < 60, seconds < 60
    INTEGER = auto()  # An integer
    RATIO = auto()  # A tuple of 2 ints, both non-negative
    RATIO_SPECIAL = auto() # 1:1
    RATING_SERVICE_NAME_AND_NUMERICAL_VALUE = auto() # my favourites 3/5
    RATING_SERVICE_NAME_AND_LIKE_DISLIKE = auto() # my favourites like
    RATING_SERVICE_NAME_AND_INCDEC = auto() # my favourites 3/5
    NAMESPACE_AND_NUM_TAGS = auto()


# Possible operator formats
# Implemented in parse_operator
class Operators( Enum ):
    RELATIONAL = auto()  # One of '=', '<', '>', UNICODE_APPROX_EQUAL ('≈') (takes '~=' too)
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
    'num(ber)?( of)? (?=[^\\s].* tags)': (Predicate.NUM_OF_TAGS_WITH_NAMESPACE, None, Value.NAMESPACE_AND_NUM_TAGS, None),
    'num(ber)?( of)? urls': (Predicate.NUM_OF_URLS, Operators.RELATIONAL, Value.NATURAL, None),
    'num(ber)?( of)? words': (Predicate.NUM_OF_WORDS, Operators.RELATIONAL_EXACT, Value.NATURAL, None),
    'height': (Predicate.HEIGHT, Operators.RELATIONAL, Value.NATURAL, Units.PIXELS_OR_NONE),
    'width': (Predicate.WIDTH, Operators.RELATIONAL, Value.NATURAL, Units.PIXELS_OR_NONE),
    'file ?size': (Predicate.FILESIZE, Operators.RELATIONAL, Value.NATURAL, Units.FILESIZE),
    'similar to(?! data)( files)?': (Predicate.SIMILAR_TO_FILES, None, Value.SHA256_HASHLIST_WITH_DISTANCE, None),
    'similar to data': (Predicate.SIMILAR_TO_DATA, None, Value.SIMILAR_TO_HASHLIST_WITH_DISTANCE, None),
    'limit': (Predicate.LIMIT, Operators.ONLY_EQUAL, Value.NATURAL, None),
    'file ?type': (Predicate.FILETYPE, Operators.ONLY_EQUAL, Value.FILETYPE_LIST, None),
    'hash': (Predicate.HASH, Operators.EQUAL_NOT_CONSUMING, Value.HASHLIST_WITH_ALGORITHM, None),
    'archived? (date|time)|(date|time) archived|archived.': (Predicate.ARCHIVED_DATE, Operators.RELATIONAL_TIME, Value.DATE_OR_TIME_INTERVAL, None),
    'modified (date|time)|(date|time) modified|modified': (Predicate.MOD_DATE, Operators.RELATIONAL_TIME, Value.DATE_OR_TIME_INTERVAL, None),
    'last view(ed)? (date|time)|(date|time) last viewed|last viewed': (Predicate.LAST_VIEWED_TIME, Operators.RELATIONAL_TIME, Value.DATE_OR_TIME_INTERVAL, None),
    'import(ed)? (date|time)|(date|time) imported|imported': (Predicate.TIME_IMPORTED, Operators.RELATIONAL_TIME, Value.DATE_OR_TIME_INTERVAL, None),
    'duration': (Predicate.DURATION, Operators.RELATIONAL, Value.TIME_SEC_MSEC, None),
    'framerate': (Predicate.FRAMERATE, Operators.RELATIONAL_EXACT, Value.NATURAL, Units.FPS_OR_NONE),
    'num(ber)?( of)? frames': (Predicate.NUM_OF_FRAMES, Operators.RELATIONAL, Value.NATURAL, None),
    'file service': (Predicate.FILE_SERVICE, Operators.FILESERVICE_STATUS, Value.ANY_STRING, None),
    'num(ber)?( of)? file relationships': (Predicate.NUM_FILE_RELS, Operators.RELATIONAL, Value.NATURAL, Units.FILE_RELATIONSHIP_TYPE),
    'ratio(?=.*\d)': (Predicate.RATIO, Operators.RATIO_OPERATORS, Value.RATIO, None),
    'ratio(?!.*\d)': (Predicate.RATIO_SPECIAL, Operators.RATIO_OPERATORS_SPECIAL, Value.RATIO_SPECIAL, None),
    'num pixels': (Predicate.NUM_PIXELS, Operators.RELATIONAL, Value.NATURAL, Units.PIXELS),
    'media views': (Predicate.MEDIA_VIEWS, Operators.RELATIONAL, Value.NATURAL, None),
    'preview views': (Predicate.PREVIEW_VIEWS, Operators.RELATIONAL, Value.NATURAL, None),
    'all views': (Predicate.ALL_VIEWS, Operators.RELATIONAL, Value.NATURAL, None),
    'media viewtime': (Predicate.MEDIA_VIEWTIME, Operators.RELATIONAL, Value.TIME_INTERVAL, None),
    'preview viewtime': (Predicate.PREVIEW_VIEWTIME, Operators.RELATIONAL, Value.TIME_INTERVAL, None),
    'all viewtime': (Predicate.ALL_VIEWTIME, Operators.RELATIONAL, Value.TIME_INTERVAL, None),
    'has (a )?url matching regex': (Predicate.URL_REGEX, None, Value.ANY_STRING, None),
    '(does not|doesn\'t) have (a )?url matching regex': (Predicate.NO_URL_REGEX, None, Value.ANY_STRING, None),
    'has url': (Predicate.URL, None, Value.ANY_STRING, None),
    '(does not|doesn\'t) have url': (Predicate.NO_URL, None, Value.ANY_STRING, None),
    'has (a )?(url with )?domain': (Predicate.DOMAIN, None, Value.ANY_STRING, None),
    '(does not|doesn\'t) have (a )?(url with )?domain': (Predicate.NO_DOMAIN, None, Value.ANY_STRING, None),
    'has (a )?url with (url )?class': (Predicate.URL_CLASS, None, Value.ANY_STRING, None),
    '(does not|doesn\'t) have (a )?url with (url )?class': (Predicate.NO_URL_CLASS, None, Value.ANY_STRING, None),
    'tag as number': (Predicate.TAG_AS_NUMBER, Operators.TAG_RELATIONAL, Value.INTEGER, None),
    'has notes?$': (Predicate.HAS_NOTES, None, None, None),
    '((has )?no|does not have( a)?|doesn\'t have) notes?$': (Predicate.NO_NOTES, None, None, None),
    'num(ber)?( of)? notes?': (Predicate.NUM_NOTES, Operators.RELATIONAL_EXACT, Value.NATURAL, None),
    '(has (a )?)?note (with name|named)': (Predicate.HAS_NOTE_NAME, None, Value.ANY_STRING, None),
    '((has )?no|does not have( a)?|doesn\'t have( a)?) note (with name|named)': (Predicate.NO_NOTE_NAME, None, Value.ANY_STRING, None),
    'has( a)? rating( for)?': (Predicate.HAS_RATING, None, Value.ANY_STRING, None ),
    '((has )?no|does not have( a)?|doesn\'t have( a)?) rating( for)?': (Predicate.NO_RATING, None, Value.ANY_STRING, None ),
    'rating( for)?(?=.+?\d+/\d+$)': (Predicate.RATING_SPECIFIC_NUMERICAL, Operators.RELATIONAL_FOR_RATING_SERVICE, Value.RATING_SERVICE_NAME_AND_NUMERICAL_VALUE, None ),
    'rating( for)?(?=.+?(like|dislike)$)': (Predicate.RATING_SPECIFIC_LIKE_DISLIKE, None, Value.RATING_SERVICE_NAME_AND_LIKE_DISLIKE, None ),
    'rating( for)?(?=.+?[^/]\d+$)': (Predicate.RATING_SPECIFIC_INCDEC, Operators.RELATIONAL_FOR_RATING_SERVICE, Value.RATING_SERVICE_NAME_AND_INCDEC, None ),
}

def string_looks_like_date( string ):
    
    # this sucks but it will do for now
    
    test_words = [ 'year', 'month', 'day', 'hour', 'second', 'ago' ]
    
    return True not in ( word in string for word in test_words )
    

# Parsing is just finding a matching predicate name,
# then trying to parse it by consuming the input string.
# The parse_* functions consume some of the string and return a (remaining part of the string, parsed value) tuple.
def parse_system_predicate( string: str ):
    
    # TODO: (hydev): rework this thing into passing around a 'parse result object' that the operator parser can set a value for and say 'yeah value is sorted' for things like 'has words' = '> 0' in one swoop
    
    string = string.lower().strip()
    string = string.replace( '_', ' ' )
    if string.startswith( "-" ):
        raise ValueError( "System predicate can't start with negation" )
    if not string.startswith( SYSTEM_PREDICATE_PREFIX ):
        raise ValueError( "Not a system predicate!" )
    string = string[ len( SYSTEM_PREDICATE_PREFIX ): ]
    for pred_regex in SYSTEM_PREDICATES:
        match = re.match( pred_regex.replace( ' ', '([_ ]+)' ) + ":?", string )
        if match:
            pred = SYSTEM_PREDICATES[ pred_regex ]
            string = string[ len( match[ 0 ] ): ]
            string, operator = parse_operator( string, pred[ 1 ] )
            string, value = parse_value( string, pred[ 2 ] )
            string, unit = parse_unit( string, pred[ 3 ] )
            if string: raise ValueError( "Unrecognized characters at the end of the predicate: " + string )
            return pred[ 0 ], operator, value, unit
            
        
    
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
    

def parse_value( string: str, spec ):
    
    string = string.strip()
    
    if spec is None:
        
        return string, None
        
    elif spec in ( Value.NATURAL, Value.INTEGER ):
        
        # 'has urls', 'has words'
        if string.startswith( 'has' ) or string.startswith( 'no' ):
            
            return '', 0
            
        
        match = re.match( '-?[0-9,]+', string )
        
        if match:
            
            rest_of_string = string[ len( match[ 0 ] ): ]
            
            value_text = match[ 0 ]
            
            value_text = value_text.replace( ',', '' )
            
            value = int( value_text )
            
            if spec == Value.NATURAL and value < 0:
                
                raise ValueError( "Invalid value, expected a positive integer!" )
                
            
            return ( rest_of_string, value )
            
        
        if spec == Value.NATURAL:
            
            raise ValueError( "Invalid value, expected a natural number" )
            
        else:
            
            raise ValueError( "Invalid value, expected an integer" )
            
        
    elif spec == Value.SHA256_HASHLIST_WITH_DISTANCE:
        match = re.match( '(?P<hashes>([0-9a-f]{4}[0-9a-f]+(\s|,)*)+)(with\s+)?(distance\s+)?(of\s+)?(?P<distance>0|([1-9][0-9]*))?', string )
        if match:
            hashes = set( hsh.strip() for hsh in re.sub( '\s', ' ', match[ 'hashes' ].replace( ',', ' ' ) ).split( ' ' ) if len( hsh ) > 0 )
            
            d = match.groupdict()
            
            if 'distance' in d and d[ 'distance' ] is not None:
                
                distance = int( match[ 'distance' ] )
                
            else:
                
                distance = 4
                
            
            return string[ len( match[ 0 ] ): ], (hashes, distance)
        raise ValueError( "Invalid value, expected a list of hashes with distance" )
    elif spec == Value.SIMILAR_TO_HASHLIST_WITH_DISTANCE:
        match = re.match( '(?P<hashes>([0-9a-f]{4}[0-9a-f]+(\s|,)*)+)(with\s+)?(distance\s+)?(of\s+)?(?P<distance>0|([1-9][0-9]*))?', string )
        if match:
            hashes = set( hsh.strip() for hsh in re.sub( '\s', ' ', match[ 'hashes' ].replace( ',', ' ' ) ).split( ' ' ) if len( hsh ) > 0 )
            pixel_hashes = { hash for hash in hashes if len( hash ) == 64 }
            perceptual_hashes = { hash for hash in hashes if len( hash ) == 16 }
            
            d = match.groupdict()
            
            if 'distance' in d and d[ 'distance' ] is not None:
                
                distance = int( match[ 'distance' ] )
                
            else:
                
                distance = 8
                
            
            return string[ len( match[ 0 ] ): ], (pixel_hashes, perceptual_hashes, distance)
        raise ValueError( "Invalid value, expected a list of hashes with distance" )
    elif spec == Value.HASHLIST_WITH_ALGORITHM:
        
        # hydev KISS hijack here, instead of clever regex to capture algorithm in all sorts of situations, let's just grab the hex we see and scan the rest for non-hex phrases mate
        # old pattern: match = re.match( '(?P<hashes>([0-9a-f]+(\s|,)*)+)((with\s+)?algorithm)?\s*(?P<algorithm>sha256|sha512|md5|sha1|)', string )
        
        algorithm = 'sha256'
        
        for possible_algorithm in ( 'md5', 'sha1', 'sha512' ):
            
            if possible_algorithm in string:
                
                algorithm = possible_algorithm
                
                break
                
            
        
        # {8} here to make sure we are looking at proper hash hex and not some short 'a' or 'de' word
        match = re.search( '(?P<hashes>([0-9a-f]{8}[0-9a-f]+(\s|,)*)+)', string )
        
        if match:
            hashes = set( hsh.strip() for hsh in re.sub( '\s', ' ', match[ 'hashes' ].replace( ',', ' ' ) ).split( ' ' ) if len( hsh ) > 0 )
            return string[ match.endpos : ], (hashes, algorithm)
        
        raise ValueError( "Invalid value, expected a list of hashes and perhaps an algorithm" )
        
    
    elif spec == Value.FILETYPE_LIST:
        
        valid_values = sorted( FILETYPES.keys(), key = lambda k: len( k ), reverse = True )
        ftype_regex = '(' + '|'.join( [ '(' + val + ')' for val in valid_values ] ) + ')'
        match = re.match( '(' + ftype_regex + '(\s|,)+)*' + ftype_regex, string )
        
        if match:
            
            found_ftypes_all = re.sub( '\s', ' ', match[ 0 ].replace( ',', '|' ) ).split( '|' )
            found_ftypes_good = [ ]
            for ftype in found_ftypes_all:
                ftype = ftype.strip()
                if len( ftype ) > 0 and ftype in FILETYPES:
                    found_ftypes_good.extend( FILETYPES[ ftype ] )
            return string[ len( match[ 0 ] ): ], set( found_ftypes_good )
            
        
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
                    
                    return ( '', dt )
                    
                
                return ( '', ( years, months, days, hours ) )
                
            else:
                
                return ( '', dt )
                
            
        else:
            
            match = re.match( '((?P<year>0|([1-9][0-9]*))\s*(years|year))?\s*((?P<month>0|([1-9][0-9]*))\s*(months|month))?\s*((?P<day>0|([1-9][0-9]*))\s*(days|day))?\s*((?P<hour>0|([1-9][0-9]*))\s*(hours|hour|h))?', string )
            if match and (match.group( 'year' ) or match.group( 'month' ) or match.group( 'day' ) or match.group( 'hour' )):
                years = int( match.group( 'year' ) ) if match.group( 'year' ) else 0
                months = int( match.group( 'month' ) ) if match.group( 'month' ) else 0
                days = int( match.group( 'day' ) ) if match.group( 'day' ) else 0
                hours = int( match.group( 'hour' ) ) if match.group( 'hour' ) else 0
                
                string_result = string[ len( match[ 0 ] ): ]
                
                if string_result == 'ago':
                    
                    string_result = ''
                    
                
                return string_result, (years, months, days, hours)
                
            
            match = re.match( '(?P<year>[0-9][0-9][0-9][0-9])-(?P<month>[0-9][0-9]?)-(?P<day>[0-9][0-9]?)', string )
            if match:
                # good expansion here would be to parse a full date with 08:20am kind of thing, but we'll wait for better datetime parsing library for that I think!
                return string[ len( match[ 0 ] ): ], datetime.datetime( int( match.group( 'year' ) ), int( match.group( 'month' ) ), int( match.group( 'day' ) ) )
            raise ValueError( "Invalid value, expected a date or a time interval" )
            
        
    elif spec == Value.TIME_SEC_MSEC:
        match = re.match( '((?P<sec>0|([1-9][0-9]*))\s*(seconds|second|secs|sec|s))?\s*((?P<msec>0|([1-9][0-9]*))\s*(milliseconds|millisecond|msecs|msec|ms))?', string )
        if match and (match.group( 'sec' ) or match.group( 'msec' )):
            seconds = int( match.group( 'sec' ) ) if match.group( 'sec' ) else 0
            mseconds = int( match.group( 'msec' ) ) if match.group( 'msec' ) else 0
            seconds += math.floor( mseconds / 1000 )
            mseconds = mseconds % 1000
            return string[ len( match[ 0 ] ): ], (seconds, mseconds)
        raise ValueError( "Invalid value, expected a duration" )
    elif spec == Value.ANY_STRING:
        return "", string
    elif spec == Value.TIME_INTERVAL:
        match = re.match( '((?P<day>0|([1-9][0-9]*))\s*(days|day))?\s*((?P<hour>0|([1-9][0-9]*))\s*(hours|hour|h))?\s*((?P<minute>0|([1-9][0-9]*))\s*(minutes|minute|mins|min))?\s*((?P<second>0|([1-9][0-9]*))\s*(seconds|second|secs|sec|s))?', string )
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
            return string[ len( match[ 0 ] ): ], (days, hours, minutes, seconds)
        raise ValueError( "Invalid value, expected a time interval" )
    elif spec == Value.RATIO:
        match = re.match( '(?P<first>0|([1-9][0-9]*)):(?P<second>0|([1-9][0-9]*))', string )
        if match: return string[ len( match[ 0 ] ): ], (int( match[ 'first' ] ), int( match[ 'second' ] ))
        raise ValueError( "Invalid value, expected a ratio" )
    elif spec == Value.RATIO_SPECIAL:
        
        if string == 'square': return ( '', ( 1, 1 ) )
        if string == 'landscape': return ( '', ( 1, 1 ) )
        if string == 'portrait': return ( '', ( 1, 1 ) )
        
    elif spec == Value.RATING_SERVICE_NAME_AND_NUMERICAL_VALUE:
        
        # 'my favourites 3/5' (no operator here)
        
        match = re.match( '(?P<name>.+?)\s+(?P<num>\d+)/(?P<den>\d+)$', string )
        
        if match:
            
            service_name = match[ 'name' ]
            numerator = int( match[ 'num' ] )
            denominator = int( match[ 'den' ] )
            
            if numerator < 0 or numerator > denominator:
                
                raise ValueError( 'Invalid value, rating value was out of bounds')
                
            
            return ( '', ( numerator, service_name ) )
            
        
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
        
        return ( '', ( value, service_name ) )
        
    elif spec == Value.RATING_SERVICE_NAME_AND_INCDEC:
        
        # 'I'm cooooollecting counter 123' (no operator here)
        
        match = re.match( '(?P<name>.+?)\s+(?P<num>\d+)$', string )
        
        if match:
            
            service_name = match[ 'name' ]
            value = int( match[ 'num' ] )
            
            return ( '', ( value, service_name ) )
            
        
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
            
            
            ( gubbins, operator ) = parse_operator( operator_string, Operators.RELATIONAL )
            
            return ( '', ( namespace, operator, num ) )
            
        
    
    raise ValueError( "Invalid value specification" )
    

def parse_operator( string: str, spec ):
    
    while string.startswith( ':' ) or string.startswith( ' ' ):
        
        string = string.strip()
        
        if string.startswith( ':' ):
            
            string = string[ 1 : ]
            
        
    
    if spec is None:
        return string, None
    elif spec in ( Operators.RELATIONAL, Operators.RELATIONAL_EXACT, Operators.RELATIONAL_TIME ):
        exact = spec == Operators.RELATIONAL_EXACT
        ops = [ '=', '<', '>' ]
        
        if spec == Operators.RELATIONAL_TIME:
            
            re_result = re.search( r'\d.*', string )
            
            if re_result:
                
                op_string = string[ : re_result.start() ]
                string_result = re_result.group()
                
                invert_ops = not string_looks_like_date( string_result )
                
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
        if string.startswith( 'has' ): return string, '>'
        if string.startswith( 'no' ): return string, '='
        raise ValueError( "Invalid relational operator" )
    elif spec == Operators.RELATIONAL_FOR_RATING_SERVICE:
        
        # "favourites service name > 3/5"
        # since service name can be all sorts of gubbins, we'll work backwards and KISS
        match = re.match( '(?P<first>.*?)(?P<second>(dislike|like|\d+/\d+|\d+))$', string )
        
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
                    
                    return ( parsing_string, possible_operator )
                    
                
            
        raise ValueError( "Invalid rating operator" )
    elif spec == Operators.EQUAL:
        if string.startswith( '==' ): return string[ 2: ], '='
        if string.startswith( UNICODE_NOT_EQUAL ): return string[ 1: ], '!='
        if string.startswith( '!=' ): return string[ 2: ], '!='
        if string.startswith( '=' ): return string[ 1: ], '='
        if string.startswith( 'is not' ): return string[ 6: ], '!='
        if string.startswith( 'isn\'t' ): return string[ 5: ], '!='
        if string.startswith( 'is' ): return string[ 2: ], '='
        raise ValueError( "Invalid equality operator" )
    elif spec == Operators.EQUAL_NOT_CONSUMING:
        
        # hydev checking in here with some nonsense that catches an awkward situation
        # system:hash (md5) = blah
        # we want to see the = but not eat the md5, so in this special case, which isn't hard to parse otherwise, we'll just look for it and return no changes
        
        if '==' in string: return string, '='
        if UNICODE_NOT_EQUAL in string: return string, '!='
        if '!=' in string: return string, '!='
        if '=' in string: return string, '='
        if 'is not' in string: return string, '!='
        if 'isn\'t' in string: return string, '!='
        if 'is' in string: return string, '='
        raise ValueError( "Invalid equality operator" )
    elif spec == Operators.FILESERVICE_STATUS:
        match = re.match( '(is )?currently in', string )
        if match: return string[ len( match[ 0 ] ): ], 'is currently in'
        match = re.match( '((is )?not currently in)|isn\'t currently in', string )
        if match: return string[ len( match[ 0 ] ): ], 'is not currently in'
        match = re.match( '(is )?pending to', string )
        if match: return string[ len( match[ 0 ] ): ], 'is pending to'
        match = re.match( '((is )?not pending to)|isn\'t pending to', string )
        if match: return string[ len( match[ 0 ] ): ], 'is not pending to'
        raise ValueError( "Invalid operator, expected a file service relationship" )
    elif spec == Operators.TAG_RELATIONAL:
        
        # note this is in the correct order, also, to eliminate = vs == ambiguity
        all_operators_piped = '|'.join( ( s_r[0] for s_r in operator_strings_and_results ) )
        
        match = re.match( f'(?P<namespace>.*)\s+(?P<op>({all_operators_piped}))', string )
        
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
                
            
            return string[ len( match[ 0 ] ): ], (namespace, op)
            
        
        raise ValueError( "Invalid operator, expected a tag followed by a relational operator" )
        
    elif spec == Operators.ONLY_EQUAL:
        if string.startswith( '==' ): return string[ 2: ], '='
        if string.startswith( '=' ): return string[ 1: ], '='
        if string.startswith( 'is' ): return string[ 2: ], '='
        raise ValueError( "Invalid equality operator" )
    elif spec == Operators.RATIO_OPERATORS:
        if string.startswith( 'wider than' ): return string[ 10: ], 'wider than'
        if string.startswith( 'taller than' ): return string[ 11: ], 'taller than'
        if string.startswith( 'is wider than' ): return string[ 13: ], 'wider than'
        if string.startswith( 'is taller than' ): return string[ 14: ], 'taller than'
        if string.startswith( '==' ): return string[ 2: ], '='
        if string.startswith( '=' ): return string[ 1: ], '='
        if string.startswith( 'is' ): return string[ 2: ], '='
        if string.startswith( '~=' ): return string[ 2: ], UNICODE_APPROX_EQUAL
        if string.startswith( UNICODE_APPROX_EQUAL ): return string[ 1: ], UNICODE_APPROX_EQUAL
        raise ValueError( "Invalid ratio operator" )
    elif spec == Operators.RATIO_OPERATORS_SPECIAL:
        
        if 'square' in string: return 'square', '='
        if 'portrait' in string: return 'portrait', 'taller than'
        if 'landscape' in string: return 'landscape', 'wider than'
        
    
    raise ValueError( "Invalid operator specification" )
    
