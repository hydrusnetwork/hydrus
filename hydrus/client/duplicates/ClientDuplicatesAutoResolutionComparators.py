import collections.abc
import random
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client.duplicates import ClientDuplicatesComparisonStatements
from hydrus.client.files.images import ClientVisualData
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientMetadataConditional 
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate

class PairComparator( HydrusSerialisable.SerialisableBase ):
    
    def CanDetermineBetter( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def IsFast( self ) -> bool:
        
        raise NotImplementedError()
        
    
    def GetSummary( self ) -> str:
        
        raise NotImplementedError()
        
    
    def OrderDoesNotMatter( self ) -> bool:
        
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
            
        
    
    def IsFast( self ) -> bool:
        
        return True
        
    
    def OrderDoesNotMatter( self ) -> bool:
        
        return self._looking_at == LOOKING_AT_EITHER
        
    
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
            
        else:
            
            return False
            
        
    

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
        
        we_time_pred = self._system_predicate.GetType() in (
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME,
            ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME
        )
        
        we_duration_pred = self._system_predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION
        
        what_we_are_testing = 'B'
        
        if self._multiplier != 1.0:
            
            what_we_are_testing = f'{self._multiplier:.2f}x {what_we_are_testing}'
            
        
        if we_time_pred or we_duration_pred:
            
            absolute_number_renderer = lambda t: HydrusTime.TimeDeltaToPrettyTimeDelta( t / 1000 )
            
            delta_string = absolute_number_renderer( self._delta )
            
        else:
            
            absolute_number_renderer = None
            delta_string = self._delta
            
        
        if self._delta > 0:
            
            what_we_are_testing = f'{what_we_are_testing} +{delta_string}'
            
        elif self._delta < 0:
            
            what_we_are_testing = f'{what_we_are_testing} {delta_string}'
            
        
        number_test_string = self._number_test.ToString( absolute_number_renderer = absolute_number_renderer, replacement_value_string = what_we_are_testing, use_time_operators = we_time_pred )
        
        return f'A has "{pred_string}" {number_test_string}'
        
    
    def IsFast( self ) -> bool:
        
        return True
        
    
    def OrderDoesNotMatter( self ) -> bool:
        
        return self._number_test.operator in ( ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL, ClientNumberTest.NUMBER_TEST_OPERATOR_NOT_EQUAL ) and self._multiplier == 1.0 and self._delta == 0
        
    
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
HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME = 2
HARDCODED_COMPARATOR_TYPE_HAS_ICC_PROFILE_SAME = 3
# do not put pixel similarity here. we'll have this enum be a toolbox of _very_ hardcoded stuff, no customisation for KISS

hardcoded_comparator_type_str_lookup = {
    HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME : 'A and B have the same filetype',
    HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS : 'A and B have different filetypes',
    HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME : 'A and B have the same "has exif" value',
    HARDCODED_COMPARATOR_TYPE_HAS_ICC_PROFILE_SAME : 'A and B have the same "has icc profile" value',
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
        
    
    def IsFast( self ) -> bool:
        
        return True
        
    
    def OrderDoesNotMatter( self ):
        
        return True
        
    
    def Test( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult ) -> bool:
        
        if self._hardcoded_type in ( HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME, HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS ):
            
            a_filetype = media_result_a.GetMime()
            b_filetype = media_result_b.GetMime()
            
            if self._hardcoded_type == HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME:
                
                return a_filetype == b_filetype
                
            elif self._hardcoded_type == HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS:
                
                return a_filetype != b_filetype
                
            
        elif self._hardcoded_type == HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME:
            
            return media_result_a.GetFileInfoManager().has_exif == media_result_b.GetFileInfoManager().has_exif
            
        elif self._hardcoded_type == HARDCODED_COMPARATOR_TYPE_HAS_ICC_PROFILE_SAME:
            
            return media_result_a.GetFileInfoManager().has_icc_profile == media_result_b.GetFileInfoManager().has_icc_profile
            
        
        raise Exception( f'Do not understand what I should do with a type of {self._hardcoded_type}!' )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_HARDCODED ] = PairComparatorRelativeHardcoded

class PairComparatorRelativeVisualDuplicates( PairComparator ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_VISUAL_DUPLICATES
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Pair Comparator - Relative Visual Duplicates'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, acceptable_confidence = ClientVisualData.VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY ):
        """
        This guy compares the pair directly using the "A and B are visual duplicates" algorithm.
        
        Since the algorithm biases towards false positive, we won't turn on 'they are not duplicates' detection, but if we end up graduating that confidence, we could. We'd want to add a direction operator here obviously.
        We'd have to differentiate "These files are too small to process" versus "I positively recognise these are very different".
        """
        
        super().__init__()
        
        self._acceptable_confidence = acceptable_confidence
        
    
    def _GetSerialisableInfo( self ):
        
        return self._acceptable_confidence
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._acceptable_confidence = serialisable_info
        
    
    def CanDetermineBetter( self ) -> bool:
        
        return False
        
    
    def GetAcceptableConfidence( self ) -> int:
        
        return self._acceptable_confidence
        
    
    def GetSummary( self ):
        
        s = ClientVisualData.result_str_lookup.get( self._acceptable_confidence, 'unknown confidence' )
        
        return f'A and B are {s}'
        
    
    def IsFast( self ) -> bool:
        
        return False
        
    
    def OrderDoesNotMatter( self ):
        
        return True
        
    
    def Test( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult ) -> bool:
        
        if media_result_a.GetMime() in HC.IMAGES and media_result_b.GetMime() in HC.IMAGES:
            
            visual_data_a = ClientDuplicatesComparisonStatements.GetVisualData( media_result_a )
            visual_data_b = ClientDuplicatesComparisonStatements.GetVisualData( media_result_b )
            
            ( simple_seems_good, simple_result, simple_score_statement ) = ClientVisualData.FilesAreVisuallySimilarSimple( visual_data_a, visual_data_b )
            
            if simple_seems_good:
                
                visual_data_tiled_a = ClientDuplicatesComparisonStatements.GetVisualDataTiled( media_result_a )
                visual_data_tiled_b = ClientDuplicatesComparisonStatements.GetVisualDataTiled( media_result_b )
                
                ( regional_seems_good, regional_result, regional_score_statement ) = ClientVisualData.FilesAreVisuallySimilarRegional( visual_data_tiled_a, visual_data_tiled_b )
                
                return regional_result >= self._acceptable_confidence
                
            
        
        return False
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_TWO_FILES_RELATIVE_VISUAL_DUPLICATES ] = PairComparatorRelativeVisualDuplicates

class PairComparatorOR( PairComparator ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_OR
    SERIALISABLE_NAME = 'Duplicates Auto-Resolution Pair Comparator - OR'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, sub_comparators: collections.abc.Collection[ PairComparator ] = None ):
        """
        This guy holds other comparators and does an OR of them. 
        """
        
        if sub_comparators is None:
            
            sub_comparators = []
            
        
        super().__init__()
        
        self._sub_comparators = HydrusSerialisable.SerialisableList( sub_comparators )
        
        self._SortComparators()
        
    
    def _GetSerialisableInfo( self ):
        
        return self._sub_comparators.GetSerialisableTuple()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._sub_comparators = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_info )
        
        self._SortComparators()
        
    
    def _SortComparators( self ):
        
        # maybe one day we sort for speed, but for now let's just be stable
        
        self._sub_comparators = HydrusSerialisable.SerialisableList( sorted( self._sub_comparators, key = lambda sc: sc.GetSummary() ) )
        
    
    def GetComparators( self ):
        
        return self._sub_comparators
        
    
    def CanDetermineBetter( self ) -> bool:
        
        # let's be strict to stay safe
        return len( self._sub_comparators ) > 0 and False not in ( sub_comparator.CanDetermineBetter() for sub_comparator in self._sub_comparators )
        
    
    def GetSummary( self ):
        
        return '(' + ') OR ('.join( ( sub_comparator.GetSummary() for sub_comparator in self._sub_comparators ) ) + ')'
        
    
    def IsFast( self ) -> bool:
        
        # let's be strict to stay safe
        return False not in ( sub_comparator.IsFast() for sub_comparator in self._sub_comparators )
        
    
    def OrderDoesNotMatter( self ):
        
        # let's be strict to stay safe
        return False not in ( sub_comparator.OrderDoesNotMatter() for sub_comparator in self._sub_comparators )
        
    
    def Test( self, media_result_a: ClientMediaResult.MediaResult, media_result_b: ClientMediaResult.MediaResult ) -> bool:
        
        for sub_comparator in self._sub_comparators:
            
            if sub_comparator.Test( media_result_a, media_result_b ):
                
                return True
                
            
        
        return False
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_COMPARATOR_OR ] = PairComparatorOR

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
        
        self._comparators: list[ PairComparator ] = HydrusSerialisable.SerialisableList()
        
    
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
        
    
    def GetMatchingAB( self, media_result_1: ClientMediaResult.MediaResult, media_result_2: ClientMediaResult.MediaResult, test_both_ways_around = True ) -> typing.Optional[ tuple[ ClientMediaResult.MediaResult, ClientMediaResult.MediaResult ] ]:
        
        pair = [ media_result_1, media_result_2 ]
        
        if test_both_ways_around:
            
            # just in case both match
            random.shuffle( pair )
            
        
        ( media_result_1, media_result_2 ) = pair
        
        if len( self._comparators ) == 0:
            
            # no testing, just return whatever. let's hope this is an alternates thing
            return ( media_result_1, media_result_2 )
            
        
        # ok we are splaying the logic out here to optimise
        
        fast_comparators = [ comparator for comparator in self._comparators if comparator.IsFast() ]
        slow_comparators = [ comparator for comparator in self._comparators if not comparator.IsFast() ]
        
        fast_comparators_where_order_may_matter = [ comparator for comparator in fast_comparators if not comparator.OrderDoesNotMatter() ]
        fast_comparators_where_order_matters_not = [ comparator for comparator in fast_comparators if comparator.OrderDoesNotMatter() ]
        
        slow_comparators_where_order_may_matter = [ comparator for comparator in slow_comparators if not comparator.OrderDoesNotMatter() ]
        slow_comparators_where_order_matters_not = [ comparator for comparator in slow_comparators if comparator.OrderDoesNotMatter() ]
        
        one_two_ok = True
        two_one_ok = test_both_ways_around
        
        if False in ( comparator.Test( media_result_1, media_result_2 ) for comparator in fast_comparators_where_order_matters_not ):
            
            one_two_ok = False
            two_one_ok = False
            
        
        if one_two_ok:
            
            if False in ( comparator.Test( media_result_1, media_result_2 ) for comparator in fast_comparators_where_order_may_matter ):
                
                one_two_ok = False
                
            
        
        if two_one_ok:
            
            if False in ( comparator.Test( media_result_2, media_result_1 ) for comparator in fast_comparators_where_order_may_matter ):
                
                two_one_ok = False
                
            
        
        if one_two_ok or two_one_ok:
            
            if False in ( comparator.Test( media_result_1, media_result_2 ) for comparator in slow_comparators_where_order_matters_not ):
                
                one_two_ok = False
                two_one_ok = False
                
            
        
        if one_two_ok:
            
            if False in ( comparator.Test( media_result_1, media_result_2 ) for comparator in slow_comparators_where_order_may_matter ):
                
                one_two_ok = False
                
            
        
        if one_two_ok:
            
            return ( media_result_1, media_result_2 )
            
        
        if two_one_ok:
            
            if False in ( comparator.Test( media_result_2, media_result_1 ) for comparator in slow_comparators_where_order_may_matter ):
                
                two_one_ok = False
                
            
        
        if two_one_ok:
            
            return ( media_result_2, media_result_1 )
            
        
        return None
        
    
    def GetSummary( self ) -> str:
        
        comparator_strings = sorted( [ comparator.GetSummary() for comparator in self._comparators ] )
        
        return ', '.join( comparator_strings )
        
    
    def IsFast( self ) -> bool:
        
        return False not in ( comparator.IsFast() for comparator in self._comparators )
        
    
    def MatchingPairMatchesBothWaysAround( self, media_result_1: ClientMediaResult.MediaResult, media_result_2: ClientMediaResult.MediaResult ) -> bool:
        """This presumes the pair DO match as 1,2."""
        
        fast_comparators_where_order_may_matter = [ comparator for comparator in self._comparators if comparator.IsFast() and not comparator.OrderDoesNotMatter() ]
        
        slow_comparators_where_order_may_matter = [ comparator for comparator in self._comparators if not comparator.IsFast() and not comparator.OrderDoesNotMatter() ]
        
        if False in ( comparator.Test( media_result_2, media_result_1 ) for comparator in fast_comparators_where_order_may_matter ):
            
            return False
            
        
        if False in ( comparator.Test( media_result_2, media_result_1 ) for comparator in slow_comparators_where_order_may_matter ):
            
            return False
            
        
        return True
        
    
    def SetComparators( self, comparators: collections.abc.Collection[ PairComparator ] ):
        
        self._comparators = list( comparators )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATES_AUTO_RESOLUTION_PAIR_SELECTOR ] = PairSelector
