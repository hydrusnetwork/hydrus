import os
import sys

# dirs

BASE_DIR = sys.path[0]

if BASE_DIR == '':
    
    BASE_DIR = os.getcwdu()
    
else:
    
    try:
        
        BASE_DIR = BASE_DIR.decode( 'utf-8' )
        
    except:
        
        pass
        
    
BIN_DIR = os.path.join( BASE_DIR, 'bin' )
HELP_DIR = os.path.join( BASE_DIR, 'help' )
INCLUDE_DIR = os.path.join( BASE_DIR, 'include' )
STATIC_DIR = os.path.join( BASE_DIR, 'static' )

DEFAULT_DB_DIR = os.path.join( BASE_DIR, 'db' )
LICENSE_PATH = os.path.join( BASE_DIR, 'license.txt' )

#

PLATFORM_WINDOWS = False
PLATFORM_OSX  = False
PLATFORM_LINUX = False

if sys.platform == 'win32': PLATFORM_WINDOWS = True
elif sys.platform == 'darwin': PLATFORM_OSX = True
elif sys.platform == 'linux2': PLATFORM_LINUX = True

RUNNING_FROM_SOURCE = sys.argv[0].endswith( '.py' ) or sys.argv[0].endswith( '.pyw' )

import sqlite3
import traceback
import yaml

options = {}

# Misc

NETWORK_VERSION = 18
SOFTWARE_VERSION = 249

UNSCALED_THUMBNAIL_DIMENSIONS = ( 200, 200 )

HYDRUS_KEY_LENGTH = 32

UPDATE_DURATION = 100000
READ_BLOCK_SIZE = 256 * 1024

lifetimes = [ ( 'one month', 31 * 86400 ), ( 'three months', 3 * 31 * 86400 ), ( 'six months', 6 * 31 * 86400 ), ( 'one year', 12 * 31 * 86400 ), ( 'two years', 24 * 31 * 86400 ), ( 'five years', 60 * 31 * 86400 ), ( 'does not expire', None ) ]

# Enums

BANDWIDTH_TYPE_DATA = 0
BANDWIDTH_TYPE_REQUESTS = 1

bandwidth_type_string_lookup = {}

bandwidth_type_string_lookup[ BANDWIDTH_TYPE_DATA ] = 'data'
bandwidth_type_string_lookup[ BANDWIDTH_TYPE_REQUESTS ] = 'requests'

CONTENT_MERGE_ACTION_DO_NOTHING = 0
CONTENT_MERGE_ACTION_COPY = 1
CONTENT_MERGE_ACTION_MOVE = 2
CONTENT_MERGE_ACTION_UNION = 3

CONTENT_STATUS_CURRENT = 0
CONTENT_STATUS_PENDING = 1
CONTENT_STATUS_DELETED = 2
CONTENT_STATUS_PETITIONED = 3

content_status_string_lookup = {}

content_status_string_lookup[ CONTENT_STATUS_CURRENT ] = 'current'
content_status_string_lookup[ CONTENT_STATUS_PENDING ] = 'pending'
content_status_string_lookup[ CONTENT_STATUS_DELETED ] = 'deleted'
content_status_string_lookup[ CONTENT_STATUS_PETITIONED ] = 'petitioned'

CONTENT_TYPE_MAPPINGS = 0
CONTENT_TYPE_TAG_SIBLINGS = 1
CONTENT_TYPE_TAG_PARENTS = 2
CONTENT_TYPE_FILES = 3
CONTENT_TYPE_RATINGS = 4
CONTENT_TYPE_MAPPING = 5
CONTENT_TYPE_DIRECTORIES = 6
CONTENT_TYPE_URLS = 7
CONTENT_TYPE_VETO = 8
CONTENT_TYPE_ACCOUNTS = 9
CONTENT_TYPE_OPTIONS = 10
CONTENT_TYPE_SERVICES = 11
CONTENT_TYPE_UNKNOWN = 12
CONTENT_TYPE_ACCOUNT_TYPES = 13

content_type_string_lookup = {}

