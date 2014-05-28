import os
import sys

# dirs

BASE_DIR = sys.path[0]

BIN_DIR = BASE_DIR + os.path.sep + 'bin'
DB_DIR = BASE_DIR + os.path.sep + 'db'
CLIENT_FILES_DIR = DB_DIR + os.path.sep + 'client_files'
SERVER_FILES_DIR = DB_DIR + os.path.sep + 'server_files'
CLIENT_THUMBNAILS_DIR = DB_DIR + os.path.sep + 'client_thumbnails'
SERVER_THUMBNAILS_DIR = DB_DIR + os.path.sep + 'server_thumbnails'
SERVER_MESSAGES_DIR = DB_DIR + os.path.sep + 'server_messages'
CLIENT_UPDATES_DIR = DB_DIR + os.path.sep + 'client_updates'
SERVER_UPDATES_DIR = DB_DIR + os.path.sep + 'server_updates'
LOGS_DIR = BASE_DIR + os.path.sep + 'logs'
STATIC_DIR = BASE_DIR + os.path.sep + 'static'
TEMP_DIR = BASE_DIR + os.path.sep + 'temp'

#

PLATFORM_WINDOWS = False
PLATFORM_OSX  = False
PLATFORM_LINUX = False

if sys.platform == 'win32': PLATFORM_WINDOWS = True
elif sys.platform == 'darwin': PLATFORM_OSX = True
elif sys.platform == 'linux2': PLATFORM_LINUX = True

if PLATFORM_LINUX:
    
    if not hasattr( sys, 'frozen' ):
        
        import wxversion
        
        if not wxversion.checkInstalled( '2.9' ): raise Exception( 'Need wxPython 2.9 on linux!' )
        
        wxversion.select( '2.9' )
        

import wx

import bisect
import bs4
import collections
import cStringIO
import httplib
import HydrusExceptions
import HydrusNetworking
import HydrusPubSub
import itertools
import locale
import Queue
import re
import sqlite3
import threading
import time
import traceback
import yaml

options = {}

# Misc

NETWORK_VERSION = 13
SOFTWARE_VERSION = 117

UNSCALED_THUMBNAIL_DIMENSIONS = ( 200, 200 )

HYDRUS_KEY_LENGTH = 32

UPDATE_DURATION = 100000

lifetimes = [ ( 'one month', 31 * 86400 ), ( 'three months', 3 * 31 * 86400 ), ( 'six months', 6 * 31 * 86400 ), ( 'one year', 12 * 31 * 86400 ), ( 'two years', 24 * 31 * 86400 ), ( 'five years', 60 * 31 * 86400 ), ( 'does not expire', None ) ]

app = None
shutdown = False

is_first_start = False
is_db_updated = False
repos_changed = False
subs_changed = False

http = None

busy_doing_pubsub = False

# Enums

CONTENT_DATA_TYPE_MAPPINGS = 0
CONTENT_DATA_TYPE_TAG_SIBLINGS = 1
CONTENT_DATA_TYPE_TAG_PARENTS = 2
CONTENT_DATA_TYPE_FILES = 3
CONTENT_DATA_TYPE_RATINGS = 4

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
CONTENT_UPDATE_DENY_PEND = 11
CONTENT_UPDATE_DENY_PETITION = 12
CONTENT_UPDATE_ADVANCED = 13

content_update_string_lookup = {}

content_update_string_lookup[ CONTENT_UPDATE_ADD ] = 'add'
content_update_string_lookup[ CONTENT_UPDATE_DELETE ] = 'delete'
content_update_string_lookup[ CONTENT_UPDATE_PENDING ] = 'pending'
content_update_string_lookup[ CONTENT_UPDATE_RESCIND_PENDING ] = 'rescind pending'
content_update_string_lookup[ CONTENT_UPDATE_PETITION ] = 'petition'
content_update_string_lookup[ CONTENT_UPDATE_RESCIND_PETITION ] = 'rescind petition'
content_update_string_lookup[ CONTENT_UPDATE_EDIT_LOG ] = 'edit log'
content_update_string_lookup[ CONTENT_UPDATE_ARCHIVE ] = 'archive'
content_update_string_lookup[ CONTENT_UPDATE_INBOX ] = 'inbox'
content_update_string_lookup[ CONTENT_UPDATE_RATING ] = 'rating'
content_update_string_lookup[ CONTENT_UPDATE_RATINGS_FILTER ] = 'incomplete ratings'
content_update_string_lookup[ CONTENT_UPDATE_DENY_PEND ] = 'deny pend'
content_update_string_lookup[ CONTENT_UPDATE_DENY_PETITION ] = 'deny petition'

IMPORT_FOLDER_TYPE_DELETE = 0
IMPORT_FOLDER_TYPE_SYNCHRONISE = 1

MESSAGE_TYPE_TEXT = 0
MESSAGE_TYPE_ERROR = 1
MESSAGE_TYPE_FILES = 2
MESSAGE_TYPE_GAUGE = 3
MESSAGE_TYPE_DB_ERROR = 4

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
COMBINED_TAG = 10
COMBINED_FILE = 11
LOCAL_BOORU = 12
SERVER_ADMIN = 99
NULL_SERVICE = 100

service_string_lookup = {}

service_string_lookup[ TAG_REPOSITORY ] = 'hydrus tag repository'
service_string_lookup[ FILE_REPOSITORY ] = 'hydrus file repository'
service_string_lookup[ LOCAL_FILE ] = 'hydrus local file service'
service_string_lookup[ MESSAGE_DEPOT ] = 'hydrus message depot'
service_string_lookup[ LOCAL_TAG ] = 'local tag service'
service_string_lookup[ LOCAL_RATING_NUMERICAL ] = 'local numerical rating service'
service_string_lookup[ LOCAL_RATING_LIKE ] = 'local like/dislike rating service'
service_string_lookup[ RATING_NUMERICAL_REPOSITORY ] = 'hydrus numerical rating repository'
service_string_lookup[ RATING_LIKE_REPOSITORY ] = 'hydrus like/dislike rating repository'
service_string_lookup[ COMBINED_TAG ] = 'virtual combined tag service'
service_string_lookup[ COMBINED_FILE ] = 'virtual combined file service'
service_string_lookup[ LOCAL_BOORU ] = 'hydrus local booru'
service_string_lookup[ SERVER_ADMIN ] = 'hydrus server administration'
service_string_lookup[ NULL_SERVICE ] = 'null service'

RATINGS_SERVICES = [ LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY ]
REPOSITORIES = [ TAG_REPOSITORY, FILE_REPOSITORY, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY ]
RESTRICTED_SERVICES = ( REPOSITORIES ) + [ SERVER_ADMIN, MESSAGE_DEPOT ]
REMOTE_SERVICES = list( RESTRICTED_SERVICES )
LOCAL_SERVICES = [ LOCAL_FILE, LOCAL_TAG, LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, LOCAL_BOORU ]
ALL_SERVICES = list( REMOTE_SERVICES ) + list( LOCAL_SERVICES )

SERVICES_WITH_THUMBNAILS = [ FILE_REPOSITORY, LOCAL_FILE ]

DELETE_FILES_PETITION = 0
DELETE_TAG_PETITION = 1

BAN = 0
SUPERBAN = 1
CHANGE_ACCOUNT_TYPE = 2
ADD_TO_EXPIRY = 3
SET_EXPIRY = 4

CURRENT = 0
PENDING = 1
DELETED = 2
PETITIONED = 3
DELETED_PENDING = 4

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
SERVICE_INFO_NUM_PENDING_MAPPINGS = 15
SERVICE_INFO_NUM_PETITIONED_MAPPINGS = 16
SERVICE_INFO_NUM_PENDING_FILES = 15
SERVICE_INFO_NUM_PETITIONED_FILES = 16
SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS = 17
SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS = 18
SERVICE_INFO_NUM_PENDING_TAG_PARENTS = 19
SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS = 20
SERVICE_INFO_NUM_SHARES = 21

SERVICE_UPDATE_ACCOUNT = 0
SERVICE_UPDATE_DELETE_PENDING = 1
SERVICE_UPDATE_ERROR = 2
SERVICE_UPDATE_BEGIN_END = 3
SERVICE_UPDATE_RESET = 4
SERVICE_UPDATE_REQUEST_MADE = 5
SERVICE_UPDATE_LAST_CHECK = 6
SERVICE_UPDATE_NEWS = 7
SERVICE_UPDATE_NEXT_DOWNLOAD_TIMESTAMP = 8
SERVICE_UPDATE_NEXT_PROCESSING_TIMESTAMP = 9

