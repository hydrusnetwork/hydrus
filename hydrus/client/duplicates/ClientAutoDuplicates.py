import random
import threading

from hydrus.core import HydrusSerialisable

from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.metadata import ClientMetadataConditional

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
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_AUTO_DUPLICATES_PAIR_COMPARATOR_ONE_FILE
    SERIALISABLE_NAME = 'Auto-Duplicates Pair Comparator - One File'
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
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_AUTO_DUPLICATES_PAIR_COMPARATOR_ONE_FILE ] = PairComparatorOneFile

class PairComparatorRelative( PairComparator ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_AUTO_DUPLICATES_PAIR_COMPARATOR_TWO_FILES_RELATIVE
    SERIALISABLE_NAME = 'Auto-Duplicates Pair Comparator - Relative'
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
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_AUTO_DUPLICATES_PAIR_COMPARATOR_TWO_FILES_RELATIVE ] = PairComparatorRelative

class PairSelectorAndComparator( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_AUTO_DUPLICATES_PAIR_SELECTOR_AND_COMPARATOR
    SERIALISABLE_NAME = 'Auto-Duplicates Pair Selector and Comparator'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        """
        This guy holds a bunch of rules. It is given a pair of media and it tests all the rules both ways around. If the files pass all the rules, we have a match and thus a confirmed better file.
        
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
            
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_AUTO_DUPLICATES_PAIR_SELECTOR_AND_COMPARATOR ] = PairSelectorAndComparator

class DuplicatesAutoResolutionRule( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_AUTO_DUPLICATES_RULE
    SERIALISABLE_NAME = 'Auto-Duplicates Rule'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, name ):
        """
        This guy holds everything to make a single auto-resolution job work. It knows the search it wants to do, and, when given pairs from that search, will confirm whether one file passes its auto-resolution threshold and should be auto-considered better.
        """
        
        super().__init__( name )
        
        # the id here will be for the database to match up rules to cached pair statuses. slightly wewmode, but we'll see
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
    
    def GetId( self ) -> int:
        
        return self._id
        
    
    def SetId( self, id: int ):
        
        self._id = id
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_AUTO_DUPLICATES_RULE ] = DuplicatesAutoResolutionRule

class DuplicatesAutoResolutionManager( object ):
    
    my_instance = None
    
    def __init__( self ):
        """
        This guy is going to be the mainloop daemon that runs all this gubbins.
        
        Needs some careful locking for when the edit dialog is open, like import folders manager etc..
        """
        
        DuplicatesAutoResolutionManager.my_instance = self
        
        # my rules, start with empty and then load from db or whatever on controller init
        
        self._lock = threading.Lock()
        
    
    @staticmethod
    def instance() -> 'DuplicatesAutoResolutionManager':
        
        if DuplicatesAutoResolutionManager.my_instance is None:
            
            DuplicatesAutoResolutionManager()
            
        
        return DuplicatesAutoResolutionManager.my_instance
        
    
    def Wake( self ):
        
        pass
        
    