content_type_string_lookup[ CONTENT_TYPE_MAPPINGS ] = 'mappings'
content_type_string_lookup[ CONTENT_TYPE_TAG_SIBLINGS ] = 'tag siblings'
content_type_string_lookup[ CONTENT_TYPE_TAG_PARENTS ] = 'tag parents'
content_type_string_lookup[ CONTENT_TYPE_FILES ] = 'files'
content_type_string_lookup[ CONTENT_TYPE_RATINGS ] = 'ratings'
content_type_string_lookup[ CONTENT_TYPE_MAPPING ] = 'mapping'
content_type_string_lookup[ CONTENT_TYPE_DIRECTORIES ] = 'directories'
content_type_string_lookup[ CONTENT_TYPE_URLS ] = 'urls'
content_type_string_lookup[ CONTENT_TYPE_VETO ] = 'veto'
content_type_string_lookup[ CONTENT_TYPE_ACCOUNTS ] = 'accounts'
content_type_string_lookup[ CONTENT_TYPE_OPTIONS ] = 'options'
content_type_string_lookup[ CONTENT_TYPE_SERVICES ] = 'services'
content_type_string_lookup[ CONTENT_TYPE_UNKNOWN ] = 'unknown'
content_type_string_lookup[ CONTENT_TYPE_ACCOUNT_TYPES ] = 'account types'

REPOSITORY_CONTENT_TYPES = [ CONTENT_TYPE_FILES, CONTENT_TYPE_MAPPINGS, CONTENT_TYPE_TAG_PARENTS, CONTENT_TYPE_TAG_SIBLINGS ]

CONTENT_UPDATE_ADD = 0
CONTENT_UPDATE_DELETE = 1
CONTENT_UPDATE_PEND = 2
CONTENT_UPDATE_RESCIND_PEND = 3
CONTENT_UPDATE_PETITION = 4
CONTENT_UPDATE_RESCIND_PETITION = 5
CONTENT_UPDATE_EDIT_LOG = 6
CONTENT_UPDATE_ARCHIVE = 7
CONTENT_UPDATE_INBOX = 8
CONTENT_UPDATE_RATING = 9
CONTENT_UPDATE_DENY_PEND = 11
CONTENT_UPDATE_DENY_PETITION = 12
CONTENT_UPDATE_ADVANCED = 13
CONTENT_UPDATE_UNDELETE = 14

content_update_string_lookup = {}

content_update_string_lookup[ CONTENT_UPDATE_ADD ] = 'add'
content_update_string_lookup[ CONTENT_UPDATE_DELETE ] = 'delete'
content_update_string_lookup[ CONTENT_UPDATE_PEND ] = 'pending'
content_update_string_lookup[ CONTENT_UPDATE_RESCIND_PEND ] = 'rescind pending'
content_update_string_lookup[ CONTENT_UPDATE_PETITION ] = 'petition'
content_update_string_lookup[ CONTENT_UPDATE_RESCIND_PETITION ] = 'rescind petition'
content_update_string_lookup[ CONTENT_UPDATE_EDIT_LOG ] = 'edit log'
content_update_string_lookup[ CONTENT_UPDATE_ARCHIVE ] = 'archive'
content_update_string_lookup[ CONTENT_UPDATE_INBOX ] = 'inbox'
content_update_string_lookup[ CONTENT_UPDATE_RATING ] = 'rating'
content_update_string_lookup[ CONTENT_UPDATE_DENY_PEND ] = 'deny pend'
content_update_string_lookup[ CONTENT_UPDATE_DENY_PETITION ] = 'deny petition'
content_update_string_lookup[ CONTENT_UPDATE_UNDELETE ] = 'undelete'

DEFINITIONS_TYPE_HASHES = 0
DEFINITIONS_TYPE_TAGS = 1

DUPLICATE_UNKNOWN = 0
DUPLICATE_NOT_DUPLICATE = 1
DUPLICATE_SAME_FILE = 2
DUPLICATE_ALTERNATE = 3

ENCODING_RAW = 0
ENCODING_HEX = 1
ENCODING_BASE64 = 2

encoding_string_lookup = {}

encoding_string_lookup[ ENCODING_RAW ] = 'raw bytes'
encoding_string_lookup[ ENCODING_HEX ] = 'hexadecimal'
encoding_string_lookup[ ENCODING_BASE64 ] = 'base64'

