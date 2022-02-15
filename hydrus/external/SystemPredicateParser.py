#made by prkc for Hydrus Network
#Licensed under the same terms as Hydrus Network
# hydev has changed a couple things here and there, and changed how filetypes work

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

import math
import re
import datetime
from enum import Enum, auto

# This needs to be updated with all types that Hydrus supports.
FILETYPES = {}

def InitialiseFiletypes( str_to_enum ):
    
    for ( filetype_string, enum ) in str_to_enum.items():
        
        if isinstance( enum, int ):
            
            enum_tuple = ( enum, )
            
        else:
            
            enum_tuple = tuple( enum )
            
        
        if '/' in filetype_string:
            
            ( filetype_class, specific_filetype ) = filetype_string.split( '/', 1 )
            
            FILETYPES[ specific_filetype ] = enum_tuple
            
        
        FILETYPES[ filetype_string ] = enum_tuple
        
    

NAMESPACE_SEPARATOR = ':'
SYSTEM_PREDICATE_PREFIX = 'system'+NAMESPACE_SEPARATOR

# This enum lists all the recognized predicate types.
class Predicate(Enum):
    EVERYTHING = auto()
    INBOX = auto()
    ARCHIVE = auto()
    HAS_DURATION = auto()
    NO_DURATION = auto()
    BEST_QUALITY_OF_GROUP = auto()
    NOT_BEST_QUALITY_OF_GROUP = auto()
    HAS_AUDIO = auto()
    NO_AUDIO = auto()
    HAS_ICC_PROFILE = auto()
    NO_ICC_PROFILE = auto()
    HAS_TAGS = auto()
    UNTAGGED = auto()
    NUM_OF_TAGS = auto()
    NUM_OF_WORDS = auto()
    HEIGHT = auto()
    WIDTH = auto()
    FILESIZE = auto()
    SIMILAR_TO = auto()
    LIMIT = auto()
    FILETYPE = auto()
    HASH = auto()
    MOD_DATE = auto()
    LAST_VIEWED_TIME = auto()
    TIME_IMPORTED = auto()
    DURATION = auto()
    FILE_SERVICE = auto()
    NUM_FILE_RELS = auto()
    RATIO = auto()
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

# This enum lists the possible value formats a predicate can have (if it has a value).
# Parsing for each of these options is implemented in parse_value
class Value(Enum):
    NATURAL = auto() #An int which holds a non-negative value
    HASHLIST_WITH_DISTANCE = auto() #A 2-tuple, where the first part is a set of potential hashes (as strings), the second part is a non-negative integer
    HASHLIST_WITH_ALGORITHM = auto() #A 2-tuple, where the first part is a set of potential hashes (as strings), the second part is one of 'sha256', 'md5', 'sha1', 'sha512'
    FILETYPE_LIST = auto() #A set of file types using the enum set in InitialiseFiletypes as defined in FILETYPES
    #Either a tuple of 4 non-negative integers: (years, months, days, hours) where the latter is < 24 OR
    #a datetime.date object. For the latter, only the YYYY-MM-DD format is accepted.
    #dateutils has a function to try to guess and parse arbitrary date formats but I didn't use it here since it would be an additional dependency.
    DATE_OR_TIME_INTERVAL = auto()
    TIME_SEC_MSEC = auto() #A tuple of two non-negative integers: (seconds, milliseconds) where the latter is <1000
    ANY_STRING = auto() #A string (accepts any string so can't use units after this since it consumes the entire remaining part of the input)
    TIME_INTERVAL = auto() #A tuple of 4 non-negative integers: (days, hours, minutes, seconds) where hours < 24, minutes < 60, seconds < 60
    INTEGER = auto() #An integer
    RATIO = auto() #A tuple of 2 ints, both non-negative

