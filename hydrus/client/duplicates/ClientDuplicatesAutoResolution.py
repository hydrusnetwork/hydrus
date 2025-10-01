import collections
import collections.abc
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientDuplicatesAutoResolutionComparators
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.files.images import ClientVisualData
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientMetadataConditional 
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchFileSearchContext

# in the database I guess we'll assign these in a new table to all outstanding pairs that match a search
DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH = 0
DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED = 1
DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST = 2
DUPLICATE_STATUS_ACTIONED = 3
DUPLICATE_STATUS_NOT_SEARCHED = 4 # assign this to new pairs that are added, by default
DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION = 5
DUPLICATE_STATUS_USER_DECLINED = 6

duplicate_status_str_lookup = {
    DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH : 'Did not match search',
    DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 'Matches search, not yet tested',
    DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 'Matches search, failed test',
    DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION : 'Matches search, passed test, ready to action',
    DUPLICATE_STATUS_ACTIONED : 'Actioned',
    DUPLICATE_STATUS_NOT_SEARCHED : 'Not searched',
    DUPLICATE_STATUS_USER_DECLINED : 'User declined'
}

DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_PAUSED = 0
DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION = 1
DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC = 2

duplicates_auto_resolution_rule_operation_mode_desc_lookup = {
    DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_PAUSED : 'paused',
    DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION : 'semi-automatic: will search and test, but no action without human approval',
    DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC : 'fully automatic: will search and test and action'
}

duplicates_auto_resolution_rule_operation_mode_str_lookup = {
    DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_PAUSED : 'paused',
    DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION : 'semi-automatic',
    DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC : 'fully automatic'
}

NEW_RULE_SESSION_ID = -1

def ActionAutoResolutionReviewPairs( rule: "DuplicatesAutoResolutionRule", decisions, status_hook = None ):
    
    approve_pairs = [ ( decision.media_result_a, decision.media_result_b ) for decision in decisions if decision.approved ]
    deny_pairs = [ ( decision.media_result_a, decision.media_result_b ) for decision in decisions if not decision.approved ]
    
    for ( num_done, num_to_do, chunk ) in HydrusLists.SplitListIntoChunksRich( approve_pairs, 4 ):
        
        message = f'approving: {HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )}'
        
        if status_hook is not None:
            
            status_hook( message )
            
        
        # this is safe to run on a bunch of related pairs like AB, AC, DB--the db figures that out
        CG.client_controller.WriteSynchronous( 'duplicates_auto_resolution_approve_pending_pairs', rule, chunk )
        
    
    for ( num_done, num_to_do, chunk ) in HydrusLists.SplitListIntoChunksRich( deny_pairs, 4 ):
        
        message = f'denying: {HydrusNumbers.ValueRangeToPrettyString( num_done, num_to_do )}'
        
        if status_hook is not None:
            
            status_hook( message )
            
        
        # this is safe to run on a bunch of related pairs like AB, AC, DB--the db figures that out
        CG.client_controller.WriteSynchronous( 'duplicates_auto_resolution_deny_pending_pairs', rule, chunk )
        
    

