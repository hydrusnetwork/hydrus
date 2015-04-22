import bs4
import collections
import HydrusConstants as HC
import HydrusExceptions
import HydrusGlobals
import locale
import os
import sqlite3
import sys
import threading
import time
import traceback
import yaml
import wx
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
    
def ConvertServiceKeysToContentUpdatesToPrettyString( service_keys_to_content_updates ):
    
    num_files = 0
    actions = set()
    locations = set()
    
    extra_words = ''
    
    for ( service_key, content_updates ) in service_keys_to_content_updates.items():
        
        if len( content_updates ) > 0:
            
            name = wx.GetApp().GetManager( 'services' ).GetService( service_key ).GetName()
            
            locations.add( name )
            
        
        for content_update in content_updates:
            
            ( data_type, action, row ) = content_update.ToTuple()
            
            if data_type == HC.CONTENT_DATA_TYPE_MAPPINGS: extra_words = ' tags for'
            
            actions.add( HC.content_update_string_lookup[ action ] )
            
            num_files += len( content_update.GetHashes() )
            
        
    
    s = ', '.join( locations ) + '->' + ', '.join( actions ) + extra_words + ' ' + ConvertIntToPrettyString( num_files ) + ' files'
    
    return s
    
def ConvertShortcutToPrettyShortcut( modifier, key ):
    
    if modifier == wx.ACCEL_NORMAL: modifier = ''
    elif modifier == wx.ACCEL_ALT: modifier = 'alt'
    elif modifier == wx.ACCEL_CTRL: modifier = 'ctrl'
    elif modifier == wx.ACCEL_SHIFT: modifier = 'shift'
    
    if key in range( 65, 91 ): key = chr( key + 32 ) # + 32 for converting ascii A -> a
    elif key in range( 97, 123 ): key = chr( key )
    else: key = HC.wxk_code_string_lookup[ key ]
    
    return ( modifier, key )
    
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
    
    if timestamp is None or timestamp == 0: return 'not updated'
    
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
    
def ConvertZoomToPercentage( zoom ):
    
    zoom = zoom * 100.0
    
    pretty_zoom = '%.0f' % zoom + '%'
    
    return pretty_zoom
    
def DebugPrint( debug_info ):
    
    print( debug_info )
    
    sys.stdout.flush()
    sys.stderr.flush()
    
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
    
def MergeKeyToListDicts( key_to_list_dicts ):
    
    result = collections.defaultdict( list )
    
    for key_to_list_dict in key_to_list_dicts:
        
        for ( key, value ) in key_to_list_dict.items(): result[ key ].extend( value )
        
    
    return result
    
def ShowExceptionDefault( e ):
    
    etype = type( e )
    
    value = ToString( e )
    
    trace_list = traceback.format_stack()
    
    trace = ''.join( trace_list )
    
    message = ToString( etype.__name__ ) + ': ' + ToString( value ) + os.linesep + ToString( trace )
    
    try: print( message )
    except: print( repr( message ) )
    
ShowException = ShowExceptionDefault

def ShowTextDefault( text ):
    
    print( text )
    
ShowText = ShowTextDefault

def SplayListForDB( xs ): return '("' + '","'.join( ( ToString( x ) for x in xs ) ) + '")'

def SplitListIntoChunks( xs, n ):
    
    for i in xrange( 0, len( xs ), n ): yield xs[ i : i + n ]
    
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
            else: return GetNow() > expires
            
        
    
    def _IsBytesExceeded( self ):
        
        account_type = self._info[ 'account_type' ]
        
        max_num_bytes = account_type.GetMaxBytes()
        
        used_bytes = self._info[ 'used_bytes' ]
        
        return max_num_bytes is not None and used_bytes > max_num_bytes
        
    
    def _IsExpired( self ):
        
        if self._info[ 'expires' ] is None: return False
        else: return GetNow() > self._info[ 'expires' ]
        
    
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
        else: return ConvertIntToPrettyString( used_requests ) + '/' + ConvertIntToPrettyString( max_num_requests ) + ' requests used this month'
        
    
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

