import collections
import httplib
import HydrusPubSub
import locale
import os
import Queue
import re
import sqlite3
import sys
import threading
import time
import traceback
import urlparse
import wx
import yaml

BASE_DIR = sys.path[0]

DB_DIR = BASE_DIR + os.path.sep + 'db'
CLIENT_FILES_DIR = DB_DIR + os.path.sep + 'client_files'
SERVER_FILES_DIR = DB_DIR + os.path.sep + 'server_files'
CLIENT_THUMBNAILS_DIR = DB_DIR + os.path.sep + 'client_thumbnails'
SERVER_THUMBNAILS_DIR = DB_DIR + os.path.sep + 'server_thumbnails'
SERVER_MESSAGES_DIR = DB_DIR + os.path.sep + 'server_messages'
SERVER_UPDATES_DIR = DB_DIR + os.path.sep + 'server_updates'
LOGS_DIR = BASE_DIR + os.path.sep + 'logs'
STATIC_DIR = BASE_DIR + os.path.sep + 'static'
TEMP_DIR = BASE_DIR + os.path.sep + 'temp'

# Misc

NETWORK_VERSION = 9
SOFTWARE_VERSION = 66

UNSCALED_THUMBNAIL_DIMENSIONS = ( 200, 200 )

HYDRUS_KEY_LENGTH = 32

UPDATE_DURATION = 100000

expirations = [ ( 'one month', 31 * 86400 ), ( 'three months', 3 * 31 * 86400 ), ( 'six months', 6 * 31 * 86400 ), ( 'one year', 12 * 31 * 86400 ), ( 'two years', 24 * 31 * 86400 ), ( 'five years', 60 * 31 * 86400 ), ( 'does not expire', None ) ]

shutdown = False
is_first_start = False

# Enums

CONTENT_UPDATE_ADD = 0
CONTENT_UPDATE_DELETE = 1
CONTENT_UPDATE_PENDING = 2
CONTENT_UPDATE_RESCIND_PENDING = 3
CONTENT_UPDATE_PETITION = 4
CONTENT_UPDATE_RESCIND_PETITION = 5
CONTENT_UPDATE_EDIT_LOG = 6
CONTENT_UPDATE_ARCHIVE = 7
CONTENT_UPDATE_INBOX = 8
CONTENT_UPDATE_RATING = 9
CONTENT_UPDATE_RATINGS_FILTER = 10

GET_DATA = 0
POST_DATA = 1
POST_PETITIONS = 2
RESOLVE_PETITIONS = 3
MANAGE_USERS = 4
GENERAL_ADMIN = 5
EDIT_SERVICES = 6

CREATABLE_PERMISSIONS = [ GET_DATA, POST_DATA, POST_PETITIONS, RESOLVE_PETITIONS, MANAGE_USERS, GENERAL_ADMIN ]
ADMIN_PERMISSIONS = [ RESOLVE_PETITIONS, MANAGE_USERS, GENERAL_ADMIN, EDIT_SERVICES ]

permissions_string_lookup = {}

permissions_string_lookup[ GET_DATA ] = 'get data'
permissions_string_lookup[ POST_DATA ] = 'post data'
permissions_string_lookup[ POST_PETITIONS ] = 'post petitions'
permissions_string_lookup[ RESOLVE_PETITIONS ] = 'resolve petitions'
permissions_string_lookup[ MANAGE_USERS ] = 'manage users'
permissions_string_lookup[ GENERAL_ADMIN ] = 'general administration'
permissions_string_lookup[ EDIT_SERVICES ] = 'edit services'

TAG_REPOSITORY = 0
FILE_REPOSITORY = 1
LOCAL_FILE = 2
MESSAGE_DEPOT = 3
LOCAL_TAG = 5
LOCAL_RATING_NUMERICAL = 6
LOCAL_RATING_LIKE = 7
RATING_NUMERICAL_REPOSITORY = 8
RATING_LIKE_REPOSITORY = 9
SERVER_ADMIN = 99
NULL_SERVICE = 100

service_string_lookup = {}

service_string_lookup[ TAG_REPOSITORY ] = 'hydrus tag repository'
service_string_lookup[ FILE_REPOSITORY ] = 'hydrus file repository'
service_string_lookup[ LOCAL_FILE ] = 'hydrus local file service'
service_string_lookup[ MESSAGE_DEPOT ] = 'hydrus message depot'
service_string_lookup[ SERVER_ADMIN ] = 'hydrus server administration'

RATINGS_SERVICES = [ LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY ]
REPOSITORIES = [ TAG_REPOSITORY, FILE_REPOSITORY, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY ]
RESTRICTED_SERVICES = list( REPOSITORIES ) + [ SERVER_ADMIN, MESSAGE_DEPOT ]
REMOTE_SERVICES = list( RESTRICTED_SERVICES )
ALL_SERVICES = list( REMOTE_SERVICES ) + [ LOCAL_FILE, LOCAL_TAG, LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL ]

SERVICES_WITH_THUMBNAILS = [ FILE_REPOSITORY, LOCAL_FILE ]

DELETE_FILES_PETITION = 0
DELETE_TAG_PETITION = 1

BAN = 0
SUPERBAN = 1
CHANGE_ACCOUNT_TYPE = 2
ADD_TO_EXPIRES = 3
SET_EXPIRES = 4

CURRENT = 0
PENDING = 1
DELETED = 2
PETITIONED = 3

HIGH_PRIORITY = 0
LOW_PRIORITY = 2

SCORE_PETITION = 0

SERVICE_INFO_NUM_FILES = 0
SERVICE_INFO_NUM_INBOX = 1
SERVICE_INFO_NUM_LOCAL = 2
SERVICE_INFO_NUM_MAPPINGS = 3
SERVICE_INFO_NUM_DELETED_MAPPINGS = 4
SERVICE_INFO_NUM_DELETED_FILES = 5
SERVICE_INFO_NUM_THUMBNAILS = 6
SERVICE_INFO_NUM_THUMBNAILS_LOCAL = 7
SERVICE_INFO_TOTAL_SIZE = 8
SERVICE_INFO_NUM_NAMESPACES = 9
SERVICE_INFO_NUM_TAGS = 10
SERVICE_INFO_NUM_PENDING = 11
SERVICE_INFO_NUM_CONVERSATIONS = 12
SERVICE_INFO_NUM_UNREAD = 13
SERVICE_INFO_NUM_DRAFTS = 14

SERVICE_UPDATE_ACCOUNT = 0
SERVICE_UPDATE_DELETE_PENDING = 1
SERVICE_UPDATE_ERROR = 2
SERVICE_UPDATE_NEXT_BEGIN = 3
SERVICE_UPDATE_RESET = 4
SERVICE_UPDATE_REQUEST_MADE = 5
SERVICE_UPDATE_LAST_CHECK = 6

ADD = 0
DELETE = 1
EDIT = 2

APPROVE = 0
DENY = 1

GET = 0
POST = 1
OPTIONS = 2

APPLICATION_HYDRUS_CLIENT_COLLECTION = 0
IMAGE_JPEG = 1
IMAGE_PNG = 2
IMAGE_GIF = 3
IMAGE_BMP = 4
APPLICATION_FLASH = 5
APPLICATION_YAML = 6
IMAGE_ICON = 7
TEXT_HTML = 8
VIDEO_FLV = 9
APPLICATION_PDF = 10
APPLICATION_OCTET_STREAM = 100
APPLICATION_UNKNOWN = 101

ALLOWED_MIMES = ( IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_BMP, APPLICATION_FLASH, VIDEO_FLV, APPLICATION_PDF )

IMAGES = ( IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_BMP )

APPLICATIONS = ( APPLICATION_FLASH, APPLICATION_PDF )

NOISY_MIMES = ( APPLICATION_FLASH, VIDEO_FLV )

MIMES_WITH_THUMBNAILS = ( IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_BMP )

mime_enum_lookup = {}

