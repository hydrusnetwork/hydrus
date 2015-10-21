import bs4
import collections
import HydrusConstants as HC
import HydrusExceptions
import HydrusGlobals
import HydrusSerialisable
import locale
import os
import psutil
import send2trash
import shutil
import sqlite3
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
    
def ConvertContentsToClientToServerContentUpdatePackage( action, contents, reason = None ):
    
    hashes_to_hash_ids = {}
    hash_ids_to_hashes = {}
    hash_i = 0
    
    content_data_dict = GetEmptyDataDict()
    
    for content in contents:
        
        content_type = content.GetContentType()
        content_data = content.GetContent()
        
        if content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = content_data
            
        elif content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = content_data
            
        elif content_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            ( old_tag, new_tag ) = content_data
            
            hashes = set()
            
        
        hash_ids = []
        
        for hash in hashes:
            
            if hash not in hashes_to_hash_ids:
                
                hashes_to_hash_ids[ hash ] = hash_i
                hash_ids_to_hashes[ hash_i ] = hash
                
                hash_i += 1
                
            
            hash_ids.append( hashes_to_hash_ids[ hash ] )
            
        
        if action in ( HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ):
            
            if reason is None:
                
                reason = 'admin'
                
            
            if content_type == HC.CONTENT_TYPE_FILES:
                
                row = ( hash_ids, reason )
                
            elif content_type == HC.CONTENT_TYPE_MAPPINGS:
                
                row = ( tag, hash_ids, reason )
                
            else:
                
                row = ( ( old_tag, new_tag ), reason )
                
            
        elif action in ( HC.CONTENT_UPDATE_DENY_PEND, HC.CONTENT_UPDATE_DENY_PETITION ):
            
            if content_type == HC.CONTENT_TYPE_FILES:
                
                row = hash_ids
                
            elif content_type == HC.CONTENT_TYPE_MAPPINGS:
                
                row = ( tag, hash_ids )
                
            elif content_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
                
                row = ( old_tag, new_tag )
                
            
        
        content_data_dict[ content_type ][ action ].append( row )
        
    
    return ClientToServerContentUpdatePackage( content_data_dict, hash_ids_to_hashes )
    
    
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
    
def ConvertIntToPixels( i ):
    
    if i == 1: return 'pixels'
    elif i == 1000: return 'kilopixels'
    elif i == 1000000: return 'megapixels'
    else: return 'megapixels'
    
def ConvertIntToPrettyString( num ): return ToString( locale.format( "%d", num, grouping = True ) )

def ConvertIntToUnit( unit ):
    
    if unit == 1: return 'B'
    elif unit == 1024: return 'KB'
    elif unit == 1048576: return 'MB'
    elif unit == 1073741824: return 'GB'
    
def ConvertMillisecondsToPrettyTime( ms ):
    
    hours = ms / 3600000
    
    if hours == 1: hours_result = '1 hour'
    else: hours_result = ToString( hours ) + ' hours'
    
    ms = ms % 3600000
    
    minutes = ms / 60000
    
    if minutes == 1: minutes_result = '1 minute'
    else: minutes_result = ToString( minutes ) + ' minutes'
    
    ms = ms % 60000
    
    seconds = ms / 1000
    
    if seconds == 1: seconds_result = '1 second'
    else: seconds_result = ToString( seconds ) + ' seconds'
    
    detailed_seconds = float( ms ) / 1000.0
    
    if detailed_seconds == 1.0: detailed_seconds_result = '1.0 seconds'
    else:detailed_seconds_result = '%.1f' % detailed_seconds + ' seconds'
    
    ms = ms % 1000
    
    if ms == 1: milliseconds_result = '1 millisecond'
    else: milliseconds_result = ToString( ms ) + ' milliseconds'
    
    if hours > 0: return hours_result + ' ' + minutes_result
    
    if minutes > 0: return minutes_result + ' ' + seconds_result
    
    if seconds > 0: return detailed_seconds_result
    
    return milliseconds_result
    
