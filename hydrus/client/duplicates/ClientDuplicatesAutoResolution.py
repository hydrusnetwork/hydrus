import collections
import random
import threading
import time
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientMetadataConditional 
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchFileSearchContext

# in the database I guess we'll assign these in a new table to all outstanding pairs that match a search
DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH = 0
DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED = 1
DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST = 2
DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST = 3 # presumably this will not be needed much since we'll delete the duplicate pair soon after, but we may as well be careful
DUPLICATE_STATUS_NOT_SEARCHED = 4 # assign this to new pairs that are added, by default

duplicate_status_str_lookup = {
    DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH : 'Did not match search',
    DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 'Matches search, not yet tested',
    DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 'Matches search, failed test',
    DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST : 'Matches search, passed test',
    DUPLICATE_STATUS_NOT_SEARCHED : 'Not searched'
}

class PairComparator( HydrusSerialisable.SerialisableBase ):
    
    def CanDetermineBetter( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def GetSummary( self ) -> str:
        
        raise NotImplementedError()
        
    
    def Test( self, media_result_better, media_result_worse ) -> bool:
        
        raise NotImplementedError()
        
    

LOOKING_AT_A = 0
LOOKING_AT_B = 1
LOOKING_AT_EITHER = 2

class PairComparatorOneFile( PairComparator ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_ONE_FILE
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Pair Comparator - One File'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        """
        This guy holds one test and is told to test either the better or worse candidate. Multiple of these stacked up make for 'the better file is a jpeg over one megabyte, the worse file is a jpeg under 100KB'.
        """
        
        super().__init__()
        
        # this guy tests the A or the B for a single property
        # user could set up multiple on either side of the equation
        # what are we testing?
            # A: mime is jpeg (& worse file is png)
            # B: has icc profile
            # EITHER: filesize < 200KB
        
        self._looking_at = LOOKING_AT_A
        
        self._metadata_conditional = ClientMetadataConditional.MetadataConditional()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_metadata_conditional = self._metadata_conditional.GetSerialisableTuple()
        
        return ( self._looking_at, serialisable_metadata_conditional )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._looking_at, serialisable_metadata_conditional ) = serialisable_info
        
        self._metadata_conditional = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_metadata_conditional )
        
    
    def CanDetermineBetter( self ) -> bool:
        
        return self._looking_at in ( LOOKING_AT_A, LOOKING_AT_B )
        
    
    def GetLookingAt( self ) -> int:
        
        return self._looking_at
        
    
    def GetMetadataConditional( self ) -> ClientMetadataConditional.MetadataConditional:
        
        return self._metadata_conditional
        
    
    def GetSummary( self ):
        
        if self._looking_at == LOOKING_AT_A:
            
            return f'A will match: {self._metadata_conditional.GetSummary()}'
            
        elif self._looking_at == LOOKING_AT_B:
            
            return f'B will match: {self._metadata_conditional.GetSummary()}'
            
        elif self._looking_at == LOOKING_AT_EITHER:
            
            return f'either will match: {self._metadata_conditional.GetSummary()}'
            
        else:
            
            return 'unknown comparator rule!'
            
        
    
    def SetLookingAt( self, looking_at: int ):
        
        self._looking_at = looking_at
        
    
    def SetMetadataConditional( self, metadata_conditional: ClientMetadataConditional.MetadataConditional ):
        
        self._metadata_conditional = metadata_conditional
        
    
    def Test( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult ) -> bool:
        
        if self._looking_at == LOOKING_AT_A:
            
            return self._metadata_conditional.Test( media_result_a )
            
        elif self._looking_at == LOOKING_AT_B:
            
            return self._metadata_conditional.Test( media_result_b )
            
        elif self._looking_at == LOOKING_AT_EITHER:
            
            return self._metadata_conditional.Test( media_result_a ) or self._metadata_conditional.Test( media_result_b )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_ONE_FILE ] = PairComparatorOneFile

class PairComparatorRelative( PairComparator ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Pair Comparator - Relative'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        """
        This guy compares the pair directly. It can say 'yes the better candidate is 4x bigger than the worse'. 
        """
        
        super().__init__()
        
        # this work does not need to be done yet!
        
        # THIS WILL NOT BE A METADATA CONDITIONAL
        # THIS WILL BE A NEW OBJECT ENTIRELY
        # IT WILL CONSULT TWO MEDIA RESULTS AND CREATE A DYNAMIC NUMBER TEST TO DO >, x4, approx-=, whatever
        # WE _MAY_ USE UN-FLESHED SYSTEM PREDS OR SIMILAR TO SPECIFY AND PERFORM OUR METADATA FETCH, SINCE THOSE GUYS WILL LEARN THAT TECH FOR MEDIA TESTS ANYWAY
        
        # property
            # width
            # filesize
            # age
            # etc..
        # operator
            # is more than 4x larger
            # is at least x absolute value larger?
        
    
    def CanDetermineBetter( self ) -> bool:
        
        return True
        
    
    # serialisable gubbins
    # get/set
    
    def GetSummary( self ):
        
        return 'A has 4x pixel count of B'
        
    
    def Test( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult ) -> bool:
        
        return False
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE ] = PairComparatorRelative

class PairSelector( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_SELECTOR
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Pair Selector'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        """
        This guy holds a bunch of comparators. It is given a pair of media and it tests all the rules both ways around. If the files pass all the rules, we have a match and thus a confirmed better file.
        
        A potential future expansion here is to attach scores to the rules and have a score threshold, but let's not get ahead of ourselves.
        """
        
        super().__init__()
        
        self._comparators: typing.List[ PairComparator ] = HydrusSerialisable.SerialisableList()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_comparators = HydrusSerialisable.SerialisableList( self._comparators ).GetSerialisableTuple()
        
        return serialisable_comparators
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        serialisable_comparators = serialisable_info
        
        self._comparators = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_comparators )
        
    
    def CanDetermineBetter( self ):
        
        # note this is correctly false if no comparators
        
        return True in ( comparator.CanDetermineBetter() for comparator in self._comparators )
        
    
    def GetComparators( self ):
        
        return self._comparators
        
    
    def GetMatchingAB( self, media_result_1: ClientMediaResult.MediaResult, media_result_2: ClientMediaResult.MediaResult, test_both_ways_around = True ) -> typing.Optional[ typing.Tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult ] ]:
        
        pair = [ media_result_1, media_result_2 ]
        
        if test_both_ways_around:
            
            # just in case both match
            random.shuffle( pair )
            
        
        ( media_result_1, media_result_2 ) = pair
        
        if len( self._comparators ) == 0:
            
            # no testing, just return whatever. let's hope this is an alternates thing
            return ( media_result_1, media_result_2 )
            
        
        if False not in ( comparator.Test( media_result_1, media_result_2 ) for comparator in self._comparators ):
            
            return ( media_result_1, media_result_2 )
            
        elif test_both_ways_around and False not in ( comparator.Test( media_result_2, media_result_1 ) for comparator in self._comparators ):
            
            return ( media_result_2, media_result_1 )
            
        else:
            
            return None
            
        
    
    def GetSummary( self ) -> str:
        
        comparator_strings = sorted( [ comparator.GetSummary() for comparator in self._comparators ] )
        
        return ', '.join( comparator_strings )
        
    
    def PairMatchesBothWaysAround( self, media_result_1: ClientMediaResult.MediaResult, media_result_2: ClientMediaResult.MediaResult ) -> bool:
        
        return self.GetMatchingAB( media_result_1, media_result_2, test_both_ways_around = False ) is not None and self.GetMatchingAB( media_result_2, media_result_1, test_both_ways_around = False ) is not None
        
    
    def SetComparators( self, comparators: typing.Collection[ PairComparator ] ):
        
        self._comparators = list( comparators )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_SELECTOR ] = PairSelector

class DuplicatesAutoResolutionRule( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Rule'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        """
        This guy holds everything to make a single auto-resolution job work. It knows the search it wants to do, and, when given pairs from that search, will confirm whether one file passes its auto-resolution threshold and should be auto-considered better.
        """
        
        super().__init__( name )
        
        # the id here will be for the database to match up rules to cached pair statuses. slightly wewmode, but we'll see
        self._id = -1
        
        self._paused = False
        
        self._potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        self._pair_selector = PairSelector()
        
        self._action = HC.DUPLICATE_BETTER
        
        self._delete_a = False
        self._delete_b = False
        
        self._custom_duplicate_content_merge_options: typing.Optional[ ClientDuplicates.DuplicateContentMergeOptions ] = None
        
        self._counts_cache = collections.Counter()
        
    
    def __eq__( self, other ):
        
        if isinstance( other, DuplicatesAutoResolutionRule ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return self._id.__hash__()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_potential_duplicates_search_context = self._potential_duplicates_search_context.GetSerialisableTuple()
        serialisable_pair_selector = self._pair_selector.GetSerialisableTuple()
        serialisable_custom_duplicate_content_merge_options = None if self._custom_duplicate_content_merge_options is None else self._custom_duplicate_content_merge_options.GetSerialisableTuple()
        
        return (
            self._id,
            self._paused,
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
            self._paused,
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
        
    
    def CanWorkHard( self ):
        
        return not self._paused and ( self.HasResolutionWorkToDo() or self.HasSearchWorkToDo() )
        
    
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
        
    
    def GetCountsCacheDuplicate( self ):
        
        return collections.Counter( self._counts_cache )
        
    
    def GetDeleteInfo( self ) -> typing.Tuple[ bool, bool ]:
        
        return ( self._delete_a, self._delete_b )
        
    
    def GetDuplicateContentMergeOptions( self ) -> typing.Optional[ ClientDuplicates.DuplicateContentMergeOptions ]:
        
        return self._custom_duplicate_content_merge_options
        
    
    def GetId( self ) -> int:
        
        return self._id
        
    
    def GetPairSelector( self ) -> PairSelector:
        
        return self._pair_selector
        
    
    def GetPairSelectorSummary( self ) -> str:
        
        return self._pair_selector.GetSummary()
        
    
    def GetPotentialDuplicatesSearchContext( self ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext:
        
        return self._potential_duplicates_search_context
        
    
    def GetRuleSummary( self ) -> str:
        
        return self._potential_duplicates_search_context.GetSummary()
        
    
    def GetSearchSummary( self ) -> str:
        
        if sum( self._counts_cache.values() ) == 0:
            
            return 'no data'
            
        
        not_searched = self._counts_cache[ DUPLICATE_STATUS_NOT_SEARCHED ]
        not_match = self._counts_cache[ DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH ]
        not_tested = self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED ]
        failed_test = self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST ]
        
        passed_test = self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST ]
        
        result = ''
        
        if not_searched > 0:
            
            result += f'{HydrusNumbers.ToHumanInt( not_searched )} to search, '
            
        
        if not_tested > 0:
            
            result += f'{HydrusNumbers.ToHumanInt( not_tested )} still to test, '
            
        
        if not_searched + not_tested == 0:
            
            result += 'Done! '
            
        
        result += f'{HydrusNumbers.ToHumanInt( passed_test )} pairs resolved'
        
        if failed_test > 0:
            
            result += f' ({HydrusNumbers.ToHumanInt( failed_test )} failed the test)'
            
        
        if not_match > 0:
            
            result += f' ({HydrusNumbers.ToHumanInt( not_match )} did not match the search)'
            
        
        return result
        
    
    def HasResolutionWorkToDo( self ):
        
        return self._counts_cache[ DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED ] > 0
        
    
    def HasSearchWorkToDo( self ):
        
        return self._counts_cache[ DUPLICATE_STATUS_NOT_SEARCHED ] > 0
        
    
    def IsPaused( self ) -> bool:
        
        return self._paused
        
    
    def SetAction( self, action: int ):
        
        self._action = action
        
    
    def SetCountsCache( self, counts ):
        
        self._counts_cache = counts
        
    
    def SetDeleteInfo( self, delete_a: bool, delete_b: bool ):
        
        self._delete_a = delete_a
        self._delete_b = delete_b
        
    
    def SetDuplicateContentMergeOptions( self, duplicate_content_merge_options: typing.Optional[ ClientDuplicates.DuplicateContentMergeOptions ] ):
        
        self._custom_duplicate_content_merge_options = duplicate_content_merge_options
        
    
    def SetId( self, value: int ):
        
        self._id = value
        
    
    def SetPaused( self, value: bool ):
        
        self._paused = value
        
    
    def SetPotentialDuplicatesSearchContext( self, value: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ):
        
        self._potential_duplicates_search_context = value
        
    
    def SetPairSelector( self, value: PairSelector ):
        
        self._pair_selector = value
        
    
    def TestPair( self, media_result_1: ClientMediaResult.MediaResult, media_result_2: ClientMediaResult.MediaResult ):
        
        result = self._pair_selector.GetMatchingAB( media_result_1, media_result_2 )
        
        if result is None:
            
            return None
            
        else:
            
            ( media_result_a, media_result_b ) = result
            
        
        action = self._action
        delete_a = self._delete_a
        delete_b = self._delete_b
        
        if action == HC.DUPLICATE_WORSE:
            
            action = HC.DUPLICATE_BETTER
            
            ( media_result_a, media_result_b ) = ( media_result_b, media_result_a )
            ( delete_a, delete_b ) = ( delete_b, delete_a )
            
        
        if self._custom_duplicate_content_merge_options is None:
            
            duplicate_content_merge_options = CG.client_controller.new_options.GetDuplicateContentMergeOptions( action )
            
        else:
            
            duplicate_content_merge_options = self._custom_duplicate_content_merge_options
            
        
        hash_a = media_result_a.GetHash()
        hash_b = media_result_b.GetHash()
        
        content_update_packages = [ duplicate_content_merge_options.ProcessPairIntoContentUpdatePackage( media_result_a, media_result_b, delete_a = delete_a, delete_b = delete_b, file_deletion_reason = f'duplicates auto-resolution ({self._name})' ) ]
        
        return ( action, hash_a, hash_b, content_update_packages )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_RULE ] = DuplicatesAutoResolutionRule

def GetDefaultRuleSuggestions() -> typing.List[ DuplicatesAutoResolutionRule ]:
    
    suggested_rules = []
    
    #
    
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
    
    selector = PairSelector()
    
    comparator = PairComparatorOneFile()
    
    comparator.SetLookingAt( LOOKING_AT_A )
    
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
    
    #
    
    return suggested_rules
    

class DuplicatesAutoResolutionManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        """
        This guy is going to be the mainloop daemon that runs all this gubbins.
        
        Needs some careful locking for when the edit dialog is open, like import folders manager etc..
        """
        
        super().__init__( controller, 15 )
        
        self._currently_searching_rule = None
        self._currently_resolving_rule = None
        self._working_hard_rules = set()
        
        self._edit_work_lock = threading.Lock()
        
    
    def _AbleToWork( self ):
        
        if len( self._working_hard_rules ) > 0:
            
            return True
            
        
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
            
            work_period = 0.25
            time_it_took = 1.0
            
            if able_to_work:
                
                CG.client_controller.WaitUntilViewFree()
                
                with self._edit_work_lock:
                    
                    start_time = HydrusTime.GetNowFloat()
                    
                    try:
                        
                        still_work_to_do = self._WorkRules( work_period )
                        
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
                        
                    
                    time_it_took = HydrusTime.GetNowFloat() - start_time
                    
                
                CG.client_controller.pub( 'notify_duplicates_auto_resolution_work_complete' )
                
            
            with self._lock:
                
                wait_period = self._GetWaitPeriod( work_period, time_it_took, still_work_to_do )
                
            
            self._wake_event.wait( wait_period )
            
            self._wake_event.clear()
            
        
    
    def _FilterToWorkingHardRules( self, rules: typing.Collection[ DuplicatesAutoResolutionRule ] ):
        
        if len( self._working_hard_rules ) > 0:
            
            for rule in rules:
                
                if rule in self._working_hard_rules and not rule.CanWorkHard():
                    
                    self._working_hard_rules.discard( rule )
                    
                
            
            if len( self._working_hard_rules ) > 0:
                
                rules = [ rule for rule in rules if rule in self._working_hard_rules ]
                
            
        
        return rules
        
    
    def _GetWaitPeriod( self, work_period: float, time_it_took: float, still_work_to_do: bool ):
        
        if len( self._working_hard_rules ) > 0:
            
            return 0.1
            
        
        if not still_work_to_do:
            
            return 600
            
        
        if CG.client_controller.CurrentlyIdle():
            
            rest_ratio = 1
            
        else:
            
            rest_ratio = 10
            
        
        reasonable_work_time = min( 5 * work_period, time_it_took )
        
        return reasonable_work_time * rest_ratio
        
    
    def _WorkRules( self, allowed_work_time: float ):
        
        time_to_stop = HydrusTime.GetNowFloat() + allowed_work_time
        
        still_work_to_do = False
        
        matching_pairs_produced = False
        
        rules = CG.client_controller.Read( 'duplicate_auto_resolution_rules_with_counts' )
        
        with self._lock:
            
            rules = self._FilterToWorkingHardRules( rules )
            
        
        for rule in rules:
            
            if rule.IsPaused():
                
                continue
                
            
            if rule.HasSearchWorkToDo():
                
                try:
                    
                    with self._lock:
                        
                        self._currently_searching_rule = rule
                        
                    
                    ( still_work_to_do_here, matching_pairs_produced_here ) = CG.client_controller.WriteSynchronous( 'duplicate_auto_resolution_do_search_work', rule )
                    
                    if still_work_to_do_here:
                        
                        still_work_to_do = True
                        
                    
                    if matching_pairs_produced_here:
                        
                        matching_pairs_produced = True
                        
                    
                finally:
                    
                    with self._lock:
                        
                        self._currently_searching_rule = None
                        
                    
                
            
            if HydrusTime.TimeHasPassedFloat( time_to_stop ):
                
                return True
                
            
        
        if matching_pairs_produced:
            
            rules = CG.client_controller.Read( 'duplicate_auto_resolution_rules_with_counts' )
            
            with self._lock:
                
                rules = self._FilterToWorkingHardRules( rules )
                
            
        
        for rule in rules:
            
            if rule.IsPaused():
                
                continue
                
            
            if rule.HasResolutionWorkToDo():
                
                try:
                    
                    with self._lock:
                        
                        self._currently_resolving_rule = rule
                        
                    
                    still_work_to_do_here = CG.client_controller.WriteSynchronous( 'duplicate_auto_resolution_do_resolution_work', rule, stop_time = time_to_stop )
                    
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
        
    
    def GetRules( self ) -> typing.List[ DuplicatesAutoResolutionRule ]:
        
        rules = CG.client_controller.Read( 'duplicate_auto_resolution_rules_with_counts' )
        
        return rules
        
    
    def GetRunningStatus( self, rule: DuplicatesAutoResolutionRule ) -> str:
        
        with self._lock:
            
            if rule == self._currently_searching_rule:
                
                return 'searching'
                
            elif rule == self._currently_resolving_rule:
                
                return 'resolving'
                
            elif rule in self._working_hard_rules:
                
                return 'working hard'
                
            elif rule.HasSearchWorkToDo() or rule.HasSearchWorkToDo():
                
                return 'pending'
                
            else:
                
                return 'idle'
                
            
        
    
    def GetWorkingHard( self ) -> typing.Collection[ DuplicatesAutoResolutionRule ]:
        
        with self._lock:
            
            return set( self._working_hard_rules )
            
        
    
    def ResetRuleSearchProgress( self, rules: typing.Collection[ DuplicatesAutoResolutionRule ] ):
        
        for rule in rules:
            
            CG.client_controller.WriteSynchronous( 'duplicate_auto_resolution_reset_rule_search_progress', rule )
            
        
        self.Wake()
        
    
    def SetRules( self, rules: typing.Collection[ DuplicatesAutoResolutionRule ] ):
        
        with self._lock:
            
            self._working_hard_rules = set()
            
        
        CG.client_controller.Write( 'duplicate_auto_resolution_set_rules', rules )
        
        self.Wake()
        
    
    def SetWorkingHard( self, rule: DuplicatesAutoResolutionRule, work_hard: bool ):
        
        with self._lock:
            
            if work_hard and rule not in self._working_hard_rules and rule.CanWorkHard():
                
                self._working_hard_rules.add( rule )
                
            elif not work_hard and rule in self._working_hard_rules:
                
                self._working_hard_rules.discard( rule )
                
            
        
        self.Wake()
        
    
