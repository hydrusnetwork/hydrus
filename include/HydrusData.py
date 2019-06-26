import bs4
import collections
import cProfile
import io
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
from . import HydrusText
import locale
import os
import pstats
import psutil
import random
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import traceback
import yaml
import itertools

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
    
def CalculateScoreFromRating( count, rating ):
    
    # http://www.evanmiller.org/how-not-to-sort-by-average-rating.html
    
    positive = count * rating
    negative = count * ( 1.0 - rating )
    
    # positive + negative = count
    
    # I think I've parsed this correctly from the website! Not sure though!
    score = ( ( positive + 1.9208 ) / count - 1.96 * ( ( ( positive * negative ) / count + 0.9604 ) ** 0.5 ) / count ) / ( 1 + 3.8416 / count )
    
    return score
    
def CleanRunningFile( db_path, instance ):
    
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
    
def ConvertIntToPrettyOrdinalString( num ):
    
    remainder = num % 10
    
    if remainder == 1:
        
        ordinal = 'st'
        
    elif remainder == 2:
        
        ordinal = 'nd'
        
    elif remainder == 3:
        
        ordinal = 'rd'
        
    else:
        
        ordinal = 'th'
        
    
    return ToHumanInt( num ) + ordinal
    
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
    
    ( width, height ) = resolution
    
    return ToHumanInt( width ) + 'x' + ToHumanInt( height )
    
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
        YEAR = 12 * MONTH
        
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
        
    
def ConvertTimestampToPrettyTime( timestamp, in_gmt = False, include_24h_time = True ):
    
    if timestamp is None:
        
        return 'no time given'
        
    
    if include_24h_time:
        
        phrase = '%Y/%m/%d %H:%M:%S'
        
    else:
        
        phrase = '%Y/%m/%d'
        
    
    try:
        
        if in_gmt:
            
            struct_time = time.gmtime( timestamp )
            
            phrase = phrase + ' GMT'
            
        else:
            
            struct_time = time.localtime( timestamp )
            
        
        return time.strftime( phrase, struct_time )
        
    except:
        
        return 'unparseable time {}'.format( timestamp )
        
    
def TimestampToPrettyTimeDelta( timestamp, just_now_string = 'now', just_now_threshold = 3, show_seconds = True ):
    
    if timestamp is None:
        
        timestamp = 0
        
    
    if HG.client_controller.new_options.GetBoolean( 'always_show_iso_time' ):
        
        return ConvertTimestampToPrettyTime( timestamp )
        
    
    if not show_seconds:
        
        just_now_threshold = max( just_now_threshold, 60 )
        
    
    try:
        
        time_delta = abs( timestamp - GetNow() )
        
        if time_delta <= just_now_threshold:
            
            return just_now_string
            
        
        time_delta_string = TimeDeltaToPrettyTimeDelta( time_delta, show_seconds = show_seconds )
        
        if TimeHasPassed( timestamp ):
            
            return time_delta_string + ' ago'
            
        else:
            
            return 'in ' + time_delta_string
            
        
    except:
        
        return 'unparseable time {}'.format( timestamp )
        
    
def ConvertUglyNamespaceToPrettyString( namespace ):
    
    if namespace is None or namespace == '':
        
        return 'no namespace'
        
    else:
        
        return namespace
        
    
def ConvertUglyNamespacesToPrettyStrings( namespaces ):
    
    namespaces = list( namespaces )
    
    namespaces.sort()
    
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
    