def ConvertNumericalRatingToPrettyString( lower, upper, rating, rounded_result = False, out_of = True ):
    
    rating_converted = ( rating * ( upper - lower ) ) + lower
    
    if rounded_result: s = ToString( '%.2f' % round( rating_converted ) )
    else: s = ToString( '%.2f' % rating_converted )
    
    if out_of:
        
        if lower in ( 0, 1 ): s += '/' + ToString( '%.2f' % upper )
        
    
    return s
    
def ConvertPixelsToInt( unit ):
    
    if unit == 'pixels': return 1
    elif unit == 'kilopixels': return 1000
    elif unit == 'megapixels': return 1000000
    
def ConvertPortablePathToAbsPath( portable_path ):
    
    if portable_path is None: return None
    
    if os.path.isabs( portable_path ): abs_path = portable_path
    else: abs_path = os.path.normpath( HC.BASE_DIR + os.path.sep + portable_path )
    
    if os.path.exists( abs_path ): return abs_path
    else: return None
    
def ConvertPrettyStringsToUglyNamespaces( pretty_strings ):
    
    result = { s for s in pretty_strings if s != 'no namespace' }
    
    if 'no namespace' in pretty_strings: result.add( '' )
    
    return result
    
def ConvertStatusToPrefix( status ):
    
    if status == HC.CURRENT: return ''
    elif status == HC.PENDING: return '(+) '
    elif status == HC.PETITIONED: return '(-) '
    elif status == HC.DELETED: return '(X) '
    elif status == HC.DELETED_PENDING: return '(X+) '
    
def ConvertTimestampToPrettyAge( timestamp ):
    
    if timestamp == 0 or timestamp is None: return 'unknown age'
    
    age = GetNow() - timestamp
    
    seconds = age % 60
    if seconds == 1: s = '1 second'
    else: s = ToString( seconds ) + ' seconds'
    
    age = age / 60
    minutes = age % 60
    if minutes == 1: m = '1 minute'
    else: m = ToString( minutes ) + ' minutes'
    
    age = age / 60
    hours = age % 24
    if hours == 1: h = '1 hour'
    else: h = ToString( hours ) + ' hours'
    
    age = age / 24
    days = age % 30
    if days == 1: d = '1 day'
    else: d = ToString( days ) + ' days'
    
    age = age / 30
    months = age % 12
    if months == 1: mo = '1 month'
    else: mo = ToString( months ) + ' months'
    
    years = age / 12
    if years == 1: y = '1 year'
    else: y = ToString( years ) + ' years'
    
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
    else: s = ToString( seconds ) + ' seconds'
    
    age = age / 60
    minutes = age % 60
    if minutes == 1: m = '1 minute'
    else: m = ToString( minutes ) + ' minutes'
    
    age = age / 60
    hours = age % 24
    if hours == 1: h = '1 hour'
    else: h = ToString( hours ) + ' hours'
    
    age = age / 24
    days = age % 30
    if days == 1: d = '1 day'
    else: d = ToString( days ) + ' days'
    
    age = age / 30
    months = age % 12
    if months == 1: mo = '1 month'
    else: mo = ToString( months ) + ' months'
    
    years = age / 12
    if years == 1: y = '1 year'
    else: y = ToString( years ) + ' years'
    
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
    else: s = ToString( seconds ) + ' seconds'
    
    expires = expires / 60
    minutes = expires % 60
    if minutes == 1: m = '1 minute'
    else: m = ToString( minutes ) + ' minutes'
    
    expires = expires / 60
    hours = expires % 24
    if hours == 1: h = '1 hour'
    else: h = ToString( hours ) + ' hours'
    
    expires = expires / 24
    days = expires % 30
    if days == 1: d = '1 day'
    else: d = ToString( days ) + ' days'
    
    expires = expires / 30
    months = expires % 12
    if months == 1: mo = '1 month'
    else: mo = ToString( months ) + ' months'
    
    years = expires / 12
    if years == 1: y = '1 year'
    else: y = ToString( years ) + ' years'
    
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
    else: s = ToString( seconds ) + ' seconds'
    
    pending = pending / 60
    minutes = pending % 60
    if minutes == 1: m = '1 minute'
    else: m = ToString( minutes ) + ' minutes'
    
    pending = pending / 60
    hours = pending % 24
    if hours == 1: h = '1 hour'
    else: h = ToString( hours ) + ' hours'
    
    pending = pending / 24
    days = pending % 30
    if days == 1: d = '1 day'
    else: d = ToString( days ) + ' days'
    
    pending = pending / 30
    months = pending % 12
    if months == 1: mo = '1 month'
    else: mo = ToString( months ) + ' months'
    
    years = pending / 12
    if years == 1: y = '1 year'
    else: y = ToString( years ) + ' years'
    
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
    else: s = ToString( seconds ) + ' seconds'
    
    age = age / 60
    minutes = age % 60
    if minutes == 1: m = '1 minute'
    else: m = ToString( minutes ) + ' minutes'
    
    age = age / 60
    hours = age % 24
    if hours == 1: h = '1 hour'
    else: h = ToString( hours ) + ' hours'
    
    age = age / 24
    days = age % 30
    if days == 1: d = '1 day'
    else: d = ToString( days ) + ' days'
    
    age = age / 30
    months = age % 12
    if months == 1: mo = '1 month'
    else: mo = ToString( months ) + ' months'
    
    years = age / 12
    if years == 1: y = '1 year'
    else: y = ToString( years ) + ' years'
    
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
    