# Possible operator formats
# Implemented in parse_operator
class Operators(Enum):
    RELATIONAL = auto() #One of '=', '<', '>', '\u2248' ('≈') (takes '~=' too)
    EQUAL = auto() #One of '=' or '!='
    FILESERVICE_STATUS = auto() #One of 'is not currently in', 'is currently in', 'is not pending to', 'is pending to'
    TAG_RELATIONAL = auto() #A tuple of a string (a potential tag name) and a relational operator (as a string)
    ONLY_EQUAL = auto() #None (meaning =, since thats the only accepted operator)
    RATIO_OPERATORS = auto() #One of '=', 'wider than','taller than', '\u2248' ('≈') (takes '~=' too)

# Possible unit formats
# Implemented in parse_unit
class Units(Enum):
    FILESIZE = auto() #One of 'B', 'KB', 'MB', 'GB'
    FILE_RELATIONSHIP_TYPE = auto() #One of 'not related/false positive', 'duplicates', 'alternates', 'potential duplicates'
    PIXELS_OR_NONE = auto() #Always None (meaning pixels)
    PIXELS = auto() #One of 'pixels', 'kilopixels', 'megapixels'

# All system predicates
# A predicate is described by a 4-tuple of (predicate type, operator format, value format, unit format) (use None if some are not applicable)
# The keys are regexes matching the predicate names as written by the user.
# The parser will also automatically accept _ instead of space in the predicate names, always use space in this dict.
SYSTEM_PREDICATES = {
    'everything': (Predicate.EVERYTHING, None, None, None),
    'inbox': (Predicate.INBOX, None, None, None),
    'archive': (Predicate.ARCHIVE, None, None, None),
    'has duration': (Predicate.HAS_DURATION, None, None, None),
    'no duration': (Predicate.NO_DURATION, None, None, None),
    '(is the )?best quality( file)? of( its)?( duplicate)? group': (Predicate.BEST_QUALITY_OF_GROUP, None, None, None),
    '(((is )?not)|(isn\'t))( the)? best quality( file)? of( its)?( duplicate)? group': (Predicate.NOT_BEST_QUALITY_OF_GROUP, None, None, None),
    'has audio': (Predicate.HAS_AUDIO, None, None, None),
    'no audio': (Predicate.NO_AUDIO, None, None, None),
    'has icc profile': (Predicate.HAS_ICC_PROFILE, None, None, None),
    'no icc profile': (Predicate.NO_ICC_PROFILE, None, None, None),
    'has tags': (Predicate.HAS_TAGS, None, None, None),
    'untagged|no tags': (Predicate.UNTAGGED, None, None, None),
    'number of tags': (Predicate.NUM_OF_TAGS, Operators.RELATIONAL, Value.NATURAL, None),
    'number of words': (Predicate.NUM_OF_WORDS, Operators.RELATIONAL, Value.NATURAL, None),
    'height': (Predicate.HEIGHT, Operators.RELATIONAL, Value.NATURAL, Units.PIXELS_OR_NONE),
    'width': (Predicate.WIDTH, Operators.RELATIONAL, Value.NATURAL, Units.PIXELS_OR_NONE),
    'file ?size': (Predicate.FILESIZE, Operators.RELATIONAL, Value.NATURAL, Units.FILESIZE),
    'similar to': (Predicate.SIMILAR_TO, None, Value.HASHLIST_WITH_DISTANCE, None),
    'limit': (Predicate.LIMIT, Operators.ONLY_EQUAL, Value.NATURAL, None),
    'file ?type': (Predicate.FILETYPE, Operators.ONLY_EQUAL, Value.FILETYPE_LIST, None),
    'hash': (Predicate.HASH, Operators.ONLY_EQUAL, Value.HASHLIST_WITH_ALGORITHM, None),
    'modified date|date modified': (Predicate.MOD_DATE, Operators.RELATIONAL, Value.DATE_OR_TIME_INTERVAL, None),
    'last viewed time|last view time': (Predicate.LAST_VIEWED_TIME, Operators.RELATIONAL, Value.DATE_OR_TIME_INTERVAL, None),
    'time imported|import time': (Predicate.TIME_IMPORTED, Operators.RELATIONAL, Value.DATE_OR_TIME_INTERVAL, None),
    'duration': (Predicate.DURATION, Operators.RELATIONAL, Value.TIME_SEC_MSEC, None),
    'file service': (Predicate.FILE_SERVICE, Operators.FILESERVICE_STATUS, Value.ANY_STRING, None),
    'num(ber of)? file relationships': (Predicate.NUM_FILE_RELS, Operators.RELATIONAL, Value.NATURAL, Units.FILE_RELATIONSHIP_TYPE),
    'ratio': (Predicate.RATIO, Operators.RATIO_OPERATORS, Value.RATIO, None),
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
    'tag as number': (Predicate.TAG_AS_NUMBER, Operators.TAG_RELATIONAL, Value.INTEGER, None)
}

