import collections
import cProfile
import decimal
import fractions
import io
import itertools
import os
import pstats
import psutil
import random
import re
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import traceback
import typing
import yaml

from hydrus.core import HydrusBoot
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusText

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
    
def BytesToNoneOrHex( b: typing.Optional[ bytes ] ):
    
    if b is None:
        
        return None
        
    else:
        
        return b.hex()
        
    
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
        
    
def ConvertFloatToPercentage( f ):
    
    return '{:.1f}%'.format( f * 100 )
    
def ConvertIntToPixels( i ):
    
    if i == 1: return 'pixels'
    elif i == 1000: return 'kilopixels'
    elif i == 1000000: return 'megapixels'
    else: return 'megapixels'
    
def ConvertIndexToPrettyOrdinalString( index: int ):
    
    if index >= 0:
        
        return ConvertIntToPrettyOrdinalString( index + 1 )
        
    else:
        
        return ConvertIntToPrettyOrdinalString( index )
        
    
def ConvertIntToPrettyOrdinalString( num: int ):
    
    if num == 0:
        
        return 'unknown position'
        
    
    tens = ( abs( num ) % 100 ) // 10
    
    if tens == 1:
        
        ordinal = 'th'
        
    else:
        
        remainder = abs( num ) % 10
        
        if remainder == 1:
            
            ordinal = 'st'
            
        elif remainder == 2:
            
            ordinal = 'nd'
            
        elif remainder == 3:
            
            ordinal = 'rd'
            
        else:
            
            ordinal = 'th'
            
        
    
    s = '{}{}'.format( ToHumanInt( abs( num ) ), ordinal )
    
    if num < 0:
        
        if num == -1:
            
            s = 'last'
            
        else:
            
            s = '{} from last'.format( s )
            
        
    
    return s
    
def ConvertIntToUnit( unit ):
    
    if unit == 1: return 'B'
    elif unit == 1024: return 'KB'
    elif unit == 1048576: return 'MB'
    elif unit == 1073741824: return 'GB'
    
def ConvertMillisecondsToPrettyTime( ms ):
    
    hours = ms // 3600000
    
    if hours == 1: hours_result = '1 hour'
    else: hours_result = str( hours ) + ' hours'
    
    ms = ms % 3600000
    
    minutes = ms // 60000
    
    if minutes == 1: minutes_result = '1 minute'
    else: minutes_result = str( minutes ) + ' minutes'
    
    ms = ms % 60000
    
    seconds = ms // 1000
    
    if seconds == 1: seconds_result = '1 second'
    else: seconds_result = str( seconds ) + ' seconds'
    
    detailed_seconds = ms / 1000
    
    detailed_seconds_result = '{:.1f} seconds'.format( detailed_seconds )
    
    ms = ms % 1000
    
    if hours > 0: return hours_result + ' ' + minutes_result
    
    if minutes > 0: return minutes_result + ' ' + seconds_result
    
    if seconds > 0: return detailed_seconds_result
    
    ms = int( ms )
    
    if ms == 1: milliseconds_result = '1 millisecond'
    else: milliseconds_result = '{} milliseconds'.format( ms )
    
    return milliseconds_result
    
def ConvertNumericalRatingToPrettyString( lower, upper, rating, rounded_result = False, out_of = True ):
    
    rating_converted = ( rating * ( upper - lower ) ) + lower
    
    if rounded_result:
        
        rating_converted = round( rating_converted )
        
    
    s = '{:.2f}'.format( rating_converted )
    
    if out_of and lower in ( 0, 1 ):
        
        s += '/{:.2f}'.format( upper )
        
    
    return s
    
def ConvertPixelsToInt( unit ):
    
    if unit == 'pixels': return 1
    elif unit == 'kilopixels': return 1000
    elif unit == 'megapixels': return 1000000
    
def ConvertPrettyStringsToUglyNamespaces( pretty_strings ):
    
    result = { s for s in pretty_strings if s != 'no namespace' }
    
    if 'no namespace' in pretty_strings: result.add( '' )
    
    return result
    
def ConvertResolutionToPrettyString( resolution ):
    
    if resolution is None:
        
        return 'no resolution'
        
    
    if not isinstance( resolution, tuple ):
        
        try:
            
            resolution = tuple( resolution )
            
        except:
            
            return 'broken resolution'
            
        
    
    if resolution in HC.NICE_RESOLUTIONS:
        
        return HC.NICE_RESOLUTIONS[ resolution ]
        
    
    ( width, height ) = resolution
    
    return '{}x{}'.format( ToHumanInt( width ), ToHumanInt( height ) )
    
def ConvertStatusToPrefix( status ):
    
    if status == HC.CONTENT_STATUS_CURRENT: return ''
    elif status == HC.CONTENT_STATUS_PENDING: return '(+) '
    elif status == HC.CONTENT_STATUS_PETITIONED: return '(-) '
    elif status == HC.CONTENT_STATUS_DELETED: return '(X) '
    