def ConvertValueRangeToPrettyString( value, range ):
    
    return ConvertIntToPrettyString( value ) + '/' + ConvertIntToPrettyString( range )
    
def DebugPrint( debug_info ):
    
    print( debug_info )
    
    sys.stdout.flush()
    sys.stderr.flush()
    
def DeletePath( path ):
    
    if os.path.isdir( path ):
        
        shutil.rmtree( path )
        
    else:
        
        os.remove( path )
        
    
def DeserialisePrettyTags( text ):
    
    text = text.replace( '\r', '' )
    
    tags = text.split( '\n' )
    
    return tags
    
def GenerateKey():
    
    return os.urandom( HC.HYDRUS_KEY_LENGTH )
    
def GetEmptyDataDict():
    
    data = collections.defaultdict( default_dict_list )
    
    return data
    
def GetHammingDistance( phash1, phash2 ):
    
    distance = 0
    
    phash1 = bytearray( phash1 )
    phash2 = bytearray( phash2 )
    
    for i in range( len( phash1 ) ):
        
        xor = phash1[i] ^ phash2[i]
        
        while xor > 0:
            
            distance += 1
            xor &= xor - 1
            
        
    
    return distance
    
def GetNow(): return int( time.time() )

def GetNowPrecise():
    
    if HC.PLATFORM_WINDOWS: return time.clock()
    else: return time.time()
    
def GetSiblingProcessPorts( instance ):
    
    path = HC.BASE_DIR + os.path.sep + instance + '_running'
    
    if os.path.exists( path ):
        
        with open( path, 'rb' ) as f:
            
            result = f.read()
            
            try:
                
                ( pid, create_time ) = result.split( os.linesep )
                
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
    
    sets_to_reduce.sort( cmp = lambda x, y: cmp( len( x ), len( y ) ) )
    
    for set_to_reduce in sets_to_reduce:
        
        if len( set_to_reduce ) == 0: return set()
        
        if answer is None: answer = set( set_to_reduce )
        else:
            
            # same thing as union; I could go &= here, but I want to be quick, so use the function call
            if len( answer ) == 0: return set()
            else: answer.intersection_update( set_to_reduce )
            
        
    
    if answer is None: return set()
    else: return answer
    
def IsAlreadyRunning( instance ):
    
    path = HC.BASE_DIR + os.path.sep + instance + '_running'
    
    if os.path.exists( path ):
        
        with open( path, 'rb' ) as f:
            
            result = f.read()
            
            try:
                
                ( pid, create_time ) = result.split( os.linesep )
                
                pid = int( pid )
                create_time = float( create_time )
                
            except ValueError:
                
                return False
                
            
            try:
                
                if psutil.pid_exists( pid ):
                    
                    p = psutil.Process( pid )
                    
                    if p.create_time() == create_time and p.is_running():
                        
                        return True
                        
                    
                
            except psutil.Error:
                
                return False
                
            
        
    
    return False
    