# Parsing is just finding a matching predicate name,
# then trying to parse it by consuming the input string.
# The parse_* functions consume some of the string and return a (remaining part of the string, parsed value) tuple.
def parse_system_predicate(string):
    string = string.lower().strip()
    if string.startswith("-"):
        raise ValueError("System predicate can't start with negation")
    if not string.startswith(SYSTEM_PREDICATE_PREFIX):
        raise ValueError("Not a system predicate!")
    string = string[len(SYSTEM_PREDICATE_PREFIX):]
    for pred_regex in SYSTEM_PREDICATES:
        match = re.match(pred_regex.replace(' ','([_ ]+)')+":?", string)
        if match:
            pred = SYSTEM_PREDICATES[pred_regex]
            string = string[len(match[0]):]
            string, operator = parse_operator(string, pred[1])
            string, value = parse_value(string, pred[2])
            string, unit = parse_unit(string, pred[3])
            if string: raise ValueError("Unrecognized characters at the end of the predicate: "+string)
            return pred[0], operator, value, unit
    raise ValueError("Unknown system predicate!")

def parse_unit(string, spec):
    string = string.strip()
    if spec is None:
        return string, None
    elif spec == Units.FILESIZE:
        match = re.match('b|byte|bytes', string)
        if match: return string[len(match[0]):], 'B'
        match = re.match('kb|kilobytes|kilobyte', string)
        if match: return string[len(match[0]):], 'KB'
        match = re.match('mb|megabytes|megabyte', string)
        if match: return string[len(match[0]):], 'MB'
        match = re.match('gb|gigabytes|gigabyte', string)
        if match: return string[len(match[0]):], 'GB'
        raise ValueError("Invalid unit, expected a filesize")
    elif spec == Units.FILE_RELATIONSHIP_TYPE:
        match = re.match('duplicates', string)
        if match: return string[len(match[0]):], 'duplicates'
        match = re.match('alternates', string)
        if match: return string[len(match[0]):], 'alternates'
        match = re.match('(not related/false positives?)|not related|(false positives?)', string)
        if match: return string[len(match[0]):], 'not related/false positive'
        match = re.match('potential duplicates', string)
        if match: return string[len(match[0]):], 'potential duplicates'
        raise ValueError("Invalid unit, expected a file relationship")
    elif spec == Units.PIXELS_OR_NONE:
        if not string:
            return string, None
        else:
            match = re.match('(pixels?)|px', string)
            if match: return string[len(match[0]):], None
        raise ValueError("Invalid unit, expected no unit or pixels")
    elif spec == Units.PIXELS:
        match = re.match('px|pixels|pixel', string)
        if match: return string[len(match[0]):], 'pixels'
        match = re.match('kpx|kilopixels|kilopixel', string)
        if match: return string[len(match[0]):], 'kilopixels'
        match = re.match('mpx|megapixels|megapixel', string)
        if match: return string[len(match[0]):], 'megapixels'
        raise ValueError("Invalid unit, expected pixels")
    raise ValueError("Invalid unit specification")

