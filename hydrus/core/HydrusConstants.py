import os
import sqlite3
import sys
import typing
import yaml

# old method of getting frozen dir, doesn't work for symlinks looks like:
# BASE_DIR = getattr( sys, '_MEIPASS', None )

RUNNING_FROM_FROZEN_BUILD = getattr( sys, 'frozen', False )

if RUNNING_FROM_FROZEN_BUILD:
    
    real_exe_path = os.path.realpath( sys.executable )
    
    BASE_DIR = os.path.dirname( real_exe_path )
    
else:
    
    try:
        
        hc_realpath_dir = os.path.dirname( os.path.realpath( __file__ ) )
        
        HYDRUS_MODULE_DIR = os.path.split( hc_realpath_dir )[0]
        
        BASE_DIR = os.path.split( HYDRUS_MODULE_DIR )[0]
        
    except NameError: # if __file__ is not defined due to some weird OS
        
        BASE_DIR = os.path.realpath( sys.path[0] )
        
    
    if BASE_DIR == '':
        
        BASE_DIR = os.getcwd()
        

muh_platform = sys.platform.lower()

PLATFORM_WINDOWS = muh_platform == 'win32'
PLATFORM_MACOS = muh_platform == 'darwin'
PLATFORM_LINUX = muh_platform == 'linux'
PLATFORM_HAIKU = muh_platform == 'haiku1'

RUNNING_FROM_SOURCE = sys.argv[0].endswith( '.py' ) or sys.argv[0].endswith( '.pyw' )
RUNNING_FROM_MACOS_APP = os.path.exists( os.path.join( BASE_DIR, 'running_from_app' ) )

BIN_DIR = os.path.join( BASE_DIR, 'bin' )
HELP_DIR = os.path.join( BASE_DIR, 'help' )
INCLUDE_DIR = os.path.join( BASE_DIR, 'include' )
STATIC_DIR = os.path.join( BASE_DIR, 'static' )

DEFAULT_DB_DIR = os.path.join( BASE_DIR, 'db' )

if PLATFORM_MACOS:
    
    desired_userpath_db_dir = os.path.join( '~', 'Library', 'Hydrus' )
    
else:
    
    desired_userpath_db_dir = os.path.join( '~', 'Hydrus' )
    

USERPATH_DB_DIR = os.path.expanduser( desired_userpath_db_dir )

if USERPATH_DB_DIR == desired_userpath_db_dir:
    
    # could not figure it out, probably a crazy user situation atm
    
    USERPATH_DB_DIR = None
    

LICENSE_PATH = os.path.join( BASE_DIR, 'license.txt' )

#

options = {}

# Misc

NETWORK_VERSION = 20
SOFTWARE_VERSION = 478
CLIENT_API_VERSION = 28

SERVER_THUMBNAIL_DIMENSIONS = ( 200, 200 )

HYDRUS_KEY_LENGTH = 32

READ_BLOCK_SIZE = 256 * 1024

lifetimes = [ ( 'one month', 30 * 86400 ), ( 'three months', 3 * 30 * 86400 ), ( 'six months', 6 * 30 * 86400 ), ( 'one year', 365 * 86400 ), ( 'two years', 2 * 365 * 86400 ), ( 'five years', 5 * 365 * 86400 ), ( 'does not expire', None ) ]

# some typing stuff

noneable_int = typing.Optional[ int ]
noneable_str = typing.Optional[ str ]

# Enums

BANDWIDTH_TYPE_DATA = 0
BANDWIDTH_TYPE_REQUESTS = 1

bandwidth_type_string_lookup = {
    BANDWIDTH_TYPE_DATA : 'data',
    BANDWIDTH_TYPE_REQUESTS : 'requests'
}

CONTENT_MERGE_ACTION_COPY = 0
CONTENT_MERGE_ACTION_MOVE = 1
CONTENT_MERGE_ACTION_TWO_WAY_MERGE = 2

content_merge_string_lookup = {
    CONTENT_MERGE_ACTION_COPY : 'copy from worse to better',
    CONTENT_MERGE_ACTION_MOVE : 'move from worse to better',
    CONTENT_MERGE_ACTION_TWO_WAY_MERGE : 'copy in both directions'
}

CONTENT_STATUS_CURRENT = 0
CONTENT_STATUS_PENDING = 1
CONTENT_STATUS_DELETED = 2
CONTENT_STATUS_PETITIONED = 3

content_status_string_lookup = {
    CONTENT_STATUS_CURRENT : 'current',
    CONTENT_STATUS_PENDING : 'pending',
    CONTENT_STATUS_DELETED : 'deleted',
    CONTENT_STATUS_PETITIONED : 'petitioned'
}

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
CONTENT_TYPE_VARIABLE = 14
CONTENT_TYPE_HASH = 15
CONTENT_TYPE_TIMESTAMP = 16
CONTENT_TYPE_TITLE = 17
CONTENT_TYPE_NOTES = 18
CONTENT_TYPE_FILE_VIEWING_STATS = 19
CONTENT_TYPE_TAG = 20
CONTENT_TYPE_DEFINITIONS = 21