def MergeKeyToListDicts( key_to_list_dicts ):
    
    result = collections.defaultdict( list )
    
    for key_to_list_dict in key_to_list_dicts:
        
        for ( key, value ) in key_to_list_dict.items(): result[ key ].extend( value )
        
    
    return result
    
def ReadFileLikeAsBlocks( f ):
    
    next_block = f.read( HC.READ_BLOCK_SIZE )
    
    while next_block != '':
        
        yield next_block
        
        next_block = f.read( HC.READ_BLOCK_SIZE )
        
    
def RecordRunningStart( instance ):
    
    path = HC.BASE_DIR + os.path.sep + instance + '_running'
    
    record_string = ''
    
    try:
        
        me = psutil.Process()
        
        record_string += str( me.pid )
        record_string += os.linesep
        record_string += str( me.create_time() )
        
    except psutil.Error:
        
        return
        
    
    with open( path, 'wb' ) as f:
        
        f.write( record_string )
        
    
def RecyclePath( path ):
    
    original_path = path
    
    if HC.PLATFORM_LINUX:
        
        # send2trash for Linux tries to do some Python3 str() stuff in prepping non-str paths for recycling
        
        if not isinstance( path, str ):
            
            try:
                
                path = path.encode( sys.getfilesystemencoding() )
                
            except:
                
                print( 'Trying to prepare a file for recycling created this error:' )
                traceback.print_exc()
                
                return
                
            
        
    
    try:
        
        send2trash.send2trash( path )
        
    except:
        
        print( 'Trying to recycle a file created this error:' )
        traceback.print_exc()
        
        print( 'It has been fully deleted instead.' )
        
        DeletePath( original_path )
        
    
def ShowExceptionDefault( e ):
    
    etype = type( e )
    
    value = ToString( e )
    
    trace_list = traceback.format_stack()
    
    trace = ''.join( trace_list )
    
    message = ToString( etype.__name__ ) + ': ' + ToString( value ) + os.linesep + ToString( trace )
    
    print( '' )
    print( 'The following exception occured at ' + ConvertTimestampToPrettyTime( GetNow() ) + ':' )
    
    try: print( message )
    except: print( repr( message ) )
    
    sys.stdout.flush()
    sys.stderr.flush()
    
    time.sleep( 1 )
    
ShowException = ShowExceptionDefault

def ShowTextDefault( text ):
    
    print( text )
    
ShowText = ShowTextDefault

def SplayListForDB( xs ): return '("' + '","'.join( ( ToString( x ) for x in xs ) ) + '")'

def SplitListIntoChunks( xs, n ):
    
    for i in xrange( 0, len( xs ), n ): yield xs[ i : i + n ]
    
def TimeHasPassed( timestamp ):
    
    return GetNow() > timestamp
    
def TimeHasPassedPrecise( precise_timestamp ):
    
    return GetNowPrecise() > precise_timestamp
    
def TimeUntil( timestamp ):
    
    return timestamp - GetNow()
    
def ToBytes( text_producing_object ):
    
    if type( text_producing_object ) == unicode: return text_producing_object.encode( 'utf-8' )
    else: return str( text_producing_object )
    
def ToString( text_producing_object ):
    
    if type( text_producing_object ) in ( str, unicode, bs4.element.NavigableString ): text = text_producing_object
    else:
        try: text = str( text_producing_object ) # dealing with exceptions, etc...
        except: text = repr( text_producing_object )
    
    try: return unicode( text )
    except:
        
        try: return text.decode( locale.getpreferredencoding() )
        except: return str( text )
        
    
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
        
    
    def IsAdmin( self ): return True in [ self.HasPermission( permission ) for permission in HC.ADMIN_PERMISSIONS ]
    
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
    
    def __repr__( self ): return 'Account Identifier: ' + ToString( ( self._type, self._data ) )
    
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

