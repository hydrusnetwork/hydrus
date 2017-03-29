import bs4
import collections
import cProfile
import cStringIO
import HydrusConstants as HC
import HydrusExceptions
import HydrusGlobals
import HydrusSerialisable
import locale
import os
import pstats
import psutil
import random
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
    
    count = float( count )
    
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
        
    
def ConvertIntToBytes( size ):
    
    if size is None: return 'unknown size'
    
    suffixes = ( '', 'K', 'M', 'G', 'T', 'P' )
    
    suffix_index = 0
    
    size = float( size )
    
    while size > 1024.0:
        
        size = size / 1024.0
        
        suffix_index += 1
        
    
    if size < 10.0: return '%.1f' % size + suffixes[ suffix_index ] + 'B'
    
    return '%.0f' % size + suffixes[ suffix_index ] + 'B'
    
def ConvertIntToFirst( n ):
    
    # straight from stack, wew
    return "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])
    
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
        
    
    return ConvertIntToPrettyString( num ) + ordinal
    
def ConvertIntToPrettyString( num ):
    
    # don't feed this a unicode string u'%d'--locale can't handle it
    text = locale.format( '%d', num, grouping = True )
    
    try:
        
        text = text.decode( locale.getpreferredencoding() )
        
        text = ToUnicode( text )
        
    except:
        
        text = ToUnicode( text )
        
    
    return text
    
def ConvertIntToUnit( unit ):
    
    if unit == 1: return 'B'
    elif unit == 1024: return 'KB'
    elif unit == 1048576: return 'MB'
    elif unit == 1073741824: return 'GB'
    
def ConvertMillisecondsToPrettyTime( ms ):
    
    hours = ms / 3600000
    
    if hours == 1: hours_result = '1 hour'
    else: hours_result = str( hours ) + ' hours'
    
    ms = ms % 3600000
    
    minutes = ms / 60000
    
    if minutes == 1: minutes_result = '1 minute'
    else: minutes_result = str( minutes ) + ' minutes'
    
    ms = ms % 60000
    
    seconds = ms / 1000
    
    if seconds == 1: seconds_result = '1 second'
    else: seconds_result = str( seconds ) + ' seconds'
    
    detailed_seconds = float( ms ) / 1000.0
    
    if detailed_seconds == 1.0: detailed_seconds_result = '1.0 seconds'
    else:detailed_seconds_result = '%.1f' % detailed_seconds + ' seconds'
    
    ms = ms % 1000
    
    if ms == 1: milliseconds_result = '1 millisecond'
    else: milliseconds_result = str( ms ) + ' milliseconds'
    
    if hours > 0: return hours_result + ' ' + minutes_result
    
    if minutes > 0: return minutes_result + ' ' + seconds_result
    
    if seconds > 0: return detailed_seconds_result
    
    return milliseconds_result
    
def ConvertNumericalRatingToPrettyString( lower, upper, rating, rounded_result = False, out_of = True ):
    
    rating_converted = ( rating * ( upper - lower ) ) + lower
    
    if rounded_result: s = '%.2f' % round( rating_converted )
    else: s = '%.2f' % rating_converted
    
    if out_of:
        
        if lower in ( 0, 1 ): s += '/%.2f' % upper
        
    
    return s
    
def ConvertPixelsToInt( unit ):
    
    if unit == 'pixels': return 1
    elif unit == 'kilopixels': return 1000
    elif unit == 'megapixels': return 1000000
    
def ConvertPrettyStringsToUglyNamespaces( pretty_strings ):
    
    result = { s for s in pretty_strings if s != 'no namespace' }
    
    if 'no namespace' in pretty_strings: result.add( '' )
    
    return result
    
def ConvertTimeDeltaToPrettyString( seconds ):
    
    if seconds is None:
        
        return 'month'
        
    
    if seconds > 60:
        
        seconds = int( seconds )
        
        if seconds > 86400:
            
            days = seconds / 86400
            hours = ( seconds % 86400 ) / 3600
            
            result = '%d' % days + ' days'
            
            if hours > 0:
                
                result += ' %d' % hours + ' hours'
                
            
        elif seconds > 3600:
            
            hours = seconds / 3600
            minutes = ( seconds % 3600 ) / 60
            
            result = '%d' % hours + ' hours'
            
            if minutes > 0:
                
                result += ' %d' % minutes + ' minutes'
                
            
        else:
            
            minutes = seconds / 60
            seconds = seconds % 60
            
            result = '%d' % minutes + ' minutes'
            
            if seconds > 0:
                
                result += ' %d' % seconds + ' seconds'
                
            
        
    elif seconds > 1:
        
        result = '%.1f' % seconds + ' seconds'
        
    elif seconds > 0.1:
        
        result = '%d' % ( seconds * 1000 ) + ' milliseconds'
        
    elif seconds > 0.01:
        
        result = '%.1f' % ( seconds * 1000 ) + ' milliseconds'
        
    elif seconds > 0.001:
        
        result = '%.2f' % ( seconds * 1000 ) + ' milliseconds'
        
    else:
        
        result = '%d' % ( seconds * 1000000 ) + ' microseconds'
        
    
    return result
    