content_type_string_lookup = {
    CONTENT_TYPE_MAPPINGS : 'mappings',
    CONTENT_TYPE_TAG_SIBLINGS : 'tag siblings',
    CONTENT_TYPE_TAG_PARENTS : 'tag parents',
    CONTENT_TYPE_FILES : 'files',
    CONTENT_TYPE_RATINGS : 'ratings',
    CONTENT_TYPE_MAPPING : 'mapping',
    CONTENT_TYPE_DIRECTORIES : 'directories',
    CONTENT_TYPE_URLS : 'urls',
    CONTENT_TYPE_VETO : 'veto',
    CONTENT_TYPE_ACCOUNTS : 'accounts',
    CONTENT_TYPE_OPTIONS : 'options',
    CONTENT_TYPE_SERVICES : 'services',
    CONTENT_TYPE_UNKNOWN : 'unknown',
    CONTENT_TYPE_ACCOUNT_TYPES : 'account types',
    CONTENT_TYPE_VARIABLE : 'variable',
    CONTENT_TYPE_HASH : 'hash',
    CONTENT_TYPE_TIMESTAMP : 'timestamp',
    CONTENT_TYPE_TITLE : 'title',
    CONTENT_TYPE_NOTES : 'notes',
    CONTENT_TYPE_FILE_VIEWING_STATS : 'file viewing stats',
    CONTENT_TYPE_DEFINITIONS : 'definitions'
}

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
CONTENT_UPDATE_SET = 15
CONTENT_UPDATE_FLIP = 16
CONTENT_UPDATE_CLEAR_DELETE_RECORD = 17
CONTENT_UPDATE_INCREMENT = 18
CONTENT_UPDATE_DECREMENT = 19

content_update_string_lookup = {
    CONTENT_UPDATE_ADD : 'add',
    CONTENT_UPDATE_DELETE : 'delete',
    CONTENT_UPDATE_PEND : 'pending',
    CONTENT_UPDATE_RESCIND_PEND : 'rescind pending',
    CONTENT_UPDATE_PETITION : 'petition',
    CONTENT_UPDATE_RESCIND_PETITION : 'rescind petition',
    CONTENT_UPDATE_EDIT_LOG : 'edit log',
    CONTENT_UPDATE_ARCHIVE : 'archive',
    CONTENT_UPDATE_INBOX : 'inbox',
    CONTENT_UPDATE_RATING : 'rating',
    CONTENT_UPDATE_DENY_PEND : 'deny pend',
    CONTENT_UPDATE_DENY_PETITION : 'deny petition',
    CONTENT_UPDATE_UNDELETE : 'undelete',
    CONTENT_UPDATE_SET : 'set',
    CONTENT_UPDATE_FLIP : 'flip on/off',
    CONTENT_UPDATE_CLEAR_DELETE_RECORD : 'clear deletion record',
    CONTENT_UPDATE_INCREMENT : 'increment',
    CONTENT_UPDATE_DECREMENT : 'decrement'
}

DEFINITIONS_TYPE_HASHES = 0
DEFINITIONS_TYPE_TAGS = 1

DUPLICATE_POTENTIAL = 0
DUPLICATE_FALSE_POSITIVE = 1
DUPLICATE_SAME_QUALITY = 2
DUPLICATE_ALTERNATE = 3
DUPLICATE_BETTER = 4
DUPLICATE_SMALLER_BETTER = 5
DUPLICATE_LARGER_BETTER = 6
DUPLICATE_WORSE = 7
DUPLICATE_MEMBER = 8
DUPLICATE_KING = 9
DUPLICATE_CONFIRMED_ALTERNATE = 10

duplicate_type_string_lookup = {
    DUPLICATE_POTENTIAL : 'potential duplicates',
    DUPLICATE_FALSE_POSITIVE : 'not related/false positive',
    DUPLICATE_SAME_QUALITY : 'same quality',
    DUPLICATE_ALTERNATE : 'alternates',
    DUPLICATE_BETTER : 'this is better',
    DUPLICATE_SMALLER_BETTER : 'smaller hash_id is better',
    DUPLICATE_LARGER_BETTER : 'larger hash_id is better',
    DUPLICATE_WORSE : 'this is worse',
    DUPLICATE_MEMBER : 'duplicates',
    DUPLICATE_KING : 'the best quality duplicate',
    DUPLICATE_CONFIRMED_ALTERNATE : 'confirmed alternates'
}

ENCODING_RAW = 0
ENCODING_HEX = 1
ENCODING_BASE64 = 2

encoding_string_lookup = {
    ENCODING_RAW : 'raw bytes',
    ENCODING_HEX : 'hexadecimal',
    ENCODING_BASE64 : 'base64'
}

IMPORT_FOLDER_TYPE_DELETE = 0
IMPORT_FOLDER_TYPE_SYNCHRONISE = 1

EXPORT_FOLDER_TYPE_REGULAR = 0
EXPORT_FOLDER_TYPE_SYNCHRONISE = 1

FILTER_WHITELIST = 0
FILTER_BLACKLIST = 1

HYDRUS_CLIENT = 0
HYDRUS_SERVER = 1
HYDRUS_TEST = 2

MAINTENANCE_IDLE = 0
MAINTENANCE_SHUTDOWN = 1
MAINTENANCE_FORCED = 2
MAINTENANCE_ACTIVE = 3

NICE_RESOLUTIONS = {
    ( 640, 480 ) : '480p',
    ( 1280, 720 ) : '720p',
    ( 1920, 1080 ) : '1080p',
    ( 3840, 2160 ) : '4k',
    ( 720, 1280 ) : 'vertical 720p',
    ( 1080, 1920 ) : 'vertical 1080p',
    ( 2160, 3840 ) : 'vertical 4k'
}

