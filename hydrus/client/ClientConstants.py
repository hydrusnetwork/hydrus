import os

from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC

#

BLANK_PERCEPTUAL_HASH = b'\x80\x00\x00\x00\x00\x00\x00\x00' # first bit 1 but everything else 0 means only significant part of dct was [0,0], which represents flat colour

CAN_HIDE_MOUSE = True

CANVAS_MEDIA_VIEWER = 0
CANVAS_PREVIEW = 1
CANVAS_MEDIA_VIEWER_DUPLICATES = 2

CANVAS_MEDIA_VIEWER_TYPES = { CANVAS_MEDIA_VIEWER, CANVAS_MEDIA_VIEWER_DUPLICATES }

canvas_type_str_lookup = {}

canvas_type_str_lookup[ CANVAS_MEDIA_VIEWER ] = 'media viewer'
canvas_type_str_lookup[ CANVAS_PREVIEW ] = 'preview'
canvas_type_str_lookup[ CANVAS_MEDIA_VIEWER_DUPLICATES ] = 'duplicates filter'

# Hue is generally 200, Sat and Lum changes based on need
COLOUR_LIGHT_SELECTED = QG.QColor( 235, 248, 255 )
COLOUR_SELECTED = QG.QColor( 217, 242, 255 )
COLOUR_SELECTED_DARK = QG.QColor( 1, 17, 26 )
COLOUR_UNSELECTED = QG.QColor( 223, 227, 230 )

COLOUR_MESSAGE = QG.QColor( 230, 246, 255 )

COLOUR_THUMB_BACKGROUND = 0
COLOUR_THUMB_BACKGROUND_SELECTED = 1
COLOUR_THUMB_BACKGROUND_REMOTE = 2
COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED = 3
COLOUR_THUMB_BORDER = 4
COLOUR_THUMB_BORDER_SELECTED = 5
COLOUR_THUMB_BORDER_REMOTE = 6
COLOUR_THUMB_BORDER_REMOTE_SELECTED = 7
COLOUR_THUMBGRID_BACKGROUND = 8
COLOUR_AUTOCOMPLETE_BACKGROUND = 9
COLOUR_MEDIA_BACKGROUND = 10
COLOUR_MEDIA_TEXT = 11
COLOUR_TAGS_BOX = 12

DISCRIMINANT_INBOX = 0
DISCRIMINANT_LOCAL = 1
DISCRIMINANT_NOT_LOCAL = 2
DISCRIMINANT_ARCHIVE = 3
DISCRIMINANT_DOWNLOADING = 4
DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH = 5

DIRECTION_UP = 0
DIRECTION_LEFT = 1
DIRECTION_RIGHT = 2
DIRECTION_DOWN = 3

directions_alignment_string_lookup = {}

directions_alignment_string_lookup[ DIRECTION_UP ] = 'top'
directions_alignment_string_lookup[ DIRECTION_LEFT ] = 'left'
directions_alignment_string_lookup[ DIRECTION_RIGHT ] = 'right'
directions_alignment_string_lookup[ DIRECTION_DOWN ] = 'bottom'

FIELD_VERIFICATION_RECAPTCHA = 0
FIELD_COMMENT = 1
FIELD_TEXT = 2
FIELD_CHECKBOX = 3
FIELD_FILE = 4
FIELD_THREAD_ID = 5
FIELD_PASSWORD = 6

FIELDS = [ FIELD_VERIFICATION_RECAPTCHA, FIELD_COMMENT, FIELD_TEXT, FIELD_CHECKBOX, FIELD_FILE, FIELD_THREAD_ID, FIELD_PASSWORD ]

field_enum_lookup = {}

field_enum_lookup[ 'recaptcha' ] = FIELD_VERIFICATION_RECAPTCHA
field_enum_lookup[ 'comment' ] = FIELD_COMMENT
field_enum_lookup[ 'text' ] = FIELD_TEXT
field_enum_lookup[ 'checkbox' ] = FIELD_CHECKBOX
field_enum_lookup[ 'file' ] = FIELD_FILE
field_enum_lookup[ 'thread id' ] = FIELD_THREAD_ID
field_enum_lookup[ 'password' ] = FIELD_PASSWORD