def TimeDeltaToPrettyTimeDelta( seconds, show_seconds = True ):
    
    if seconds is None:
        
        return 'per month'
        
    
    if seconds == 0:
        
        return '0 seconds'
        
    
    if seconds < 0:
        
        seconds = abs( seconds )
        
    
    if seconds >= 60:
        
        seconds = int( seconds )
        
        MINUTE = 60
        HOUR = 60 * MINUTE
        DAY = 24 * HOUR
        MONTH = 30 * DAY
        YEAR = 365 * DAY
        
        lines = []
        
        lines.append( ( 'year', YEAR ) )
        lines.append( ( 'month', MONTH ) )
        lines.append( ( 'day', DAY ) )
        lines.append( ( 'hour', HOUR ) )
        lines.append( ( 'minute', MINUTE ) )
        
        if show_seconds:
            
            lines.append( ( 'second', 1 ) )
            
        
        result_components = []
        
        for ( time_string, duration ) in lines:
            
            time_quantity = seconds // duration
            
            seconds %= duration
            
            if time_quantity > 0:
                
                s = ToHumanInt( time_quantity ) + ' ' + time_string
                
                if time_quantity > 1:
                    
                    s += 's'
                    
                
                result_components.append( s )
                
                if len( result_components ) == 2: # we now have 1 month 2 days
                    
                    break
                    
                
            else:
                
                if len( result_components ) > 0: # something like '1 year' -- in which case we do not care about the days and hours
                    
                    break
                    
                
            
        
        result = ' '.join( result_components )
        
    elif seconds > 1:
        
        if int( seconds ) == seconds:
            
            result = ToHumanInt( seconds ) + ' seconds'
            
        else:
            
            result = '{:.1f} seconds'.format( seconds )
            
        
    elif seconds == 1:
        
        result = '1 second'
        
    elif seconds > 0.1:
        
        result = '{} milliseconds'.format( int( seconds * 1000 ) )
        
    elif seconds > 0.01:
        
        result = '{:.1f} milliseconds'.format( int( seconds * 1000 ) )
        
    elif seconds > 0.001:
        
        result = '{:.2f} milliseconds'.format( int( seconds * 1000 ) )
        
    else:
        
        result = '{} microseconds'.format( int( seconds * 1000000 ) )
        
    
    return result
    
def ConvertTimestampToPrettyExpires( timestamp ):
    
    if timestamp is None:
        
        return 'does not expire'
        
    
    if timestamp == 0:
        
        return 'unknown expiration'
        
    
    try:
        
        time_delta_string = TimestampToPrettyTimeDelta( timestamp )
        
        if TimeHasPassed( timestamp ):
            
            return 'expired ' + time_delta_string
            
        else:
            return 'expires ' + time_delta_string
            
        
    except:
        
        return 'unparseable time {}'.format( timestamp )
        
    
def ConvertTimestampToPrettyTime( timestamp, in_utc = False, include_24h_time = True ):
    
    if timestamp is None:
        
        return 'unknown time'
        
    
    if include_24h_time:
        
        phrase = '%Y-%m-%d %H:%M:%S'
        
    else:
        
        phrase = '%Y-%m-%d'
        
    
    try:
        
        if in_utc:
            
            struct_time = time.gmtime( timestamp )
            
            phrase = phrase + ' UTC'
            
        else:
            
            struct_time = time.localtime( timestamp )
            
        
        return time.strftime( phrase, struct_time )
        
    except:
        
        return 'unparseable time {}'.format( timestamp )
        
    
def BaseTimestampToPrettyTimeDelta( timestamp, just_now_string = 'now', just_now_threshold = 3, history_suffix = ' ago', show_seconds = True, no_prefix = False ):
    
    if timestamp is None:
        
        return 'at an unknown time'
        
    
    if not show_seconds:
        
        just_now_threshold = max( just_now_threshold, 60 )
        
    
    try:
        
        time_delta = abs( timestamp - GetNow() )
        
        if time_delta <= just_now_threshold:
            
            return just_now_string
            
        
        time_delta_string = TimeDeltaToPrettyTimeDelta( time_delta, show_seconds = show_seconds )
        
        if TimeHasPassed( timestamp ):
            
            return '{}{}'.format( time_delta_string, history_suffix )
            
        else:
            
            if no_prefix:
                
                return time_delta_string
                
            else:
                
                return 'in ' + time_delta_string
                
            
        
    except:
        
        return 'unparseable time {}'.format( timestamp )
        
    
TimestampToPrettyTimeDelta = BaseTimestampToPrettyTimeDelta

def ConvertUglyNamespaceToPrettyString( namespace ):
    
    if namespace is None or namespace == '':
        
        return 'no namespace'
        
    else:
        
        return namespace
        
    