def ConvertStatusToPrefix( status ):
    
    if status == HC.CONTENT_STATUS_CURRENT: return ''
    elif status == HC.CONTENT_STATUS_PENDING: return '(+) '
    elif status == HC.CONTENT_STATUS_PETITIONED: return '(-) '
    elif status == HC.CONTENT_STATUS_DELETED: return '(X) '
    
def ConvertTimestampToPrettyAge( timestamp ):
    
    if timestamp == 0 or timestamp is None: return 'unknown age'
    
    age = GetNow() - timestamp
    
    seconds = age % 60
    if seconds == 1: s = '1 second'
    else: s = str( seconds ) + ' seconds'
    
    age = age / 60
    minutes = age % 60
    if minutes == 1: m = '1 minute'
    else: m = str( minutes ) + ' minutes'
    
    age = age / 60
    hours = age % 24
    if hours == 1: h = '1 hour'
    else: h = str( hours ) + ' hours'
    
    age = age / 24
    days = age % 30
    if days == 1: d = '1 day'
    else: d = str( days ) + ' days'
    
    age = age / 30
    months = age % 12
    if months == 1: mo = '1 month'
    else: mo = str( months ) + ' months'
    
    years = age / 12
    if years == 1: y = '1 year'
    else: y = str( years ) + ' years'
    
    if years > 0: return ' '.join( ( y, mo ) ) + ' old'
    elif months > 0: return ' '.join( ( mo, d ) ) + ' old'
    elif days > 0: return ' '.join( ( d, h ) ) + ' old'
    elif hours > 0: return ' '.join( ( h, m ) ) + ' old'
    else: return ' '.join( ( m, s ) ) + ' old'
    
def ConvertTimestampToPrettyAgo( timestamp ):
    
    if timestamp is None or timestamp == 0: return 'unknown time'
    
    age = GetNow() - timestamp
    
    seconds = age % 60
    if seconds == 1: s = '1 second'
    else: s = str( seconds ) + ' seconds'
    
    age = age / 60
    minutes = age % 60
    if minutes == 1: m = '1 minute'
    else: m = str( minutes ) + ' minutes'
    
    age = age / 60
    hours = age % 24
    if hours == 1: h = '1 hour'
    else: h = str( hours ) + ' hours'
    
    age = age / 24
    days = age % 30
    if days == 1: d = '1 day'
    else: d = str( days ) + ' days'
    
    age = age / 30
    months = age % 12
    if months == 1: mo = '1 month'
    else: mo = str( months ) + ' months'
    
    years = age / 12
    if years == 1: y = '1 year'
    else: y = str( years ) + ' years'
    
    if years > 0: return ' '.join( ( y, mo ) ) + ' ago'
    elif months > 0: return ' '.join( ( mo, d ) ) + ' ago'
    elif days > 0: return ' '.join( ( d, h ) ) + ' ago'
    elif hours > 0: return ' '.join( ( h, m ) ) + ' ago'
    else: return ' '.join( ( m, s ) ) + ' ago'
    
def ConvertTimestampToPrettyExpires( timestamp ):
    
    if timestamp is None: return 'does not expire'
    if timestamp == 0: return 'unknown expiration'
    
    expires = GetNow() - timestamp
    
    if expires >= 0: already_happend = True
    else:
        
        expires *= -1
        
        already_happend = False
        
    
    seconds = expires % 60
    if seconds == 1: s = '1 second'
    else: s = str( seconds ) + ' seconds'
    
    expires = expires / 60
    minutes = expires % 60
    if minutes == 1: m = '1 minute'
    else: m = str( minutes ) + ' minutes'
    
    expires = expires / 60
    hours = expires % 24
    if hours == 1: h = '1 hour'
    else: h = str( hours ) + ' hours'
    
    expires = expires / 24
    days = expires % 30
    if days == 1: d = '1 day'
    else: d = str( days ) + ' days'
    
    expires = expires / 30
    months = expires % 12
    if months == 1: mo = '1 month'
    else: mo = str( months ) + ' months'
    
    years = expires / 12
    if years == 1: y = '1 year'
    else: y = str( years ) + ' years'
    
    if already_happend:
        
        if years > 0: return 'expired ' + ' '.join( ( y, mo ) ) + ' ago'
        elif months > 0: return 'expired ' + ' '.join( ( mo, d ) ) + ' ago'
        elif days > 0: return 'expired ' + ' '.join( ( d, h ) ) + ' ago'
        elif hours > 0: return 'expired ' + ' '.join( ( h, m ) ) + ' ago'
        else: return 'expired ' + ' '.join( ( m, s ) ) + ' ago'
        
    else:
        
        if years > 0: return 'expires in ' + ' '.join( ( y, mo ) )
        elif months > 0: return 'expires in ' + ' '.join( ( mo, d ) )
        elif days > 0: return 'expires in ' + ' '.join( ( d, h ) )
        elif hours > 0: return 'expires in ' + ' '.join( ( h, m ) )
        else: return 'expires in ' + ' '.join( ( m, s ) )
        
    