field_string_lookup = {}

field_string_lookup[ FIELD_VERIFICATION_RECAPTCHA ] = 'recaptcha'
field_string_lookup[ FIELD_COMMENT ] = 'comment'
field_string_lookup[ FIELD_TEXT ] = 'text'
field_string_lookup[ FIELD_CHECKBOX ] = 'checkbox'
field_string_lookup[ FIELD_FILE ] = 'file'
field_string_lookup[ FIELD_THREAD_ID ] = 'thread id'
field_string_lookup[ FIELD_PASSWORD ] = 'password'

FILE_VIEWING_STATS_MENU_DISPLAY_NONE = 0
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_ONLY = 1
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_IN_SUBMENU = 2
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_STACKED = 3
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_SUMMED = 4

FLAGS_NONE = 0

FLAGS_CENTER = 3

FLAGS_EXPAND_PERPENDICULAR = 4
FLAGS_EXPAND_BOTH_WAYS = 5

FLAGS_EXPAND_BOTH_WAYS_POLITE = 7
FLAGS_EXPAND_BOTH_WAYS_SHY = 8

FLAGS_EXPAND_SIZER_PERPENDICULAR = 10
FLAGS_EXPAND_SIZER_BOTH_WAYS = 11

FLAGS_ON_LEFT = 12
FLAGS_ON_RIGHT = 13

FLAGS_CENTER_PERPENDICULAR = 15
FLAGS_SIZER_VCENTER = 16
FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH = 17

DAY = 0
WEEK = 1
MONTH = 2

RESTRICTION_MIN_RESOLUTION = 0
RESTRICTION_MAX_RESOLUTION = 1
RESTRICTION_MAX_FILE_SIZE = 2
RESTRICTION_ALLOWED_MIMES = 3

HAMMING_EXACT_MATCH = 0
HAMMING_VERY_SIMILAR = 2
HAMMING_SIMILAR = 4
HAMMING_SPECULATIVE = 8

hamming_string_lookup = {
    HAMMING_EXACT_MATCH : 'exact match',
    HAMMING_VERY_SIMILAR : 'very similar',
    HAMMING_SIMILAR : 'similar',
    HAMMING_SPECULATIVE : 'speculative'
}

SIMILAR_FILES_PIXEL_DUPES_REQUIRED = 0
SIMILAR_FILES_PIXEL_DUPES_ALLOWED = 1
SIMILAR_FILES_PIXEL_DUPES_EXCLUDED = 2

similar_files_pixel_dupes_string_lookup = {
    SIMILAR_FILES_PIXEL_DUPES_REQUIRED : 'must be pixel dupes',
    SIMILAR_FILES_PIXEL_DUPES_ALLOWED : 'can be pixel dupes',
    SIMILAR_FILES_PIXEL_DUPES_EXCLUDED : 'must not be pixel dupes'
}

IDLE_NOT_ON_SHUTDOWN = 0
IDLE_ON_SHUTDOWN = 1
IDLE_ON_SHUTDOWN_ASK_FIRST = 2

idle_string_lookup = {}

idle_string_lookup[ IDLE_NOT_ON_SHUTDOWN ] = 'do not run jobs on shutdown'
idle_string_lookup[ IDLE_ON_SHUTDOWN ] = 'run jobs on shutdown if needed'
idle_string_lookup[ IDLE_ON_SHUTDOWN_ASK_FIRST ] = 'run jobs on shutdown if needed, but ask first'

IMPORT_FOLDER_DELETE = 0
IMPORT_FOLDER_IGNORE = 1
IMPORT_FOLDER_MOVE = 2

import_folder_string_lookup = {}

import_folder_string_lookup[ IMPORT_FOLDER_DELETE ] = 'delete the file'
import_folder_string_lookup[ IMPORT_FOLDER_IGNORE ] = 'leave the file alone, do not reattempt it'
import_folder_string_lookup[ IMPORT_FOLDER_MOVE ] = 'move the file'

EXIT_SESSION_SESSION_NAME = 'exit session'
LAST_SESSION_SESSION_NAME = 'last session'

MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE = 0
MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE_PAUSED = 1
MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED = 2
MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED = 3
MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON = 4
MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY = 5
MEDIA_VIEWER_ACTION_DO_NOT_SHOW = 6
MEDIA_VIEWER_ACTION_SHOW_WITH_MPV = 7

media_viewer_action_string_lookup = {}

media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE ] = 'show with native hydrus viewer'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE_PAUSED ] = 'show as normal, but start paused -- obselete'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED ] = 'show, but initially behind an embed button -- obselete'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED ] = 'show, but initially behind an embed button, and start paused -- obselete'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON ] = 'show an \'open externally\' button'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY ] = 'do not show in the media viewer. on thumbnail activation, open externally'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_DO_NOT_SHOW ] = 'do not show at all'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_WITH_MPV ] = 'show using mpv'

unsupported_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, MEDIA_VIEWER_ACTION_DO_NOT_SHOW ]
static_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE ] + unsupported_media_actions
animated_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_WITH_MPV ] + static_media_actions
audio_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_WITH_MPV ] + unsupported_media_actions

# actions, can_start_paused, can_start_with_embed
static_full_support = ( static_media_actions, False, True )
animated_full_support = ( animated_media_actions, True, True )
audio_full_support = ( audio_media_actions, True, True )
no_support = ( unsupported_media_actions, False, False )

media_viewer_capabilities = {}

media_viewer_capabilities[ HC.GENERAL_ANIMATION ] = animated_full_support
media_viewer_capabilities[ HC.GENERAL_IMAGE ] = static_full_support
media_viewer_capabilities[ HC.GENERAL_VIDEO ] = animated_full_support
media_viewer_capabilities[ HC.GENERAL_AUDIO ] = audio_full_support
media_viewer_capabilities[ HC.GENERAL_APPLICATION ] = no_support

for mime in HC.SEARCHABLE_MIMES:
    
    if mime in HC.ANIMATIONS:
        
        media_viewer_capabilities[ mime ] = animated_full_support
        
    elif mime in HC.IMAGES:
        
        media_viewer_capabilities[ mime ] = static_full_support
        
    elif mime in HC.VIDEO:
        
        media_viewer_capabilities[ mime ] = animated_full_support
        
    elif mime in HC.AUDIO:
        
        media_viewer_capabilities[ mime ] = audio_full_support
        
    else:
        
        media_viewer_capabilities[ mime ] = no_support
        
    

media_viewer_capabilities[ HC.APPLICATION_HYDRUS_UPDATE_CONTENT ] = no_support
media_viewer_capabilities[ HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS ] = no_support

MEDIA_VIEWER_SCALE_100 = 0
MEDIA_VIEWER_SCALE_MAX_REGULAR = 1
MEDIA_VIEWER_SCALE_TO_CANVAS = 2

media_viewer_scale_string_lookup = {}

media_viewer_scale_string_lookup[ MEDIA_VIEWER_SCALE_100 ] = 'show at 100%'
media_viewer_scale_string_lookup[ MEDIA_VIEWER_SCALE_MAX_REGULAR ] = 'scale to the largest regular zoom that fits'
media_viewer_scale_string_lookup[ MEDIA_VIEWER_SCALE_TO_CANVAS ] = 'scale to the canvas size'

NEW_PAGE_GOES_FAR_LEFT = 0
NEW_PAGE_GOES_LEFT_OF_CURRENT = 1
NEW_PAGE_GOES_RIGHT_OF_CURRENT = 2
NEW_PAGE_GOES_FAR_RIGHT = 3

new_page_goes_string_lookup = {}

new_page_goes_string_lookup[ NEW_PAGE_GOES_FAR_LEFT ] = 'the far left'
new_page_goes_string_lookup[ NEW_PAGE_GOES_LEFT_OF_CURRENT ] = 'left of current page tab'
new_page_goes_string_lookup[ NEW_PAGE_GOES_RIGHT_OF_CURRENT ] = 'right of current page tab'
new_page_goes_string_lookup[ NEW_PAGE_GOES_FAR_RIGHT ] = 'the far right'