def parse_value(string, spec):
    string = string.strip()
    if spec is None:
        return string, None
    elif spec == Value.NATURAL:
        match = re.match('0|([1-9][0-9]*)', string)
        if match: return string[len(match[0]):], int(match[0])
        raise ValueError("Invalid value, expected a natural number")
    elif spec == Value.HASHLIST_WITH_DISTANCE:
        match = re.match('(?P<hashes>([0-9a-f]+(\s|,)+)+)(with\s+)?distance\s+(?P<distance>0|([1-9][0-9]*))', string)
        if match:
            hashes = set(hsh.strip() for hsh in re.sub('\s', ' ', match['hashes'].replace(',', ' ')).split(' ') if len(hsh) > 0)
            distance = int(match['distance'])
            return string[len(match[0]):], (hashes, distance)
        raise ValueError("Invalid value, expected a list of hashes with distance")
    elif spec == Value.HASHLIST_WITH_ALGORITHM:
        match = re.match('(?P<hashes>[0-9a-f]+((\s|,)+[0-9a-f]+)*)((with\s+)?algorithm)?\s*(?P<algorithm>sha256|sha512|md5|sha1|)', string)
        if match:
            hashes = set(hsh.strip() for hsh in re.sub('\s', ' ', match['hashes'].replace(',', ' ')).split(' ') if len(hsh) > 0)
            algorithm = match['algorithm'] if len(match['algorithm']) > 0 else 'sha256'
            return string[len(match[0]):], (hashes, algorithm)
        raise ValueError("Invalid value, expected a list of hashes with algorithm")
    elif spec == Value.FILETYPE_LIST:
        valid_values = sorted( FILETYPES.keys(), key = lambda k: len( k ), reverse = True )
        ftype_regex = '('+'|'.join(['('+val+')' for val in valid_values])+')'
        match = re.match('('+ftype_regex+'(\s|,)+)*'+ftype_regex, string)
        if match:
            found_ftypes_all = re.sub('\s', ' ', match[0].replace(',', ' ')).split(' ')
            found_ftypes_good = []
            for ftype in found_ftypes_all:
                if len(ftype) > 0 and ftype in FILETYPES:
                    found_ftypes_good.extend( FILETYPES[ ftype ] )
            return string[len(match[0]):], set(found_ftypes_good)
        raise ValueError("Invalid value, expected a list of file types")
    elif spec == Value.DATE_OR_TIME_INTERVAL:
        match = re.match('((?P<year>0|([1-9][0-9]*))\s*(years|year))?\s*((?P<month>0|([1-9][0-9]*))\s*(months|month))?\s*((?P<day>0|([1-9][0-9]*))\s*(days|day))?\s*((?P<hour>0|([1-9][0-9]*))\s*(hours|hour|h))?', string)
        if match and (match.group('year') or match.group('month') or match.group('day') or match.group('hour')):
            years = int(match.group('year')) if match.group('year') else 0
            months = int(match.group('month')) if match.group('month') else 0
            days = int(match.group('day')) if match.group('day') else 0
            hours = int(match.group('hour')) if match.group('hour') else 0
            days += math.floor(hours/24)
            hours = hours % 24
            return string[len(match[0]):], (years, months, days, hours)
        match  = re.match('(?P<year>[0-9][0-9][0-9][0-9])-(?P<month>[0-9][0-9]?)-(?P<day>[0-9][0-9]?)', string)
        if match:
            return string[len(match[0]):], datetime.date(int(match.group('year')), int(match.group('month')), int(match.group('day')))
        raise ValueError("Invalid value, expected a date or a time interval")
    elif spec == Value.TIME_SEC_MSEC:
        match = re.match('((?P<sec>0|([1-9][0-9]*))\s*(seconds|second|secs|sec|s))?\s*((?P<msec>0|([1-9][0-9]*))\s*(milliseconds|milliseconds|msecs|msec|ms))?', string)
        if match and (match.group('sec') or match.group('msec')):
            seconds = int(match.group('sec')) if match.group('sec') else 0
            mseconds = int(match.group('msec')) if match.group('msec') else 0
            seconds += math.floor(mseconds/1000)
            mseconds = mseconds % 1000
            return string[len(match[0]):], (seconds, mseconds)
        raise ValueError("Invalid value, expected a duration")    
    elif spec == Value.ANY_STRING:
        return "", string
    elif spec == Value.TIME_INTERVAL:
        match = re.match('((?P<day>0|([1-9][0-9]*))\s*(days|day))?\s*((?P<hour>0|([1-9][0-9]*))\s*(hours|hour|h))?\s*((?P<minute>0|([1-9][0-9]*))\s*(minutes|minute|mins|min))?\s*((?P<second>0|([1-9][0-9]*))\s*(seconds|second|secs|sec|s))?', string)
        if match and (match.group('day') or match.group('hour') or match.group('minute') or match.group('second')):
            days = int(match.group('day')) if match.group('day') else 0
            hours = int(match.group('hour')) if match.group('hour') else 0
            minutes = int(match.group('minute')) if match.group('minute') else 0
            seconds = int(match.group('second')) if match.group('second') else 0
            minutes += math.floor(seconds/60)
            seconds = seconds % 60
            hours += math.floor(minutes/60)
            minutes = minutes % 60
            days += math.floor(hours/24)
            hours = hours % 24
            return string[len(match[0]):], (days, hours, minutes, seconds)
        raise ValueError("Invalid value, expected a time interval")
    elif spec == Value.INTEGER:
        match = re.match('0|(-?[1-9][0-9]*)', string)
        if match: return string[len(match[0]):], int(match[0])
        raise ValueError("Invalid value, expected an integer")
    elif spec == Value.RATIO:
        match = re.match('(?P<first>0|([1-9][0-9]*)):(?P<second>0|([1-9][0-9]*))', string)
        if match: return string[len(match[0]):], (int(match['first']), int(match['second']))
        raise ValueError("Invalid value, expected a ratio")
    raise ValueError("Invalid value specification")