ADD = 0
DELETE = 1
EDIT = 2
SET = 3

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
APPLICATION_ZIP = 11
APPLICATION_HYDRUS_ENCRYPTED_ZIP = 12
AUDIO_MP3 = 13
VIDEO_MP4 = 14
AUDIO_OGG = 15
AUDIO_FLAC = 16
AUDIO_WMA = 17
VIDEO_WMV = 18
UNDETERMINED_WM = 19
VIDEO_MKV = 20
VIDEO_WEBM = 21
APPLICATION_OCTET_STREAM = 100
APPLICATION_UNKNOWN = 101

ALLOWED_MIMES = ( IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_BMP, APPLICATION_FLASH, VIDEO_FLV, VIDEO_MP4, VIDEO_MKV, VIDEO_WEBM, APPLICATION_PDF, AUDIO_MP3, AUDIO_OGG, AUDIO_FLAC, AUDIO_WMA, VIDEO_WMV )

IMAGES = ( IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_BMP )

AUDIO = ( AUDIO_MP3, AUDIO_OGG, AUDIO_FLAC, AUDIO_WMA )

VIDEO = ( VIDEO_FLV, VIDEO_MP4, VIDEO_WMV, VIDEO_MKV, VIDEO_WEBM )

APPLICATIONS = ( APPLICATION_FLASH, APPLICATION_PDF, APPLICATION_ZIP )

NOISY_MIMES = tuple( [ APPLICATION_FLASH ] + list( AUDIO ) + list( VIDEO ) )

ARCHIVES = ( APPLICATION_ZIP, APPLICATION_HYDRUS_ENCRYPTED_ZIP )

MIMES_WITH_THUMBNAILS = ( IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_BMP, VIDEO_WEBM )

# mp3 header is complicated

mime_enum_lookup = {}

mime_enum_lookup[ 'collection' ] = APPLICATION_HYDRUS_CLIENT_COLLECTION
mime_enum_lookup[ 'image/jpe' ] = IMAGE_JPEG
mime_enum_lookup[ 'image/jpeg' ] = IMAGE_JPEG
mime_enum_lookup[ 'image/jpg' ] = IMAGE_JPEG
mime_enum_lookup[ 'image/x-png' ] = IMAGE_PNG
mime_enum_lookup[ 'image/png' ] = IMAGE_PNG
mime_enum_lookup[ 'image/gif' ] = IMAGE_GIF
mime_enum_lookup[ 'image/bmp' ] = IMAGE_BMP
mime_enum_lookup[ 'image' ] = IMAGES
mime_enum_lookup[ 'image/vnd.microsoft.icon' ] = IMAGE_ICON
mime_enum_lookup[ 'application/x-shockwave-flash' ] = APPLICATION_FLASH
mime_enum_lookup[ 'application/octet-stream' ] = APPLICATION_OCTET_STREAM
mime_enum_lookup[ 'application/x-yaml' ] = APPLICATION_YAML
mime_enum_lookup[ 'PDF document' ] = APPLICATION_PDF
mime_enum_lookup[ 'application/pdf' ] = APPLICATION_PDF
mime_enum_lookup[ 'application/zip' ] = APPLICATION_ZIP
mime_enum_lookup[ 'application/hydrus-encrypted-zip' ] = APPLICATION_HYDRUS_ENCRYPTED_ZIP
mime_enum_lookup[ 'application' ] = APPLICATIONS
mime_enum_lookup[ 'audio/mp3' ] = AUDIO_MP3
mime_enum_lookup[ 'audio/ogg' ] = AUDIO_OGG
mime_enum_lookup[ 'audio/flac' ] = AUDIO_FLAC
mime_enum_lookup[ 'audio/x-ms-wma' ] = AUDIO_WMA
mime_enum_lookup[ 'text/html' ] = TEXT_HTML
mime_enum_lookup[ 'video/x-flv' ] = VIDEO_FLV
mime_enum_lookup[ 'video/mp4' ] = VIDEO_MP4
mime_enum_lookup[ 'video/x-ms-wmv' ] = VIDEO_WMV
mime_enum_lookup[ 'video/x-matroska' ] = VIDEO_MKV
mime_enum_lookup[ 'video/webm' ] = VIDEO_WEBM
mime_enum_lookup[ 'video' ] = VIDEO
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
mime_string_lookup[ APPLICATION_ZIP ] = 'application/zip'
mime_string_lookup[ APPLICATION_HYDRUS_ENCRYPTED_ZIP ] = 'application/hydrus-encrypted-zip'
mime_string_lookup[ APPLICATIONS ] = 'application'
mime_string_lookup[ AUDIO_MP3 ] = 'audio/mp3'
mime_string_lookup[ AUDIO_OGG ] = 'audio/ogg'
mime_string_lookup[ AUDIO_FLAC ] = 'audio/flac'
mime_string_lookup[ AUDIO_WMA ] = 'audio/x-ms-wma'
mime_string_lookup[ AUDIO ] = 'audio'
mime_string_lookup[ TEXT_HTML ] = 'text/html'
mime_string_lookup[ VIDEO_FLV ] = 'video/x-flv'
mime_string_lookup[ VIDEO_MP4 ] = 'video/mp4'
mime_string_lookup[ VIDEO_WMV ] = 'video/x-ms-wmv'
mime_string_lookup[ VIDEO_MKV ] = 'video/x-matroska'
mime_string_lookup[ VIDEO_WEBM ] = 'video/webm'
mime_string_lookup[ VIDEO ] = 'video'
mime_string_lookup[ UNDETERMINED_WM ] = 'audio/x-ms-wma or video/x-ms-wmv'
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
mime_ext_lookup[ APPLICATION_ZIP ] = '.zip'
mime_ext_lookup[ APPLICATION_HYDRUS_ENCRYPTED_ZIP ] = '.zip.encrypted'
mime_ext_lookup[ AUDIO_MP3 ] = '.mp3'
mime_ext_lookup[ AUDIO_OGG ] = '.ogg'
mime_ext_lookup[ AUDIO_FLAC ] = '.flac'
mime_ext_lookup[ AUDIO_WMA ] = '.wma'
mime_ext_lookup[ TEXT_HTML ] = '.html'
mime_ext_lookup[ VIDEO_FLV ] = '.flv'
mime_ext_lookup[ VIDEO_MP4 ] = '.mp4'
mime_ext_lookup[ VIDEO_WMV ] = '.wmv'
mime_ext_lookup[ VIDEO_MKV ] = '.mkv'
mime_ext_lookup[ VIDEO_WEBM ] = '.webm'
mime_ext_lookup[ APPLICATION_UNKNOWN ] = ''
#mime_ext_lookup[ 'application/x-rar-compressed' ] = '.rar'

ALLOWED_MIME_EXTENSIONS = [ mime_ext_lookup[ mime ] for mime in ALLOWED_MIMES ]

PREDICATE_TYPE_SYSTEM = 0
PREDICATE_TYPE_TAG = 1
PREDICATE_TYPE_NAMESPACE = 2
PREDICATE_TYPE_PARENT = 3

SITE_TYPE_DEVIANT_ART = 0
SITE_TYPE_GIPHY = 1
SITE_TYPE_PIXIV = 2
SITE_TYPE_BOORU = 3
SITE_TYPE_TUMBLR = 4
SITE_TYPE_HENTAI_FOUNDRY = 5
SITE_TYPE_NEWGROUNDS = 6

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
restricted_requests.append( ( GET, 'access_key_verification', None ) )
restricted_requests.append( ( GET, 'account', None ) )
restricted_requests.append( ( GET, 'account_info', MANAGE_USERS ) )
restricted_requests.append( ( GET, 'account_types', MANAGE_USERS ) )
restricted_requests.append( ( GET, 'options', GENERAL_ADMIN ) )
restricted_requests.append( ( GET, 'registration_keys', GENERAL_ADMIN ) )
restricted_requests.append( ( GET, 'session_key', None ) )
restricted_requests.append( ( GET, 'stats', GENERAL_ADMIN ) )
restricted_requests.append( ( POST, 'account', ( MANAGE_USERS, GENERAL_ADMIN ) ) )
restricted_requests.append( ( POST, 'account_types', GENERAL_ADMIN ) )
restricted_requests.append( ( POST, 'options', GENERAL_ADMIN ) )