def ConvertTimestampToPrettyPending( timestamp ):
    
    if timestamp is None: return ''
    if timestamp == 0: return 'imminent'
    
    pending = GetNow() - timestamp
    
    if pending >= 0: return 'imminent'
    else: pending *= -1
    
    seconds = pending % 60
    if seconds == 1: s = '1 second'
    else: s = str( seconds ) + ' seconds'
    
    pending = pending / 60
    minutes = pending % 60
    if minutes == 1: m = '1 minute'
    else: m = str( minutes ) + ' minutes'
    
    pending = pending / 60
    hours = pending % 24
    if hours == 1: h = '1 hour'
    else: h = str( hours ) + ' hours'
    
    pending = pending / 24
    days = pending % 30
    if days == 1: d = '1 day'
    else: d = str( days ) + ' days'
    
    pending = pending / 30
    months = pending % 12
    if months == 1: mo = '1 month'
    else: mo = str( months ) + ' months'
    
    years = pending / 12
    if years == 1: y = '1 year'
    else: y = str( years ) + ' years'
    
    if years > 0: return 'in ' + ' '.join( ( y, mo ) )
    elif months > 0: return 'in ' + ' '.join( ( mo, d ) )
    elif days > 0: return 'in ' + ' '.join( ( d, h ) )
    elif hours > 0: return 'in ' + ' '.join( ( h, m ) )
    else: return 'in ' + ' '.join( ( m, s ) )
    
def ConvertTimestampToPrettySync( timestamp ):
    
    if timestamp is None or timestamp == 0: return '(initial sync has not yet occured)'
    
    age = GetNow() - timestamp
    
    seconds = age % 60
    if seconds == 1: s = '1 second'
    else: s = str( seconds ) + ' seconds'
    
    age = age / 60
    minutes = age % 60
    if minutes == 1: m = '1 minute'
    else: m = str( minutes ) + ' minutes'
    
    age = age / 60
    hours = age % 24
    if hours == 1: h = '1 hour'
    else: h = str( hours ) + ' hours'
    
    age = age / 24
    days = age % 30
    if days == 1: d = '1 day'
    else: d = str( days ) + ' days'
    
    age = age / 30
    months = age % 12
    if months == 1: mo = '1 month'
    else: mo = str( months ) + ' months'
    
    years = age / 12
    if years == 1: y = '1 year'
    else: y = str( years ) + ' years'
    
    if years > 0: return ' '.join( ( y, mo ) ) + ' ago'
    elif months > 0: return ' '.join( ( mo, d ) ) + ' ago'
    elif days > 0: return ' '.join( ( d, h ) ) + ' ago'
    elif hours > 0: return ' '.join( ( h, m ) ) + ' ago'
    else: return ' '.join( ( m, s ) ) + ' ago'
    
def ConvertTimestampToPrettyTime( timestamp ): return time.strftime( '%Y/%m/%d %H:%M:%S', time.localtime( timestamp ) )

def ConvertTimestampToHumanPrettyTime( timestamp ):
    
    now = GetNow()
    
    difference = now - timestamp
    
    if difference < 60: return 'just now'
    elif difference < 86400 * 7: return ConvertTimestampToPrettyAgo( timestamp )
    else: return ConvertTimestampToPrettyTime( timestamp )
    
def ConvertTimeToPrettyTime( secs ):
    
    return time.strftime( '%H:%M:%S', time.gmtime( secs ) )
    
def ConvertUglyNamespacesToPrettyStrings( namespaces ):
    
    result = [ namespace for namespace in namespaces if namespace != '' and namespace is not None ]
    
    result.sort()
    
    if '' in namespaces or None in namespaces: result.insert( 0, 'no namespace' )
    
    return result
    
def ConvertUnitToInt( unit ):
    
    if unit == 'B': return 1
    elif unit == 'KB': return 1024
    elif unit == 'MB': return 1048576
    elif unit == 'GB': return 1073741824
    
def ConvertValueRangeToBytes( value, range ):
    
    return ConvertIntToBytes( value ) + '/' + ConvertIntToBytes( range )
    