def parse_operator(string, spec):
    string = string.strip()
    if spec is None:
        return string, None
    elif spec == Operators.RELATIONAL:
        ops = ['\u2248', '=', '<', '>', '\u2260']
        if string.startswith('=='): return string[2:], '='
        if string.startswith('!='): return string[2:], '\u2260'
        if string.startswith('is not'): return string[6:], '\u2260'
        if string.startswith('isn\'t'): return string[5:], '\u2260'
        if string.startswith( '~=' ): return string[2:], '\u2248'
        for op in ops:
            if string.startswith(op): return string[len(op):], op
        if string.startswith('is'): return string[2:], '='
        raise ValueError("Invalid relation operator")
    elif spec == Operators.EQUAL:
        if string.startswith('=='): return string[2:], '='
        if string.startswith('='): return string[1:], '='
        if string.startswith('is'): return string[2:], '='
        if string.startswith( '\u2260' ): return string[1:], '!='
        if string.startswith('!='): return string[2:], '!='
        if string.startswith('is not'): return string[6:], '!='
        if string.startswith('isn\'t'): return string[5:], '!='
        raise ValueError("Invalid equality operator")
    elif spec == Operators.FILESERVICE_STATUS:
        match = re.match('(is )?currently in', string)
        if match: return string[len(match[0]):], 'is currently in'
        match = re.match('((is )?not currently in)|isn\'t currently in', string)
        if match: return string[len(match[0]):], 'is not currently in'
        match = re.match('(is )?pending to', string)
        if match: return string[len(match[0]):], 'is pending to'
        match = re.match('((is )?not pending to)|isn\'t pending to', string)
        if match: return string[len(match[0]):], 'is not pending to'
        raise ValueError("Invalid operator, expected a file service relationship")
    elif spec == Operators.TAG_RELATIONAL:
        match = re.match('(?P<tag>.*)\s+(?P<op>(<|>|=|==|~=|\u2248|\u2260|is|is not))', string)
        if re.match:
            tag = match['tag']
            op = match['op']
            if op == '==': op = '='
            if op == 'is': op = '='
            return string[len(match[0]):], (tag, op)
        raise ValueError("Invalid operator, expected a tag followed by a relational operator")
    elif spec == Operators.ONLY_EQUAL:
        if string.startswith('=='): return string[2:], '='
        if string.startswith('='): return string[1:], '='
        if string.startswith('is'): return string[2:], '='
        raise ValueError("Invalid equality operator")
    elif spec == Operators.RATIO_OPERATORS:
        if string.startswith('wider than'): return string[10:], 'wider than'
        if string.startswith('taller than'): return string[11:], 'taller than'
        if string.startswith('is wider than'): return string[13:], 'wider than'
        if string.startswith('is taller than'): return string[14:], 'taller than'
        if string.startswith('=='): return string[2:], '='
        if string.startswith('='): return string[1:], '='
        if string.startswith('is'): return string[2:], '='
        if string.startswith('~='): return string[2:], '\u2248'
        if string.startswith('\u2248'): return string[1:], '\u2248'
        raise ValueError("Invalid ratio operator")
    raise ValueError("Invalid operator specification")