mime_enum_lookup[ 'collection' ] = APPLICATION_HYDRUS_CLIENT_COLLECTION
mime_enum_lookup[ 'image/jpe' ] = IMAGE_JPEG
mime_enum_lookup[ 'image/jpeg' ] = IMAGE_JPEG
mime_enum_lookup[ 'image/jpg' ] = IMAGE_JPEG
mime_enum_lookup[ 'image/png' ] = IMAGE_PNG
mime_enum_lookup[ 'image/gif' ] = IMAGE_GIF
mime_enum_lookup[ 'image/bmp' ] = IMAGE_BMP
mime_enum_lookup[ 'image' ] = IMAGES
mime_enum_lookup[ 'image/vnd.microsoft.icon' ] = IMAGE_ICON
mime_enum_lookup[ 'application/x-shockwave-flash' ] = APPLICATION_FLASH
mime_enum_lookup[ 'application/octet-stream' ] = APPLICATION_OCTET_STREAM
mime_enum_lookup[ 'application/x-yaml' ] = APPLICATION_YAML
mime_enum_lookup[ 'application/pdf' ] = APPLICATION_PDF
mime_enum_lookup[ 'application' ] = APPLICATIONS
mime_enum_lookup[ 'text/html' ] = TEXT_HTML
mime_enum_lookup[ 'video/x-flv' ] = VIDEO_FLV
mime_enum_lookup[ 'unknown mime' ] = APPLICATION_UNKNOWN

mime_string_lookup = {}

mime_string_lookup[ APPLICATION_HYDRUS_CLIENT_COLLECTION ] = 'collection'
mime_string_lookup[ IMAGE_JPEG ] = 'image/jpg'
mime_string_lookup[ IMAGE_PNG ] = 'image/png'
mime_string_lookup[ IMAGE_GIF ] = 'image/gif'
mime_string_lookup[ IMAGE_BMP ] = 'image/bmp'
mime_string_lookup[ IMAGES ] = 'image'
mime_string_lookup[ IMAGE_ICON ] = 'image/vnd.microsoft.icon'
mime_string_lookup[ APPLICATION_FLASH ] = 'application/x-shockwave-flash'
mime_string_lookup[ APPLICATION_OCTET_STREAM ] = 'application/octet-stream'
mime_string_lookup[ APPLICATION_YAML ] = 'application/x-yaml'
mime_string_lookup[ APPLICATION_PDF ] = 'application/pdf'
mime_string_lookup[ APPLICATIONS ] = 'application'
mime_string_lookup[ TEXT_HTML ] = 'text/html'
mime_string_lookup[ VIDEO_FLV ] = 'video/x-flv'
mime_string_lookup[ APPLICATION_UNKNOWN ] = 'unknown mime'

mime_ext_lookup = {}

mime_ext_lookup[ APPLICATION_HYDRUS_CLIENT_COLLECTION ] = '.collection'
mime_ext_lookup[ IMAGE_JPEG ] = '.jpg'
mime_ext_lookup[ IMAGE_PNG ] = '.png'
mime_ext_lookup[ IMAGE_GIF ] = '.gif'
mime_ext_lookup[ IMAGE_BMP ] = '.bmp'
mime_ext_lookup[ IMAGE_ICON ] = '.ico'
mime_ext_lookup[ APPLICATION_FLASH ] = '.swf'
mime_ext_lookup[ APPLICATION_OCTET_STREAM ] = '.bin'
mime_ext_lookup[ APPLICATION_YAML ] = '.yaml'
mime_ext_lookup[ APPLICATION_PDF ] = '.pdf'
mime_ext_lookup[ TEXT_HTML ] = '.html'
mime_ext_lookup[ VIDEO_FLV ] = '.flv'
mime_ext_lookup[ APPLICATION_UNKNOWN ] = ''
#mime_ext_lookup[ 'application/x-rar-compressed' ] = '.rar'

ALLOWED_MIME_EXTENSIONS = [ mime_ext_lookup[ mime ] for mime in ALLOWED_MIMES ]

header_and_mime = [
    ( '\xff\xd8', IMAGE_JPEG ),
    ( 'GIF87a', IMAGE_GIF ),
    ( 'GIF89a', IMAGE_GIF ),
    ( '\x89PNG', IMAGE_PNG ),
    ( 'BM', IMAGE_BMP ),
    ( 'CWS', APPLICATION_FLASH ),
    ( 'FWS', APPLICATION_FLASH ),
    ( 'FLV', VIDEO_FLV ),
    ( '%PDF', APPLICATION_PDF )
    ]

PREDICATE_TYPE_SYSTEM = 0
PREDICATE_TYPE_TAG = 1
PREDICATE_TYPE_NAMESPACE = 2

SITE_DOWNLOAD_TYPE_DEVIANT_ART = 0
SITE_DOWNLOAD_TYPE_GIPHY = 1
SITE_DOWNLOAD_TYPE_PIXIV = 2
SITE_DOWNLOAD_TYPE_BOORU = 3
SITE_DOWNLOAD_TYPE_TUMBLR = 4
SITE_DOWNLOAD_TYPE_HENTAI_FOUNDRY = 5

SYSTEM_PREDICATE_TYPE_EVERYTHING = 0
SYSTEM_PREDICATE_TYPE_INBOX = 1
SYSTEM_PREDICATE_TYPE_ARCHIVE = 2
SYSTEM_PREDICATE_TYPE_UNTAGGED = 3
SYSTEM_PREDICATE_TYPE_NUM_TAGS = 4
SYSTEM_PREDICATE_TYPE_LIMIT = 5
SYSTEM_PREDICATE_TYPE_SIZE = 6
SYSTEM_PREDICATE_TYPE_AGE = 7
SYSTEM_PREDICATE_TYPE_HASH = 8
SYSTEM_PREDICATE_TYPE_WIDTH = 9
SYSTEM_PREDICATE_TYPE_HEIGHT = 10
SYSTEM_PREDICATE_TYPE_RATIO = 11
SYSTEM_PREDICATE_TYPE_DURATION = 12
SYSTEM_PREDICATE_TYPE_MIME = 13
SYSTEM_PREDICATE_TYPE_RATING = 14
SYSTEM_PREDICATE_TYPE_SIMILAR_TO = 15
SYSTEM_PREDICATE_TYPE_LOCAL = 17
SYSTEM_PREDICATE_TYPE_NOT_LOCAL = 18
SYSTEM_PREDICATE_TYPE_NUM_WORDS = 19
SYSTEM_PREDICATE_TYPE_FILE_SERVICE = 20

wxk_code_string_lookup = {
    wx.WXK_SPACE: 'space',
    wx.WXK_BACK: 'backspace',
    wx.WXK_TAB: 'tab',
    wx.WXK_RETURN: 'return',
    wx.WXK_NUMPAD_ENTER: 'enter',
    wx.WXK_PAUSE: 'pause',
    wx.WXK_ESCAPE: 'escape',
    wx.WXK_INSERT: 'insert',
    wx.WXK_DELETE: 'delete',
    wx.WXK_UP: 'up',
    wx.WXK_DOWN: 'down',
    wx.WXK_LEFT: 'left',
    wx.WXK_RIGHT: 'right',
    wx.WXK_HOME: 'home',
    wx.WXK_END: 'end',
    wx.WXK_PAGEDOWN: 'page up',
    wx.WXK_PAGEUP: 'page down',
    wx.WXK_F1: 'f1',
    wx.WXK_F2: 'f2',
    wx.WXK_F3: 'f3',
    wx.WXK_F4: 'f4',
    wx.WXK_F5: 'f5',
    wx.WXK_F6: 'f6',
    wx.WXK_F7: 'f7',
    wx.WXK_F8: 'f8',
    wx.WXK_F9: 'f9',
    wx.WXK_F10: 'f10',
    wx.WXK_F11: 'f11',
    wx.WXK_F12: 'f12',
    wx.WXK_ADD: '+',
    wx.WXK_DIVIDE: '/',
    wx.WXK_SUBTRACT: '-',
    wx.WXK_MULTIPLY: '*',
    wx.WXK_NUMPAD1: 'numpad 1',
    wx.WXK_NUMPAD2: 'numpad 2',
    wx.WXK_NUMPAD3: 'numpad 3',
    wx.WXK_NUMPAD4: 'numpad 4',
    wx.WXK_NUMPAD5: 'numpad 5',
    wx.WXK_NUMPAD6: 'numpad 6',
    wx.WXK_NUMPAD7: 'numpad 7',
    wx.WXK_NUMPAD8: 'numpad 8',
    wx.WXK_NUMPAD9: 'numpad 9',
    wx.WXK_NUMPAD0: 'numpad 0',
    wx.WXK_NUMPAD_UP: 'numpad up',
    wx.WXK_NUMPAD_DOWN: 'numpad down',
    wx.WXK_NUMPAD_LEFT: 'numpad left',
    wx.WXK_NUMPAD_RIGHT: 'numpad right',
    wx.WXK_NUMPAD_HOME: 'numpad home',
    wx.WXK_NUMPAD_END: 'numpad end',
    wx.WXK_NUMPAD_PAGEDOWN: 'numpad page up',
    wx.WXK_NUMPAD_PAGEUP: 'numpad page down',
    wx.WXK_NUMPAD_ADD: 'numpad +',
    wx.WXK_NUMPAD_DIVIDE: 'numpad /',
    wx.WXK_NUMPAD_SUBTRACT: 'numpad -',
    wx.WXK_NUMPAD_MULTIPLY: 'numpad *',
    wx.WXK_NUMPAD_DELETE: 'numpad delete',
    wx.WXK_NUMPAD_DECIMAL: 'numpad decimal'
    }

