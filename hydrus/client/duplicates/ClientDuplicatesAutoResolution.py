import random
import threading
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.metadata import ClientMetadataConditional
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchFileSearchContext

# in the database I guess we'll assign these in a new table to all outstanding pairs that match a search
DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH = 0
DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED = 1
DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST = 2
DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST = 3 # presumably this will not be needed much since we'll delete the duplicate pair soon after, but we may as well be careful
DUPLICATE_STATUS_NOT_SEARCHED = 4 # assign this to new pairs that are added, by default??? then re-do the search with system:hash tacked on maybe, regularly

class PairComparator( HydrusSerialisable.SerialisableBase ):
    
    def Test( self, media_result_better, media_result_worse ):
        
        raise NotImplementedError()
        
    

LOOKING_AT_BETTER_CANDIDATE = 0
LOOKING_AT_WORSE_CANDIDATE = 1

class PairComparatorOneFile( PairComparator ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_ONE_FILE
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Pair Comparator - One File'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        """
        This guy holds one test and is told to test either the better or worse candidate. Multiple of these stacked up make for 'the better file is a jpeg over one megabyte, the worse file is a jpeg under 100KB'.
        """
        
        super().__init__()
        
        # this guy tests the better or the worse for a single property
        # user could set up multiple on either side of the equation
        # what are we testing?
            # better file mime is jpeg (& worse file is png)
            # better file has icc profile
            # worse file filesize < 200KB
        
        self._looking_at = LOOKING_AT_BETTER_CANDIDATE
        
        self._metadata_conditional = ClientMetadataConditional.MetadataConditional()
        
    
    # serialisable gubbins
    # get/set
    
    def Test( self, media_result_better, media_result_worse ):
        
        if self._looking_at == LOOKING_AT_BETTER_CANDIDATE:
            
            return self._metadata_conditional.Test( media_result_better )
            
        else:
            
            return self._metadata_conditional.Test( media_result_worse )
            
        
    

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
        
        # if I am feeling big brain, isn't this just a dynamic one-file metadata conditional?
            # if we want 4x size, then we just pull the size of A and ask if B is <0.25x that or whatever. we don't need a clever two-file MetadataConditional test
        # so, this guy should yeah just store two or three simple enums to handle type, operator, and quantity
        
        # property
            # width
            # filesize
            # age
            # etc..
        # operator
            # is more than 4x larger
            # is at least x absolute value larger?
        
    
    # serialisable gubbins
    # get/set
    
    def Test( self, media_result_better, media_result_worse ):
        
        pass
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE ] = PairComparatorRelative

class PairSelectorAndComparator( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_SELECTOR_AND_COMPARATOR
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Pair Selector and Comparator'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        """
        This guy holds a bunch of comparators. It is given a pair of media and it tests all the rules both ways around. If the files pass all the rules, we have a match and thus a confirmed better file.
        
        A potential future expansion here is to attach scores to the rules and have a score threshold, but let's not get ahead of ourselves.
        """
        
        super().__init__()
        
        self._comparators = HydrusSerialisable.SerialisableList()
        
    
    # serialisable gubbins
    # get/set
    
    def GetMatchingMedia( self, media_result_1, media_result_2 ):
        
        pair = [ media_result_1, media_result_2 ]
        
        # just in case both match
        random.shuffle( pair )
        
        ( media_result_1, media_result_2 ) = pair
        
        if False not in ( comparator.Test( media_result_1, media_result_2 ) for comparator in self._comparators ):
            
            return media_result_1
            
        elif False not in ( comparator.Test( media_result_2, media_result_1 ) for comparator in self._comparators ):
            
            return media_result_2
            
        else:
            
            return None
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_SELECTOR_AND_COMPARATOR ] = PairSelectorAndComparator

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
        
        self._selector_and_comparator = None
        
        # action info
            # set as better
            # delete the other one
            # optional custom merge options
        
        # a search cache that we can update on every run, just some nice numbers for the human to see or force-populate in UI that say 'ok for this search we have 700,000 pairs, and we already processed 220,000'
        # I think a dict of numbers to strings
        # number of pairs that match the search
        # how many didn't pass the comparator test
        # also would be neat just to remember how many pairs we have successfully processed
        
    
    # serialisable gubbins
    # get/set
    # 'here's a pair of media results, pass/fail?'
    
    def GetId( self ) -> int:
        
        return self._id
        
    
    def GetActionSummary( self ) -> str:
        
        return 'set A as better, delete worse'
        
    
    def GetComparatorSummary( self ) -> str:
        
        return 'if A is jpeg and B is png'
        
    
    def GetPotentialDuplicatesSearchContext( self ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext:
        
        return self._potential_duplicates_search_context
        
    
    def GetRuleSummary( self ) -> str:
        
        return 'system:filetype is jpeg & system:filetype is png, pixel duplicates'
        
    
    def GetSearchSummary( self ) -> str:
        
        return 'unknown'
        
    
    def IsPaused( self ) -> bool:
        
        return self._paused
        
    
    def SetId( self, value: int ):
        
        self._id = value
        
    
    def SetPaused( self, value: bool ):
        
        self._paused = value
        
    
    def SetPotentialDuplicatesSearchContext( self, value: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext ):
        
        self._potential_duplicates_search_context = value
        
    

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
    
    duplicates_auto_resolution_rule = DuplicatesAutoResolutionRule( 'pixel-perfect jpegs vs pngs' )
    
    duplicates_auto_resolution_rule.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
    
    suggested_rules.append( duplicates_auto_resolution_rule )
    
    # add on a thing here about resolution. one(both) files need to be like at least 128x128
    
    #
    
    return suggested_rules
    

class DuplicatesAutoResolutionManager( ClientDaemons.ManagerWithMainLoop ):
    
    def __init__( self, controller: "CG.ClientController.Controller" ):
        """
        This guy is going to be the mainloop daemon that runs all this gubbins.
        
        Needs some careful locking for when the edit dialog is open, like import folders manager etc..
        """
        
        super().__init__( controller )
        
        self._ids_to_rules = {}
        
        # load rules from db or whatever on controller init
        # on program first boot, we should initialise with the defaults set to paused!
        
    
    def _AbleToWork( self ):
        
        if CG.client_controller.CurrentlyIdle():
            
            if not CG.client_controller.new_options.GetBoolean( 'duplicates_auto_resolution_during_idle' ):
                
                return False
                
            
            if not CG.client_controller.GoodTimeToStartBackgroundWork():
                
                return False
                
            
        else:
            
            if not CG.client_controller.new_options.GetBoolean( 'duplicates_auto_resolution_during_active' ):
                
                return False
                
            
        
        return True
        
    
    def GetName( self ) -> str:
        
        return 'duplicates auto-resolution'
        
    
    def GetRules( self ):
        
        return []
        
    
    def GetRunningStatus( self, rule_id: int ) -> str:
        
        return 'idle'
        
    
    def MainLoop( self ):
        
        try:
            
            time_to_start = HydrusTime.GetNow() + 15
            
            while not HydrusTime.TimeHasPassed( time_to_start ):
                
                with self._lock:
                    
                    self._CheckShutdown()
                    
                
                self._wake_event.wait( 1 )
                
            
            while True:
                
                with self._lock:
                    
                    self._CheckShutdown()
                    
                    able_to_work = self._AbleToWork()
                    
                
                still_work_to_do = False
                
                work_period = 0.25
                time_it_took = 1.0
                
                if able_to_work:
                    
                    CG.client_controller.WaitUntilViewFree()
                    
                    start_time = HydrusTime.GetNowFloat()
                    
                    try:
                        
                        pass # get some work, do some work
                        still_work_to_do = False
                        
                    except Exception as e:
                        
                        self._serious_error_encountered = True
                        
                        HydrusData.PrintException( e )
                        
                        message = 'There was an unexpected problem during duplicates auto-resolution work! This system will not run again this boot. A full traceback of this error should be written to the log.'
                        message += '\n' * 2
                        message += str( e )
                        
                        HydrusData.ShowText( message )
                        
                    finally:
                        
                        CG.client_controller.pub( 'notify_duplicates_auto_resolution_work_complete' )
                        
                    
                    time_it_took = HydrusTime.GetNowFloat() - start_time
                    
                
                wait_period = self._GetWaitPeriod( work_period, time_it_took, still_work_to_do )
                
                self._wake_event.wait( wait_period )
                
                self._wake_event.clear()
                
            
        except HydrusExceptions.ShutdownException:
            
            pass
            
        finally:
            
            self._mainloop_is_finished = True
            
        
    
    def _GetWaitPeriod( self, work_period: float, time_it_took: float, still_work_to_do: bool ):
        
        if not still_work_to_do:
            
            return 600
            
        
        if CG.client_controller.CurrentlyIdle():
            
            rest_ratio = 1
            
        else:
            
            rest_ratio = 10
            
        
        reasonable_work_time = min( 5 * work_period, time_it_took )
        
        return reasonable_work_time * rest_ratio
        
    
    def SetRules( self, rules: typing.Collection[ DuplicatesAutoResolutionRule ] ):
        
        # save to database
        
        # make sure the rules that need ids now have them
        
        self._ids_to_rules = { rule.GetId() : rule for rule in rules }
        
        # send out an update signal
        
    