admin_requests = list( restricted_requests )
admin_requests.append( ( GET, 'init', None ) )
admin_requests.append( ( GET, 'services', EDIT_SERVICES ) )
admin_requests.append( ( POST, 'backup', EDIT_SERVICES ) )
admin_requests.append( ( POST, 'services', EDIT_SERVICES ) )

repository_requests = list( restricted_requests )
repository_requests.append( ( GET, 'num_petitions', RESOLVE_PETITIONS ) )
repository_requests.append( ( GET, 'petition', RESOLVE_PETITIONS ) )
repository_requests.append( ( GET, 'update', GET_DATA ) )
repository_requests.append( ( POST, 'news', GENERAL_ADMIN ) )
repository_requests.append( ( POST, 'update', POST_DATA ) )

file_repository_requests = list( repository_requests )
file_repository_requests.append( ( GET, 'file', GET_DATA ) )
file_repository_requests.append( ( GET, 'ip', GENERAL_ADMIN ) )
file_repository_requests.append( ( GET, 'thumbnail', GET_DATA ) )
file_repository_requests.append( ( POST, 'file', POST_DATA ) )

tag_repository_requests = list( repository_requests )

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
DEFAULT_OPTIONS[ SERVER_ADMIN ][ 'upnp' ] = None

DEFAULT_OPTIONS[ FILE_REPOSITORY ] = {}
DEFAULT_OPTIONS[ FILE_REPOSITORY ][ 'max_monthly_data' ] = None
DEFAULT_OPTIONS[ FILE_REPOSITORY ][ 'max_storage' ] = None
DEFAULT_OPTIONS[ FILE_REPOSITORY ][ 'log_uploader_ips' ] = False
DEFAULT_OPTIONS[ FILE_REPOSITORY ][ 'message' ] = 'hydrus file repository'
DEFAULT_OPTIONS[ FILE_REPOSITORY ][ 'upnp' ] = None

DEFAULT_OPTIONS[ TAG_REPOSITORY ] = {}
DEFAULT_OPTIONS[ TAG_REPOSITORY ][ 'max_monthly_data' ] = None
DEFAULT_OPTIONS[ TAG_REPOSITORY ][ 'message' ] = 'hydrus tag repository'
DEFAULT_OPTIONS[ TAG_REPOSITORY ][ 'upnp' ] = None

DEFAULT_OPTIONS[ MESSAGE_DEPOT ] = {}
DEFAULT_OPTIONS[ MESSAGE_DEPOT ][ 'max_monthly_data' ] = None
DEFAULT_OPTIONS[ MESSAGE_DEPOT ][ 'max_storage' ] = None
DEFAULT_OPTIONS[ MESSAGE_DEPOT ][ 'message' ] = 'hydrus message depot'
DEFAULT_OPTIONS[ MESSAGE_DEPOT ][ 'upnp' ] = None

# Hydrus pubsub

EVT_PUBSUB = HydrusPubSub.EVT_PUBSUB
pubsub = HydrusPubSub.HydrusPubSub()

def default_dict_list(): return collections.defaultdict( list )

def default_dict_set(): return collections.defaultdict( set )

def b( text_producing_object ):
    
    if type( text_producing_object ) == unicode: return text_producing_object.encode( 'utf-8' )
    else: return str( text_producing_object )
    
def ChunkifyList( the_list, chunk_size ):
    
    for i in xrange( 0, len( the_list ), chunk_size ): yield the_list[ i : i + chunk_size ]
    
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
    
def CleanTag( tag ):
    
    tag = tag[:1024]
    
    if tag == '': return ''
    
    tag = tag.lower()
    
    tag = u( tag )
    
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
    
def ConvertIntToPrettyString( num ): return u( locale.format( "%d", num, grouping = True ) )

def ConvertMillisecondsToPrettyTime( ms ):
    
    hours = ms / 3600000
    
    if hours == 1: hours_result = '1 hour'
    else: hours_result = u( hours ) + ' hours'
    
    ms = ms % 3600000
    
    minutes = ms / 60000
    
    if minutes == 1: minutes_result = '1 minute'
    else: minutes_result = u( minutes ) + ' minutes'
    
    ms = ms % 60000
    
    seconds = ms / 1000
    
    if seconds == 1: seconds_result = '1 second'
    else: seconds_result = u( seconds ) + ' seconds'
    
    detailed_seconds = float( ms ) / 1000.0
    
    if detailed_seconds == 1.0: detailed_seconds_result = '1.0 seconds'
    else:detailed_seconds_result = '%.1f' % detailed_seconds + ' seconds'
    
    ms = ms % 1000
    
    if ms == 1: milliseconds_result = '1 millisecond'
    else: milliseconds_result = u( ms ) + ' milliseconds'
    
    if hours > 0: return hours_result + ' ' + minutes_result
    
    if minutes > 0: return minutes_result + ' ' + seconds_result
    
    if seconds > 0: return detailed_seconds_result
    
    return milliseconds_result
    
def ConvertNumericalRatingToPrettyString( lower, upper, rating, rounded_result = False, out_of = True ):
    
    rating_converted = ( rating * ( upper - lower ) ) + lower
    
    if rounded_result: s = u( '%.2f' % round( rating_converted ) )
    else: s = u( '%.2f' % rating_converted )
    
    if out_of:
        
        if lower in ( 0, 1 ): s += '/' + u( '%.2f' % upper )
        
    
    return s
    
def ConvertPortablePathToAbsPath( portable_path ):
    
    if portable_path is None: return None
    
    if os.path.isabs( portable_path ): abs_path = portable_path
    else: abs_path = os.path.normpath( BASE_DIR + os.path.sep + portable_path )
    
    if os.path.exists( abs_path ): return abs_path
    else: return None
    
def ConvertServiceIdentifiersToContentUpdatesToPrettyString( service_identifiers_to_content_updates ):
    
    num_files = 0
    actions = set()
    locations = set()
    
    extra_words = ''
    
    for ( service_identifier, content_updates ) in service_identifiers_to_content_updates.items():
        
        if len( content_updates ) > 0: locations.add( service_identifier.GetName() )
        
        for content_update in content_updates:
            
            ( data_type, action, row ) = content_update.ToTuple()
            
            if data_type == CONTENT_DATA_TYPE_MAPPINGS: extra_words = ' tags for'
            
            actions.add( content_update_string_lookup[ action ] )
            
            num_files += len( content_update.GetHashes() )
            
        
    
    s = ', '.join( locations ) + '->' + ', '.join( actions ) + extra_words + ' ' + ConvertIntToPrettyString( num_files ) + ' files'
    
    return s
    
def ConvertShortcutToPrettyShortcut( modifier, key, action ):
    
    if modifier == wx.ACCEL_NORMAL: modifier = ''
    elif modifier == wx.ACCEL_ALT: modifier = 'alt'
    elif modifier == wx.ACCEL_CTRL: modifier = 'ctrl'
    elif modifier == wx.ACCEL_SHIFT: modifier = 'shift'
    
    if key in range( 65, 91 ): key = chr( key + 32 ) # + 32 for converting ascii A -> a
    elif key in range( 97, 123 ): key = chr( key )
    else: key = wxk_code_string_lookup[ key ]
    
    return ( modifier, key, action )
    
def ConvertStatusToPrefix( status ):
    
    if status == CURRENT: return ''
    elif status == PENDING: return '(+) '
    elif status == PETITIONED: return '(-) '
    elif status == DELETED: return '(X) '
    elif status == DELETED_PENDING: return '(X+) '
    