class AccountIdentifier( HydrusYAMLBase ):
    
    TYPE_ACCOUNT_KEY = 1
    TYPE_HASH = 2
    TYPE_MAPPING = 3
    TYPE_SIBLING = 4
    TYPE_PARENT = 5
    
    yaml_tag = u'!AccountIdentifier'
    
    def __init__( self, account_key = None, hash = None, tag = None ):
        
        HydrusYAMLBase.__init__( self )
        
        if account_key is not None:
            
            self._type = self.TYPE_ACCOUNT_KEY
            self._data = account_key
            
        elif hash is not None:
            
            if tag is not None:
                
                self._type = self.TYPE_MAPPING
                self._data = ( hash, tag )
                
            else:
                
                self._type = self.TYPE_HASH
                self._data = hash
                
            
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._type, self._data ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Account Identifier: ' + ToString( ( self._type, self._data ) )
    
    def GetData( self ): return self._data
    
    def HasAccountKey( self ): return self._type == self.TYPE_ACCOUNT_KEY
    
    def HasHash( self ): return self._type == self.TYPE_HASH
    
    def HasMapping( self ): return self._type == self.TYPE_MAPPING
    
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

class ClientToServerUpdate( HydrusYAMLBase ):
    
    yaml_tag = u'!ClientToServerUpdate'
    
    def __init__( self, content_data, hash_ids_to_hashes ):
        
        HydrusYAMLBase.__init__( self )
        
        # we need to flatten it from a collections.defaultdict to just a normal dict so it can be YAMLised
        
        self._content_data = {}
        
        for data_type in content_data:
            
            self._content_data[ data_type ] = {}
            
            for action in content_data[ data_type ]: self._content_data[ data_type ][ action ] = content_data[ data_type ][ action ]
            
        
        self._hash_ids_to_hashes = hash_ids_to_hashes
        
    
    def GetContentUpdates( self, for_client = False ):
        
        data_types = [ HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_DATA_TYPE_TAG_PARENTS ]
        actions = [ HC.CONTENT_UPDATE_PENDING, HC.CONTENT_UPDATE_PETITION, HC.CONTENT_UPDATE_DENY_PEND, HC.CONTENT_UPDATE_DENY_PETITION ]
        
        content_updates = []
        
        for ( data_type, action ) in itertools.product( data_types, actions ):
            
            munge_row = lambda row: row
            
            if for_client:
                
                if action == HC.CONTENT_UPDATE_PENDING: new_action = HC.CONTENT_UPDATE_ADD
                elif action == HC.CONTENT_UPDATE_PETITION: new_action = HC.CONTENT_UPDATE_DELETE
                else: continue
                
                if data_type in ( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_DATA_TYPE_TAG_PARENTS ) and action in ( HC.CONTENT_UPDATE_PENDING, HC.CONTENT_UPDATE_PETITION ):
                    
                    munge_row = lambda ( pair, reason ): pair
                    
                elif data_type == HC.CONTENT_DATA_TYPE_FILES and action == HC.CONTENT_UPDATE_PETITION:
                    
                    munge_row = lambda ( hashes, reason ): hashes
                    
                elif data_type == HC.CONTENT_DATA_TYPE_MAPPINGS and action == HC.CONTENT_UPDATE_PETITION:
                    
                    munge_row = lambda ( tag, hashes, reason ): ( tag, hashes )
                    
                
            else: new_action = action
            
            content_updates.extend( [ ContentUpdate( data_type, new_action, munge_row( row ) ) for row in self.GetContentDataIterator( data_type, action ) ] )
            
        
        return content_updates
        
    
    def GetHashes( self ): return self._hash_ids_to_hashes.values()
    
    def GetContentDataIterator( self, data_type, action ):
        
        if data_type not in self._content_data or action not in self._content_data[ data_type ]: return ()
        
        data = self._content_data[ data_type ][ action ]
        
        if data_type == HC.CONTENT_DATA_TYPE_FILES:
            
            if action == HC.CONTENT_UPDATE_PETITION: return ( ( { self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids }, reason ) for ( hash_ids, reason ) in data )
            else: return ( { self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids } for hash_ids in ( data, ) )
            
        if data_type == HC.CONTENT_DATA_TYPE_MAPPINGS:
            
            if action == HC.CONTENT_UPDATE_PETITION: return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ], reason ) for ( tag, hash_ids, reason ) in data )
            else: return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( tag, hash_ids ) in data )
            
        else: return data.__iter__()
        
    
    def GetTags( self ):
        
        tags = set()
        
        try: tags.update( ( tag for ( tag, hash_ids ) in self._content_data[ HC.CONTENT_DATA_TYPE_MAPPINGS ][ HC.CONTENT_UPDATE_PENDING ] ) )
        except: pass
        
        try: tags.update( ( tag for ( tag, hash_ids, reason ) in self._content_data[ HC.CONTENT_DATA_TYPE_MAPPINGS ][ HC.CONTENT_UPDATE_PETITION ] ) )
        except: pass
        
        return tags
        
    
    def IsEmpty( self ):
        
        num_total = 0
        
        for data_type in self._content_data:
            
            for action in self._content_data[ data_type ]: num_total += len( self._content_data[ data_type ][ action ] )
            
        
        return num_total == 0
        
    
