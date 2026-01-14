import os
import platform
import sqlite3
import sys

# if you ever remove this, don't forget it is in HydrusBoot as the third party library check
import yaml

# old method of getting frozen dir, doesn't work for symlinks looks like:
# BASE_DIR = getattr( sys, '_MEIPASS', None )

RUNNING_CLIENT = False
RUNNING_SERVER = False

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

if PLATFORM_WINDOWS:
    NICE_PLATFORM_STRING = 'Windows'
elif PLATFORM_MACOS:
    NICE_PLATFORM_STRING = 'macOS'
elif PLATFORM_LINUX:
    NICE_PLATFORM_STRING = 'Linux'
elif PLATFORM_HAIKU:
    NICE_PLATFORM_STRING = 'Haiku'

NICE_ARCHITECTURE_STRING = platform.machine()

if NICE_ARCHITECTURE_STRING == 'AMD64':
    
    NICE_ARCHITECTURE_STRING = 'x86_64'
    

RUNNING_FROM_MACOS_APP = os.path.exists( os.path.join( BASE_DIR, 'running_from_app' ) )

# I used to check argv[0], but it is unreliable
# sys.argv[0].endswith( '.py' ) or sys.argv[0].endswith( '.pyw' )
RUNNING_FROM_SOURCE = not ( RUNNING_FROM_FROZEN_BUILD or RUNNING_FROM_MACOS_APP )

if RUNNING_FROM_SOURCE:
    NICE_RUNNING_AS_STRING = 'from source'
elif RUNNING_FROM_FROZEN_BUILD:
    NICE_RUNNING_AS_STRING = 'from frozen build'
elif RUNNING_FROM_MACOS_APP:
    NICE_RUNNING_AS_STRING = 'from App'

BIN_DIR = os.path.join( BASE_DIR, 'bin' )
HELP_DIR = os.path.join( BASE_DIR, 'help' )
INCLUDE_DIR = os.path.join( BASE_DIR, 'include' )

DEFAULT_DB_DIR = os.path.join( BASE_DIR, 'db' )

if PLATFORM_MACOS:
    
    desired_userpath_db_dir = os.path.join( '~', 'Library', 'Hydrus' )
    
else:
    
    desired_userpath_db_dir = os.path.join( '~', 'Hydrus' )
    

USERPATH_DB_DIR = os.path.expanduser( desired_userpath_db_dir )

if USERPATH_DB_DIR == desired_userpath_db_dir:
    
    # could not figure it out, probably a crazy user situation atm
    
    USERPATH_DB_DIR = None
    

WE_SWITCHED_TO_USERPATH = False

LICENSE_PATH = os.path.join( BASE_DIR, 'license.txt' )

#

options = {}

# Misc

NETWORK_VERSION = 20
SOFTWARE_VERSION = 655
CLIENT_API_VERSION = 84

SERVER_THUMBNAIL_DIMENSIONS = ( 200, 200 )

HYDRUS_KEY_LENGTH = 32

READ_BLOCK_SIZE = 256 * 1024

lifetimes = [ ( 'one month', 30 * 86400 ), ( 'three months', 3 * 30 * 86400 ), ( 'six months', 6 * 30 * 86400 ), ( 'one year', 365 * 86400 ), ( 'two years', 2 * 365 * 86400 ), ( 'five years', 5 * 365 * 86400 ), ( 'does not expire', None ) ]

USERPATH_SVG_ICON = 'star_shapes'

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
CONTENT_MERGE_ACTION_NONE = 3
CONTENT_MERGE_ACTION_ADD_MOVE = 4

content_merge_string_lookup = {
    CONTENT_MERGE_ACTION_COPY : 'copy from worse to better',
    CONTENT_MERGE_ACTION_MOVE : 'move from worse to better',
    CONTENT_MERGE_ACTION_TWO_WAY_MERGE : 'copy in both directions',
    CONTENT_MERGE_ACTION_NONE : 'make no change'
}

content_number_merge_string_lookup = {
    CONTENT_MERGE_ACTION_COPY : 'add worse to better',
    CONTENT_MERGE_ACTION_MOVE : 'take from worse and add to better',
    CONTENT_MERGE_ACTION_TWO_WAY_MERGE : 'add in both directions',
    CONTENT_MERGE_ACTION_NONE : 'make no change'
}

