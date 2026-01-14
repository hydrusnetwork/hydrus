import collections
import collections.abc
import decimal
import fractions
import os
import struct
import sys
import time
import traceback
import yaml

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers

def default_dict_list(): return collections.defaultdict( list )

def default_dict_set(): return collections.defaultdict( set )

def BuildKeyToListDict( pairs ):
    
    d = collections.defaultdict( list )
    
    for ( key, value ) in pairs: d[ key ].append( value )
    
    return d
    

def BuildKeyToSetDict( pairs ):
    
    d = collections.defaultdict( set )
    
    for ( key, value ) in pairs: d[ key ].add( value )
    
    return d
    

def BytesToNoneOrHex( b: bytes | None ):
    
    if b is None:
        
        return None
        
    else:
        
        return b.hex()
        
    

def HexToNoneOrBytes( h: str | None ):
    
    if h is None:
        
        return None
        
    else:
        
        return bytes.fromhex( h )
        
    

def CalculateScoreFromRating( count, rating ):
    
    # https://www.evanmiller.org/how-not-to-sort-by-average-rating.html
    
    positive = count * rating
    negative = count * ( 1.0 - rating )
    
    # positive + negative = count
    
    # I think I've parsed this correctly from the website! Not sure though!
    score = ( ( positive + 1.9208 ) / count - 1.96 * ( ( ( positive * negative ) / count + 0.9604 ) ** 0.5 ) / count ) / ( 1 + 3.8416 / count )
    
    return score
    

def CheckProgramIsNotShuttingDown():
    
    if HG.model_shutdown:
        
        raise HydrusExceptions.ShutdownException( 'Application is shutting down!' )
        
    

def CleanRunningFile( db_path, instance ):
    
    # just to be careful
    
    path = os.path.join( db_path, instance + '_running' )
    
    try:
        
        os.remove( path )
        
    except:
        
        pass
        
    

status_to_prefix = {
    HC.CONTENT_STATUS_CURRENT : '',
    HC.CONTENT_STATUS_PENDING : '(+) ',
    HC.CONTENT_STATUS_PETITIONED : '(-) ',
    HC.CONTENT_STATUS_DELETED : '(X) '
}

def ConvertValueRangeToBytes( value, range ):
    
    return ToHumanBytes( value ) + '/' + ToHumanBytes( range )
    

def DebugPrint( debug_info ):
    
    Print( debug_info )
    
    sys.stdout.flush()
    sys.stderr.flush()
    

def GenerateKey():
    
    return os.urandom( HC.HYDRUS_KEY_LENGTH )
    

def Get64BitHammingDistance( perceptual_hash1, perceptual_hash2 ):
    
    # old slow strategy:
    
    #while xor > 0:
    #    
    #    distance += 1
    #    xor &= xor - 1
    #    
    
    # ---------------------
    
    # cool stackexchange strategy:
    
    # Here it is: https://stackoverflow.com/questions/9829578/fast-way-of-counting-non-zero-bits-in-positive-integer/9830282#9830282
    
    # n = struct.unpack( '!Q', perceptual_hash1 )[0] ^ struct.unpack( '!Q', perceptual_hash2 )[0]
    
    # n = ( n & 0x5555555555555555 ) + ( ( n & 0xAAAAAAAAAAAAAAAA ) >> 1 ) # 10101010, 01010101
    # n = ( n & 0x3333333333333333 ) + ( ( n & 0xCCCCCCCCCCCCCCCC ) >> 2 ) # 11001100, 00110011
    # n = ( n & 0x0F0F0F0F0F0F0F0F ) + ( ( n & 0xF0F0F0F0F0F0F0F0 ) >> 4 ) # 11110000, 00001111
    # n = ( n & 0x00FF00FF00FF00FF ) + ( ( n & 0xFF00FF00FF00FF00 ) >> 8 ) # etc...
    # n = ( n & 0x0000FFFF0000FFFF ) + ( ( n & 0xFFFF0000FFFF0000 ) >> 16 )
    # n = ( n & 0x00000000FFFFFFFF ) + ( n >> 32 )
    
    # you technically are going n & 0xFFFFFFFF00000000 at the end, but that's a no-op with the >> 32 afterwards, so can be omitted
    
    # ---------------------
    
    # lame but about 9% faster than the stackexchange using timeit (0.1286 vs 0.1383 for 100000 comparisons) (when including the xor and os.urandom to generate phashes)
    
    # n = struct.unpack( '!Q', perceptual_hash1 )[0] ^ struct.unpack( '!Q', perceptual_hash2 )[0]
    
    # return bin( n ).count( '1' )
    
    # collapsed because that also boosts by another 1% or so
    
    return bin( struct.unpack( '!Q', perceptual_hash1 )[0] ^ struct.unpack( '!Q', perceptual_hash2 )[0] ).count( '1' )
    
    # ---------------------
    
    # once python 3.10 rolls around apparently you can just do int.bit_count(), which _may_ be six times faster
    # not sure how that handles signed numbers, but shouldn't matter here
    
    # another option is https://www.valuedlessons.com/2009/01/popcount-in-python-with-benchmarks.html, which is just an array where the byte value is an address on a list to the answer
    