def ConvertTimestampToPrettyAge( timestamp ):
    
    if timestamp == 0 or timestamp is None: return 'unknown age'
    
    age = GetNow() - timestamp
    
    seconds = age % 60
    if seconds == 1: s = '1 second'
    else: s = u( seconds ) + ' seconds'
    
    age = age / 60
    minutes = age % 60
    if minutes == 1: m = '1 minute'
    else: m = u( minutes ) + ' minutes'
    
    age = age / 60
    hours = age % 24
    if hours == 1: h = '1 hour'
    else: h = u( hours ) + ' hours'
    
    age = age / 24
    days = age % 30
    if days == 1: d = '1 day'
    else: d = u( days ) + ' days'
    
    age = age / 30
    months = age % 12
    if months == 1: mo = '1 month'
    else: mo = u( months ) + ' months'
    
    years = age / 12
    if years == 1: y = '1 year'
    else: y = u( years ) + ' years'
    
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
    else: s = u( seconds ) + ' seconds'
    
    age = age / 60
    minutes = age % 60
    if minutes == 1: m = '1 minute'
    else: m = u( minutes ) + ' minutes'
    
    age = age / 60
    hours = age % 24
    if hours == 1: h = '1 hour'
    else: h = u( hours ) + ' hours'
    
    age = age / 24
    days = age % 30
    if days == 1: d = '1 day'
    else: d = u( days ) + ' days'
    
    age = age / 30
    months = age % 12
    if months == 1: mo = '1 month'
    else: mo = u( months ) + ' months'
    
    years = age / 12
    if years == 1: y = '1 year'
    else: y = u( years ) + ' years'
    
    if years > 0: return ' '.join( ( y, mo ) ) + ' ago'
    elif months > 0: return ' '.join( ( mo, d ) ) + ' ago'
    elif days > 0: return ' '.join( ( d, h ) ) + ' ago'
    elif hours > 0: return ' '.join( ( h, m ) ) + ' ago'
    else: return ' '.join( ( m, s ) ) + ' ago'
    
def ConvertTimestampToPrettyExpiry( timestamp ):
    
    if timestamp is None: return 'does not expire'
    if timestamp == 0: return 'unknown expiration'
    
    expiry = GetNow() - timestamp
    
    if expiry >= 0: already_happend = True
    else:
        
        expiry *= -1
        
        already_happend = False
        
    
    seconds = expiry % 60
    if seconds == 1: s = '1 second'
    else: s = u( seconds ) + ' seconds'
    
    expiry = expiry / 60
    minutes = expiry % 60
    if minutes == 1: m = '1 minute'
    else: m = u( minutes ) + ' minutes'
    
    expiry = expiry / 60
    hours = expiry % 24
    if hours == 1: h = '1 hour'
    else: h = u( hours ) + ' hours'
    
    expiry = expiry / 24
    days = expiry % 30
    if days == 1: d = '1 day'
    else: d = u( days ) + ' days'
    
    expiry = expiry / 30
    months = expiry % 12
    if months == 1: mo = '1 month'
    else: mo = u( months ) + ' months'
    
    years = expiry / 12
    if years == 1: y = '1 year'
    else: y = u( years ) + ' years'
    
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
    else: s = u( seconds ) + ' seconds'
    
    pending = pending / 60
    minutes = pending % 60
    if minutes == 1: m = '1 minute'
    else: m = u( minutes ) + ' minutes'
    
    pending = pending / 60
    hours = pending % 24
    if hours == 1: h = '1 hour'
    else: h = u( hours ) + ' hours'
    
    pending = pending / 24
    days = pending % 30
    if days == 1: d = '1 day'
    else: d = u( days ) + ' days'
    
    pending = pending / 30
    months = pending % 12
    if months == 1: mo = '1 month'
    else: mo = u( months ) + ' months'
    
    years = pending / 12
    if years == 1: y = '1 year'
    else: y = u( years ) + ' years'
    
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
    else: s = u( seconds ) + ' seconds'
    
    age = age / 60
    minutes = age % 60
    if minutes == 1: m = '1 minute'
    else: m = u( minutes ) + ' minutes'
    
    age = age / 60
    hours = age % 24
    if hours == 1: h = '1 hour'
    else: h = u( hours ) + ' hours'
    
    age = age / 24
    days = age % 30
    if days == 1: d = '1 day'
    else: d = u( days ) + ' days'
    
    age = age / 30
    months = age % 12
    if months == 1: mo = '1 month'
    else: mo = u( months ) + ' months'
    
    years = age / 12
    if years == 1: y = '1 year'
    else: y = u( years ) + ' years'
    
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
    
def ConvertUnitToInteger( unit ):
    
    if unit == 'B': return 1
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
    
def GetEmptyDataDict():
    
    data = collections.defaultdict( default_dict_list )
    
    return data
    
def GetNow(): return int( time.time() )

def GetShortcutFromEvent( event ):
    
    modifier = wx.ACCEL_NORMAL
    
    if event.AltDown(): modifier = wx.ACCEL_ALT
    elif event.CmdDown(): modifier = wx.ACCEL_CTRL
    elif event.ShiftDown(): modifier = wx.ACCEL_SHIFT
    
    key = event.KeyCode
    
    return ( modifier, key )
    
def GetTempPath(): return TEMP_DIR + os.path.sep + os.urandom( 32 ).encode( 'hex' )

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

def MergeKeyToListDicts( key_to_list_dicts ):
    
    result = collections.defaultdict( list )
    
    for key_to_list_dict in key_to_list_dicts:
        
        for ( key, value ) in key_to_list_dict.items(): result[ key ].extend( value )
        
    
    return result
    
def SearchEntryMatchesPredicate( search_entry, predicate ):
    
    ( predicate_type, info ) = predicate.GetInfo()
    
    if predicate_type == PREDICATE_TYPE_TAG:
        
        ( operator, value ) = info
        
        return SearchEntryMatchesTag( search_entry, value )
        
    else: return False
    
def SearchEntryMatchesTag( search_entry, tag, search_siblings = True ):
    
    if ':' in search_entry: ( search_entry_namespace, search_entry ) = search_entry.split( ':', 1 )
    
    if search_siblings:
        
        sibling_manager = app.GetManager( 'tag_siblings' )
        
        tags = sibling_manager.GetAllSiblings( tag )
        
    else: tags = [ tag ]
    
    for tag in tags:
        
        if ':' in tag:
            
            ( n, t ) = tag.split( ':', 1 )
            
            comparee = t
            
        else: comparee = tag
        
        if comparee.startswith( search_entry ) or ' ' + search_entry in comparee: return True
        
    
    return False
    
def ShowExceptionDefault( e ):
    
    etype = type( e )
    
    value = u( e )
    
    trace_list = traceback.format_stack()
    
    trace = ''.join( trace_list )
    
    message = u( etype.__name__ ) + ': ' + u( value ) + os.linesep + u( trace )
    
    try: print( message )
    except: print( repr( message ) )
    
ShowException = ShowExceptionDefault

def ShowTextDefault( text ):
    
    print( text )
    
ShowText = ShowTextDefault

def SplayListForDB( xs ): return '(' + ','.join( [ '"' + u( x ) + '"' for x in xs ] ) + ')'

def SplayTupleListForDB( first_column_name, second_column_name, xys ): return ' OR '.join( [ '( ' + first_column_name + '=' + u( x ) + ' AND ' + second_column_name + ' IN ' + SplayListForDB( ys ) + ' )' for ( x, ys ) in xys ] )

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
    