# request checking

BANDWIDTH_CONSUMING_REQUESTS = set()

BANDWIDTH_CONSUMING_REQUESTS.add( ( TAG_REPOSITORY, GET, 'update' ) )
BANDWIDTH_CONSUMING_REQUESTS.add( ( TAG_REPOSITORY, POST, 'mappings' ) )
BANDWIDTH_CONSUMING_REQUESTS.add( ( TAG_REPOSITORY, POST, 'petitions' ) )
BANDWIDTH_CONSUMING_REQUESTS.add( ( FILE_REPOSITORY, GET, 'update' ) )
BANDWIDTH_CONSUMING_REQUESTS.add( ( FILE_REPOSITORY, GET, 'file' ) )
BANDWIDTH_CONSUMING_REQUESTS.add( ( FILE_REPOSITORY, GET, 'thumbnail' ) )
BANDWIDTH_CONSUMING_REQUESTS.add( ( FILE_REPOSITORY, POST, 'file' ) )
BANDWIDTH_CONSUMING_REQUESTS.add( ( FILE_REPOSITORY, POST, 'petitions' ) )

service_requests = []
service_requests.append( ( GET, '', None ) )
service_requests.append( ( GET, 'favicon.ico', None ) )

local_file_requests = list( service_requests )
local_file_requests.append( ( GET, 'file', None ) )
local_file_requests.append( ( GET, 'thumbnail', None ) )

restricted_requests = list( service_requests )
restricted_requests.append( ( GET, 'access_key', None ) )
restricted_requests.append( ( GET, 'account', None ) )
restricted_requests.append( ( GET, 'account_info', MANAGE_USERS ) )
restricted_requests.append( ( GET, 'account_types', MANAGE_USERS ) )
restricted_requests.append( ( GET, 'options', GENERAL_ADMIN ) )
restricted_requests.append( ( GET, 'registration_keys', GENERAL_ADMIN ) )
restricted_requests.append( ( GET, 'session_key', None ) )
restricted_requests.append( ( GET, 'stats', GENERAL_ADMIN ) )
restricted_requests.append( ( POST, 'account_modification', ( MANAGE_USERS, GENERAL_ADMIN ) ) )
restricted_requests.append( ( POST, 'account_types_modification', GENERAL_ADMIN ) )
restricted_requests.append( ( POST, 'options', GENERAL_ADMIN ) )

admin_requests = list( restricted_requests )
admin_requests.append( ( GET, 'init', None ) )
admin_requests.append( ( GET, 'services', EDIT_SERVICES ) )
admin_requests.append( ( POST, 'backup', EDIT_SERVICES ) )
admin_requests.append( ( POST, 'services_modification', EDIT_SERVICES ) )

repository_requests = list( restricted_requests )
repository_requests.append( ( GET, 'num_petitions', RESOLVE_PETITIONS ) )
repository_requests.append( ( GET, 'petition', RESOLVE_PETITIONS ) )
repository_requests.append( ( GET, 'update', GET_DATA ) )
repository_requests.append( ( POST, 'news', GENERAL_ADMIN ) )
repository_requests.append( ( POST, 'petition_denial', RESOLVE_PETITIONS ) )
repository_requests.append( ( POST, 'petitions', ( POST_PETITIONS, RESOLVE_PETITIONS ) ) )

file_repository_requests = list( repository_requests )
file_repository_requests.append( ( GET, 'file', GET_DATA ) )
file_repository_requests.append( ( GET, 'ip', GENERAL_ADMIN ) )
file_repository_requests.append( ( GET, 'thumbnail', GET_DATA ) )
file_repository_requests.append( ( POST, 'file', POST_DATA ) )

tag_repository_requests = list( repository_requests )
tag_repository_requests.append( ( POST, 'mappings', POST_DATA ) )

message_depot_requests = list( restricted_requests )
message_depot_requests.append( ( GET, 'message', GET_DATA ) )
message_depot_requests.append( ( GET, 'message_info_since', GET_DATA ) )
message_depot_requests.append( ( GET, 'public_key', None ) )
message_depot_requests.append( ( POST, 'contact', POST_DATA ) )
message_depot_requests.append( ( POST, 'message', None ) )
message_depot_requests.append( ( POST, 'message_statuses', None ) )

all_requests = []
all_requests.extend( [ ( LOCAL_FILE, request_type, request, permissions ) for ( request_type, request, permissions ) in local_file_requests ] )
all_requests.extend( [ ( SERVER_ADMIN, request_type, request, permissions ) for ( request_type, request, permissions ) in admin_requests ] )
all_requests.extend( [ ( FILE_REPOSITORY, request_type, request, permissions ) for ( request_type, request, permissions ) in file_repository_requests ] )
all_requests.extend( [ ( TAG_REPOSITORY, request_type, request, permissions ) for ( request_type, request, permissions ) in tag_repository_requests ] )
all_requests.extend( [ ( MESSAGE_DEPOT, request_type, request, permissions ) for ( request_type, request, permissions ) in message_depot_requests ] )

ALLOWED_REQUESTS = { ( service_type, request_type, request ) for ( service_type, request_type, request, permissions ) in all_requests }

REQUESTS_TO_PERMISSIONS = { ( service_type, request_type, request ) : permissions for ( service_type, request_type, request, permissions ) in all_requests }

# default options

DEFAULT_LOCAL_FILE_PORT = 45865
DEFAULT_SERVER_ADMIN_PORT = 45870
DEFAULT_SERVICE_PORT = 45871

DEFAULT_OPTIONS = {}

DEFAULT_OPTIONS[ SERVER_ADMIN ] = {}
DEFAULT_OPTIONS[ SERVER_ADMIN ][ 'max_monthly_data' ] = None
DEFAULT_OPTIONS[ SERVER_ADMIN ][ 'max_storage' ] = None
DEFAULT_OPTIONS[ SERVER_ADMIN ][ 'message' ] = 'hydrus server administration service'

DEFAULT_OPTIONS[ FILE_REPOSITORY ] = {}
DEFAULT_OPTIONS[ FILE_REPOSITORY ][ 'max_monthly_data' ] = None
DEFAULT_OPTIONS[ FILE_REPOSITORY ][ 'max_storage' ] = None
DEFAULT_OPTIONS[ FILE_REPOSITORY ][ 'log_uploader_ips' ] = False
DEFAULT_OPTIONS[ FILE_REPOSITORY ][ 'message' ] = 'hydrus file repository'

DEFAULT_OPTIONS[ TAG_REPOSITORY ] = {}
DEFAULT_OPTIONS[ TAG_REPOSITORY ][ 'max_monthly_data' ] = None
DEFAULT_OPTIONS[ TAG_REPOSITORY ][ 'message' ] = 'hydrus tag repository'

DEFAULT_OPTIONS[ MESSAGE_DEPOT ] = {}
DEFAULT_OPTIONS[ MESSAGE_DEPOT ][ 'max_monthly_data' ] = None
DEFAULT_OPTIONS[ MESSAGE_DEPOT ][ 'max_storage' ] = None
DEFAULT_OPTIONS[ MESSAGE_DEPOT ][ 'message' ] = 'hydrus message depot'

# Hydrus pubsub

EVT_PUBSUB = HydrusPubSub.EVT_PUBSUB
pubsub = HydrusPubSub.HydrusPubSub()

def BuildKeyToListDict( pairs ):
    
    d = collections.defaultdict( list )
    
    for ( key, value ) in pairs: d[ key ].append( value )
    
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
    
def CleanTag( tag ):
    
    if tag == '': return ''
    
    tag = tag.lower()
    
    tag = unicode( tag )
    
    tag = re.sub( '[\s]+', ' ', tag, flags = re.UNICODE ) # turns multiple spaces into single spaces
    
    tag = re.sub( '\s\Z', '', tag, flags = re.UNICODE ) # removes space at the end
    
    while re.match( '\s|-|system:', tag, flags = re.UNICODE ) is not None:
        
        tag = re.sub( '\A(\s|-|system:)', '', tag, flags = re.UNICODE ) # removes space at the beginning
        
    
    return tag
    
def ConvertAbsPathToPortablePath( abs_path ):
    
    if abs_path == '': return None
    
    try: return os.path.relpath( abs_path, BASE_DIR )
    except: return abs_path
    
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
    