def ConvertValueRangeToPrettyString( value, range ):
    
    return ConvertIntToPrettyString( value ) + '/' + ConvertIntToPrettyString( range )
    
def DebugPrint( debug_info ):
    
    Print( debug_info )
    
    sys.stdout.flush()
    sys.stderr.flush()
    
def DeserialisePrettyTags( text ):
    
    text = text.replace( '\r', '' )
    
    tags = text.split( '\n' )
    
    return tags
    
def EncodeBytes( encoding, data ):
    
    data = ToByteString( data )
    
    if encoding == HC.ENCODING_RAW:
        
        encoded_data = data
        
    elif encoding == HC.ENCODING_HEX:
        
        encoded_data = data.encode( 'hex' )
        
    elif encoding == HC.ENCODING_BASE64:
        
        encoded_data = data.encode( 'base64' )
        
    
    return encoded_data
    
def GenerateKey():
    
    return os.urandom( HC.HYDRUS_KEY_LENGTH )
    
def GetEmptyDataDict():
    
    data = collections.defaultdict( default_dict_list )
    
    return data
    
def Get64BitHammingDistance( phash1, phash2 ):
    
    # old way of doing this was:
    #while xor > 0:
    #    
    #    distance += 1
    #    xor &= xor - 1
    #    
    
    # convert to unsigned long long, then xor
    # then through the power of stackexchange magic, we get number of bits in record time
    
    n = struct.unpack( '!Q', phash1 )[0] ^ struct.unpack( '!Q', phash2 )[0]
    
    n = ( n & 0x5555555555555555 ) + ( ( n & 0xAAAAAAAAAAAAAAAA ) >> 1 ) # 10101010, 01010101
    n = ( n & 0x3333333333333333 ) + ( ( n & 0xCCCCCCCCCCCCCCCC ) >> 2 ) # 11001100, 00110011
    n = ( n & 0x0F0F0F0F0F0F0F0F ) + ( ( n & 0xF0F0F0F0F0F0F0F0 ) >> 4 ) # 11110000, 00001111
    n = ( n & 0x00FF00FF00FF00FF ) + ( ( n & 0xFF00FF00FF00FF00 ) >> 8 ) # etc...
    n = ( n & 0x0000FFFF0000FFFF ) + ( ( n & 0xFFFF0000FFFF0000 ) >> 16 )
    n = ( n & 0x00000000FFFFFFFF ) + ( ( n & 0xFFFFFFFF00000000 ) >> 32 )
    
    return n
    
def GetNow(): return int( time.time() )

def GetNowPrecise():
    
    if HC.PLATFORM_WINDOWS: return time.clock()
    else: return time.time()
    
def GetSiblingProcessPorts( db_path, instance ):
    
    path = os.path.join( db_path, instance + '_running' )
    
    if os.path.exists( path ):
        
        with open( path, 'rb' ) as f:
            
            result = f.read()
            
            try:
                
                ( pid, create_time ) = SplitByLinesep( result )
                
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
    
def GetSubprocessStartupInfo():
    
    if HC.PLATFORM_WINDOWS:
        
        # This suppresses the terminal window that tends to pop up when calling ffmpeg or whatever
        
        startupinfo = subprocess.STARTUPINFO()
        
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
    else:
        
        startupinfo = None
        
    
    return startupinfo
    
def IntelligentMassIntersect( sets_to_reduce ):
    
    answer = None
    
    sets_to_reduce = list( sets_to_reduce )
    
    def get_len( item ):
        
        return len( item )
        
    
    sets_to_reduce.sort( key = get_len )
    
    for set_to_reduce in sets_to_reduce:
        
        if len( set_to_reduce ) == 0: return set()
        
        if answer is None: answer = set( set_to_reduce )
        else:
            
            # same thing as union; I could go &= here, but I want to be quick, so use the function call
            if len( answer ) == 0: return set()
            else: answer.intersection_update( set_to_reduce )
            
        
    
    if answer is None: return set()
    else: return answer
    
def IsAlreadyRunning( db_path, instance ):
    
    path = os.path.join( db_path, instance + '_running' )
    
    if os.path.exists( path ):
        
        with open( path, 'rb' ) as f:
            
            result = f.read()
            
            try:
                
                ( pid, create_time ) = SplitByLinesep( result )
                
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
    
    median_index = len( population ) / 2
    
    row = population.pop( median_index )
    
    return row
    
def MergeKeyToListDicts( key_to_list_dicts ):
    
    result = collections.defaultdict( list )
    
    for key_to_list_dict in key_to_list_dicts:
        
        for ( key, value ) in key_to_list_dict.items(): result[ key ].extend( value )
        
    
    return result
    
def Print( text ):
    
    print( ToUnicode( text ) )
    
ShowText = Print

