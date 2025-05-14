import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

NUMBER_TEST_OPERATOR_LESS_THAN = 0
NUMBER_TEST_OPERATOR_GREATER_THAN = 1
NUMBER_TEST_OPERATOR_EQUAL = 2
NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT = 3
NUMBER_TEST_OPERATOR_NOT_EQUAL = 4
NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE = 5

number_test_operator_to_str_lookup = {
    NUMBER_TEST_OPERATOR_LESS_THAN : '<',
    NUMBER_TEST_OPERATOR_GREATER_THAN : '>',
    NUMBER_TEST_OPERATOR_EQUAL : '=',
    NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT : HC.UNICODE_APPROX_EQUAL,
    NUMBER_TEST_OPERATOR_NOT_EQUAL : HC.UNICODE_NOT_EQUAL,
    NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE : HC.UNICODE_APPROX_EQUAL
}

number_test_operator_to_desc_lookup = {
    NUMBER_TEST_OPERATOR_LESS_THAN : 'less than',
    NUMBER_TEST_OPERATOR_GREATER_THAN : 'greater than',
    NUMBER_TEST_OPERATOR_EQUAL : 'equal',
    NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT : 'equal within a percentage range',
    NUMBER_TEST_OPERATOR_NOT_EQUAL : 'not equal',
    NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE : 'equal within an absolute range'
}

legacy_str_operator_to_number_test_operator_lookup = { s : o for ( o, s ) in number_test_operator_to_str_lookup.items() }

number_test_operator_to_pretty_str_lookup = {
    NUMBER_TEST_OPERATOR_LESS_THAN : 'less than',
    NUMBER_TEST_OPERATOR_GREATER_THAN : 'more than',
    NUMBER_TEST_OPERATOR_EQUAL : 'is',
    NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT : 'is about',
    NUMBER_TEST_OPERATOR_NOT_EQUAL : 'is not',
    NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE : 'is about'
}

number_test_str_to_operator_lookup = { value : key for ( key, value ) in number_test_operator_to_str_lookup.items() if key != NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE }

class NumberTest( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_NUMBER_TEST
    SERIALISABLE_NAME = 'Number Test'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, operator = NUMBER_TEST_OPERATOR_EQUAL, value = 1, extra_value = None ):
        
        super().__init__()
        
        if operator == NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT and value == 0:
            
            operator = NUMBER_TEST_OPERATOR_EQUAL
            extra_value = None
            
        
        self.operator = operator
        self.value = value
        
        if extra_value is None:
            
            if self.operator == NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT:
                
                extra_value = 0.15
                
            elif self.operator == NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE:
                
                extra_value = 1
                
            
        
        self.extra_value = extra_value
        
    
    def __eq__( self, other ):
        
        if isinstance( other, NumberTest ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.operator, self.value, self.extra_value ).__hash__()
        
    
    def __repr__( self ):
        
        return self.ToString()
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self.operator, self.value, self.extra_value )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.operator, self.value, self.extra_value ) = serialisable_info
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( operator, value ) = old_serialisable_info
            
            if operator == NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT:
                
                extra_value = 0.15
                
            else:
                
                extra_value = None
                
            
            new_serialisable_info = ( operator, value, extra_value )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetLambda( self, replacement_test_value = None ):
        
        if replacement_test_value is None:
            
            value_to_test = self.value
            
        else:
            
            value_to_test = replacement_test_value
            
        
        if self.operator == NUMBER_TEST_OPERATOR_LESS_THAN:
            
            if value_to_test > 0:
                
                return lambda x: x is None or x < value_to_test
                
            else:
                
                return lambda x: x is not None and x < value_to_test
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_GREATER_THAN:
            
            if value_to_test < 0:
                
                return lambda x: x is None or x > value_to_test
                
            else:
                
                return lambda x: x is not None and x > value_to_test
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_EQUAL:
            
            if value_to_test == 0:
                
                return lambda x: x is None or x == value_to_test
                
            else:
                
                return lambda x: x == value_to_test
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT:
            
            lower = value_to_test * ( 1 - self.extra_value )
            upper = value_to_test * ( 1 + self.extra_value )
            
            if lower <= 0:
                
                return lambda x: x is None or x <= upper
                
            else:
                
                return lambda x: x is not None and lower <= x <= upper
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE:
            
            lower = value_to_test - self.extra_value
            upper = value_to_test + self.extra_value
            
            if lower <= 0:
                
                return lambda x: x is None or x <= upper
                
            else:
                
                return lambda x: x is not None and lower <= x <= upper
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_NOT_EQUAL:
            
            if value_to_test == 0:
                
                return lambda x: x is not None and x != value_to_test
                
            else:
                
                return lambda x: x is None or x != value_to_test
                
            
        
    
    def GetSQLitePredicates( self, variable_name ):
        
        if self.operator == NUMBER_TEST_OPERATOR_LESS_THAN:
            
            if self.value > 0:
                
                return [ f'( {variable_name} IS NULL OR {variable_name} < {self.value} )' ]
                
            else:
                
                return [ f'{variable_name} < {self.value}' ]
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_GREATER_THAN:
            
            if self.value < 0:
                
                return [ f'( {variable_name} IS NULL OR {variable_name} > {self.value} )' ]
                
            else:
                
                return [ f'{variable_name} > {self.value}' ]
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_EQUAL:
            
            if self.value == 0:
                
                return [ f'( {variable_name} IS NULL OR {variable_name} = {self.value} )' ]
                
            else:
                
                return [ f'{variable_name} = {self.value}' ]
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT:
            
            lower = self.value * ( 1 - self.extra_value )
            upper = self.value * ( 1 + self.extra_value )
            
            if lower <= 0:
                
                return [ f'( {variable_name} is NULL OR {variable_name} <= {upper} )' ]
                
            else:
                
                return [ f'{variable_name} >= {lower}', f'{variable_name} <= {upper}' ]
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE:
            
            lower = self.value - self.extra_value
            upper = self.value + self.extra_value
            
            if lower <= 0:
                
                return [ f'( {variable_name} IS NULL OR {variable_name} <= {upper} )' ]
                
            else:
                
                return [ f'{variable_name} >= {lower}', f'{variable_name} <= {upper}' ]
                
            
        elif self.operator == NUMBER_TEST_OPERATOR_NOT_EQUAL:
            
            if self.value == 0:
                
                return [ f'{variable_name} IS NOT NULL AND {variable_name} != {self.value}' ]
                
            else:
                
                return [ f'( {variable_name} IS NULL OR {variable_name} != {self.value} )' ]
                
            
        
        return []
        
    
    def IsAnythingButZero( self ):
        
        return self.operator in ( NUMBER_TEST_OPERATOR_NOT_EQUAL, NUMBER_TEST_OPERATOR_GREATER_THAN ) and self.value == 0
        
    
    def IsZero( self ):
        
        actually_zero = self.operator == NUMBER_TEST_OPERATOR_EQUAL and self.value == 0
        less_than_one = self.operator == NUMBER_TEST_OPERATOR_LESS_THAN and self.value == 1
        
        return actually_zero or less_than_one
        
    
    def ToString( self, absolute_number_renderer: typing.Optional[ typing.Callable ] = None, replacement_value_string: typing.Optional[ str ] = None ) -> str:
        
        if absolute_number_renderer is None:
            
            absolute_number_renderer = HydrusNumbers.ToHumanInt
            
        
        if replacement_value_string is None:
            
            value_string = absolute_number_renderer( self.value )
            
        else:
            
            value_string = replacement_value_string
            
        
        result = f'{number_test_operator_to_str_lookup[ self.operator ]} {value_string}'
        
        if self.operator == NUMBER_TEST_OPERATOR_APPROXIMATE_PERCENT:
            
            result += f' {HC.UNICODE_PLUS_OR_MINUS}{HydrusNumbers.FloatToPercentage(self.extra_value)}'
            
        elif self.operator == NUMBER_TEST_OPERATOR_APPROXIMATE_ABSOLUTE:
            
            result += f' {HC.UNICODE_PLUS_OR_MINUS}{absolute_number_renderer(self.extra_value)}'
            
        
        return result
        
    
    def WantsZero( self ):
        
        return self.GetLambda()( 0 )
        
    
    @staticmethod
    def STATICCreateFromCharacters( operator_str: str, value: int ) -> "NumberTest":
        
        operator = number_test_str_to_operator_lookup[ operator_str ]
        
        return NumberTest( operator, value )
        
    
    @staticmethod
    def STATICCreateMegaLambda( number_tests: typing.Collection[ "NumberTest" ] ):
        
        lambdas = [ number_test.GetLambda() for number_test in number_tests ]
        
        return lambda x: False not in ( lamb( x ) for lamb in lambdas )
        
    
    def Test( self, value, replacement_test_value = None ) -> bool:
        
        return self.GetLambda( replacement_test_value = replacement_test_value )( value )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_NUMBER_TEST ] = NumberTest