def ConvertIntToPrettyString( num ): return locale.format( "%d", num, grouping = True )

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
    
    if rounded_result: s = str( '%.2f' % round( rating_converted ) )
    else: s = str( '%.2f' % rating_converted )
    
    if out_of:
        
        if lower in ( 0, 1 ): s += '/' + str( '%.2f' % upper )
        
    
    return s
    
def ConvertPortablePathToAbsPath( portable_path ):
    
    if portable_path is None: return None
    
    if os.path.isabs( portable_path ): abs_path = portable_path
    else: abs_path = os.path.normpath( BASE_DIR + os.path.sep + portable_path )
    
    if os.path.exists( abs_path ): return abs_path
    else: return None
    
def ConvertShortcutToPrettyShortcut( modifier, key, action ):
    
    if modifier == wx.ACCEL_NORMAL: modifier = ''
    elif modifier == wx.ACCEL_ALT: modifier = 'alt'
    elif modifier == wx.ACCEL_CTRL: modifier = 'ctrl'
    elif modifier == wx.ACCEL_SHIFT: modifier = 'shift'
    
    if key in range( 65, 91 ): key = chr( key + 32 ) # + 32 for converting ascii A -> a
    elif key in range( 97, 123 ): key = chr( key )
    else: key = wxk_code_string_lookup[ key ]
    
    return ( modifier, key, action )
    
def ConvertTimestampToPrettyAge( timestamp ):
    
    if timestamp == 0 or timestamp is None: return 'unknown age'
    
    age = int( time.time() ) - timestamp
    
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
    
    if timestamp == 0: return 'unknown when'
    
    age = int( time.time() ) - timestamp
    
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
    if timestamp == 0: return 'unknown expiry'
    
    expires = int( time.time() ) - timestamp
    
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
    
    pending = int( time.time() ) - timestamp
    
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
    
    if timestamp == 0: return 'not updated'
    
    age = int( time.time() ) - timestamp
    
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
    
    if years > 0: return 'updated to ' + ' '.join( ( y, mo ) ) + ' ago'
    elif months > 0: return 'updated to ' + ' '.join( ( mo, d ) ) + ' ago'
    elif days > 0: return 'updated to ' + ' '.join( ( d, h ) ) + ' ago'
    elif hours > 0: return 'updated to ' + ' '.join( ( h, m ) ) + ' ago'
    else: return 'updated to ' + ' '.join( ( m, s ) ) + ' ago'
    
def ConvertTimestampToPrettyTime( timestamp ): return time.strftime( '%Y/%m/%d %H:%M:%S', time.localtime( timestamp ) )

def ConvertTimestampToHumanPrettyTime( timestamp ):
    
    now = int( time.time() )
    
    difference = now - timestamp
    
    if difference < 60: return 'just now'
    elif difference < 86400 * 7: return ConvertTimestampToPrettyAgo( timestamp )
    else: return ConvertTimestampToPrettyTime( timestamp )
    
def ConvertTimeToPrettyTime( secs ):
    
    return time.strftime( '%H:%M:%S', time.gmtime( secs ) )
    
def ConvertUnitToInteger( unit ):
    
    if unit == 'B': return 8
    elif unit == 'KB': return 1024
    elif unit == 'MB': return 1048576
    elif unit == 'GB': return 1073741824
    
def ConvertUnitToString( unit ):
    
    if unit == 8: return 'B'
    elif unit == 1024: return 'KB'
    elif unit == 1048576: return 'MB'
    elif unit == 1073741824: return 'GB'
    
def ConvertZoomToPercentage( zoom ):
    
    zoom = zoom * 100.0
    
    pretty_zoom = '%.0f' % zoom + '%'
    
    return pretty_zoom
    
def GetMimeFromPath( filename ):
    
    f = open( filename, 'rb' )
    
    return GetMimeFromFilePointer( f )
    
def GetMimeFromFilePointer( f ):
    
    try:
        
        f.seek( 0 )
        
        header = f.read( 256 )
        
        return GetMimeFromString( header )
        
    except: raise Exception( 'I could not identify the mime of the file' )
    
def GetMimeFromString( file ):
    
    for ( header, mime ) in header_and_mime:
        
        if file.startswith( header ):
            
            return mime
            
        
    
    return APPLICATION_OCTET_STREAM
    
def GetShortcutFromEvent( event ):
    
    modifier = wx.ACCEL_NORMAL
    
    if event.AltDown(): modifier = wx.ACCEL_ALT
    elif event.ControlDown(): modifier = wx.ACCEL_CTRL
    elif event.ShiftDown(): modifier = wx.ACCEL_SHIFT
    
    key = event.KeyCode
    
    return ( modifier, key )
    
def IntelligentMassUnion( iterables_to_reduce ):
    
    # while I might usually go |= here (for style), it is quicker to use the ugly .update when we want to be quick
    # set.update also converts the second argument to a set, if appropriate!
    
    #return reduce( set.union, iterables_to_reduce, set() )
    
    # also: reduce is slower, I think, cause of union rather than update!
    
    answer = set()
    
    for i in iterables_to_reduce: answer.update( i )
    
    return answer
    
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
    
def IsCollection( mime ): return mime in ( APPLICATION_HYDRUS_CLIENT_COLLECTION, ) # this is a little convoluted, but I want to keep it similar to IsImage, IsText, IsAudio, IsX

def IsImage( mime ): return mime in ( IMAGE_JPEG, IMAGE_GIF, IMAGE_PNG, IMAGE_BMP )

def SearchEntryMatchesPredicate( search_entry, predicate ):
    
    ( predicate_type, info ) = predicate.GetInfo()
    
    if predicate_type == PREDICATE_TYPE_TAG:
        
        ( operator, value ) = info
        
        return SearchEntryMatchesTag( search_entry, value )
        
    else: return False
    
def SearchEntryMatchesTag( search_entry, tag ):
    
    # note that at no point is the namespace checked against the search_entry!
    
    if ':' in tag:
        
        ( n, t ) = tag.split( ':', 1 )
        
        return t.startswith( search_entry )
        
    else: return tag.startswith( search_entry )
    
def SplayListForDB( xs ): return '(' + ','.join( [ '"' + str( x ) + '"' for x in xs ] ) + ')'

def SplayTupleListForDB( first_column_name, second_column_name, xys ): return ' OR '.join( [ '( ' + first_column_name + '=' + str( x ) + ' AND ' + second_column_name + ' IN ' + SplayListForDB( ys ) + ' )' for ( x, ys ) in xys ] )

def ThumbnailResolution( original_resolution, target_resolution ):
    
    ( original_width, original_height ) = original_resolution
    ( target_width, target_height ) = target_resolution
    
    if original_width > target_width:
        
        original_height = max( original_height * target_width / float( original_width ), 1 )
        original_width = target_width
        
    
    if round( original_height ) > target_height:
        
        original_width = max( original_width * target_height / float( original_height ), 1 )
        original_height = target_height
        
    
    return ( int( round( original_width ) ), int( round( original_height ) ) )