content_modified_date_merge_string_lookup = {
    CONTENT_MERGE_ACTION_COPY : 'earlier worse overwrites later better',
    CONTENT_MERGE_ACTION_TWO_WAY_MERGE : 'both get earliest',
    CONTENT_MERGE_ACTION_NONE : 'make no change'
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
CONTENT_TYPE_HTTP_HEADERS = 22

content_type_string_lookup = {
    CONTENT_TYPE_MAPPINGS : 'tag mappings',
    CONTENT_TYPE_TAG_SIBLINGS : 'tag siblings',
    CONTENT_TYPE_TAG_PARENTS : 'tag parents',
    CONTENT_TYPE_FILES : 'files',
    CONTENT_TYPE_RATINGS : 'ratings',
    CONTENT_TYPE_MAPPING : 'tag mapping',
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
    CONTENT_TYPE_TAG : 'tag',
    CONTENT_TYPE_DEFINITIONS : 'definitions',
    CONTENT_TYPE_HTTP_HEADERS : 'http headers'
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
CONTENT_UPDATE_MOVE = 20
CONTENT_UPDATE_DELETE_FROM_SOURCE_AFTER_MIGRATE = 21
CONTENT_UPDATE_MOVE_MERGE = 22

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
    CONTENT_UPDATE_DECREMENT : 'decrement',
    CONTENT_UPDATE_MOVE : 'move (if not already in destination)',
    CONTENT_UPDATE_MOVE_MERGE : 'move (even if already in destination)'
}

DEFINITIONS_TYPE_HASHES = 0
DEFINITIONS_TYPE_TAGS = 1

# TODO: I should probably split this into status and action, but keeping the same enum stuff; this is confusing
DUPLICATE_POTENTIAL = 0
DUPLICATE_FALSE_POSITIVE = 1
DUPLICATE_SAME_QUALITY = 2
DUPLICATE_ALTERNATE = 3
DUPLICATE_BETTER = 4
DUPLICATE_SMALLER_BETTER = 5
DUPLICATE_LARGER_BETTER = 6
DUPLICATE_WORSE = 7 # aieeeeeeee
DUPLICATE_MEMBER = 8
DUPLICATE_KING = 9
DUPLICATE_CONFIRMED_ALTERNATE = 10

duplicate_type_string_lookup = {
    DUPLICATE_POTENTIAL : 'potential duplicates',
    DUPLICATE_FALSE_POSITIVE : 'not related/false positive',
    DUPLICATE_SAME_QUALITY : 'same quality',
    DUPLICATE_ALTERNATE : 'alternates',
    DUPLICATE_BETTER : 'this is a better duplicate',
    DUPLICATE_SMALLER_BETTER : 'smaller hash_id is a better duplicate',
    DUPLICATE_LARGER_BETTER : 'larger hash_id is a better duplicate',
    DUPLICATE_WORSE : 'this is a worse duplicate',
    DUPLICATE_MEMBER : 'duplicates',
    DUPLICATE_KING : 'the best quality duplicate',
    DUPLICATE_CONFIRMED_ALTERNATE : 'confirmed alternates'
}

duplicate_type_auto_resolution_action_description_lookup = {
    DUPLICATE_FALSE_POSITIVE : 'set as not related/false positive',
    DUPLICATE_SAME_QUALITY : 'set as same quality',
    DUPLICATE_ALTERNATE : 'set as alternates',
    DUPLICATE_BETTER : 'set as duplicates--A better',
    DUPLICATE_WORSE : 'set as duplicates--B better'
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

filter_black_white_str_lookup = {
    FILTER_WHITELIST : 'whitelist',
    FILTER_BLACKLIST : 'blacklist'
}

HYDRUS_CLIENT = 0
HYDRUS_SERVER = 1
HYDRUS_TEST = 2

LOGICAL_OPERATOR_ALL = 0
LOGICAL_OPERATOR_ANY = 1
LOGICAL_OPERATOR_ONLY = 2

MAINTENANCE_IDLE = 0
MAINTENANCE_SHUTDOWN = 1
MAINTENANCE_FORCED = 2
MAINTENANCE_ACTIVE = 3

NICE_RESOLUTIONS = {
    ( 640, 480 ) : '480p',
    ( 1280, 720 ) : '720p',
    ( 1920, 1080 ) : '1080p',
    ( 3840, 2160 ) : '2160p',
    ( 720, 1280 ) : 'vertical 720p',
    ( 1080, 1920 ) : 'vertical 1080p',
    ( 2160, 3840 ) : 'vertical 2160p'
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
HYDRUS_LOCAL_FILE_STORAGE = 15
TEST_SERVICE = 16
LOCAL_NOTES = 17
CLIENT_API_SERVICE = 18
COMBINED_DELETED_FILE = 19
LOCAL_FILE_UPDATE_DOMAIN = 20
COMBINED_LOCAL_FILE_DOMAINS = 21
LOCAL_RATING_INCDEC = 22
SERVER_ADMIN = 99
NULL_SERVICE = 100

service_string_lookup = {
    TAG_REPOSITORY : 'hydrus tag repository',
    FILE_REPOSITORY : 'hydrus file repository',
    LOCAL_FILE_DOMAIN : 'local file domain',
    LOCAL_FILE_TRASH_DOMAIN : 'local trash file domain',
    LOCAL_FILE_UPDATE_DOMAIN : 'local update file domain',
    HYDRUS_LOCAL_FILE_STORAGE : 'virtual combined local file domain',
    COMBINED_LOCAL_FILE_DOMAINS : 'virtual combined local media domain',
    MESSAGE_DEPOT : 'hydrus message depot',
    LOCAL_TAG : 'local tag domain',
    LOCAL_RATING_INCDEC : 'local inc/dec rating service',
    LOCAL_RATING_NUMERICAL : 'local numerical rating service',
    LOCAL_RATING_LIKE : 'local like/dislike rating service',
    RATING_NUMERICAL_REPOSITORY : 'hydrus numerical rating repository',
    RATING_LIKE_REPOSITORY : 'hydrus like/dislike rating repository',
    COMBINED_TAG : 'virtual combined tag domain',
    COMBINED_FILE : 'virtual combined file domain',
    LOCAL_BOORU : 'client local booru',
    CLIENT_API_SERVICE : 'client api',
    IPFS : 'ipfs daemon',
    TEST_SERVICE : 'test service',
    LOCAL_NOTES : 'local file notes service',
    SERVER_ADMIN : 'hydrus server administration service',
    COMBINED_DELETED_FILE : 'virtual deleted file service',
    NULL_SERVICE : 'null service'
}

service_string_lookup_short = {
    TAG_REPOSITORY : 'tag repository',
    FILE_REPOSITORY : 'file repository',
    LOCAL_FILE_DOMAIN : 'local file domain',
    LOCAL_FILE_TRASH_DOMAIN : 'trash',
    LOCAL_FILE_UPDATE_DOMAIN : 'local update file domain',
    HYDRUS_LOCAL_FILE_STORAGE : 'hydrus local file storage',
    COMBINED_LOCAL_FILE_DOMAINS : 'combined local file domains',
    MESSAGE_DEPOT : 'hydrus message depot',
    LOCAL_TAG : 'local tag domain',
    LOCAL_RATING_INCDEC : 'inc/dec ratings',
    LOCAL_RATING_NUMERICAL : 'numerical ratings',
    LOCAL_RATING_LIKE : 'like/dislike ratings',
    RATING_NUMERICAL_REPOSITORY : 'hydrus numerical rating repository',
    RATING_LIKE_REPOSITORY : 'hydrus like/dislike rating repository',
    COMBINED_TAG : 'all known tags',
    COMBINED_FILE : 'all known files',
    LOCAL_BOORU : 'local booru',
    CLIENT_API_SERVICE : 'client api',
    IPFS : 'ipfs',
    TEST_SERVICE : 'test service',
    LOCAL_NOTES : 'notes',
    SERVER_ADMIN : 'hydrus server administration',
    COMBINED_DELETED_FILE : 'virtual deleted file service',
    NULL_SERVICE : 'null service'
}

service_description_lookup = {
    TAG_REPOSITORY : 'A repository of tag mapping data (tag-file pairs) stored on a remote server. Clients can sync with it, which means to download all the file hashes, tags, and mappings it knows of and synchronise that to local metadata storage. Clients can also upload new mapping data, which will in turn be shared to all users.\n\nThe "all known tags" service is a union of all local tag domains and remote tag repositories.',
    FILE_REPOSITORY : 'A repository of files stored on a remote server. Clients can sync with it, which means to regularly download all the file hashes and thumbnails. You can search it like any other file domain, viewing the thumbnails, and download files. Clients can also upload new files, which will in turn be shared to all users.',
    LOCAL_FILE_DOMAIN : 'This stores media files you have imported. You can have multiple local file domains, and files may be in multiple local file domains at once. Each domain is completely isolated from one another when you perform a file or tag search (if your search page is pointed at A, you will not get any file search results or tag autocomplete suggestions from B).',
    LOCAL_FILE_TRASH_DOMAIN : 'This is where your files go when they have been removed from all your local file domains. It is a waiting area to allow for undeletes of mistakes. When files are deleted from this place, they are physically deleted.',
    LOCAL_FILE_UPDATE_DOMAIN : 'This holds repository update files if you decide to sync with a file or tag repository. It is full of zipped up JSON and is not covered by "combined local file domains" like the normal local file domains. You can generally ignore it.',
    HYDRUS_LOCAL_FILE_STORAGE : 'This represents all files currently tracked and stored in your database. If a file is in here, it is either in "repository updates", "combined local file domains", or "trash", and it should be loadable from disk.\n\nWhen a file is deleted from the trash, it also leaves this domain and is scheduled to be physically deleted--which usually happens within a few seconds.',
    COMBINED_LOCAL_FILE_DOMAINS : 'This represents all files currently in any of your local file domains. You start with only "my files", but if you add more, this is a convenient umbrella that unions all of them with efficient search tech. When a file is deleted from all of its local file domains, it leaves this service and enters the trash.',
    MESSAGE_DEPOT : 'You should not see this text',
    LOCAL_TAG : 'This stores tag mappings (tag-file pairs) that you have added/imported. You can have multiple local tag domains, and the exact same mappings map appear in multiple domains.\n\nTags are not removed when files are deleted, and if you later re-import the file, you will see it still has its tags.\n\nThe "all known tags" service is a union of all local tag services and tag repositories.',
    LOCAL_RATING_INCDEC : 'This stores inc/dec ratings.\n\nRatings are not removed when files are deleted, and if you later re-import the file, you will see it still has its ratings.',
    LOCAL_RATING_NUMERICAL : 'This stores numerical ratings.\n\nRatings are not removed when files are deleted, and if you later re-import the file, you will see it still has its ratings.',
    LOCAL_RATING_LIKE : 'This stores like/dislike ratings.\n\nRatings are not removed when files are deleted, and if you later re-import the file, you will see it still has its ratings.',
    RATING_NUMERICAL_REPOSITORY : 'You should not see this text',
    RATING_LIKE_REPOSITORY : 'You should not see this text',
    COMBINED_TAG : 'This is a union of all your local tag domains and remote tag repositories.',
    COMBINED_FILE : 'This is a special view on a tag service. It will deliver results without any cross-reference with a known file service, and thus if the file is tagged on a service, you will see it whether you have it, had it, or have never had it.',
    LOCAL_BOORU : 'You should not see this text',
    CLIENT_API_SERVICE : 'The Client API.',
    IPFS : 'A remote listing of files stored/pinned on an IPFS daemon. You can search it like any other file domain.',
    TEST_SERVICE : 'You should not see this text',
    LOCAL_NOTES : 'This stores your file notes.\n\nNotes are not removed when files are deleted, and if you later re-import the file, you will see it still has its notes.',
    SERVER_ADMIN : 'This is an interface to a server that allows editing of admin accounts and which remote services are running.',
    COMBINED_DELETED_FILE : 'This represents all the files that have ever been deleted from any location. It is for advanced technical jobs, and you can generally ignore it.',
    NULL_SERVICE : 'You should not see this text'
}

SPECIFIC_LOCAL_FILE_SERVICES = ( LOCAL_FILE_DOMAIN, LOCAL_FILE_UPDATE_DOMAIN, LOCAL_FILE_TRASH_DOMAIN )
LOCAL_FILE_SERVICES = SPECIFIC_LOCAL_FILE_SERVICES + ( HYDRUS_LOCAL_FILE_STORAGE, COMBINED_LOCAL_FILE_DOMAINS )
LOCAL_FILE_SERVICES_IN_NICE_ORDER = ( LOCAL_FILE_DOMAIN, COMBINED_LOCAL_FILE_DOMAINS, LOCAL_FILE_TRASH_DOMAIN, LOCAL_FILE_UPDATE_DOMAIN, HYDRUS_LOCAL_FILE_STORAGE )
LOCAL_TAG_SERVICES = ( LOCAL_TAG, )

LOCAL_SERVICES = LOCAL_FILE_SERVICES + LOCAL_TAG_SERVICES + ( LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, LOCAL_RATING_INCDEC, LOCAL_NOTES, CLIENT_API_SERVICE )

STAR_RATINGS_SERVICES = ( LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY )
LOCAL_RATINGS_SERVICES = ( LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, LOCAL_RATING_INCDEC )
RATINGS_SERVICES = ( LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, LOCAL_RATING_INCDEC, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY )
REPOSITORIES = ( TAG_REPOSITORY, FILE_REPOSITORY, RATING_LIKE_REPOSITORY, RATING_NUMERICAL_REPOSITORY )
RESTRICTED_SERVICES = REPOSITORIES + ( SERVER_ADMIN, MESSAGE_DEPOT )
REMOTE_SERVICES = RESTRICTED_SERVICES + ( IPFS, )
REMOTE_FILE_SERVICES = ( FILE_REPOSITORY, IPFS )
REAL_FILE_SERVICES = LOCAL_FILE_SERVICES + ( COMBINED_DELETED_FILE, ) + REMOTE_FILE_SERVICES
REAL_TAG_SERVICES = ( LOCAL_TAG, TAG_REPOSITORY )
ADDREMOVABLE_SERVICES = ( LOCAL_TAG, LOCAL_FILE_DOMAIN, LOCAL_RATING_LIKE, LOCAL_RATING_NUMERICAL, LOCAL_RATING_INCDEC, FILE_REPOSITORY, TAG_REPOSITORY, SERVER_ADMIN, IPFS )
MUST_HAVE_AT_LEAST_ONE_SERVICES = ( LOCAL_TAG, LOCAL_FILE_DOMAIN )
MUST_BE_EMPTY_OF_FILES_SERVICES = ( LOCAL_FILE_DOMAIN, )

FILE_SERVICES_WITH_SPECIFIC_MAPPING_CACHES = REAL_FILE_SERVICES
FILE_SERVICES_WITH_SPECIFIC_TAG_LOOKUP_CACHES = ( HYDRUS_LOCAL_FILE_STORAGE, COMBINED_DELETED_FILE, FILE_REPOSITORY, IPFS )

FILE_SERVICES_COVERED_BY_COMBINED_LOCAL_FILE_DOMAINS = ( LOCAL_FILE_DOMAIN, )
FILE_SERVICES_COVERED_BY_HYDRUS_LOCAL_FILE_STORAGE = ( COMBINED_LOCAL_FILE_DOMAINS, LOCAL_FILE_DOMAIN, LOCAL_FILE_UPDATE_DOMAIN, LOCAL_FILE_TRASH_DOMAIN )
FILE_SERVICES_COVERED_BY_COMBINED_DELETED_FILE = ( COMBINED_LOCAL_FILE_DOMAINS, LOCAL_FILE_DOMAIN, LOCAL_FILE_UPDATE_DOMAIN, FILE_REPOSITORY, IPFS )

ALL_SERVICES = REMOTE_SERVICES + LOCAL_SERVICES + ( COMBINED_FILE, COMBINED_TAG, COMBINED_DELETED_FILE )
ALL_TAG_SERVICES = REAL_TAG_SERVICES + ( COMBINED_TAG, )
ALL_FILE_SERVICES = REAL_FILE_SERVICES + ( COMBINED_FILE, )

FILE_SERVICES_WITH_NO_DELETE_RECORD = ( COMBINED_FILE, LOCAL_FILE_TRASH_DOMAIN, COMBINED_DELETED_FILE )
FILE_SERVICES_WITH_DELETE_RECORD = tuple( ( t for t in REAL_FILE_SERVICES if t not in FILE_SERVICES_WITH_NO_DELETE_RECORD ) )

SERVICES_WITH_THUMBNAILS = [ FILE_REPOSITORY, LOCAL_FILE_DOMAIN ]

SERVICE_TYPES_TO_CONTENT_TYPES = {
    FILE_REPOSITORY : ( CONTENT_TYPE_FILES, ),
    LOCAL_FILE_DOMAIN : ( CONTENT_TYPE_FILES, ),
    LOCAL_FILE_UPDATE_DOMAIN : ( CONTENT_TYPE_FILES, ),
    LOCAL_FILE_TRASH_DOMAIN : ( CONTENT_TYPE_FILES, ),
    COMBINED_LOCAL_FILE_DOMAINS : ( CONTENT_TYPE_FILES, ),
    HYDRUS_LOCAL_FILE_STORAGE : ( CONTENT_TYPE_FILES, ),
    IPFS : ( CONTENT_TYPE_FILES, ),
    TAG_REPOSITORY : ( CONTENT_TYPE_MAPPINGS, CONTENT_TYPE_TAG_PARENTS, CONTENT_TYPE_TAG_SIBLINGS ),
    LOCAL_TAG : ( CONTENT_TYPE_MAPPINGS, CONTENT_TYPE_TAG_PARENTS, CONTENT_TYPE_TAG_SIBLINGS ),
    LOCAL_RATING_LIKE : ( CONTENT_TYPE_RATINGS, ),
    LOCAL_RATING_NUMERICAL : ( CONTENT_TYPE_RATINGS, ),
    LOCAL_RATING_INCDEC : ( CONTENT_TYPE_RATINGS, )
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
SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS = 17
SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS = 18
SERVICE_INFO_NUM_PENDING_TAG_PARENTS = 19
SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS = 20
SERVICE_INFO_NUM_SHARES = 21
SERVICE_INFO_NUM_VIEWABLE_FILES = 22
SERVICE_INFO_NUM_TAG_SIBLINGS = 23
SERVICE_INFO_NUM_TAG_PARENTS = 24
SERVICE_INFO_NUM_DELETED_TAG_SIBLINGS = 25
SERVICE_INFO_NUM_DELETED_TAG_PARENTS = 26
SERVICE_INFO_NUM_ACTIONABLE_FILE_ADD_PETITIONS = 27
SERVICE_INFO_NUM_ACTIONABLE_FILE_DELETE_PETITIONS = 28
SERVICE_INFO_NUM_ACTIONABLE_MAPPING_ADD_PETITIONS = 29
SERVICE_INFO_NUM_ACTIONABLE_MAPPING_DELETE_PETITIONS = 30
SERVICE_INFO_NUM_ACTIONABLE_SIBLING_ADD_PETITIONS = 31
SERVICE_INFO_NUM_ACTIONABLE_SIBLING_DELETE_PETITIONS = 32
SERVICE_INFO_NUM_ACTIONABLE_PARENT_ADD_PETITIONS = 33
SERVICE_INFO_NUM_ACTIONABLE_PARENT_DELETE_PETITIONS = 34
SERVICE_INFO_NUM_FILE_HASHES = 35
SERVICE_INFO_NUM_PENDING_FILES = 36
SERVICE_INFO_NUM_PETITIONED_FILES = 37

service_info_enum_str_lookup = {
    SERVICE_INFO_NUM_FILE_HASHES : 'number of file hashes',
    SERVICE_INFO_NUM_FILES : 'number of files',
    SERVICE_INFO_NUM_INBOX : 'number in inbox',
    SERVICE_INFO_NUM_LOCAL : 'number of local files',
    SERVICE_INFO_NUM_MAPPINGS : 'number of mappings',
    SERVICE_INFO_NUM_DELETED_MAPPINGS : 'number of deleted mappings',
    SERVICE_INFO_NUM_DELETED_FILES : 'number of deleted files',
    SERVICE_INFO_NUM_THUMBNAILS : 'number of thumbnails',
    SERVICE_INFO_NUM_THUMBNAILS_LOCAL : 'number of local thumbnails',
    SERVICE_INFO_TOTAL_SIZE : 'total size',
    SERVICE_INFO_NUM_NAMESPACES : 'number of namespaces',
    SERVICE_INFO_NUM_TAGS : 'number of tags',
    SERVICE_INFO_NUM_PENDING : 'number pending',
    SERVICE_INFO_NUM_CONVERSATIONS : 'number of conversations',
    SERVICE_INFO_NUM_UNREAD : 'number of unread conversations',
    SERVICE_INFO_NUM_DRAFTS : 'number of drafts',
    SERVICE_INFO_NUM_PENDING_MAPPINGS : 'number of pending mappings',
    SERVICE_INFO_NUM_PETITIONED_MAPPINGS : 'number of petitioned mappings',
    SERVICE_INFO_NUM_PENDING_FILES : 'number of pending files',
    SERVICE_INFO_NUM_PETITIONED_FILES : 'number of petitioned files',
    SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS : 'number of pending tag siblings',
    SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS : 'number of petitioned tag siblings',
    SERVICE_INFO_NUM_PENDING_TAG_PARENTS : 'number of pending tag parents',
    SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS : 'number of petitioned tag parents',
    SERVICE_INFO_NUM_SHARES : 'number of shares',
    SERVICE_INFO_NUM_VIEWABLE_FILES : 'number of viewable files',
    SERVICE_INFO_NUM_TAG_SIBLINGS : 'number of tag siblings',
    SERVICE_INFO_NUM_TAG_PARENTS : 'number of tag parents',
    SERVICE_INFO_NUM_DELETED_TAG_SIBLINGS : 'number of deleted tag siblings',
    SERVICE_INFO_NUM_DELETED_TAG_PARENTS : 'number of deleted tag parents',
    SERVICE_INFO_NUM_ACTIONABLE_FILE_ADD_PETITIONS : 'number of actionable add-file petitions',
    SERVICE_INFO_NUM_ACTIONABLE_FILE_DELETE_PETITIONS : 'number of actionable delete-file petitions',
    SERVICE_INFO_NUM_ACTIONABLE_MAPPING_ADD_PETITIONS : 'number of actionable add-mapping petitions',
    SERVICE_INFO_NUM_ACTIONABLE_MAPPING_DELETE_PETITIONS : 'number of actionable delete-mapping petitions',
    SERVICE_INFO_NUM_ACTIONABLE_SIBLING_ADD_PETITIONS : 'number of actionable add-sibling petitions',
    SERVICE_INFO_NUM_ACTIONABLE_SIBLING_DELETE_PETITIONS : 'number of actionable delete-sibling petitions',
    SERVICE_INFO_NUM_ACTIONABLE_PARENT_ADD_PETITIONS : 'number of actionable add-parent petitions',
    SERVICE_INFO_NUM_ACTIONABLE_PARENT_DELETE_PETITIONS : 'number of actionable delete-parent petitions'
}

FILE_REPOSITORY_SERVICE_INFO_TYPES = [
    SERVICE_INFO_NUM_FILE_HASHES,
    SERVICE_INFO_NUM_FILES,
    SERVICE_INFO_NUM_DELETED_FILES,
    SERVICE_INFO_NUM_PENDING_FILES,
    SERVICE_INFO_NUM_PETITIONED_FILES,
    SERVICE_INFO_NUM_ACTIONABLE_FILE_ADD_PETITIONS,
    SERVICE_INFO_NUM_ACTIONABLE_FILE_DELETE_PETITIONS,
]

TAG_REPOSITORY_SERVICE_INFO_TYPES = [
    SERVICE_INFO_NUM_FILE_HASHES,
    SERVICE_INFO_NUM_TAGS,
    SERVICE_INFO_NUM_MAPPINGS,
    SERVICE_INFO_NUM_DELETED_MAPPINGS,
    SERVICE_INFO_NUM_PENDING_MAPPINGS,
    SERVICE_INFO_NUM_PETITIONED_MAPPINGS,
    SERVICE_INFO_NUM_ACTIONABLE_MAPPING_ADD_PETITIONS,
    SERVICE_INFO_NUM_ACTIONABLE_MAPPING_DELETE_PETITIONS,
    SERVICE_INFO_NUM_TAG_SIBLINGS,
    SERVICE_INFO_NUM_DELETED_TAG_SIBLINGS,
    SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS,
    SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS,
    SERVICE_INFO_NUM_ACTIONABLE_SIBLING_ADD_PETITIONS,
    SERVICE_INFO_NUM_ACTIONABLE_SIBLING_DELETE_PETITIONS,
    SERVICE_INFO_NUM_TAG_PARENTS,
    SERVICE_INFO_NUM_DELETED_TAG_PARENTS,
    SERVICE_INFO_NUM_PENDING_TAG_PARENTS,
    SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS,
    SERVICE_INFO_NUM_ACTIONABLE_PARENT_ADD_PETITIONS,
    SERVICE_INFO_NUM_ACTIONABLE_PARENT_DELETE_PETITIONS
]

SERVICE_UPDATE_DELETE_PENDING = 0
SERVICE_UPDATE_RESET = 1

TIMESTAMP_TYPE_MODIFIED_DOMAIN = 0
TIMESTAMP_TYPE_MODIFIED_FILE = 1 # simple
TIMESTAMP_TYPE_MODIFIED_AGGREGATE = 2 # virtual
TIMESTAMP_TYPE_IMPORTED = 3
TIMESTAMP_TYPE_DELETED = 4
TIMESTAMP_TYPE_ARCHIVED = 5 # simple
TIMESTAMP_TYPE_LAST_VIEWED = 6
TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED = 7

timestamp_type_str_lookup = {
    TIMESTAMP_TYPE_MODIFIED_DOMAIN : 'domain modified time',
    TIMESTAMP_TYPE_MODIFIED_FILE : 'file modified time',
    TIMESTAMP_TYPE_MODIFIED_AGGREGATE : 'aggregate modified time',
    TIMESTAMP_TYPE_IMPORTED : 'imported time',
    TIMESTAMP_TYPE_DELETED : 'deleted time',
    TIMESTAMP_TYPE_ARCHIVED : 'archived time',
    TIMESTAMP_TYPE_LAST_VIEWED : 'last viewed time',
    TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED : 'previous imported time (for undelete)'
}

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
ANIMATION_GIF = 3
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
ANIMATION_APNG = 23
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
APPLICATION_WINDOWS_EXE = 52
AUDIO_WAVPACK = 53
APPLICATION_SAI2 = 54
APPLICATION_KRITA = 55
IMAGE_SVG = 56
APPLICATION_XCF = 57
APPLICATION_GZIP = 58
GENERAL_APPLICATION_ARCHIVE = 59
GENERAL_IMAGE_PROJECT = 60
IMAGE_HEIF = 61
IMAGE_HEIF_SEQUENCE = 62
IMAGE_HEIC = 63
IMAGE_HEIC_SEQUENCE = 64
IMAGE_AVIF = 65
IMAGE_AVIF_SEQUENCE = 66
UNDETERMINED_GIF = 67
IMAGE_GIF = 68
APPLICATION_PROCREATE = 69
IMAGE_QOI = 70
APPLICATION_EPUB = 71
APPLICATION_DJVU = 72
APPLICATION_CBZ = 73
ANIMATION_UGOIRA = 74
APPLICATION_RTF = 75
APPLICATION_DOCX = 76
APPLICATION_XLSX = 77
APPLICATION_PPTX = 78
UNDETERMINED_OLE = 79
APPLICATION_DOC = 80
APPLICATION_XLS = 81
APPLICATION_PPT = 82
ANIMATION_WEBP = 83
UNDETERMINED_WEBP = 84
IMAGE_JXL = 85
APPLICATION_PAINT_DOT_NET = 86
UNDETERMINED_JXL = 87
ANIMATION_JXL = 88
APPLICATION_OCTET_STREAM = 100
APPLICATION_UNKNOWN = 101

GENERAL_FILETYPES = {
    GENERAL_APPLICATION,
    GENERAL_AUDIO,
    GENERAL_IMAGE,
    GENERAL_VIDEO,
    GENERAL_ANIMATION,
    GENERAL_APPLICATION_ARCHIVE,
    GENERAL_IMAGE_PROJECT
}

SEARCHABLE_MIMES = {
    IMAGE_JPEG,
    IMAGE_PNG,
    ANIMATION_APNG,
    IMAGE_GIF,
    ANIMATION_GIF,
    IMAGE_WEBP,
    ANIMATION_WEBP,
    IMAGE_TIFF,
    IMAGE_QOI,
    IMAGE_ICON,
    IMAGE_SVG,
    IMAGE_HEIF,
    IMAGE_HEIF_SEQUENCE,
    IMAGE_HEIC,
    IMAGE_HEIC_SEQUENCE,
    IMAGE_AVIF,
    IMAGE_AVIF_SEQUENCE,
    IMAGE_BMP,
    IMAGE_JXL,
    ANIMATION_JXL,
    ANIMATION_UGOIRA,
    APPLICATION_FLASH,
    VIDEO_AVI,
    VIDEO_FLV,
    VIDEO_MOV,
    VIDEO_MP4,
    VIDEO_MKV,
    VIDEO_REALMEDIA,
    VIDEO_WEBM,
    VIDEO_OGV,
    VIDEO_MPEG,
    APPLICATION_CBZ,
    APPLICATION_CLIP,
    APPLICATION_PSD,
    APPLICATION_SAI2,
    APPLICATION_KRITA,
    APPLICATION_XCF,
    APPLICATION_PROCREATE,
    APPLICATION_PDF,
    APPLICATION_DOCX,
    APPLICATION_XLSX,
    APPLICATION_PPTX,
    APPLICATION_DOC,
    APPLICATION_XLS,
    APPLICATION_PPT,
    APPLICATION_EPUB,
    APPLICATION_DJVU,
    APPLICATION_PAINT_DOT_NET,
    APPLICATION_RTF,
    APPLICATION_ZIP,
    APPLICATION_RAR,
    APPLICATION_7Z,
    APPLICATION_GZIP,
    AUDIO_M4A,
    AUDIO_MP3,
    AUDIO_REALMEDIA,
    AUDIO_OGG,
    AUDIO_FLAC,
    AUDIO_WAVE,
    AUDIO_TRUEAUDIO,
    AUDIO_WMA,
    VIDEO_WMV,
    AUDIO_MKV,
    AUDIO_MP4,
    AUDIO_WAVPACK
}

ALLOWED_MIMES = set( SEARCHABLE_MIMES ).union( { APPLICATION_HYDRUS_UPDATE_CONTENT, APPLICATION_HYDRUS_UPDATE_DEFINITIONS } )

DECOMPRESSION_BOMB_IMAGES = {
    IMAGE_JPEG,
    IMAGE_PNG
}

# Keep these as ordered lists, bro--we use that in a couple places in UI
IMAGES = [
    IMAGE_JPEG,
    IMAGE_PNG,
    IMAGE_GIF,
    IMAGE_WEBP,
    IMAGE_JXL,
    IMAGE_AVIF,
    IMAGE_BMP,
    IMAGE_HEIC,
    IMAGE_HEIF,
    IMAGE_ICON,
    IMAGE_QOI,
    IMAGE_TIFF
]

ANIMATIONS = [
    ANIMATION_GIF,
    ANIMATION_APNG,
    ANIMATION_WEBP,
    ANIMATION_JXL,
    IMAGE_AVIF_SEQUENCE,
    IMAGE_HEIC_SEQUENCE,
    IMAGE_HEIF_SEQUENCE,
    ANIMATION_UGOIRA
]

VIEWABLE_ANIMATIONS = [
    ANIMATION_GIF,
    ANIMATION_APNG,
    ANIMATION_WEBP,
    ANIMATION_JXL,
    IMAGE_AVIF_SEQUENCE,
    IMAGE_HEIC_SEQUENCE,
    IMAGE_HEIF_SEQUENCE,
    ANIMATION_UGOIRA
]

HEIF_TYPE_SEQUENCES = [
    IMAGE_HEIC_SEQUENCE,
    IMAGE_HEIF_SEQUENCE
]

AUDIO = [
    AUDIO_MP3,
    AUDIO_OGG,
    AUDIO_FLAC,
    AUDIO_M4A,
    AUDIO_MKV,
    AUDIO_MP4,
    AUDIO_REALMEDIA,
    AUDIO_TRUEAUDIO,
    AUDIO_WAVE,
    AUDIO_WAVPACK,
    AUDIO_WMA
]

VIDEO = [
    VIDEO_MP4,
    VIDEO_WEBM,
    VIDEO_MKV,
    VIDEO_AVI,
    VIDEO_FLV,
    VIDEO_MOV,
    VIDEO_MPEG,
    VIDEO_OGV,
    VIDEO_REALMEDIA,
    VIDEO_WMV
]

APPLICATIONS = [
    APPLICATION_FLASH,
    APPLICATION_PDF,
    APPLICATION_EPUB,
    APPLICATION_DJVU,
    APPLICATION_DOCX,
    APPLICATION_XLSX,
    APPLICATION_PPTX,
    APPLICATION_DOC,
    APPLICATION_XLS,
    APPLICATION_PPT,
    APPLICATION_RTF
]

IMAGE_PROJECT_FILES = [
    APPLICATION_CLIP,
    APPLICATION_KRITA,
    APPLICATION_PAINT_DOT_NET,
    APPLICATION_PROCREATE,
    APPLICATION_PSD,
    APPLICATION_SAI2,
    IMAGE_SVG,
    APPLICATION_XCF
]

ARCHIVES = [
    APPLICATION_CBZ,
    APPLICATION_7Z,
    APPLICATION_GZIP,
    APPLICATION_RAR,
    APPLICATION_ZIP
]

VIEWABLE_IMAGE_PROJECT_FILES = { APPLICATION_PSD, APPLICATION_KRITA }

# zip files that have a `mimetype` file inside
OPEN_DOCUMENT_ZIPS = { APPLICATION_KRITA, APPLICATION_EPUB }

# zip files that have a `[Content_Types].xml` file inside
MICROSOFT_OPEN_XML_DOCUMENT_ZIPS = { APPLICATION_DOCX, APPLICATION_XLSX, APPLICATION_PPTX }

POTENTIAL_OFFICE_OLE_MIMES = { APPLICATION_DOC, APPLICATION_PPT, APPLICATION_XLS }

general_mimetypes_to_mime_groups = {
    GENERAL_APPLICATION : APPLICATIONS,
    GENERAL_APPLICATION_ARCHIVE : ARCHIVES,
    GENERAL_IMAGE_PROJECT : IMAGE_PROJECT_FILES,
    GENERAL_AUDIO : AUDIO,
    GENERAL_IMAGE : IMAGES,
    GENERAL_VIDEO : VIDEO,
    GENERAL_ANIMATION : ANIMATIONS
}

mimes_to_general_mimetypes = {}

for ( general_mime_type, mimes_in_type ) in general_mimetypes_to_mime_groups.items():
    
    for mime in mimes_in_type:
        
        mimes_to_general_mimetypes[ mime ] = general_mime_type
        
    

PIL_HEIF_MIMES = {
    IMAGE_HEIF,
    IMAGE_HEIF_SEQUENCE,
    IMAGE_HEIC,
    IMAGE_HEIC_SEQUENCE
}

# AVIF SEQUENCE is not here because we handle it with ffmpeg I think, not PIL
PIL_AVIF_MIMES = {
    IMAGE_AVIF
}

MIMES_THAT_DEFINITELY_HAVE_AUDIO = tuple( [ APPLICATION_FLASH ] + list( AUDIO ) )
MIMES_THAT_MAY_HAVE_AUDIO = tuple( list( MIMES_THAT_DEFINITELY_HAVE_AUDIO ) + list( VIDEO ) )

MIMES_THAT_WE_CAN_CHECK_FOR_TRANSPARENCY = {
    IMAGE_JXL,
    IMAGE_PNG,
    IMAGE_GIF,
    IMAGE_WEBP,
    IMAGE_BMP,
    IMAGE_ICON,
    IMAGE_TIFF,
    IMAGE_QOI,
    IMAGE_AVIF,
    IMAGE_HEIF,
    IMAGE_HEIC,
    ANIMATION_GIF,
    ANIMATION_APNG,
    ANIMATION_WEBP,
    ANIMATION_JXL,
    IMAGE_AVIF_SEQUENCE,
    IMAGE_HEIF_SEQUENCE,
    IMAGE_HEIC_SEQUENCE
}

MIMES_THAT_MAY_THEORETICALLY_HAVE_TRANSPARENCY = MIMES_THAT_WE_CAN_CHECK_FOR_TRANSPARENCY.union( {
    APPLICATION_PSD,
    APPLICATION_SAI2,
    APPLICATION_KRITA,
    APPLICATION_XCF,
    APPLICATION_PROCREATE,
    APPLICATION_CLIP,
    IMAGE_SVG
} )

APPLICATIONS_WITH_THUMBNAILS = { IMAGE_SVG, APPLICATION_PDF, APPLICATION_FLASH, APPLICATION_CLIP, APPLICATION_PROCREATE, APPLICATION_CBZ, APPLICATION_PPTX, APPLICATION_PAINT_DOT_NET, APPLICATION_EPUB }.union( VIEWABLE_IMAGE_PROJECT_FILES )

MIMES_WITH_THUMBNAILS = set( IMAGES ).union( ANIMATIONS ).union( VIDEO ).union( APPLICATIONS_WITH_THUMBNAILS )

# basically a flash or a clip or a svg or whatever can normally just have some janked out resolution, so when testing such for thumbnail gen etc.., we'll ignore applications
MIMES_THAT_ALWAYS_HAVE_GOOD_RESOLUTION = set( IMAGES ).union( ANIMATIONS ).union( VIDEO )

FILES_THAT_CAN_HAVE_ICC_PROFILE = { IMAGE_BMP, IMAGE_JPEG, IMAGE_JXL, IMAGE_TIFF, IMAGE_PNG, IMAGE_GIF, APPLICATION_PSD, IMAGE_AVIF }.union( PIL_HEIF_MIMES )
FILES_THAT_CAN_HAVE_EXIF = { IMAGE_JPEG, IMAGE_JXL, IMAGE_TIFF, IMAGE_PNG, IMAGE_WEBP, ANIMATION_JXL, ANIMATION_APNG, ANIMATION_WEBP, IMAGE_AVIF }.union( PIL_HEIF_MIMES )

# images and animations that PIL can handle
FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA = { IMAGE_JPEG, IMAGE_JXL, IMAGE_PNG, IMAGE_BMP, IMAGE_WEBP, IMAGE_TIFF, IMAGE_ICON, IMAGE_GIF, IMAGE_AVIF, ANIMATION_JXL, ANIMATION_GIF, ANIMATION_APNG, ANIMATION_WEBP }
FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA.update( PIL_HEIF_MIMES )
FILES_THAT_CAN_HAVE_HUMAN_READABLE_EMBEDDED_METADATA.add( APPLICATION_PDF )

FILES_THAT_CAN_HAVE_PIXEL_HASH = set( IMAGES ).union( VIEWABLE_IMAGE_PROJECT_FILES )
FILES_THAT_HAVE_PERCEPTUAL_HASH = set( IMAGES ).union( VIEWABLE_IMAGE_PROJECT_FILES )

HYDRUS_UPDATE_FILES = ( APPLICATION_HYDRUS_UPDATE_DEFINITIONS, APPLICATION_HYDRUS_UPDATE_CONTENT )

mime_enum_lookup = {
    'collection' : APPLICATION_HYDRUS_CLIENT_COLLECTION,
    'image/jpe' : IMAGE_JPEG,
    'image/jpeg' : IMAGE_JPEG,
    'image/jpg' : IMAGE_JPEG,
    'image/x-png' : IMAGE_PNG,
    'image/png' : IMAGE_PNG,
    'image/apng' : ANIMATION_APNG,
    'image/gif' : ANIMATION_GIF, # no lookup goes to static gif
    'image/bmp' : IMAGE_BMP,
    'image/webp' : IMAGE_WEBP,
    'image/tiff' : IMAGE_TIFF,
    'image/qoi' : IMAGE_QOI,
    'image/x-icon' : IMAGE_ICON,
    'image/svg+xml': IMAGE_SVG,
    'image/heif' : IMAGE_HEIF,
    'image/heif-sequence' : IMAGE_HEIF_SEQUENCE,
    'image/heic' : IMAGE_HEIC,
    'image/heic-sequence' : IMAGE_HEIC_SEQUENCE,
    'image/avif' : IMAGE_AVIF,
    'image/avif-sequence' : IMAGE_AVIF_SEQUENCE,
    'image/jxl' : IMAGE_JXL, # could also be animated jxl
    'image/vnd.microsoft.icon' : IMAGE_ICON,
    'image' : IMAGES,
    'application/x-shockwave-flash' : APPLICATION_FLASH,
    'application/x-photoshop' : APPLICATION_PSD,
    'image/vnd.adobe.photoshop' : APPLICATION_PSD,
    'application/vnd.adobe.photoshop' : APPLICATION_PSD,
    'application/clip' : APPLICATION_CLIP, # made up
    'application/sai2': APPLICATION_SAI2, # made up
    'application/x-krita': APPLICATION_KRITA,
    'image/vnd.paint.net' : APPLICATION_PAINT_DOT_NET, # not official
    'application/x-paintnet' : APPLICATION_PAINT_DOT_NET, # not official
    'application/x-procreate': APPLICATION_PROCREATE, # made up
    'image/x-xcf' : APPLICATION_XCF,
    'application/octet-stream' : APPLICATION_OCTET_STREAM,
    'application/x-yaml' : APPLICATION_YAML,
    'PDF document' : APPLICATION_PDF,
    'application/pdf' : APPLICATION_PDF,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document' : APPLICATION_DOCX,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : APPLICATION_XLSX,
    'application/vnd.openxmlformats-officedocument.presentationml.presentation' : APPLICATION_PPTX,
    'application/msword' : APPLICATION_DOC,
    'application/vnd.ms-word' : APPLICATION_DOC,
    'application/vnd.ms-excel' : APPLICATION_XLS,
    'application/msexcel' : APPLICATION_XLS,
    'application/vnd.ms-powerpoint' : APPLICATION_PPT,
    'application/powerpoint' : APPLICATION_PPT,
    'application/mspowerpoint' : APPLICATION_PPT,
    'application/epub+zip' : APPLICATION_EPUB,
    'image/vnd.djvu' : APPLICATION_DJVU,
    'image/vnd.djvu+multipage' : APPLICATION_DJVU,
    'image/x-djvu' : APPLICATION_DJVU,
    'text/rtf' : APPLICATION_RTF,
    'application/rtf': APPLICATION_RTF,
    'application/vnd.comicbook+zip' : APPLICATION_CBZ,
    'application/zip' : APPLICATION_ZIP,
    'application/vnd.rar' : APPLICATION_RAR,
    'application/x-7z-compressed' : APPLICATION_7Z,
    'application/gzip': APPLICATION_GZIP,
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
    'audio/wavpack' : AUDIO_WAVPACK,
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
    'application/x-ole-storage' : UNDETERMINED_OLE,
    'unknown filetype' : APPLICATION_UNKNOWN
}

mime_string_lookup = {
    APPLICATION_HYDRUS_CLIENT_COLLECTION : 'collection',
    IMAGE_JPEG : 'jpeg',
    IMAGE_PNG : 'png',
    ANIMATION_APNG : 'apng',
    IMAGE_GIF : 'static gif',
    ANIMATION_GIF : 'animated gif',
    IMAGE_BMP : 'bitmap',
    IMAGE_WEBP : 'webp',
    ANIMATION_WEBP : 'animated webp',
    IMAGE_TIFF : 'tiff',
    IMAGE_QOI : 'qoi',
    IMAGE_ICON : 'icon',
    IMAGE_SVG : 'svg',
    IMAGE_HEIF : 'heif',
    IMAGE_HEIF_SEQUENCE : 'heif sequence',
    IMAGE_HEIC : 'heic',
    IMAGE_HEIC_SEQUENCE : 'heic sequence',
    IMAGE_AVIF : 'avif',
    IMAGE_AVIF_SEQUENCE : 'avif sequence',
    IMAGE_JXL : 'jxl',
    ANIMATION_JXL : 'animated jxl',
    ANIMATION_UGOIRA : 'ugoira',
    APPLICATION_CBZ : 'cbz',
    APPLICATION_FLASH : 'flash',
    APPLICATION_OCTET_STREAM : 'application/octet-stream',
    APPLICATION_YAML : 'yaml',
    APPLICATION_JSON : 'json',
    APPLICATION_CBOR : 'cbor',
    APPLICATION_PDF : 'pdf',
    APPLICATION_DOCX : 'docx',
    APPLICATION_XLSX : 'xlsx',
    APPLICATION_PPTX : 'pptx',
    APPLICATION_DOC : 'doc',
    APPLICATION_XLS : 'xls',
    APPLICATION_PPT : 'ppt',
    APPLICATION_EPUB : 'epub',
    APPLICATION_DJVU : 'djvu',
    APPLICATION_RTF : 'rtf',
    APPLICATION_PSD : 'psd',
    APPLICATION_CLIP : 'clip',
    APPLICATION_SAI2 : 'sai2',
    APPLICATION_KRITA : 'krita',
    APPLICATION_PAINT_DOT_NET : 'paint.net',
    APPLICATION_XCF : 'xcf',
    APPLICATION_PROCREATE : 'procreate',
    APPLICATION_ZIP : 'zip',
    APPLICATION_RAR : 'rar',
    APPLICATION_7Z : '7z',
    APPLICATION_GZIP: 'gzip',
    APPLICATION_WINDOWS_EXE : 'windows exe',
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
    AUDIO_WAVPACK : 'wavpack',
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
    UNDETERMINED_OLE : 'ole file',
    UNDETERMINED_WEBP : 'webp with or without animation',
    UNDETERMINED_JXL : 'jxl with or without animation',
    APPLICATION_UNKNOWN : 'unknown filetype',
    GENERAL_APPLICATION : 'application',
    GENERAL_APPLICATION_ARCHIVE : 'archive',
    GENERAL_IMAGE_PROJECT : 'image project file',
    GENERAL_AUDIO : 'audio',
    GENERAL_IMAGE : 'image',
    GENERAL_VIDEO : 'video',
    GENERAL_ANIMATION : 'animation'
}

string_enum_lookup = { s : enum for ( enum, s ) in mime_string_lookup.items() }

mime_mimetype_string_lookup = {
    APPLICATION_HYDRUS_CLIENT_COLLECTION : 'collection',
    IMAGE_JPEG : 'image/jpeg',
    IMAGE_PNG : 'image/png',
    ANIMATION_APNG : 'image/apng',
    IMAGE_GIF : 'image/gif',
    ANIMATION_GIF : 'image/gif',
    IMAGE_BMP : 'image/bmp',
    IMAGE_WEBP : 'image/webp',
    ANIMATION_WEBP : 'image/webp',
    IMAGE_TIFF : 'image/tiff',
    IMAGE_QOI : 'image/qoi',
    IMAGE_ICON : 'image/x-icon',
    IMAGE_SVG : 'image/svg+xml',
    IMAGE_HEIF: 'image/heif',
    IMAGE_HEIF_SEQUENCE: 'image/heif-sequence',
    IMAGE_HEIC: 'image/heic',
    IMAGE_HEIC_SEQUENCE: 'image/heic-sequence',
    IMAGE_AVIF: 'image/avif',
    IMAGE_AVIF_SEQUENCE: 'image/avif-sequence',
    IMAGE_JXL: 'image/jxl',
    ANIMATION_JXL : 'image/jxl',
    ANIMATION_UGOIRA : 'application/zip',
    APPLICATION_FLASH : 'application/x-shockwave-flash',
    APPLICATION_OCTET_STREAM : 'application/octet-stream',
    APPLICATION_CBZ: 'application/vnd.comicbook+zip',
    APPLICATION_YAML : 'application/x-yaml',
    APPLICATION_JSON : 'application/json',
    APPLICATION_CBOR : 'application/cbor',
    APPLICATION_PDF : 'application/pdf',
    APPLICATION_DOCX : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    APPLICATION_XLSX : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    APPLICATION_PPTX : 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    APPLICATION_DOC : 'application/msword',
    APPLICATION_XLS : 'application/vnd.ms-excel',
    APPLICATION_PPT : 'application/vnd.ms-powerpoint',
    APPLICATION_EPUB : 'application/epub+zip',
    APPLICATION_DJVU : 'image/vnd.djvu',
    APPLICATION_RTF: 'application/rtf',
    APPLICATION_PSD : 'image/vnd.adobe.photoshop',
    APPLICATION_CLIP : 'application/clip', # made up
    APPLICATION_SAI2: 'application/sai2', # made up
    APPLICATION_KRITA: 'application/x-krita',
    APPLICATION_PAINT_DOT_NET : 'application/x-paintnet', # no official
    APPLICATION_XCF : 'image/x-xcf',
    APPLICATION_PROCREATE : 'application/x-procreate', # made up
    APPLICATION_ZIP : 'application/zip',
    APPLICATION_RAR : 'application/vnd.rar',
    APPLICATION_7Z : 'application/x-7z-compressed',
    APPLICATION_GZIP: 'application/gzip',
    APPLICATION_WINDOWS_EXE : 'application/octet-stream',
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
    AUDIO_WAVPACK : 'audio/wavpack',
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
    UNDETERMINED_OLE : 'application/x-ole-storage',
    APPLICATION_UNKNOWN : 'unknown filetype',
    GENERAL_APPLICATION : 'application',
    GENERAL_APPLICATION_ARCHIVE : 'archive',
    GENERAL_IMAGE_PROJECT : 'image project file',
    GENERAL_AUDIO : 'audio',
    GENERAL_IMAGE : 'image',
    GENERAL_VIDEO : 'video',
    GENERAL_ANIMATION : 'animation'
}

mime_mimetype_string_lookup[ UNDETERMINED_WM ] = '{} or {}'.format( mime_mimetype_string_lookup[ AUDIO_WMA ], mime_mimetype_string_lookup[ VIDEO_WMV ] )
mime_mimetype_string_lookup[ UNDETERMINED_MP4 ] = '{} or {}'.format( mime_mimetype_string_lookup[ AUDIO_MP4 ], mime_mimetype_string_lookup[ VIDEO_MP4 ] )
mime_mimetype_string_lookup[ UNDETERMINED_PNG ] = '{} or {}'.format( mime_mimetype_string_lookup[ IMAGE_PNG ], mime_mimetype_string_lookup[ ANIMATION_APNG ] )
mime_mimetype_string_lookup[ UNDETERMINED_WEBP ] = 'image/webp, static or animated'
mime_mimetype_string_lookup[ UNDETERMINED_WEBP ] = 'image/jxl, static or animated'

mime_ext_lookup = {
    APPLICATION_HYDRUS_CLIENT_COLLECTION : '.collection',
    IMAGE_JPEG : '.jpg',
    IMAGE_PNG : '.png',
    ANIMATION_APNG : '.png',
    IMAGE_GIF : '.gif',
    ANIMATION_GIF : '.gif',
    IMAGE_BMP : '.bmp',
    IMAGE_WEBP : '.webp',
    ANIMATION_WEBP : '.webp',
    IMAGE_TIFF : '.tiff',
    IMAGE_QOI: '.qoi',
    IMAGE_ICON : '.ico',
    IMAGE_SVG : '.svg',
    IMAGE_HEIF: '.heif',
    IMAGE_HEIF_SEQUENCE: '.heifs',
    IMAGE_HEIC: '.heic',
    IMAGE_HEIC_SEQUENCE: '.heics',
    IMAGE_AVIF: '.avif',
    IMAGE_AVIF_SEQUENCE: '.avifs',
    IMAGE_JXL : '.jxl',
    ANIMATION_JXL : '.jxl',
    ANIMATION_UGOIRA : '.zip',
    APPLICATION_CBZ : '.cbz',   
    APPLICATION_FLASH : '.swf',
    APPLICATION_OCTET_STREAM : '.bin',
    APPLICATION_YAML : '.yaml',
    APPLICATION_JSON : '.json',
    APPLICATION_PDF : '.pdf',
    APPLICATION_DOCX : '.docx',
    APPLICATION_XLSX : '.xlsx',
    APPLICATION_PPTX : '.pptx',
    APPLICATION_DOC : '.doc',
    APPLICATION_XLS : '.xls',
    APPLICATION_PPT : '.ppt',
    APPLICATION_EPUB : '.epub',
    APPLICATION_DJVU : '.djvu',
    APPLICATION_RTF : '.rtf',
    APPLICATION_PSD : '.psd',
    APPLICATION_CLIP : '.clip',
    APPLICATION_SAI2 : '.sai2',
    APPLICATION_KRITA : '.kra',
    APPLICATION_PAINT_DOT_NET : '.pdn',
    APPLICATION_XCF : '.xcf',
    APPLICATION_PROCREATE : '.procreate',
    APPLICATION_ZIP : '.zip',
    APPLICATION_RAR : '.rar',
    APPLICATION_7Z : '.7z',
    APPLICATION_GZIP: '.gz',
    APPLICATION_WINDOWS_EXE : '.exe',
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
    AUDIO_WAVPACK : '.wv',
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

IMAGE_FILE_EXTS = { mime_ext_lookup[ mime ] for mime in IMAGES }
IMAGE_FILE_EXTS.update( ( '.jpe', '.jpeg' ) )
VIDEO_FILE_EXTS = { mime_ext_lookup[ mime ] for mime in VIDEO }

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

TIMEZONE_UTC = 0
TIMEZONE_LOCAL = 1
TIMEZONE_OFFSET = 2

UNICODE_APPROX_EQUAL = '\u2248'
UNICODE_BYTE_ORDER_MARK = '\uFEFF'
UNICODE_ELLIPSIS = '\u2026'
UNICODE_NOT_EQUAL = '\u2260'
UNICODE_REPLACEMENT_CHARACTER = '\ufffd'
UNICODE_PLUS_OR_MINUS = '\u00B1'
UNICODE_LESS_THAN_OR_EQUAL_TO = '\u2264'
UNICODE_GREATER_THAN_OR_EQUAL_TO = '\u2265'

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
    URL_TYPE_API : 'api/redirect url',
    URL_TYPE_FILE : 'file url',
    URL_TYPE_GALLERY : 'gallery url',
    URL_TYPE_WATCHABLE : 'watchable url',
    URL_TYPE_UNKNOWN : 'unknown url',
    URL_TYPE_NEXT : 'next page url',
    URL_TYPE_DESIRED : 'downloadable/pursuable url',
    URL_TYPE_SUB_GALLERY : 'sub-gallery url (is queued even if creator found no post/file urls)'
}

REMOTE_HELP = "https://hydrusnetwork.github.io/hydrus"

DOCUMENTATION_INDEX = "index.html"
DOCUMENTATION_CHANGELOG = f"changelog.html#version_{SOFTWARE_VERSION}"
DOCUMENTATION_DOWNLOADER_GUGS = "downloader_gugs.html"
DOCUMENTATION_DOWNLOADER_LOGIN = 'downloader_login.html'
DOCUMENTATION_ADDING_NEW_DOWNLOADERS = 'adding_new_downloaders.html'
DOCUMENTATION_DOWNLOADER_URL_CLASSES = 'downloader_url_classes.html'
DOCUMENTATION_GETTING_STARTED_SUBSCRIPTIONS = 'getting_started_subscriptions.html'
DOCUMENTATION_DATABASE_MIGRATION = 'database_migration.html'
DOCUMENTATION_DUPLICATES = 'duplicates.html'
DOCUMENTATION_DUPLICATES_AUTO_RESOLUTION = 'advanced_duplicates_auto_resolution.html'
DOCUMENTATION_DOWNLOADER_SHARING = 'downloader_sharing.html'
DOCUMENTATION_DOWNLOADER_PARSERS_PAGE_PARSERS_PAGE_PARSERS = 'downloader_parsers_page_parsers.html#page_parsers'
DOCUMENTATION_DOWNLOADER_PARSERS_CONTENT_PARSERS_CONTENT_PARSERS = 'downloader_parsers_content_parsers.html#content_parsers'
DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_ZIPPER_FORMULA = 'downloader_parsers_formulae.html#zipper_formula'
DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_CONTEXT_VARIABLE_FORMULA = 'downloader_parsers_formulae.html#context_variable_formula'
DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_HTML_FORMULA = 'downloader_parsers_formulae.html#html_formula'
DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_JSON_FORMULA = 'downloader_parsers_formulae.html#json_formula'
DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_NESTED_FORMULA = 'downloader_parsers_formulae.html#nested_formula'
DOCUMENTATION_DOWNLOADER_PARSERS_FORMULAE_STATIC = 'downloader_parsers_formulae.html#static_formula'
DOCUMENTATION_RATINGS = 'getting_started_ratings.html'
DOCUMENTATION_SIDECARS = 'advanced_sidecars.html'
DOCUMENTATION_ABOUT_DOCS = "about_docs.html"

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
