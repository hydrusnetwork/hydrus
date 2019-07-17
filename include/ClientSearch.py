import calendar
from . import ClientConstants as CC
from . import ClientData
from . import ClientTags
import datetime
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
from . import HydrusTags
import re
import time
import wx

IGNORED_TAG_SEARCH_CHARACTERS = '[](){}"\''
IGNORED_TAG_SEARCH_CHARACTERS_UNICODE_TRANSLATE = { ord( char ) : None for char in IGNORED_TAG_SEARCH_CHARACTERS }

def ConvertTagToSearchable( tag ):
    
    if tag == '':
        
        return ''
        
    
    while '**' in tag:
        
        tag = tag.replace( '**', '*' )
        
    
    if IsComplexWildcard( tag ):
        
        return tag
        
    
    tag = tag.translate( IGNORED_TAG_SEARCH_CHARACTERS_UNICODE_TRANSLATE )
    
    return tag

def ConvertEntryTextToSearchText( entry_text ):
    
    entry_text = HydrusTags.CleanTag( entry_text )
    
    entry_text = ConvertTagToSearchable( entry_text )
    
    if not IsComplexWildcard( entry_text ) and not entry_text.endswith( '*' ):
        
        entry_text = entry_text + '*'
        
    
    return entry_text
    
def FilterPredicatesBySearchText( service_key, search_text, predicates ):
    
    tags_to_predicates = {}
    
    for predicate in predicates:
        
        ( predicate_type, value, inclusive ) = predicate.GetInfo()
        
        if predicate_type == HC.PREDICATE_TYPE_TAG:
            
            tags_to_predicates[ value ] = predicate
            
        
    
    matching_tags = FilterTagsBySearchText( service_key, search_text, list(tags_to_predicates.keys()) )
    
    matches = [ tags_to_predicates[ tag ] for tag in matching_tags ]
    
    return matches
    
def FilterTagsBySearchText( service_key, search_text, tags, search_siblings = True ):
    
    def compile_re( s ):
        
        regular_parts_of_s = s.split( '*' )
        
        escaped_parts_of_s = list(map( re.escape, regular_parts_of_s ))
        
        s = '.*'.join( escaped_parts_of_s )
        
        # \A is start of string
        # \Z is end of string
        # \s is whitespace
        
        if s.startswith( '.*' ):
            
            beginning = '(\\A|:)'
            
        else:
            
            beginning = '(\\A|:|\\s)'
            
        
        if s.endswith( '.*' ):
            
            end = '\\Z' # end of string
            
        else:
            
            end = '(\\s|\\Z)' # whitespace or end of string
            
        
        return re.compile( beginning + s + end )
        
    
    re_predicate = compile_re( search_text )
    
    siblings_manager = HG.client_controller.tag_siblings_manager
    
    result = []
    
    for tag in tags:
        
        if search_siblings:
            
            possible_tags = siblings_manager.GetAllSiblings( service_key, tag )
            
        else:
            
            possible_tags = [ tag ]
            
        
        if not IsComplexWildcard( search_text ):
            
            possible_tags = list(map( ConvertTagToSearchable, possible_tags ))
            
        
        for possible_tag in possible_tags:
            
            if re_predicate.search( possible_tag ) is not None:
                
                result.append( tag )
                
                break
                
            
        
    
    return result
    
def IsComplexWildcard( search_text ):
    
    num_stars = search_text.count( '*' )
    
    if num_stars > 1:
        
        return True
        
    
    if num_stars == 1 and not search_text.endswith( '*' ):
        
        return True
        
    
    return False
    
def SortPredicates( predicates ):
    
    key = lambda p: p.GetCount()
    
    predicates.sort( key = key, reverse = True )
    
    return predicates

SEARCH_TYPE_AND = 0
SEARCH_TYPE_OR = 1

class FileSearchContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT
    SERIALISABLE_NAME = 'File Search Context'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, file_service_key = CC.COMBINED_FILE_SERVICE_KEY, tag_service_key = CC.COMBINED_TAG_SERVICE_KEY, search_type = SEARCH_TYPE_AND, include_current_tags = True, include_pending_tags = True, predicates = None ):
        
        if predicates is None: predicates = []
        
        self._file_service_key = file_service_key
        self._tag_service_key = tag_service_key
        
        self._search_type = search_type
        
        self._include_current_tags = include_current_tags
        self._include_pending_tags = include_pending_tags
        
        self._predicates = predicates
        
        self._search_complete = False
        
        self._InitialiseTemporaryVariables()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_predicates = [ predicate.GetSerialisableTuple() for predicate in self._predicates ]
        
        return ( self._file_service_key.hex(), self._tag_service_key.hex(), self._search_type, self._include_current_tags, self._include_pending_tags, serialisable_predicates, self._search_complete )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( file_service_key, tag_service_key, self._search_type, self._include_current_tags, self._include_pending_tags, serialisable_predicates, self._search_complete ) = serialisable_info
        
        self._file_service_key = bytes.fromhex( file_service_key )
        self._tag_service_key = bytes.fromhex( tag_service_key )
        
        services_manager = HG.client_controller.services_manager
        
        if not services_manager.ServiceExists( self._file_service_key ):
            
            self._file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
            
        
        if not services_manager.ServiceExists( self._tag_service_key ):
            
            self._tag_service_key = CC.COMBINED_TAG_SERVICE_KEY
            
        
        self._predicates = [ HydrusSerialisable.CreateFromSerialisableTuple( pred_tuple ) for pred_tuple in serialisable_predicates ]
        
        self._InitialiseTemporaryVariables()
        
    
    def _InitialiseTemporaryVariables( self ):
        
        system_predicates = [ predicate for predicate in self._predicates if predicate.GetType() in HC.SYSTEM_PREDICATES ]
        
        self._system_predicates = FileSystemPredicates( system_predicates )
        
        tag_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == HC.PREDICATE_TYPE_TAG ]
        
        self._tags_to_include = []
        self._tags_to_exclude = []
        
        for predicate in tag_predicates:
            
            tag = predicate.GetValue()
            
            if predicate.GetInclusive(): self._tags_to_include.append( tag )
            else: self._tags_to_exclude.append( tag )
            
        
        namespace_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == HC.PREDICATE_TYPE_NAMESPACE ]
        
        self._namespaces_to_include = []
        self._namespaces_to_exclude = []
        
        for predicate in namespace_predicates:
            
            namespace = predicate.GetValue()
            
            if predicate.GetInclusive(): self._namespaces_to_include.append( namespace )
            else: self._namespaces_to_exclude.append( namespace )
            
        
        wildcard_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == HC.PREDICATE_TYPE_WILDCARD ]
        
        self._wildcards_to_include = []
        self._wildcards_to_exclude = []
        
        for predicate in wildcard_predicates:
            
            wildcard = predicate.GetValue()
            
            if predicate.GetInclusive(): self._wildcards_to_include.append( wildcard )
            else: self._wildcards_to_exclude.append( wildcard )
            
        
        self._or_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == HC.PREDICATE_TYPE_OR_CONTAINER ]
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( file_service_key_hex, tag_service_key_hex, include_current_tags, include_pending_tags, serialisable_predicates, search_complete ) = old_serialisable_info
            
            search_type = SEARCH_TYPE_AND
            
            new_serialisable_info = ( file_service_key_hex, tag_service_key_hex, search_type, include_current_tags, include_pending_tags, serialisable_predicates, search_complete )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( file_service_key_hex, tag_service_key_hex, search_type, include_current_tags, include_pending_tags, serialisable_predicates, search_complete ) = old_serialisable_info
            
            # screwed up the serialisation code for the previous update, so these were getting swapped
            
            search_type = SEARCH_TYPE_AND
            include_current_tags = True
            
            new_serialisable_info = ( file_service_key_hex, tag_service_key_hex, search_type, include_current_tags, include_pending_tags, serialisable_predicates, search_complete )
            
            return ( 3, new_serialisable_info )
            
        
    
    def GetFileServiceKey( self ): return self._file_service_key
    def GetNamespacesToExclude( self ): return self._namespaces_to_exclude
    def GetNamespacesToInclude( self ): return self._namespaces_to_include
    def GetORPredicates( self ): return self._or_predicates
    def GetPredicates( self ): return self._predicates
    def GetSystemPredicates( self ): return self._system_predicates
    def GetTagServiceKey( self ): return self._tag_service_key
    def GetTagsToExclude( self ): return self._tags_to_exclude
    def GetTagsToInclude( self ): return self._tags_to_include
    def GetWildcardsToExclude( self ): return self._wildcards_to_exclude
    def GetWildcardsToInclude( self ): return self._wildcards_to_include
    
    def HasNoPredicates( self ):
        
        return len( self._predicates ) == 0
        
    
    def IncludeCurrentTags( self ): return self._include_current_tags
    def IncludePendingTags( self ): return self._include_pending_tags
    def IsComplete( self ): return self._search_complete
    
    def IsJustSystemEverything( self ):
        
        return len( self._predicates ) == 1 and self._system_predicates.HasSystemEverything()
        
    
    def SetComplete( self ): self._search_complete = True
    
    def SetFileServiceKey( self, file_service_key ):
        
        self._file_service_key = file_service_key
        
    
    def SetIncludeCurrentTags( self, value ):
        
        self._include_current_tags = value
        
    
    def SetIncludePendingTags( self, value ):
        
        self._include_pending_tags = value
        
    
    def SetPredicates( self, predicates ):
        
        self._predicates = predicates
        
        self._InitialiseTemporaryVariables()
        
    
    def SetTagServiceKey( self, tag_service_key ):
        
        self._tag_service_key = tag_service_key
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT ] = FileSearchContext