class AdvancedHTTPConnection():
    
    def __init__( self, url = '', scheme = 'http', host = '', port = None, service_identifier = None, accept_cookies = False ):
        
        if len( url ) > 0:
            
            parse_result = urlparse.urlparse( url )
            
            ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
            
        
        self._scheme = scheme
        self._host = host
        self._port = port
        self._service_identifier = service_identifier
        self._accept_cookies = accept_cookies
        
        self._cookies = {}
        
        if service_identifier is None: timeout = 30
        else: timeout = 300
        
        if self._scheme == 'http': self._connection = httplib.HTTPConnection( self._host, self._port, timeout = timeout )
        else: self._connection = httplib.HTTPSConnection( self._host, self._port, timeout = timeout )
        
    
    def close( self ): self._connection.close()
    
    def connect( self ): self._connection.connect()
    
    def GetCookies( self ): return self._cookies
    
    def geturl( self, url, headers = {}, is_redirect = False, follow_redirects = True ):
        
        parse_result = urlparse.urlparse( url )
        
        request = parse_result.path
        
        query = parse_result.query
        
        if query != '': request += '?' + query
        
        return self.request( 'GET', request, headers = headers, is_redirect = is_redirect, follow_redirects = follow_redirects )
        
    
    def request( self, request_type, request, headers = {}, body = None, is_redirect = False, follow_redirects = True ):
        
        if 'User-Agent' not in headers: headers[ 'User-Agent' ] = 'hydrus/' + str( NETWORK_VERSION )
        
        if len( self._cookies ) > 0: headers[ 'Cookie' ] = '; '.join( [ k + '=' + v for ( k, v ) in self._cookies.items() ] )
        
        try:
            
            self._connection.request( request_type, request, headers = headers, body = body )
            
            response = self._connection.getresponse()
            
            raw_response = response.read()
            
        except ( httplib.CannotSendRequest, httplib.BadStatusLine ):
            
            # for some reason, we can't send a request on the current connection, so let's make a new one!
            
            try:
                
                if self._scheme == 'http': self._connection = httplib.HTTPConnection( self._host, self._port )
                else: self._connection = httplib.HTTPSConnection( self._host, self._port )
                
                self._connection.request( request_type, request, headers = headers, body = body )
                
                response = self._connection.getresponse()
                
                raw_response = response.read()
                
            except:
                print( traceback.format_exc() )
                raise
            
        except:
            print( traceback.format_exc() )
            raise Exception( 'Could not connect to server' )
        
        if self._accept_cookies:
            
            for cookie in response.msg.getallmatchingheaders( 'Set-Cookie' ): # msg is a mimetools.Message
                
                try:
                    
                    cookie = cookie.replace( 'Set-Cookie: ', '' )
                    
                    if ';' in cookie: ( cookie, expiry_gumpf ) = cookie.split( ';', 1 )
                    
                    ( k, v ) = cookie.split( '=' )
                    
                    self._cookies[ k ] = v
                    
                except: pass
                
            
        
        if len( raw_response ) > 0:
            
            content_type = response.getheader( 'Content-Type' )
            
            if content_type is not None:
                
                # additional info can be a filename or charset=utf-8 or whatever
                
                if content_type == 'text/html':
                    
                    mime_string = content_type
                    
                    try: raw_response = raw_response.decode( 'utf-8' )
                    except: pass
                    
                elif '; ' in content_type:
                    
                    ( mime_string, additional_info ) = content_type.split( '; ' )
                    
                    if 'charset=' in additional_info:
                        
                        # this does utf-8, ISO-8859-4, whatever
                        
                        ( gumpf, charset ) = additional_info.split( '=' )
                        
                        try: raw_response = raw_response.decode( charset )
                        except: pass
                        
                    
                else: mime_string = content_type
                
                if mime_string in mime_enum_lookup and mime_enum_lookup[ mime_string ] == APPLICATION_YAML:
                    
                    try: parsed_response = yaml.safe_load( raw_response )
                    except Exception as e: raise NetworkVersionException( 'Failed to parse a response object!' + os.linesep + unicode( e ) )
                    
                else: parsed_response = raw_response
                
            else: parsed_response = raw_response
            
        else: parsed_response = raw_response
        
        if self._service_identifier is not None:
            
            service_type = self._service_identifier.GetType()
            
            server_header = response.getheader( 'Server' )
            
            service_string = service_string_lookup[ service_type ]
            
            if server_header is None or service_string not in server_header:
                
                pubsub.pub( 'service_update_db', ServiceUpdate( SERVICE_UPDATE_ACCOUNT, self._service_identifier, GetUnknownAccount() ) )
                
                raise WrongServiceTypeException( 'Target was not a ' + service_string + '!' )
                
            
            if '?' in request: request_command = request.split( '?' )[0]
            else: request_command = request
            
            if '/' in request_command: request_command = request_command.split( '/' )[1]
            
            if request_type == 'GET':
                
                if ( service_type, GET, request_command ) in BANDWIDTH_CONSUMING_REQUESTS: pubsub.pub( 'service_update_db', ServiceUpdate( SERVICE_UPDATE_REQUEST_MADE, self._service_identifier, len( raw_response ) ) )
                
            elif ( service_type, POST, request_command ) in BANDWIDTH_CONSUMING_REQUESTS: pubsub.pub( 'service_update_db', ServiceUpdate( SERVICE_UPDATE_REQUEST_MADE, self._service_identifier, len( body ) ) )
            
        
        if response.status == 200: return parsed_response
        elif response.status == 205: return
        elif response.status in ( 301, 302, 303, 307 ):
            
            location = response.getheader( 'Location' )
            
            if location is None: raise Exception( data )
            else:
                
                if not follow_redirects: return ''
                
                if is_redirect: raise Exception( 'Too many redirects!' )
                
                url = location
                
                parse_result = urlparse.urlparse( url )
                
                redirected_request = parse_result.path
                
                redirected_query = parse_result.query
                
                if redirected_query != '': redirected_request += '?' + redirected_query
                
                ( scheme, host, port ) = ( parse_result.scheme, parse_result.hostname, parse_result.port )
                
                if ( scheme is None or scheme == self._scheme ) and ( request == redirected_request or request in redirected_request or redirected_request in request ): raise Exception( 'Redirection problem' )
                else:
                    
                    if host is None or ( host == self._host and port == self._port ): connection = self
                    else: connection = AdvancedHTTPConnection( url )
                    
                    if response.status in ( 301, 307 ):
                        
                        # 301: moved permanently, repeat request
                        # 307: moved temporarily, repeat request
                        
                        return connection.request( request_type, redirected_request, headers = headers, body = body, is_redirect = True )
                        
                    elif response.status in ( 302, 303 ):
                        
                        # 302: moved temporarily, repeat request (except everyone treats it like 303 for no good fucking reason)
                        # 303: thanks, now go here with GET
                        
                        return connection.request( 'GET', redirected_request, is_redirect = True )
                        
                    
                
            
        elif response.status == 304: raise NotModifiedException()
        else:
            
            if self._service_identifier is not None:
                
                pubsub.pub( 'service_update_db', ServiceUpdate( SERVICE_UPDATE_ERROR, self._service_identifier, parsed_response ) )
                
                if response.status in ( 401, 426 ): pubsub.pub( 'service_update_db', ServiceUpdate( SERVICE_UPDATE_ACCOUNT, self._service_identifier, GetUnknownAccount() ) )
                
            
            if response.status == 401: raise PermissionsException( parsed_response )
            elif response.status == 403: raise ForbiddenException( parsed_response )
            elif response.status == 404: raise NotFoundException( parsed_response )
            elif response.status == 426: raise NetworkVersionException( parsed_response )
            elif response.status in ( 500, 501, 502, 503 ):
                
                try: print( parsed_response )
                except: pass
                
                raise Exception( parsed_response )
                
            else: raise Exception( parsed_response )
           
        
    
    def SetCookie( self, key, value ): self._cookies[ key ] = value
    
class HydrusYAMLBase( yaml.YAMLObject ):
    
    yaml_loader = yaml.SafeLoader
    yaml_dumper = yaml.SafeDumper
    