IMPORT_FOLDER_TYPE_DELETE = 0
IMPORT_FOLDER_TYPE_SYNCHRONISE = 1

EXPORT_FOLDER_TYPE_REGULAR = 0
EXPORT_FOLDER_TYPE_SYNCHRONISE = 1

HAMMING_EXACT_MATCH = 0
HAMMING_VERY_SIMILAR = 2
HAMMING_SIMILAR = 4
HAMMING_SPECULATIVE = 8

hamming_string_lookup = {}

hamming_string_lookup[ HAMMING_EXACT_MATCH ] = 'exact match'
hamming_string_lookup[ HAMMING_VERY_SIMILAR ] = 'very similar'
hamming_string_lookup[ HAMMING_SIMILAR ] = 'similar'
hamming_string_lookup[ HAMMING_SPECULATIVE ] = 'speculative'

HYDRUS_CLIENT = 0
HYDRUS_SERVER = 1
HYDRUS_TEST = 2

GET_DATA = 0
POST_DATA = 1
POST_PETITIONS = 2
RESOLVE_PETITIONS = 3
MANAGE_USERS = 4
GENERAL_ADMIN = 5
EDIT_SERVICES = 6
UNKNOWN_PERMISSION = 7

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
permissions_string_lookup[ UNKNOWN_PERMISSION ] = 'unknown'

# new permissions

PERMISSION_ACTION_PETITION = 0
PERMISSION_ACTION_CREATE = 1
PERMISSION_ACTION_OVERRULE = 2

permission_pair_string_lookup = {}

permission_pair_string_lookup[ ( CONTENT_TYPE_ACCOUNTS, None ) ] = 'cannot change accounts'
permission_pair_string_lookup[ ( CONTENT_TYPE_ACCOUNTS, PERMISSION_ACTION_CREATE ) ] = 'can create accounts'
permission_pair_string_lookup[ ( CONTENT_TYPE_ACCOUNTS, PERMISSION_ACTION_OVERRULE ) ] = 'can manage accounts completely'

permission_pair_string_lookup[ ( CONTENT_TYPE_ACCOUNT_TYPES, None ) ] = 'cannot change account types'
permission_pair_string_lookup[ ( CONTENT_TYPE_ACCOUNT_TYPES, PERMISSION_ACTION_OVERRULE ) ] = 'can manage account types completely'

permission_pair_string_lookup[ ( CONTENT_TYPE_SERVICES, None ) ] = 'cannot change services'
permission_pair_string_lookup[ ( CONTENT_TYPE_SERVICES, PERMISSION_ACTION_OVERRULE ) ] = 'can manage services completely'

permission_pair_string_lookup[ ( CONTENT_TYPE_FILES, None ) ] = 'can only download files'
permission_pair_string_lookup[ ( CONTENT_TYPE_FILES, PERMISSION_ACTION_PETITION ) ] = 'can petition to remove existing files'
permission_pair_string_lookup[ ( CONTENT_TYPE_FILES, PERMISSION_ACTION_CREATE ) ] = 'can upload new files and petition existing ones'
permission_pair_string_lookup[ ( CONTENT_TYPE_FILES, PERMISSION_ACTION_OVERRULE ) ] = 'can upload and delete files and process petitions'

permission_pair_string_lookup[ ( CONTENT_TYPE_MAPPINGS, None ) ] = 'can only download mappings'
permission_pair_string_lookup[ ( CONTENT_TYPE_MAPPINGS, PERMISSION_ACTION_PETITION ) ] = 'can petition to remove existing mappings'
permission_pair_string_lookup[ ( CONTENT_TYPE_MAPPINGS, PERMISSION_ACTION_CREATE ) ] = 'can upload new mappings and petition existing ones'
permission_pair_string_lookup[ ( CONTENT_TYPE_MAPPINGS, PERMISSION_ACTION_OVERRULE ) ] = 'can upload and delete mappings and process petitions'

