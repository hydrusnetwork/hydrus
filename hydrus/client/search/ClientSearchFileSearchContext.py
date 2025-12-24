import collections
import collections.abc

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientTime
from hydrus.client.media import ClientMediaResult
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

SEARCH_TYPE_AND = 0
SEARCH_TYPE_OR = 1

class FileSystemPredicates( object ):
    
    def __init__( self, predicates: collections.abc.Collection[ ClientSearchPredicate.Predicate ] ):
        
        system_predicates = [ predicate for predicate in predicates if predicate.GetType() in ClientSearchPredicate.SYSTEM_PREDICATE_TYPES ]
        
        self._has_system_everything = False
        
        self._inbox = False
        self._archive = False
        self._local = False
        self._not_local = False
        
        self._common_info = {}
        self._system_pred_types_to_timestamp_ranges_ms = collections.defaultdict( dict )
        
        self._allowed_filetypes = None
        
        self._limit = None
        self._similar_to_files = None
        self._similar_to_data = None
        
        self._required_file_service_statuses = collections.defaultdict( set )
        self._excluded_file_service_statuses = collections.defaultdict( set )
        
        self._ratings_predicates = []
        self._advanced_ratings_predicates = []
        
        self._num_tags_predicates = []
        self._num_urls_predicates = []
        
        self._advanced_tag_predicates = []
        
        self._duplicate_count_predicates = []
        
        self._king_filter = None
        
        self._file_viewing_stats_predicates = []
        
        for predicate in system_predicates:
            
            predicate_type = predicate.GetType()
            value = predicate.GetValue()
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING: self._has_system_everything = True
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX: self._inbox = True
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE: self._archive = True
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LOCAL: self._local = True
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NOT_LOCAL: self._not_local = True
            
            for number_test_predicate_type in [
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_NOTES,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_FRAMES,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION,
                ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FRAMERATE
            ]:
                
                if predicate_type == number_test_predicate_type:
                    
                    if number_test_predicate_type not in self._common_info:
                        
                        self._common_info[ number_test_predicate_type ] = []
                        
                    
                    number_test = value
                    
                    self._common_info[ number_test_predicate_type ].append( number_test )
                    
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
                
                ( operator, rule_type, rule, description ) = value
                
                if 'known_url_rules' not in self._common_info:
                    
                    self._common_info[ 'known_url_rules' ] = []
                    
                
                self._common_info[ 'known_url_rules' ].append( ( operator, rule_type, rule ) )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_AUDIO:
                
                has_audio = value
                
                self._common_info[ 'has_audio' ] = has_audio
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY:
                
                has_transparency = value
                
                self._common_info[ 'has_transparency' ] = has_transparency
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF:
                
                has_exif = value
                
                self._common_info[ 'has_exif' ] = has_exif
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA:
                
                has_human_readable_embedded_metadata = value
                
                self._common_info[ 'has_human_readable_embedded_metadata' ] = has_human_readable_embedded_metadata
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE:
                
                has_icc_profile = value
                
                self._common_info[ 'has_icc_profile' ] = has_icc_profile
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE:
                
                has_forced_filetype = value
                
                self._common_info[ 'has_forced_filetype' ] = has_forced_filetype
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH:
                
                ( hashes, hash_type ) = value
                
                if 'hashes' not in self._common_info:
                    
                    self._common_info[ 'hashes' ] = []
                    
                
                self._common_info[ 'hashes' ].append( ( hashes, hash_type, predicate.IsInclusive() ) )
                
            
            if predicate_type in ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME ):
                
                ( operator, age_type, age_value ) = value
                
                if age_type == 'delta':
                    
                    ( years, months, days, hours ) = age_value
                    
                    dt = HydrusTime.CalendarDeltaToDateTime( years, months, days, hours )
                    
                    time_pivot_ms = HydrusTime.DateTimeToTimestampMS( dt )
                    
                    # this is backwards (less than means min timestamp) because we are talking about age, not timestamp
                    
                    # the before/since semantic logic is:
                    # '<' 7 days age means 'since that date'
                    # '>' 7 days ago means 'before that date'
                    
                    if operator == '<':
                        
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '>' ] = time_pivot_ms
                        
                    elif operator == '>':
                        
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '<' ] = time_pivot_ms
                        
                    elif operator == HC.UNICODE_APPROX_EQUAL:
                        
                        rough_timedelta_gap = HydrusTime.CalendarDeltaToRoughDateTimeTimeDelta( years, months, days, hours ) * 0.15
                        
                        earliest_dt = dt - rough_timedelta_gap
                        latest_dt = dt + rough_timedelta_gap
                        
                        earliest_time_pivot_ms = HydrusTime.DateTimeToTimestampMS( earliest_dt )
                        latest_time_pivot_ms = HydrusTime.DateTimeToTimestampMS( latest_dt )
                        
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '>' ] = earliest_time_pivot_ms
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '<' ] = latest_time_pivot_ms
                        
                    
                elif age_type == 'date':
                    
                    ( year, month, day, hour, minute ) = age_value
                    
                    dt = HydrusTime.GetDateTime( year, month, day, hour, minute )
                    
                    time_pivot_ms = HydrusTime.DateTimeToTimestampMS( dt )
                    
                    dt_day_of_start = HydrusTime.GetDateTime( year, month, day, 0, 0 )
                    
                    day_of_start_timestamp_ms = HydrusTime.DateTimeToTimestampMS( dt_day_of_start )
                    day_of_end_timestamp_ms = HydrusTime.DateTimeToTimestampMS( ClientTime.CalendarDelta( dt_day_of_start, day_delta = 1 ) )
                    
                    # the before/since semantic logic is:
                    # '<' 2022-05-05 means 'before that date'
                    # '>' 2022-05-05 means 'since that date'
                    
                    if operator == '<':
                        
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '<' ] = time_pivot_ms
                        
                    elif operator == '>':
                        
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '>' ] = time_pivot_ms
                        
                    elif operator == '=':
                        
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '>' ] = day_of_start_timestamp_ms
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '<' ] = day_of_end_timestamp_ms
                        
                    elif operator == HC.UNICODE_APPROX_EQUAL:
                        
                        previous_month_timestamp_ms = HydrusTime.DateTimeToTimestampMS( ClientTime.CalendarDelta( dt, month_delta = -1 ) )
                        next_month_timestamp_ms = HydrusTime.DateTimeToTimestampMS( ClientTime.CalendarDelta( dt, month_delta = 1 ) )
                        
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '>' ] = previous_month_timestamp_ms
                        self._system_pred_types_to_timestamp_ranges_ms[ predicate_type ][ '<' ] = next_month_timestamp_ms
                        
                    
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME:
                
                summary_mimes = value
                
                if isinstance( summary_mimes, int ):
                    
                    summary_mimes = ( summary_mimes, )
                    
                
                specific_mimes = ClientSearchPredicate.ConvertSummaryFiletypesToSpecific( summary_mimes )
                
                # this is a bit unusual, but at the DB end things are easier if we keep things inclusive so this is KISS
                if not predicate.IsInclusive():
                    
                    specific_mimes = set( HC.SEARCHABLE_MIMES ).difference( specific_mimes )
                    
                
                if self._allowed_filetypes is None:
                    
                    self._allowed_filetypes = set( HC.SEARCHABLE_MIMES )
                    
                
                self._allowed_filetypes.intersection_update( specific_mimes )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS:
                
                self._num_tags_predicates.append( predicate )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING_ADVANCED:
                
                self._advanced_ratings_predicates.append( predicate )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING:
                
                ( operator, value, service_key ) = value
                
                self._ratings_predicates.append( ( operator, value, service_key ) )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO:
                
                ( operator, ratio_width, ratio_height ) = value
                
                if operator == '=': self._common_info[ 'ratio' ] = ( ratio_width, ratio_height )
                elif operator == 'wider than':
                    
                    self._common_info[ 'min_ratio' ] = ( ratio_width, ratio_height )
                    
                elif operator == 'taller than':
                    
                    self._common_info[ 'max_ratio' ] = ( ratio_width, ratio_height )
                    
                elif operator == HC.UNICODE_NOT_EQUAL:
                    
                    self._common_info[ 'not_ratio' ] = ( ratio_width, ratio_height )
                    
                elif operator == HC.UNICODE_APPROX_EQUAL:
                    
                    self._common_info[ 'min_ratio' ] = ( ratio_width * 0.85, ratio_height )
                    self._common_info[ 'max_ratio' ] = ( ratio_width * 1.15, ratio_height )
                    
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE:
                
                ( operator, size, unit ) = value
                
                size = size * unit
                
                if operator == '<': self._common_info[ 'max_size' ] = size
                elif operator == '>': self._common_info[ 'min_size' ] = size
                elif operator == '=': self._common_info[ 'size' ] = size
                elif operator == HC.UNICODE_NOT_EQUAL: self._common_info[ 'not_size' ] = size
                elif operator == HC.UNICODE_APPROX_EQUAL:
                    
                    self._common_info[ 'min_size' ] = int( size * 0.85 )
                    self._common_info[ 'max_size' ] = int( size * 1.15 )
                    
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_ADVANCED:
                
                self._advanced_tag_predicates.append( predicate )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
                
                ( namespace, operator, num ) = value
                
                if operator == '<': self._common_info[ 'max_tag_as_number' ] = ( namespace, num )
                elif operator == '>': self._common_info[ 'min_tag_as_number' ] = ( namespace, num )
                elif operator == HC.UNICODE_APPROX_EQUAL:
                    
                    self._common_info[ 'min_tag_as_number' ] = ( namespace, int( num * 0.85 ) )
                    self._common_info[ 'max_tag_as_number' ] = ( namespace, int( num * 1.15 ) )
                    
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_PIXELS:
                
                ( operator, num_pixels, unit ) = value
                
                num_pixels = num_pixels * unit
                
                if operator == '<': self._common_info[ 'max_num_pixels' ] = num_pixels
                elif operator == '>': self._common_info[ 'min_num_pixels' ] = num_pixels
                elif operator == '=': self._common_info[ 'num_pixels' ] = num_pixels
                elif operator == HC.UNICODE_NOT_EQUAL: self._common_info[ 'not_num_pixels' ] = num_pixels
                elif operator == HC.UNICODE_APPROX_EQUAL:
                    
                    self._common_info[ 'min_num_pixels' ] = int( num_pixels * 0.85 )
                    self._common_info[ 'max_num_pixels' ] = int( num_pixels * 1.15 )
                    
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME:
                
                ( operator, name ) = value
                
                if operator:
                    
                    label = 'has_note_names'
                    
                else:
                    
                    label = 'not_has_note_names'
                    
                
                if label not in self._common_info:
                    
                    self._common_info[ label ] = set()
                    
                
                self._common_info[ label ].add( name )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT:
                
                limit = value
                
                if self._limit is None:
                    
                    self._limit = limit
                    
                else:
                    
                    self._limit = min( limit, self._limit )
                    
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
                
                ( operator, status, service_key ) = value
                
                if operator:
                    
                    self._required_file_service_statuses[ service_key ].add( status )
                    
                else:
                    
                    self._excluded_file_service_statuses[ service_key ].add( status )
                    
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES:
                
                ( hashes, max_hamming ) = value
                
                self._similar_to_files = ( hashes, max_hamming )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA:
                
                ( pixel_hashes, perceptual_hashes, max_hamming ) = value
                
                self._similar_to_data = ( pixel_hashes, perceptual_hashes, max_hamming )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT:
                
                ( operator, num_relationships, dupe_type ) = value
                
                self._duplicate_count_predicates.append( ( operator, num_relationships, dupe_type ) )
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING:
                
                king = value
                
                self._king_filter = king
                
            
            if predicate_type == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
                
                ( view_type, viewing_locations, operator, viewing_value ) = value
                
                stupid_lookup_dict = {
                    'media' : CC.CANVAS_MEDIA_VIEWER,
                    'preview' : CC.CANVAS_PREVIEW,
                    'client api' : CC.CANVAS_CLIENT_API
                }
                
                desired_canvas_types = [ stupid_lookup_dict[ viewing_location ] for viewing_location in viewing_locations ]
                
                self._file_viewing_stats_predicates.append( ( view_type, desired_canvas_types, operator, viewing_value ) )
                
            
        
    
    def GetAdvancedTagPredicates( self ):
        
        return self._advanced_tag_predicates
        
    
    def GetAdvancedRatingsPredicates( self ):
        
        return self._advanced_ratings_predicates
        
    
    def GetAllowedFiletypes( self ):
        
        return self._allowed_filetypes
        
    
    def GetDuplicateRelationshipCountPredicates( self ):
        
        return self._duplicate_count_predicates
        
    
    def GetFileServiceStatuses( self ):
        
        return ( self._required_file_service_statuses, self._excluded_file_service_statuses )
        
    
    def GetFileViewingStatsPredicates( self ):
        
        return self._file_viewing_stats_predicates
        
    
    def GetKingFilter( self ):
        
        return self._king_filter
        
    
    def GetLimit( self, apply_implicit_limit = True ):
        
        if self._limit is None and apply_implicit_limit:
            
            forced_search_limit = CG.client_controller.new_options.GetNoneableInteger( 'forced_search_limit' )
            
            return forced_search_limit
            
        
        return self._limit
        
    
    def GetNumTagsNumberTests( self ) -> dict[ str, list[ ClientNumberTest.NumberTest ] ]:
        
        namespaces_to_tests = collections.defaultdict( list )
        
        for predicate in self._num_tags_predicates:
            
            ( namespace, operator, value ) = predicate.GetValue()
            
            test = ClientNumberTest.NumberTest.STATICCreateFromCharacters( operator, value )
            
            namespaces_to_tests[ namespace ].append( test )
            
        
        return namespaces_to_tests
        
    
    def GetRatingsPredicates( self ):
        
        return self._ratings_predicates
        
    
    def GetSimilarToData( self ):
        
        return self._similar_to_data
        
    
    def GetSimilarToFiles( self ):
        
        return self._similar_to_files
        
    
    def GetSimpleInfo( self ):
        
        return self._common_info
        
    
    def GetTimestampRangesMS( self ):
        
        return self._system_pred_types_to_timestamp_ranges_ms
        
    
    def HasAllowedFiletypes( self ):
        
        return self._allowed_filetypes is not None
        
    
    def HasSimilarToData( self ):
        
        return self._similar_to_data is not None
        
    
    def HasSimilarToFiles( self ):
        
        return self._similar_to_files is not None
        
    
    def HasSystemEverything( self ):
        
        return self._has_system_everything
        
    
    def HasSystemLimit( self ):
        
        return self._limit is not None
        
    
    def MustBeArchive( self ): return self._archive
    
    def MustBeInbox( self ): return self._inbox
    
    def MustBeLocal( self ): return self._local
    
    def MustNotBeLocal( self ): return self._not_local
    

class FileSearchContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT
    SERIALISABLE_NAME = 'File Search Context'
    SERIALISABLE_VERSION = 5
    
    def __init__( self, location_context = None, tag_context = None, search_type = SEARCH_TYPE_AND, predicates: list[ ClientSearchPredicate.Predicate ] | None = None ):
        
        if location_context is None:
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
            
        
        if tag_context is None:
            
            tag_context = ClientSearchTagContext.TagContext()
            
        
        if predicates is None:
            
            predicates = []
            
        
        self._location_context = location_context
        self._tag_context = tag_context
        
        self._search_type = search_type
        
        self._predicates = predicates
        
        self._search_complete = False
        
        self._InitialiseTemporaryVariables()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_predicates = [ predicate.GetSerialisableTuple() for predicate in self._predicates ]
        serialisable_location_context = self._location_context.GetSerialisableTuple()
        
        return ( serialisable_location_context, self._tag_context.GetSerialisableTuple(), self._search_type, serialisable_predicates, self._search_complete )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_location_context, serialisable_tag_context, self._search_type, serialisable_predicates, self._search_complete ) = serialisable_info
        
        self._location_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_location_context )
        self._tag_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_context )
        
        self._predicates = [ HydrusSerialisable.CreateFromSerialisableTuple( pred_tuple ) for pred_tuple in serialisable_predicates ]
        
        self._InitialiseTemporaryVariables()
        
    
    def _InitialiseTemporaryVariables( self ):
        
        system_predicates = [ predicate for predicate in self._predicates if predicate.GetType() in ClientSearchPredicate.SYSTEM_PREDICATE_TYPES ]
        
        self._system_predicates = FileSystemPredicates( system_predicates )
        
        tag_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_TAG ]
        
        self._tags_to_include = []
        self._tags_to_exclude = []
        
        for predicate in tag_predicates:
            
            tag = predicate.GetValue()
            
            if predicate.GetInclusive(): self._tags_to_include.append( tag )
            else: self._tags_to_exclude.append( tag )
            
        
        namespace_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE ]
        
        self._namespaces_to_include = []
        self._namespaces_to_exclude = []
        
        for predicate in namespace_predicates:
            
            namespace = predicate.GetValue()
            
            if predicate.GetInclusive(): self._namespaces_to_include.append( namespace )
            else: self._namespaces_to_exclude.append( namespace )
            
        
        wildcard_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_WILDCARD ]
        
        self._wildcards_to_include = []
        self._wildcards_to_exclude = []
        
        for predicate in wildcard_predicates:
            
            # this is an important convert. preds store nice looking text, but convert for the actual search
            wildcard = ClientSearchTagContext.ConvertTagToSearchable( predicate.GetValue() )
            
            if predicate.GetInclusive(): self._wildcards_to_include.append( wildcard )
            else: self._wildcards_to_exclude.append( wildcard )
            
        
        self._or_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER ]
        
    
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
            
        
        if version == 3:
            
            ( file_service_key_hex, tag_service_key_hex, search_type, include_current_tags, include_pending_tags, serialisable_predicates, search_complete ) = old_serialisable_info
            
            tag_service_key = bytes.fromhex( tag_service_key_hex )
            
            tag_context = ClientSearchTagContext.TagContext( service_key = tag_service_key, include_current_tags = include_current_tags, include_pending_tags = include_pending_tags )
            
            serialisable_tag_context = tag_context.GetSerialisableTuple()
            
            new_serialisable_info = ( file_service_key_hex, serialisable_tag_context, search_type, serialisable_predicates, search_complete )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( file_service_key_hex, serialisable_tag_context, search_type, serialisable_predicates, search_complete ) = old_serialisable_info
            
            file_service_key = bytes.fromhex( file_service_key_hex )
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( file_service_key )
            
            serialisable_location_context = location_context.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_location_context, serialisable_tag_context, search_type, serialisable_predicates, search_complete )
            
            return ( 5, new_serialisable_info )
            
        
    
    def FixMissingServices( self, filter_method ):
        
        self._location_context.FixMissingServices( filter_method )
        self._tag_context.FixMissingServices( filter_method )
        
    
    def GetLocationContext( self ) -> ClientLocation.LocationContext:
        
        return self._location_context
        
    
    def GetNamespacesToExclude( self ): return self._namespaces_to_exclude
    
    def GetNamespacesToInclude( self ): return self._namespaces_to_include
    
    def GetORPredicates( self ): return self._or_predicates
    
    def GetPredicates( self ) -> list[ ClientSearchPredicate.Predicate ]:
        
        return self._predicates
        
    
    def GetSummary( self ):
        
        if len( self._predicates ) == 0:
            
            return 'allows all files'
            
        
        pred_strings = sorted( [ pred.ToString() for pred in self._predicates ] )
        
        if len( pred_strings ) > 3:
            
            return f'{HydrusNumbers.ToHumanInt( len( pred_strings ) )} predicates'
            
        else:
            
            return ', '.join( pred_strings )
            
        
    
    def GetSystemPredicates( self ) -> FileSystemPredicates:
        
        return self._system_predicates
        
    
    def GetTagContext( self ) -> ClientSearchTagContext.TagContext:
        
        return self._tag_context
        
    
    def GetTagsToExclude( self ): return self._tags_to_exclude
    def GetTagsToInclude( self ): return self._tags_to_include
    def GetWildcardsToExclude( self ): return self._wildcards_to_exclude
    def GetWildcardsToInclude( self ): return self._wildcards_to_include
    
    def HasNoPredicates( self ):
        
        return len( self._predicates ) == 0
        
    
    def IsComplete( self ):
        
        return self._search_complete
        
    
    def IsJustSystemEverything( self ):
        
        return len( self._predicates ) == 1 and self._system_predicates.HasSystemEverything()
        
    
    def SetComplete( self ):
        
        self._search_complete = True
        
    
    def SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._location_context = location_context
        
    
    def SetIncludeCurrentTags( self, value ):
        
        self._tag_context.include_current_tags = value
        
    
    def SetIncludePendingTags( self, value ):
        
        self._tag_context.include_pending_tags = value
        
    
    def SetPredicates( self, predicates ):
        
        self._predicates = predicates
        
        self._InitialiseTemporaryVariables()
        
    
    def SetTagContext( self, tag_context: ClientSearchTagContext.TagContext ):
        
        self._tag_context = tag_context
        
    
    def SetTagServiceKey( self, tag_service_key ):
        
        self._tag_context.service_key = tag_service_key
        self._tag_context.display_service_key = tag_service_key
        
    
    def TestMediaResult( self, media_result: ClientMediaResult.MediaResult ):
        
        # note that TestMediaResult may well get a file and tag context, in which case I guess the predicate will get those here
        
        return False not in ( predicate.TestMediaResult( media_result ) for predicate in self._predicates )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT ] = FileSearchContext