NETWORK_CONTEXT_GLOBAL = 0
NETWORK_CONTEXT_HYDRUS = 1
NETWORK_CONTEXT_DOMAIN = 2
NETWORK_CONTEXT_DOWNLOADER = 3
NETWORK_CONTEXT_DOWNLOADER_PAGE = 4
NETWORK_CONTEXT_SUBSCRIPTION = 5
NETWORK_CONTEXT_WATCHER_PAGE = 6

network_context_type_string_lookup = {}

network_context_type_string_lookup[ NETWORK_CONTEXT_GLOBAL ] = 'global'
network_context_type_string_lookup[ NETWORK_CONTEXT_HYDRUS ] = 'hydrus service'
network_context_type_string_lookup[ NETWORK_CONTEXT_DOMAIN ] = 'web domain'
network_context_type_string_lookup[ NETWORK_CONTEXT_DOWNLOADER ] = 'downloader'
network_context_type_string_lookup[ NETWORK_CONTEXT_DOWNLOADER_PAGE ] = 'downloader page'
network_context_type_string_lookup[ NETWORK_CONTEXT_SUBSCRIPTION ] = 'subscription'
network_context_type_string_lookup[ NETWORK_CONTEXT_WATCHER_PAGE ] = 'watcher page'

network_context_type_description_lookup = {}

network_context_type_description_lookup[ NETWORK_CONTEXT_GLOBAL ] = 'All network traffic, no matter the source or destination.'
network_context_type_description_lookup[ NETWORK_CONTEXT_HYDRUS ] = 'Network traffic going to or from a hydrus service.'
network_context_type_description_lookup[ NETWORK_CONTEXT_DOMAIN ] = 'Network traffic going to or from a web domain (or a subdomain).'
network_context_type_description_lookup[ NETWORK_CONTEXT_DOWNLOADER ] = 'Network traffic going through a downloader. This is no longer used.'
network_context_type_description_lookup[ NETWORK_CONTEXT_DOWNLOADER_PAGE ] = 'Network traffic going through a single downloader page. This is an ephemeral context--it will not be saved through a client restart. It is useful to throttle individual downloader pages so they give the db and other import pages time to do work.'
network_context_type_description_lookup[ NETWORK_CONTEXT_SUBSCRIPTION ] = 'Network traffic going through a subscription query. Each query gets its own network context, named \'[subscription name]: [query text]\'.'
network_context_type_description_lookup[ NETWORK_CONTEXT_WATCHER_PAGE ] = 'Network traffic going through a single watcher page. This is an ephemeral context--it will not be saved through a client restart. It is useful to throttle individual watcher pages so they give the db and other import pages time to do work.'

PAGE_FILE_COUNT_DISPLAY_ALL = 0
PAGE_FILE_COUNT_DISPLAY_NONE = 1
PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS = 2

page_file_count_display_string_lookup = {}

page_file_count_display_string_lookup[ PAGE_FILE_COUNT_DISPLAY_ALL ] = 'for all pages'
page_file_count_display_string_lookup[ PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS ] = 'for import pages'
page_file_count_display_string_lookup[ PAGE_FILE_COUNT_DISPLAY_NONE ] = 'for no pages'

SHUTDOWN_TIMESTAMP_VACUUM = 0
SHUTDOWN_TIMESTAMP_FATTEN_AC_CACHE = 1
SHUTDOWN_TIMESTAMP_DELETE_ORPHANS = 2

SORT_FILES_BY_FILESIZE = 0
SORT_FILES_BY_DURATION = 1
SORT_FILES_BY_IMPORT_TIME = 2
SORT_FILES_BY_MIME = 3
SORT_FILES_BY_RANDOM = 4
SORT_FILES_BY_WIDTH = 5
SORT_FILES_BY_HEIGHT = 6
SORT_FILES_BY_RATIO = 7
SORT_FILES_BY_NUM_PIXELS = 8
SORT_FILES_BY_NUM_TAGS = 9
SORT_FILES_BY_MEDIA_VIEWS = 10
SORT_FILES_BY_MEDIA_VIEWTIME = 11
SORT_FILES_BY_APPROX_BITRATE = 12
SORT_FILES_BY_HAS_AUDIO = 13
SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP = 14
SORT_FILES_BY_FRAMERATE = 15
SORT_FILES_BY_NUM_FRAMES = 16
SORT_FILES_BY_NUM_COLLECTION_FILES = 17
SORT_FILES_BY_LAST_VIEWED_TIME = 18