permission_pair_string_lookup[ ( CONTENT_TYPE_TAG_PARENTS, None ) ] = 'can only download tag parents'
permission_pair_string_lookup[ ( CONTENT_TYPE_TAG_PARENTS, PERMISSION_ACTION_PETITION ) ] = 'can petition to add or remove tag parents'
permission_pair_string_lookup[ ( CONTENT_TYPE_TAG_PARENTS, PERMISSION_ACTION_OVERRULE ) ] = 'can upload and delete tag parents and process petitions'

permission_pair_string_lookup[ ( CONTENT_TYPE_TAG_SIBLINGS, None ) ] = 'can only download tag siblings'
permission_pair_string_lookup[ ( CONTENT_TYPE_TAG_SIBLINGS, PERMISSION_ACTION_PETITION ) ] = 'can petition to add or remove tag siblings'
permission_pair_string_lookup[ ( CONTENT_TYPE_TAG_SIBLINGS, PERMISSION_ACTION_OVERRULE ) ] = 'can upload and delete tag siblings and process petitions'

TAG_REPOSITORY = 0
FILE_REPOSITORY = 1
LOCAL_FILE_DOMAIN = 2
MESSAGE_DEPOT = 3
LOCAL_TAG = 5
LOCAL_RATING_NUMERICAL = 6
LOCAL_RATING_LIKE = 7
RATING_NUMERICAL_REPOSITORY = 8
RATING_LIKE_REPOSITORY = 9
COMBINED_TAG = 10
COMBINED_FILE = 11
LOCAL_BOORU = 12
IPFS = 13
LOCAL_FILE_TRASH_DOMAIN = 14
COMBINED_LOCAL_FILE = 15
SERVER_ADMIN = 99
NULL_SERVICE = 100

service_string_lookup = {}

service_string_lookup[ TAG_REPOSITORY ] = 'hydrus tag repository'
service_string_lookup[ FILE_REPOSITORY ] = 'hydrus file repository'
service_string_lookup[ LOCAL_FILE_DOMAIN ] = 'local file domain'
service_string_lookup[ LOCAL_FILE_TRASH_DOMAIN ] = 'local trash file domain'
service_string_lookup[ COMBINED_LOCAL_FILE ] = 'virtual combined local file service'
service_string_lookup[ MESSAGE_DEPOT ] = 'hydrus message depot'
service_string_lookup[ LOCAL_TAG ] = 'local tag service'
service_string_lookup[ LOCAL_RATING_NUMERICAL ] = 'local numerical rating service'
service_string_lookup[ LOCAL_RATING_LIKE ] = 'local like/dislike rating service'
service_string_lookup[ RATING_NUMERICAL_REPOSITORY ] = 'hydrus numerical rating repository'
service_string_lookup[ RATING_LIKE_REPOSITORY ] = 'hydrus like/dislike rating repository'
service_string_lookup[ COMBINED_TAG ] = 'virtual combined tag service'
service_string_lookup[ COMBINED_FILE ] = 'virtual combined file service'
service_string_lookup[ LOCAL_BOORU ] = 'hydrus local booru'
service_string_lookup[ IPFS ] = 'ipfs daemon'
service_string_lookup[ SERVER_ADMIN ] = 'hydrus server administration service'
service_string_lookup[ NULL_SERVICE ] = 'null service'

LOCAL_FILE_SERVICES = ( LOCAL_FILE_DOMAIN, LOCAL_FILE_TRASH_DOMAIN, COMBINED_LOCAL_FILE )
LOCAL_TAG_SERVICES = ( LOCAL_TAG, )

LOCAL_SERVICES = LOCAL_FILE_SERVICES + LOCAL_TAG_SERVICES + ( LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, LOCAL_BOORU )