examples = [
    "system:everything",
    "system:inbox  ",
    "system:archive ",
    "system:has duration",
    "system:has_duration",
    "   system:no_duration",
    "system:no duration",
    "system:is the best quality file  of its group",
    "system:isn't the best quality file of its duplicate group",
    "system:has_audio",
    "system:no audio",
    "system:has icc profile",
    "system:no icc profile",
    "system:has tags",
    "system:no tags",
    "system:untagged",
    "system:number of tags > 5",
    "system:number of tags ~= 10",
    "system:number of tags > 0  ",
    "system:number of words < 2",
    "system:height = 600px",
    "system:height is 800",
    "system:height > 900",
    "system:width < 200",
    "system:width > 1000 pixels",
    "system:filesize ~= 50 kilobytes",
    "system:filesize > 10megabytes",
    "system:file size    < 1 GB",
    "system:file size > 0 B",
    "system:similar to abcdef1 abcdef2 abcdef3, abcdef4 with distance 3",
    "system:similar to abcdef distance 5",
    "system:limit is 5000",
    "system:limit = 100",
    "system:filetype is jpeg",
    "system:filetype =   image/jpg, image/png, apng",
    "system:hash = abcdef1 abcdef2 abcdef3",
    "system:hash = abcdef1 abcdef, abcdef4 md5",
    "system:modified date < 7  years 45 days 70h",
    "system:modified date > 2011-06-04",
    "system:date modified > 7 years 2    months",
    "system:date modified < 1 day",
    "system:date modified < 0 years 1 month 1 day 1 hour",
    "system:time_imported < 7 years 45 days 70h",
    "system:time imported > 2011-06-04",
    "system:time imported > 7 years 2 months",
    "system:time imported < 1 day",
    "system:time imported < 0 years 1 month 1 day 1 hour",
    " system:time imported ~= 2011-1-3 ",
    "system:import time < 7 years 45 days 70h",
    "system:import time > 2011-06-04",
    "system:import time > 7 years 2 months",
    "system:import time < 1 day",
    "system:import time < 0 years 1 month 1 day 1 hour",
    " system:import time ~= 2011-1-3 ",
    "system:import time ~= 1996-05-2",
    "system:duration < 5 seconds",
    "system:duration ~= 5 sec 6000 msecs",
    "system:duration > 3 milliseconds",
    "system:file service is pending to my files",
    "   system:file service currently in my files",
    "system:file service isn't currently in my files",
    "system:file service is not pending to my files",
    "system:num file relationships < 3 alternates",
    "system:number of file relationships > 3 false positives",
    "system:ratio is wider than 16:9        ",
    "system:ratio is 16:9",
    "system:ratio taller than 1:1",
    "system:num pixels > 50 px",
    "system:num pixels < 1 megapixels ",
    "system:num pixels ~= 5 kilopixel",
    "system:media views ~= 10",
    "system:all views > 0",
    "system:preview views < 10  ",
    "system:media viewtime < 1 days 1 hour 0 minutes",
    "system:all viewtime > 1 hours 100 seconds",
    "system:preview viewtime ~= 1 day 30 hours 100 minutes 90s",
    " system:has url matching regex reg.*ex ",
    "system:does not have a url matching regex test",
    "system:has_url https://test.test/",
    " system:doesn't have url test url here  ",
    "system:has domain test.com",
    "system:doesn't have domain test.com",
    "system:has a url with class safebooru file page",
    "system:doesn't have a url with url class safebooru file page ",
    "system:tag as number page < 5"
]

if __name__ == "__main__":
    for ex in examples:
        print(ex)
        print(parse_system_predicate(ex))
