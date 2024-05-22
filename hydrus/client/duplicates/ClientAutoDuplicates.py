import random
import threading

from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client.duplicates import ClientDuplicates

DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH = 0
DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED = 1
DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST = 2
DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST = 3 # presumably this will not be needed much since we'll delete the duplicate pair soon after, but we may as well be careful

class PairComparatorRule( HydrusSerialisable.SerialisableBase ):
    
    def Test( self, media_result_better, media_result_worse ):
        
        raise NotImplementedError()
        
    

LOOKING_AT_BETTER_CANDIDATE = 0
LOOKING_AT_WORSE_CANDIDATE = 1

class PairComparatorRuleOneFile( PairComparatorRule ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_AUTO_DUPLICATES_PAIR_COMPARATOR_RULE_ONE_FILE
    SERIALISABLE_NAME = 'Auto-Duplicates Pair Comparator Rule - One File'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        PairComparatorRule.__init__( self )
        
        self._looking_at = LOOKING_AT_BETTER_CANDIDATE
        
        # ok bro time to get metadata conditional working. first draft will be filetype test for jpeg/png. no need for UI yet
        self._metadata_conditional = None
        # what are we testing?
            # this would be a great place to insert MetadataConditional
            # mime is jpeg
            # has icc profile
            # maybe stuff like filesize > 200KB
        
    
    # serialisable gubbins
    # get/set
    
    def Test( self, media_result_better, media_result_worse ):
        
        if self._looking_at == LOOKING_AT_BETTER_CANDIDATE:
            
            return self._metadata_conditional.Test( media_result_better )
            
        else:
            
            return self._metadata_conditional.Test( media_result_worse )
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_AUTO_DUPLICATES_PAIR_COMPARATOR_RULE_ONE_FILE ] = PairComparatorRuleOneFile

class PairComparatorRuleTwoFiles( PairComparatorRule ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_AUTO_DUPLICATES_PAIR_COMPARATOR_RULE_TWO_FILES
    SERIALISABLE_NAME = 'Auto-Duplicates Pair Comparator Rule - Two Files'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        PairComparatorRule.__init__( self )
        
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
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_AUTO_DUPLICATES_PAIR_COMPARATOR_RULE_TWO_FILES ] = PairComparatorRuleTwoFiles

class PairSelectorAndComparator( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_AUTO_DUPLICATES_PAIR_SELECTOR_AND_COMPARATOR
    SERIALISABLE_NAME = 'Auto-Duplicates Pair Selector and Comparator'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._rules = HydrusSerialisable.SerialisableList()
        
    
    # serialisable gubbins
    # get/set
    
    def GetMatchingMedia( self, media_result_1, media_result_2 ):
        
        pair = [ media_result_1, media_result_2 ]
        
        # just in case both match
        random.shuffle( pair )
        
        ( media_result_1, media_result_2 ) = pair
        
        if False not in ( rule.Test( media_result_1, media_result_2 ) for rule in self._rules ):
            
            return media_result_1
            
        elif False not in ( rule.Test( media_result_2, media_result_1 ) for rule in self._rules ):
            
            return media_result_2
            
        else:
            
            return None
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_AUTO_DUPLICATES_PAIR_SELECTOR_AND_COMPARATOR ] = PairSelectorAndComparator

class DuplicatesAutoResolutionRule( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_AUTO_DUPLICATES_RULE
    SERIALISABLE_NAME = 'Auto-Duplicates Rule'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        self._id = -1
        
        # maybe make this search part into its own object? in ClientDuplicates
        # could wangle duplicate pages and client api dupe stuff to work in the same guy, great idea
        self._file_search_context_1 = None
        self._file_search_context_2 = None
        self._dupe_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
        self._pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        self._max_hamming_distance = 4
        
        self._selector_and_comparator = None
        
        # action info
            # set as better
            # delete the other one
            # optional custom merge options
        
    
    # serialisable gubbins
    # get/set
    # 'here's a pair of media results, pass/fail?'
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_AUTO_DUPLICATES_RULE ] = DuplicatesAutoResolutionRule

class DuplicatesAutoResolutionManager( object ):
    
    my_instance = None
    
    def __init__( self ):
        
        DuplicatesAutoResolutionManager.my_instance = self
        
        # my rules, start with empty and then load from db or whatever on controller init
        
        self._lock = threading.Lock()
        
    
    @staticmethod
    def instance() -> 'DuplicatesAutoResolutionManager':
        
        if DuplicatesAutoResolutionManager.my_instance is None:
            
            DuplicatesAutoResolutionManager()
            
        
        return DuplicatesAutoResolutionManager.my_instance
        
    