UNKNOWN_ACCOUNT_TYPE = AccountType( 'unknown account', [ HC.UNKNOWN_PERMISSION ], ( None, None ) )

def GetUnknownAccount( account_key = None ): return Account( account_key, UNKNOWN_ACCOUNT_TYPE, 0, None, 0, 0 )

class ClientToServerContentUpdatePackage( HydrusYAMLBase ):
    
    yaml_tag = u'!ClientToServerContentUpdatePackage'
    
    def __init__( self, content_data, hash_ids_to_hashes ):
        
        HydrusYAMLBase.__init__( self )
        
        # we need to flatten it from a collections.defaultdict to just a normal dict so it can be YAMLised
        
        self._content_data = {}
        
        for data_type in content_data:
            
            self._content_data[ data_type ] = {}
            
            for action in content_data[ data_type ]: self._content_data[ data_type ][ action ] = content_data[ data_type ][ action ]
            
        
        self._hash_ids_to_hashes = hash_ids_to_hashes
        
    
    def GetContentUpdates( self, for_client = False ):
        
        data_types = [ HC.CONTENT_TYPE_FILES, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ]
        actions = [ HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION, HC.CONTENT_UPDATE_DENY_PEND, HC.CONTENT_UPDATE_DENY_PETITION ]
        
        content_updates = []
        
        for ( data_type, action ) in itertools.product( data_types, actions ):
            
            munge_row = lambda row: row
            
            if for_client:
                
                if action == HC.CONTENT_UPDATE_PEND: new_action = HC.CONTENT_UPDATE_ADD
                elif action == HC.CONTENT_UPDATE_PETITION: new_action = HC.CONTENT_UPDATE_DELETE
                else: continue
                
                if data_type in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ) and action in ( HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ):
                    
                    munge_row = lambda ( pair, reason ): pair
                    
                elif data_type == HC.CONTENT_TYPE_FILES and action == HC.CONTENT_UPDATE_PETITION:
                    
                    munge_row = lambda ( hashes, reason ): hashes
                    
                elif data_type == HC.CONTENT_TYPE_MAPPINGS and action == HC.CONTENT_UPDATE_PETITION:
                    
                    munge_row = lambda ( tag, hashes, reason ): ( tag, hashes )
                    
                
            else: new_action = action
            
            content_updates.extend( [ ContentUpdate( data_type, new_action, munge_row( row ) ) for row in self.GetContentDataIterator( data_type, action ) ] )
            
        
        return content_updates
        
    
    def GetHashes( self ): return self._hash_ids_to_hashes.values()
    
    def GetContentDataIterator( self, data_type, action ):
        
        if data_type not in self._content_data or action not in self._content_data[ data_type ]: return ()
        
        data = self._content_data[ data_type ][ action ]
        
        if data_type == HC.CONTENT_TYPE_FILES:
            
            if action == HC.CONTENT_UPDATE_PETITION: return ( ( { self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids }, reason ) for ( hash_ids, reason ) in data )
            else: return ( { self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids } for hash_ids in ( data, ) )
            
        if data_type == HC.CONTENT_TYPE_MAPPINGS:
            
            if action == HC.CONTENT_UPDATE_PETITION: return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ], reason ) for ( tag, hash_ids, reason ) in data )
            else: return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( tag, hash_ids ) in data )
            
        else: return data.__iter__()
        
    
    def GetTags( self ):
        
        tags = set()
        
        try: tags.update( ( tag for ( tag, hash_ids ) in self._content_data[ HC.CONTENT_TYPE_MAPPINGS ][ HC.CONTENT_UPDATE_PEND ] ) )
        except: pass
        
        try: tags.update( ( tag for ( tag, hash_ids, reason ) in self._content_data[ HC.CONTENT_TYPE_MAPPINGS ][ HC.CONTENT_UPDATE_PETITION ] ) )
        except: pass
        
        return tags
        
    
    def IsEmpty( self ):
        
        num_total = 0
        
        for data_type in self._content_data:
            
            for action in self._content_data[ data_type ]: num_total += len( self._content_data[ data_type ][ action ] )
            
        
        return num_total == 0
        
    