class FileSystemPredicates( object ):
    
    def __init__( self, system_predicates, apply_implicit_limit = True ):
        
        self._has_system_everything = False
        
        self._inbox = False
        self._archive = False
        self._local = False
        self._not_local = False
        
        self._common_info = {}
        
        self._limit = None
        self._similar_to = None
        
        self._file_services_to_include_current = []
        self._file_services_to_include_pending = []
        self._file_services_to_exclude_current = []
        self._file_services_to_exclude_pending = []
        
        self._ratings_predicates = []
        
        self._duplicate_count_predicates = []
        
        self._file_viewing_stats_predicates = []
        
        new_options = HG.client_controller.new_options
        
        for predicate in system_predicates:
            
            predicate_type = predicate.GetType()
            value = predicate.GetValue()
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_EVERYTHING: self._has_system_everything = True
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_INBOX: self._inbox = True
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_ARCHIVE: self._archive = True
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_LOCAL: self._local = True
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL: self._not_local = True
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
                
                ( operator, rule_type, rule, description ) = value
                
                if 'known_url_rules' not in self._common_info:
                    
                    self._common_info[ 'known_url_rules' ] = []
                    
                
                self._common_info[ 'known_url_rules' ].append( ( operator, rule_type, rule ) )
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_HASH:
                
                ( hash, hash_type ) = value
                
                self._common_info[ 'hash' ] = ( hash, hash_type )
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_AGE:
                
                ( operator, age_type, age_value ) = value
                
                if age_type == 'delta':
                    
                    ( years, months, days, hours ) = age_value
                    
                    age = ( ( ( ( ( ( ( years * 12 ) + months ) * 30 ) + days ) * 24 ) + hours ) * 3600 )
                    
                    now = HydrusData.GetNow()
                    
                    # this is backwards (less than means min timestamp) because we are talking about age, not timestamp
                    
                    if operator == '<':
                        
                        self._common_info[ 'min_timestamp' ] = now - age
                        
                    elif operator == '>':
                        
                        self._common_info[ 'max_timestamp' ] = now - age
                        
                    elif operator == '\u2248':
                        
                        self._common_info[ 'min_timestamp' ] = now - int( age * 1.15 )
                        self._common_info[ 'max_timestamp' ] = now - int( age * 0.85 )
                        
                    
                elif age_type == 'date':
                    
                    ( year, month, day ) = age_value
                    
                    # convert this dt, which is in local time, to a gmt timestamp
                    
                    day_dt = datetime.datetime( year, month, day )
                    timestamp = int( time.mktime( day_dt.timetuple() ) )
                    
                    if operator == '<':
                        
                        self._common_info[ 'max_timestamp' ] = timestamp
                        
                    elif operator == '>':
                        
                        self._common_info[ 'min_timestamp' ] = timestamp + 86400
                        
                    elif operator == '=':
                        
                        self._common_info[ 'min_timestamp' ] = timestamp
                        self._common_info[ 'max_timestamp' ] = timestamp + 86400
                        
                    elif operator == '\u2248':
                        
                        self._common_info[ 'min_timestamp' ] = timestamp - 86400 * 30
                        self._common_info[ 'max_timestamp' ] = timestamp + 86400 * 30
                        
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_MIME:
                
                mimes = value
                
                if isinstance( mimes, int ): mimes = ( mimes, )
                
                self._common_info[ 'mimes' ] = mimes
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_DURATION:
                
                ( operator, duration ) = value
                
                if operator == '<': self._common_info[ 'max_duration' ] = duration
                elif operator == '>': self._common_info[ 'min_duration' ] = duration
                elif operator == '=': self._common_info[ 'duration' ] = duration
                elif operator == '\u2248':
                    
                    if duration == 0:
                        
                        self._common_info[ 'duration' ] = 0
                        
                    else:
                        
                        self._common_info[ 'min_duration' ] = int( duration * 0.85 )
                        self._common_info[ 'max_duration' ] = int( duration * 1.15 )
                        
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATING:
                
                ( operator, value, service_key ) = value
                
                self._ratings_predicates.append( ( operator, value, service_key ) )
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATIO:
                
                ( operator, ratio_width, ratio_height ) = value
                
                if operator == '=': self._common_info[ 'ratio' ] = ( ratio_width, ratio_height )
                elif operator == 'wider than':
                    
                    self._common_info[ 'min_ratio' ] = ( ratio_width, ratio_height )
                    
                elif operator == 'taller than':
                    
                    self._common_info[ 'max_ratio' ] = ( ratio_width, ratio_height )
                    
                elif operator == '\u2248':
                    
                    self._common_info[ 'min_ratio' ] = ( ratio_width * 0.85, ratio_height )
                    self._common_info[ 'max_ratio' ] = ( ratio_width * 1.15, ratio_height )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIZE:
                
                ( operator, size, unit ) = value
                
                size = size * unit
                
                if operator == '<': self._common_info[ 'max_size' ] = size
                elif operator == '>': self._common_info[ 'min_size' ] = size
                elif operator == '=': self._common_info[ 'size' ] = size
                elif operator == '\u2248':
                    
                    self._common_info[ 'min_size' ] = int( size * 0.85 )
                    self._common_info[ 'max_size' ] = int( size * 1.15 )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS:
                
                ( operator, num_tags ) = value
                
                if operator == '<': self._common_info[ 'max_num_tags' ] = num_tags
                elif operator == '=': self._common_info[ 'num_tags' ] = num_tags
                elif operator == '>': self._common_info[ 'min_num_tags' ] = num_tags
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
                
                ( namespace, operator, num ) = value
                
                if operator == '<': self._common_info[ 'max_tag_as_number' ] = ( namespace, num )
                elif operator == '>': self._common_info[ 'min_tag_as_number' ] = ( namespace, num )
                elif operator == '\u2248':
                    
                    self._common_info[ 'min_tag_as_number' ] = ( namespace, int( num * 0.85 ) )
                    self._common_info[ 'max_tag_as_number' ] = ( namespace, int( num * 1.15 ) )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_WIDTH:
                
                ( operator, width ) = value
                
                if operator == '<': self._common_info[ 'max_width' ] = width
                elif operator == '>': self._common_info[ 'min_width' ] = width
                elif operator == '=': self._common_info[ 'width' ] = width
                elif operator == '\u2248':
                    
                    if width == 0: self._common_info[ 'width' ] = 0
                    else:
                        
                        self._common_info[ 'min_width' ] = int( width * 0.85 )
                        self._common_info[ 'max_width' ] = int( width * 1.15 )
                        
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_PIXELS:
                
                ( operator, num_pixels, unit ) = value
                
                num_pixels = num_pixels * unit
                
                if operator == '<': self._common_info[ 'max_num_pixels' ] = num_pixels
                elif operator == '>': self._common_info[ 'min_num_pixels' ] = num_pixels
                elif operator == '=': self._common_info[ 'num_pixels' ] = num_pixels
                elif operator == '\u2248':
                    
                    self._common_info[ 'min_num_pixels' ] = int( num_pixels * 0.85 )
                    self._common_info[ 'max_num_pixels' ] = int( num_pixels * 1.15 )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_HEIGHT:
                
                ( operator, height ) = value
                
                if operator == '<': self._common_info[ 'max_height' ] = height
                elif operator == '>': self._common_info[ 'min_height' ] = height
                elif operator == '=': self._common_info[ 'height' ] = height
                elif operator == '\u2248':
                    
                    if height == 0: self._common_info[ 'height' ] = 0
                    else:
                        
                        self._common_info[ 'min_height' ] = int( height * 0.85 )
                        self._common_info[ 'max_height' ] = int( height * 1.15 )
                        
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS:
                
                ( operator, num_words ) = value
                
                if operator == '<': self._common_info[ 'max_num_words' ] = num_words
                elif operator == '>': self._common_info[ 'min_num_words' ] = num_words
                elif operator == '=': self._common_info[ 'num_words' ] = num_words
                elif operator == '\u2248':
                    
                    if num_words == 0: self._common_info[ 'num_words' ] = 0
                    else:
                        
                        self._common_info[ 'min_num_words' ] = int( num_words * 0.85 )
                        self._common_info[ 'max_num_words' ] = int( num_words * 1.15 )
                        
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_LIMIT:
                
                limit = value
                
                if self._limit is None:
                    
                    self._limit = limit
                    
                else:
                    
                    self._limit = min( limit, self._limit )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
                
                ( operator, current_or_pending, service_key ) = value
                
                if operator == True:
                    
                    if current_or_pending == HC.CONTENT_STATUS_CURRENT: self._file_services_to_include_current.append( service_key )
                    else: self._file_services_to_include_pending.append( service_key )
                    
                else:
                    
                    if current_or_pending == HC.CONTENT_STATUS_CURRENT: self._file_services_to_exclude_current.append( service_key )
                    else: self._file_services_to_exclude_pending.append( service_key )
                    
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
                
                ( hash, max_hamming ) = value
                
                self._similar_to = ( hash, max_hamming )
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_DUPLICATE_RELATIONSHIP_COUNT:
                
                ( operator, num_relationships, dupe_type ) = value
                
                self._duplicate_count_predicates.append( ( operator, num_relationships, dupe_type ) )
                
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
                
                ( view_type, viewing_locations, operator, viewing_value ) = value
                
                self._file_viewing_stats_predicates.append( ( view_type, viewing_locations, operator, viewing_value ) )
                
            
        
    
    def GetDuplicateRelationshipCountPredicates( self ):
        
        return self._duplicate_count_predicates
        
    
    def GetFileServiceInfo( self ):
        
        return ( self._file_services_to_include_current, self._file_services_to_include_pending, self._file_services_to_exclude_current, self._file_services_to_exclude_pending )
        
    
    def GetFileViewingStatsPredicates( self ):
        
        return self._file_viewing_stats_predicates
        
    
    def GetSimpleInfo( self ):
        
        return self._common_info
        
    
    def GetLimit( self, apply_implicit_limit = True ):
        
        if self._limit is None and apply_implicit_limit:
            
            forced_search_limit = HG.client_controller.new_options.GetNoneableInteger( 'forced_search_limit' )
            
            return forced_search_limit
            
        
        return self._limit
        
    
    def GetRatingsPredicates( self ): return self._ratings_predicates
    
    def GetSimilarTo( self ): return self._similar_to
    
    def HasSimilarTo( self ): return self._similar_to is not None
    
    def HasSystemEverything( self ):
        
        return self._has_system_everything
        
    
    def MustBeArchive( self ): return self._archive
    
    def MustBeInbox( self ): return self._inbox
    
    def MustBeLocal( self ): return self._local
    
    def MustNotBeLocal( self ): return self._not_local
    
