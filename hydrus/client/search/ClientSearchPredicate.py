import collections.abc
import datetime
import re
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientTime
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientNumberTest

PREDICATE_TYPE_TAG = 0
PREDICATE_TYPE_NAMESPACE = 1
PREDICATE_TYPE_PARENT = 2
PREDICATE_TYPE_WILDCARD = 3
PREDICATE_TYPE_SYSTEM_EVERYTHING = 4
PREDICATE_TYPE_SYSTEM_INBOX = 5
PREDICATE_TYPE_SYSTEM_ARCHIVE = 6
PREDICATE_TYPE_SYSTEM_UNTAGGED = 7
PREDICATE_TYPE_SYSTEM_NUM_TAGS = 8
PREDICATE_TYPE_SYSTEM_LIMIT = 9
PREDICATE_TYPE_SYSTEM_SIZE = 10
PREDICATE_TYPE_SYSTEM_IMPORT_TIME = 11
PREDICATE_TYPE_SYSTEM_HASH = 12
PREDICATE_TYPE_SYSTEM_WIDTH = 13
PREDICATE_TYPE_SYSTEM_HEIGHT = 14
PREDICATE_TYPE_SYSTEM_RATIO = 15
PREDICATE_TYPE_SYSTEM_DURATION = 16
PREDICATE_TYPE_SYSTEM_MIME = 17
PREDICATE_TYPE_SYSTEM_RATING = 18
PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES = 19
PREDICATE_TYPE_SYSTEM_LOCAL = 20
PREDICATE_TYPE_SYSTEM_NOT_LOCAL = 21
PREDICATE_TYPE_SYSTEM_NUM_WORDS = 22
PREDICATE_TYPE_SYSTEM_FILE_SERVICE = 23
PREDICATE_TYPE_SYSTEM_NUM_PIXELS = 24
PREDICATE_TYPE_SYSTEM_DIMENSIONS = 25
PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT = 26
PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER = 27
PREDICATE_TYPE_SYSTEM_KNOWN_URLS = 28
PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS = 29
PREDICATE_TYPE_OR_CONTAINER = 30
PREDICATE_TYPE_LABEL = 31
PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING = 32
PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS = 33
PREDICATE_TYPE_SYSTEM_HAS_AUDIO = 34
PREDICATE_TYPE_SYSTEM_MODIFIED_TIME = 35
PREDICATE_TYPE_SYSTEM_FRAMERATE = 36
PREDICATE_TYPE_SYSTEM_NUM_FRAMES = 37
PREDICATE_TYPE_SYSTEM_NUM_NOTES = 38
PREDICATE_TYPE_SYSTEM_NOTES = 39
PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME = 40
PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE = 41
PREDICATE_TYPE_SYSTEM_TIME = 42
PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME = 43
PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA = 44
PREDICATE_TYPE_SYSTEM_FILE_PROPERTIES = 45
PREDICATE_TYPE_SYSTEM_HAS_EXIF = 46
PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME = 47
PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA = 48
PREDICATE_TYPE_SYSTEM_SIMILAR_TO = 49
PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY = 50
PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE = 51
PREDICATE_TYPE_SYSTEM_NUM_URLS = 52
PREDICATE_TYPE_SYSTEM_URLS = 53
PREDICATE_TYPE_SYSTEM_TAG_ADVANCED = 54

SYSTEM_PREDICATE_TYPES = {
    PREDICATE_TYPE_SYSTEM_EVERYTHING,
    PREDICATE_TYPE_SYSTEM_INBOX,
    PREDICATE_TYPE_SYSTEM_ARCHIVE,
    PREDICATE_TYPE_SYSTEM_UNTAGGED,
    PREDICATE_TYPE_SYSTEM_NUM_TAGS,
    PREDICATE_TYPE_SYSTEM_LIMIT,
    PREDICATE_TYPE_SYSTEM_SIZE,
    PREDICATE_TYPE_SYSTEM_IMPORT_TIME,
    PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME,
    PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
    PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME,
    PREDICATE_TYPE_SYSTEM_HASH,
    PREDICATE_TYPE_SYSTEM_WIDTH,
    PREDICATE_TYPE_SYSTEM_HEIGHT,
    PREDICATE_TYPE_SYSTEM_RATIO,
    PREDICATE_TYPE_SYSTEM_DURATION,
    PREDICATE_TYPE_SYSTEM_FRAMERATE,
    PREDICATE_TYPE_SYSTEM_NUM_FRAMES,
    PREDICATE_TYPE_SYSTEM_HAS_AUDIO,
    PREDICATE_TYPE_SYSTEM_FILE_PROPERTIES,
    PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY,
    PREDICATE_TYPE_SYSTEM_HAS_EXIF,
    PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA,
    PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE,
    PREDICATE_TYPE_SYSTEM_MIME,
    PREDICATE_TYPE_SYSTEM_RATING,
    PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES,
    PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA,
    PREDICATE_TYPE_SYSTEM_SIMILAR_TO,
    PREDICATE_TYPE_SYSTEM_LOCAL,
    PREDICATE_TYPE_SYSTEM_NOT_LOCAL,
    PREDICATE_TYPE_SYSTEM_NUM_WORDS,
    PREDICATE_TYPE_SYSTEM_NUM_NOTES,
    PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME,
    PREDICATE_TYPE_SYSTEM_FILE_SERVICE,
    PREDICATE_TYPE_SYSTEM_NUM_PIXELS,
    PREDICATE_TYPE_SYSTEM_DIMENSIONS,
    PREDICATE_TYPE_SYSTEM_NOTES,
    PREDICATE_TYPE_SYSTEM_TAG_ADVANCED,
    PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER,
    PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS,
    PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT,
    PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING,
    PREDICATE_TYPE_SYSTEM_KNOWN_URLS,
    PREDICATE_TYPE_SYSTEM_NUM_URLS,
    PREDICATE_TYPE_SYSTEM_URLS,
    PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS,
    PREDICATE_TYPE_SYSTEM_TIME,
    PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE
}

def ConvertSpecificFiletypesToSummary( specific_mimes: collections.abc.Collection[ int ], only_searchable = True ) -> collections.abc.Collection[ int ]:
    
    specific_mimes_to_process = set( specific_mimes )
    
    summary_mimes = set()
    
    for ( general_mime, mime_group ) in HC.general_mimetypes_to_mime_groups.items():
        
        if only_searchable:
            
            mime_group = set( mime_group )
            mime_group.intersection_update( HC.SEARCHABLE_MIMES )
            
        
        if specific_mimes_to_process.issuperset( mime_group ):
            
            summary_mimes.add( general_mime )
            specific_mimes_to_process.difference_update( mime_group )
            
        
    
    summary_mimes.update( specific_mimes_to_process )
    
    return summary_mimes
    

def ConvertSummaryFiletypesToSpecific( summary_mimes: collections.abc.Collection[ int ], only_searchable = True ) -> collections.abc.Collection[ int ]:
    
    specific_mimes = set()
    
    for mime in summary_mimes:
        
        if mime in HC.GENERAL_FILETYPES:
            
            specific_mimes.update( HC.general_mimetypes_to_mime_groups[ mime ] )
            
        else:
            
            specific_mimes.add( mime )
            
        
    
    if only_searchable:
        
        specific_mimes.intersection_update( HC.SEARCHABLE_MIMES )
        
    
    return specific_mimes
    

def ConvertSummaryFiletypesToString( summary_mimes: collections.abc.Collection[ int ] ) -> str:
    
    if set( summary_mimes ) == HC.GENERAL_FILETYPES:
        
        mime_text = 'anything'
        
    else:
        
        summary_mimes = sorted( summary_mimes, key = lambda m: HC.mime_mimetype_string_lookup[ m ] )
        
        mime_text = ', '.join( [ HC.mime_string_lookup[ mime ] for mime in summary_mimes ] )
        
    
    return mime_text
    