class Content( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_CONTENT
    SERIALISABLE_VERSION = 1
    
    def __init__( self, content_type = None, content = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._content_type = content_type
        self._content = content
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._content_type, self._content ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Content: ' + self.ToString()
    
    def _GetSerialisableInfo( self ):
        
        def EncodeHashes( hs ):
            
            return [ h.encode( 'hex' ) for h in hs ]
            
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = self._content
            
            serialisable_content = EncodeHashes( hashes )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, hash ) = self._content
            
            serialisable_content = ( tag, hash.encode( 'hex' ) )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._content
            
            serialisable_content = ( tag, EncodeHashes( hashes ) )
            
        elif self._content_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            ( old_tag, new_tag ) = self._content
            
            serialisable_content = ( old_tag, new_tag )
            
        
        return ( self._content_type, serialisable_content )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        def DecodeHashes( hs ):
            
            return [ h.decode( 'hex' ) for h in hs ]
            
        
        ( self._content_type, serialisable_content ) = serialisable_info
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            serialisable_hashes = serialisable_content
            
            self._content = DecodeHashes( serialisable_hashes )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, serialisable_hash ) = serialisable_content
            
            self._content = ( tag, serialisable_hash.decode( 'hex' ) )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, serialisable_hashes ) = serialisable_content
            
            self._content = ( tag, DecodeHashes( serialisable_hashes ) )
            
        elif self._content_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ):
            
            ( old_tag, new_tag ) = serialisable_content
            
            self._content = ( old_tag, new_tag )
            
        
    
    def GetContent( self ):
        
        return self._content
        
    
    def GetContentType( self ):
        
        return self._content_type
        
    
    def GetHashes( self ):
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = self._content
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, hash ) = self._content
            
            return [ hash ]
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._content
            
        else:
            
            hashes = []
            
        
        return hashes
        
    
    def HasHashes( self ):
        
        return self._content_type in ( HC.CONTENT_TYPE_FILES, HC.CONTENT_TYPE_MAPPING, HC.CONTENT_TYPE_MAPPINGS )
        
    
    def ToString( self ):
        
        if self._content_type == HC.CONTENT_TYPE_FILES:
            
            hashes = self._content
            
            text = 'FILES: ' + ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPING:
            
            ( tag, hash ) = self._content
            
            text = 'MAPPING: ' + tag + ' for ' + hash.encode( 'hex' )
            
        elif self._content_type == HC.CONTENT_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._content
            
            text = 'MAPPINGS: ' + tag + ' for ' + ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
        elif self._content_type == HC.CONTENT_TYPE_TAG_PARENTS:
            
            ( child, parent ) = self._content
            
            text = 'PARENT: ' '"' + child + '" -> "' + parent + '"'
            
        elif self._content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
            
            ( old_tag, new_tag ) = self._content
            
            text = 'SIBLING: ' + '"' + old_tag + '" -> "' + new_tag + '"'
            
        
        return text
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_CONTENT ] = Content