def PrintException( e, do_wait = True ):
    
    if isinstance( e, HydrusExceptions.ShutdownException ):
        
        return
        
    
    etype = type( e )
    
    value = ToUnicode( e )
    
    trace_list = traceback.format_stack()
    
    trace = ''.join( trace_list )
    
    message = ToUnicode( etype.__name__ ) + ': ' + ToUnicode( value ) + os.linesep + ToUnicode( trace )
    
    Print( '' )
    Print( 'Exception:' )
    
    DebugPrint( message )
    
    if do_wait:
        
        time.sleep( 1 )
        
    
ShowException = PrintException

def Profile( summary, code, g, l ):
    
    profile = cProfile.Profile()
    
    profile.runctx( code, g, l )
    
    output = cStringIO.StringIO()
    
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
    
    HydrusGlobals.controller.PrintProfile( summary, output.read() )
    
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
        
    
    with open( path, 'wb' ) as f:
        
        f.write( ToByteString( record_string ) )
        
    
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
    
def SplayListForDB( xs ): return '(' + ','.join( ( str( x ) for x in xs ) ) + ')'

def SplitByLinesep( raw_text ):
    
    if '\r\n' in raw_text:
        
        return raw_text.split( '\r\n' )
        
    else:
        
        return raw_text.split( '\n' )
        
    

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
        
    
    for i in xrange( 0, len( xs ), n ):
        
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
    
def TimeHasPassedPrecise( precise_timestamp ):
    
    return GetNowPrecise() > precise_timestamp
    
def TimeUntil( timestamp ):
    
    return timestamp - GetNow()
    
def ToByteString( text_producing_object ):
    
    if isinstance( text_producing_object, unicode ):
        
        return text_producing_object.encode( 'utf-8' )
        
    elif isinstance( text_producing_object, str ):
        
        return text_producing_object
        
    else:
        
        try:
            
            return str( text_producing_object )
            
        except:
            
            return str( repr( text_producing_object ) )
            
        
    
def ToUnicode( text_producing_object ):
    
    if isinstance( text_producing_object, ( str, unicode, bs4.element.NavigableString ) ):
        
        text = text_producing_object
        
    else:
        
        try:
            
            text = str( text_producing_object ) # dealing with exceptions, etc...
            
        except:
            
            try:
                
                text = unicode( text_producing_object )
                
            except:
                
                text = repr( text_producing_object )
                
            
        
    
    if not isinstance( text, unicode ):
        
        try:
            
            text = text.decode( 'utf-8' )
            
        except:
            
            try:
                
                text = text.decode( locale.getpreferredencoding() )
                
            except:
                
                text = repr( text ).decode( 'utf-8' )
                
            
            
        
    
    return text
    
def WaitForProcessToFinish( p, timeout ):
    
    started = GetNow()
    
    while p.poll() is None:
        
        if TimeHasPassed( started + timeout ):
            
            p.kill()
            
            raise Exception( 'Process did not finish within ' + ConvertIntToPrettyString( timeout ) + ' seconds!' )
            
        
        time.sleep( 2 )
        
    
class HydrusYAMLBase( yaml.YAMLObject ):
    
    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper
    