SYSTEM_SORT_TYPES = {
    SORT_FILES_BY_NUM_COLLECTION_FILES,
    SORT_FILES_BY_HEIGHT,
    SORT_FILES_BY_WIDTH,
    SORT_FILES_BY_RATIO,
    SORT_FILES_BY_NUM_PIXELS,
    SORT_FILES_BY_DURATION,
    SORT_FILES_BY_FRAMERATE,
    SORT_FILES_BY_NUM_FRAMES,
    SORT_FILES_BY_FILESIZE,
    SORT_FILES_BY_APPROX_BITRATE,
    SORT_FILES_BY_HAS_AUDIO,
    SORT_FILES_BY_MIME,
    SORT_FILES_BY_RANDOM,
    SORT_FILES_BY_NUM_TAGS,
    SORT_FILES_BY_MEDIA_VIEWS,
    SORT_FILES_BY_MEDIA_VIEWTIME,
    SORT_FILES_BY_IMPORT_TIME,
    SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP,
    SORT_FILES_BY_LAST_VIEWED_TIME
}

system_sort_type_submetatype_string_lookup = {}

system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_NUM_COLLECTION_FILES ] = 'collections'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_HEIGHT ] = 'dimensions'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_NUM_PIXELS ] = 'dimensions'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_RATIO ] = 'dimensions'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_WIDTH ] = 'dimensions'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_DURATION ] = 'duration'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_FRAMERATE ] = 'duration'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_NUM_FRAMES ] = 'duration'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_APPROX_BITRATE ] = 'file'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_FILESIZE ] = 'file'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_MIME ] = 'file'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_HAS_AUDIO ] = 'file'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_RANDOM ] = None
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_NUM_TAGS ] = 'tags'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_IMPORT_TIME ] = 'time'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP ] = 'time'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_LAST_VIEWED_TIME ] = 'time'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_MEDIA_VIEWS ] = 'views'
system_sort_type_submetatype_string_lookup[ SORT_FILES_BY_MEDIA_VIEWTIME ] = 'views'

sort_type_basic_string_lookup = {}

sort_type_basic_string_lookup[ SORT_FILES_BY_DURATION ] = 'duration'
sort_type_basic_string_lookup[ SORT_FILES_BY_FRAMERATE ] = 'framerate'
sort_type_basic_string_lookup[ SORT_FILES_BY_NUM_FRAMES ] = 'number of frames'
sort_type_basic_string_lookup[ SORT_FILES_BY_HEIGHT ] = 'height'
sort_type_basic_string_lookup[ SORT_FILES_BY_NUM_COLLECTION_FILES ] = 'number of files in collection'
sort_type_basic_string_lookup[ SORT_FILES_BY_NUM_PIXELS ] = 'number of pixels'
sort_type_basic_string_lookup[ SORT_FILES_BY_RATIO ] = 'resolution ratio'
sort_type_basic_string_lookup[ SORT_FILES_BY_WIDTH ] = 'width'
sort_type_basic_string_lookup[ SORT_FILES_BY_APPROX_BITRATE ] = 'approximate bitrate'
sort_type_basic_string_lookup[ SORT_FILES_BY_FILESIZE ] = 'filesize'
sort_type_basic_string_lookup[ SORT_FILES_BY_MIME ] = 'filetype'
sort_type_basic_string_lookup[ SORT_FILES_BY_HAS_AUDIO ] = 'has audio'
sort_type_basic_string_lookup[ SORT_FILES_BY_IMPORT_TIME ] = 'import time'
sort_type_basic_string_lookup[ SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP ] = 'modified time'
sort_type_basic_string_lookup[ SORT_FILES_BY_LAST_VIEWED_TIME ] = 'last viewed time'
sort_type_basic_string_lookup[ SORT_FILES_BY_RANDOM ] = 'random'
sort_type_basic_string_lookup[ SORT_FILES_BY_NUM_TAGS ] = 'number of tags'
sort_type_basic_string_lookup[ SORT_FILES_BY_MEDIA_VIEWS ] = 'media views'
sort_type_basic_string_lookup[ SORT_FILES_BY_MEDIA_VIEWTIME ] = 'media viewtime'