class ContentUpdate( object ):
    
    def __init__( self, data_type, action, row ):
        
        self._data_type = data_type
        self._action = action
        self._row = row
        
    
    def __eq__( self, other ): return self._data_type == other._data_type and self._action == other._action and self._row == other._row
    
    def __ne__( self, other ): return not self.__eq__( other )
    
    def __repr__( self ): return 'Content Update: ' + ToString( ( self._data_type, self._action, self._row ) )
    
    def GetHashes( self ):
        
        if self._data_type == HC.CONTENT_TYPE_FILES:
            
            if self._action == HC.CONTENT_UPDATE_ADD:
                
                hash = self._row[0]
                
                hashes = set( ( hash, ) )
                
            elif self._action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_UNDELETE, HC.CONTENT_UPDATE_INBOX, HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_RESCIND_PETITION ): hashes = self._row
            elif self._action == HC.CONTENT_UPDATE_PETITION: ( hashes, reason ) = self._row
            
        elif self._data_type == HC.CONTENT_TYPE_MAPPINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADVANCED: hashes = set()
            elif self._action == HC.CONTENT_UPDATE_PETITION: ( tag, hashes, reason ) = self._row
            else: ( tag, hashes ) = self._row
            
        elif self._data_type in ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_TYPE_TAG_SIBLINGS ): hashes = set()
        elif self._data_type == HC.CONTENT_TYPE_RATINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADD: ( rating, hashes ) = self._row
            
        
        if type( hashes ) != set: hashes = set( hashes )
        
        return hashes
        
    
    def ToTuple( self ): return ( self._data_type, self._action, self._row )
    
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
    
    yaml_tag = u'!JobDatabase'
    
    def __init__( self, action, job_type, synchronous, *args, **kwargs ):
        
        self._action = action
        self._type = job_type
        self._synchronous = synchronous
        self._args = args
        self._kwargs = kwargs
        
        self._result = None
        self._result_ready = threading.Event()
        
    
    def GetAction( self ): return self._action
    
    def GetArgs( self ): return self._args
    
    def GetKWArgs( self ): return self._kwargs
    
    def GetResult( self ):
        
        while True:
            
            if self._result_ready.wait( 5 ) == True: break
            elif HydrusGlobals.model_shutdown: raise HydrusExceptions.ShutdownException( 'Application quit before db could serve result!' )
            
        
        if isinstance( self._result, HydrusExceptions.DBException ):
            
            ( text, gumpf, db_traceback ) = self._result.args
            
            trace_list = traceback.format_stack()
            
            caller_traceback = 'Stack Trace (most recent call last):' + os.linesep * 2 + os.linesep.join( trace_list )
            
            raise HydrusExceptions.DBException( text, caller_traceback, db_traceback )
            
        elif isinstance( self._result, Exception ):
            
            raise self._result
            
        else: return self._result
        
    
    def GetType( self ): return self._type
    
    def IsSynchronous( self ): return self._synchronous
    
    def PutResult( self, result ):
        
        self._result = result
        
        self._result_ready.set()
        
    
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
        
    
    def GetNumContentUpdates( self ):
        
        num = 0
        
        for data_type in self._content_data:
            
            for action in self._content_data[ data_type ]:
                
                num += len( self._content_data[ data_type ][ action ] )
                
            
        
        return num
        
    
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
        
    
    def IterateContentUpdates( self, as_if_pending = False ):
        
        data_types = [ HC.CONTENT_TYPE_FILES, HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ]
        actions = [ HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ]
        
        for ( data_type, action ) in itertools.product( data_types, actions ):
            
            for row in self.GetContentDataIterator( data_type, action ):
                
                yieldee_action = action
                
                if as_if_pending:
                    
                    if action == HC.CONTENT_UPDATE_ADD: yieldee_action = HC.CONTENT_UPDATE_PEND
                    elif action == HC.CONTENT_UPDATE_DELETE: continue
                    
                
                yield ContentUpdate( data_type, yieldee_action, row )
                
            
        
    
    def GetHashes( self ): return set( self._hash_ids_to_hashes.values() )
    
    def GetTags( self ):
        
        tags = set()
        
        tags.update( ( tag for ( tag, hash_ids ) in self.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.CURRENT ) ) )
        tags.update( ( tag for ( tag, hash_ids ) in self.GetContentDataIterator( HC.CONTENT_TYPE_MAPPINGS, HC.DELETED ) ) )
        
        tags.update( ( old_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.CURRENT ) ) )
        tags.update( ( new_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CURRENT ) ) )
        tags.update( ( old_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_TYPE_TAG_PARENTS, HC.DELETED ) ) )
        tags.update( ( new_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.DELETED ) ) )
        
        return tags
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVER_TO_CLIENT_CONTENT_UPDATE_PACKAGE ] = ServerToClientContentUpdatePackage