NICE_RATIOS = {
    1 : '1:1',
    4 / 3 : '4:3',
    5 / 4 : '5:4',
    16 / 9 : '16:9',
    21 / 9 : '21:9',
    47 / 20 : '2.35:1',
    9 / 16 : '9:16',
    2 / 3 : '2:3',
    4 / 5 : '4:5'
}

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

permissions_string_lookup = {
    GET_DATA : 'get data',
    POST_DATA : 'post data',
    POST_PETITIONS : 'post petitions',
    RESOLVE_PETITIONS : 'resolve petitions',
    MANAGE_USERS : 'manage users',
    GENERAL_ADMIN : 'general administration',
    EDIT_SERVICES : 'edit services',
    UNKNOWN_PERMISSION : 'unknown'
}

# new permissions

PERMISSION_ACTION_PETITION = 0
PERMISSION_ACTION_CREATE = 1
PERMISSION_ACTION_MODERATE = 2

permission_pair_string_lookup = {
    ( CONTENT_TYPE_ACCOUNTS, None ) : 'cannot change accounts',
    ( CONTENT_TYPE_ACCOUNTS, PERMISSION_ACTION_CREATE ) : 'can create accounts',
    ( CONTENT_TYPE_ACCOUNTS, PERMISSION_ACTION_MODERATE ) : 'can manage accounts completely',
    ( CONTENT_TYPE_ACCOUNT_TYPES, None ) : 'cannot change account types',
    ( CONTENT_TYPE_ACCOUNT_TYPES, PERMISSION_ACTION_MODERATE ) : 'can manage account types completely',
    ( CONTENT_TYPE_OPTIONS, None ) : 'cannot change service options',
    ( CONTENT_TYPE_OPTIONS, PERMISSION_ACTION_MODERATE ) : 'can manage service options completely',
    ( CONTENT_TYPE_SERVICES, None ) : 'cannot change services',
    ( CONTENT_TYPE_SERVICES, PERMISSION_ACTION_MODERATE ) : 'can manage services completely',
    ( CONTENT_TYPE_FILES, None ) : 'can only download files',
    ( CONTENT_TYPE_FILES, PERMISSION_ACTION_PETITION ) : 'can petition to remove existing files',
    ( CONTENT_TYPE_FILES, PERMISSION_ACTION_CREATE ) : 'can upload new files and petition existing ones',
    ( CONTENT_TYPE_FILES, PERMISSION_ACTION_MODERATE ) : 'can upload and delete files and process petitions',
    ( CONTENT_TYPE_MAPPINGS, None ) : 'can only download mappings',
    ( CONTENT_TYPE_MAPPINGS, PERMISSION_ACTION_PETITION ) : 'can petition to remove existing mappings',
    ( CONTENT_TYPE_MAPPINGS, PERMISSION_ACTION_CREATE ) : 'can upload new mappings and petition existing ones',
    ( CONTENT_TYPE_MAPPINGS, PERMISSION_ACTION_MODERATE ) : 'can upload and delete mappings and process petitions',
    ( CONTENT_TYPE_TAG_PARENTS, None ) : 'can only download tag parents',
    ( CONTENT_TYPE_TAG_PARENTS, PERMISSION_ACTION_PETITION ) : 'can petition to add or remove tag parents',
    ( CONTENT_TYPE_TAG_PARENTS, PERMISSION_ACTION_MODERATE ) : 'can upload and delete tag parents and process petitions',
    ( CONTENT_TYPE_TAG_SIBLINGS, None ) : 'can only download tag siblings',
    ( CONTENT_TYPE_TAG_SIBLINGS, PERMISSION_ACTION_PETITION ) : 'can petition to add or remove tag siblings',
    ( CONTENT_TYPE_TAG_SIBLINGS, PERMISSION_ACTION_MODERATE ) : 'can upload and delete tag siblings and process petitions'
}

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
TEST_SERVICE = 16
LOCAL_NOTES = 17
CLIENT_API_SERVICE = 18
COMBINED_DELETED_FILE = 19
SERVER_ADMIN = 99
NULL_SERVICE = 100

service_string_lookup = {
    TAG_REPOSITORY : 'hydrus tag repository',
    FILE_REPOSITORY : 'hydrus file repository',
    LOCAL_FILE_DOMAIN : 'local file domain',
    LOCAL_FILE_TRASH_DOMAIN : 'local trash file domain',
    COMBINED_LOCAL_FILE : 'virtual combined local file service',
    MESSAGE_DEPOT : 'hydrus message depot',
    LOCAL_TAG : 'local tag service',
    LOCAL_RATING_NUMERICAL : 'local numerical rating service',
    LOCAL_RATING_LIKE : 'local like/dislike rating service',
    RATING_NUMERICAL_REPOSITORY : 'hydrus numerical rating repository',
    RATING_LIKE_REPOSITORY : 'hydrus like/dislike rating repository',
    COMBINED_TAG : 'virtual combined tag service',
    COMBINED_FILE : 'virtual combined file service',
    LOCAL_BOORU : 'client local booru',
    CLIENT_API_SERVICE : 'client api',
    IPFS : 'ipfs daemon',
    TEST_SERVICE : 'test service',
    LOCAL_NOTES : 'local file notes service',
    SERVER_ADMIN : 'hydrus server administration service',
    COMBINED_DELETED_FILE : 'virtual deleted file service',
    NULL_SERVICE : 'null service'
}

