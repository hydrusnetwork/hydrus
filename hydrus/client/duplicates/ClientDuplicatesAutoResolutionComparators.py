import random
import typing

from hydrus.core import HydrusSerialisable

from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientMetadataConditional 
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate

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

class PairComparatorRelativeFileInfo( PairComparator ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_FILE_INFO
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Pair Comparator - Relative File Info'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        """
        This guy compares the pair directly. It can say 'yes the better candidate is 4x bigger than the worse'. 
        """
        
        super().__init__()
        
        self._system_predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE )
        self._number_test = ClientNumberTest.NumberTest( operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN )
        self._multiplier = 1.0
        self._delta = 0
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_system_predicate = self._system_predicate.GetSerialisableTuple()
        serialisable_number_test = self._number_test.GetSerialisableTuple()
        
        return ( serialisable_system_predicate, serialisable_number_test, self._multiplier, self._delta )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_system_predicate, serialisable_number_test, self._multiplier, self._delta ) = serialisable_info
        
        self._system_predicate = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_system_predicate )
        self._number_test = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_number_test )
        
    
    def CanDetermineBetter( self ) -> bool:
        
        return self._number_test.operator in ( ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN, ClientNumberTest.NUMBER_TEST_OPERATOR_LESS_THAN ) or ( self._multiplier != 1.0 or self._delta != 0 )
        
    
    def GetMultiplier( self ) -> float:
        
        return self._multiplier
        
    
    def GetDelta( self ) -> int:
        
        return self._delta
        
    
    def GetNumberTest( self ) -> ClientNumberTest.NumberTest:
        
        return self._number_test
        
    
    def GetSystemPredicate( self ) -> ClientSearchPredicate.Predicate:
        
        return self._system_predicate
        
    
    def GetSummary( self ):
        
        pred_string = self._system_predicate.ToString()
        
        what_we_are_testing = 'B'
        
        if self._multiplier != 1.0:
            
            what_we_are_testing = f'{self._multiplier:.2f}x {what_we_are_testing}'
            
        
        if self._delta > 0:
            
            what_we_are_testing = f'{what_we_are_testing} +{self._delta}'
            
        elif self._delta < 0:
            
            what_we_are_testing = f'{what_we_are_testing} {self._delta}'
            
        
        number_test_string = self._number_test.ToString( replacement_value_string = what_we_are_testing )
        
        return f'A has {pred_string} {number_test_string}'
        
    
    def SetMultiplier( self, multiplier: float ):
        
        self._multiplier = multiplier
        
    
    def SetDelta( self, delta: int ):
        
        self._delta = delta
        
    
    def SetNumberTest( self, number_test: ClientNumberTest.NumberTest ):
        
        self._number_test = number_test 
        
    
    def SetSystemPredicate( self, system_predicate: ClientSearchPredicate.Predicate ):
        
        self._system_predicate = system_predicate
        
    
    def Test( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult ) -> bool:
        
        value_a = self._system_predicate.ExtractValueFromMediaResult( media_result_a )
        value_b = self._system_predicate.ExtractValueFromMediaResult( media_result_b )
        
        if value_a is None or value_b is None:
            
            return False
            
        
        prepared_value_b = int( value_b * self._multiplier ) + self._delta
        
        return self._number_test.Test( value_a, replacement_test_value = prepared_value_b )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_FILE_INFO ] = PairComparatorRelativeFileInfo

HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME = 0
HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS = 1
# do not put pixel similarity here. we'll have this as a toolbox of _very_ hardcoded stuff, no customisation for KISS

hardcoded_comparator_type_str_lookup = {
    HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME : 'A and B have the same filetype',
    HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS : 'A and B have different filetypes'
}

class PairComparatorRelativeHardcoded( PairComparator ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_HARDCODED
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Pair Comparator - Relative Hardcoded'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, hardcoded_type = HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME ):
        """
        This guy compares the pair directly using special code for tricky jobs. 
        """
        
        super().__init__()
        
        self._hardcoded_type = hardcoded_type
        
    
    def _GetSerialisableInfo( self ):
        
        return self._hardcoded_type
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._hardcoded_type = serialisable_info
        
    
    def CanDetermineBetter( self ) -> bool:
        
        return False
        
    
    def GetSummary( self ):
        
        return hardcoded_comparator_type_str_lookup[ self._hardcoded_type ]
        
    
    def Test( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult ) -> bool:
        
        if self._hardcoded_type in ( HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME, HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS ):
            
            a_filetype = media_result_a.GetMime()
            b_filetype = media_result_b.GetMime()
            
            if self._hardcoded_type == HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME:
                
                return a_filetype == b_filetype
                
            elif self._hardcoded_type == HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS:
                
                return a_filetype != b_filetype
                
            
        
        raise Exception( f'Do not understand what I should do with a type of {self._hardcoded_type}!' )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_HARDCODED ] = PairComparatorRelativeHardcoded

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
        
    
    def __eq__( self, other ):
        
        if isinstance( other, PairSelector ):
            
            return self.GetSerialisableTuple() == other.GetSerialisableTuple()
            
        
        return NotImplemented
        
    
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