class ContentUpdate( object ):
    
    def __init__( self, data_type, action, row ):
        
        self._data_type = data_type
        self._action = action
        self._row = row
        
    
    def __eq__( self, other ): return self._data_type == other._data_type and self._action == other._action and self._row == other._row
    
    def __ne__( self, other ): return not self.__eq__( other )
    
    def __repr__( self ): return 'Content Update: ' + ToString( ( self._data_type, self._action, self._row ) )
    
    def GetHashes( self ):
        
        if self._data_type == HC.CONTENT_DATA_TYPE_FILES:
            
            if self._action == HC.CONTENT_UPDATE_ADD:
                
                hash = self._row[0]
                
                hashes = set( ( hash, ) )
                
            elif self._action in ( HC.CONTENT_UPDATE_ARCHIVE, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_INBOX, HC.CONTENT_UPDATE_PENDING, HC.CONTENT_UPDATE_RESCIND_PENDING, HC.CONTENT_UPDATE_RESCIND_PETITION ): hashes = self._row
            elif self._action == HC.CONTENT_UPDATE_PETITION: ( hashes, reason ) = self._row
            
        elif self._data_type == HC.CONTENT_DATA_TYPE_MAPPINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADVANCED: hashes = set()
            elif self._action == HC.CONTENT_UPDATE_PETITION: ( tag, hashes, reason ) = self._row
            else: ( tag, hashes ) = self._row
            
        elif self._data_type in ( HC.CONTENT_DATA_TYPE_TAG_PARENTS, HC.CONTENT_DATA_TYPE_TAG_SIBLINGS ): hashes = set()
        elif self._data_type == HC.CONTENT_DATA_TYPE_RATINGS:
            
            if self._action == HC.CONTENT_UPDATE_ADD: ( rating, hashes ) = self._row
            elif self._action == HC.CONTENT_UPDATE_RATINGS_FILTER: ( min, max, hashes ) = self._row
            
        
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
            elif HydrusGlobals.shutdown: raise Exception( 'Application quit before db could serve result!' )
            
        
        if isinstance( self._result, Exception ):
            
            if isinstance( self._result, HydrusExceptions.DBException ):
                
                ( text, gumpf, db_traceback ) = self._result.args
                
                trace_list = traceback.format_stack()
                
                caller_traceback = 'Stack Trace (most recent call last):' + os.linesep * 2 + os.linesep.join( trace_list )
                
                raise HydrusExceptions.DBException( text, caller_traceback, db_traceback )
                
            else: raise self._result
            
        else: return self._result
        
    
    def GetType( self ): return self._type
    
    def IsSynchronous( self ): return self._synchronous
    
    def PutResult( self, result ):
        
        self._result = result
        
        self._result_ready.set()
        
    