LOCAL_FILE_SERVICES = ( LOCAL_FILE_DOMAIN, LOCAL_FILE_TRASH_DOMAIN, COMBINED_LOCAL_FILE )
LOCAL_TAG_SERVICES = ( LOCAL_TAG, )

LOCAL_SERVICES = LOCAL_FILE_SERVICES + LOCAL_TAG_SERVICES + ( LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, LOCAL_BOORU, LOCAL_NOTES, CLIENT_API_SERVICE )

RATINGS_SERVICES = ( LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY )
REPOSITORIES = ( TAG_REPOSITORY, FILE_REPOSITORY, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY )
RESTRICTED_SERVICES = REPOSITORIES + ( SERVER_ADMIN, MESSAGE_DEPOT )
REMOTE_SERVICES = RESTRICTED_SERVICES + ( IPFS, )
REMOTE_FILE_SERVICES = ( FILE_REPOSITORY, IPFS )
FILE_SERVICES = LOCAL_FILE_SERVICES + ( FILE_REPOSITORY, IPFS )
REAL_TAG_SERVICES = ( LOCAL_TAG, TAG_REPOSITORY )
ADDREMOVABLE_SERVICES = ( LOCAL_TAG, LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, FILE_REPOSITORY, TAG_REPOSITORY, SERVER_ADMIN, IPFS )
MUST_HAVE_AT_LEAST_ONE_SERVICES = ( LOCAL_TAG, )
NONEDITABLE_SERVICES = ( LOCAL_FILE_DOMAIN, LOCAL_FILE_TRASH_DOMAIN, COMBINED_FILE, COMBINED_TAG, COMBINED_LOCAL_FILE )

FILE_SERVICES_WITH_NO_DELETE_RECORD = ( LOCAL_FILE_TRASH_DOMAIN, COMBINED_DELETED_FILE )

FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES = ( LOCAL_FILE_DOMAIN, LOCAL_FILE_TRASH_DOMAIN, COMBINED_LOCAL_FILE, COMBINED_DELETED_FILE, FILE_REPOSITORY, IPFS )
FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES = ( COMBINED_LOCAL_FILE, COMBINED_DELETED_FILE, FILE_REPOSITORY, IPFS )

FILE_SERVICES_COVERED_BY_COMBINED_LOCAL_FILE = ( LOCAL_FILE_DOMAIN, LOCAL_FILE_TRASH_DOMAIN )
FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE = ( LOCAL_FILE_DOMAIN, FILE_REPOSITORY, IPFS )

ALL_SERVICES = REMOTE_SERVICES + LOCAL_SERVICES + ( COMBINED_FILE, COMBINED_TAG, COMBINED_DELETED_FILE )
ALL_TAG_SERVICES = REAL_TAG_SERVICES + ( COMBINED_TAG, )
ALL_FILE_SERVICES = FILE_SERVICES + ( COMBINED_FILE, )

SERVICES_WITH_THUMBNAILS = [ FILE_REPOSITORY, LOCAL_FILE_DOMAIN ]

SERVICE_TYPES_TO_CONTENT_TYPES = {
    FILE_REPOSITORY : ( CONTENT_TYPE_FILES, ),
    LOCAL_FILE_DOMAIN : ( CONTENT_TYPE_FILES, ),
    LOCAL_FILE_TRASH_DOMAIN : ( CONTENT_TYPE_FILES, ),
    COMBINED_LOCAL_FILE : ( CONTENT_TYPE_FILES, ),
    IPFS : ( CONTENT_TYPE_FILES, ),
    TAG_REPOSITORY : ( CONTENT_TYPE_MAPPINGS, CONTENT_TYPE_TAG_PARENTS, CONTENT_TYPE_TAG_SIBLINGS ),
    LOCAL_TAG : ( CONTENT_TYPE_MAPPINGS, CONTENT_TYPE_TAG_PARENTS, CONTENT_TYPE_TAG_SIBLINGS ),
    LOCAL_RATING_LIKE : ( CONTENT_TYPE_RATINGS, ),
    LOCAL_RATING_NUMERICAL : ( CONTENT_TYPE_RATINGS, )
}

DELETE_FILES_PETITION = 0
DELETE_TAG_PETITION = 1

BAN = 0
SUPERBAN = 1

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

query_type_string_lookup = {
    GET : 'GET',
    POST : 'POST',
    OPTIONS : 'OPTIONS'
}

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
IMAGE_APNG = 23
UNDETERMINED_PNG = 24
VIDEO_MPEG = 25
VIDEO_MOV = 26
VIDEO_AVI = 27
APPLICATION_HYDRUS_UPDATE_DEFINITIONS = 28
APPLICATION_HYDRUS_UPDATE_CONTENT = 29
TEXT_PLAIN = 30
APPLICATION_RAR = 31
APPLICATION_7Z = 32
IMAGE_WEBP = 33
IMAGE_TIFF = 34
APPLICATION_PSD = 35
AUDIO_M4A = 36
VIDEO_REALMEDIA = 37
AUDIO_REALMEDIA = 38
AUDIO_TRUEAUDIO = 39
GENERAL_AUDIO = 40
GENERAL_IMAGE = 41
GENERAL_VIDEO = 42
GENERAL_APPLICATION = 43
GENERAL_ANIMATION = 44
APPLICATION_CLIP = 45
AUDIO_WAVE = 46
VIDEO_OGV = 47
AUDIO_MKV = 48
AUDIO_MP4 = 49
UNDETERMINED_MP4 = 50
APPLICATION_CBOR = 51
APPLICATION_OCTET_STREAM = 100
APPLICATION_UNKNOWN = 101