class ServerToClientPetition( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SERVER_TO_CLIENT_PETITION
    SERIALISABLE_VERSION = 1
    
    def __init__( self, action = None, petitioner_account_identifier = None, reason = None, contents = None ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._action = action
        self._petitioner_account_identifier = petitioner_account_identifier
        self._reason = reason
        self._contents = contents
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_petitioner_account_identifier = self._petitioner_account_identifier.GetSerialisableTuple()
        serialisable_contents = [ content.GetSerialisableTuple() for content in self._contents ]
        
        return ( self._action, serialisable_petitioner_account_identifier, self._reason, serialisable_contents )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._action, serialisable_petitioner_account_identifier, self._reason, serialisable_contents ) = serialisable_info
        
        self._petitioner_account_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_petitioner_account_identifier )
        self._contents = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_content ) for serialisable_content in serialisable_contents ]
        
    
    def GetActionTextAndColour( self ):
        
        action_text = ''
        
        if self._action == HC.CONTENT_UPDATE_PEND:
            
            action_text += 'ADD'
            action_colour = ( 0, 128, 0 )
            
        elif self._action == HC.CONTENT_UPDATE_PETITION:
            
            action_text += 'DELETE'
            action_colour = ( 128, 0, 0 )
            
        
        return ( action_text, action_colour )
        
    
    def GetApproval( self, filtered_contents ):
        
        return ConvertContentsToClientToServerContentUpdatePackage( self._action, filtered_contents, reason = self._reason )
        
    
    def GetContents( self ):
        
        return self._contents
        
    
    def GetDenial( self, filtered_contents ):
        
        if self._action == HC.CONTENT_UPDATE_PEND:
            
            denial_action = HC.CONTENT_UPDATE_DENY_PEND
            
        elif self._action == HC.CONTENT_UPDATE_PETITION:
            
            denial_action = HC.CONTENT_UPDATE_DENY_PETITION
            
        
        return ConvertContentsToClientToServerContentUpdatePackage( denial_action, filtered_contents )
        
    
    def GetPetitionerIdentifier( self ):
        
        return self._petitioner_account_identifier
        
    
    def GetReason( self ):
        
        return self._reason
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVER_TO_CLIENT_PETITION ] = ServerToClientPetition

class ServerToClientServiceUpdatePackage( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SERVER_TO_CLIENT_SERVICE_UPDATE_PACKAGE
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._service_data = {}
        
    
    def _GetSerialisableInfo( self ):
        
        return self._service_data.items()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._service_data = dict( serialisable_info )
        
    
    def GetBegin( self ):
        
        ( begin, end ) = self._service_data[ HC.SERVICE_UPDATE_BEGIN_END ]
        
        return begin
        
    
    def GetNextBegin( self ):
        
        ( begin, end ) = self._service_data[ HC.SERVICE_UPDATE_BEGIN_END ]
        
        return end + 1
        
    
    def GetSubindexCount( self ):
        
        return self._service_data[ HC.SERVICE_UPDATE_SUBINDEX_COUNT ]
        
    
    def IterateServiceUpdates( self ):
        
        if HC.SERVICE_UPDATE_NEWS in self._service_data:
            
            news_rows = self._service_data[ HC.SERVICE_UPDATE_NEWS ]
            
            yield ServiceUpdate( HC.SERVICE_UPDATE_NEWS, news_rows )
            
        
    
    def SetBeginEnd( self, begin, end ):
        
        self._service_data[ HC.SERVICE_UPDATE_BEGIN_END ] = ( begin, end )
        
    
    def SetNews( self, news_rows ):
        
        self._service_data[ HC.SERVICE_UPDATE_NEWS ] = news_rows
        
    
    def SetSubindexCount( self, count ):
        
        self._service_data[ HC.SERVICE_UPDATE_SUBINDEX_COUNT ] = count
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SERVER_TO_CLIENT_SERVICE_UPDATE_PACKAGE ] = ServerToClientServiceUpdatePackage

class ServiceUpdate( object ):
    
    def __init__( self, action, row = None ):
        
        self._action = action
        self._row = row
        
    
    def ToTuple( self ): return ( self._action, self._row )
    