class Account( HydrusYAMLBase ):
    
    yaml_tag = u'!Account'
    
    def __init__( self, account_key, account_type, created, expires, used_bytes, used_requests, banned_info = None ):
        
        HydrusYAMLBase.__init__( self )
        
        self._info = {}
        
        self._info[ 'account_key' ] = account_key
        self._info[ 'account_type' ] = account_type
        self._info[ 'created' ] = created
        self._info[ 'expires' ] = expires
        self._info[ 'used_bytes' ] = used_bytes
        self._info[ 'used_requests' ] = used_requests
        if banned_info is not None: self._info[ 'banned_info' ] = banned_info
        
        self._info[ 'fresh_timestamp' ] = GetNow()
        
    
    def __repr__( self ): return self.ConvertToString()
    
    def __str__( self ): return self.ConvertToString()
    
    def _IsBanned( self ):
        
        if 'banned_info' not in self._info: return False
        else:
            
            ( reason, created, expires ) = self._info[ 'banned_info' ]
            
            if expires is None: return True
            else: return not TimeHasPassed( expires )
            
        
    
    def _IsBytesExceeded( self ):
        
        account_type = self._info[ 'account_type' ]
        
        max_num_bytes = account_type.GetMaxBytes()
        
        used_bytes = self._info[ 'used_bytes' ]
        
        return max_num_bytes is not None and used_bytes > max_num_bytes
        
    
    def _IsExpired( self ):
        
        if self._info[ 'expires' ] is None: return False
        else: return TimeHasPassed( self._info[ 'expires' ] )
        
    
    def _IsRequestsExceeded( self ):
        
        account_type = self._info[ 'account_type' ]
        
        max_num_requests = account_type.GetMaxRequests()
        
        used_requests = self._info[ 'used_requests' ]
        
        return max_num_requests is not None and used_requests > max_num_requests
        
    
    def CheckPermission( self, permission ):
        
        if self._IsBanned(): raise HydrusExceptions.PermissionException( 'This account is banned!' )
        
        if self._IsExpired(): raise HydrusExceptions.PermissionException( 'This account is expired.' )
        
        if self._IsBytesExceeded(): raise HydrusExceptions.PermissionException( 'You have hit your data transfer limit, and cannot make any more requests for the month.' )
        
        if self._IsRequestsExceeded(): raise HydrusExceptions.PermissionException( 'You have hit your requests limit, and cannot make any more requests for the month.' )
        
        if not self._info[ 'account_type' ].HasPermission( permission ): raise HydrusExceptions.PermissionException( 'You do not have permission to do that.' )
        
    
    def ConvertToString( self ): return ConvertTimestampToPrettyAge( self._info[ 'created' ] ) + os.linesep + self._info[ 'account_type' ].ConvertToString() + os.linesep + 'which '+ ConvertTimestampToPrettyExpires( self._info[ 'expires' ] )
    
    def GetAccountKey( self ): return self._info[ 'account_key' ]
    
    def GetAccountType( self ): return self._info[ 'account_type' ]
    
    def GetCreated( self ): return self._info[ 'created' ]
    
    def GetExpires( self ): return self._info[ 'expires' ]
    
    def GetExpiresString( self ):
        
        if self._IsBanned():
            
            ( reason, created, expires ) = self._info[ 'banned_info' ]
            
            return 'banned ' + ConvertTimestampToPrettyAge( created ) + ', ' + ConvertTimestampToPrettyExpires( expires ) + ' because: ' + reason
            
        else: return ConvertTimestampToPrettyAge( self._info[ 'created' ] ) + ' and ' + ConvertTimestampToPrettyExpires( self._info[ 'expires' ] )
        
    
    def GetUsedBytesString( self ):
        
        max_num_bytes = self._info[ 'account_type' ].GetMaxBytes()
        
        used_bytes = self._info[ 'used_bytes' ]
        
        if max_num_bytes is None: return ConvertIntToBytes( used_bytes ) + ' used this month'
        else: return ConvertIntToBytes( used_bytes ) + '/' + ConvertIntToBytes( max_num_bytes ) + ' used this month'
        
    
    def GetUsedRequestsString( self ):
        
        max_num_requests = self._info[ 'account_type' ].GetMaxRequests()
        
        used_requests = self._info[ 'used_requests' ]
        
        if max_num_requests is None: return ConvertIntToPrettyString( used_requests ) + ' requests used this month'
        else: return ConvertValueRangeToPrettyString( used_requests, max_num_requests ) + ' requests used this month'
        
    
    def GetUsedBytes( self ): return self._info[ 'used_bytes' ]
    
    def GetUsedRequests( self ): return self._info[ 'used_bytes' ]
    
    def HasAccountKey( self ):
        
        if 'account_key' in self._info and self._info[ 'account_key' ] is not None: return True
        
        return False
        
    
    def HasPermission( self, permission ):
        
        if self._IsBanned(): return False
        
        if self._IsExpired(): return False
        
        if self._IsBytesExceeded(): return False
        
        if self._IsRequestsExceeded(): return False
        
        return self._info[ 'account_type' ].HasPermission( permission )
        
    
    def IsBanned( self ): return self._IsBanned()
    
    def IsStale( self ): return self._info[ 'fresh_timestamp' ] + HC.UPDATE_DURATION * 5 < GetNow()
    
    def IsUnknownAccount( self ): return self._info[ 'account_type' ].IsUnknownAccountType()
    
    def MakeFresh( self ): self._info[ 'fresh_timestamp' ] = GetNow()
    
    def MakeStale( self ): self._info[ 'fresh_timestamp' ] = 0
    
    def RequestMade( self, num_bytes ):
        
        self._info[ 'used_bytes' ] += num_bytes
        self._info[ 'used_requests' ] += 1
        
    
sqlite3.register_adapter( Account, yaml.safe_dump )

class AccountIdentifier( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_ACCOUNT_IDENTIFIER
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
    
    def __repr__( self ): return 'Account Identifier: ' + ToUnicode( ( self._type, self._data ) )
    
    def _GetSerialisableInfo( self ):
        
        if self._type == self.TYPE_ACCOUNT_KEY:
            
            serialisable_data = self._data.encode( 'hex' )
            
        elif self._type == self.TYPE_CONTENT:
            
            serialisable_data = self._data.GetSerialisableTuple()
            
        
        return ( self._type, serialisable_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._type, serialisable_data ) = serialisable_info
        
        if self._type == self.TYPE_ACCOUNT_KEY:
            
            self._data = serialisable_data.decode( 'hex' )
            
        elif self._type == self.TYPE_CONTENT:
            
            self._data = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_data )
            
        
    
    def GetData( self ): return self._data
    
    def HasAccountKey( self ): return self._type == self.TYPE_ACCOUNT_KEY
    
    def HasContent( self ): return self._type == self.TYPE_CONTENT
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_ACCOUNT_IDENTIFIER ] = AccountIdentifier