GENERAL_FILETYPES = { GENERAL_APPLICATION, GENERAL_AUDIO, GENERAL_IMAGE, GENERAL_VIDEO, GENERAL_ANIMATION }

SEARCHABLE_MIMES = { IMAGE_JPEG, IMAGE_PNG, IMAGE_APNG, IMAGE_GIF, IMAGE_WEBP, IMAGE_TIFF, IMAGE_ICON, APPLICATION_FLASH, VIDEO_AVI, VIDEO_FLV, VIDEO_MOV, VIDEO_MP4, VIDEO_MKV, VIDEO_REALMEDIA, VIDEO_WEBM, VIDEO_OGV, VIDEO_MPEG, APPLICATION_CLIP, APPLICATION_PSD, APPLICATION_PDF, APPLICATION_ZIP, APPLICATION_RAR, APPLICATION_7Z, AUDIO_M4A, AUDIO_MP3, AUDIO_REALMEDIA, AUDIO_OGG, AUDIO_FLAC, AUDIO_WAVE, AUDIO_TRUEAUDIO, AUDIO_WMA, VIDEO_WMV, AUDIO_MKV, AUDIO_MP4 }

STORABLE_MIMES = set( SEARCHABLE_MIMES ).union( { APPLICATION_HYDRUS_UPDATE_CONTENT, APPLICATION_HYDRUS_UPDATE_DEFINITIONS } )

ALLOWED_MIMES = set( STORABLE_MIMES ).union( { IMAGE_BMP } )

DECOMPRESSION_BOMB_IMAGES = { IMAGE_JPEG, IMAGE_PNG }

IMAGES = { IMAGE_JPEG, IMAGE_PNG, IMAGE_BMP, IMAGE_WEBP, IMAGE_TIFF, IMAGE_ICON }

ANIMATIONS = { IMAGE_GIF, IMAGE_APNG }

AUDIO = { AUDIO_M4A, AUDIO_MP3, AUDIO_OGG, AUDIO_FLAC, AUDIO_WAVE, AUDIO_WMA, AUDIO_REALMEDIA, AUDIO_TRUEAUDIO, AUDIO_MKV, AUDIO_MP4 }

VIDEO = { VIDEO_AVI, VIDEO_FLV, VIDEO_MOV, VIDEO_MP4, VIDEO_WMV, VIDEO_MKV, VIDEO_REALMEDIA, VIDEO_WEBM, VIDEO_OGV, VIDEO_MPEG }

APPLICATIONS = { APPLICATION_FLASH, APPLICATION_PSD, APPLICATION_CLIP, APPLICATION_PDF, APPLICATION_ZIP, APPLICATION_RAR, APPLICATION_7Z }

general_mimetypes_to_mime_groups = {
    GENERAL_APPLICATION : APPLICATIONS,
    GENERAL_AUDIO : AUDIO,
    GENERAL_IMAGE : IMAGES,
    GENERAL_VIDEO : VIDEO,
    GENERAL_ANIMATION : ANIMATIONS
}

mimes_to_general_mimetypes = {}

for ( general_mime_type, mimes_in_type ) in general_mimetypes_to_mime_groups.items():
    
    for mime in mimes_in_type:
        
        mimes_to_general_mimetypes[ mime ] = general_mime_type
        
    

MIMES_THAT_DEFINITELY_HAVE_AUDIO = tuple( [ APPLICATION_FLASH ] + list( AUDIO ) )
MIMES_THAT_MAY_HAVE_AUDIO = tuple( list( MIMES_THAT_DEFINITELY_HAVE_AUDIO ) + list( VIDEO ) )

ARCHIVES = { APPLICATION_ZIP, APPLICATION_HYDRUS_ENCRYPTED_ZIP, APPLICATION_RAR, APPLICATION_7Z }

MIMES_WITH_THUMBNAILS = set( IMAGES ).union( ANIMATIONS ).union( VIDEO ).union( { APPLICATION_FLASH, APPLICATION_CLIP, APPLICATION_PSD } )

# I think this is correct, but not certain. we've seen something called icc_profile from PIL for all of these I think!
FILES_THAT_CAN_HAVE_ICC_PROFILE = { IMAGE_JPEG, IMAGE_PNG, IMAGE_GIF, IMAGE_TIFF }

FILES_THAT_CAN_HAVE_PIXEL_HASH = set( IMAGES ).union( { IMAGE_GIF } )
FILES_THAT_HAVE_PERCEPTUAL_HASH = set( IMAGES )

HYDRUS_UPDATE_FILES = ( APPLICATION_HYDRUS_UPDATE_DEFINITIONS, APPLICATION_HYDRUS_UPDATE_CONTENT )