def Get64BitHammingDistance( phash1, phash2 ):
    
    # old way of doing this was:
    #while xor > 0:
    #    
    #    distance += 1
    #    xor &= xor - 1
    #    
    
    # convert to unsigned long long, then xor
    # then through the power of stackexchange magic, we get number of bits in record time
    # Here it is: https://stackoverflow.com/questions/9829578/fast-way-of-counting-non-zero-bits-in-positive-integer/9830282#9830282
    
    n = struct.unpack( '!Q', phash1 )[0] ^ struct.unpack( '!Q', phash2 )[0]
    
    n = ( n & 0x5555555555555555 ) + ( ( n & 0xAAAAAAAAAAAAAAAA ) >> 1 ) # 10101010, 01010101
    n = ( n & 0x3333333333333333 ) + ( ( n & 0xCCCCCCCCCCCCCCCC ) >> 2 ) # 11001100, 00110011
    n = ( n & 0x0F0F0F0F0F0F0F0F ) + ( ( n & 0xF0F0F0F0F0F0F0F0 ) >> 4 ) # 11110000, 00001111
    n = ( n & 0x00FF00FF00FF00FF ) + ( ( n & 0xFF00FF00FF00FF00 ) >> 8 ) # etc...
    n = ( n & 0x0000FFFF0000FFFF ) + ( ( n & 0xFFFF0000FFFF0000 ) >> 16 )
    n = ( n & 0x00000000FFFFFFFF ) + ( n >> 32 )
    
    # you technically are going n & 0xFFFFFFFF00000000 at the end, but that's a no-op with the >> 32 afterwards, so can be omitted
    
    return n
    
def GetEmptyDataDict():
    
    data = collections.defaultdict( default_dict_list )
    
    return data
    
def GetNow():
    
    return int( time.time() )
    
def GetNowFloat():
    
    return time.time()
    
def GetNowPrecise():
    
    if HC.PLATFORM_WINDOWS:
        
        return time.clock()
        
    else:
        
        return time.time()
        
    
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
        
    
    if HC.RUNNING_FROM_FROZEN_BUILD:
        
        # let's make a proper env for subprocess that doesn't have pyinstaller woo woo in it
        
        env = os.environ.copy()
        
        changes_made = False
        
        lp_key = 'LD_LIBRARY_PATH'
        lp_orig_key = lp_key + '_ORIG'
        
        if lp_orig_key in env:
            
            env[ lp_key ] = env[ lp_orig_key ]
            
            changes_made = True
            
        elif lp_key in env:
            
            del env[ lp_key ]
            
            changes_made = True
            
        
        if ( HC.PLATFORM_LINUX or HC.PLATFORM_OSX ) and 'PATH' in env:
            
            # fix for pyinstaller, which drops this stuff for some reason and hence breaks ffmpeg
            
            path = env[ 'PATH' ]
            
            path_locations = set( path.split( ':' ) )
            desired_path_locations = [ '/usr/bin', '/usr/local/bin' ]
            
            for desired_path_location in desired_path_locations:
                
                if desired_path_location not in path_locations:
                    
                    path = desired_path_location + ':' + path
                    
                    env[ 'PATH' ] = path
                    
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
    
    def get_len( item ):
        
        return len( item )
        
    
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
    
def Print( text ):
    
    try:
        
        print( str( text ) )
        
    except:
        
        print( repr( text ) )
        
    
ShowText = Print

def PrintException( e, do_wait = True ):
    
    if isinstance( e, HydrusExceptions.ShutdownException ):
        
        return
        
    
    etype = type( e )
    
    ( etype, value, tb ) = sys.exc_info()
    
    if etype is None:
        
        etype = type( e )
        value = str( e )
        
        trace = 'No error trace'
        
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

def Profile( summary, code, g, l, min_duration_ms = 20 ):
    
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
        
        details = output.read()
        
    else:
        
        summary += ' - It took ' + TimeDeltaToPrettyTimeDelta( time_took ) + '.'
        
        details = ''
        
    
    HG.controller.PrintProfile( summary, details )
    
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
        
        args = [ '"' + me + '"' ] + sys.argv[1:]
        
    
    os.execv( exe, args )
    
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
        