class JobKey( object ):
    
    def __init__( self, pausable = False, cancellable = False ):
        
        self._key = os.urandom( 32 )
        
        self._pausable = pausable
        self._cancellable = cancellable
        
        self._deleted = threading.Event()
        self._begun = threading.Event()
        self._done = threading.Event()
        self._cancelled = threading.Event()
        self._paused = threading.Event()
        
        self._variable_lock = threading.Lock()
        self._variables = dict()
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return self._key.__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def Begin( self ): self._begun.set()
    
    def Cancel( self ):
        
        self._cancelled.set()
        
        self.Finish()
        
    
    def Delete( self ):
        
        self.Finish()
        
        self._deleted.set()
        
    
    def DeleteVariable( self, name ):
        
        with self._variable_lock:
            
            if name in self._variables: del self._variables[ name ]
            
        
        time.sleep( 0.00001 )
        
    
    def Finish( self ): self._done.set()
    
    def GetKey( self ): return self._key
    
    def GetVariable( self, name ):
        
        with self._variable_lock: return self._variables[ name ]
        
    
    def HasVariable( self, name ):
        
        with self._variable_lock: return name in self._variables
        
    
    def IsBegun( self ): return self._begun.is_set()
    
    def IsCancellable( self ): return self._cancellable and not self.IsDone()
    
    def IsCancelled( self ): return HydrusGlobals.shutdown or self._cancelled.is_set()
    
    def IsDeleted( self ): return HydrusGlobals.shutdown or self._deleted.is_set()
    
    def IsDone( self ): return HydrusGlobals.shutdown or self._done.is_set()
    
    def IsPausable( self ): return self._pausable and not self.IsDone()
    
    def IsPaused( self ): return self._paused.is_set() and not self.IsDone()
    
    def IsWorking( self ): return self.IsBegun() and not self.IsDone()
    
    def Pause( self ): self._paused.set()
    
    def PauseResume( self ):
        
        if self._paused.is_set(): self._paused.clear()
        else: self._paused.set()
        
    
    def Resume( self ): self._paused.clear()
    
    def SetCancellable( self, value ): self._cancellable = value
    
    def SetPausable( self, value ): self._pausable = value
    
    def SetVariable( self, name, value ):
        
        with self._variable_lock: self._variables[ name ] = value
        
        time.sleep( 0.00001 )
        
    
    def ToString( self ):
        
        stuff_to_print = []
        
        with self._variable_lock:
            
            if 'popup_message_title' in self._variables: stuff_to_print.append( self._variables[ 'popup_message_title' ] )
            
            if 'popup_message_text_1' in self._variables: stuff_to_print.append( self._variables[ 'popup_message_text_1' ] )
            
            if 'popup_message_text_2' in self._variables: stuff_to_print.append( self._variables[ 'popup_message_text_2' ] )
            
            if 'popup_message_traceback' in self._variables: stuff_to_print.append( self._variables[ 'popup_message_traceback' ] )
            
            if 'popup_message_caller_traceback' in self._variables: stuff_to_print.append( self._variables[ 'popup_message_caller_traceback' ] )
            
            if 'popup_message_db_traceback' in self._variables: stuff_to_print.append( self._variables[ 'popup_message_db_traceback' ] )
            
        
        return os.linesep.join( stuff_to_print )
        
    
    def WaitOnPause( self ):
        
        while self._paused.is_set():
            
            time.sleep( 0.1 )
            
            if HydrusGlobals.shutdown or self.IsDone(): return
            
        
    