RATINGS_SERVICES = ( LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY )
REPOSITORIES = ( TAG_REPOSITORY, FILE_REPOSITORY, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY )
RESTRICTED_SERVICES = REPOSITORIES + ( SERVER_ADMIN, MESSAGE_DEPOT )
REMOTE_SERVICES = RESTRICTED_SERVICES + ( IPFS, )
FILE_SERVICES = LOCAL_FILE_SERVICES + ( FILE_REPOSITORY, IPFS )
TAG_SERVICES = ( LOCAL_TAG, TAG_REPOSITORY )
ADDREMOVABLE_SERVICES = ( LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, FILE_REPOSITORY, TAG_REPOSITORY, SERVER_ADMIN, IPFS )
NONEDITABLE_SERVICES = ( LOCAL_FILE_DOMAIN, LOCAL_FILE_TRASH_DOMAIN, LOCAL_TAG, COMBINED_FILE, COMBINED_TAG, COMBINED_LOCAL_FILE )
AUTOCOMPLETE_CACHE_SPECIFIC_FILE_SERVICES = ( LOCAL_FILE_DOMAIN, LOCAL_FILE_TRASH_DOMAIN, COMBINED_LOCAL_FILE, FILE_REPOSITORY )
ALL_SERVICES = REMOTE_SERVICES + LOCAL_SERVICES + ( COMBINED_FILE, COMBINED_TAG )

SERVICES_WITH_THUMBNAILS = [ FILE_REPOSITORY, LOCAL_FILE_DOMAIN ]

DELETE_FILES_PETITION = 0
DELETE_TAG_PETITION = 1

BAN = 0
SUPERBAN = 1
CHANGE_ACCOUNT_TYPE = 2
ADD_TO_EXPIRES = 3
SET_EXPIRES = 4

HIGH_PRIORITY = 0
LOW_PRIORITY = 2
INTERRUPTABLE_PRIORITY = 4

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
SERVICE_INFO_NUM_VIEWABLE_FILES = 22

SERVICE_UPDATE_DELETE_PENDING = 0
SERVICE_UPDATE_RESET = 1

ADD = 0
DELETE = 1
EDIT = 2
SET = 3

APPROVE = 0
DENY = 1

GET = 0
POST = 1
OPTIONS = 2

query_type_string_lookup = {}

query_type_string_lookup[ GET ] = 'GET'
query_type_string_lookup[ POST ] = 'POST'
query_type_string_lookup[ OPTIONS ] = 'OPTIONS'

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
APPLICATION_JSON = 22
VIDEO_APNG = 23
UNDETERMINED_PNG = 24
VIDEO_MPEG = 25
VIDEO_MOV = 26
VIDEO_AVI = 27
APPLICATION_HYDRUS_UPDATE_DEFINITIONS = 28
APPLICATION_HYDRUS_UPDATE_CONTENT = 29
APPLICATION_OCTET_STREAM = 100
APPLICATION_UNKNOWN = 101

ALLOWED_MIMES = ( IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_BMP, APPLICATION_FLASH, VIDEO_AVI, VIDEO_FLV, VIDEO_MOV, VIDEO_MP4, VIDEO_MKV, VIDEO_WEBM, VIDEO_MPEG, APPLICATION_PDF, AUDIO_MP3, AUDIO_OGG, AUDIO_FLAC, AUDIO_WMA, VIDEO_WMV, APPLICATION_HYDRUS_UPDATE_CONTENT, APPLICATION_HYDRUS_UPDATE_DEFINITIONS )
SEARCHABLE_MIMES = ( IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, APPLICATION_FLASH, VIDEO_AVI, VIDEO_FLV, VIDEO_MOV, VIDEO_MP4, VIDEO_MKV, VIDEO_WEBM, VIDEO_MPEG, APPLICATION_PDF, AUDIO_MP3, AUDIO_OGG, AUDIO_FLAC, AUDIO_WMA, VIDEO_WMV )

IMAGES = ( IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_BMP )

AUDIO = ( AUDIO_MP3, AUDIO_OGG, AUDIO_FLAC, AUDIO_WMA )

VIDEO = ( VIDEO_AVI, VIDEO_FLV, VIDEO_MOV, VIDEO_MP4, VIDEO_WMV, VIDEO_MKV, VIDEO_WEBM, VIDEO_MPEG )

NATIVE_VIDEO = ( VIDEO_AVI, VIDEO_FLV, VIDEO_MOV, VIDEO_MP4, VIDEO_WMV, VIDEO_MKV, VIDEO_WEBM, VIDEO_MPEG )

APPLICATIONS = ( APPLICATION_FLASH, APPLICATION_PDF, APPLICATION_ZIP )