def u( text_producing_object ):
    
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
    
    def __init__( self, account_id, account_type, created, expiry, used_data, banned_info = None ):
        
        HydrusYAMLBase.__init__( self )
        
        self._account_id = account_id
        self._account_type = account_type
        self._created = created
        self._expiry = expiry
        self._used_data = used_data
        self._banned_info = banned_info
        
        self._object_instantiation_timestamp = GetNow()
        
    
    def __repr__( self ): return self.ConvertToString()
    
    def __str__( self ): return self.ConvertToString()
    
    def _IsBanned( self ):
        
        if self._banned_info is None: return False
        else:
            
            ( reason, created, expiry ) = self._banned_info
            
            if expiry is None: return True
            else: return GetNow() > expiry
            
        
    
    def _IsExpired( self ):
        
        if self._expiry is None: return False
        else: return GetNow() > self._expiry
        
    
    def CheckPermission( self, permission ):
        
        if self._IsBanned(): raise HydrusExceptions.PermissionException( 'This account is banned!' )
        
        if self._IsExpired(): raise HydrusExceptions.PermissionException( 'This account is expired.' )
        
        ( max_num_bytes, max_num_requests ) = self._account_type.GetMaxMonthlyData()
        
        ( used_bytes, used_requests ) = self._used_data
        
        if max_num_bytes is not None and used_bytes > max_num_bytes: raise HydrusExceptions.PermissionException( 'You have hit your data transfer limit (' + ConvertIntToBytes( max_num_bytes ) + '), and cannot make any more requests for the month.' )
        
        if max_num_requests is not None and used_requests > max_num_requests: raise HydrusExceptions.PermissionException( 'You have hit your requests limit (' + ConvertIntToPrettyString( max_num_requests ) + '), and cannot make any more requests for the month.' )
        
        if not self._account_type.HasPermission( permission ): raise HydrusExceptions.PermissionException( 'You do not have permission to do that.' )
        
    
    def ConvertToString( self ): return ConvertTimestampToPrettyAge( self._created ) + os.linesep + self._account_type.ConvertToString( self._used_data ) + os.linesep + 'which '+ ConvertTimestampToPrettyExpiry( self._expiry )
    
    def GetAccountIdentifier( self ): return AccountIdentifier( account_id = self._account_id )
    
    def GetAccountType( self ): return self._account_type
    
    def GetBannedInfo( self ): return self._banned_info
    
    def GetCreated( self ): return self._created
    
    def GetExpiry( self ): return self._expiry
    
    def GetExpiryString( self ):
        
        if self._IsBanned():
            
            ( reason, created, expiry ) = self._banned_info
            
            return 'banned ' + ConvertTimestampToPrettyAge( created ) + ', ' + ConvertTimestampToPrettyExpiry( expiry ) + ' because: ' + reason
            
        else: return ConvertTimestampToPrettyAge( self._created ) + ' and ' + ConvertTimestampToPrettyExpiry( self._expiry )
        
    
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
        
        if self._IsBanned(): return False
        
        if self._IsExpired(): return False
        
        ( max_num_bytes, max_num_requests ) = self._account_type.GetMaxMonthlyData()
        
        ( used_bytes, used_requests ) = self._used_data
        
        if max_num_bytes is not None and used_bytes >= max_num_bytes: return False
        if max_num_requests is not None and used_requests >= max_num_requests: return False
        
        return self._account_type.HasPermission( permission )
        
    
    def IsAdmin( self ): return True in [ self.HasPermissions( permission ) for permission in ADMIN_PERMISSIONS ]
    
    def IsBanned( self ): return self._IsBanned()
    
    def IsStale( self ): return self._object_instantiation_timestamp + UPDATE_DURATION * 5 < GetNow()
    
    def MakeFresh( self ): self._object_instantiation_timestamp = GetNow()
    
    def MakeStale( self ): self._object_instantiation_timestamp = 0
    
    def RequestMade( self, num_bytes ):
        
        ( used_bytes, used_requests ) = self._used_data
        
        used_bytes += num_bytes
        used_requests += 1
        
        self._used_data = ( used_bytes, used_requests )
        
    
class AccountIdentifier( HydrusYAMLBase ):
    
    TYPE_ACCOUNT_ID = 0
    TYPE_ACCESS_KEY = 1
    TYPE_HASH = 2
    TYPE_MAPPING = 3
    TYPE_SIBLING = 4
    TYPE_PARENT = 5
    
    yaml_tag = u'!AccountIdentifier'
    
    def __init__( self, access_key = None, hash = None, tag = None, account_id = None ):
        
        HydrusYAMLBase.__init__( self )
        
        if account_id is not None:
            
            self._type = self.TYPE_ACCOUNT_ID
            self._data = account_id
            
        elif access_key is not None:
            
            self._type = self.TYPE_ACCESS_KEY
            self._data = access_key
            
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
    
    def __repr__( self ): return 'Account Identifier: ' + u( ( self._type, self._data ) )
    
    def GetData( self ): return self._data
    
    def HasAccessKey( self ): return self._type == self.TYPE_ACCESS_KEY
    
    def HasAccountId( self ): return self._type == self.TYPE_ACCOUNT_ID
    
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
    
UNKNOWN_ACCOUNT_TYPE = AccountType( 'unknown account', [], ( None, None ) )

def GetUnknownAccount(): return Account( 0, UNKNOWN_ACCOUNT_TYPE, 0, None, ( 0, 0 ) )

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
    
    def __repr__( self ): return 'Client Service Identifier: ' + u( ( self._name, service_string_lookup[ self._type ] ) )
    
    def GetInfo( self ): return ( self._service_key, self._type, self._name )
    
    def GetName( self ): return self._name
    
    def GetServiceKey( self ): return self._service_key
    
    def GetType( self ): return self._type
    
LOCAL_FILE_SERVICE_IDENTIFIER = ClientServiceIdentifier( 'local files', LOCAL_FILE, 'local files' )
LOCAL_TAG_SERVICE_IDENTIFIER = ClientServiceIdentifier( 'local tags', LOCAL_TAG, 'local tags' )
LOCAL_BOORU_SERVICE_IDENTIFIER = ClientServiceIdentifier( 'local booru', LOCAL_BOORU, 'local booru' )
COMBINED_FILE_SERVICE_IDENTIFIER = ClientServiceIdentifier( 'all known files', COMBINED_FILE, 'all known files' )
COMBINED_TAG_SERVICE_IDENTIFIER = ClientServiceIdentifier( 'all known tags', COMBINED_TAG, 'all known tags' )
NULL_SERVICE_IDENTIFIER = ClientServiceIdentifier( '', NULL_SERVICE, 'no service' )

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
        
        data_types = [ CONTENT_DATA_TYPE_FILES, CONTENT_DATA_TYPE_MAPPINGS, CONTENT_DATA_TYPE_TAG_SIBLINGS, CONTENT_DATA_TYPE_TAG_PARENTS ]
        actions = [ CONTENT_UPDATE_PENDING, CONTENT_UPDATE_PETITION, CONTENT_UPDATE_DENY_PEND, CONTENT_UPDATE_DENY_PETITION ]
        
        content_updates = []
        
        for ( data_type, action ) in itertools.product( data_types, actions ):
            
            munge_row = lambda row: row
            
            if for_client:
                
                if action == CONTENT_UPDATE_PENDING: new_action = CONTENT_UPDATE_ADD
                elif action == CONTENT_UPDATE_PETITION: new_action = CONTENT_UPDATE_DELETE
                else: continue
                
                if data_type in ( CONTENT_DATA_TYPE_TAG_SIBLINGS, CONTENT_DATA_TYPE_TAG_PARENTS ) and action in ( CONTENT_UPDATE_PENDING, CONTENT_UPDATE_PETITION ):
                    
                    munge_row = lambda ( pair, reason ): pair
                    
                elif data_type == CONTENT_DATA_TYPE_FILES and action == CONTENT_UPDATE_PETITION:
                    
                    munge_row = lambda ( hashes, reason ): hashes
                    
                elif data_type == CONTENT_DATA_TYPE_MAPPINGS and action == CONTENT_UPDATE_PETITION:
                    
                    munge_row = lambda ( tag, hashes, reason ): ( tag, hashes )
                    
                
            else: new_action = action
            
            content_updates.extend( [ ContentUpdate( data_type, new_action, munge_row( row ) ) for row in self.GetContentDataIterator( data_type, action ) ] )
            
        
        return content_updates
        
    
    def GetHashes( self ): return self._hash_ids_to_hashes.values()
    
    def GetContentDataIterator( self, data_type, action ):
        
        if data_type not in self._content_data or action not in self._content_data[ data_type ]: return ()
        
        data = self._content_data[ data_type ][ action ]
        
        if data_type == CONTENT_DATA_TYPE_FILES:
            
            if action == CONTENT_UPDATE_PETITION: return ( ( { self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids }, reason ) for ( hash_ids, reason ) in data )
            else: return ( { self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids } for hash_ids in ( data, ) )
            
        if data_type == CONTENT_DATA_TYPE_MAPPINGS:
            
            if action == CONTENT_UPDATE_PETITION: return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ], reason ) for ( tag, hash_ids, reason ) in data )
            else: return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( tag, hash_ids ) in data )
            
        else: return data.__iter__()
        
    
    def GetTags( self ):
        
        tags = set()
        
        try: tags.update( ( tag for ( tag, hash_ids ) in self._content_data[ CONTENT_DATA_TYPE_MAPPINGS ][ CONTENT_UPDATE_PENDING ] ) )
        except: pass
        
        try: tags.update( ( tag for ( tag, hash_ids, reason ) in self._content_data[ CONTENT_DATA_TYPE_MAPPINGS ][ CONTENT_UPDATE_PETITION ] ) )
        except: pass
        
        return tags
        
    
    def IsEmpty( self ):
        
        num_total = 0
        
        for data_type in self._content_data:
            
            for action in self._content_data[ data_type ]: num_total += len( self._content_data[ data_type ][ action ] )
            
        
        return num_total == 0
        
    