class ServerToClientPetition( HydrusYAMLBase ):
    
    yaml_tag = u'!ServerToClientPetition'
    
    def __init__( self, petition_type, action, petitioner_account_identifier, petition_data, reason ):
        
        HydrusYAMLBase.__init__( self )
        
        self._petition_type = petition_type
        self._action = action
        self._petitioner_account_identifier = petitioner_account_identifier
        self._petition_data = petition_data
        self._reason = reason
        
    
    def GetApproval( self, reason = None ):
        
        if reason is None: reason = self._reason
        
        if self._petition_type == HC.CONTENT_DATA_TYPE_FILES: hashes = self._petition_data
        elif self._petition_type == HC.CONTENT_DATA_TYPE_MAPPINGS: ( tag, hashes ) = self._petition_data
        else: hashes = set()
        
        hash_ids_to_hashes = dict( enumerate( hashes ) )
        
        hash_ids = hash_ids_to_hashes.keys()
        
        content_data = GetEmptyDataDict()
        
        if self._petition_type == HC.CONTENT_DATA_TYPE_FILES: row = ( hash_ids, reason )
        elif self._petition_type == HC.CONTENT_DATA_TYPE_MAPPINGS: row = ( tag, hash_ids, reason )
        else:
            
            ( old, new ) = self._petition_data
            
            row = ( ( old, new ), reason )
            
        
        content_data[ self._petition_type ][ self._action ].append( row )
        
        return ClientToServerUpdate( content_data, hash_ids_to_hashes )
        
    
    def GetDenial( self ):
        
        if self._petition_type == HC.CONTENT_DATA_TYPE_FILES: hashes = self._petition_data
        elif self._petition_type == HC.CONTENT_DATA_TYPE_MAPPINGS: ( tag, hashes ) = self._petition_data
        else: hashes = set()
        
        hash_ids_to_hashes = dict( enumerate( hashes ) )
        
        hash_ids = hash_ids_to_hashes.keys()
        
        if self._petition_type == HC.CONTENT_DATA_TYPE_FILES: row_list = hash_ids
        elif self._petition_type == HC.CONTENT_DATA_TYPE_MAPPINGS: row_list = [ ( tag, hash_ids ) ]
        else: row_list = [ self._petition_data ]
        
        content_data = GetEmptyDataDict()
        
        if self._action == HC.CONTENT_UPDATE_PENDING: denial_action = HC.CONTENT_UPDATE_DENY_PEND
        elif self._action == HC.CONTENT_UPDATE_PETITION: denial_action = HC.CONTENT_UPDATE_DENY_PETITION
        
        content_data[ self._petition_type ][ denial_action ] = row_list
        
        return ClientToServerUpdate( content_data, hash_ids_to_hashes )
        
    
    def GetHashes( self ):
        
        if self._petition_type == HC.CONTENT_DATA_TYPE_FILES: hashes = self._petition_data
        elif self._petition_type == HC.CONTENT_DATA_TYPE_MAPPINGS: ( tag, hashes ) = self._petition_data
        else: hashes = set()
        
        return hashes
        
    
    def GetPetitionerIdentifier( self ): return self._petitioner_account_identifier
    
    def GetPetitionString( self ):
        
        if self._action == HC.CONTENT_UPDATE_PENDING: action_word = 'Add '
        elif self._action == HC.CONTENT_UPDATE_PETITION: action_word = 'Remove '
        
        if self._petition_type == HC.CONTENT_DATA_TYPE_FILES:
            
            hashes = self._petition_data
            
            content_phrase = ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
        elif self._petition_type == HC.CONTENT_DATA_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._petition_data
            
            content_phrase = tag + ' for ' + ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
        elif self._petition_type == HC.CONTENT_DATA_TYPE_TAG_SIBLINGS:
            
            ( old_tag, new_tag ) = self._petition_data
            
            content_phrase = 'sibling ' + old_tag + '->' + new_tag
            
        elif self._petition_type == HC.CONTENT_DATA_TYPE_TAG_PARENTS:
            
            ( old_tag, new_tag ) = self._petition_data
            
            content_phrase = 'parent ' + old_tag + '->' + new_tag
            
        
        return action_word + content_phrase + os.linesep * 2 + self._reason
        
    