NOISY_MIMES = tuple( [ APPLICATION_FLASH ] + list( AUDIO ) + list( VIDEO ) )

ARCHIVES = ( APPLICATION_ZIP, APPLICATION_HYDRUS_ENCRYPTED_ZIP )

MIMES_WITH_THUMBNAILS = ( APPLICATION_FLASH, IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_BMP, VIDEO_AVI, VIDEO_FLV, VIDEO_MOV, VIDEO_MP4, VIDEO_WMV, VIDEO_MKV, VIDEO_WEBM, VIDEO_MPEG )

MIMES_WE_CAN_PHASH = ( IMAGE_JPEG, IMAGE_PNG )

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
mime_enum_lookup[ 'application/json' ] = APPLICATION_JSON
mime_enum_lookup[ 'application/hydrus-encrypted-zip' ] = APPLICATION_HYDRUS_ENCRYPTED_ZIP
mime_enum_lookup[ 'application/hydrus-update-content' ] = APPLICATION_HYDRUS_UPDATE_CONTENT
mime_enum_lookup[ 'application/hydrus-update-definitions' ] = APPLICATION_HYDRUS_UPDATE_DEFINITIONS
mime_enum_lookup[ 'application' ] = APPLICATIONS
mime_enum_lookup[ 'audio/mp3' ] = AUDIO_MP3
mime_enum_lookup[ 'audio/ogg' ] = AUDIO_OGG
mime_enum_lookup[ 'audio/flac' ] = AUDIO_FLAC
mime_enum_lookup[ 'audio/x-ms-wma' ] = AUDIO_WMA
mime_enum_lookup[ 'text/html' ] = TEXT_HTML
mime_enum_lookup[ 'video/png' ] = VIDEO_APNG
mime_enum_lookup[ 'video/x-msvideo' ] = VIDEO_AVI
mime_enum_lookup[ 'video/x-flv' ] = VIDEO_FLV
mime_enum_lookup[ 'video/quicktime' ] = VIDEO_MOV
mime_enum_lookup[ 'video/mp4' ] = VIDEO_MP4
mime_enum_lookup[ 'video/mpeg' ] = VIDEO_MPEG
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
mime_string_lookup[ APPLICATION_JSON ] = 'application/json'
mime_string_lookup[ APPLICATION_PDF ] = 'application/pdf'
mime_string_lookup[ APPLICATION_ZIP ] = 'application/zip'
mime_string_lookup[ APPLICATION_HYDRUS_ENCRYPTED_ZIP ] = 'application/hydrus-encrypted-zip'
mime_string_lookup[ APPLICATION_HYDRUS_UPDATE_CONTENT ] = 'application/hydrus-update-content'
mime_string_lookup[ APPLICATION_HYDRUS_UPDATE_DEFINITIONS ] = 'application/hydrus-update-definitions'
mime_string_lookup[ APPLICATIONS ] = 'application'
mime_string_lookup[ AUDIO_MP3 ] = 'audio/mp3'
mime_string_lookup[ AUDIO_OGG ] = 'audio/ogg'
mime_string_lookup[ AUDIO_FLAC ] = 'audio/flac'
mime_string_lookup[ AUDIO_WMA ] = 'audio/x-ms-wma'
mime_string_lookup[ AUDIO ] = 'audio'
mime_string_lookup[ TEXT_HTML ] = 'text/html'
mime_string_lookup[ VIDEO_APNG ] = 'video/png'
mime_string_lookup[ VIDEO_AVI ] = 'video/x-msvideo'
mime_string_lookup[ VIDEO_FLV ] = 'video/x-flv'
mime_string_lookup[ VIDEO_MOV ] = 'video/quicktime'
mime_string_lookup[ VIDEO_MP4 ] = 'video/mp4'
mime_string_lookup[ VIDEO_MPEG ] = 'video/mpeg'
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
mime_ext_lookup[ APPLICATION_JSON ] = '.json'
mime_ext_lookup[ APPLICATION_PDF ] = '.pdf'
mime_ext_lookup[ APPLICATION_ZIP ] = '.zip'
mime_ext_lookup[ APPLICATION_HYDRUS_ENCRYPTED_ZIP ] = '.zip.encrypted'
mime_ext_lookup[ APPLICATION_HYDRUS_UPDATE_CONTENT ] = ''
mime_ext_lookup[ APPLICATION_HYDRUS_UPDATE_DEFINITIONS ] = ''
mime_ext_lookup[ AUDIO_MP3 ] = '.mp3'
mime_ext_lookup[ AUDIO_OGG ] = '.ogg'
mime_ext_lookup[ AUDIO_FLAC ] = '.flac'
mime_ext_lookup[ AUDIO_WMA ] = '.wma'
mime_ext_lookup[ TEXT_HTML ] = '.html'
mime_ext_lookup[ VIDEO_APNG ] = '.png'
mime_ext_lookup[ VIDEO_AVI ] = '.avi'
mime_ext_lookup[ VIDEO_FLV ] = '.flv'
mime_ext_lookup[ VIDEO_MOV ] = '.mov'
mime_ext_lookup[ VIDEO_MP4 ] = '.mp4'
mime_ext_lookup[ VIDEO_MPEG ] = '.mpeg'
mime_ext_lookup[ VIDEO_WMV ] = '.wmv'
mime_ext_lookup[ VIDEO_MKV ] = '.mkv'
mime_ext_lookup[ VIDEO_WEBM ] = '.webm'
mime_ext_lookup[ APPLICATION_UNKNOWN ] = ''
#mime_ext_lookup[ 'application/x-rar-compressed' ] = '.rar'