mime_enum_lookup = {
    'collection' : APPLICATION_HYDRUS_CLIENT_COLLECTION,
    'image/jpe' : IMAGE_JPEG,
    'image/jpeg' : IMAGE_JPEG,
    'image/jpg' : IMAGE_JPEG,
    'image/x-png' : IMAGE_PNG,
    'image/png' : IMAGE_PNG,
    'image/apng' : IMAGE_APNG,
    'image/gif' : IMAGE_GIF,
    'image/bmp' : IMAGE_BMP,
    'image/webp' : IMAGE_WEBP,
    'image/tiff' : IMAGE_TIFF,
    'image/x-icon' : IMAGE_ICON,
    'image/vnd.microsoft.icon' : IMAGE_ICON,
    'image' : IMAGES,
    'application/x-shockwave-flash' : APPLICATION_FLASH,
    'application/x-photoshop' : APPLICATION_PSD,
    'image/vnd.adobe.photoshop' : APPLICATION_PSD,
    'application/clip' : APPLICATION_CLIP,
    'application/octet-stream' : APPLICATION_OCTET_STREAM,
    'application/x-yaml' : APPLICATION_YAML,
    'PDF document' : APPLICATION_PDF,
    'application/pdf' : APPLICATION_PDF,
    'application/zip' : APPLICATION_ZIP,
    'application/vnd.rar' : APPLICATION_RAR,
    'application/x-7z-compressed' : APPLICATION_7Z,
    'application/json' : APPLICATION_JSON,
    'application/cbor': APPLICATION_CBOR,
    'application/hydrus-encrypted-zip' : APPLICATION_HYDRUS_ENCRYPTED_ZIP,
    'application/hydrus-update-content' : APPLICATION_HYDRUS_UPDATE_CONTENT,
    'application/hydrus-update-definitions' : APPLICATION_HYDRUS_UPDATE_DEFINITIONS,
    'application' : APPLICATIONS,
    'audio/mp4' : AUDIO_M4A,
    'audio/mp3' : AUDIO_MP3,
    'audio/ogg' : AUDIO_OGG,
    'audio/vnd.rn-realaudio' : AUDIO_REALMEDIA,
    'audio/x-tta' : AUDIO_TRUEAUDIO,
    'audio/flac' : AUDIO_FLAC,
    'audio/x-wav' : AUDIO_WAVE,
    'audio/wav' : AUDIO_WAVE,
    'audio/wave' : AUDIO_WAVE,
    'audio/x-ms-wma' : AUDIO_WMA,
    'text/html' : TEXT_HTML,
    'text/plain' : TEXT_PLAIN,
    'video/x-msvideo' : VIDEO_AVI,
    'video/x-flv' : VIDEO_FLV,
    'video/quicktime' : VIDEO_MOV,
    'video/mp4' : VIDEO_MP4,
    'video/mpeg' : VIDEO_MPEG,
    'video/x-ms-wmv' : VIDEO_WMV,
    'video/x-matroska' : VIDEO_MKV,
    'video/ogg' : VIDEO_OGV,
    'video/vnd.rn-realvideo' : VIDEO_REALMEDIA,
    'application/vnd.rn-realmedia' : VIDEO_REALMEDIA,
    'video/webm' : VIDEO_WEBM,
    'video' : VIDEO,
    'unknown filetype' : APPLICATION_UNKNOWN
}

mime_string_lookup = {
    APPLICATION_HYDRUS_CLIENT_COLLECTION : 'collection',
    IMAGE_JPEG : 'jpeg',
    IMAGE_PNG : 'png',
    IMAGE_APNG : 'apng',
    IMAGE_GIF : 'gif',
    IMAGE_BMP : 'bmp',
    IMAGE_WEBP : 'webp',
    IMAGE_TIFF : 'tiff',
    IMAGE_ICON : 'icon',
    APPLICATION_FLASH : 'flash',
    APPLICATION_OCTET_STREAM : 'application/octet-stream',
    APPLICATION_YAML : 'yaml',
    APPLICATION_JSON : 'json',
    APPLICATION_CBOR : 'cbor',
    APPLICATION_PDF : 'pdf',
    APPLICATION_PSD : 'photoshop psd',
    APPLICATION_CLIP : 'clip',
    APPLICATION_ZIP : 'zip',
    APPLICATION_RAR : 'rar',
    APPLICATION_7Z : '7z',
    APPLICATION_HYDRUS_ENCRYPTED_ZIP : 'application/hydrus-encrypted-zip',
    APPLICATION_HYDRUS_UPDATE_CONTENT : 'application/hydrus-update-content',
    APPLICATION_HYDRUS_UPDATE_DEFINITIONS : 'application/hydrus-update-definitions',
    AUDIO_M4A : 'm4a',
    AUDIO_MP3 : 'mp3',
    AUDIO_OGG : 'ogg',
    AUDIO_FLAC : 'flac',
    AUDIO_MKV : 'matroska audio',
    AUDIO_MP4 : 'mp4 audio',
    AUDIO_WAVE : 'wave',
    AUDIO_REALMEDIA : 'realaudio',
    AUDIO_TRUEAUDIO : 'tta',
    AUDIO_WMA : 'wma',
    TEXT_HTML : 'html',
    TEXT_PLAIN : 'plaintext',
    VIDEO_AVI : 'avi',
    VIDEO_FLV : 'flv',
    VIDEO_MOV : 'quicktime',
    VIDEO_MP4 : 'mp4',
    VIDEO_MPEG : 'mpeg',
    VIDEO_WMV : 'wmv',
    VIDEO_MKV : 'matroska',
    VIDEO_OGV : 'ogv',
    VIDEO_REALMEDIA : 'realvideo',
    VIDEO_WEBM : 'webm',
    UNDETERMINED_WM : 'wma or wmv',
    UNDETERMINED_MP4 : 'mp4 with or without audio',
    UNDETERMINED_PNG : 'png or apng',
    APPLICATION_UNKNOWN : 'unknown filetype',
    GENERAL_APPLICATION : 'application',
    GENERAL_AUDIO : 'audio',
    GENERAL_IMAGE : 'image',
    GENERAL_VIDEO : 'video',
    GENERAL_ANIMATION : 'animation'
}