class Account( HydrusYAMLBase ):
    
    yaml_tag = u'!Account'
    
    def __init__( self, account_id, account_type, created, expires, used_data, banned_info = None ):
        
        HydrusYAMLBase.__init__( self )
        
        self._account_id = account_id
        self._account_type = account_type
        self._created = created
        self._expires = expires
        self._used_data = used_data
        self._banned_info = banned_info
        
        self._object_instantiation_timestamp = int( time.time() )
        
    
    def __repr__( self ): return self.ConvertToString()
    
    def __str__( self ): return self.ConvertToString()
    
    def _IsBanned( self ):
        
        if self._banned_info is None: return False
        else:
            
            ( reason, created, expires ) = self._banned_info
            
            if expires is None: return True
            else: return int( time.time() ) > expires
            
        
    
    def _IsExpired( self ):
        
        if self._expires is None: return False
        else: return int( time.time() ) > self._expires
        
    
    def CheckPermissions( self, permissions ):
        
        if type( permissions ) == int: permissions = ( permissions, )
        
        if self._IsBanned(): raise PermissionException( 'This account is banned!' )
        
        if self._IsExpired(): raise PermissionException( 'This account is expired.' )
        
        ( max_num_bytes, max_num_requests ) = self._account_type.GetMaxMonthlyData()
        
        ( used_bytes, used_requests ) = self._used_data
        
        if max_num_bytes is not None and used_bytes > max_num_bytes: raise PermissionException( 'You have hit your data transfer limit (' + ConvertIntToBytes( max_num_bytes ) + '), and cannot download any more for the month.' )
        
        if max_num_requests is not None and used_requests > max_num_requests: raise PermissionException( 'You have hit your requests limit (' + ConvertIntToPrettyString( max_num_requests ) + '), and cannot download any more for the month.' )
        
        if len( permissions ) > 0 and True not in [ self._account_type.HasPermission( permission ) for permission in permissions ]: raise PermissionException( 'You do not have permission to do that.' )
        
    
    def ConvertToString( self ): return ConvertTimestampToPrettyAge( self._created ) + os.linesep + self._account_type.ConvertToString( self._used_data ) + os.linesep + 'which '+ ConvertTimestampToPrettyExpires( self._expires )
    
    def GetAccountIdentifier( self ): return AccountIdentifier( account_id = account_id )
    
    def GetAccountType( self ): return self._account_type
    
    def GetBannedInfo( self ): return self._banned_info
    
    def GetCreated( self ): return self._created
    
    def GetExpires( self ): return self._expires
    
    def GetExpiresString( self ):
        
        if self._IsBanned():
            
            ( reason, created, expires ) = self._banned_info
            
            return 'banned ' + ConvertTimestampToPrettyAge( created ) + ', ' + ConvertTimestampToPrettyExpires( expires ) + ' because: ' + reason
            
        else: return ConvertTimestampToPrettyAge( self._created ) + ' and ' + ConvertTimestampToPrettyExpires( self._expires )
        
    
    def GetAccountId( self ): return self._account_id
    
    def GetUsedBytesString( self ):
        
        ( max_num_bytes, max_num_requests ) = self._account_type.GetMaxMonthlyData()
        ( used_bytes, used_requests ) = self._used_data
        
        if max_num_bytes is None: return ConvertIntToBytes( used_bytes ) + ' used this month'
        else: return ConvertIntToBytes( used_bytes ) + '/' + ConvertIntToBytes( max_num_bytes ) + ' used this month'
        
    
    def GetUsedRequestsString( self ):
        
        ( max_num_bytes, max_num_requests ) = self._account_type.GetMaxMonthlyData()
        ( used_bytes, used_requests ) = self._used_data
        
        if max_num_requests is None: return ConvertIntToPrettyString( used_requests ) + ' requests used this month'
        else: return ConvertIntToPrettyString( used_requests ) + '/' + ConvertIntToPrettyString( max_num_requests ) + ' requests used this month'
        
    
    def GetUsedData( self ): return self._used_data
    
    def HasPermission( self, permission ):
        
        if self._IsExpired(): return False
        
        ( max_num_bytes, max_num_requests ) = self._account_type.GetMaxMonthlyData()
        
        ( used_bytes, used_requests ) = self._used_data
        
        if max_num_bytes is not None and used_bytes >= max_num_bytes: return False
        if max_num_requests is not None and used_requests >= max_num_requests: return False
        
        return self._account_type.HasPermission( permission )
        
    
    def IsAdmin( self ): return True in [ self.HasPermissions( permission ) for permission in ADMIN_PERMISSIONS ]
    
    def IsBanned( self ): return self._IsBanned()
    
    def IsStale( self ): return self._object_instantiation_timestamp + UPDATE_DURATION * 5 < int( time.time() )
    
    def MakeFresh( self ): self._object_instantiation_timestamp = int( time.time() )
    
    def MakeStale( self ): self._object_instantiation_timestamp = 0
    
    def RequestMade( self, num_bytes ):
        
        ( used_bytes, used_requests ) = self._used_data
        
        used_bytes += num_bytes
        used_requests += 1
        
        self._used_data = ( used_bytes, used_requests )
        
    
class AccountIdentifier( HydrusYAMLBase ):
    
    yaml_tag = u'!AccountIdentifier'
    
    def __init__( self, access_key = None, hash = None, tag = None, account_id = None ):
        
        HydrusYAMLBase.__init__( self )
        
        self._access_key = access_key
        self._hash = hash
        self._tag = tag
        self._account_id = account_id
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._hash, self._tag, self._account_id ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def GetAccessKey( self ): return self._access_key
    
    def GetAccountId( self ): return self._account_id
    
    def GetHash( self ): return self._hash
    
    def GetMapping( self ): return ( self._tag, self._hash )
    
    def HasAccessKey( self ): return self._access_key is not None
    
    def HasHash( self ): return self._hash is not None and self._tag is None
    
    def HasAccountId( self ): return self._account_id is not None
    
    def HasMapping( self ): return self._tag is not None and self._hash is not None
    
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
    
    def GetMaxMonthlyData( self ): return self._max_monthly_data
    
    def GetMaxMonthlyDataString( self ):
        
        ( max_num_bytes, max_num_requests ) = self._max_monthly_data
        
        if max_num_bytes is None: max_num_bytes_string = 'No limit'
        else: max_num_bytes_string = ConvertIntToBytes( max_num_bytes )
        
        if max_num_requests is None: max_num_requests_string = 'No limit'
        else: max_num_requests_string = ConvertIntToPrettyString( max_num_requests )
        
        return ( max_num_bytes_string, max_num_requests_string )
        
    
    def ConvertToString( self, data_usage = None ):
        
        result_string = self._title + ' with '
        
        if len( self._permissions ) == 0: result_string += 'no permissions'
        else: result_string += ', '.join( [ permissions_string_lookup[ permission ] for permission in self._permissions ] ) + ' permissions'
        
        return result_string
        
    
    def HasPermission( self, permission ): return permission in self._permissions
    
class ClientFilePetitionDenial( HydrusYAMLBase ):
    
    yaml_tag = u'!ClientFilePetitionDenial'
    
    def __init__( self, hashes ):
        
        HydrusYAMLBase.__init__( self )
        
        self._hashes = hashes
        
    
    def GetInfo( self ): return self._hashes
    
class ClientFilePetitions( HydrusYAMLBase ):
    
    yaml_tag = u'!ClientFilePetitions'
    
    def __init__( self, petitions ):
        
        HydrusYAMLBase.__init__( self )
        
        self._petitions = petitions
        
    
    def __iter__( self ): return ( petition for petition in self._petitions )
    
    def __len__( self ): return len( self._petitions )
    
    def GetHashes( self ): return IntelligentMassUnion( [ hashes for ( reason, hashes ) in self._petitions ] )
    
class ClientMappingPetitionDenial( HydrusYAMLBase ):
    
    yaml_tag = u'!ClientMappingPetitionDenial'
    
    def __init__( self, tag, hashes ):
        
        HydrusYAMLBase.__init__( self )
        
        self._tag = tag
        self._hashes = hashes
        
    
    def GetInfo( self ): return ( self._tag, self._hashes )
    
class ClientMappingPetitions( HydrusYAMLBase ):
    
    yaml_tag = u'!ClientMappingPetitions'
    
    def __init__( self, petitions, hash_ids_to_hashes ):
        
        HydrusYAMLBase.__init__( self )
        
        self._petitions = petitions
        
        self._hash_ids_to_hashes = hash_ids_to_hashes
        
    
    def __iter__( self ): return ( ( reason, tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( reason, tag, hash_ids ) in self._petitions )
    
    def __len__( self ): return len( self._petitions )
    
    def GetHashes( self ): return self._hash_ids_to_hashes.values()
    
    def GetTags( self ): return [ tag for ( reason, tag, hash_ids ) in self._petitions ]
    
class ClientMappings( HydrusYAMLBase ):
    
    yaml_tag = u'!ClientMappings'
    
    def __init__( self, mappings, hash_ids_to_hashes ):
        
        HydrusYAMLBase.__init__( self )
        
        self._mappings = mappings
        
        self._hash_ids_to_hashes = hash_ids_to_hashes
        
    
    def __iter__( self ): return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( tag, hash_ids ) in self._mappings )
    
    def __len__( self ): return len( self._mappings )
    
    def GetHashes( self ): return self._hash_ids_to_hashes.values()
    
    def GetTags( self ): return [ tag for ( tag, hash_ids ) in self._mappings ]
    
class ClientServiceIdentifier( HydrusYAMLBase ):
    
    yaml_tag = u'!ClientServiceIdentifier'
    
    def __init__( self, service_key, type, name ):
        
        HydrusYAMLBase.__init__( self )
        
        self._service_key = service_key
        self._type = type
        self._name = name
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return self._service_key.__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def GetName( self ): return self._name
    
    def GetServiceKey( self ): return self._service_key
    
    def GetType( self ): return self._type
    
LOCAL_FILE_SERVICE_IDENTIFIER = ClientServiceIdentifier( 'local files', LOCAL_FILE, 'local files' )
LOCAL_TAG_SERVICE_IDENTIFIER = ClientServiceIdentifier( 'local tags', LOCAL_TAG, 'local tags' )
NULL_SERVICE_IDENTIFIER = ClientServiceIdentifier( '', NULL_SERVICE, 'no service' )

class ContentUpdate():
    
    def __init__( self, action, service_identifier, hashes, info = None ):
        
        self._action = action
        self._service_identifier = service_identifier
        self._hashes = set( hashes )
        self._info = info
        
    
    def GetAction( self ): return self._action
    
    def GetHashes( self ): return self._hashes
    
    def GetInfo( self ): return self._info
    
    def GetServiceIdentifier( self ): return self._service_identifier
    