class ServerToClientUpdate( HydrusYAMLBase ):

    yaml_tag = u'!ServerToClientUpdate'
    
    def __init__( self, service_data, content_data, hash_ids_to_hashes ):
        
        HydrusYAMLBase.__init__( self )
        
        self._service_data = service_data
        
        self._content_data = {}
        
        for data_type in content_data:
            
            self._content_data[ data_type ] = {}
            
            for action in content_data[ data_type ]: self._content_data[ data_type ][ action ] = content_data[ data_type ][ action ]
            
        
        self._hash_ids_to_hashes = hash_ids_to_hashes
        
    
    def GetBeginEnd( self ):
        
        ( begin, end ) = self._service_data[ HC.SERVICE_UPDATE_BEGIN_END ]
        
        return ( begin, end )
        
    
    def GetContentDataIterator( self, data_type, action ):
        
        if data_type not in self._content_data or action not in self._content_data[ data_type ]: return ()
        
        data = self._content_data[ data_type ][ action ]
        
        if data_type == HC.CONTENT_DATA_TYPE_FILES:
            
            if action == HC.CONTENT_UPDATE_ADD: return ( ( self._hash_ids_to_hashes[ hash_id ], size, mime, timestamp, width, height, duration, num_frames, num_words ) for ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in data )
            else: return ( { self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids } for hash_ids in ( data, ) )
            
        elif data_type == HC.CONTENT_DATA_TYPE_MAPPINGS: return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( tag, hash_ids ) in data )
        else: return data.__iter__()
        
    
    def GetNumContentUpdates( self ):
        
        num = 0
        
        data_types = [ HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_DATA_TYPE_TAG_PARENTS ]
        actions = [ HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ]
        
        for ( data_type, action ) in itertools.product( data_types, actions ):
            
            for row in self.GetContentDataIterator( data_type, action ): num += 1
            
        
        return num
        
    
    # this needs work!
    # we need a universal content_update for both client and server
    def IterateContentUpdates( self, as_if_pending = False ):
        
        data_types = [ HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CONTENT_DATA_TYPE_TAG_PARENTS ]
        actions = [ HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE ]
        
        for ( data_type, action ) in itertools.product( data_types, actions ):
            
            for row in self.GetContentDataIterator( data_type, action ):
                
                yieldee_action = action
                
                if as_if_pending:
                    
                    if action == HC.CONTENT_UPDATE_ADD: yieldee_action = HC.CONTENT_UPDATE_PENDING
                    elif action == HC.CONTENT_UPDATE_DELETE: continue
                    
                
                yield ContentUpdate( data_type, yieldee_action, row )
                
            
        
    
    def IterateServiceUpdates( self ):
        
        service_types = [ HC.SERVICE_UPDATE_NEWS ]
        
        for service_type in service_types:
            
            if service_type in self._service_data:
                
                data = self._service_data[ service_type ]
                
                yield ServiceUpdate( service_type, data )
                
            
        
    
    def GetHashes( self ): return set( self._hash_ids_to_hashes.values() )
    
    def GetTags( self ):
        
        tags = set()
        
        tags.update( ( tag for ( tag, hash_ids ) in self.GetContentDataIterator( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CURRENT ) ) )
        tags.update( ( tag for ( tag, hash_ids ) in self.GetContentDataIterator( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.DELETED ) ) )
        
        tags.update( ( old_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CURRENT ) ) )
        tags.update( ( new_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.CURRENT ) ) )
        tags.update( ( old_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.DELETED ) ) )
        tags.update( ( new_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( HC.CONTENT_DATA_TYPE_TAG_SIBLINGS, HC.DELETED ) ) )
        
        return tags
        
    
    def GetServiceData( self, service_type ): return self._service_data[ service_type ]
    