def SplitListIntoChunks( xs, n ):
    
    if isinstance( xs, set ):
        
        xs = list( xs )
        
    
    for i in range( 0, len( xs ), n ):
        
        yield xs[ i : i + n ]
        
    
def SplitMappingListIntoChunks( xs, n ):
    
    chunk_weight = 0
    chunk = []
    
    for ( tag_item, hash_items ) in xs:
        
        for chunk_of_hash_items in SplitListIntoChunks( hash_items, n ):
            
            chunk.append( ( tag_item, chunk_of_hash_items ) )
            
            chunk_weight += len( chunk_of_hash_items )
            
            if chunk_weight > n:
                
                yield chunk
                
                chunk_weight = 0
                chunk = []
                
            
        
    
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
    
def ToHumanBytes( size ):
    
    if size is None:
        
        return 'unknown size'
        
    
    if size < 1024:
        
        return ToHumanInt( size ) + 'B'
        
    
    suffixes = ( '', 'K', 'M', 'G', 'T', 'P' )
    
    suffix_index = 0
    
    while size >= 1024:
        
        size = size / 1024
        
        suffix_index += 1
        
    
    suffix = suffixes[ suffix_index ]
    
    if size < 10.0:
        
        # 3.1MB
        
        return '{:.1f}{}B'.format( size, suffix )
        
    else:
        
        # 23MB
        
        return '{:.0f}{}B'.format( size, suffix )
        
    
def ToHumanInt( num ):
    
    text = locale.format_string( '%d', num, grouping = True )
    
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
    
class AccountIdentifier( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_ACCOUNT_IDENTIFIER
    SERIALISABLE_NAME = 'Account Identifier'
    SERIALISABLE_VERSION = 1
    
    TYPE_ACCOUNT_KEY = 1
    TYPE_CONTENT = 2
    
    def __init__( self, account_key = None, content = None ):
        
        HydrusYAMLBase.__init__( self )
        
        if account_key is not None:
            
            self._type = self.TYPE_ACCOUNT_KEY
            self._data = account_key
            
        elif content is not None:
            
            self._type = self.TYPE_CONTENT
            self._data = content
            
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._type, self._data ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Account Identifier: ' + str( ( self._type, self._data ) )
    
    def _GetSerialisableInfo( self ):
        
        if self._type == self.TYPE_ACCOUNT_KEY:
            
            serialisable_data = self._data.hex()
            
        elif self._type == self.TYPE_CONTENT:
            
            serialisable_data = self._data.GetSerialisableTuple()
            
        
        return ( self._type, serialisable_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._type, serialisable_data ) = serialisable_info
        
        if self._type == self.TYPE_ACCOUNT_KEY:
            
            self._data = bytes.fromhex( serialisable_data )
            
        elif self._type == self.TYPE_CONTENT:
            
            self._data = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_data )
            
        
    
    def GetData( self ): return self._data
    
    def HasAccountKey( self ): return self._type == self.TYPE_ACCOUNT_KEY
    
    def HasContent( self ): return self._type == self.TYPE_CONTENT
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_ACCOUNT_IDENTIFIER ] = AccountIdentifier