mime_mimetype_string_lookup = {
    APPLICATION_HYDRUS_CLIENT_COLLECTION : 'collection',
    IMAGE_JPEG : 'image/jpeg',
    IMAGE_PNG : 'image/png',
    IMAGE_APNG : 'image/apng',
    IMAGE_GIF : 'image/gif',
    IMAGE_BMP : 'image/bmp',
    IMAGE_WEBP : 'image/webp',
    IMAGE_TIFF : 'image/tiff',
    IMAGE_ICON : 'image/x-icon',
    APPLICATION_FLASH : 'application/x-shockwave-flash',
    APPLICATION_OCTET_STREAM : 'application/octet-stream',
    APPLICATION_YAML : 'application/x-yaml',
    APPLICATION_JSON : 'application/json',
    APPLICATION_CBOR : 'application/cbor',
    APPLICATION_PDF : 'application/pdf',
    APPLICATION_PSD : 'application/x-photoshop',
    APPLICATION_CLIP : 'application/clip',
    APPLICATION_ZIP : 'application/zip',
    APPLICATION_RAR : 'application/vnd.rar',
    APPLICATION_7Z : 'application/x-7z-compressed',
    APPLICATION_HYDRUS_ENCRYPTED_ZIP : 'application/hydrus-encrypted-zip',
    APPLICATION_HYDRUS_UPDATE_CONTENT : 'application/hydrus-update-content',
    APPLICATION_HYDRUS_UPDATE_DEFINITIONS : 'application/hydrus-update-definitions',
    AUDIO_M4A : 'audio/mp4',
    AUDIO_MP3 : 'audio/mp3',
    AUDIO_OGG : 'audio/ogg',
    AUDIO_FLAC : 'audio/flac',
    AUDIO_MKV : 'audio/x-matroska',
    AUDIO_MP4 : 'audio/mp4',
    AUDIO_WAVE : 'audio/x-wav',
    AUDIO_REALMEDIA : 'audio/vnd.rn-realaudio',
    AUDIO_TRUEAUDIO : 'audio/x-tta',
    AUDIO_WMA : 'audio/x-ms-wma',
    TEXT_HTML : 'text/html',
    TEXT_PLAIN : 'text/plain',
    VIDEO_AVI : 'video/x-msvideo',
    VIDEO_FLV : 'video/x-flv',
    VIDEO_MOV : 'video/quicktime',
    VIDEO_MP4 : 'video/mp4',
    VIDEO_MPEG : 'video/mpeg',
    VIDEO_WMV : 'video/x-ms-wmv',
    VIDEO_MKV : 'video/x-matroska',
    VIDEO_OGV : 'video/ogg',
    VIDEO_REALMEDIA : 'video/vnd.rn-realvideo',
    VIDEO_WEBM : 'video/webm',
    APPLICATION_UNKNOWN : 'unknown filetype',
    GENERAL_APPLICATION : 'application',
    GENERAL_AUDIO : 'audio',
    GENERAL_IMAGE : 'image',
    GENERAL_VIDEO : 'video',
    GENERAL_ANIMATION : 'animation'
}

mime_mimetype_string_lookup[ UNDETERMINED_WM ] = '{} or {}'.format( mime_mimetype_string_lookup[ AUDIO_WMA ], mime_mimetype_string_lookup[ VIDEO_WMV ] )
mime_mimetype_string_lookup[ UNDETERMINED_MP4 ] = '{} or {}'.format( mime_mimetype_string_lookup[ AUDIO_MP4 ], mime_mimetype_string_lookup[ VIDEO_MP4 ] )
mime_mimetype_string_lookup[ UNDETERMINED_PNG ] = '{} or {}'.format( mime_mimetype_string_lookup[ IMAGE_PNG ], mime_mimetype_string_lookup[ IMAGE_APNG ] )