def GetNicelyDivisibleNumberForZoom( zoom, no_bigger_than ):
    
    # it is most convenient to have tiles that line up with the current zoom ratio
    # 768 is a convenient size for meaty GPU blitting, but as a number it doesn't make for nice multiplication
    
    # a 'nice' size is one that divides nicely by our zoom, so that integer translations between canvas and native res aren't losing too much in the float remainder
    
    # the trick of going ( 123456 // 16 ) * 16 to give you a nice multiple of 16 does not work with floats like 1.4 lmao.
    # what we can do instead is phrase 1.4 as 7/5 and use 7 as our int. any number cleanly divisible by 7 is cleanly divisible by 1.4
    
    base_frac = fractions.Fraction( zoom )
    
    denominator_limit = 10000
    
    frac = base_frac
    
    while frac.numerator > no_bigger_than:
        
        frac = base_frac.limit_denominator( denominator_limit )
        
        denominator_limit //= 2
        
        if denominator_limit < 10:
            
            return -1
            
        
    
    if frac.numerator == 0:
        
        return -1
        
    
    return frac.numerator
    

def GetEmptyDataDict():
    
    data = collections.defaultdict( default_dict_list )
    
    return data
    

def GetNonDupeName( original_name: str, disallowed_names: set[ str ], do_casefold: bool = False ):
    
    if do_casefold:
        
        disallowed_names = { name.casefold() for name in disallowed_names }
        
    
    def name_exists( name: str ):
        
        if do_casefold:
            
            return name.casefold() in disallowed_names
            
        else:
            
            return name in disallowed_names
            
        
    
    i = 1
    
    non_dupe_name = original_name
    
    while name_exists( non_dupe_name ):
        
        non_dupe_name = original_name + ' (' + str( i ) + ')'
        
        i += 1
        
    
    return non_dupe_name
    

def GetTypeName( obj_type ):
    
    if hasattr( obj_type, '__name__' ):
        
        return obj_type.__name__
        
    else:
        
        return repr( obj_type )
        
    

def LastShutdownWasBad( db_path, instance ):
    
    path = os.path.join( db_path, instance + '_running' )
    
    if os.path.exists( path ):
        
        return True
        
    else:
        
        return False
        

def MergeKeyToListDicts( key_to_list_dicts ):
    
    result = collections.defaultdict( list )
    
    for key_to_list_dict in key_to_list_dicts:
        
        for ( key, value ) in list(key_to_list_dict.items()): result[ key ].extend( value )
        
    
    return result
    

def Print( text ):
    
    try:
        
        print( str( text ) )
        
    except:
        
        print( repr( text ) )
        
    

ShowText = Print

def PrintException( e, do_wait = True ):
    
    ( etype, value, tb ) = sys.exc_info()
    
    PrintExceptionTuple( etype, value, tb, do_wait = do_wait )
    