class AccountType( HydrusYAMLBase ):
    
    yaml_tag = '!AccountType'
    
    def __init__( self, title, permissions, max_monthly_data ):
        
        HydrusYAMLBase.__init__( self )
        
        self._title = title
        self._permissions = permissions
        self._max_monthly_data = max_monthly_data
        
    
    def __repr__( self ): return self.ConvertToString()
    
    def GetPermissions( self ): return self._permissions
    
    def GetTitle( self ): return self._title
    
    def GetMaxBytes( self ):
        
        ( max_num_bytes, max_num_requests ) = self._max_monthly_data
        
        return max_num_bytes
        
    
    def GetMaxRequests( self ):
        
        ( max_num_bytes, max_num_requests ) = self._max_monthly_data
        
        return max_num_requests
        
    
    def GetMaxBytesString( self ):
        
        ( max_num_bytes, max_num_requests ) = self._max_monthly_data
        
        if max_num_bytes is None: max_num_bytes_string = 'No limit'
        else: max_num_bytes_string = ToHumanBytes( max_num_bytes )
        
        return max_num_bytes_string
        
    
    def GetMaxRequestsString( self ):
        
        ( max_num_bytes, max_num_requests ) = self._max_monthly_data
        
        if max_num_requests is None: max_num_requests_string = 'No limit'
        else: max_num_requests_string = ToHumanInt( max_num_requests )
        
        return max_num_requests_string
        
    
    def ConvertToString( self ):
        
        result_string = self._title + ' with '
        
        if self._permissions == [ HC.UNKNOWN_PERMISSION ]: result_string += 'no permissions'
        else: result_string += ', '.join( [ HC.permissions_string_lookup[ permission ] for permission in self._permissions ] ) + ' permissions'
        
        return result_string
        
    
    def IsUnknownAccountType( self ): return self._permissions == [ HC.UNKNOWN_PERMISSION ]
    
    def HasPermission( self, permission ): return permission in self._permissions
    
sqlite3.register_adapter( AccountType, yaml.safe_dump )

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
        
        self._func = func
        self._args = args
        self._kwargs = kwargs
        
    
    def __call__( self ):
        
        self._func( *self._args, **self._kwargs )
        
    
    def __repr__( self ):
        
        return 'Call: ' + repr( ( self._func, self._args, self._kwargs ) )
        
    
class ContentUpdate( object ):
    
    def __init__( self, data_type, action, row, reason = None ):
        
        self._data_type = data_type
        self._action = action
        self._row = row
        self._reason = reason
        
    
    def __eq__( self, other ):
        
        return hash( self ) == hash( other )
        
    
    def __ne__( self, other ): return not self.__eq__( other )
    
    def __hash__( self ):
        
        return hash( ( self._data_type, self._action, repr( self._row ) ) )
        
    
    def __repr__( self ):
        
        return 'Content Update: ' + str( ( self._data_type, self._action, self._row, self._reason ) )
        
    
    def GetAction( self ):
        
        return self._action
        
    
    def GetDataType( self ):
        
        return self._data_type
        
    
    def GetHashes( self ):
        
        if self._data_type == HC.CONTENT_TYPE_FILES:
            
            if self._action == HC.CONTENT_UPDATE_ADVANCED:
                
                hashes = set()
                
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
                
                ( notes, hash ) = self._row
                
                hashes = { hash }
                
            
        elif self._data_type == HC.CONTENT_TYPE_FILE_VIEWING_STATS:
            
            ( hash, preview_views_delta, preview_viewtime_delta, media_views_delta, media_viewtime_delta ) = self._row
            
            hashes = { hash }
            
        
        if not isinstance( hashes, set ):
            
            hashes = set( hashes )
            
        
        return hashes
        
    
    def GetReason( self ):
        
        if self._reason is None:
            
            return 'No reason given.'
            
        else:
            
            return self._reason
            
        
    
    def GetWeight( self ):
        
        return len( self.GetHashes() )
        
    
    def IsInboxRelated( self ):
        
        return self._action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_INBOX )
        
    
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
        
    
    def GetCallableTuple( self ):
        
        return ( self._action, self._args, self._kwargs )
        
    
    def GetResult( self ):
        
        time.sleep( 0.00001 ) # this one neat trick can save hassle on superquick jobs as event.wait can be laggy
        
        while True:
            
            if self._result_ready.wait( 2 ) == True:
                
                break
                
            elif HG.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application quit before db could serve result!' )
                
            
        
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
        
        return self._type + ' ' + self._action
        
    
class ServiceUpdate( object ):
    
    def __init__( self, action, row = None ):
        
        self._action = action
        self._row = row
        
    
    def ToTuple( self ):
        
        return ( self._action, self._row )
        
    