class DAEMON( threading.Thread ):
    
    def __init__( self, name, callable, period = 1200 ):
        
        threading.Thread.__init__( self, name = name )
        
        self._callable = callable
        self._period = period
        
        self._event = threading.Event()
        
        pubsub.sub( self, 'shutdown', 'shutdown' )
        
    
    def shutdown( self ): self._event.set()
    
class DAEMONQueue( DAEMON ):
    
    def __init__( self, name, callable, queue_topic, period = 10 ):
        
        DAEMON.__init__( self, name, callable, period )
        
        self._queue = Queue.Queue()
        self._queue_topic = queue_topic
        
        self.start()
        
        pubsub.sub( self, 'put', queue_topic )
        
    
    def put( self, data ): self._queue.put( data )
    
    def run( self ):
        
        time.sleep( 3 )
        
        while True:
            
            while self._queue.qsize() == 0:
                
                if shutdown: return
                
                self._event.wait( self._period )
                
                self._event.clear()
                
            
            items = []
            
            while self._queue.qsize() > 0: items.append( self._queue.get() )
            
            try: self._callable( items )
            except: print( traceback.format_exc() )
            
        
    
class DAEMONWorker( DAEMON ):
    
    def __init__( self, name, callable, topics = [], period = 1200, init_wait = 3 ):
        
        DAEMON.__init__( self, name, callable, period )
        
        self._topics = topics
        self._init_wait = init_wait
        
        self.start()
        
        for topic in topics: pubsub.sub( self, 'set', topic )
        
    
    def run( self ):
        
        self._event.wait( self._init_wait )
        
        while True:
            
            if shutdown: return
            
            try: self._callable()
            except: print( traceback.format_exc() )
            
            if shutdown: return
            
            self._event.wait( self._period )
            
            self._event.clear()
            
        
    
    def set( self, *args, **kwargs ): self._event.set()
    
class HydrusUpdate( HydrusYAMLBase ):

    yaml_tag = u'!HydrusUpdate'
    
    def __init__( self, news, begin, end ):
        
        HydrusYAMLBase.__init__( self )
        
        self._news = news
        
        self._begin = begin
        self._end = end
        
    
    def GetBegin( self ): return self._begin
    
    def GetEnd( self ): return self._end
    
    def GetNextBegin( self ): return self._end + 1
    
    def GetNews( self ): return [ ( news, timestamp ) for ( news, timestamp ) in self._news ]
    
    def SplitIntoSubUpdates( self ): return [ self ]
    
class HydrusUpdateFileRepository( HydrusUpdate ):
    
    yaml_tag = u'!HydrusUpdateFileRepository'
    
    def __init__( self, files, deleted_hashes, news, begin, end ):
        
        HydrusUpdate.__init__( self, news, begin, end )
        
        self._files = files
        self._deleted_hashes = deleted_hashes
        
    
    def GetDeletedHashes( self ): return self._deleted_hashes
    
    def GetFiles( self ): return self._files
    
    def GetHashes( self ): return [ hash for ( hash, size, mime, timestamp, width, height, duration, num_frames, num_words ) in self._files ]
    
class HydrusUpdateTagRepository( HydrusUpdate ):
    
    yaml_tag = u'!HydrusUpdateTagRepository'
    
    def __init__( self, mappings, deleted_mappings, hash_ids_to_hashes, news, begin, end ):
        
        HydrusUpdate.__init__( self, news, begin, end )
        
        self._hash_ids_to_hashes = hash_ids_to_hashes
        
        self._mappings = mappings
        self._deleted_mappings = deleted_mappings
        
    
    def GetDeletedMappings( self ): return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( tag, hash_ids ) in self._deleted_mappings )
    
    def GetMappings( self ): return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( tag, hash_ids ) in self._mappings )
    
    def GetTags( self ): return [ tag for ( tag, hash_ids ) in self._mappings ]
    
    def SplitIntoSubUpdates( self ):
        
        updates = [ HydrusUpdateTagRepository( [], [], {}, self._news, self._begin, None ) ]
        
        total_mappings = sum( [ len( hashes ) for ( tag, hashes ) in self._mappings ] )
        
        total_tags = len( self._mappings )
        
        number_updates_to_make = total_mappings / 500
        
        if number_updates_to_make == 0: number_updates_to_make = 1
        
        int_to_split_by = total_tags / number_updates_to_make
        
        if int_to_split_by == 0: int_to_split_by = 1
        
        for i in range( 0, len( self._mappings ), int_to_split_by ):
            
            mappings_subset = self._mappings[ i : i + int_to_split_by ]
            
            updates.append( HydrusUpdateTagRepository( mappings_subset, [], self._hash_ids_to_hashes, [], self._begin, None ) )
            
        
        for i in range( 0, len( self._deleted_mappings ), int_to_split_by ):
            
            deleted_mappings_subset = self._deleted_mappings[ i : i + int_to_split_by ]
            
            updates.append( HydrusUpdateTagRepository( [], deleted_mappings_subset, self._hash_ids_to_hashes, [], self._begin, None ) )
            
        
        updates.append( HydrusUpdateTagRepository( [], [], {}, [], self._begin, self._end ) )
        
        return updates
        
    
class JobInternal():
    
    yaml_tag = u'!JobInternal'
    
    def __init__( self, action, type, *args, **kwargs ):
        
        self._action = action
        self._type = type
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
            elif shutdown: raise Exception( 'Application quit before db could serve result!' )
            
        
        if issubclass( type( self._result ), Exception ): raise self._result
        else: return self._result
        
    
    def GetType( self ): return self._type
    
    def PutResult( self, result ):
        
        self._result = result
        
        self._result_ready.set()
        
    
class JobServer():
    
    yaml_tag = u'!JobServer'
    
    def __init__( self, *args ):
        
        self._args = args
        
        self._result = None
        self._result_ready = threading.Event()
        
    
    def GetArgs( self ): return self._args
    
    def GetResult( self ):
        
        while True:
            
            if self._result_ready.wait( 5 ) == True: break
            elif shutdown: raise Exception( 'Application quit before db could serve result!' )
            
        
        if issubclass( type( self._result ), Exception ): raise self._result
        else: return self._result
        
    
    def PutResult( self, result ):
        
        self._result = result
        
        self._result_ready.set()
        
    