def PrintExceptionTuple( etype, value, tb, do_wait = True ):
    
    if etype is None:
        
        etype = HydrusExceptions.UnknownException
        
    
    if etype == HydrusExceptions.ShutdownException:
        
        return
        
    
    if value is None:
        
        value = 'Unknown error'
        
    
    if tb is None:
        
        trace = 'No error trace!'
        
    else:
        
        trace = ''.join( traceback.format_exception( etype, value, tb ) )
        
    
    trace = trace.rstrip()
    
    stack_list = traceback.format_stack()
    
    stack = ''.join( stack_list )
    
    stack = stack.rstrip()
    
    message = f'''================ Exception ================
{etype.__name__}: {value}
================ Traceback ================
{trace}
================== Stack ==================
{stack}
=================== End ==================='''
    
    DebugPrint( '\n' + message )
    
    if do_wait:
        
        time.sleep( 0.2 )
        
    
    return message
    

ShowException = PrintException
ShowExceptionTuple = PrintExceptionTuple

def BaseToHumanBytes( size, sig_figs = 3 ):
    
    #
    #               ░█▓▓▓▓▓▒  ░▒░   ▒   ▒ ░  ░ ░▒ ░░     ░▒  ░  ░▒░ ▒░▒▒▒░▓▓▒▒▓  
    #            ▒▓▒▒▓▒  ░      ░   ▒                ░░       ░░  ░▒▒▒▓▒▒▓▓      
    #             ▓█▓▒░ ▒▒░    ▒░  ▒▓░ ░  ░░░ ░   ░░░▒▒ ░     ░░░  ▒▓▓▓▒▓▓▒      
    #              ▒▒░▒▒░░     ▒░░▒▓░▒░▒░░░░░░░░ ░▒▒▒▓   ░     ░▒▒░ ▒▓▒▓█▒       
    #                ░█▓  ░░░ ▒▒░▒▒   ▒▒▒░░░░▒▒░░▒▒▒░░▒▒ ▒░     ░░░░░░▒█▒        
    #               ░░▒▒ ▒░░▒░▒▒▒░     ░░░▒▒▒░░▒░ ░    ▓▒▒░    ░  ▒█▓░▒░         
    #             ░░░ ░▒ ▓▒░▒░▒           ░▒▒▒▒         ▒▓░ ░  ▒  ▒█▓            
    #           ░░░    ▓░▒▒░░▒   ▒▒▒▒░░    ░░░            ░░░  ▒ ░▒░ ░           
    #         ░▒░      ▓░▒▒░░▒░▒▓▓████▓         ░▒▒▒▒▒   ░▒░░ ▓▒ ▒▒  ░▒░         
    #       ░░░░ ░░    ░░▒░▒░░░    ░░░     ░    ░▒▒▒▒▓█▓ ▒░░░▒▓░▒▒░   ░░░░       
    #       ▒ ░  ░░░░░░ ░▓░▓▒░░░  ░       ░░           ░▒▒░▒▒▒▒░▓░     ░ ░▒░     
    #       ▒░░  ░░░░░░ ▒▒░▒░▒▒░░░░░░            ░░░░░░▒▒░▓▒░▒▒▓░      ░   ░░    
    #   ░░░░▒▒▒░░░  ░░  ▓░▒░░▒▒░                  ░░░░░░ ░▒▒▒▒▓▓  ░  ░ ░░   ▒░░  
    #   ▒▒░   ▒▒░  ░░  ▒▒▒▓░░▒ ░        ░░░░░░░          ░░▒░░▒▓  ░░░░ ░░  ░▒░░▒ 
    # ▒░░   ░ ▒▒  ░░  ▒▓▒▓▒ ▒░░▒▓                      ▓▒░▒▒░░░▓▒  ░░  ░░ ▒▒░  ░░
    # ░  ░▒▒░░▒▒░░  ░▒▒▒▒▒  ▒░░▒▓▒░                  ░▒▓█▒░▒ ░░▒▓▒     ▒▒▒ ▒░▒░  
    # ▒░▒▓▓░░░░░▒▒▒▒░░░▓▒   ▒░ ▒▓░░▒▒░            ░░▒▒░▒▓░ ▒░ ▒░▒▒▒ ░░░░▓   ▒░▒░ 
    # ▒ ▒▒ ▒░░░▒░░    ▒▒    ░░░▒▒░░░░▒▒▒░     ░░▒▒░▒▒░░▒▓▒░▒  ░ ▒░▒▒░░░░░▒░░▒▒▒▒ 
    # ░ ▒▒▒░        ░░▒      ▒░░▒░░░░░▒▒▒▒▒▒▒▒▒▒▓▒░░▒░▒▒░▒▒░   ░ ▒░░░▒░░░░░░░▒▒▒░
    # ▒  ▒▓        ░▒▒      ░▒░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▒░▒▒▒▒▒░░▒░      ▒░   ░▒▒░▒░ ▒  
    # ▒   ▒▒░     ░▒░   ░  ▒░░▒▒░  ░▒▒▒▒ ░▒▒▒░  ▒░▒▒   ▒▒ ▒▒       ▒        ▓░░▒░
    # ░░  ░▒    ░▒▒░   ░ ░▒░░░░   ░░       ░   ▒▒▓▓█▒   ░░▒▓▒░      ▒░     ░▒▒░░░
    # ▒░  ░░▒ ▒▒▒     ░░▒▒░░░   ░ ▒░  ░░▒▒▒▒▒░██▓▒▓██     ▒▓▒▒░  ░   ▒▒   ▒▓▒  ░░
    # ░░▒▒▒▒▒▒░      ░░░   ░    ▒▒░▒  ░▒▒░▓█░ ██▓▓▓▓  ▒   ░▓ ░░▒░     ░▒░ ▒░░░░▒ 
    #   ▒▒░       ░▒▒           ▒▓▒ ▓▓▓▓█▒▓▓▓▒▒▓▓▓▓ ▒▓▒   ▒▒    ░░░     ░▒▒░░░▒░ 
    #      ░   ░░▒▒▓▒▒          ░░▓▓▓███▒▒█▓██▒░░ ▒▒▒▒░   ▒▓     ░▒▒░ ░   ░▒▒▒░  
    # ░  ░░ ░▒▒▒▒▒▓▓▒▒░         ▒▒▒█▓▓▓░ ▓▓▒▓▓▒░░░▒▓▒░░   ▒▒     ░▒█▓░ ░░   ░░░  
    #   ▒░░▒▓▒░▒░ ▒▒ ▒▒░  ░░░░▒▓▓▓▒▓▓▓▓ ▒▓▒▒▓▓░▒▒▒▒▒▒▒▓▒  ▒▒    ░▒▒▒▓▓▒░░▒   ░▒▒▒
    # ▒▒▒░ ▒░ ░░   ▒ ░▓▓▒▒░░░░░░░                       ▓░▒░  ░▓▓▓░  ░▒▓░▒▓▒▓▒▓▓▓
    # ▓░  ▒░  ▒▓   ▓░               ░░░░░░░░░░░▒▒▒▒▒▒▓▓▒ ▒▒▓▓▓▓▓▓▓▓▓░ ▒▓▒▓▓▓▒▓▓▓▓
    #     ░░  ▓▒   ░▒▓▓▒▒▒▓▓▓▒▓▓▓▓▓▓█▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ▓▒▒▒▒▒▓▓▓▓▒▓▓▒▒▒▒▒▓▓▓▓▒ 
    #    ░░░ ▒▒▒▒▓▓░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░▓▒▒▒▒▒▒▒▓▓▓▓▓▓▓▒▒▒▒▒░ ░ 
    #   ░░   ▒▓  ██░▓▓▓▓▓▓▓▓▓▓█▓▓▒▒▒ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░▒▓▒▒▒▒▒▒▒▒▒░▒▒░░▒▒░ ░░░░░
    #   ░▒░░░▒▓   ▓░▒▓▓▓▓▓▓▓▓▓▒      ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▓ ▓░ ▒▒▒▒▒▒▒▒░   ░▒▒▒▒░░░░
    #   ▒▒░ ░▒▓   ▒▓░▓▓▓▓█▓▒      ░▓▓▓▓▓▓▓█▒▓▒ ▒▓▓▓▓▓▒▓░ ▓    ░▒▒░▒░░░░▒▒▒▒▒░░░░░
    # ▓▒▒▒▒▒▒▓▓   ▒▓▒▓▓▓▒░     ░▓▓██▓▓▓█▓▒  ░  ▒▓▓▓▓▒▓▒ ▒▓         ▒ ░▓▓▓▓▒ ░░░░▒
    # ░░▓▓▓▓▒▓▓  ░░▓▓      ░▓████▓▓▓▒▒▒      ▒██▓▒▓█▒   ▓▒         ▒  ░░▒▓▓▒▓▒▒▒ 
    #    ░░▒▒▒▒   ▒▒     ▒▓█▓▒░░          ░▓██▓▒░░░█░   ▓          ▒ ░  ░▓▒▒▓▓▒▓▒
    # ░░░░░ ▒▒    ▓▒ ░░             ▒░░▒▒▓▓▓▒░░ ░█▓█▒  ▒▓          ▒░░  ░▓▒▒     
    # ▒░░░░▒▓▒   ░██          ▒▒▒▒░░▒▓   ▒▒  ░▒░▒███░  ▓▒          ▒░░  ░▓▒░░░░▒ 
    # ░ ░░░▓▒░ ▒█▒▓█░             ░  ▒░  ░░      ▒▓▒   ▓          ░▒    ░▓▓▒░▒░░░
    # ░░▒▒▒▓▓▓▓░▓▓ ██▒    ░▒░▒▒▒▒░░▒ ▒▓           ▓   ▒▓          ▒░   ░░▓▓▒░▒▒▒░
    # ░░▒▒▓█▓░   █ ░█▒      ░ ░ ░▒▒░░▓░   ▓░     ░▓░  █░     ░░   ▒░   ░ ▓▓▒░ ░▒░
    # ░░▒▓░       █ ██          ░ ░▒ ▒    █▓▒▒▒░░▒▒░ ▓▒           ░       ▒▓▒░ ░ 
    #
    
    if size is None:
        
        return 'unknown size'
        
    
    # my definition of sig figs is nonsense here. basically I mean 'can we show decimal places and not look stupid long?'
    
    if size < 1024:
        
        return HydrusNumbers.ToHumanInt( size ) + 'B'
        
    
    suffixes = ( '', 'K', 'M', 'G', 'T', 'P' )
    
    suffix_index = 0
    
    ctx = decimal.getcontext()
    
    # yo, ctx is actually a global, you set prec later, it'll hang around for the /= stuff here lmaaaaaoooooo
    # 188213746 was flipping between 179MB/180MB because the prec = 10 was being triggered later on 180MB
    ctx.prec = 28
    
    d = decimal.Decimal( size )
    
    while d >= 1024:
        
        d /= 1024
        
        suffix_index += 1
        
    
    suffix = suffixes[ suffix_index ]
    
    # ok, if we have 237KB, we still want all 237, even if user said 2 sf
    while d.log10() >= sig_figs:
        
        sig_figs += 1
        
    
    ctx.prec = sig_figs
    ctx.rounding = decimal.ROUND_HALF_EVEN
    
    d = d.normalize( ctx )
    
    try:
        
        # if we have 30, this will be normalised to 3E+1, so we want to quantize it back
        
        ( sign, digits, exp ) = d.as_tuple()
        
        if exp > 0:
            
            ctx.prec = 10 # careful to make precising bigger again though, or we get an error
            
            d = d.quantize( 0 )
            
        
    except:
        
        # blarg
        pass
        
    
    return '{} {}B'.format( d, suffix )
    

ToHumanBytes = BaseToHumanBytes

class HydrusYAMLBase( yaml.YAMLObject ):
    
    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper
    

class Call( object ):
    
    def __init__( self, func, *args, **kwargs ):
        
        self._label = None
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        
    
    def __call__( self ):
        
        return self._func( *self._args, **self._kwargs )
        
    
    def __repr__( self ):
        
        label = self._GetLabel()
        
        return 'Call: {}'.format( label )
        
    
    def _GetLabel( self ) -> str:
        
        if self._label is None:
            
            # this can actually cause an error with Qt objects that are dead or from the wrong thread, wew!
            label = '{}( {}, {} )'.format( self._func, self._args, self._kwargs )
            
        else:
            
            label = self._label
            
        
        return label
        
    
    def GetLabel( self ) -> str:
        
        return self._GetLabel()
        
    
    def SetLabel( self, label: str ):
        
        self._label = label
        
    