sort_type_string_lookup = {}

for sort_type in SYSTEM_SORT_TYPES:
    
    ms = system_sort_type_submetatype_string_lookup[ sort_type ]
    s = sort_type_basic_string_lookup[ sort_type ]
    
    if ms is not None:
        
        s = '{}: {}'.format( ms, s )
        
    
    sort_type_string_lookup[ sort_type ] = s
    

SYSTEM_SORT_TYPES_SORT_CONTROL_SORTED = sorted( SYSTEM_SORT_TYPES, key = lambda sst: sort_type_string_lookup[ sst ] )

SORT_ASC = 0
SORT_DESC = 1

STATUS_UNKNOWN = 0
STATUS_SUCCESSFUL_AND_NEW = 1
STATUS_SUCCESSFUL_BUT_REDUNDANT = 2
STATUS_DELETED = 3
STATUS_ERROR = 4
STATUS_NEW = 5 # no longer used
STATUS_PAUSED = 6 # not used
STATUS_VETOED = 7
STATUS_SKIPPED = 8

status_string_lookup = {}

status_string_lookup[ STATUS_UNKNOWN ] = ''
status_string_lookup[ STATUS_SUCCESSFUL_AND_NEW ] = 'successful'
status_string_lookup[ STATUS_SUCCESSFUL_BUT_REDUNDANT ] = 'already in db'
status_string_lookup[ STATUS_DELETED ] = 'deleted'
status_string_lookup[ STATUS_ERROR ] = 'error'
status_string_lookup[ STATUS_NEW ] = 'new'
status_string_lookup[ STATUS_PAUSED ] = 'paused'
status_string_lookup[ STATUS_VETOED ] = 'ignored'
status_string_lookup[ STATUS_SKIPPED ] = 'skipped'

SUCCESSFUL_IMPORT_STATES = { STATUS_SUCCESSFUL_AND_NEW, STATUS_SUCCESSFUL_BUT_REDUNDANT }
UNSUCCESSFUL_IMPORT_STATES = { STATUS_DELETED, STATUS_ERROR, STATUS_VETOED }
FAILED_IMPORT_STATES = { STATUS_ERROR, STATUS_VETOED }

UNICODE_ALMOST_EQUAL_TO = '\u2248'
UNICODE_NOT_EQUAL_TO = '\u2260'

ZOOM_NEAREST = 0 # pixelly garbage
ZOOM_LINEAR = 1 # simple and quick
ZOOM_AREA = 2 # for shrinking without moire
ZOOM_CUBIC = 3 # for interpolating, pretty good
ZOOM_LANCZOS4 = 4 # for interpolating, noice

zoom_string_lookup = {}

zoom_string_lookup[ ZOOM_NEAREST ] = 'nearest neighbour'
zoom_string_lookup[ ZOOM_LINEAR ] = 'bilinear interpolation'
zoom_string_lookup[ ZOOM_AREA ] = 'pixel area resampling'
zoom_string_lookup[ ZOOM_CUBIC ] = '4x4 bilinear interpolation'
zoom_string_lookup[ ZOOM_LANCZOS4 ] = '8x8 Lanczos interpolation'