class DuplicatesAutoResolutionRule( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Rule'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name ):
        """
        This guy holds everything to make a single auto-resolution job work. It knows the search it wants to do, and, when given pairs from that search, will confirm whether one file passes its auto-resolution threshold and should be auto-considered better.
        """
        
        super().__init__( name )
        
        # by doing this we use more than we'd like, but it solves an issue in the dialog compared to having all uninitialised as -1
        global NEW_RULE_SESSION_ID
        
        # the id here will be for the database to match up rules to cached pair statuses. slightly wewmode, but we'll see
        self._id = NEW_RULE_SESSION_ID
        
        NEW_RULE_SESSION_ID -= 1
        
        self._operation_mode = DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION
        
        self._max_pending_pairs = 512
        
        self._potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        self._pair_selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        self._action = HC.DUPLICATE_BETTER
        
        self._delete_a = False
        self._delete_b = False
        
        self._custom_duplicate_content_merge_options: typing.Optional[ ClientDuplicates.DuplicateContentMergeOptions ] = None
        
        self._counts_lock = threading.Lock()
        self._counts_cache = collections.Counter()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, DuplicatesAutoResolutionRule ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        # before we are initialised (i.e. in the dialog list), let's return something unique
        return self._id.__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_potential_duplicates_search_context = self._potential_duplicates_search_context.GetSerialisableTuple()
        serialisable_pair_selector = self._pair_selector.GetSerialisableTuple()
        serialisable_custom_duplicate_content_merge_options = None if self._custom_duplicate_content_merge_options is None else self._custom_duplicate_content_merge_options.GetSerialisableTuple()
        
        return (
            self._id,
            self._operation_mode,
            self._max_pending_pairs,
            serialisable_potential_duplicates_search_context,
            serialisable_pair_selector,
            self._action,
            self._delete_a,
            self._delete_b,
            serialisable_custom_duplicate_content_merge_options
        )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        (
            self._id,
            self._operation_mode,
            self._max_pending_pairs,
            serialisable_potential_duplicates_search_context,
            serialisable_pair_selector,
            self._action,
            self._delete_a,
            self._delete_b,
            serialisable_custom_duplicate_content_merge_options
        ) = serialisable_info
        
        self._potential_duplicates_search_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_potential_duplicates_search_context )
        self._pair_selector = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_pair_selector )
        self._custom_duplicate_content_merge_options = None if serialisable_custom_duplicate_content_merge_options is None else HydrusSerialisable.CreateFromSerialisableTuple( serialisable_custom_duplicate_content_merge_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            (
                id,
                operation_mode,
                serialisable_potential_duplicates_search_context,
                serialisable_pair_selector,
                action,
                delete_a,
                delete_b,
                serialisable_custom_duplicate_content_merge_options
            ) = old_serialisable_info
            
            max_pending_pairs = 512
            
            new_serialisable_info = (
                id,
                operation_mode,
                max_pending_pairs,
                serialisable_potential_duplicates_search_context,
                serialisable_pair_selector,
                action,
                delete_a,
                delete_b,
                serialisable_custom_duplicate_content_merge_options
            )
            
            return ( 2, new_serialisable_info )
            
        
    
    def CanWorkHard( self ):
        
        return self._operation_mode != DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_PAUSED and ( self.HasResolutionWorkToDo() or self.HasSearchWorkToDo() )
        
    
    def GetAction( self ) -> int:
        
        return self._action
        
    
    def GetActionSummary( self ) -> str:
        
        s = HC.duplicate_type_auto_resolution_action_description_lookup[ self._action ]
        
        if self._delete_a:
            
            s += ', delete A'
            
        
        if self._delete_b:
            
            s += ', delete B'
            
        
        if self._custom_duplicate_content_merge_options is None:
            
            s += ', default merge options'
            
        else:
            
            s += ', custom merge options'
            
        
        return s
        
    
    def GetActionSummaryOnMatchingPair( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult, do_either_way_test = True ) -> str:
        
        components = []
        
        if do_either_way_test:
            
            if self._pair_selector.MatchingPairMatchesBothWaysAround( media_result_a, media_result_b ):
                
                components.append( 'either way around' )
                
            else:
                
                components.append( 'this way around' )
                
            
        
        #
        
        action_s = HC.duplicate_type_auto_resolution_action_description_lookup[ self._action ]
        
        components.append( action_s )
        
        #
        
        if self._custom_duplicate_content_merge_options is None:
            
            duplicate_content_merge_options = CG.client_controller.new_options.GetDuplicateContentMergeOptions( self._action )
            
        else:
            
            duplicate_content_merge_options = self._custom_duplicate_content_merge_options
            
        
        try:
            
            components.append( duplicate_content_merge_options.GetMergeSummaryOnPair( media_result_a, media_result_b, self._delete_a, self._delete_b, in_auto_resolution = True ) )
            
        except Exception as e:
            
            HydrusData.ShowException( e, do_wait = False )
            
            components.append( 'Could not summarise the duplicate merge! Please tell hydrus dev.' )
            
        
        return '\n'.join( components )
        
    
    def GetCountsCacheDuplicate( self ):
        
        return collections.Counter( self._counts_cache )
        
    
    def GetDeleteInfo( self ) -> tuple[ bool, bool ]:
        
        return ( self._delete_a, self._delete_b )
        
    
    def GetDuplicateActionResult( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult ):
        
        action = self._action
        delete_a = self._delete_a
        delete_b = self._delete_b
        
        if self._custom_duplicate_content_merge_options is None:
            
            duplicate_content_merge_options = CG.client_controller.new_options.GetDuplicateContentMergeOptions( action )
            
        else:
            
            duplicate_content_merge_options = self._custom_duplicate_content_merge_options
            
        
        hash_a = media_result_a.GetHash()
        hash_b = media_result_b.GetHash()
        
        content_update_packages = duplicate_content_merge_options.ProcessPairIntoContentUpdatePackages( media_result_a, media_result_b, delete_a = delete_a, delete_b = delete_b, file_deletion_reason = f'duplicates auto-resolution ({self._name})', in_auto_resolution = True )
        
        # TODO: Make this an object bro
        return ( action, hash_a, hash_b, content_update_packages )
        
    
    def GetDuplicateContentMergeOptions( self ) -> typing.Optional[ ClientDuplicates.DuplicateContentMergeOptions ]:
        
        return self._custom_duplicate_content_merge_options
        
    
    def GetId( self ) -> int:
        
        return self._id
        
    
    def GetMaxPendingPairs( self ) -> typing.Optional[ int ]:
        
        return self._max_pending_pairs
        
    
    def GetOperationMode( self ) -> int:
        
        return self._operation_mode
        
    
    def GetPairSelector( self ) -> ClientDuplicatesAutoResolutionComparators.PairSelector:
        
        return self._pair_selector
        
    
    def GetPairSelectorSummary( self ) -> str:
        
        return self._pair_selector.GetSummary()
        
    
    def GetPotentialDuplicatesSearchContext( self ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext:
        
        return self._potential_duplicates_search_context
        
    
    def GetRuleSummary( self ) -> str:
        
        return self._potential_duplicates_search_context.GetSummary()
        
    
    def GetSearchSummary( self ) -> str:
        
        with self._counts_lock:
            
            if sum( self._counts_cache.values() ) == 0:
                
                return 'no data'
                
            
            not_searched = self._counts_cache[ DUPLICATE_STATUS_NOT_SEARCHED ]
            not_match = self._counts_cache[ DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH ]
            not_tested = self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED ]
            failed_test = self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST ]
            ready_to_action = self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION ]
            actioned = self._counts_cache[ DUPLICATE_STATUS_ACTIONED ]
            declined = self._counts_cache[ DUPLICATE_STATUS_USER_DECLINED ]
            
        
        result = ''
        
        if not_searched > 0:
            
            result += f'{HydrusNumbers.ToHumanInt( not_searched )} to search, '
            
        
        if not_tested > 0:
            
            result += f'{HydrusNumbers.ToHumanInt( not_tested )} still to test, '
            
        
        if ready_to_action > 0:
            
            result += f'{HydrusNumbers.ToHumanInt( ready_to_action )} ready to resolve, '
            
        
        if not_searched + not_tested + ready_to_action == 0:
            
            result += 'Done! '
            
        
        result += f'{HydrusNumbers.ToHumanInt( actioned )} pairs resolved'
        
        if failed_test > 0:
            
            result += f' ({HydrusNumbers.ToHumanInt( failed_test )} failed the test)'
            
        
        if declined > 0:
            
            result += f' ({HydrusNumbers.ToHumanInt( declined )} declined by user)'
            
        
        if not_match > 0:
            
            result += f' ({HydrusNumbers.ToHumanInt( not_match )} did not match the search)'
            
        
        return result
        
    
    def HasResolutionWorkToDo( self ):
        
        with self._counts_lock:
            
            if self._operation_mode == DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION:
                
                if self._max_pending_pairs is not None and self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION ] >= self._max_pending_pairs:
                    
                    return False
                    
                
            
            return self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED ] > 0
            
        
    
    def HasSearchWorkToDo( self ):
        
        with self._counts_lock:
            
            return self._counts_cache[ DUPLICATE_STATUS_NOT_SEARCHED ] > 0
            
        
    
    def HasUserWorkToDo( self ):
        
        with self._counts_lock:
            
            return self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION ] > 0
            
        
    
    def IsPaused( self ):
        
        return self._operation_mode == DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_PAUSED
        
    
    def SetAction( self, action: int ):
        
        self._action = action
        
    
    def SetCount( self, status, count ):
        
        with self._counts_lock:
            
            self._counts_cache[ status ] = count
            
        
    
    def SetCountsCache( self, counts ):
        
        with self._counts_lock:
            
            self._counts_cache = counts
            
        
    
    def SetDeleteInfo( self, delete_a: bool, delete_b: bool ):
        
        self._delete_a = delete_a
        self._delete_b = delete_b
        
    
    def SetDuplicateContentMergeOptions( self, duplicate_content_merge_options: typing.Optional[ ClientDuplicates.DuplicateContentMergeOptions ] ):
        
        self._custom_duplicate_content_merge_options = duplicate_content_merge_options
        
    
    def SetId( self, value: int ):
        
        self._id = value
        
    
    def SetOperationMode( self, value: int ):
        
        self._operation_mode = value
        
    
    def SetMaxPendingPairs( self, value: typing.Optional[ int ] ):
        
        self._max_pending_pairs = value
        
    
    def SetPotentialDuplicatesSearchContext( self, value: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ):
        
        self._potential_duplicates_search_context = value
        
    
    def SetPairSelector( self, value: ClientDuplicatesAutoResolutionComparators.PairSelector ):
        
        self._pair_selector = value
        
    
    def TestPair( self, media_result_1: ClientMediaResult.MediaResult, media_result_2: ClientMediaResult.MediaResult ):
        
        result = self._pair_selector.GetMatchingAB( media_result_1, media_result_2 )
        
        if result is None:
            
            return None
            
        else:
            
            ( media_result_a, media_result_b ) = result
            
        
        return self.GetDuplicateActionResult( media_result_a, media_result_b )
        
    
    def UpdateCount( self, status: int, delta: int ):
        
        with self._counts_lock:
            
            self._counts_cache[ status ] += delta
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE ] = DuplicatesAutoResolutionRule