class ContentUpdate():
    
    def __init__( self, data_type, action, row ):
        
        self._data_type = data_type
        self._action = action
        self._row = row
        
    
    def __eq__( self, other ): return self._data_type == other._data_type and self._action == other._action and self._row == other._row
    
    def __ne__( self, other ): return not self.__eq__( other )
    
    def __repr__( self ): return 'Content Update: ' + u( ( self._data_type, self._action, self._row ) )
    
    def GetHashes( self ):
        
        if self._data_type == CONTENT_DATA_TYPE_FILES:
            
            if self._action == CONTENT_UPDATE_ADD:
                
                hash = self._row[0]
                
                hashes = set( ( hash, ) )
                
            elif self._action in ( CONTENT_UPDATE_ARCHIVE, CONTENT_UPDATE_DELETE, CONTENT_UPDATE_INBOX, CONTENT_UPDATE_PENDING, CONTENT_UPDATE_RESCIND_PENDING, CONTENT_UPDATE_RESCIND_PETITION ): hashes = self._row
            elif self._action == CONTENT_UPDATE_PETITION: ( hashes, reason ) = self._row
            
        elif self._data_type == CONTENT_DATA_TYPE_MAPPINGS:
            
            if self._action == CONTENT_UPDATE_PETITION: ( tag, hashes, reason ) = self._row
            else: ( tag, hashes ) = self._row
            
        elif self._data_type in ( CONTENT_DATA_TYPE_TAG_PARENTS, CONTENT_DATA_TYPE_TAG_SIBLINGS ): hashes = set()
        elif self._data_type == CONTENT_DATA_TYPE_RATINGS:
            
            if self._action == CONTENT_UPDATE_ADD: ( rating, hashes ) = self._row
            elif self._action == CONTENT_UPDATE_RATINGS_FILTER: ( min, max, hashes ) = self._row
            
        
        if type( hashes ) != set: hashes = set( hashes )
        
        return hashes
        
    
    def ToTuple( self ): return ( self._data_type, self._action, self._row )
    
class JobDatabase():
    
    yaml_tag = u'!JobDatabase'
    
    def __init__( self, action, type, synchronous, *args, **kwargs ):
        
        self._action = action
        self._type = type
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
            elif shutdown: raise Exception( 'Application quit before db could serve result!' )
            
        
        if isinstance( self._result, Exception ):
            
            if isinstance( self._result, HydrusExceptions.DBException ):
                
                ( text, gumpf, db_traceback ) = self._result.args
                
                trace_list = traceback.format_stack()
                
                caller_traceback = 'Stack Trace (most recent call last):' + os.linesep + os.linesep + os.linesep.join( trace_list )
                
                raise HydrusExceptions.DBException( text, caller_traceback, db_traceback )
                
            else: raise self._result
            
        else: return self._result
        
    
    def GetType( self ): return self._type
    
    def IsSynchronous( self ): return self._synchronous
    
    def PutResult( self, result ):
        
        self._result = result
        
        self._result_ready.set()
        
    
class JobKey():
    
    def __init__( self ):
        
        self._key = os.urandom( 32 )
        
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
        
    
    def Finish( self ): self._done.set()
    
    def GetKey( self ): return self._key
    
    def GetVariable( self, name ):
        
        with self._variable_lock: return self._variables[ name ]
        
    
    def HasVariable( self, name ):
        
        with self._variable_lock: return name in self._variables
        
    
    def IsBegun( self ): return self._begun.is_set()
    
    def IsCancelled( self ): return shutdown or self._cancelled.is_set()
    
    def IsDone( self ): return shutdown or self._done.is_set()
    
    def IsPaused( self ): return self._paused.is_set()
    
    def IsWorking( self ): return self.IsBegun() and not self.IsDone()
    
    def Pause( self ): self._paused.set()
    
    def PauseResume( self ):
        
        if self._paused.is_set(): self._paused.clear()
        else: self._paused.set()
        
    
    def Resume( self ): self._paused.clear()
    
    def SetVariable( self, name, value ):
        
        with self._variable_lock: self._variables[ name ] = value
        
    
    def WaitOnPause( self ):
        
        while self._paused.is_set():
            
            time.sleep( 0.1 )
            
            if shutdown or self.IsDone(): return
            
        
    
class JobNetwork():
    
    yaml_tag = u'!JobNetwork'
    
    def __init__( self, request_type, request, headers = {}, body = None, response_to_path = False, redirects_permitted = 4, service_identifier = None ):
        
        self._request_type = request_type
        self._request = request
        self._headers = headers
        self._body = body
        self._response_to_path = response_to_path
        self._redirects_permitted = redirects_permitted
        self._service_identifier = service_identifier
        
        self._result = None
        self._result_ready = threading.Event()
        
    
    def ToTuple( self ): return ( self._request_type, self._request, self._headers, self._body, self._response_to_path, self._redirects_permitted, self._service_identifier )
    
    def GetResult( self ):
        
        while True:
            
            if self._result_ready.wait( 5 ) == True: break
            elif shutdown: raise Exception( 'Application quit before network could serve result!' )
            
        
        if issubclass( type( self._result ), Exception ):
            
            etype = type( self._result )
            
            network_traceback = unicode( self._result )
            
            trace_list = traceback.format_stack()
            
            my_trace = 'Stack Trace (most recent call last):' + os.linesep + os.linesep + os.linesep.join( trace_list )
            
            full_message = os.linesep.join( ( 'Calling Thread:', my_trace, 'Network Thread:', network_traceback ) )
            
            raise etype( full_message )
            
        else: return self._result
        
    
    def PutResult( self, result ):
        
        self._result = result
        
        self._result_ready.set()
        
    
class Message():
    
    def __init__( self, message_type, info ):
        
        self._message_type = message_type
        self._info = info
        
        self._closed = False
        
        self._lock = threading.Lock()
        
    
    def Close( self ): self._closed = True
    
    def GetInfo( self, name ):
        
        with self._lock: return self._info[ name ]
        
    
    def GetType( self ): return self._message_type
    
    def HasInfo( self, name ):
        
        with self._lock: return name in self._info
        
    
    def IsClosed( self ): return self._closed
    
    def SetInfo( self, name, value ):
        
        with self._lock: self._info[ name ] = value
        
    
class MessageGauge( Message ):
    
    def __init__( self, message_type, text ):
        
        info = {}
        
        info[ 'mode' ] = 'text'
        info[ 'text' ] = text
        
        Message.__init__( self, message_type, info )
        
    