class Predicate( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PREDICATE
    SERIALISABLE_NAME = 'File Search Predicate'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, predicate_type = None, value = None, inclusive = True, min_current_count = 0, min_pending_count = 0, max_current_count = None, max_pending_count = None ):
        
        if isinstance( value, ( list, set ) ):
            
            value = tuple( value )
            
        
        self._predicate_type = predicate_type
        self._value = value
        
        self._inclusive = inclusive
        
        self._min_current_count = min_current_count
        self._min_pending_count = min_pending_count
        self._max_current_count = max_current_count
        self._max_pending_count = max_pending_count
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self._predicate_type, self._value, self._inclusive ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        return 'Predicate: ' + str( ( self._predicate_type, self._value, self._inclusive, self.GetCount() ) )
        
    
    def _GetSerialisableInfo( self ):
        
        if self._predicate_type in ( HC.PREDICATE_TYPE_SYSTEM_RATING, HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE ):
            
            ( operator, value, service_key ) = self._value
            
            serialisable_value = ( operator, value, service_key.hex() )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
            
            ( hash, max_hamming ) = self._value
            
            serialisable_value = ( hash.hex(), max_hamming )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            ( operator, rule_type, rule, description ) = self._value
            
            if rule_type in ( 'url_match', 'url_class' ):
                
                serialisable_rule = rule.GetSerialisableTuple()
                
            else:
                
                serialisable_rule = rule
                
            
            serialisable_value = ( operator, rule_type, serialisable_rule, description )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_HASH:
            
            ( hash, hash_type ) = self._value
            
            serialisable_value = ( hash.hex(), hash_type )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_OR_CONTAINER:
            
            or_predicates = self._value
            
            serialisable_value = HydrusSerialisable.SerialisableList( or_predicates ).GetSerialisableTuple()
            
        else:
            
            serialisable_value = self._value
            
        
        return ( self._predicate_type, serialisable_value, self._inclusive )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._predicate_type, serialisable_value, self._inclusive ) = serialisable_info
        
        if self._predicate_type in ( HC.PREDICATE_TYPE_SYSTEM_RATING, HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE ):
            
            ( operator, value, service_key ) = serialisable_value
            
            self._value = ( operator, value, bytes.fromhex( service_key ) )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
            
            ( serialisable_hash, max_hamming ) = serialisable_value
            
            self._value = ( bytes.fromhex( serialisable_hash ), max_hamming )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            ( operator, rule_type, serialisable_rule, description ) = serialisable_value
            
            if rule_type in ( 'url_match', 'url_class' ):
                
                rule = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_rule )
                
            else:
                
                rule = serialisable_rule
                
            
            self._value = ( operator, rule_type, rule, description )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_HASH:
            
            ( serialisable_hash, hash_type ) = serialisable_value
            
            self._value = ( bytes.fromhex( serialisable_hash ), hash_type )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_AGE:
            
            ( operator, age_type, age_value ) = serialisable_value
            
            self._value = ( operator, age_type, tuple( age_value ) )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
            
            ( view_type, viewing_locations, operator, viewing_value ) = serialisable_value
            
            self._value = ( view_type, tuple( viewing_locations ), operator, viewing_value )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_OR_CONTAINER:
            
            serialisable_or_predicates = serialisable_value
            
            self._value = tuple( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_or_predicates ) )
            
        else:
            
            self._value = serialisable_value
            
        
        if isinstance( self._value, list ):
            
            self._value = tuple( self._value )
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type == HC.PREDICATE_TYPE_SYSTEM_AGE:
                
                ( operator, years, months, days, hours ) = serialisable_value
                
                serialisable_value = ( operator, 'delta', ( years, months, days, hours ) )
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 2, new_serialisable_info )
            
        
    
    def AddCounts( self, predicate ):
        
        ( min_current_count, max_current_count, min_pending_count, max_pending_count ) = predicate.GetAllCounts()
        
        ( self._min_current_count, self._max_current_count ) = ClientData.MergeCounts( self._min_current_count, self._max_current_count, min_current_count, max_current_count )
        ( self._min_pending_count, self._max_pending_count) = ClientData.MergeCounts( self._min_pending_count, self._max_pending_count, min_pending_count, max_pending_count )
        
    
    def GetAllCounts( self ):
        
        return ( self._min_current_count, self._max_current_count, self._min_pending_count, self._max_pending_count )
        
    
    def GetCopy( self ):
        
        return Predicate( self._predicate_type, self._value, self._inclusive, self._min_current_count, self._min_pending_count, self._max_current_count, self._max_pending_count )
        
    
    def GetCountlessCopy( self ):
        
        return Predicate( self._predicate_type, self._value, self._inclusive )
        
    
    def GetCount( self, current_or_pending = None ):
        
        if current_or_pending is None:
            
            return self._min_current_count + self._min_pending_count
            
        elif current_or_pending == HC.CONTENT_STATUS_CURRENT:
            
            return self._min_current_count
            
        elif current_or_pending == HC.CONTENT_STATUS_PENDING:
            
            return self._min_pending_count
            
        
    
    def GetNamespace( self ):
        
        if self._predicate_type in HC.SYSTEM_PREDICATES:
            
            return 'system'
            
        elif self._predicate_type == HC.PREDICATE_TYPE_NAMESPACE:
            
            namespace = self._value
            
            return namespace
            
        elif self._predicate_type in ( HC.PREDICATE_TYPE_PARENT, HC.PREDICATE_TYPE_TAG, HC.PREDICATE_TYPE_WILDCARD ):
            
            tag_analogue = self._value
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag_analogue )
            
            return namespace
            
        else:
            
            return ''
            
        
    
    def GetInclusive( self ):
        
        # patch from an upgrade mess-up ~v144
        if not hasattr( self, '_inclusive' ):
            
            if self._predicate_type not in HC.SYSTEM_PREDICATES:
                
                ( operator, value ) = self._value
                
                self._value = value
                
                self._inclusive = operator == '+'
                
            else: self._inclusive = True
            
        
        return self._inclusive
        
    
    def GetInfo( self ):
        
        return ( self._predicate_type, self._value, self._inclusive )
        
    
    def GetInverseCopy( self ):
        
        if self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_ARCHIVE:
            
            return Predicate( HC.PREDICATE_TYPE_SYSTEM_INBOX )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_INBOX:
            
            return Predicate( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_LOCAL:
            
            return Predicate( HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL:
            
            return Predicate( HC.PREDICATE_TYPE_SYSTEM_LOCAL )
            
        elif self._predicate_type in ( HC.PREDICATE_TYPE_TAG, HC.PREDICATE_TYPE_NAMESPACE, HC.PREDICATE_TYPE_WILDCARD ):
            
            return Predicate( self._predicate_type, self._value, not self._inclusive )
            
        else:
            
            return None
            
        
    
    def GetTextsAndNamespaces( self, or_under_construction = False ):
        
        if self._predicate_type == HC.PREDICATE_TYPE_OR_CONTAINER:
            
            texts_and_namespaces = []
            
            if or_under_construction:
                
                texts_and_namespaces.append( ( 'OR: ', 'system' ) )
                
            
            for or_predicate in self._value:
                
                texts_and_namespaces.append( ( or_predicate.ToString(), or_predicate.GetNamespace() ) )
                
                texts_and_namespaces.append( ( ' OR ', 'system' ) )
                
            
            texts_and_namespaces = texts_and_namespaces[ : -1 ]
            
        else:
            
            texts_and_namespaces = [ ( self.ToString(), self.GetNamespace() ) ]
            
        
        return texts_and_namespaces
        
    
    def GetType( self ):
        
        return self._predicate_type
        
    
    def IsInclusive( self ):
        
        return self._inclusive
        
    
    def ToString( self, with_count = True, sibling_service_key = None, render_for_user = False, or_under_construction = False ):
        
        count_text = ''
        
        if with_count:
            
            if self._min_current_count > 0:
                
                number_text = HydrusData.ToHumanInt( self._min_current_count )
                
                if self._max_current_count is not None:
                    
                    number_text += '-' + HydrusData.ToHumanInt( self._max_current_count )
                    
                
                count_text += ' (' + number_text + ')'
                
            
            if self._min_pending_count > 0:
                
                number_text = HydrusData.ToHumanInt( self._min_pending_count )
                
                if self._max_pending_count is not None:
                    
                    number_text += '-' + HydrusData.ToHumanInt( self._max_pending_count )
                    
                
                count_text += ' (+' + number_text + ')'
                
            
        
        if self._predicate_type in HC.SYSTEM_PREDICATES:
            
            if self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_EVERYTHING: base = 'everything'
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_INBOX: base = 'inbox'
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_ARCHIVE: base = 'archive'
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_UNTAGGED: base = 'untagged'
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_LOCAL: base = 'local'
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL: base = 'not local'
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_DIMENSIONS: base = 'dimensions'
            elif self._predicate_type in ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, HC.PREDICATE_TYPE_SYSTEM_WIDTH, HC.PREDICATE_TYPE_SYSTEM_HEIGHT, HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS ):
                
                if self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS: base = 'number of tags'
                elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_WIDTH: base = 'width'
                elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_HEIGHT: base = 'height'
                elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS: base = 'number of words'
                
                if self._value is not None:
                    
                    ( operator, value ) = self._value
                    
                    base += ' ' + operator + ' ' + HydrusData.ToHumanInt( value )
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_DURATION:
                
                base = 'duration'
                
                if self._value is not None:
                    
                    ( operator, value ) = self._value
                    
                    base += ' ' + operator + ' ' + HydrusData.ConvertMillisecondsToPrettyTime( value )
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATIO:
                
                base = 'ratio'
                
                if self._value is not None:
                    
                    ( operator, ratio_width, ratio_height ) = self._value
                    
                    base += ' ' + operator + ' ' + str( ratio_width ) + ':' + str( ratio_height )
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIZE:
                
                base = 'size'
                
                if self._value is not None:
                    
                    ( operator, size, unit ) = self._value
                    
                    base += ' ' + operator + ' ' + str( size ) + HydrusData.ConvertIntToUnit( unit )
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_LIMIT:
                
                base = 'limit'
                
                if self._value is not None:
                    
                    value = self._value
                    
                    base += ' is ' + HydrusData.ToHumanInt( value )
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_AGE:
                
                base = 'time imported'
                
                if self._value is not None:
                    
                    ( operator, age_type, age_value ) = self._value
                    
                    if age_type == 'delta':
                        
                        ( years, months, days, hours ) = age_value
                        
                        DAY = 86400
                        MONTH = DAY * 30
                        YEAR = MONTH * 12
                        
                        time_delta = 0
                        
                        time_delta += hours * 3600
                        time_delta += days * DAY
                        time_delta += months * MONTH
                        time_delta += years * YEAR
                        
                        if operator == '<':
                            
                            pretty_operator = 'since '
                            
                        elif operator == '>':
                            
                            pretty_operator = 'before '
                            
                        elif operator == '\u2248':
                            
                            pretty_operator = 'around '
                            
                        
                        base += ': ' + pretty_operator + HydrusData.TimeDeltaToPrettyTimeDelta( time_delta ) + ' ago'
                        
                    elif age_type == 'date':
                        
                        ( year, month, day ) = age_value
                        
                        dt = datetime.datetime( year, month, day )
                        
                        # make a timestamp (IN GMT SECS SINCE 1970) from the local meaning of 2018/02/01
                        timestamp = int( time.mktime( dt.timetuple() ) )
                        
                        if operator == '<':
                            
                            pretty_operator = 'before '
                            
                        elif operator == '>':
                            
                            pretty_operator = 'since '
                            
                        elif operator == '=':
                            
                            pretty_operator = 'on the day of '
                            
                        elif operator == '\u2248':
                            
                            pretty_operator = 'a month either side of '
                            
                        
                        # convert this GMT TIMESTAMP to a pretty local string
                        base += ': ' + pretty_operator + HydrusData.ConvertTimestampToPrettyTime( timestamp, include_24h_time = False )
                        
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_NUM_PIXELS:
                
                base = 'num_pixels'
                
                if self._value is not None:
                    
                    ( operator, num_pixels, unit ) = self._value
                    
                    base += ' ' + operator + ' ' + str( num_pixels ) + ' ' + HydrusData.ConvertIntToPixels( unit )
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
                
                base = 'known url'
                
                if self._value is not None:
                    
                    ( operator, rule_type, rule, description ) = self._value
                    
                    base = description
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_HASH:
                
                base = 'hash'
                
                if self._value is not None:
                    
                    ( hash, hash_type ) = self._value
                    
                    base = hash_type + ' hash is ' + hash.hex()
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_MIME:
                
                base = 'filetype'
                
                if self._value is not None:
                    
                    mimes = self._value
                    
                    if set( mimes ) == set( HC.SEARCHABLE_MIMES ):
                        
                        mime_text = 'anything'
                        
                    elif set( mimes ) == set( HC.SEARCHABLE_MIMES ).intersection( set( HC.APPLICATIONS ) ):
                        
                        mime_text = 'application'
                        
                    elif set( mimes ) == set( HC.SEARCHABLE_MIMES ).intersection( set( HC.AUDIO ) ):
                        
                        mime_text = 'audio'
                        
                    elif set( mimes ) == set( HC.SEARCHABLE_MIMES ).intersection( set( HC.IMAGES ) ):
                        
                        mime_text = 'image'
                        
                    elif set( mimes ) == set( HC.SEARCHABLE_MIMES ).intersection( set( HC.VIDEO ) ):
                        
                        mime_text = 'video'
                        
                    else:
                        
                        mime_text = ', '.join( [ HC.mime_string_lookup[ mime ] for mime in mimes ] )
                        
                    
                    base += ' is ' + mime_text
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_RATING:
                
                base = 'rating'
                
                if self._value is not None:
                    
                    ( operator, value, service_key ) = self._value
                    
                    try:
                        
                        service = HG.client_controller.services_manager.GetService( service_key )
                        
                        service_type = service.GetServiceType()
                        
                        pretty_value = str( value )
                        
                        if service_type == HC.LOCAL_RATING_LIKE:
                            
                            if value == 0:
                                
                                pretty_value = 'dislike'
                                
                            elif value == 1:
                                
                                pretty_value = 'like'
                                
                            
                        elif service_type == HC.LOCAL_RATING_NUMERICAL:
                            
                            if isinstance( value, float ):
                                
                                allow_zero = service.AllowZero()
                                num_stars = service.GetNumStars()
                                
                                if allow_zero:
                                    
                                    star_range = num_stars
                                    
                                else:
                                    
                                    star_range = num_stars - 1
                                    
                                
                                pretty_x = int( round( value * star_range ) )
                                pretty_y = num_stars
                                
                                if not allow_zero:
                                    
                                    pretty_x += 1
                                    
                                
                                pretty_value = HydrusData.ConvertValueRangeToPrettyString( pretty_x, pretty_y )
                                
                            
                        
                        base += ' for ' + service.GetName() + ' ' + operator + ' ' + pretty_value
                        
                    except HydrusExceptions.DataMissing:
                        
                        base = 'system:unknown rating service system predicate'
                        
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
                
                base = 'similar to'
                
                if self._value is not None:
                    
                    ( hash, max_hamming ) = self._value
                    
                    base += ' ' + hash.hex() + ' using max hamming of ' + str( max_hamming )
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
                
                if self._value is None:
                    
                    base = 'file service'
                    
                else:
                    
                    ( operator, current_or_pending, service_key ) = self._value
                    
                    if operator == True: base = 'is'
                    else: base = 'is not'
                    
                    if current_or_pending == HC.CONTENT_STATUS_PENDING: base += ' pending to '
                    else: base += ' currently in '
                    
                    try:
                        
                        service = HG.client_controller.services_manager.GetService( service_key )
                        
                        base += service.GetName()
                        
                    except HydrusExceptions.DataMissing:
                        
                        base = 'unknown file service system predicate'
                        
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
                
                if self._value is None:
                    
                    base = 'tag as number'
                    
                else:
                    
                    ( namespace, operator, num ) = self._value
                    
                    if namespace == '':
                        
                        n_text = 'tag'
                        
                    else:
                        
                        n_text = namespace
                        
                    
                    if operator == '\u2248':
                        
                        o_text = ' about '
                        
                    elif operator == '<':
                        
                        o_text = ' less than '
                        
                    elif operator == '>':
                        
                        o_text = ' more than '
                        
                    
                    base = n_text + o_text + HydrusData.ToHumanInt( num )
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_DUPLICATE_RELATIONSHIP_COUNT:
                
                base = 'num duplicate relationships'
                
                if self._value is not None:
                    
                    ( operator, num_relationships, dupe_type ) = self._value
                    
                    if operator == '\u2248':
                        
                        o_text = ' about '
                        
                    elif operator == '<':
                        
                        o_text = ' less than '
                        
                    elif operator == '>':
                        
                        o_text = ' more than '
                        
                    elif operator == '=':
                        
                        o_text = ' '
                        
                    
                    base += ' - has' + o_text + HydrusData.ToHumanInt( num_relationships ) + ' ' + HC.duplicate_type_string_lookup[ dupe_type ]
                    
                
            elif self._predicate_type == HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
                
                base = 'file viewing statistics'
                
                if self._value is not None:
                    
                    ( view_type, viewing_locations, operator, viewing_value ) = self._value
                    
                    include_media = 'media' in viewing_locations
                    include_previews = 'preview' in viewing_locations
                    
                    if include_media and include_previews:
                        
                        domain = 'all '
                        
                    elif include_media:
                        
                        domain = 'media '
                        
                    elif include_previews:
                        
                        domain = 'preview '
                        
                    else:
                        
                        domain = 'unknown '
                        
                    
                    if view_type == 'views':
                        
                        value_string = HydrusData.ToHumanInt( viewing_value )
                        
                    elif view_type == 'viewtime':
                        
                        value_string = HydrusData.TimeDeltaToPrettyTimeDelta( viewing_value )
                        
                    
                    base = domain + view_type + operator + value_string
                    
                
            
            base = HydrusTags.CombineTag( 'system', base )
            
            base = ClientTags.RenderTag( base, render_for_user )
            
            base += count_text
            
        elif self._predicate_type == HC.PREDICATE_TYPE_TAG:
            
            tag = self._value
            
            if not self._inclusive: base = '-'
            else: base = ''
            
            base += ClientTags.RenderTag( tag, render_for_user )
            
            base += count_text
            
            if sibling_service_key is not None:
                
                siblings_manager = HG.client_controller.tag_siblings_manager
                
                sibling = siblings_manager.GetSibling( sibling_service_key, tag )
                
                if sibling is not None:
                    
                    sibling = ClientTags.RenderTag( sibling, render_for_user )
                    
                    base += ' (will display as ' + sibling + ')'
                    
                
            
        elif self._predicate_type == HC.PREDICATE_TYPE_PARENT:
            
            base = '    '
            
            tag = self._value
            
            base += ClientTags.RenderTag( tag, render_for_user )
            
            base += count_text
            
        elif self._predicate_type == HC.PREDICATE_TYPE_NAMESPACE:
            
            namespace = self._value
            
            if not self._inclusive: base = '-'
            else: base = ''
            
            anything_tag = HydrusTags.CombineTag( namespace, '*anything*' )
            
            anything_tag = ClientTags.RenderTag( anything_tag, render_for_user )
            
            base += anything_tag
            
        elif self._predicate_type == HC.PREDICATE_TYPE_WILDCARD:
            
            wildcard = self._value + ' (wildcard search)'
            
            if not self._inclusive:
                
                base = '-'
                
            else:
                
                base = ''
                
            
            base += wildcard
            
        elif self._predicate_type == HC.PREDICATE_TYPE_OR_CONTAINER:
            
            or_predicates = self._value
            
            base = ''
            
            if or_under_construction:
                
                base += 'OR: '
                
            
            base += ' OR '.join( ( or_predicate.ToString( render_for_user = render_for_user ) for or_predicate in or_predicates ) )
            
        elif self._predicate_type == HC.PREDICATE_TYPE_LABEL:
            
            label = self._value
            
            base = label
            
        
        return base
        
    
    def GetUnnamespacedCopy( self ):
        
        if self._predicate_type == HC.PREDICATE_TYPE_TAG:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( self._value )
            
            return Predicate( self._predicate_type, subtag, self._inclusive, self._min_current_count, self._min_pending_count, self._max_current_count, self._max_pending_count )
            
        
        return self.GetCopy()
        
    
    def GetValue( self ):
        
        return self._value
        
    
    def HasNonZeroCount( self ):
        
        return self._min_current_count > 0 or self._min_pending_count > 0
        
    
    def SetInclusive( self, inclusive ):
        
        self._inclusive = inclusive
        

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PREDICATE ] = Predicate

SYSTEM_PREDICATE_INBOX = Predicate( HC.PREDICATE_TYPE_SYSTEM_INBOX, None )

SYSTEM_PREDICATE_ARCHIVE = Predicate( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE, None )

SYSTEM_PREDICATE_LOCAL = Predicate( HC.PREDICATE_TYPE_SYSTEM_LOCAL, None )

SYSTEM_PREDICATE_NOT_LOCAL = Predicate( HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None )