class ServiceUpdate( object ):
    
    def __init__( self, action, row = None ):
        
        self._action = action
        self._row = row
        
    
    def ToTuple( self ): return ( self._action, self._row )

class Predicate( HydrusYAMLBase ):
    
    yaml_tag = u'!Predicate'
    
    def __init__( self, predicate_type, value, inclusive = True, counts = None ):
        
        if counts is None: counts = {}
        
        self._predicate_type = predicate_type
        self._value = value
        
        self._inclusive = inclusive
        self._counts = {}
        
        self._counts[ HC.CURRENT ] = 0
        self._counts[ HC.PENDING ] = 0
        
        for ( current_or_pending, count ) in counts.items(): self.AddToCount( current_or_pending, count )
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._predicate_type, self._value ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Predicate: ' + ToString( ( self._predicate_type, self._value, self._counts ) )
    
    def AddToCount( self, current_or_pending, count ): self._counts[ current_or_pending ] += count
    
    def GetCopy( self ): return Predicate( self._predicate_type, self._value, self._inclusive, self._counts )
    
    def GetCountlessCopy( self ): return Predicate( self._predicate_type, self._value, self._inclusive )
    
    def GetCount( self, current_or_pending = None ):
        
        if current_or_pending is None: return sum( self._counts.values() )
        else: return self._counts[ current_or_pending ]
        
    
    def GetInclusive( self ):
        
        # patch from an upgrade mess-up ~v144
        if not hasattr( self, '_inclusive' ):
            
            if self._predicate_type != HC.PREDICATE_TYPE_SYSTEM:
                
                ( operator, value ) = self._value
                
                self._value = value
                
                self._inclusive = operator == '+'
                
            else: self._inclusive = True
            
        
        return self._inclusive
        
    
    def GetInfo( self ): return ( self._predicate_type, self._value, self._inclusive )
    
    def GetPredicateType( self ): return self._predicate_type
    
    def GetUnicode( self, with_count = True ):
        
        count_text = u''
        
        if with_count:
            
            if self._counts[ HC.CURRENT ] > 0: count_text += u' (' + ConvertIntToPrettyString( self._counts[ HC.CURRENT ] ) + u')'
            if self._counts[ HC.PENDING ] > 0: count_text += u' (+' + ConvertIntToPrettyString( self._counts[ HC.PENDING ] ) + u')'
            
        
        if self._predicate_type == HC.PREDICATE_TYPE_SYSTEM:
            
            ( system_predicate_type, info ) = self._value
            
            if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_EVERYTHING: base = u'system:everything'
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_INBOX: base = u'system:inbox'
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_ARCHIVE: base = u'system:archive'
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_UNTAGGED: base = u'system:untagged'
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_LOCAL: base = u'system:local'
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL: base = u'system:not local'
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_DIMENSIONS: base = u'system:dimensions'
            elif system_predicate_type in ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, HC.SYSTEM_PREDICATE_TYPE_WIDTH, HC.SYSTEM_PREDICATE_TYPE_HEIGHT, HC.SYSTEM_PREDICATE_TYPE_DURATION, HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS ):
                
                if system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS: base = u'system:number of tags'
                elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_WIDTH: base = u'system:width'
                elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_HEIGHT: base = u'system:height'
                elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_DURATION: base = u'system:duration'
                elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS: base = u'system:number of words'
                
                if info is not None:
                    
                    ( operator, value ) = info
                    
                    base += u' ' + operator + u' ' + ConvertIntToPrettyString( value )
                    
                
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_RATIO:
                
                base = u'system:ratio'
                
                if info is not None:
                    
                    ( operator, ratio_width, ratio_height ) = info
                    
                    base += u' ' + operator + u' ' + ToString( ratio_width ) + u':' + ToString( ratio_height )
                    
                
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_SIZE:
                
                base = u'system:size'
                
                if info is not None:
                    
                    ( operator, size, unit ) = info
                    
                    base += u' ' + operator + u' ' + ToString( size ) + ConvertIntToUnit( unit )
                    
                
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_LIMIT:
                
                base = u'system:limit'
                
                if info is not None:
                    
                    value = info
                    
                    base += u' is ' + ConvertIntToPrettyString( value )
                    
                
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_AGE:
                
                base = u'system:age'
                
                if info is not None:
                    
                    ( operator, years, months, days, hours ) = info
                    
                    base += u' ' + operator + u' ' + ToString( years ) + u'y' + ToString( months ) + u'm' + ToString( days ) + u'd' + ToString( hours ) + u'h'
                    
                    
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_NUM_PIXELS:
                
                base = u'system:num_pixels'
                
                if info is not None:
                    
                    ( operator, num_pixels, unit ) = info
                    
                    base += u' ' + operator + u' ' + ToString( num_pixels ) + ' ' + ConvertIntToPixels( unit )
                    
                
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_HASH:
                
                base = u'system:hash'
                
                if info is not None:
                    
                    hash = info
                    
                    base += u' is ' + hash.encode( 'hex' )
                    
                
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_MIME:
                
                base = u'system:mime'
                
                if info is not None:
                    
                    mime = info
                    
                    base += u' is ' + HC.mime_string_lookup[ mime ]
                    
                
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_RATING:
                
                base = u'system:rating'
                
                if info is not None:
                    
                    ( service_key, operator, value ) = info
                    
                    service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
                    
                    base += u' for ' + service.GetName() + u' ' + operator + u' ' + ToString( value )
                    
                
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO:
                
                base = u'system:similar to'
                
                if info is not None:
                    
                    ( hash, max_hamming ) = info
                    
                    base += u' ' + hash.encode( 'hex' ) + u' using max hamming of ' + ToString( max_hamming )
                    
                
            elif system_predicate_type == HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE:
                
                base = u'system:'
                
                if info is None:
                    
                    base += 'file service'
                    
                else:
                    
                    ( operator, current_or_pending, service_key ) = info
                    
                    if operator == True: base += u'is'
                    else: base += u'is not'
                    
                    if current_or_pending == HC.PENDING: base += u' pending to '
                    else: base += u' currently in '
                    
                    service = wx.GetApp().GetManager( 'services' ).GetService( service_key )
                    
                    base += service.GetName()
                    
                
            
            base += count_text
            
        elif self._predicate_type == HC.PREDICATE_TYPE_TAG:
            
            tag = self._value
            
            if not self._inclusive: base = u'-'
            else: base = u''
            
            base += tag
            
            base += count_text
            
            siblings_manager = wx.GetApp().GetManager( 'tag_siblings' )
            
            sibling = siblings_manager.GetSibling( tag )
            
            if sibling is not None: base += u' (will display as ' + sibling + ')'
            
        elif self._predicate_type == HC.PREDICATE_TYPE_PARENT:
            
            base = '    '
            
            tag = self._value
            
            base += tag
            
            base += count_text
            
        elif self._predicate_type == HC.PREDICATE_TYPE_NAMESPACE:
            
            namespace = self._value
            
            if not self._inclusive: base = u'-'
            else: base = u''
            
            base += namespace + u':*'
            
        elif self._predicate_type == HC.PREDICATE_TYPE_WILDCARD:
            
            wildcard = self._value
            
            if not self._inclusive: base = u'-'
            else: base = u''
            
            base += wildcard
            
        
        return base
        
    
    def GetValue( self ): return self._value
    
    def SetInclusive( self, inclusive ): self._inclusive = inclusive

def ReadFileLikeAsBlocks( f, block_size ):
    
    next_block = f.read( block_size )
    
    while next_block != '':
        
        yield next_block
        
        next_block = f.read( block_size )
    