class Predicate( HydrusYAMLBase ):
    
    yaml_tag = u'!Predicate'
    
    def __init__( self, predicate_type, value, counts = {} ):
        
        self._predicate_type = predicate_type
        self._value = value
        
        self._counts = {}
        
        self._counts[ CURRENT ] = 0
        self._counts[ PENDING ] = 0
        
        for ( type, count ) in counts.items(): self.AddToCount( type, count )
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return ( self._predicate_type, self._value ).__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Predicate: ' + u( ( self._predicate_type, self._value, self._counts ) )
    
    def AddToCount( self, type, count ): self._counts[ type ] += count
    
    def GetCopy( self ): return Predicate( self._predicate_type, self._value, self._counts )
    
    def GetCountlessCopy( self ): return Predicate( self._predicate_type, self._value )
    
    def GetCount( self, type = None ):
        
        if type is None: return sum( self._counts.values() )
        else: return self._counts[ type ]
        
    
    def GetInfo( self ): return ( self._predicate_type, self._value )
    
    def GetPredicateType( self ): return self._predicate_type
    
    def GetUnicode( self, with_count = True ):
        
        count_text = u''
        
        if with_count:
            
            count_text 
            
            if self._counts[ CURRENT ] > 0: count_text += u' (' + ConvertIntToPrettyString( self._counts[ CURRENT ] ) + u')'
            if self._counts[ PENDING ] > 0: count_text += u' (+' + ConvertIntToPrettyString( self._counts[ PENDING ] ) + u')'
            
        
        if self._predicate_type == PREDICATE_TYPE_SYSTEM:
            
            ( system_predicate_type, info ) = self._value
            
            if system_predicate_type == SYSTEM_PREDICATE_TYPE_EVERYTHING: base = u'system:everything'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_INBOX: base = u'system:inbox'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_ARCHIVE: base = u'system:archive'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_UNTAGGED: base = u'system:untagged'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_LOCAL: base = u'system:local'
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_NOT_LOCAL: base = u'system:not local'
            elif system_predicate_type in ( SYSTEM_PREDICATE_TYPE_NUM_TAGS, SYSTEM_PREDICATE_TYPE_WIDTH, SYSTEM_PREDICATE_TYPE_HEIGHT, SYSTEM_PREDICATE_TYPE_DURATION, SYSTEM_PREDICATE_TYPE_NUM_WORDS ):
                
                if system_predicate_type == SYSTEM_PREDICATE_TYPE_NUM_TAGS: base = u'system:number of tags'
                elif system_predicate_type == SYSTEM_PREDICATE_TYPE_WIDTH: base = u'system:width'
                elif system_predicate_type == SYSTEM_PREDICATE_TYPE_HEIGHT: base = u'system:height'
                elif system_predicate_type == SYSTEM_PREDICATE_TYPE_DURATION: base = u'system:duration'
                elif system_predicate_type == SYSTEM_PREDICATE_TYPE_NUM_WORDS: base = u'system:number of words'
                
                if info is not None:
                    
                    ( operator, value ) = info
                    
                    base += u' ' + operator + u' ' + u( value )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_RATIO:
                
                base = u'system:ratio'
                
                if info is not None:
                    
                    ( operator, ratio_width, ratio_height ) = info
                    
                    base += u' ' + operator + u' ' + u( ratio_width ) + u':' + u( ratio_height )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_SIZE:
                
                base = u'system:size'
                
                if info is not None:
                    
                    ( operator, size, unit ) = info
                    
                    base += u' ' + operator + u' ' + u( size ) + ConvertUnitToString( unit )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_LIMIT:
                
                base = u'system:limit'
                
                if info is not None:
                    
                    value = info
                    
                    base += u' is ' + u( value )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_AGE:
                
                base = u'system:age'
                
                if info is not None:
                    
                    ( operator, years, months, days, hours ) = info
                    
                    base += u' ' + operator + u' ' + u( years ) + u'y' + u( months ) + u'm' + u( days ) + u'd' + u( hours ) + u'h'
                    
                
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
                    
                    base += u' for ' + service_identifier.GetName() + u' ' + operator + u' ' + u( value )
                    
                
            elif system_predicate_type == SYSTEM_PREDICATE_TYPE_SIMILAR_TO:
                
                base = u'system:similar to '
                
                if info is not None:
                    
                    ( hash, max_hamming ) = info
                    
                    base += u' ' + hash.encode( 'hex' ) + u' using max hamming of ' + u( max_hamming )
                    
                
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
                    
                
            
            base += count_text
            
        elif self._predicate_type == PREDICATE_TYPE_TAG:
            
            ( operator, tag ) = self._value
            
            if operator == '-': base = u'-'
            elif operator == '+': base = u''
            
            base += tag
            
            base += count_text
            
            siblings_manager = app.GetManager( 'tag_siblings' )
            
            sibling = siblings_manager.GetSibling( tag )
            
            if sibling is not None: base += u' (' + sibling + u')'
            
        elif self._predicate_type == PREDICATE_TYPE_PARENT:
            
            base = '    '
            
            tag = self._value
            
            base += tag
            
            base += count_text
            
        elif self._predicate_type == PREDICATE_TYPE_NAMESPACE:
            
            ( operator, namespace ) = self._value
            
            if operator == '-': base = u'-'
            elif operator == '+': base = u''
            
            base += namespace + u':*'
            
        
        return base
        
    
    def GetTag( self ):
        
        if self._predicate_type == PREDICATE_TYPE_TAG:
            
            ( operator, tag ) = self._value
            
            return tag
            
        else: return 'no tag'
        
    
    def GetValue( self ): return self._value
    
    def SetOperator( self, operator ):
        
        if self._predicate_type == PREDICATE_TYPE_TAG:
            
            ( old_operator, tag ) = self._value
            
            self._value = ( operator, tag )
            
        
    
SYSTEM_PREDICATE_INBOX = Predicate( PREDICATE_TYPE_SYSTEM, ( SYSTEM_PREDICATE_TYPE_INBOX, None ) )
SYSTEM_PREDICATE_ARCHIVE = Predicate( PREDICATE_TYPE_SYSTEM, ( SYSTEM_PREDICATE_TYPE_ARCHIVE, None ) )
SYSTEM_PREDICATE_LOCAL = Predicate( PREDICATE_TYPE_SYSTEM, ( SYSTEM_PREDICATE_TYPE_LOCAL, None ) )
SYSTEM_PREDICATE_NOT_LOCAL = Predicate( PREDICATE_TYPE_SYSTEM, ( SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None ) )

class ResponseContext():
    
    def __init__( self, status_code, mime = APPLICATION_YAML, body = None, path = None, is_yaml = False, cookies = [] ):
        
        self._status_code = status_code
        self._mime = mime
        self._body = body
        self._path = path
        self._is_yaml = is_yaml
        self._cookies = cookies
        
    
    def GetCookies( self ): return self._cookies
    
    def GetLength( self ): return len( self._body )
    
    def GetMimeBody( self ): return ( self._mime, self._body )
    
    def GetPath( self ): return self._path
    
    def GetStatusCode( self ): return self._status_code
    
    def HasBody( self ): return self._body is not None
    
    def HasPath( self ): return self._path is not None
    
    def IsYAML( self ): return self._is_yaml
    
class ServerServiceIdentifier( HydrusYAMLBase ):
    
    yaml_tag = u'!ServerServiceIdentifier'
    
    def __init__( self, service_key, type ):
        
        HydrusYAMLBase.__init__( self )
        
        self._service_key = service_key
        self._type = type
        
    
    def __eq__( self, other ): return self.__hash__() == other.__hash__()
    
    def __hash__( self ): return self._service_key.__hash__()
    
    def __ne__( self, other ): return self.__hash__() != other.__hash__()
    
    def __repr__( self ): return 'Server Service Identifier: ' + service_string_lookup[ self._type ]
    
    def GetServiceKey( self ): return self._service_key
    
    def GetType( self ): return self._type
    
SERVER_ADMIN_IDENTIFIER = ServerServiceIdentifier( 'server admin', SERVER_ADMIN )