def ConvertUglyNamespacesToPrettyStrings( namespaces ):
    
    namespaces = sorted( namespaces )
    
    result = [ ConvertUglyNamespaceToPrettyString( namespace ) for namespace in namespaces ]
    
    return result
    
def ConvertUnitToInt( unit ):
    
    if unit == 'B': return 1
    elif unit == 'KB': return 1024
    elif unit == 'MB': return 1048576
    elif unit == 'GB': return 1073741824
    
def ConvertValueRangeToBytes( value, range ):
    
    return ToHumanBytes( value ) + '/' + ToHumanBytes( range )
    
def ConvertValueRangeToPrettyString( value, range ):
    
    return ToHumanInt( value ) + '/' + ToHumanInt( range )
    
def ConvertValueRangeToScanbarTimestampsMS( value_ms, range_ms ):
    
    value_ms = int( round( value_ms ) )
    
    range_hours = range_ms // 3600000
    value_hours = value_ms // 3600000
    range_minutes = ( range_ms % 3600000 ) // 60000
    value_minutes = ( value_ms % 3600000 ) // 60000
    range_seconds = ( range_ms % 60000 ) // 1000
    value_seconds = ( value_ms % 60000 ) // 1000
    range_ms = range_ms % 1000
    value_ms = value_ms % 1000
    
    if range_hours > 0:
        
        # 0:01:23.033/1:12:57.067
        
        time_phrase = '{}:{:0>2}:{:0>2}.{:0>3}'
        
        args = ( value_hours, value_minutes, value_seconds, value_ms, range_hours, range_minutes, range_seconds, range_ms )
        
    elif range_minutes > 0:
        
        # 01:23.033/12:57.067 or 0:23.033/1:57.067
        
        if range_minutes > 9:
            
            time_phrase = '{:0>2}:{:0>2}.{:0>3}'
            
        else:
            
            time_phrase = '{:0>1}:{:0>2}.{:0>3}'
            
        
        args = ( value_minutes, value_seconds, value_ms, range_minutes, range_seconds, range_ms )
        
    else:
        
        # 23.033/57.067 or 3.033/7.067 or 0.033/0.067
        
        if range_seconds > 9:
            
            time_phrase = '{:0>2}.{:0>3}'
            
        else:
            
            time_phrase = '{:0>1}.{:0>3}'
            
        
        args = ( value_seconds, value_ms, range_seconds, range_ms )
        
    
    full_phrase = '{}/{}'.format( time_phrase, time_phrase )
    
    result = full_phrase.format( *args )
    
    return result
    
def DebugPrint( debug_info ):
    
    Print( debug_info )
    
    sys.stdout.flush()
    sys.stderr.flush()
    
def DedupeList( xs ):
    
    xs_seen = set()
    
    xs_return = []
    
    for x in xs:
        
        if x in xs_seen:
            
            continue
            
        
        xs_return.append( x )
        
        xs_seen.add( x )
        
    
    return xs_return
    
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
    
def GetNonDupeName( original_name, disallowed_names ):
    
    i = 1
    
    non_dupe_name = original_name
    
    while non_dupe_name in disallowed_names:
        
        non_dupe_name = original_name + ' (' + str( i ) + ')'
        
        i += 1
        
    
    return non_dupe_name
    
def GetNow():
    
    return int( time.time() )
    
def GetNowFloat():
    
    return time.time()
    
def GetNowPrecise():
    
    return time.perf_counter()
    
def GetSiblingProcessPorts( db_path, instance ):
    
    path = os.path.join( db_path, instance + '_running' )
    
    if os.path.exists( path ):
        
        with open( path, 'r', encoding = 'utf-8' ) as f:
            
            file_text = f.read()
            
            try:
                
                ( pid, create_time ) = HydrusText.DeserialiseNewlinedTexts( file_text )
                
                pid = int( pid )
                create_time = float( create_time )
                
            except ValueError:
                
                return None
                
            
            try:
                
                if psutil.pid_exists( pid ):
                    
                    ports = []
                    
                    p = psutil.Process( pid )
                    
                    for conn in p.connections():
                        
                        if conn.status == 'LISTEN':
                            
                            ports.append( int( conn.laddr[1] ) )
                            
                        
                    
                    return ports
                    
                
            except psutil.Error:
                
                return None
                
            
        
    
    return None
    