class Predicate():
    
    def __init__( self, predicate_type, value, count ):
        
        self._predicate_type = predicate_type
        self._value = value
        self._count = count
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._predicate_type, self._value ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def GetCountlessCopy( self ): return Predicate( self._predicate_type, self._value, None )
    
    def GetCount( self ): return self._count
    
    def GetInfo( self ): return ( self._predicate_type, self._value )
    
    def GetPredicateType( self ): return self._predicate_type
    
    def GetUnicode( self ):
        
        if self._predicate_type == PREDICATE_TYPE_SYSTEM:
            
            ( system_predicate_type, info ) = self._value
            
            if system_predicate_type == SYSTEM_PREDICATE_TYPE_EVERYTHING: base = u'system:everything'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_INBOX: base = u'system:inbox'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_ARCHIVE: base = u'system:archive'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_UNTAGGED: base = u'system:untagged'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_LOCAL: base = u'system:local'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_NOT_LOCAL: base = u'system:not local'
            elif system_predicate_type in ( SYSTEM_PREDICATE_TYPE_NUM_TAGS, SYSTEM_PREDICATE_TYPE_WIDTH, SYSTEM_PREDICATE_TYPE_HEIGHT, SYSTEM_PREDICATE_TYPE_RATIO, SYSTEM_PREDICATE_TYPE_DURATION, SYSTEM_PREDICATE_TYPE_NUM_WORDS ):
                
                if system_predicate_type == SYSTEM_PREDICATE_TYPE_NUM_TAGS: base = u'system:number of tags'
                elif system_predicate_type == SYSTEM_PREDICATE_TYPE_WIDTH: base = u'system:width'
                elif system_predicate_type == SYSTEM_PREDICATE_TYPE_HEIGHT: base = u'system:height'
                elif system_predicate_type == SYSTEM_PREDICATE_TYPE_RATIO: base = u'system:ratio'
                elif system_predicate_type == SYSTEM_PREDICATE_TYPE_DURATION: base = u'system:duration'
                elif system_predicate_type == SYSTEM_PREDICATE_TYPE_NUM_WORDS: base = u'system:number of words'
                
                if info is not None:
                    
                    ( operator, value ) = info
                    
                    base += u' ' + operator + u' ' + unicode( value )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_SIZE:
                
                base = u'system:size'
                
                if info is not None:
                    
                    ( operator, size, unit ) = info
                    
                    base += u' ' + operator + u' ' + unicode( size ) + ConvertUnitToString( unit )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_LIMIT:
                
                base = u'system:limit'
                
                if info is not None:
                    
                    value = info
                    
                    base += u' is ' + unicode( value )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_AGE:
                
                base = u'system:age'
                
                if info is not None:
                    
                    ( operator, years, months, days ) = info
                    
                    base += u' ' + operator + u' ' + unicode( years ) + u'y' + unicode( months ) + u'm' + unicode( days ) + u'd'
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_HASH:
                
                base = u'system:hash'
                
                if info is not None:
                    
                    hash = info
                    
                    base += u' is ' + hash.encode( 'hex' )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_MIME:
                
                base = u'system:mime'
                
                if info is not None:
                    
                    mime = info
                    
                    base += u' is ' + mime_string_lookup[ mime ]
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_RATING:
                
                base = u'system:rating'
                
                if info is not None:
                    
                    ( service_identifier, operator, value ) = info
                    
                    base += u' for ' + service_identifier.GetName() + u' ' + operator + u' ' + unicode( value )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_SIMILAR_TO:
                
                base = u'system:similar to '
                
                if info is not None:
                    
                    ( hash, max_hamming ) = info
                    
                    base += u' ' + hash.encode( 'hex' ) + u' using max hamming of ' + unicode( max_hamming )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_FILE_SERVICE:
                
                base = u'system:file service'
                
                if info is not None:
                    
                    ( operator, type, service_identifier ) = info
                    
                    base += u':'
                    
                    if operator == True: base += u' is'
                    else: base += u' is not'
                    
                    if type == PENDING: base += u' pending to '
                    else: base += u' currently in '
                    
                    base += service_identifier.GetName()
                    
                
            
        elif self._predicate_type == PREDICATE_TYPE_TAG:
            
            ( operator, tag ) = self._value
            
            if operator == '-': base = u'-'
            elif operator == '+': base = u''
            
            base += tag
            
        elif self._predicate_type == PREDICATE_TYPE_NAMESPACE:
            
            ( operator, namespace ) = self._value
            
            if operator == '-': base = u'-'
            elif operator == '+': base = u''
            
            base += namespace + u':*'
            
        
        if self._count is None: return base
        else: return base + u' (' + ConvertIntToPrettyString( self._count ) + u')'
        
    
    def GetValue( self ): return self._value
    
    def SetOperator( self, operator ):
        
        if self._predicate_type == PREDICATE_TYPE_TAG:
            
            ( old_operator, tag ) = self._value
            
            self._value = ( operator, tag )
            
        
    
SYSTEM_PREDICATE_INBOX = Predicate( PREDICATE_TYPE_SYSTEM, ( SYSTEM_PREDICATE_TYPE_INBOX, None ), None )
SYSTEM_PREDICATE_ARCHIVE = Predicate( PREDICATE_TYPE_SYSTEM, ( SYSTEM_PREDICATE_TYPE_ARCHIVE, None ), None )
SYSTEM_PREDICATE_LOCAL = Predicate( PREDICATE_TYPE_SYSTEM, ( SYSTEM_PREDICATE_TYPE_LOCAL, None ), None )
SYSTEM_PREDICATE_NOT_LOCAL = Predicate( PREDICATE_TYPE_SYSTEM, ( SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None ), None )

class ResponseContext():
    
    def __init__( self, status_code, mime = None, body = '', filename = None, cookies = [] ):
        
        self._status_code = status_code
        self._mime = mime
        self._body = body
        self._filename = filename
        self._cookies = cookies
        
    
    def GetCookies( self ): return self._cookies
    
    def GetFilename( self ): return self._filename
    
    def GetLength( self ): return len( self._body )
    
    def GetMimeBody( self ): return ( self._mime, self._body )
    
    def GetStatusCode( self ): return self._status_code
    
    def HasBody( self ): return self._body != ''
    
    def HasFilename( self ): return self._filename is not None
    
class ServerPetition( HydrusYAMLBase ):
    
    yaml_tag = u'!ServerPetition'
    
    def __init__( self, petitioner_identifier ):
        
        HydrusYAMLBase.__init__( self )
        
        self._petitioner_identifier = petitioner_identifier
        
    
    def GetPetitionerIdentifier( self ): return self._petitioner_identifier
    
class ServerFilePetition( ServerPetition ):
    
    yaml_tag = u'!ServerFilePetition'
    
    def __init__( self, petitioner_identifier, reason, hashes ):
        
        ServerPetition.__init__( self, petitioner_identifier )
        
        self._reason = reason
        self._hashes = hashes
        
    
    def GetClientPetition( self ): return ClientFilePetitions( [ ( self._reason, self._hashes ) ] )
    
    def GetClientPetitionDenial( self ): return ClientFilePetitionDenial( self._hashes )
    
    def GetPetitionHashes( self ): return self._hashes
    
    def GetPetitionInfo( self ): return ( self._reason, self._hashes )
    
    def GetPetitionInfoDenial( self ): return ( self._hashes, )
    
    def GetPetitionString( self ): return 'For ' + ConvertIntToPrettyString( len( self._hashes ) ) + ' files:' + os.linesep + os.linesep + self._reason
    
class ServerMappingPetition( ServerPetition ):
    
    yaml_tag = u'!ServerMappingPetition'
    
    def __init__( self, petitioner_identifier, reason, tag, hashes ):
        
        ServerPetition.__init__( self, petitioner_identifier )
        
        self._reason = reason
        self._tag = tag
        self._hashes = hashes
        
    
    def GetClientPetition( self ):
        
        hash_ids_to_hashes = { enum : hash for ( enum, hash ) in enumerate( self._hashes ) }
        
        hash_ids = hash_ids_to_hashes.keys()
        
        return ClientMappingPetitions( [ ( self._reason, self._tag, hash_ids ) ], hash_ids_to_hashes )
        
    
    def GetClientPetitionDenial( self ): return ClientMappingPetitionDenial( self._tag, self._hashes )
    
    def GetPetitionHashes( self ): return self._hashes
    
    def GetPetitionInfo( self ): return ( self._reason, self._tag, self._hashes )
    
    def GetPetitionString( self ): return 'Tag: ' + self._tag + ' for ' + ConvertIntToPrettyString( len( self._hashes ) ) + ' files.' + os.linesep + os.linesep + 'Reason: ' + self._reason
    
class ServerServiceIdentifier( HydrusYAMLBase ):
    
    yaml_tag = u'!ServerServiceIdentifier'
    
    def __init__( self, type, port ):
        
        HydrusYAMLBase.__init__( self )
        
        self._type = type
        self._port = port
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._type, self._port ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def GetPort( self ): return self._port
    
    def GetType( self ): return self._type
    
class ServiceUpdate():
    
    def __init__( self, action, service_identifier, info = None ):
        
        self._action = action # make this an enumerated thing, yo
        self._service_identifier = service_identifier
        self._info = info
        
    
    def GetAction( self ): return self._action
    
    def GetInfo( self ): return self._info
    
    def GetServiceIdentifier( self ): return self._service_identifier
    
# sqlite mod

sqlite3.register_adapter( dict, yaml.safe_dump )
sqlite3.register_adapter( list, yaml.safe_dump )
sqlite3.register_adapter( Account, yaml.safe_dump )
sqlite3.register_adapter( AccountType, yaml.safe_dump )
sqlite3.register_converter( 'TEXT_YAML', yaml.safe_load )

sqlite3.register_converter( 'BLOB_BYTES', str )

# for some reason, sqlite doesn't parse to int before this, despite the column affinity
# it gives the register_converter function a bytestring :/
def integer_boolean_to_bool( integer_boolean ): return bool( int( integer_boolean ) )

sqlite3.register_adapter( bool, int )
sqlite3.register_converter( 'INTEGER_BOOLEAN', integer_boolean_to_bool )

# no converters in this case, since we always want to send the dumped string, not the object, to the network
sqlite3.register_adapter( HydrusUpdateFileRepository, yaml.safe_dump )
sqlite3.register_adapter( HydrusUpdateTagRepository, yaml.safe_dump )

# Custom Exceptions

class NetworkVersionException( Exception ): pass
class NoContentException( Exception ): pass
class NotFoundException( Exception ): pass
class NotModifiedException( Exception ): pass
class ForbiddenException( Exception ): pass
class PermissionException( Exception ): pass
class SessionException( Exception ): pass
class ShutdownException( Exception ): pass
class WrongServiceTypeException( Exception ): pass