class ServiceUpdate():
    
    def __init__( self, action, row = None ):
        
        self._action = action
        self._row = row
        
    
    def ToTuple( self ): return ( self._action, self._row )
        
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
        
        if self._petition_type == CONTENT_DATA_TYPE_FILES: hashes = self._petition_data
        elif self._petition_type == CONTENT_DATA_TYPE_MAPPINGS: ( tag, hashes ) = self._petition_data
        else: hashes = set()
        
        hash_ids_to_hashes = dict( enumerate( hashes ) )
        
        hash_ids = hash_ids_to_hashes.keys()
        
        content_data = GetEmptyDataDict()
        
        if self._petition_type == CONTENT_DATA_TYPE_FILES: row = ( hash_ids, reason )
        elif self._petition_type == CONTENT_DATA_TYPE_MAPPINGS: row = ( tag, hash_ids, reason )
        else:
            
            ( old, new ) = self._petition_data
            
            row = ( ( old, new ), reason )
            
        
        content_data[ self._petition_type ][ self._action ].append( row )
        
        return ClientToServerUpdate( content_data, hash_ids_to_hashes )
        
    
    def GetDenial( self ):
        
        if self._petition_type == CONTENT_DATA_TYPE_FILES: hashes = self._petition_data
        elif self._petition_type == CONTENT_DATA_TYPE_MAPPINGS: ( tag, hashes ) = self._petition_data
        else: hashes = set()
        
        hash_ids_to_hashes = dict( enumerate( hashes ) )
        
        hash_ids = hash_ids_to_hashes.keys()
        
        if self._petition_type == CONTENT_DATA_TYPE_FILES: row_list = hash_ids
        elif self._petition_type == CONTENT_DATA_TYPE_MAPPINGS: row_list = [ ( tag, hash_ids ) ]
        else: row_list = [ self._petition_data ]
        
        content_data = GetEmptyDataDict()
        
        if self._action == CONTENT_UPDATE_PENDING: denial_action = CONTENT_UPDATE_DENY_PEND
        elif self._action == CONTENT_UPDATE_PETITION: denial_action = CONTENT_UPDATE_DENY_PETITION
        
        content_data[ self._petition_type ][ denial_action ] = row_list
        
        return ClientToServerUpdate( content_data, hash_ids_to_hashes )
        
    
    def GetHashes( self ):
        
        if self._petition_type == CONTENT_DATA_TYPE_FILES: hashes = self._petition_data
        elif self._petition_type == CONTENT_DATA_TYPE_MAPPINGS: ( tag, hashes ) = self._petition_data
        else: hashes = set()
        
        return hashes
        
    
    def GetPetitionerIdentifier( self ): return self._petitioner_account_identifier
    
    def GetPetitionString( self ):
        
        if self._action == CONTENT_UPDATE_PENDING: action_word = 'Add '
        elif self._action == CONTENT_UPDATE_PETITION: action_word = 'Remove '
        
        if self._petition_type == CONTENT_DATA_TYPE_FILES:
            
            hashes = self._petition_data
            
            content_phrase = ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
        elif self._petition_type == CONTENT_DATA_TYPE_MAPPINGS:
            
            ( tag, hashes ) = self._petition_data
            
            content_phrase = tag + ' for ' + ConvertIntToPrettyString( len( hashes ) ) + ' files'
            
        elif self._petition_type == CONTENT_DATA_TYPE_TAG_SIBLINGS:
            
            ( old_tag, new_tag ) = self._petition_data
            
            content_phrase = ' sibling ' + old_tag + '->' + new_tag
            
        elif self._petition_type == CONTENT_DATA_TYPE_TAG_PARENTS:
            
            ( old_tag, new_tag ) = self._petition_data
            
            content_phrase = ' parent ' + old_tag + '->' + new_tag
            
        
        return action_word + content_phrase + os.linesep + os.linesep + self._reason
        
    
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
        
        ( begin, end ) = self._service_data[ SERVICE_UPDATE_BEGIN_END ]
        
        return ( begin, end )
        
    
    def GetContentDataIterator( self, data_type, action ):
        
        if data_type not in self._content_data or action not in self._content_data[ data_type ]: return ()
        
        data = self._content_data[ data_type ][ action ]
        
        if data_type == CONTENT_DATA_TYPE_FILES:
            
            if action == CONTENT_UPDATE_ADD: return ( ( self._hash_ids_to_hashes[ hash_id ], size, mime, timestamp, width, height, duration, num_frames, num_words ) for ( hash_id, size, mime, timestamp, width, height, duration, num_frames, num_words ) in data )
            else: return ( { self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids } for hash_ids in ( data, ) )
            
        elif data_type == CONTENT_DATA_TYPE_MAPPINGS: return ( ( tag, [ self._hash_ids_to_hashes[ hash_id ] for hash_id in hash_ids ] ) for ( tag, hash_ids ) in data )
        else: return data.__iter__()
        
    
    def GetNumContentUpdates( self ):
        
        num = 0
        
        data_types = [ CONTENT_DATA_TYPE_FILES, CONTENT_DATA_TYPE_MAPPINGS, CONTENT_DATA_TYPE_TAG_SIBLINGS, CONTENT_DATA_TYPE_TAG_PARENTS ]
        actions = [ CONTENT_UPDATE_ADD, CONTENT_UPDATE_DELETE ]
        
        for ( data_type, action ) in itertools.product( data_types, actions ):
            
            for row in self.GetContentDataIterator( data_type, action ): num += 1
            
        
        return num
        
    
    # this needs work!
    # we need a universal content_update for both client and server
    def IterateContentUpdates( self ):
        
        data_types = [ CONTENT_DATA_TYPE_FILES, CONTENT_DATA_TYPE_MAPPINGS, CONTENT_DATA_TYPE_TAG_SIBLINGS, CONTENT_DATA_TYPE_TAG_PARENTS ]
        actions = [ CONTENT_UPDATE_ADD, CONTENT_UPDATE_DELETE ]
        
        for ( data_type, action ) in itertools.product( data_types, actions ):
            
            for row in self.GetContentDataIterator( data_type, action ): yield ContentUpdate( data_type, action, row )
            
        
    
    def IterateServiceUpdates( self ):
        
        service_types = [ SERVICE_UPDATE_NEWS ]
        
        for service_type in service_types:
            
            if service_type in self._service_data:
                
                data = self._service_data[ service_type ]
                
                yield ServiceUpdate( service_type, data )
                
            
        
    
    def GetHashes( self ): return set( hash_ids_to_hashes.values() )
    
    def GetTags( self ):
        
        tags = set()
        
        tags.update( ( tag for ( tag, hash_ids ) in self.GetContentDataIterator( CONTENT_DATA_TYPE_MAPPINGS, CURRENT ) ) )
        tags.update( ( tag for ( tag, hash_ids ) in self.GetContentDataIterator( CONTENT_DATA_TYPE_MAPPINGS, DELETED ) ) )
        
        tags.update( ( old_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( CONTENT_DATA_TYPE_TAG_SIBLINGS, CURRENT ) ) )
        tags.update( ( new_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( CONTENT_DATA_TYPE_TAG_SIBLINGS, CURRENT ) ) )
        tags.update( ( old_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( CONTENT_DATA_TYPE_TAG_SIBLINGS, DELETED ) ) )
        tags.update( ( new_tag for ( old_tag, new_tag ) in self.GetContentDataIterator( CONTENT_DATA_TYPE_TAG_SIBLINGS, DELETED ) ) )
        
        return tags
        
    
    def GetServiceData( self, service_type ): return self._service_data[ service_type ]
    
class SortedList():
    
    def __init__( self, initial_items = [], sort_function = None ):
        
        do_sort = sort_function is not None
        
        if sort_function is None: sort_function = lambda x: x
        
        self._sorted_list = [ ( sort_function( item ), item ) for item in initial_items ]
        
        self._items_to_indices = None
        
        self._sort_function = sort_function
        
        if do_sort: self.sort()
        
    
    def __contains__( self, item ): return self._items_to_indices.__contains__( item )
    
    def __getitem__( self, value ):
        
        if type( value ) == int: return self._sorted_list.__getitem__( value )[1]
        elif type( value ) == slice: return [ item for ( sort_item, item ) in self._sorted_list.__getitem__( value ) ]
        
    
    def __iter__( self ):
        
        for ( sorting_value, item ) in self._sorted_list: yield item
        
    
    def __len__( self ): return self._sorted_list.__len__()
    
    def _DirtyIndices( self ): self._items_to_indices = None
    
    def _RecalcIndices( self ): self._items_to_indices = { item : index for ( index, ( sort_item, item ) ) in enumerate( self._sorted_list ) }
    
    def append_items( self, items ):
        
        self._sorted_list.extend( [ ( self._sort_function( item ), item ) for item in items ] )
        
        self._DirtyIndices()
        
    
    def index( self, item ):
        
        if self._items_to_indices is None: self._RecalcIndices()
        
        return self._items_to_indices[ item ]
        
    
    def insert_items( self, items ):
        
        for item in items: bisect.insort( self._sorted_list, ( self._sort_function( item ), item ) )
        
        self._DirtyIndices()
        
    
    def remove_items( self, items ):
        
        deletee_indices = [ self.index( item ) for item in items ]
        
        deletee_indices.sort()
        
        deletee_indices.reverse()
        
        for index in deletee_indices: self._sorted_list.pop( index )
        
        self._DirtyIndices()
        
    
    def sort( self, f = None ):
        
        if f is not None: self._sort_function = f
        
        self._sorted_list = [ ( self._sort_function( item ), item ) for ( old_value, item ) in self._sorted_list ]
        
        self._sorted_list.sort()
        
        self._DirtyIndices()
        

# adding tuple to yaml

def construct_python_tuple( self, node ): return tuple( self.construct_sequence( node ) )
def represent_python_tuple( self, data ): return self.represent_sequence( u'tag:yaml.org,2002:python/tuple', data )

yaml.SafeLoader.add_constructor( u'tag:yaml.org,2002:python/tuple', construct_python_tuple )
yaml.SafeDumper.add_representer( tuple, represent_python_tuple )

# for some reason, sqlite doesn't parse to int before this, despite the column affinity
# it gives the register_converter function a bytestring :/
def integer_boolean_to_bool( integer_boolean ): return bool( int( integer_boolean ) )

# sqlite mod

sqlite3.register_adapter( dict, yaml.safe_dump )
sqlite3.register_adapter( list, yaml.safe_dump )
sqlite3.register_adapter( tuple, yaml.safe_dump )
sqlite3.register_adapter( bool, int )
# no longer needed since adding tuple? do yaml objects somehow cast to __tuple__?
sqlite3.register_adapter( Account, yaml.safe_dump )
sqlite3.register_adapter( AccountType, yaml.safe_dump )
sqlite3.register_adapter( ServerToClientUpdate, yaml.safe_dump )

sqlite3.register_converter( 'BLOB_BYTES', str )
sqlite3.register_converter( 'INTEGER_BOOLEAN', integer_boolean_to_bool )
sqlite3.register_converter( 'TEXT_YAML', yaml.safe_load )