class GlobalPixmaps( object ):
    
    my_instance = None
    
    def __init__( self ):
        
        self._Initialise()
        
    
    @staticmethod
    def instance() -> 'GlobalPixmaps':
        
        if GlobalPixmaps.my_instance is None:
            
            GlobalPixmaps.my_instance = GlobalPixmaps()
            
        
        return GlobalPixmaps.my_instance
        
    
    def _Initialise( self ):
        
        # These probably *could* be created even before QApplication is constructed, but it can't hurt to wait until that's done.
        
        self.bold = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_bold.png' ) )
        self.italic = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_italic.png' ) )
        self.underline = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_underline.png' ) )
        
        self.align_left = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_align_left.png' ) )
        self.align_center = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_align_center.png' ) )
        self.align_right = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_align_right.png' ) )
        self.align_justify = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_align_justify.png' ) )
        
        self.indent_less = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_indent_remove.png' ) )
        self.indent_more = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_indent.png' ) )
        
        self.font = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'font.png' ) )
        self.colour = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'color_swatch.png' ) )
        
        self.link = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'link.png' ) )
        self.link_break = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'link_break.png' ) )
        
        self.drag = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'drag.png' ) )
        
        self.transparent = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'transparent.png' ) )
        self.downloading = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'downloading.png' ) )
        self.file_repository = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_repository_small.png' ) )
        self.file_repository_pending = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_repository_pending_small.png' ) )
        self.file_repository_petitioned = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_repository_petitioned_small.png' ) )
        self.ipfs = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'ipfs_small.png' ) )
        self.ipfs_pending = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'ipfs_pending_small.png' ) )
        self.ipfs_petitioned = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'ipfs_petitioned_small.png' ) )
        
        self.collection = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'collection.png' ) )
        self.inbox = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'inbox.png' ) )
        self.trash = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'trash.png' ) )
        
        self.refresh = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'refresh.png' ) )
        self.archive = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'archive.png' ) )
        self.to_inbox = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'to_inbox.png' ) )
        self.delete = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'trash.png' ) )
        self.trash_delete = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'delete.png' ) )
        self.undelete = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'undelete.png' ) )
        self.zoom_in = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'zoom_in.png' ) )
        self.zoom_out = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'zoom_out.png' ) )
        self.zoom_switch = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'zoom_switch.png' ) )
        self.fullscreen_switch = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'fullscreen_switch.png' ) )
        self.open_externally = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'open_externally.png' ) )
        
        self.dump_ok = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'dump_ok.png' ) )
        self.dump_recoverable = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'dump_recoverable.png' ) )
        self.dump_fail = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'dump_fail.png' ) )
        
        self.cog = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'cog.png' ) )
        self.family = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'family.png' ) )
        self.keyboard = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'keyboard.png' ) )
        self.help = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'help.png' ) )
        
        self.check = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'check.png' ) )
        self.pause = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'pause.png' ) )
        self.play = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'play.png' ) )
        self.stop = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'stop.png' ) )
        
        self.sound = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'sound.png' ) )
        self.mute = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'mute.png' ) )
        
        self.notes = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'notes.png' ) )
        
        self.file_pause = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_pause.png' ) )
        self.file_play = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_play.png' ) )
        self.gallery_pause = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'gallery_pause.png' ) )
        self.gallery_play = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'gallery_play.png' ) )
        
        self.highlight = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'highlight.png' ) )
        self.clear_highlight = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'clear_highlight.png' ) )
        
        self.star = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'star.png' ) )
        
        self.listctrl = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'listctrl.png' ) )
        
        self.copy = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'copy.png' ) )
        self.paste = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'paste.png' ) )
        
        self.eight_chan = QG.QPixmap( os.path.join( HC.STATIC_DIR, '8chan.png' ) )
        self.twitter = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'twitter.png' ) )
        self.tumblr = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'tumblr.png' ) )
        self.discord = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'discord.png' ) )
        self.patreon = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'patreon.png' ) )
        self.github = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'github.png' ) )
        
        self.first = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'first.png' ) )
        self.previous = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'previous.png' ) )
        self.next_bmp = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'next.png' ) )
        self.last = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'last.png' ) )
        self.pair = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'pair.png' ) )
        

global_pixmaps = GlobalPixmaps.instance

DEFAULT_LOCAL_TAG_SERVICE_KEY = b'local tags'

DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY = b'downloader tags'

LOCAL_FILE_SERVICE_KEY = b'local files'

LOCAL_UPDATE_SERVICE_KEY = b'repository updates'

LOCAL_BOORU_SERVICE_KEY = b'local booru'

LOCAL_NOTES_SERVICE_KEY = b'local notes'

DEFAULT_FAVOURITES_RATING_SERVICE_KEY = b'favourites'

CLIENT_API_SERVICE_KEY = b'client api'

TRASH_SERVICE_KEY = b'trash'

COMBINED_LOCAL_FILE_SERVICE_KEY = b'all local files'

COMBINED_FILE_SERVICE_KEY = b'all known files'

COMBINED_DELETED_FILE_SERVICE_KEY = b'all deleted files'

COMBINED_TAG_SERVICE_KEY = b'all known tags'

TEST_SERVICE_KEY = b'test service'