def GetDefaultRuleSuggestions() -> list[ DuplicatesAutoResolutionRule ]:
    
    one_file_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
    
    one_file_comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_B )
    
    file_search_context_mc = ClientSearchFileSearchContext.FileSearchContext(
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, value = False ),
        ]
    )
    
    metadata_conditional = ClientMetadataConditional.MetadataConditional()
    
    metadata_conditional.SetFileSearchContext( file_search_context_mc )
    
    one_file_comparator.SetMetadataConditional( metadata_conditional )
    
    hardcoded_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME )
    
    smart_exif_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOR(
        [
            one_file_comparator,
            hardcoded_comparator
        ]
    )
    
    #
    
    one_file_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
    
    one_file_comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_B )
    
    file_search_context_mc = ClientSearchFileSearchContext.FileSearchContext(
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, value = False ),
        ]
    )
    
    metadata_conditional = ClientMetadataConditional.MetadataConditional()
    
    metadata_conditional.SetFileSearchContext( file_search_context_mc )
    
    one_file_comparator.SetMetadataConditional( metadata_conditional )
    
    hardcoded_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_ICC_PROFILE_SAME )
    
    smart_icc_profile_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOR(
        [
            one_file_comparator,
            hardcoded_comparator
        ]
    )
    
    #
    
    suggested_rules = []
    
    # ############
    
    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
    
    predicates = [
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.IMAGE_JPEG, ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) )
    ]
    
    file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
        location_context = location_context,
        predicates = predicates
    )
    
    predicates = [
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.IMAGE_PNG, ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) )
    ]
    
    file_search_context_2 = ClientSearchFileSearchContext.FileSearchContext(
        location_context = location_context,
        predicates = predicates
    )
    
    potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
    
    potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
    potential_duplicates_search_context.SetFileSearchContext2( file_search_context_2 )
    potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
    potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED )
    potential_duplicates_search_context.SetMaxHammingDistance( 0 )
    
    duplicates_auto_resolution_rule = DuplicatesAutoResolutionRule( 'pixel-perfect jpegs vs pngs' )
    
    duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
    
    selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
    
    comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_A )
    
    file_search_context_mc = ClientSearchFileSearchContext.FileSearchContext(
        predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.IMAGE_JPEG, ) ) ]
    )
    
    metadata_conditional = ClientMetadataConditional.MetadataConditional()
    
    metadata_conditional.SetFileSearchContext( file_search_context_mc )
    
    comparator.SetMetadataConditional( metadata_conditional )
    
    selector.SetComparators( [ comparator ] )
    
    duplicates_auto_resolution_rule.SetPairSelector( selector )
    
    #
    
    duplicates_auto_resolution_rule.SetAction( HC.DUPLICATE_BETTER )
    duplicates_auto_resolution_rule.SetDeleteInfo( False, True )
    
    #
    
    suggested_rules.append( duplicates_auto_resolution_rule )
    
    # ############
    
    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
    
    predicates = [
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.IMAGE_JPEG, ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) )
    ]
    
    file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
        location_context = location_context,
        predicates = predicates
    )
    
    predicates = [
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.IMAGE_PNG, ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) )
    ]
    
    file_search_context_2 = ClientSearchFileSearchContext.FileSearchContext(
        location_context = location_context,
        predicates = predicates
    )
    
    potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
    
    potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
    potential_duplicates_search_context.SetFileSearchContext2( file_search_context_2 )
    potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
    potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED )
    potential_duplicates_search_context.SetMaxHammingDistance( 0 )
    
    duplicates_auto_resolution_rule = DuplicatesAutoResolutionRule( 'pixel-perfect jpegs vs pngs - except when png is smaller' )
    
    duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
    
    selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
    
    comparators = []
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
    
    comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_A )
    
    file_search_context_mc = ClientSearchFileSearchContext.FileSearchContext(
        predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.IMAGE_JPEG, ) ) ]
    )
    
    metadata_conditional = ClientMetadataConditional.MetadataConditional()
    
    metadata_conditional.SetFileSearchContext( file_search_context_mc )
    
    comparator.SetMetadataConditional( metadata_conditional )
    
    comparators.append( comparator )
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
    
    comparator.SetMultiplier( 1.00 )
    comparator.SetDelta( 0 )
    comparator.SetNumberTest( ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN ) )
    comparator.SetSystemPredicate( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE ) )
    
    comparators.append( comparator )
    
    selector.SetComparators( comparators )
    
    duplicates_auto_resolution_rule.SetPairSelector( selector )
    
    #
    
    duplicates_auto_resolution_rule.SetAction( HC.DUPLICATE_BETTER )
    duplicates_auto_resolution_rule.SetDeleteInfo( False, True )
    
    #
    
    suggested_rules.append( duplicates_auto_resolution_rule )
    
    # ############
    
    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
    
    predicates = [
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.GENERAL_IMAGE, ) ),
        ClientSearchPredicate.Predicate(
            predicate_type = ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER,
            value = [
                ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, value = True ),
                ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, value = True )
            ]
        ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) )
    ]
    
    file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
        location_context = location_context,
        predicates = predicates
    )
    
    predicates = [
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.GENERAL_IMAGE, ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, value = False ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, value = False ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) )
    ]
    
    file_search_context_2 = ClientSearchFileSearchContext.FileSearchContext(
        location_context = location_context,
        predicates = predicates
    )
    
    potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
    
    potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
    potential_duplicates_search_context.SetFileSearchContext2( file_search_context_2 )
    potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
    potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED )
    potential_duplicates_search_context.SetMaxHammingDistance( 0 )
    
    duplicates_auto_resolution_rule = DuplicatesAutoResolutionRule( 'pixel-perfect pairs - keep EXIF or ICC data' )
    
    duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
    
    selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
    
    comparators = []
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
    
    comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_B )
    
    file_search_context_mc = ClientSearchFileSearchContext.FileSearchContext(
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, value = False ),
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, value = False )
        ]
    )
    
    metadata_conditional = ClientMetadataConditional.MetadataConditional()
    
    metadata_conditional.SetFileSearchContext( file_search_context_mc )
    
    comparator.SetMetadataConditional( metadata_conditional )
    
    comparators.append( comparator )
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME )
    
    comparators.append( comparator )
    
    selector.SetComparators( comparators )
    
    duplicates_auto_resolution_rule.SetPairSelector( selector )
    
    #
    
    duplicates_auto_resolution_rule.SetAction( HC.DUPLICATE_BETTER )
    duplicates_auto_resolution_rule.SetDeleteInfo( False, True )
    
    #
    
    suggested_rules.append( duplicates_auto_resolution_rule )
    
    # ############
    
    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
    
    predicates = [
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.GENERAL_IMAGE, ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) )
    ]
    
    file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
        location_context = location_context,
        predicates = predicates
    )
    
    potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
    
    potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
    potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH )
    potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED )
    potential_duplicates_search_context.SetMaxHammingDistance( 0 )
    
    duplicates_auto_resolution_rule = DuplicatesAutoResolutionRule( 'pixel-perfect pairs' )
    
    duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
    
    selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
    
    comparators = []
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
    
    comparator.SetMultiplier( 1.00 )
    comparator.SetDelta( 0 )
    comparator.SetNumberTest( ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN ) )
    comparator.SetSystemPredicate( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE ) )
    
    comparators.append( comparator )
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME )
    
    comparators.append( comparator )
    
    comparators.append( smart_exif_comparator )
    
    comparators.append( smart_icc_profile_comparator )
    
    selector.SetComparators( comparators )
    
    duplicates_auto_resolution_rule.SetPairSelector( selector )
    
    #
    
    duplicates_auto_resolution_rule.SetAction( HC.DUPLICATE_BETTER )
    duplicates_auto_resolution_rule.SetDeleteInfo( False, True )
    
    #
    
    suggested_rules.append( duplicates_auto_resolution_rule )
    
    # ############
    
    location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
    
    predicates = [
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.GENERAL_IMAGE, ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, value = ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 128 ) ),
        ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, value = False )
    ]
    
    file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
        location_context = location_context,
        predicates = predicates
    )
    
    potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
    
    potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
    potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH )
    potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED )
    potential_duplicates_search_context.SetMaxHammingDistance( 0 )
    
    duplicates_auto_resolution_rule = DuplicatesAutoResolutionRule( 'visually similar pairs' )
    
    duplicates_auto_resolution_rule.SetMaxPendingPairs( 128 )
    duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
    
    selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
    
    comparators = []
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates( acceptable_confidence = ClientVisualData.VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY )
    
    comparators.append( comparator )
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
    
    comparator.SetMultiplier( 1.00 )
    comparator.SetDelta( 0 )
    comparator.SetNumberTest( ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO ) )
    comparator.SetSystemPredicate( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE ) )
    
    comparators.append( comparator )
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
    
    comparator.SetMultiplier( 1.00 )
    comparator.SetDelta( 0 )
    comparator.SetNumberTest( ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO ) )
    comparator.SetSystemPredicate( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH ) )
    
    comparators.append( comparator )
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
    
    comparator.SetMultiplier( 1.00 )
    comparator.SetDelta( 0 )
    comparator.SetNumberTest( ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN_OR_EQUAL_TO ) )
    comparator.SetSystemPredicate( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT ) )
    
    comparators.append( comparator )
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME )
    
    comparators.append( comparator )
    
    comparators.append( smart_exif_comparator )
    
    comparators.append( smart_icc_profile_comparator )
    
    selector.SetComparators( comparators )
    
    duplicates_auto_resolution_rule.SetPairSelector( selector )
    
    #
    
    duplicates_auto_resolution_rule.SetAction( HC.DUPLICATE_BETTER )
    duplicates_auto_resolution_rule.SetDeleteInfo( False, True )
    
    #
    
    suggested_rules.append( duplicates_auto_resolution_rule )
    
    #
    
    duplicates_auto_resolution_rule = duplicates_auto_resolution_rule.Duplicate()
    
    duplicates_auto_resolution_rule.SetName( 'visually similar pairs - only earlier imports' )
    
    comparators = list( duplicates_auto_resolution_rule.GetPairSelector().GetComparators() )
    
    comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
    
    comparator.SetMultiplier( 1.00 )
    comparator.SetDelta( 0 )
    comparator.SetNumberTest( ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN ) )
    comparator.SetSystemPredicate( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME ) )
    
    comparators.append( comparator )
    
    duplicates_auto_resolution_rule.GetPairSelector().SetComparators( comparators )
    
    suggested_rules.append( duplicates_auto_resolution_rule )
    
    # ############
    
    return suggested_rules
    

class DuplicatesAutoResolutionManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        """
        This guy is the mainloop daemon that runs all this gubbins.
        
        He has some careful locking as the dialog opens etc..
        """
        
        super().__init__( controller, 15 )
        
        self._currently_searching_rule = None
        self._currently_resolving_rule = None
        self._working_hard_rules = set()
        
        self._edit_work_lock = threading.Lock()
        
    
    def _AbleToWork( self ) -> bool:
        
        if len( self._working_hard_rules ) > 0:
            
            return True
            
        
        return self._AbleToWorkIdleNormal()
        
    
    def _AbleToWorkIdleNormal( self ) -> bool:
        
        if CG.client_controller.CurrentlyIdle():
            
            if not CG.client_controller.new_options.GetBoolean( 'duplicates_auto_resolution_during_idle' ):
                
                return False
                
            
            if not CG.client_controller.GoodTimeToStartBackgroundWork():
                
                return False
                
            
        else:
            
            if not CG.client_controller.new_options.GetBoolean( 'duplicates_auto_resolution_during_active' ):
                
                return False
                
            
        
        return True
        
    
    def _DoMainLoop( self ):
        
        while True:
            
            with self._lock:
                
                self._CheckShutdown()
                
                able_to_work = self._AbleToWork()
                
            
            still_work_to_do = False
            
            expected_work_period = self._GetWorkPeriod()
            
            if able_to_work:
                
                CG.client_controller.WaitUntilViewFree()
                
                with self._edit_work_lock:
                    
                    start_time = HydrusTime.GetNowFloat()
                    
                    try:
                        
                        still_work_to_do = self._WorkRules( expected_work_period )
                        
                    except HydrusExceptions.DataMissing as e:
                        
                        time.sleep( 5 )
                        
                        HydrusData.Print( 'While doing auto-resolution work, we discovered an id that should not exist. If you just deleted one yourself this second, let hydev know as this should not happen. You might need to run the "orphan rule" maintenance job off the cog icon on the duplicates resolution sidebar panel.' )
                        HydrusData.PrintException( e )
                        
                    except Exception as e:
                        
                        self._serious_error_encountered = True
                        
                        HydrusData.PrintException( e )
                        
                        message = 'There was an unexpected problem during duplicates auto-resolution work! This system will not run again this boot. A full traceback of this error should be written to the log.'
                        message += '\n' * 2
                        message += str( e )
                        
                        HydrusData.ShowText( message )
                        
                    
                    actual_work_period = HydrusTime.GetNowFloat() - start_time
                    
                
                CG.client_controller.pub( 'notify_duplicates_auto_resolution_work_complete' )
                
                with self._lock:
                    
                    wait_time = self._GetRestTime( expected_work_period, actual_work_period, still_work_to_do )
                    
                
            else:
                
                wait_time = 10
                
            
            FORCED_WAIT_PERIOD = 0.25
            
            if wait_time > FORCED_WAIT_PERIOD:
                
                # forced wait when lots going on
                time.sleep( FORCED_WAIT_PERIOD )
                
                wait_time -= FORCED_WAIT_PERIOD
                
            
            self._wake_event.wait( wait_time )
            
            self._wake_event.clear()
            
        
    
    def _FilterToWorkingHardRules( self, rules: collections.abc.Collection[ DuplicatesAutoResolutionRule ] ):
        
        if len( self._working_hard_rules ) > 0:
            
            for rule in rules:
                
                if rule in self._working_hard_rules and not rule.CanWorkHard():
                    
                    self._working_hard_rules.discard( rule )
                    
                
            
            if len( self._working_hard_rules ) > 0:
                
                rules = [ rule for rule in rules if rule in self._working_hard_rules ]
                
            
        
        return rules
        
    
    def _GetWaitPeriod( self, expected_work_period: float, actual_work_period: float, still_work_to_do: bool ):
        
        if len( self._working_hard_rules ) > 0:
            
            return 0.1
            
        
        if not still_work_to_do:
            
            return 600
            
        
        if CG.client_controller.CurrentlyIdle():
            
            rest_ratio = 1
            
        else:
            
            rest_ratio = 5
            
        
        reasonable_work_period = min( 20 * expected_work_period, actual_work_period )
        
        return reasonable_work_period * rest_ratio
        
    
    def _GetRestTime( self, expected_work_period: float, actual_work_period: float, still_work_to_do: bool ):
        
        if len( self._working_hard_rules ) > 0:
            
            return 0.1
            
        
        if not still_work_to_do:
            
            return 600
            
        
        if self._controller.CurrentlyIdle():
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'duplicates_auto_resolution_rest_percentage_idle' ) / 100
            
        else:
            
            rest_ratio = CG.client_controller.new_options.GetInteger( 'duplicates_auto_resolution_rest_percentage_active' ) / 100
            
        
        if actual_work_period > expected_work_period * 10:
            
            # if suddenly a job blats the user for ten seconds or _ten minutes_ during normal time, we are going to take a big break
            rest_ratio *= 30
            
        
        reasonable_work_period = min( 5 * expected_work_period, actual_work_period )
        
        return reasonable_work_period * rest_ratio
        
    
    def _GetWorkPeriod( self ):
        
        if len( self._working_hard_rules ) > 0:
            
            return 0.5
            
        
        if self._controller.CurrentlyIdle():
            
            return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'duplicates_auto_resolution_work_time_ms_idle' ) )
            
        else:
            
            return HydrusTime.SecondiseMSFloat( CG.client_controller.new_options.GetInteger( 'duplicates_auto_resolution_work_time_ms_active' ) )
            
        
    
    def _WorkRules( self, allowed_work_period: float ):
        
        time_to_stop = HydrusTime.GetNowFloat() + allowed_work_period
        
        still_work_to_do = False
        
        rules = CG.client_controller.Read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rules = sorted( rules, key = lambda r: r.GetName().casefold() )
        
        with self._lock:
            
            rules = self._FilterToWorkingHardRules( rules )
            
        
        for rule in rules:
            
            if rule.IsPaused():
                
                continue
                
            
            if rule.HasSearchWorkToDo():
                
                try:
                    
                    with self._lock:
                        
                        self._currently_searching_rule = rule
                        
                    
                    ( still_work_to_do_here, matching_pairs_produced_here ) = CG.client_controller.WriteSynchronous( 'duplicates_auto_resolution_do_search_work', rule )
                    
                    if still_work_to_do_here:
                        
                        still_work_to_do = True
                        
                    
                finally:
                    
                    with self._lock:
                        
                        self._currently_searching_rule = None
                        
                    
                
            
            if HydrusTime.TimeHasPassedFloat( time_to_stop ):
                
                return True
                
            
        
        for rule in rules:
            
            if rule.IsPaused():
                
                continue
                
            
            if rule.HasResolutionWorkToDo():
                
                try:
                    
                    with self._lock:
                        
                        self._currently_resolving_rule = rule
                        
                    
                    still_work_to_do_here = True
                    
                    previous_pair = None
                    
                    while rule.HasResolutionWorkToDo():
                        
                        media_result_pair = CG.client_controller.Read( 'duplicates_auto_resolution_resolution_pair', rule )
                        
                        if previous_pair is not None and media_result_pair == previous_pair:
                            
                            raise Exception( f'Rule {rule.GetName()} read the same resolution pair twice in a row! Please let hydev know.' )
                            
                        
                        if media_result_pair is None:
                            
                            # I believe this should never happen under no-miscount conditions as HasResolutionWorkToDo is now count-synced
                            still_work_to_do_here = False
                            
                            break
                            
                        else:
                            
                            previous_pair = media_result_pair
                            
                            ( media_result_1, media_result_2 ) = media_result_pair
                            
                            # this is the high CPU bit and needs to be out of the db
                            # we used to have a nice embedded db call that looped and could clear hundreds of null pairs in one transaction, but it relied on db-side testing
                            # maybe we could have two calls, for a known fast test somehow, but let's KISS from the other direction and simply regret the overhead
                            result = rule.TestPair( media_result_1, media_result_2 )
                            
                            if result is None:
                                
                                CG.client_controller.WriteSynchronous( 'duplicates_auto_resolution_commit_resolution_pair_failed', rule, media_result_pair )
                                
                            else:
                                
                                CG.client_controller.WriteSynchronous( 'duplicates_auto_resolution_commit_resolution_pair_passed', rule, result )
                                
                            
                        
                        if HydrusTime.TimeHasPassedFloat( time_to_stop ):
                            
                            break
                            
                        
                    
                    if still_work_to_do_here:
                        
                        still_work_to_do = True
                        
                    
                finally:
                    
                    with self._lock:
                        
                        self._currently_resolving_rule = None
                        
                    
                
            
            if HydrusTime.TimeHasPassedFloat( time_to_stop ):
                
                return True
                
            
        
        with self._lock:
            
            still_work_to_do = still_work_to_do or len( self._working_hard_rules ) > 0
            
        
        return still_work_to_do
        
    
    def GetEditWorkLock( self ):
        
        return self._edit_work_lock
        
    
    def GetName( self ) -> str:
        
        return 'duplicates auto-resolution'
        
    
    def GetRules( self ) -> list[ DuplicatesAutoResolutionRule ]:
        
        rules = CG.client_controller.Read( 'duplicates_auto_resolution_rules_with_counts' )
        
        return rules
        
    
    def GetRunningStatus( self, rule: DuplicatesAutoResolutionRule ) -> str:
        
        with self._lock:
            
            if rule.IsPaused():
                
                return 'paused'
                
            elif rule == self._currently_searching_rule:
                
                return 'searching'
                
            elif rule == self._currently_resolving_rule:
                
                return 'resolving'
                
            elif rule in self._working_hard_rules:
                
                return 'working hard'
                
            elif rule.HasSearchWorkToDo() or rule.HasResolutionWorkToDo():
                
                if self._AbleToWorkIdleNormal():
                    
                    return 'working'
                    
                else:
                    
                    return 'waiting'
                    
                
            elif rule.HasUserWorkToDo():
                
                return 'queued'
                
            else:
                
                return 'done'
                
            
        
    
    def GetWorkingHard( self ) -> collections.abc.Collection[ DuplicatesAutoResolutionRule ]:
        
        with self._lock:
            
            return set( self._working_hard_rules )
            
        
    
    def ResetRuleDeclined( self, rules: collections.abc.Collection[ DuplicatesAutoResolutionRule ] ):
        
        for rule in rules:
            
            CG.client_controller.WriteSynchronous( 'duplicates_auto_resolution_reset_rule_declined', rule )
            
        
        self.Wake()
        
    
    def ResetRuleSearchProgress( self, rules: collections.abc.Collection[ DuplicatesAutoResolutionRule ] ):
        
        for rule in rules:
            
            CG.client_controller.WriteSynchronous( 'duplicates_auto_resolution_reset_rule_search_progress', rule )
            
        
        self.Wake()
        
    
    def ResetRuleTestProgress( self, rules: collections.abc.Collection[ DuplicatesAutoResolutionRule ] ):
        
        for rule in rules:
            
            CG.client_controller.WriteSynchronous( 'duplicates_auto_resolution_reset_rule_test_progress', rule )
            
        
        self.Wake()
        
    
    def SetRules( self, rules: collections.abc.Collection[ DuplicatesAutoResolutionRule ] ):
        
        with self._lock:
            
            self._working_hard_rules = set()
            
        
        CG.client_controller.Write( 'duplicates_auto_resolution_set_rules', rules )
        
        self.Wake()
        
    
    def SetWorkingHard( self, rule: DuplicatesAutoResolutionRule, work_hard: bool ):
        
        with self._lock:
            
            if work_hard and rule not in self._working_hard_rules and rule.CanWorkHard():
                
                self._working_hard_rules.add( rule )
                
            elif not work_hard and rule in self._working_hard_rules:
                
                self._working_hard_rules.discard( rule )
                
            
        
        self.Wake()
        
    
    def WakeIfNotWorking( self ):
        
        # hacky little thing
        
        if not self._edit_work_lock.locked():
            
            self.Wake()
            
        
    