mime_ext_lookup = {
    APPLICATION_HYDRUS_CLIENT_COLLECTION : '.collection',
    IMAGE_JPEG : '.jpg',
    IMAGE_PNG : '.png',
    IMAGE_APNG : '.png',
    IMAGE_GIF : '.gif',
    IMAGE_BMP : '.bmp',
    IMAGE_WEBP : '.webp',
    IMAGE_TIFF : '.tiff',
    IMAGE_ICON : '.ico',
    APPLICATION_FLASH : '.swf',
    APPLICATION_OCTET_STREAM : '.bin',
    APPLICATION_YAML : '.yaml',
    APPLICATION_JSON : '.json',
    APPLICATION_PDF : '.pdf',
    APPLICATION_PSD : '.psd',
    APPLICATION_CLIP : '.clip',
    APPLICATION_ZIP : '.zip',
    APPLICATION_RAR : '.rar',
    APPLICATION_7Z : '.7z',
    APPLICATION_HYDRUS_ENCRYPTED_ZIP : '.zip.encrypted',
    APPLICATION_HYDRUS_UPDATE_CONTENT : '',
    APPLICATION_HYDRUS_UPDATE_DEFINITIONS : '',
    AUDIO_M4A : '.m4a',
    AUDIO_MP3 : '.mp3',
    AUDIO_MKV : '.mkv',
    AUDIO_MP4 : '.mp4',
    AUDIO_OGG : '.ogg',
    AUDIO_REALMEDIA : '.ra',
    AUDIO_FLAC : '.flac',
    AUDIO_WAVE : '.wav',
    AUDIO_TRUEAUDIO : '.tta',
    AUDIO_WMA : '.wma',
    TEXT_HTML : '.html',
    TEXT_PLAIN : '.txt',
    VIDEO_AVI : '.avi',
    VIDEO_FLV : '.flv',
    VIDEO_MOV : '.mov',
    VIDEO_MP4 : '.mp4',
    VIDEO_MPEG : '.mpeg',
    VIDEO_WMV : '.wmv',
    VIDEO_MKV : '.mkv',
    VIDEO_OGV : '.ogv',
    VIDEO_REALMEDIA : '.rm',
    VIDEO_WEBM : '.webm',
    APPLICATION_UNKNOWN : ''
}

ALLOWED_MIME_EXTENSIONS = [ mime_ext_lookup[ mime ] for mime in ALLOWED_MIMES ]

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
SITE_TYPE_WATCHER = 16

site_type_string_lookup = {
    SITE_TYPE_DEFAULT : 'default',
    SITE_TYPE_BOORU : 'booru',
    SITE_TYPE_DEVIANT_ART : 'deviant art',
    SITE_TYPE_GIPHY : 'giphy',
    SITE_TYPE_HENTAI_FOUNDRY : 'hentai foundry',
    SITE_TYPE_HENTAI_FOUNDRY_ARTIST : 'hentai foundry artist',
    SITE_TYPE_HENTAI_FOUNDRY_ARTIST_PICTURES : 'hentai foundry artist pictures',
    SITE_TYPE_HENTAI_FOUNDRY_ARTIST_SCRAPS : 'hentai foundry artist scraps',
    SITE_TYPE_HENTAI_FOUNDRY_TAGS : 'hentai foundry tags',
    SITE_TYPE_NEWGROUNDS : 'newgrounds',
    SITE_TYPE_NEWGROUNDS_GAMES : 'newgrounds games',
    SITE_TYPE_NEWGROUNDS_MOVIES : 'newgrounds movies',
    SITE_TYPE_PIXIV : 'pixiv',
    SITE_TYPE_PIXIV_ARTIST_ID : 'pixiv artist id',
    SITE_TYPE_PIXIV_TAG : 'pixiv tag',
    SITE_TYPE_TUMBLR : 'tumblr',
    SITE_TYPE_WATCHER : 'watcher'
}

TIMESTAMP_TYPE_SOURCE = 0

TIMEZONE_GMT = 0
TIMEZONE_LOCAL = 1
TIMEZONE_OFFSET = 2

URL_TYPE_POST = 0
URL_TYPE_API = 1
URL_TYPE_FILE = 2
URL_TYPE_GALLERY = 3
URL_TYPE_WATCHABLE = 4
URL_TYPE_UNKNOWN = 5
URL_TYPE_NEXT = 6
URL_TYPE_DESIRED = 7
URL_TYPE_SOURCE = 8
URL_TYPE_SUB_GALLERY = 9

url_type_string_lookup = {
    URL_TYPE_POST : 'post url',
    URL_TYPE_API : 'api url',
    URL_TYPE_FILE : 'file url',
    URL_TYPE_GALLERY : 'gallery url',
    URL_TYPE_WATCHABLE : 'watchable url',
    URL_TYPE_UNKNOWN : 'unknown url',
    URL_TYPE_NEXT : 'next page url',
    URL_TYPE_DESIRED : 'downloadable/pursuable url',
    URL_TYPE_SUB_GALLERY : 'sub-gallery url (is queued even if creator found no post/file urls)'
}

# default options

DEFAULT_SERVER_ADMIN_PORT = 45870
DEFAULT_SERVICE_PORT = 45871

SERVER_ADMIN_KEY = b'server admin'

def construct_python_tuple( self, node ):
    
    return tuple( self.construct_sequence( node ) )
    
def represent_python_tuple( self, data ):
    
    return self.represent_sequence( 'tag:yaml.org,2002:python/tuple', data )
    

yaml.SafeLoader.add_constructor( 'tag:yaml.org,2002:python/tuple', construct_python_tuple )
yaml.SafeDumper.add_representer( tuple, represent_python_tuple )

# for some reason, sqlite doesn't parse to int before this, despite the column affinity
# it gives the register_converter function a bytestring :/
def integer_boolean_to_bool( integer_boolean ):
    
    return bool( int( integer_boolean ) )
    

# sqlite mod

sqlite3.register_adapter( dict, yaml.safe_dump )
sqlite3.register_adapter( list, yaml.safe_dump )
sqlite3.register_adapter( tuple, yaml.safe_dump )
sqlite3.register_adapter( bool, int )

sqlite3.register_converter( 'INTEGER_BOOLEAN', integer_boolean_to_bool )
sqlite3.register_converter( 'TEXT_YAML', yaml.safe_load )