class AccountType( HydrusYAMLBase ):
    
    yaml_tag = u'!AccountType'
    
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
        else: max_num_bytes_string = ConvertIntToBytes( max_num_bytes )
        
        return max_num_bytes_string
        
    
    def GetMaxRequestsString( self ):
        
        ( max_num_bytes, max_num_requests ) = self._max_monthly_data
        
        if max_num_requests is None: max_num_requests_string = 'No limit'
        else: max_num_requests_string = ConvertIntToPrettyString( max_num_requests )
        
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
        
    
class ContentUpdate( object ):
    
    def __init__( self, data_type, action, row ):
        
        self._data_type = data_type
        self._action = action
        self._row = row
        
    
    def __eq__( self, other ): return self._data_type == other._data_type and self._action == other._action and self._row == other._row
    
    def __ne__( self, other ): return not self.__eq__( other )
    
    def __repr__( self ): return 'Content Update: ' + ToUnicode( ( self._data_type, self._action, self._row ) )
    
    def GetHashes( self ):
        
        if self._data_type == HC.CONTENT_TYPE_FILES:
            
            if self._action == HC.CONTENT_UPDATE_ADVANCED:
                
                hashes = set()
                
            elif self._action == HC.CONTENT_UPDATE_ADD:
                
                hash = self._row[0]
                
                hashes = set( ( hash, ) )
                
            elif self._action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_UNDELETE, HC.CONTENT_UPDATE_INBOX, HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_RESCIND_PETITION ):
                
                hashes = self._row
                
            elif self._action == HC.CONTENT_UPDATE_PETITION:
                
                ( hashes, reason ) = self._row
                
            
        elif self._data_type == HC.CONTENT_TYPE_DIRECTORIES:
            
            hashes = set()
            
        elif self._data_type == HC.CONTENT_TYPE_MAPPINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADVANCED:
                
                hashes = set()
                
            elif self._action == HC.CONTENT_UPDATE_PETITION:
                
                ( tag, hashes, reason ) = self._row
                
            else:
                
                ( tag, hashes ) = self._row
                
            
        elif self._data_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            hashes = set()
            
        elif self._data_type == HC.CONTENT_TYPE_RATINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADD:
                
                ( rating, hashes ) = self._row
                
            
        
        if not isinstance( hashes, set ):
            
            hashes = set( hashes )
            
        
        return hashes
        
    
    def GetWeight( self ):
        
        return len( self.GetHashes() )
        
    
    def IsInboxRelated( self ):
        
        return self._action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_INBOX )
        
    
    def ToTuple( self ):
        
        return ( self._data_type, self._action, self._row )
        
    
class EditLogAction( object ):
    
    yaml_tag = u'!EditLogAction'
    
    def __init__( self, action ): self._action = action
    
    def GetAction( self ): return self._action
    
class EditLogActionAdd( EditLogAction ):
    
    yaml_tag = u'!EditLogActionAdd'
    
    def __init__( self, data ):
        
        EditLogAction.__init__( self, HC.ADD )
        
        self._data = data
        
    
    def GetData( self ): return self._data
    
class EditLogActionDelete( EditLogAction ):
    
    yaml_tag = u'!EditLogActionDelete'
    
    def __init__( self, identifier ):
        
        EditLogAction.__init__( self, HC.DELETE )
        
        self._identifier = identifier
        
    
    def GetIdentifier( self ): return self._identifier
    
class EditLogActionEdit( EditLogAction ):
    
    yaml_tag = u'!EditLogActionEdit'
    
    def __init__( self, identifier, data ):
        
        EditLogAction.__init__( self, HC.EDIT )
        
        self._identifier = identifier
        self._data = data
        
    
    def GetData( self ): return self._data
    
    def GetIdentifier( self ): return self._identifier
    
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
        
        while True:
            
            if self._result_ready.wait( 2 ) == True:
                
                break
                
            elif HydrusGlobals.model_shutdown:
                
                raise HydrusExceptions.ShutdownException( 'Application quit before db could serve result!' )
                
            
        
        if isinstance( self._result, Exception ):
            
            e = self._result
            
            raise e
            
        else:
            
            return self._result
            
        
    
    def GetType( self ):
        
        return self._type
        
    
    def IsSynchronous( self ): return self._synchronous
    
    def PutResult( self, result ):
        
        self._result = result
        
        self._result_ready.set()
        
    
    def ToString( self ):
        
        return self._type + ' ' + self._action
        
    