ALLOWED_MIME_EXTENSIONS = [ mime_ext_lookup[ mime ] for mime in ALLOWED_MIMES ]

PREDICATE_TYPE_TAG = 0
PREDICATE_TYPE_NAMESPACE = 1
PREDICATE_TYPE_PARENT = 2
PREDICATE_TYPE_WILDCARD = 3
PREDICATE_TYPE_SYSTEM_EVERYTHING = 4
PREDICATE_TYPE_SYSTEM_INBOX = 5
PREDICATE_TYPE_SYSTEM_ARCHIVE = 6
PREDICATE_TYPE_SYSTEM_UNTAGGED = 7
PREDICATE_TYPE_SYSTEM_NUM_TAGS = 8
PREDICATE_TYPE_SYSTEM_LIMIT = 9
PREDICATE_TYPE_SYSTEM_SIZE = 10
PREDICATE_TYPE_SYSTEM_AGE = 11
PREDICATE_TYPE_SYSTEM_HASH = 12
PREDICATE_TYPE_SYSTEM_WIDTH = 13
PREDICATE_TYPE_SYSTEM_HEIGHT = 14
PREDICATE_TYPE_SYSTEM_RATIO = 15
PREDICATE_TYPE_SYSTEM_DURATION = 16
PREDICATE_TYPE_SYSTEM_MIME = 17
PREDICATE_TYPE_SYSTEM_RATING = 18
PREDICATE_TYPE_SYSTEM_SIMILAR_TO = 19
PREDICATE_TYPE_SYSTEM_LOCAL = 20
PREDICATE_TYPE_SYSTEM_NOT_LOCAL = 21
PREDICATE_TYPE_SYSTEM_NUM_WORDS = 22
PREDICATE_TYPE_SYSTEM_FILE_SERVICE = 23
PREDICATE_TYPE_SYSTEM_NUM_PIXELS = 24
PREDICATE_TYPE_SYSTEM_DIMENSIONS = 25

SYSTEM_PREDICATES = [ PREDICATE_TYPE_SYSTEM_EVERYTHING, PREDICATE_TYPE_SYSTEM_INBOX, PREDICATE_TYPE_SYSTEM_ARCHIVE, PREDICATE_TYPE_SYSTEM_UNTAGGED, PREDICATE_TYPE_SYSTEM_NUM_TAGS, PREDICATE_TYPE_SYSTEM_LIMIT, PREDICATE_TYPE_SYSTEM_SIZE, PREDICATE_TYPE_SYSTEM_AGE, PREDICATE_TYPE_SYSTEM_HASH, PREDICATE_TYPE_SYSTEM_WIDTH, PREDICATE_TYPE_SYSTEM_HEIGHT, PREDICATE_TYPE_SYSTEM_RATIO, PREDICATE_TYPE_SYSTEM_DURATION, PREDICATE_TYPE_SYSTEM_MIME, PREDICATE_TYPE_SYSTEM_RATING, PREDICATE_TYPE_SYSTEM_SIMILAR_TO, PREDICATE_TYPE_SYSTEM_LOCAL, PREDICATE_TYPE_SYSTEM_NOT_LOCAL, PREDICATE_TYPE_SYSTEM_NUM_WORDS, PREDICATE_TYPE_SYSTEM_FILE_SERVICE, PREDICATE_TYPE_SYSTEM_NUM_PIXELS, PREDICATE_TYPE_SYSTEM_DIMENSIONS ]