def GetSubprocessEnv():
    
    if HG.subprocess_report_mode:
        
        env = os.environ.copy()
        
        ShowText( 'Your unmodified env is: {}'.format( env ) )
        
    
    env = os.environ.copy()
    
    if HydrusBoot.ORIGINAL_PATH is not None:
        
        env[ 'PATH' ] = HydrusBoot.ORIGINAL_PATH
        
    
    if HC.RUNNING_FROM_FROZEN_BUILD:
        
        # let's make a proper env for subprocess that doesn't have pyinstaller woo woo in it
        
        changes_made = False
        
        orig_swaperoo_strings = [ 'LD_LIBRARY_PATH', 'XDG_DATA_DIRS'  ]
        ok_to_remove_absent_orig = [ 'LD_LIBRARY_PATH' ]
        
        for key in orig_swaperoo_strings:
            
            orig_key = '{}_ORIG'.format( key )
            
            if orig_key in env:
                
                env[ key ] = env[ orig_key ]
                
                changes_made = True
                
            elif key in env and key in ok_to_remove_absent_orig:
                
                del env[ key ]
                
                changes_made = True
                
            
        
        remove_if_hydrus_base_dir = [ 'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'SSL_CERT_FILE' ]
        hydrus_base_dir = HG.controller.GetDBDir()
        
        for key in remove_if_hydrus_base_dir:
            
            if key in env and env[ key ].startswith( hydrus_base_dir ):
                
                del env[ key ]
                
                changes_made = True
                
            
        
        if ( HC.PLATFORM_LINUX or HC.PLATFORM_MACOS ):
            
            if 'PATH' in env:
                
                # fix for pyinstaller, which drops this stuff for some reason and hence breaks ffmpeg
                
                path = env[ 'PATH' ]
                
                path_locations = set( path.split( ':' ) )
                desired_path_locations = [ '/usr/bin', '/usr/local/bin' ]
                
                for desired_path_location in desired_path_locations:
                    
                    if desired_path_location not in path_locations:
                        
                        path = desired_path_location + ':' + path
                        
                        env[ 'PATH' ] = path
                        
                        changes_made = True
                        
                    
                
            
            if 'XDG_DATA_DIRS' in env:
                
                xdg_data_dirs = env[ 'XDG_DATA_DIRS' ]
                
                # pyinstaller can just replace this nice usually long str with multiple paths with base_dir/share
                # absent the _orig above to rescue this, we'll populate with basic
                if ':' not in xdg_data_dirs and HC.BASE_DIR in xdg_data_dirs:
                    
                    xdg_data_dirs = '/usr/local/share:/usr/share'
                    
                    changes_made = True
                    
                
            
        
        if not changes_made:
            
            env = None
            
        
    else:
        
        env = None
        
    
    return env
    
def GetSubprocessHideTerminalStartupInfo():
    
    if HC.PLATFORM_WINDOWS:
        
        # This suppresses the terminal window that tends to pop up when calling ffmpeg or whatever
        
        startupinfo = subprocess.STARTUPINFO()
        
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
    else:
        
        startupinfo = None
        
    
    return startupinfo
    
def GetSubprocessKWArgs( hide_terminal = True, text = False ):
    
    sbp_kwargs = {}
    
    sbp_kwargs[ 'env' ] = GetSubprocessEnv()
    
    if text:
        
        # probably need to override the stdXXX pipes with i/o encoding wrappers in the case of 3.5 here
        
        if sys.version_info.minor >= 6:
            
            sbp_kwargs[ 'encoding' ] = 'utf-8'
            
        
        if sys.version_info.minor >= 7:
            
            sbp_kwargs[ 'text' ] = True
            
        else:
            
            sbp_kwargs[ 'universal_newlines' ] = True
            
        
    
    if hide_terminal:
        
        sbp_kwargs[ 'startupinfo' ] = GetSubprocessHideTerminalStartupInfo()
        
    
    if HG.subprocess_report_mode:
        
        message = 'KWargs are: {}'.format( sbp_kwargs )
        
        ShowText( message )
        
    
    return sbp_kwargs
    
def GetTimeDeltaSinceTime( timestamp ):
    
    time_since = timestamp - GetNow()
    
    result = min( time_since, 0 )
    
    return - result
    
def GetTimeDeltaUntilTime( timestamp ):
    
    time_remaining = timestamp - GetNow()
    
    return max( time_remaining, 0 )
    
def GetTimeDeltaUntilTimeFloat( timestamp ):
    
    time_remaining = timestamp - GetNowFloat()
    
    return max( time_remaining, 0.0 )
    
def GetTimeDeltaUntilTimePrecise( t ):
    
    time_remaining = t - GetNowPrecise()
    
    return max( time_remaining, 0.0 )
    
def GetTypeName( obj_type ):
    
    if hasattr( obj_type, '__name__' ):
        
        return obj_type.__name__
        
    else:
        
        return repr( obj_type )
        
    
def GenerateHumanTextSortKey():
    """Solves the 19, 20, 200, 21, 22 issue when sorting 'Page 21.jpg' type strings.
    Breaks the string into groups of text and int (i.e. ( "Page ", 21, ".jpg" ) )."""
    
    int_convert = lambda t: int( t ) if t.isdecimal() else t
    
    split_alphanum = lambda t: tuple( ( int_convert( sub_t ) for sub_t in re.split( '([0-9]+)', t.lower() ) ) )
    
    return split_alphanum
    
HumanTextSortKey = GenerateHumanTextSortKey()

def HumanTextSort( texts ):
    
    texts.sort( key = HumanTextSortKey ) 
    
def IntelligentMassIntersect( sets_to_reduce ):
    
    answer = None
    
    for set_to_reduce in sets_to_reduce:
        
        if len( set_to_reduce ) == 0:
            
            return set()
            
        
        if answer is None:
            
            answer = set( set_to_reduce )
            
        else:
            
            if len( answer ) == 0:
                
                return set()
                
            else:
                
                answer.intersection_update( set_to_reduce )
                
            
        
    
    if answer is None:
        
        return set()
        
    else:
        
        return answer
        
    
def IsAlreadyRunning( db_path, instance ):
    
    path = os.path.join( db_path, instance + '_running' )
    
    if os.path.exists( path ):
        
        with open( path, 'r', encoding = 'utf-8' ) as f:
            
            file_text = f.read()
            
            try:
                
                ( pid, create_time ) = HydrusText.DeserialiseNewlinedTexts( file_text )
                
                pid = int( pid )
                create_time = float( create_time )
                
            except ValueError:
                
                return False
                
            
            try:
                
                me = psutil.Process()
                
                if me.pid == pid and me.create_time() == create_time:
                    
                    # this is me! there is no conflict, lol!
                    # this happens when a linux process restarts with os.execl(), for instance (unlike Windows, it keeps its pid)
                    
                    return False
                    
                
                if psutil.pid_exists( pid ):
                    
                    p = psutil.Process( pid )
                    
                    if p.create_time() == create_time and p.is_running():
                        
                        return True
                        
                    
                
            except psutil.Error:
                
                return False
                
            
        
    
    return False
    
def IterateHexPrefixes():
    
    hex_chars = '0123456789abcdef'
    
    for ( one, two ) in itertools.product( hex_chars, hex_chars ):
        
        prefix = one + two
        
        yield prefix
        
    
def LastShutdownWasBad( db_path, instance ):
    
    path = os.path.join( db_path, instance + '_running' )
    
    if os.path.exists( path ):
        
        return True
        
    else:
        
        return False
        

def MassUnion( lists ):
    
    return { item for item in itertools.chain.from_iterable( lists ) }
    
def MedianPop( population ):
    
    # assume it has at least one and comes sorted
    
    median_index = len( population ) // 2
    
    row = population.pop( median_index )
    
    return row
    
def MergeKeyToListDicts( key_to_list_dicts ):
    
    result = collections.defaultdict( list )
    
    for key_to_list_dict in key_to_list_dicts:
        
        for ( key, value ) in list(key_to_list_dict.items()): result[ key ].extend( value )
        
    
    return result
    
def PartitionIterator( pred: typing.Callable[ [ object ], bool ], stream: typing.Iterable[ object ] ):
    
    ( t1, t2 ) = itertools.tee( stream )
    
    return ( itertools.filterfalse( pred, t1 ), filter( pred, t2 ) )
    
def PartitionIteratorIntoLists( pred: typing.Callable[ [ object ], bool ], stream: typing.Iterable[ object ] ):
    
    ( a, b ) = PartitionIterator( pred, stream )
    
    return ( list( a ), list( b ) )
    
def ParseHashesFromRawHexText( hash_type, hex_hashes_raw ):
    
    hash_type_to_hex_length = {
        'md5' : 32,
        'sha1' : 40,
        'sha256' : 64,
        'sha512' : 128
    }
    
    hex_hashes = HydrusText.DeserialiseNewlinedTexts( hex_hashes_raw )
    
    # convert md5:abcd to abcd
    hex_hashes = [ hex_hash.split( ':' )[-1] for hex_hash in hex_hashes ]
    
    hex_hashes = [ HydrusText.HexFilter( hex_hash ) for hex_hash in hex_hashes ]
    
    expected_hex_length = hash_type_to_hex_length[ hash_type ]
    
    bad_hex_hashes = [ hex_hash for hex_hash in hex_hashes if len( hex_hash ) != expected_hex_length ]
    
    if len( bad_hex_hashes ):
        
        m = 'Sorry, {} hashes should have {} hex characters! These did not:'.format( hash_type, expected_hex_length )
        m += os.linesep * 2
        m += os.linesep.join( ( '{} ({} characters)'.format( bad_hex_hash, len( bad_hex_hash ) ) for bad_hex_hash in bad_hex_hashes ) )
        
        raise Exception( m )
        
    
    hex_hashes = [ hex_hash for hex_hash in hex_hashes if len( hex_hash ) % 2 == 0 ]
    
    hex_hashes = DedupeList( hex_hashes )
    
    hashes = tuple( [ bytes.fromhex( hex_hash ) for hex_hash in hex_hashes ] )
    
    return hashes
    
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
        
        trace = 'No error trace--here is the stack:' + os.linesep + ''.join( traceback.format_stack() )
        
    else:
        
        trace = ''.join( traceback.format_exception( etype, value, tb ) )
        
    
    stack_list = traceback.format_stack()
    
    stack = ''.join( stack_list )
    
    message = str( etype.__name__ ) + ': ' + str( value ) + os.linesep + trace + os.linesep + stack
    
    Print( '' )
    Print( 'Exception:' )
    
    DebugPrint( message )
    
    if do_wait:
        
        time.sleep( 1 )
        
    
ShowException = PrintException
ShowExceptionTuple = PrintExceptionTuple

def Profile( summary, code, g, l, min_duration_ms = 20, show_summary = False ):
    
    profile = cProfile.Profile()
    
    started = GetNowPrecise()
    
    profile.runctx( code, g, l )
    
    finished = GetNowPrecise()
    
    time_took = finished - started
    time_took_ms = int( time_took * 1000.0 )
    
    if time_took_ms > min_duration_ms:
        
        output = io.StringIO()
        
        stats = pstats.Stats( profile, stream = output )
        
        stats.strip_dirs()
        
        stats.sort_stats( 'tottime' )
        
        output.write( 'Stats' )
        output.write( os.linesep * 2 )
        
        stats.print_stats()
        
        output.write( 'Callers' )
        output.write( os.linesep * 2 )
        
        stats.print_callers()
        
        output.seek( 0 )
        
        profile_text = output.read()
        
        with HG.profile_counter_lock:
            
            HG.profile_slow_count += 1
            
        
        if show_summary:
            
            ShowText( summary )
            
        
        HG.controller.PrintProfile( summary, profile_text = profile_text )
        
    else:
        
        with HG.profile_counter_lock:
            
            HG.profile_fast_count += 1
            
        
        if show_summary:
            
            HG.controller.PrintProfile( summary )
            
        
    
def PullNFromIterator( iterator, n ):
    
    chunk = []
    
    for item in iterator:
        
        chunk.append( item )
        
        if len( chunk ) == n:
            
            return chunk
            
        
    
    return chunk
    
def RandomPop( population ):
    
    random_index = random.randint( 0, len( population ) - 1 )
    
    row = population.pop( random_index )
    
    return row
    
def RecordRunningStart( db_path, instance ):
    
    path = os.path.join( db_path, instance + '_running' )
    
    record_string = ''
    
    try:
        
        me = psutil.Process()
        
        record_string += str( me.pid )
        record_string += os.linesep
        record_string += str( me.create_time() )
        
    except psutil.Error:
        
        return
        
    
    with open( path, 'w', encoding = 'utf-8' ) as f:
        
        f.write( record_string )
        
    
def RestartProcess():
    
    time.sleep( 1 ) # time for ports to unmap
    
    exe = sys.executable
    me = sys.argv[0]
    
    if HC.RUNNING_FROM_SOURCE:
        
        # exe is python's exe, me is the script
        
        args = [ sys.executable ] + sys.argv
        
    else:
        
        # we are running a frozen release--both exe and me are the built exe
        
        # wrap it in quotes because pyinstaller passes it on as raw text, breaking any path with spaces :/
        if not me.startswith( '"' ):
            
            me = '"{}"'.format( me )
            
        
        args = [ me ] + sys.argv[1:]
        
    
    os.execv( exe, args )
    
def SampleSetByGettingFirst( s: set, n ):
    
    # sampling from a big set can be slow, so if we don't care about super random, let's just rip off the front and let __hash__ be our random
    
    n = min( len( s ), n )
    
    sample = set()
    
    if n == 0:
        
        return sample
        
    
    for ( i, obj ) in enumerate( s ):
        
        sample.add( obj )
        
        if i >= n - 1:
            
            break
            
        
    
    return sample
    
def SetsIntersect( a, b ):
    
    # not a.isdisjoint( b )
    
    if not isinstance( a, set ):
        
        a = set( a )
        
    
    if not isinstance( b, set ):
        
        b = set( b )
        
    
    if len( a ) > len( b ):
        
        ( a, b ) = ( b, a )
        
    
    return True in ( i in b for i in a )
    
def SmoothOutMappingIterator( xs, n ):
    
    # de-spikifies mappings, so if there is ( tag, 20k files ), it breaks that up into manageable chunks
    
    chunk_weight = 0
    chunk = []
    
    for ( tag_item, hash_items ) in xs:
        
        for chunk_of_hash_items in SplitIteratorIntoChunks( hash_items, n ):
            
            yield ( tag_item, chunk_of_hash_items )
            
        
    
def SplayListForDB( xs ):
    
    return '(' + ','.join( ( str( x ) for x in xs ) ) + ')'
    
def SplitIteratorIntoChunks( iterator, n ):
    
    chunk = []
    
    for item in iterator:
        
        chunk.append( item )
        
        if len( chunk ) == n:
            
            yield chunk
            
            chunk = []
            
        
    
    if len( chunk ) > 0:
        
        yield chunk
        
    
def SplitIteratorIntoAutothrottledChunks( iterator, starting_n, precise_time_to_stop ):
    
    n = starting_n
    
    chunk = PullNFromIterator( iterator, n )
    
    while len( chunk ) > 0:
        
        time_work_started = GetNowPrecise()
        
        yield chunk
        
        work_time = GetNowPrecise() - time_work_started
        
        items_per_second = n / work_time
        
        time_remaining = precise_time_to_stop - GetNowPrecise()
        
        if TimeHasPassedPrecise( precise_time_to_stop ):
            
            n = 1
            
        else:
            
            expected_items_in_remaining_time = max( 1, int( time_remaining * items_per_second ) )
            
            quad_speed = n * 4
            
            n = min( quad_speed, expected_items_in_remaining_time )
            
        
        chunk = PullNFromIterator( iterator, n )
        
    
def SplitListIntoChunks( xs, n ):
    
    if isinstance( xs, set ):
        
        xs = list( xs )
        
    
    for i in range( 0, len( xs ), n ):
        
        yield xs[ i : i + n ]
        
    
def SplitMappingIteratorIntoAutothrottledChunks( iterator, starting_n, precise_time_to_stop ):
    
    n = starting_n
    
    chunk_weight = 0
    chunk = []
    
    for ( tag_item, hash_items ) in iterator:
        
        chunk.append( ( tag_item, hash_items ) )
        
        chunk_weight += len( hash_items )
        
        if chunk_weight >= n:
            
            time_work_started = GetNowPrecise()
            
            yield chunk
            
            work_time = GetNowPrecise() - time_work_started
            
            chunk_weight = 0
            chunk = []
            
            items_per_second = n / work_time
            
            time_remaining = precise_time_to_stop - GetNowPrecise()
            
            if TimeHasPassedPrecise( precise_time_to_stop ):
                
                n = 1
                
            else:
                
                expected_items_in_remaining_time = max( 1, int( time_remaining * items_per_second ) )
                
                quad_speed = n * 4
                
                n = min( quad_speed, expected_items_in_remaining_time )
                
            
        
    
    if len( chunk ) > 0:
        
        yield chunk
        
    
def TimeHasPassed( timestamp ):
    
    if timestamp is None:
        
        return False
        
    
    return GetNow() > timestamp
    
def TimeHasPassedFloat( timestamp ):
    
    return GetNowFloat() > timestamp
    
def TimeHasPassedPrecise( precise_timestamp ):
    
    return GetNowPrecise() > precise_timestamp
    
def TimeUntil( timestamp ):
    
    return timestamp - GetNow()
    
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
        
        return ToHumanInt( size ) + 'B'
        
    
    suffixes = ( '', 'K', 'M', 'G', 'T', 'P' )
    
    suffix_index = 0
    
    d = decimal.Decimal( size )
    
    while d >= 1024:
        
        d /= 1024
        
        suffix_index += 1
        
    
    suffix = suffixes[ suffix_index ]
    
    ctx = decimal.getcontext()
    
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
        
    
    return '{}{}B'.format( d, suffix )
    
ToHumanBytes = BaseToHumanBytes

def ToHumanInt( num ):
    
    num = int( num )
    
    # this got stomped on by mpv, which resets locale
    #text = locale.format_string( '%d', num, grouping = True )
    
    text = '{:,}'.format( num )
    
    return text
    
def WaitForProcessToFinish( p, timeout ):
    
    started = GetNow()
    
    while p.poll() is None:
        
        if TimeHasPassed( started + timeout ):
            
            p.kill()
            
            raise Exception( 'Process did not finish within ' + ToHumanInt( timeout ) + ' seconds!' )
            
        
        time.sleep( 2 )
        
    
class HydrusYAMLBase( yaml.YAMLObject ):
    
    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper
    
class BigJobPauser( object ):
    
    def __init__( self, period = 10, wait_time = 0.1 ):
        
        self._period = period
        self._wait_time = wait_time
        
        self._next_pause = GetNow() + self._period
        
    
    def Pause( self ):
        
        if TimeHasPassed( self._next_pause ):
            
            time.sleep( self._wait_time )
            
            self._next_pause = GetNow() + self._period
            
        
    
class Call( object ):
    
    def __init__( self, func, *args, **kwargs ):
        
        self._label = None
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        
    
    def __call__( self ):
        
        self._func( *self._args, **self._kwargs )
        
    
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
        
    
class ContentUpdate( object ):
    
    def __init__( self, data_type, action, row, reason = None ):
        
        self._data_type = data_type
        self._action = action
        self._row = row
        self._reason = reason
        
    
    def __eq__( self, other ):
        
        if isinstance( other, ContentUpdate ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return hash( ( self._data_type, self._action, repr( self._row ) ) )
        
    
    def __repr__( self ):
        
        return 'Content Update: ' + str( ( self._data_type, self._action, self._row, self._reason ) )
        
    
    def GetAction( self ):
        
        return self._action
        
    
    def GetDataType( self ):
        
        return self._data_type
        
    
    def GetHashes( self ):
        
        hashes = set()
        
        if self._data_type == HC.CONTENT_TYPE_FILES:
            
            if self._action == HC.CONTENT_UPDATE_ADVANCED:
                
                ( sub_action, possible_hashes ) = self._row
                
                if possible_hashes is None:
                    
                    hashes = set()
                    
                else:
                    
                    hashes = possible_hashes
                    
                
            elif self._action == HC.CONTENT_UPDATE_ADD:
                
                ( file_info_manager, timestamp ) = self._row
                
                hashes = { file_info_manager.hash }
                
            else:
                
                hashes = self._row
                
            
        elif self._data_type == HC.CONTENT_TYPE_DIRECTORIES:
            
            hashes = set()
            
        elif self._data_type == HC.CONTENT_TYPE_URLS:
            
            ( urls, hashes ) = self._row
            
        elif self._data_type == HC.CONTENT_TYPE_MAPPINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADVANCED:
                
                hashes = set()
                
            else:
                
                ( tag, hashes ) = self._row
                
            
        elif self._data_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            hashes = set()
            
        elif self._data_type == HC.CONTENT_TYPE_RATINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADD:
                
                ( rating, hashes ) = self._row
                
            
        elif self._data_type == HC.CONTENT_TYPE_NOTES:
            
            if self._action == HC.CONTENT_UPDATE_SET:
                
                ( hash, name, note ) = self._row
                
                hashes = { hash }
                
            elif self._action == HC.CONTENT_UPDATE_DELETE:
                
                ( hash, name ) = self._row
                
                hashes = { hash }
                
            
        elif self._data_type == HC.CONTENT_TYPE_FILE_VIEWING_STATS:
            
            if self._action == HC.CONTENT_UPDATE_ADD:
                
                ( hash, canvas_type, view_timestamp, views_delta, viewtime_delta ) = self._row
                
                hashes = { hash }
                
            elif self._action == HC.CONTENT_UPDATE_DELETE:
                
                hashes = self._row
                
            
        
        if not isinstance( hashes, set ):
            
            hashes = set( hashes )
            
        
        return hashes
        
    
    def GetReason( self ):
        
        if self._reason is None:
            
            return 'No reason given.'
            
        else:
            
            return self._reason
            
        
    
    def GetRow( self ):
        
        return self._row
        
    
    def GetWeight( self ):
        
        return len( self.GetHashes() )
        
    
    def HasReason( self ):
        
        return self._reason is not None
        
    
    def IsInboxRelated( self ):
        
        return self._action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_INBOX )
        
    
    def SetRow( self, row ):
        
        self._row = row
        
    
    def ToTuple( self ):
        
        return ( self._data_type, self._action, self._row )
        
    
class JobDatabase( object ):
    
    def __init__( self, job_type, synchronous, action, *args, **kwargs ):
        
        self._type = job_type
        self._synchronous = synchronous
        self._action = action
        self._args = args
        self._kwargs = kwargs
        
        self._result_ready = threading.Event()
        
    
    def __str__( self ):
        
        return 'DB Job: {}'.format( self.ToString() )
        
    
    def _DoDelayedResultRelief( self ):
        
        pass
        
    
    def GetCallableTuple( self ):
        
        return ( self._action, self._args, self._kwargs )
        
    
    def GetResult( self ):
        
        time.sleep( 0.00001 ) # this one neat trick can save hassle on superquick jobs as event.wait can be laggy
        
        while True:
            
            if self._result_ready.wait( 2 ) == True:
                
                break
                
            elif HG.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application quit before db could serve result!' )
                
            
            self._DoDelayedResultRelief()
            
        
        if isinstance( self._result, Exception ):
            
            e = self._result
            
            raise e
            
        else:
            
            return self._result
            
        
    
    def GetType( self ):
        
        return self._type
        
    
    def IsSynchronous( self ):
        
        return self._synchronous
        
    
    def PutResult( self, result ):
        
        self._result = result
        
        self._result_ready.set()
        
    
    def ToString( self ):
        
        return '{} {}'.format( self._type, self._action )
        
    
class ServiceUpdate( object ):
    
    def __init__( self, action, row = None ):
        
        self._action = action
        self._row = row
        
    
    def ToTuple( self ):
        
        return ( self._action, self._row )
        
    