class PredicateCount( object ):
    
    def __init__(
        self,
        min_current_count: int,
        min_pending_count: int,
        max_current_count: typing.Optional[ int ],
        max_pending_count: typing.Optional[ int ]
        ):
        
        self.min_current_count = min_current_count
        self.min_pending_count = min_pending_count
        self.max_current_count = max_current_count if max_current_count is not None else min_current_count
        self.max_pending_count = max_pending_count if max_pending_count is not None else min_pending_count
        
    
    def __eq__( self, other ):
        
        if isinstance( other, PredicateCount ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return (
            self.min_current_count,
            self.min_pending_count,
            self.max_current_count,
            self.max_pending_count
        ).__hash__()
        
    
    def __repr__( self ):
        
        return 'Predicate Count: {}-{} +{}-{}'.format( self.min_current_count, self.max_current_count, self.min_pending_count, self.max_pending_count )
        
    
    def AddCounts( self, count: "PredicateCount" ):
        
        ( self.min_current_count, self.max_current_count ) = ClientData.MergeCounts( self.min_current_count, self.max_current_count, count.min_current_count, count.max_current_count )
        ( self.min_pending_count, self.max_pending_count) = ClientData.MergeCounts( self.min_pending_count, self.max_pending_count, count.min_pending_count, count.max_pending_count )
        
    
    def Duplicate( self ):
        
        return PredicateCount(
            self.min_current_count,
            self.min_pending_count,
            self.max_current_count,
            self.max_pending_count
        )
        
    
    def GetMinCount( self, current_or_pending = None ):
        
        if current_or_pending is None:
            
            return self.min_current_count + self.min_pending_count
            
        elif current_or_pending == HC.CONTENT_STATUS_CURRENT:
            
            return self.min_current_count
            
        elif current_or_pending == HC.CONTENT_STATUS_PENDING:
            
            return self.min_pending_count
            
        
    
    def GetSuffixString( self ) -> str:
        
        suffix_components = []
        
        if self.min_current_count > 0 or self.max_current_count > 0:
            
            number_text = HydrusNumbers.ToHumanInt( self.min_current_count )
            
            if self.max_current_count > self.min_current_count:
                
                number_text = '{}-{}'.format( number_text, HydrusNumbers.ToHumanInt( self.max_current_count ) )
                
            
            suffix_components.append( '({})'.format( number_text ) )
            
        
        if self.min_pending_count > 0 or self.max_pending_count > 0:
            
            number_text = HydrusNumbers.ToHumanInt( self.min_pending_count )
            
            if self.max_pending_count > self.min_pending_count:
                
                number_text = '{}-{}'.format( number_text, HydrusNumbers.ToHumanInt( self.max_pending_count ) )
                
            
            suffix_components.append( '(+{})'.format( number_text ) )
            
        
        return ' '.join( suffix_components )
        
    
    def HasNonZeroCount( self ):
        
        return self.min_current_count > 0 or self.min_pending_count > 0 or self.max_current_count > 0 or self.max_pending_count > 0
        
    
    def HasZeroCount( self ):
        
        return not self.HasNonZeroCount()
        
    
    @staticmethod
    def STATICCreateCurrentCount( current_count ) -> "PredicateCount":
        
        return PredicateCount( current_count, 0, None, None )
        
    
    @staticmethod
    def STATICCreateNullCount() -> "PredicateCount":
        
        return PredicateCount( 0, 0, None, None )
        
    
    @staticmethod
    def STATICCreateStaticCount( current_count, pending_count ) -> "PredicateCount":
        
        return PredicateCount( current_count, pending_count, None, None )
        
    

EDIT_PRED_TYPES = {
    PREDICATE_TYPE_SYSTEM_IMPORT_TIME,
    PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME,
    PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
    PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME,
    PREDICATE_TYPE_SYSTEM_HEIGHT,
    PREDICATE_TYPE_SYSTEM_WIDTH,
    PREDICATE_TYPE_SYSTEM_RATIO,
    PREDICATE_TYPE_SYSTEM_NUM_PIXELS,
    PREDICATE_TYPE_SYSTEM_DURATION,
    PREDICATE_TYPE_SYSTEM_FRAMERATE,
    PREDICATE_TYPE_SYSTEM_NUM_FRAMES,
    PREDICATE_TYPE_SYSTEM_FILE_SERVICE,
    PREDICATE_TYPE_SYSTEM_KNOWN_URLS,
    PREDICATE_TYPE_SYSTEM_NUM_URLS,
    PREDICATE_TYPE_SYSTEM_HASH,
    PREDICATE_TYPE_SYSTEM_LIMIT,
    PREDICATE_TYPE_SYSTEM_MIME,
    PREDICATE_TYPE_SYSTEM_RATING,
    PREDICATE_TYPE_SYSTEM_NUM_TAGS,
    PREDICATE_TYPE_SYSTEM_NUM_NOTES,
    PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME,
    PREDICATE_TYPE_SYSTEM_NUM_WORDS,
    PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES,
    PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA,
    PREDICATE_TYPE_SYSTEM_SIZE,
    PREDICATE_TYPE_SYSTEM_TAG_ADVANCED,
    PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER,
    PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT,
    PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS,
    PREDICATE_TYPE_OR_CONTAINER,
    PREDICATE_TYPE_NAMESPACE,
    PREDICATE_TYPE_WILDCARD,
    PREDICATE_TYPE_TAG
}

# this has useful order
# bro any time you add to this, add a new unit test!
PREDICATE_TYPES_WE_CAN_TEST_ON_MEDIA_RESULTS = [
    PREDICATE_TYPE_SYSTEM_INBOX,
    PREDICATE_TYPE_SYSTEM_ARCHIVE,
    PREDICATE_TYPE_SYSTEM_MIME,
    PREDICATE_TYPE_SYSTEM_WIDTH,
    PREDICATE_TYPE_SYSTEM_HEIGHT,
    PREDICATE_TYPE_SYSTEM_NUM_URLS,
    PREDICATE_TYPE_SYSTEM_KNOWN_URLS,
    PREDICATE_TYPE_SYSTEM_HAS_EXIF,
    PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE,
    PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA,
    PREDICATE_TYPE_SYSTEM_TAG_ADVANCED,
    PREDICATE_TYPE_SYSTEM_IMPORT_TIME,
    PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
    PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME,
    PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME,
    PREDICATE_TYPE_OR_CONTAINER,
]

# this has useful order
# bro any time you add to this, add a new unit test!
PREDICATE_TYPES_WE_CAN_EXTRACT_FROM_MEDIA_RESULTS = [
    PREDICATE_TYPE_SYSTEM_SIZE,
    PREDICATE_TYPE_SYSTEM_WIDTH,
    PREDICATE_TYPE_SYSTEM_HEIGHT,
    PREDICATE_TYPE_SYSTEM_NUM_PIXELS,
    PREDICATE_TYPE_SYSTEM_DURATION,
    PREDICATE_TYPE_SYSTEM_NUM_FRAMES,
    PREDICATE_TYPE_SYSTEM_NUM_TAGS,
    PREDICATE_TYPE_SYSTEM_NUM_URLS,
    PREDICATE_TYPE_SYSTEM_IMPORT_TIME,
    PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
    PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME,
    PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME
]

class Predicate( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PREDICATE
    SERIALISABLE_NAME = 'File Search Predicate'
    SERIALISABLE_VERSION = 8
    
    def __init__(
        self,
        predicate_type: typing.Optional[ int ] = None,
        value: typing.Any = None,
        inclusive: bool = True,
        count = None
        ):
        
        if predicate_type == PREDICATE_TYPE_SYSTEM_MIME and value is not None:
            
            value = tuple( sorted( ConvertSpecificFiletypesToSummary( value ) ) )
            
        
        if predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            value = list( value )
            
            value.sort( key = lambda p: HydrusText.HumanTextSortKey( p.ToString() ) )
            
        
        if isinstance( value, ( list, set ) ):
            
            value = tuple( value )
            
        
        if count is None:
            
            count = PredicateCount.STATICCreateNullCount()
            
        
        self._predicate_type: int = predicate_type
        self._value: typing.Any = value
        
        self._inclusive = inclusive
        
        self._count = count
        
        self._ideal_sibling = None
        self._siblings = None
        self._parents = None
        self._parent_predicates = set()
        
        if self._predicate_type == PREDICATE_TYPE_PARENT:
            
            self._parent_key = HydrusData.GenerateKey()
            
        else:
            
            self._parent_key = None
            
        
        self._RecalculateMatchableSearchTexts()
        
        #
        
        self._RecalcPythonHash()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, Predicate ):
            
            if self._predicate_type == PREDICATE_TYPE_PARENT:
                
                return False
                
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self._python_hash
        
    
    def __repr__( self ):
        
        return 'Predicate: ' + str( ( self._predicate_type, self._value, self._inclusive, self._count.GetMinCount() ) )
        
    
    def _RecalcPythonHash( self ):
        
        if self._predicate_type == PREDICATE_TYPE_PARENT:
            
            self._python_hash = self._parent_key.__hash__()
            
        else:
            
            self._python_hash = ( self._predicate_type, self._value, self._inclusive ).__hash__()
            
        
    
    def _GetSerialisableInfo( self ):
        
        if self._value is None:
            
            serialisable_value = None
            
        else:
            
            if self._predicate_type in ( PREDICATE_TYPE_SYSTEM_RATING, PREDICATE_TYPE_SYSTEM_FILE_SERVICE ):
                
                ( operator, value, service_key ) = self._value
                
                serialisable_value = ( operator, value, service_key.hex() )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES:
                
                ( hashes, max_hamming ) = self._value
                
                serialisable_value = ( [ hash.hex() for hash in hashes ], max_hamming )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA:
                
                ( pixel_hashes, perceptual_hashes, max_hamming ) = self._value
                
                serialisable_value = (
                    [ pixel_hash.hex() for pixel_hash in pixel_hashes ],
                    [ perceptual_hash.hex() for perceptual_hash in perceptual_hashes ],
                    max_hamming
                )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
                
                ( operator, rule_type, rule, description ) = self._value
                
                if rule_type in ( 'url_match', 'url_class' ):
                    
                    serialisable_rule = rule.GetSerialisableTuple()
                    
                else:
                    
                    serialisable_rule = rule
                    
                
                serialisable_value = ( operator, rule_type, serialisable_rule, description )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HASH:
                
                ( hashes, hash_type ) = self._value
                
                serialisable_value = ( [ hash.hex() for hash in hashes ], hash_type )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_TAG_ADVANCED:
                
                ( service_key_or_none, tag_display_type, statuses, tag ) = self._value
                
                serialisable_service_key_or_none = HydrusData.BytesToNoneOrHex( service_key_or_none )
                serialisable_statuses = tuple( statuses )
                
                serialisable_value = ( serialisable_service_key_or_none, tag_display_type, serialisable_statuses, tag )
                
            elif self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
                
                or_predicates = self._value
                
                serialisable_value = HydrusSerialisable.SerialisableList( or_predicates ).GetSerialisableTuple()
                
            elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_WIDTH, PREDICATE_TYPE_SYSTEM_HEIGHT, PREDICATE_TYPE_SYSTEM_NUM_NOTES, PREDICATE_TYPE_SYSTEM_NUM_WORDS, PREDICATE_TYPE_SYSTEM_NUM_URLS, PREDICATE_TYPE_SYSTEM_NUM_FRAMES, PREDICATE_TYPE_SYSTEM_DURATION, PREDICATE_TYPE_SYSTEM_FRAMERATE ):
                
                number_test_or_none = typing.cast( typing.Optional[ ClientNumberTest.NumberTest ], self._value )
                
                serialisable_value = HydrusSerialisable.GetNoneableSerialisableTuple( number_test_or_none )
                
            else:
                
                serialisable_value = self._value
                
            
        
        return ( self._predicate_type, serialisable_value, self._inclusive )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._predicate_type, serialisable_value, self._inclusive ) = serialisable_info
        
        if serialisable_value is None:
            
            self._value = None
            
        else:
            
            if self._predicate_type in ( PREDICATE_TYPE_SYSTEM_RATING, PREDICATE_TYPE_SYSTEM_FILE_SERVICE ):
                
                ( operator, value, service_key ) = serialisable_value
                
                self._value = ( operator, value, bytes.fromhex( service_key ) )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES:
                
                ( serialisable_hashes, max_hamming ) = serialisable_value
                
                self._value = ( tuple( [ bytes.fromhex( serialisable_hash ) for serialisable_hash in serialisable_hashes ] ) , max_hamming )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA:
                
                ( serialisable_pixel_hashes, serialisable_perceptual_hashes, max_hamming ) = serialisable_value
                
                self._value = (
                    tuple( [ bytes.fromhex( serialisable_pixel_hash ) for serialisable_pixel_hash in serialisable_pixel_hashes ] ),
                    tuple( [ bytes.fromhex( serialisable_perceptual_hash ) for serialisable_perceptual_hash in serialisable_perceptual_hashes ] ),
                    max_hamming
                )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
                
                ( operator, rule_type, serialisable_rule, description ) = serialisable_value
                
                if rule_type in ( 'url_match', 'url_class' ):
                    
                    rule = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_rule )
                    
                else:
                    
                    rule = serialisable_rule
                    
                
                self._value = ( operator, rule_type, rule, description )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HASH:
                
                ( serialisable_hashes, hash_type ) = serialisable_value
                
                self._value = ( tuple( [ bytes.fromhex( serialisable_hash ) for serialisable_hash in serialisable_hashes ] ), hash_type )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_TAG_ADVANCED:
                
                ( serialisable_key_or_none, tag_display_type, serialisable_statuses, tag ) = serialisable_value
                
                service_key_or_none = HydrusData.HexToNoneOrBytes( serialisable_key_or_none )
                statuses = tuple( serialisable_statuses )
                
                self._value = ( service_key_or_none, tag_display_type, statuses, tag )
                
            elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_IMPORT_TIME, PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME ):
                
                ( operator, age_type, age_value ) = serialisable_value
                
                self._value = ( operator, age_type, tuple( age_value ) )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
                
                ( view_type, viewing_locations, operator, viewing_value ) = serialisable_value
                
                self._value = ( view_type, tuple( viewing_locations ), operator, viewing_value )
                
            elif self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
                
                serialisable_or_predicates = serialisable_value
                
                self._value = tuple( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_or_predicates ) )
                
                try:
                    
                    self._value = tuple( sorted( self._value, key = lambda p: HydrusText.HumanTextSortKey( p.ToString() ) ) )
                    
                except:
                    
                    pass
                    
                
            elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_WIDTH, PREDICATE_TYPE_SYSTEM_HEIGHT, PREDICATE_TYPE_SYSTEM_NUM_NOTES, PREDICATE_TYPE_SYSTEM_NUM_WORDS, PREDICATE_TYPE_SYSTEM_NUM_URLS, PREDICATE_TYPE_SYSTEM_NUM_FRAMES, PREDICATE_TYPE_SYSTEM_DURATION, PREDICATE_TYPE_SYSTEM_FRAMERATE ):
                
                serialisable_number_test = serialisable_value
                
                self._value = HydrusSerialisable.CreateFromNoneableSerialisableTuple( serialisable_number_test )
                
            else:
                
                self._value = serialisable_value
                
                if self._predicate_type == PREDICATE_TYPE_SYSTEM_MIME and self._value is not None:
                    
                    self._value = tuple( sorted( ConvertSpecificFiletypesToSummary( self._value ) ) )
                    
                
            
            if isinstance( self._value, list ):
                
                self._value = tuple( self._value )
                
            
        
        self._RecalcPythonHash()
        
    
    def _RecalculateMatchableSearchTexts( self ):
        
        if self._predicate_type == PREDICATE_TYPE_TAG:
            
            self._matchable_search_texts = { self._value }
            
            if self._siblings is not None:
                
                self._matchable_search_texts.update( self._siblings )
                
            
        else:
            
            self._matchable_search_texts = set()
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_IMPORT_TIME:
                
                ( operator, years, months, days, hours ) = serialisable_value
                
                serialisable_value = ( operator, 'delta', ( years, months, days, hours ) )
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type in ( PREDICATE_TYPE_SYSTEM_HASH, PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES ):
                
                # other value is either hash type or max hamming distance
                
                ( serialisable_hash, other_value ) = serialisable_value
                
                serialisable_hashes = ( serialisable_hash, )
                
                serialisable_value = ( serialisable_hashes, other_value )
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_NUM_TAGS:
                
                ( operator, num ) = serialisable_value
                
                namespace = '*'
                
                serialisable_value = ( namespace, operator, num )
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_MIME:
                
                specific_mimes = serialisable_value
                
                summary_mimes = ConvertSpecificFiletypesToSummary( specific_mimes )
                
                serialisable_value = tuple( sorted( summary_mimes ) )
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type in ( PREDICATE_TYPE_SYSTEM_IMPORT_TIME, PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME ):
                
                ( operator, age_type, age_value ) = serialisable_value
                
                if age_type == 'date':
                    
                    ( year, month, day ) = age_value
                    
                    hour = 0
                    minute = 0
                    
                    age_value = ( year, month, day, hour, minute )
                    
                    serialisable_value = ( operator, age_type, age_value )
                    
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_MIME:
                
                mimes = list( serialisable_value )
                
                if HC.GENERAL_APPLICATION in mimes:
                    
                    mimes.append( HC.GENERAL_APPLICATION_ARCHIVE )
                    mimes.append( HC.GENERAL_IMAGE_PROJECT )
                    
                
                mimes = tuple( mimes )
                
                serialisable_value = mimes
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type in ( PREDICATE_TYPE_SYSTEM_WIDTH, PREDICATE_TYPE_SYSTEM_HEIGHT, PREDICATE_TYPE_SYSTEM_NUM_NOTES, PREDICATE_TYPE_SYSTEM_NUM_WORDS, PREDICATE_TYPE_SYSTEM_NUM_URLS, PREDICATE_TYPE_SYSTEM_NUM_FRAMES, PREDICATE_TYPE_SYSTEM_DURATION, PREDICATE_TYPE_SYSTEM_FRAMERATE ):
                
                ( operator, value ) = serialisable_value
                
                number_test = ClientNumberTest.NumberTest.STATICCreateFromCharacters( operator, value )
                
                if predicate_type in ( PREDICATE_TYPE_SYSTEM_FRAMERATE, PREDICATE_TYPE_SYSTEM_DURATION ):
                    
                    if operator == '=':
                        
                        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT, value = value, extra_value = 0.05 )
                        
                    elif operator == HC.UNICODE_NOT_EQUAL:
                        
                        number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN, value = value )
                        
                    
                
                serialisable_value = number_test.GetSerialisableTuple()
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 8, new_serialisable_info )
            
        
    
    def CanExtractValueFromMediaResult( self ):
        
        return self._predicate_type in PREDICATE_TYPES_WE_CAN_EXTRACT_FROM_MEDIA_RESULTS
        
    
    def CanTestMediaResult( self ) -> bool:
        
        if self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            predicates = self._value
            
            return False not in [ predicate.CanTestMediaResult() for predicate in predicates ]
            
        
        return self._predicate_type in PREDICATE_TYPES_WE_CAN_TEST_ON_MEDIA_RESULTS
        
    
    def ExtractValueFromMediaResult( self, media_result: ClientMediaResult.MediaResult ) -> typing.Optional[ float ]:
        
        if self._predicate_type == PREDICATE_TYPE_SYSTEM_SIZE:
            
            return media_result.GetFileInfoManager().size
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_WIDTH:
            
            return media_result.GetFileInfoManager().width
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HEIGHT:
            
            return media_result.GetFileInfoManager().height
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_PIXELS:
            
            file_info_manager = media_result.GetFileInfoManager()
            
            if file_info_manager.height is not None and file_info_manager.width is not None:
                
                return file_info_manager.height * file_info_manager.width
                
            else:
                
                return None
                
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_DURATION:
            
            return media_result.GetFileInfoManager().duration_ms
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_FRAMES:
            
            return media_result.GetFileInfoManager().num_frames
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_TAGS:
            
            return len( media_result.GetTagsManager().GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ) )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_URLS:
            
            return len( media_result.GetLocationsManager().GetURLs() )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_IMPORT_TIME:
            
            return media_result.GetTimesManager().GetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_MODIFIED_TIME:
            
            return media_result.GetTimesManager().GetAggregateModifiedTimestampMS()
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME:
            
            return media_result.GetTimesManager().GetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME:
            
            return media_result.GetTimesManager().GetArchivedTimestampMS()
            
        else:
            
            raise NotImplementedError( f'The given predicate, "{self.ToString()}", cannot extract a value from a media result! You should not be able to get into this situation, so please contact hydev with details.' )
            
        
    
    def GetCopy( self ):
        
        return Predicate( self._predicate_type, self._value, self._inclusive, count = self._count.Duplicate() )
        
    
    def GetCount( self ):
        
        return self._count
        
    
    def GetCountlessCopy( self ):
        
        return Predicate( self._predicate_type, self._value, self._inclusive )
        
    
    def GetNamespace( self ):
        
        if self._predicate_type in SYSTEM_PREDICATE_TYPES:
            
            return 'system'
            
        elif self._predicate_type == PREDICATE_TYPE_NAMESPACE:
            
            namespace = self._value
            
            return namespace
            
        elif self._predicate_type in ( PREDICATE_TYPE_PARENT, PREDICATE_TYPE_TAG, PREDICATE_TYPE_WILDCARD ):
            
            tag_analogue = self._value
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag_analogue )
            
            if '*' in namespace:
                
                return '*'
                
            
            return namespace
            
        else:
            
            return ''
            
        
    
    def GetIdealPredicate( self ):
        
        if self._ideal_sibling is None:
            
            return None
            
        else:
            
            return Predicate( PREDICATE_TYPE_TAG, self._ideal_sibling, self._inclusive )
            
        
    
    def GetIdealSibling( self ):
        
        return self._ideal_sibling
        
    
    def GetInclusive( self ):
        
        # patch from an upgrade mess-up ~v144
        if not hasattr( self, '_inclusive' ):
            
            if self._predicate_type not in SYSTEM_PREDICATE_TYPES:
                
                ( operator, value ) = self._value
                
                self._value = value
                
                self._inclusive = operator == '+'
                
            else:
                
                self._inclusive = True
                
            
            self._RecalcPythonHash()
            
        
        return self._inclusive
        
    
    def GetInfo( self ):
        
        return ( self._predicate_type, self._value, self._inclusive )
        
    
    def GetInverseCopy( self ):
        
        if self._predicate_type == PREDICATE_TYPE_SYSTEM_ARCHIVE:
            
            return Predicate( PREDICATE_TYPE_SYSTEM_INBOX )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_INBOX:
            
            return Predicate( PREDICATE_TYPE_SYSTEM_ARCHIVE )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_LOCAL:
            
            return Predicate( PREDICATE_TYPE_SYSTEM_NOT_LOCAL )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NOT_LOCAL:
            
            return Predicate( PREDICATE_TYPE_SYSTEM_LOCAL )
            
        elif self._predicate_type in ( PREDICATE_TYPE_TAG, PREDICATE_TYPE_NAMESPACE, PREDICATE_TYPE_WILDCARD ):
            
            return Predicate( self._predicate_type, self._value, not self._inclusive )
            
        elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_HAS_AUDIO, PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, PREDICATE_TYPE_SYSTEM_HAS_EXIF, PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE ):
            
            return Predicate( self._predicate_type, not self._value )
            
        elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_NUM_NOTES, PREDICATE_TYPE_SYSTEM_NUM_WORDS, PREDICATE_TYPE_SYSTEM_NUM_URLS, PREDICATE_TYPE_SYSTEM_NUM_FRAMES, PREDICATE_TYPE_SYSTEM_DURATION ):
            
            number_test: ClientNumberTest.NumberTest = self._value
            
            if number_test is not None:
                
                if number_test.IsZero():
                    
                    return Predicate( self._predicate_type, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ) )
                    
                elif number_test.IsAnythingButZero():
                    
                    return Predicate( self._predicate_type, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ) )
                    
                
            
            return None
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING:
            
            return Predicate( self._predicate_type, not self._value )
            
        else:
            
            return None
            
        
    
    def GetMagicSortValue( self ):
        
        if self._predicate_type == PREDICATE_TYPE_SYSTEM_WIDTH:
            
            return 'system:dimensions:0'
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HEIGHT:
            
            return 'system:dimensions:1'
            
        else:
            
            return self.ToString( with_count = False )
            
        
    
    def GetMatchableSearchTexts( self ):
        
        return self._matchable_search_texts
        
    
    def GetORPredicates( self ) -> list[ "Predicate" ]:
        
        if self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            return self._value
            
        else:
            
            return []
            
        
    
    def GetParentPredicates( self ) -> set[ "Predicate" ]:
        
        return self._parent_predicates
        
    
    def GetTextsAndNamespaces( self, render_for_user: bool, or_under_construction: bool = False, prefix = '' ):
        
        if self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            or_connector_namespace = CG.client_controller.new_options.GetNoneableString( 'or_connector_custom_namespace_colour' )
            
            texts_and_namespaces = [ ( prefix + 'OR:', 'or', or_connector_namespace ) ]
            
            '''
            or_connector = CG.client_controller.new_options.GetString( 'or_connector' )
            or_connector_namespace = CG.client_controller.new_options.GetNoneableString( 'or_connector_custom_namespace_colour' )
            
            texts_and_namespaces = []
            
            for or_predicate in self._value:
                
                texts_and_namespaces.append( ( or_predicate.ToString(), 'namespace', or_predicate.GetNamespace() ) )
                
                texts_and_namespaces.append( ( or_connector, 'or', or_connector_namespace ) )
                
            
            if not or_under_construction:
                
                texts_and_namespaces = texts_and_namespaces[ : -1 ]
                
            '''
        else:
            
            texts_and_namespaces = [ ( prefix + self.ToString( render_for_user = render_for_user ), 'namespace', self.GetNamespace() ) ]
            
        
        return texts_and_namespaces
        
    
    def GetType( self ):
        
        return self._predicate_type
        
    
    def GetUnnamespacedCopy( self ):
        
        if self._predicate_type == PREDICATE_TYPE_TAG:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( self._value )
            
            return Predicate( self._predicate_type, subtag, self._inclusive, count = self._count.Duplicate() )
            
        
        return self.GetCopy()
        
    
    def GetValue( self ) -> typing.Any:
        
        return self._value
        
    
    def HasBadSiblings( self ):
        
        # not sure this is totally good, but this is a hack method
        return self._siblings is not None and self._ideal_sibling is None
        
    
    def HasIdealSibling( self ):
        
        return self._ideal_sibling is not None
        
    
    def HasParentPredicates( self ):
        
        return len( self._parent_predicates ) > 0
        
    
    def IsEditable( self ):
        
        return self._predicate_type in EDIT_PRED_TYPES
        
    
    def IsInclusive( self ):
        
        return self._inclusive
        
    
    def IsInvertible( self ):
        
        return self.GetInverseCopy() is not None
        
    
    def IsMutuallyExclusive( self, predicate ):
        
        if self._predicate_type == PREDICATE_TYPE_SYSTEM_EVERYTHING:
            
            return True
            
        
        if self.IsInvertible() and predicate == self.GetInverseCopy():
            
            return True
            
        
        my_type = self._predicate_type
        other_type = predicate.GetType()
        
        if my_type == other_type:
            
            if my_type in ( PREDICATE_TYPE_SYSTEM_LIMIT, ):
                
                return True
                
            
        
        return False
        
    
    def IsORPredicate( self ):
        
        return self._predicate_type == PREDICATE_TYPE_OR_CONTAINER
        
    
    def IsUIEditable( self, ideal_predicate: "Predicate" ) -> bool:
        
        # bleh
        
        if self._predicate_type != ideal_predicate.GetType():
            
            return False
            
        
        ideal_value = ideal_predicate.GetValue()
        
        if self._value is None:
            
            # delicate linter tapdance going on here, alter only with care
            return ideal_value is None
            
        
        if self._predicate_type in ( PREDICATE_TYPE_SYSTEM_IMPORT_TIME, PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME ):
            
            # age_type
            if self._value[1] != ideal_value[1]:
                
                return False
                
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
            
            # view_type
            if self._value[0] != ideal_value[0]:
                
                return False
                
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            # rule type
            if self._value[1] != ideal_value[1]:
                
                return False
                
            
        
        return True
        
    
    def SetCount( self, count: PredicateCount ):
        
        self._count = count
        
    
    def SetIdealSibling( self, tag: str ):
        
        self._ideal_sibling = tag
        
    
    def SetInclusive( self, inclusive ):
        
        self._inclusive = inclusive
        
        self._RecalcPythonHash()
        
    
    def SetKnownParents( self, parents: set[ str ] ):
        
        self._parents = parents
        
        self._parent_predicates = [ Predicate( PREDICATE_TYPE_PARENT, parent ) for parent in self._parents ]
        
    
    def SetKnownSiblings( self, siblings: set[ str ] ):
        
        self._siblings = siblings
        
        self._RecalculateMatchableSearchTexts()
        
    
    def TestMediaResult( self, media_result: ClientMediaResult.MediaResult ) -> bool:
        
        if self._predicate_type == PREDICATE_TYPE_SYSTEM_INBOX:
            
            return media_result.GetLocationsManager().inbox
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_ARCHIVE:
            
            return not media_result.GetLocationsManager().inbox
            
        if self._predicate_type == PREDICATE_TYPE_SYSTEM_MIME:
            
            mimes = ConvertSummaryFiletypesToSpecific( self._value )
            
            if self._inclusive:
                
                return media_result.GetMime() in mimes
                
            else:
                
                return media_result.GetMime() not in mimes
                
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HEIGHT:
            
            number_test: ClientNumberTest.NumberTest = self._value
            
            return number_test.Test( media_result.GetFileInfoManager().height )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_WIDTH:
            
            number_test: ClientNumberTest.NumberTest = self._value
            
            return number_test.Test( media_result.GetFileInfoManager().width )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_EXIF:
            
            inclusive_hack = self._value is None or self._value is True
            
            return media_result.GetFileInfoManager().has_exif == inclusive_hack
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE:
            
            inclusive_hack = self._value is None or self._value is True
            
            return media_result.GetFileInfoManager().has_icc_profile == inclusive_hack
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA:
            
            inclusive_hack = self._value is None or self._value is True
            
            return media_result.GetFileInfoManager().has_human_readable_embedded_metadata == inclusive_hack
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_URLS:
            
            number_test: ClientNumberTest.NumberTest = self._value
            
            return number_test.Test( len( media_result.GetLocationsManager().GetURLs() ) )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            ( operator, rule_type, rule, description ) = self._value
            
            urls = media_result.GetLocationsManager().GetURLs()
            
            if rule_type == 'url_class':
                
                from hydrus.client.networking import ClientNetworkingURLClass
                
                url_class: ClientNetworkingURLClass.URLClass = rule
                
                matches = True in ( url_class.Matches( url ) for url in urls )
                
            elif rule_type == 'regex':
                
                regex_rule: str = rule
                
                re_url_test = re.compile( regex_rule )
                
                matches = True in ( re_url_test.search( url ) is not None for url in urls )
                
            elif rule_type == 'exact_match':
                
                url: str = rule
                
                matches = url in urls
                
            elif rule_type == 'domain':
                
                from hydrus.client.networking import ClientNetworkingFunctions
                
                domain: str = rule
                
                domain = ClientNetworkingFunctions.RemoveWWWFromDomain( domain )
                
                matches = True in ( ClientNetworkingFunctions.ConvertURLIntoDomain( url ).endswith( domain ) for url in urls )
                
            else:
                
                return False
                
            
            if operator: # this is a bool
                
                return matches
                
            else:
                
                return not matches
                
            
        elif self._predicate_type in [
            PREDICATE_TYPE_SYSTEM_IMPORT_TIME,
            PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
            PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME,
            PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME
        ]:
            
            ( operator, age_type, age_value ) = self._value
            
            min_timestamp_ms = None
            max_timestamp_ms = None
            
            if age_type == 'delta':
                
                ( years, months, days, hours ) = age_value
                
                dt = HydrusTime.CalendarDeltaToDateTime( years, months, days, hours )
                
                time_pivot_ms = HydrusTime.DateTimeToTimestampMS( dt )
                
                # this is backwards (less than means min timestamp) because we are talking about age, not timestamp
                
                # the before/since semantic logic is:
                # '<' 7 days age means 'since that date'
                # '>' 7 days ago means 'before that date'
                
                if operator == '<':
                    
                    min_timestamp_ms = time_pivot_ms
                    
                elif operator == '>':
                    
                    max_timestamp_ms = time_pivot_ms
                    
                elif operator == HC.UNICODE_APPROX_EQUAL:
                    
                    rough_timedelta_gap = HydrusTime.CalendarDeltaToRoughDateTimeTimeDelta( years, months, days, hours ) * 0.15
                    
                    earliest_dt = dt - rough_timedelta_gap
                    latest_dt = dt + rough_timedelta_gap
                    
                    earliest_time_pivot_ms = HydrusTime.DateTimeToTimestampMS( earliest_dt )
                    latest_time_pivot_ms = HydrusTime.DateTimeToTimestampMS( latest_dt )
                    
                    min_timestamp_ms = earliest_time_pivot_ms
                    max_timestamp_ms = latest_time_pivot_ms
                    
                
            elif age_type == 'date':
                
                ( year, month, day, hour, minute ) = age_value
                
                dt = datetime.datetime( year, month, day, hour, minute )
                
                time_pivot_ms = HydrusTime.DateTimeToTimestampMS( dt )
                
                dt_day_of_start = HydrusTime.GetDateTime( year, month, day, 0, 0 )
                
                day_of_start_timestamp_ms = HydrusTime.DateTimeToTimestampMS( dt_day_of_start )
                day_of_end_timestamp_ms = HydrusTime.DateTimeToTimestampMS( ClientTime.CalendarDelta( dt_day_of_start, day_delta = 1 ) )
                
                # the before/since semantic logic is:
                # '<' 2022-05-05 means 'before that date'
                # '>' 2022-05-05 means 'since that date'
                
                if operator == '<':
                    
                    max_timestamp_ms = time_pivot_ms
                    
                elif operator == '>':
                    
                    min_timestamp_ms = time_pivot_ms
                    
                elif operator == '=':
                    
                    min_timestamp_ms = day_of_start_timestamp_ms
                    max_timestamp_ms = day_of_end_timestamp_ms
                    
                elif operator == HC.UNICODE_APPROX_EQUAL:
                    
                    previous_month_timestamp_ms = HydrusTime.DateTimeToTimestampMS( ClientTime.CalendarDelta( dt, month_delta = -1 ) )
                    next_month_timestamp_ms = HydrusTime.DateTimeToTimestampMS( ClientTime.CalendarDelta( dt, month_delta = 1 ) )
                    
                    min_timestamp_ms = previous_month_timestamp_ms
                    max_timestamp_ms = next_month_timestamp_ms
                    
                
            
            if min_timestamp_ms is None and max_timestamp_ms is None:
                
                return False
                
            
            file_timestamp_ms_to_test = None
            
            if self._predicate_type == PREDICATE_TYPE_SYSTEM_IMPORT_TIME:
                
                file_timestamp_ms_to_test = media_result.GetTimesManager().GetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_MODIFIED_TIME:
                
                file_timestamp_ms_to_test = media_result.GetTimesManager().GetAggregateModifiedTimestampMS()
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME:
                
                file_timestamp_ms_to_test = media_result.GetTimesManager().GetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER )
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME:
                
                file_timestamp_ms_to_test = media_result.GetTimesManager().GetArchivedTimestampMS()
                
            
            if file_timestamp_ms_to_test is None: # probably means no actual archived time etc..
                
                return False
                
            
            if min_timestamp_ms is not None:
                
                if file_timestamp_ms_to_test < min_timestamp_ms:
                    
                    return False
                    
                
            
            if max_timestamp_ms is not None:
                
                if file_timestamp_ms_to_test > max_timestamp_ms:
                    
                    return False
                    
                
            
            return True
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_TAG_ADVANCED:
            
            ( service_key_or_none, tag_display_type, statuses, tag ) = self._value
            
            tags_manager = media_result.GetTagsManager()
            
            we_found_it = False
            
            if service_key_or_none is None:
                
                service_key_or_none = CC.COMBINED_TAG_SERVICE_KEY
                
            
            for status in statuses:
                
                if tag in tags_manager.GetTags( service_key_or_none, tag_display_type, status ):
                    
                    we_found_it = True
                    
                    break
                    
                
            
            if self._inclusive:
                
                return we_found_it
                
            else:
                
                return not we_found_it
                
            
        elif self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            predicates = self._value
            
            return True in ( predicate.TestMediaResult( media_result ) for predicate in predicates )
            
        else:
            
            raise NotImplementedError( f'The given predicate, "{self.ToString()}", cannot test a media result! You should not be able to get into this situation, so please contact hydev with details.' )
            
        
        return False
        
    
    def _ToString( self, with_count: bool = True, render_for_user: bool = False, or_under_construction: bool = False, for_parsable_export: bool = False ) -> str:
        
        base = ''
        count_text = ''
        
        if with_count:
            
            suffix = self._count.GetSuffixString()
            
            if len( suffix ) > 0:
                
                count_text += ' {}'.format( suffix )
                
            
        
        if self._predicate_type in SYSTEM_PREDICATE_TYPES:
            
            if self._predicate_type == PREDICATE_TYPE_SYSTEM_EVERYTHING: base = 'everything'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_INBOX: base = 'inbox'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_ARCHIVE: base = 'archive'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_UNTAGGED: base = 'untagged'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_LOCAL: base = 'local'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NOT_LOCAL: base = 'not local'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_PROPERTIES: base = 'file properties'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_DIMENSIONS: base = 'dimensions'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO: base = 'similar files'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_TIME: base = 'time'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_URLS: base = 'urls'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NOTES: base = 'notes'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS: base = 'file relationships'
            elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_WIDTH, PREDICATE_TYPE_SYSTEM_HEIGHT, PREDICATE_TYPE_SYSTEM_NUM_NOTES, PREDICATE_TYPE_SYSTEM_NUM_WORDS, PREDICATE_TYPE_SYSTEM_NUM_URLS, PREDICATE_TYPE_SYSTEM_NUM_FRAMES, PREDICATE_TYPE_SYSTEM_DURATION, PREDICATE_TYPE_SYSTEM_FRAMERATE ):
                
                has_phrase = None
                not_has_phrase = None
                absolute_number_renderer = None
                
                if self._predicate_type == PREDICATE_TYPE_SYSTEM_WIDTH:
                    
                    base = 'width'
                    has_phrase = 'has width'
                    not_has_phrase = 'no width'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HEIGHT:
                    
                    base = 'height'
                    has_phrase = 'has height'
                    not_has_phrase = 'no height'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FRAMERATE:
                    
                    absolute_number_renderer = lambda s: f'{HydrusNumbers.ToHumanInt(s)}fps'
                    
                    base = 'framerate'
                    has_phrase = 'has framerate'
                    not_has_phrase = 'no framerate'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_NOTES:
                    
                    base = 'number of notes'
                    has_phrase = 'has notes'
                    not_has_phrase = 'no notes'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_WORDS:
                    
                    base = 'number of words'
                    has_phrase = 'has words'
                    not_has_phrase = 'no words'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_URLS:
                    
                    base = 'number of urls'
                    has_phrase = 'has urls'
                    not_has_phrase = 'no urls'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_FRAMES:
                    
                    base = 'number of frames'
                    has_phrase = 'has frames'
                    not_has_phrase = 'no frames'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_DURATION:
                    
                    absolute_number_renderer = lambda n: HydrusTime.MillisecondsDurationToPrettyTime( n, force_numbers = True )
                    
                    base = 'duration'
                    has_phrase = 'has duration'
                    not_has_phrase = 'no duration'
                    
                
                if self._value is not None:
                    
                    number_test: ClientNumberTest.NumberTest = self._value
                    
                    if number_test.IsZero() and not_has_phrase is not None:
                        
                        base = not_has_phrase
                        
                    elif number_test.IsAnythingButZero() and has_phrase is not None:
                        
                        base = has_phrase
                        
                    else:
                        
                        base += f' {number_test.ToString( absolute_number_renderer = absolute_number_renderer )}'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME:
                
                base = 'has note'
                
                if self._value is not None:
                    
                    ( operator, name ) = self._value
                    
                    if operator:
                        
                        base = 'has note with name "{}"'.format( name )
                        
                    else:
                        
                        base = 'does not have note with name "{}"'.format( name )
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_TAGS:
                
                base = 'number of tags'
                
                if self._value is not None:
                    
                    ( namespace, operator, value ) = self._value
                    
                    number_test = ClientNumberTest.NumberTest.STATICCreateFromCharacters( operator, value )
                    
                    any_namespace = namespace is None or namespace == '*'
                    
                    if number_test.IsAnythingButZero():
                        
                        if any_namespace:
                            
                            base = 'has tags'
                            
                        else:
                            
                            # shouldn't see this, as it'll be converted to a namespace pred, but here anyway
                            base = 'has {} tags'.format( ClientTags.RenderNamespaceForUser( namespace ) )
                            
                        
                    elif number_test.IsZero():
                        
                        if any_namespace:
                            
                            base = 'untagged'
                            
                        else:
                            
                            # shouldn't see this, as it'll be converted to a namespace pred, but here anyway
                            base = 'no {} tags'.format( ClientTags.RenderNamespaceForUser( namespace ) )
                            
                        
                    else:
                        
                        if not any_namespace:
                            
                            base = 'number of {} tags'.format( ClientTags.RenderNamespaceForUser( namespace ) )
                            
                        
                        base += ' {} {}'.format( operator, HydrusNumbers.ToHumanInt( value ) )
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_RATIO:
                
                base = 'ratio'
                
                if self._value is not None:
                    
                    ( operator, ratio_width, ratio_height ) = self._value
                    
                    base += ' ' + operator + ' ' + str( ratio_width ) + ':' + str( ratio_height )
                    
                    if ratio_width == 1 and ratio_height == 1:
                        
                        if operator == 'wider than':
                            
                            base = 'ratio is landscape'
                            
                        elif operator == 'taller than':
                            
                            base = 'ratio is portrait'
                            
                        elif operator == '=':
                            
                            base = 'ratio is square'
                            
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIZE:
                
                base = 'filesize'
                
                if self._value is not None:
                    
                    ( operator, size, unit ) = self._value
                    
                    base += ' ' + operator + ' ' + str( size ) + HydrusNumbers.IntToUnit( unit )
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_LIMIT:
                
                base = 'limit'
                
                if self._value is not None:
                    
                    value = self._value
                    
                    base += ' is ' + HydrusNumbers.ToHumanInt( value )
                    
                
            elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_IMPORT_TIME, PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME  ):
                
                if self._predicate_type == PREDICATE_TYPE_SYSTEM_IMPORT_TIME:
                    
                    base = 'import time'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME:
                    
                    base = 'last viewed time'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_MODIFIED_TIME:
                    
                    base = 'modified time'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME:
                    
                    base = 'archived time'
                    
                
                if self._value is not None:
                    
                    ( operator, age_type, age_value ) = self._value
                    
                    if age_type == 'delta':
                        
                        ( years, months, days, hours ) = age_value
                        
                        str_components = []
                        
                        for ( quantity, label ) in [
                            ( years, 'year' ),
                            ( months, 'month' ),
                            ( days, 'day' ),
                            ( hours, 'hour' ),
                        ]:
                            
                            if quantity > 0:
                                
                                str_component = '{} {}'.format( HydrusNumbers.ToHumanInt( quantity ), label )
                                
                                if quantity > 1:
                                    
                                    str_component += 's'
                                    
                                
                                str_components.append( str_component )
                                
                            
                            if len( str_components ) == 2:
                                
                                break
                                
                            
                        
                        nice_date_string = ' '.join( str_components )
                        
                        if operator == '<':
                            
                            pretty_operator = 'since'
                            
                        elif operator == '>':
                            
                            pretty_operator = 'before'
                            
                        elif operator == HC.UNICODE_APPROX_EQUAL:
                            
                            pretty_operator = 'around'
                            
                        else:
                            
                            pretty_operator = 'unknown operator'
                            
                        
                        base += ': {} {} ago'.format( pretty_operator, nice_date_string )
                        
                    elif age_type == 'date':
                        
                        ( year, month, day, hour, minute ) = age_value
                        
                        dt = datetime.datetime( year, month, day, hour, minute )
                        
                        if operator == '<':
                            
                            pretty_operator = 'before '
                            
                        elif operator == '>':
                            
                            pretty_operator = 'since '
                            
                        elif operator == '=':
                            
                            pretty_operator = 'on the day of '
                            
                        elif operator == HC.UNICODE_APPROX_EQUAL:
                            
                            pretty_operator = 'a month either side of '
                            
                        else:
                            
                            pretty_operator = 'unknown operator'
                            
                        
                        include_24h_time = operator != '=' and ( hour > 0 or minute > 0 )
                        
                        base += ': ' + pretty_operator + HydrusTime.DateTimeToPrettyTime( dt, include_24h_time = include_24h_time )
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_PIXELS:
                
                base = 'number of pixels'
                
                if self._value is not None:
                    
                    ( operator, num_pixels, unit ) = self._value
                    
                    base += ' ' + operator + ' ' + str( num_pixels ) + ' ' + HydrusNumbers.IntToPixels( unit )
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
                
                base = 'known url'
                
                if self._value is not None:
                    
                    ( operator, rule_type, rule, description ) = self._value
                    
                    base = description
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_AUDIO:
                
                base = 'has audio'
                
                if self._value is not None:
                    
                    has_audio = self._value
                    
                    if not has_audio:
                        
                        base = 'no audio'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY:
                
                base = 'has transparency'
                
                if self._value is not None:
                    
                    has_transparency = self._value
                    
                    if not has_transparency:
                        
                        base = 'no transparency'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_EXIF:
                
                base = 'has exif'
                
                if self._value is not None:
                    
                    has_exif = self._value
                    
                    if not has_exif:
                        
                        base = 'no exif'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA:
                
                base = 'has embedded metadata'
                
                if self._value is not None:
                    
                    has_human_readable_embedded_metadata = self._value
                    
                    if not has_human_readable_embedded_metadata:
                        
                        base = 'no embedded metadata'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE:
                
                base = 'has icc profile'
                
                if self._value is not None:
                    
                    has_icc_profile = self._value
                    
                    if not has_icc_profile:
                        
                        base = 'no icc profile'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE:
                
                base = 'has forced filetype'
                
                if self._value is not None:
                    
                    has_forced_filetype = self._value
                    
                    if not has_forced_filetype:
                        
                        base = 'no forced filetype'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HASH:
                
                base = 'hash'
                
                if self._value is not None:
                    
                    ( hashes, hash_type ) = self._value
                    
                    if self._inclusive:
                        
                        is_phrase = 'is'
                        
                    else:
                        
                        is_phrase = 'is not'
                        
                    
                    if len( hashes ) > 1:
                        
                        is_phrase += ' in'
                        
                    
                    if hash_type != 'sha256':
                        
                        base = f'hash ({hash_type})'
                        
                    
                    if len( hashes ) == 1 or for_parsable_export:
                        
                        hashes_string = ', '.join( ( hash.hex() for hash in hashes ) )
                        
                        base = f'{base} {is_phrase} {hashes_string}'
                        
                    else:
                        
                        base = f'{base} {is_phrase} {HydrusNumbers.ToHumanInt( len( hashes ) )} hashes'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_TAG_ADVANCED:
                
                if self._value is None:
                    
                    base = 'tag (advanced)'
                    
                else:
                    
                    if self._inclusive:
                        
                        base = 'has tag'
                        
                    else:
                        
                        base = 'does not have tag'
                        
                    
                    ( service_key_or_none, tag_display_type, statuses, tag ) = self._value
                    
                    do_more = True
                    
                    if service_key_or_none is None:
                        
                        pass
                        
                    else:
                        
                        try:
                            
                            service = CG.client_controller.services_manager.GetService( service_key_or_none )
                            
                            name = service.GetName()
                            
                            base += f' in "{name}"'
                            
                        except HydrusExceptions.DataMissing:
                            
                            base = 'unknown tag service advanced tag predicate'
                            
                            do_more = False
                            
                        
                    
                    if do_more:
                        
                        if tag_display_type == ClientTags.TAG_DISPLAY_STORAGE:
                            
                            base += ', ignoring siblings/parents'
                            
                        
                        if set( statuses ) != { HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING }:
                            
                            if len( statuses ) == 1:
                                
                                ( status, ) = statuses
                                
                                base += f', with status {HC.content_status_string_lookup[ status ]}'
                                
                            else:
                                
                                status_string = ', '.join( [ HC.content_status_string_lookup[ status ] for status in sorted( statuses ) ] )
                                
                                base += f', with status in {status_string}'
                                
                            
                        
                        base += f': "{tag}"'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_MIME:
                
                base = 'filetype'
                
                if self._value is not None:
                    
                    summary_mimes = self._value
                    
                    mime_text = ConvertSummaryFiletypesToString( summary_mimes )
                    
                    connector = ' is ' if self._inclusive else ' is not '
                    
                    base += connector + mime_text
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_RATING:
                
                base = 'rating'
                
                if self._value is not None:
                    
                    ( operator, value, service_key ) = self._value
                    
                    try:
                        
                        pretty_operator = ClientNumberTest.number_test_operator_to_pretty_str_lookup.get( ClientNumberTest.legacy_str_operator_to_number_test_operator_lookup.get( operator, 'unknown' ), 'unknown' )
                        
                        service = CG.client_controller.services_manager.GetService( service_key )
                        
                        name = service.GetName()
                        
                        if service.GetServiceType() == HC.LOCAL_RATING_INCDEC:
                            
                            if operator == '>' and value == 0:
                                
                                base = f'has count for {name}'
                                
                            elif ( operator == '<' and value == 1 ) or ( operator == '=' and value == 0 ):
                                
                                base = f'no count for {name}'
                                
                            else:
                                
                                pretty_value = service.ConvertNoneableRatingToString( value )
                                
                                base = f'count for {name} {pretty_operator} {pretty_value}'
                                
                            
                        else:
                            
                            if value == 'rated':
                                
                                base = f'has rating for {name}'
                                
                            elif value == 'not rated':
                                
                                base = f'no rating for {name}'
                                
                            else:
                                
                                pretty_value = service.ConvertNoneableRatingToString( value )
                                
                                base = f'rating for {name} {pretty_operator} {pretty_value}'
                                
                            
                        
                    except HydrusExceptions.DataMissing:
                        
                        base = 'missing rating service system predicate'
                        
                    except:
                        
                        base = 'unknown rating service system predicate'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES:
                
                base = 'similar to'
                
                if self._value is not None:
                    
                    ( hashes, max_hamming ) = self._value
                    
                    if for_parsable_export:
                        
                        hash_string = ', '.join( ( hash.hex() for hash in hashes ) )
                        
                    else:
                        
                        hash_string = f'{HydrusNumbers.ToHumanInt( len( hashes ) )} files'
                        
                    
                    base += f' {hash_string} with distance of {max_hamming}'
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA:
                
                base = 'similar to data'
                
                if self._value is not None:
                    
                    ( pixel_hashes, perceptual_hashes, max_hamming ) = self._value
                    
                    all_hashes = list( pixel_hashes ) + list( perceptual_hashes )
                    
                    if for_parsable_export:
                        
                        hash_string = ', '.join( ( hash.hex() for hash in all_hashes ) )
                        
                    else:
                        
                        components = []
                        
                        if len( pixel_hashes ) > 0:
                            
                            components.append( f'{HydrusNumbers.ToHumanInt( len( pixel_hashes ) )} pixel')
                            
                        
                        if len( perceptual_hashes ) > 0:
                            
                            components.append( f'{HydrusNumbers.ToHumanInt( len( perceptual_hashes ) )} perceptual')
                            
                        
                        component_string = ', '.join( components )
                        
                        hash_string = f'({component_string} hashes)'
                        
                    
                    if len( perceptual_hashes ) > 0:
                        
                        base += f' {hash_string} with distance of {max_hamming}'
                        
                    else:
                        
                        base += f' {hash_string}'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
                
                if self._value is None:
                    
                    base = 'file service'
                    
                else:
                    
                    ( operator, status, service_key ) = self._value
                    
                    base = 'is' if operator else 'is not'
                    
                    if status == HC.CONTENT_STATUS_CURRENT:
                        
                        base += ' currently in '
                        
                    elif status == HC.CONTENT_STATUS_DELETED:
                        
                        base += ' deleted from '
                        
                    elif status == HC.CONTENT_STATUS_PENDING:
                        
                        base += ' pending to '
                        
                    elif status == HC.CONTENT_STATUS_PETITIONED:
                        
                        base += ' petitioned from '
                        
                    
                    try:
                        
                        service = CG.client_controller.services_manager.GetService( service_key )
                        
                        base += service.GetName()
                        
                    except HydrusExceptions.DataMissing:
                        
                        base = 'unknown file service system predicate'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
                
                base = 'tag as number'
                
                if self._value is not None:
                    
                    ( namespace, operator, num ) = self._value
                    
                    if namespace == '*':
                        
                        n_text = 'any namespace'
                        
                    elif namespace == '':
                        
                        n_text = 'unnamespaced'
                        
                    else:
                        
                        n_text = namespace
                        
                    
                    if operator == HC.UNICODE_APPROX_EQUAL:
                        
                        o_text = 'about'
                        
                    elif operator == '<':
                        
                        o_text = 'less than'
                        
                    elif operator == '>':
                        
                        o_text = 'more than'
                        
                    else:
                        
                        o_text = 'unknown'
                        
                    
                    base = f'{base}: {n_text} {o_text} {HydrusNumbers.ToHumanInt( num )}'
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT:
                
                base = 'num file relationships'
                
                if self._value is not None:
                    
                    ( operator, num_relationships, dupe_type ) = self._value
                    
                    if operator == HC.UNICODE_APPROX_EQUAL:
                        
                        o_text = ' about '
                        
                    elif operator == '<':
                        
                        o_text = ' less than '
                        
                    elif operator == '>':
                        
                        o_text = ' more than '
                        
                    elif operator == '=':
                        
                        o_text = ' '
                        
                    
                    base += ' - has' + o_text + HydrusNumbers.ToHumanInt( num_relationships ) + ' ' + HC.duplicate_type_string_lookup[ dupe_type ]
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING:
                
                base = ''
                
                if self._value is not None:
                    
                    king = self._value
                    
                    if king:
                        
                        o_text = 'is the best quality file of its duplicate group'
                        
                    else:
                        
                        o_text = 'is not the best quality file of its duplicate group'
                        
                    
                    base += o_text
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
                
                base = 'file viewing statistics'
                
                if self._value is not None:
                    
                    ( view_type, viewing_locations, operator, viewing_value ) = self._value
                    
                    if len( viewing_locations ) == 0:
                        
                        domain = 'unknown'
                        
                    else:
                        
                        domain = ', '.join( viewing_locations )
                        
                    
                    if view_type == 'views':
                        
                        value_string = HydrusNumbers.ToHumanInt( viewing_value )
                        
                    elif view_type == 'viewtime':
                        
                        value_string = HydrusTime.TimeDeltaToPrettyTimeDelta( viewing_value )
                        
                    else:
                        
                        value_string = 'Unknown view type!'
                        
                    
                    base = '{} in {} {} {}'.format( view_type, domain, operator, value_string )
                    
                
            
            base = HydrusTags.CombineTag( 'system', base )
            
            base = ClientTags.RenderTag( base, render_for_user )
            
            base += count_text
            
        elif self._predicate_type == PREDICATE_TYPE_TAG:
            
            tag = self._value
            
            if not self._inclusive: base = '-'
            else: base = ''
            
            base += ClientTags.RenderTag( tag, render_for_user )
            
            base += count_text
            
        elif self._predicate_type == PREDICATE_TYPE_PARENT:
            
            if for_parsable_export:
                
                base = ''
                
            else:
                
                base = '    '
                
            
            tag = self._value
            
            base += ClientTags.RenderTag( tag, render_for_user )
            
            base += count_text
            
        elif self._predicate_type == PREDICATE_TYPE_NAMESPACE:
            
            namespace = self._value
            
            if not self._inclusive: base = '-'
            else: base = ''
            
            pretty_namespace = ClientTags.RenderNamespaceForUser( namespace )
            
            anything_tag = HydrusTags.CombineTag( pretty_namespace, '*anything*' )
            
            anything_tag = ClientTags.RenderTag( anything_tag, render_for_user )
            
            base += anything_tag
            
        elif self._predicate_type == PREDICATE_TYPE_WILDCARD:
            
            if self._value.startswith( '*:' ):
                
                ( any_namespace, subtag ) = HydrusTags.SplitTag( self._value )
                
                wildcard = '{} (any namespace)'.format( subtag )
                
            else:
                
                wildcard = self._value + ' (wildcard search)'
                
            
            if not self._inclusive:
                
                base = '-'
                
            else:
                
                base = ''
                
            
            base += wildcard
            
        elif self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            or_predicates = self._value
            
            base = ''
            
            if or_under_construction:
                
                base += 'OR: '
                
            
            base += ' OR '.join( ( or_predicate.ToString( render_for_user = render_for_user ) for or_predicate in or_predicates ) ) # pylint: disable=E1101
            
        elif self._predicate_type == PREDICATE_TYPE_LABEL:
            
            label = self._value
            
            base = label
            
        
        return base
        
    
    def ToString( self, with_count: bool = True, render_for_user: bool = False, or_under_construction: bool = False, for_parsable_export: bool = False ) -> str:
        
        try:
            
            return self._ToString( with_count = with_count, render_for_user = render_for_user, or_under_construction = or_under_construction, for_parsable_export = for_parsable_export )
            
        except Exception as e:
            
            HydrusData.PrintException( e, do_wait = False )
            
            return 'error:cannot render this predicate, check log'
            
        
    

def MergePredicates( predicates: collections.abc.Collection[ Predicate ] ):
    
    master_predicate_dict = {}
    
    for predicate in predicates:
        
        # this works because predicate.__hash__ exists
        
        if predicate in master_predicate_dict:
            
            master_predicate_dict[ predicate ].GetCount().AddCounts( predicate.GetCount() )
            
        else:
            
            master_predicate_dict[ predicate ] = predicate
            
        
    
    return list( master_predicate_dict.values() )
    

def SortPredicates( predicates: list[ Predicate ] ):
    
    key = lambda p: ( - p.GetCount().GetMinCount(), p.ToString() )
    
    predicates.sort( key = key )
    
    return predicates
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PREDICATE ] = Predicate

SYSTEM_PREDICATE_INBOX = Predicate( PREDICATE_TYPE_SYSTEM_INBOX, None )

SYSTEM_PREDICATE_ARCHIVE = Predicate( PREDICATE_TYPE_SYSTEM_ARCHIVE, None )

SYSTEM_PREDICATE_LOCAL = Predicate( PREDICATE_TYPE_SYSTEM_LOCAL, None )

SYSTEM_PREDICATE_NOT_LOCAL = Predicate( PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None )