SITE_TYPE_DEVIANT_ART = 0
SITE_TYPE_GIPHY = 1
SITE_TYPE_PIXIV = 2
SITE_TYPE_BOORU = 3
SITE_TYPE_TUMBLR = 4
SITE_TYPE_HENTAI_FOUNDRY = 5
SITE_TYPE_NEWGROUNDS = 6
SITE_TYPE_NEWGROUNDS_MOVIES = 7
SITE_TYPE_NEWGROUNDS_GAMES = 8
SITE_TYPE_HENTAI_FOUNDRY_ARTIST = 9
SITE_TYPE_HENTAI_FOUNDRY_ARTIST_PICTURES = 10
SITE_TYPE_HENTAI_FOUNDRY_ARTIST_SCRAPS = 11
SITE_TYPE_HENTAI_FOUNDRY_TAGS = 12
SITE_TYPE_PIXIV_ARTIST_ID = 13
SITE_TYPE_PIXIV_TAG = 14
SITE_TYPE_DEFAULT = 15

site_type_string_lookup = {}

site_type_string_lookup[ SITE_TYPE_DEFAULT ] = 'default'
site_type_string_lookup[ SITE_TYPE_BOORU ] = 'booru'
site_type_string_lookup[ SITE_TYPE_DEVIANT_ART ] = 'deviant art'
site_type_string_lookup[ SITE_TYPE_GIPHY ] = 'giphy'
site_type_string_lookup[ SITE_TYPE_HENTAI_FOUNDRY ] = 'hentai foundry'
site_type_string_lookup[ SITE_TYPE_HENTAI_FOUNDRY_ARTIST ] = 'hentai foundry artist'
site_type_string_lookup[ SITE_TYPE_HENTAI_FOUNDRY_ARTIST_PICTURES ] = 'hentai foundry artist pictures'
site_type_string_lookup[ SITE_TYPE_HENTAI_FOUNDRY_ARTIST_SCRAPS ] = 'hentai foundry artist scraps'
site_type_string_lookup[ SITE_TYPE_HENTAI_FOUNDRY_TAGS ] = 'hentai foundry tags'
site_type_string_lookup[ SITE_TYPE_NEWGROUNDS ] = 'newgrounds'
site_type_string_lookup[ SITE_TYPE_NEWGROUNDS_GAMES ] = 'newgrounds games'
site_type_string_lookup[ SITE_TYPE_NEWGROUNDS_MOVIES ] = 'newgrounds movies'
site_type_string_lookup[ SITE_TYPE_PIXIV ] = 'pixiv'
site_type_string_lookup[ SITE_TYPE_PIXIV_ARTIST_ID ] = 'pixiv artist id'
site_type_string_lookup[ SITE_TYPE_PIXIV_TAG ] = 'pixiv tag'
site_type_string_lookup[ SITE_TYPE_TUMBLR ] = 'tumblr'

# default options

DEFAULT_LOCAL_FILE_PORT = 45865
DEFAULT_LOCAL_BOORU_PORT = 45866
DEFAULT_SERVER_ADMIN_PORT = 45870
DEFAULT_SERVICE_PORT = 45871

SERVER_ADMIN_KEY = 'server admin'

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

sqlite3.register_converter( 'BLOB_BYTES', str )
sqlite3.register_converter( 'INTEGER_BOOLEAN', integer_boolean_to_bool )
sqlite3.register_converter( 'TEXT_YAML', yaml.safe_load )