class ServerToClientContentUpdatePackage( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SERVER_TO_CLIENT_CONTENT_UPDATE_PACKAGE
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._content_data = {}
        
        self._hash_ids_to_hashes = {}
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_content_data = []
        
        for ( data_type, actions_dict ) in self._content_data.items():
            
            serialisable_actions_dict = []
            
            for ( action, rows ) in actions_dict.items():
                
                serialisable_actions_dict.append( ( action, rows ) )
                
            
            serialisable_content_data.append( ( data_type, serialisable_actions_dict ) )
            
        
        serialisable_hashes = [ ( hash_id, hash.encode( 'hex' ) ) for ( hash_id, hash ) in self._hash_ids_to_hashes.items() ]
        
        return ( serialisable_content_data, serialisable_hashes )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_content_data, serialisable_hashes ) = serialisable_info
        
        self._content_data = {}
        
        for ( data_type, serialisable_actions_dict ) in serialisable_content_data:
            
            actions_dict = {}
            
            for ( action, rows ) in serialisable_actions_dict:
                
                actions_dict[ action ] = rows
                
            
            self._content_data[ data_type ] = actions_dict
            
        
        self._hash_ids_to_hashes = { hash_id : hash.decode( 'hex' ) for ( hash_id, hash ) in serialisable_hashes }
        
    
    def AddContentData( self, data_type, action, rows, hash_ids_to_hashes ):
        
        if data_type not in self._content_data:
            
            self._content_data[ data_type ] = {}
            
        
        if action not in self._content_data[ data_type ]:
            
            self._content_data[ data_type ][ action ] = []
            
        
        self._content_data[ data_type ][ action ].extend( rows )
        
        self._hash_ids_to_hashes.update( hash_ids_to_hashes )
        
    
    def GetContentDataIterator( self, data_type, action ):
        
        if data_type not in self._content_data or action not in self._content_data[ data_type ]: return ()
        
        data = self._content_data[ data_type ][ action ]
        
        if data_type == HC.CONTENT_TYPE_FILES:
            
            if action == HC.CONTENT_UPDATE_ADD: return ( ( self._hash_ids_to_hashes[ hash_id ], size, mime, timestamp, width, height, duration, num_frames, num_words ) for ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in data )
            else: return ( ( self._hash_ids_to_hashes[ hash_id ], ) for hash_id in data )
            
        elif data_type == HC.CONTENT_TYPE_MAPPINGS: return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( tag, hash_ids ) in data )
        else: return data.__iter__()
        
    
    def GetNumRows( self ):
        
        num = 0
        
        for data_type in self._content_data:
            
            for action in self._content_data[ data_type ]:
                
                data = self._content_data[ data_type ][ action ]
                
                if data_type == HC.CONTENT_TYPE_MAPPINGS:
                    
                    for ( tag, hash_ids ) in data:
                        
                        num += len( hash_ids )
                        
                    
                else: num += len( data )
                
            
        
        return num
        
    
    def IterateContentUpdateChunks( self, chunk_weight = 1250 ):
        
        data_types = [ HC.CONTENT_TYPE_FILES, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ]
        actions = [ HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ]
        
        content_updates = []
        weight = 0
        
        for ( data_type, action ) in itertools.product( data_types, actions ):
            
            for row in self.GetContentDataIterator( data_type, action ):
                
                content_update = ContentUpdate( data_type, action, row )
                
                weight += content_update.GetWeight()
                content_updates.append( content_update )
                
                if weight > chunk_weight:
                    
                    yield ( content_updates, weight )
                    
                    content_updates = []
                    weight = 0
                    
                
            
        
        if len( content_updates ) > 0:
            
            yield ( content_updates, weight )
            
        
    
    def GetHashes( self ): return set( self._hash_ids_to_hashes.values() )
    
    def GetTags( self ):
        
        tags = set()
        
        tags.update( ( tag for ( tag, hash_ids ) in self.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_CURRENT ) ) )
        tags.update( ( tag for ( tag, hash_ids ) in self.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_DELETED ) ) )
        
        tags.update( ( old_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_CURRENT ) ) )
        tags.update( ( new_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_CURRENT ) ) )
        tags.update( ( old_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_DELETED ) ) )
        tags.update( ( new_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_DELETED ) ) )
        
        return tags
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVER_TO_CLIENT_CONTENT_UPDATE_PACKAGE ] = ServerToClientContentUpdatePackage

class ServiceUpdate( object ):
    
    def __init__( self, action, row = None ):
        
        self._action = action
        self._row = row
        
    
    def ToTuple( self ):
        
        return ( self._action, self._row )
        
    
