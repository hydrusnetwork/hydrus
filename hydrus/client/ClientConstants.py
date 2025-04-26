import os

from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC

#

BLANK_PERCEPTUAL_HASH = b'\x80\x00\x00\x00\x00\x00\x00\x00' # first bit 1 but everything else 0 means only significant part of dct was [0,0], which represents flat colour

CAN_HIDE_MOUSE = True

CANVAS_MEDIA_VIEWER = 0
CANVAS_PREVIEW = 1
CANVAS_MEDIA_VIEWER_DUPLICATES = 2
CANVAS_MEDIA_VIEWER_ARCHIVE_DELETE = 3
CANVAS_CLIENT_API = 4

CANVAS_MEDIA_VIEWER_TYPES = { CANVAS_MEDIA_VIEWER, CANVAS_MEDIA_VIEWER_DUPLICATES, CANVAS_MEDIA_VIEWER_ARCHIVE_DELETE }

canvas_type_str_lookup = {
    CANVAS_MEDIA_VIEWER : 'media viewer',
    CANVAS_PREVIEW : 'preview viewer',
    CANVAS_MEDIA_VIEWER_DUPLICATES : 'duplicates filter',
    CANVAS_MEDIA_VIEWER_ARCHIVE_DELETE : 'archive/delete filter',
    CANVAS_CLIENT_API : 'client api viewer'
}

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

directions_alignment_string_lookup = {
    DIRECTION_UP : 'top',
    DIRECTION_LEFT : 'left',
    DIRECTION_RIGHT : 'right',
    DIRECTION_DOWN : 'bottom'
}

FIELD_VERIFICATION_RECAPTCHA = 0
FIELD_COMMENT = 1
FIELD_TEXT = 2
FIELD_CHECKBOX = 3
FIELD_FILE = 4
FIELD_THREAD_ID = 5
FIELD_PASSWORD = 6

FIELDS = [ FIELD_VERIFICATION_RECAPTCHA, FIELD_COMMENT, FIELD_TEXT, FIELD_CHECKBOX, FIELD_FILE, FIELD_THREAD_ID, FIELD_PASSWORD ]

field_enum_lookup = {
    'recaptcha' : FIELD_VERIFICATION_RECAPTCHA,
    'comment' : FIELD_COMMENT,
    'text' : FIELD_TEXT,
    'checkbox' : FIELD_CHECKBOX,
    'file' : FIELD_FILE,
    'thread id': FIELD_THREAD_ID,
    'password' : FIELD_PASSWORD
}

field_string_lookup = {
    FIELD_VERIFICATION_RECAPTCHA : 'recaptcha',
    FIELD_COMMENT : 'comment',
    FIELD_TEXT : 'text',
    FIELD_CHECKBOX : 'checkbox',
    FIELD_FILE : 'file',
    FIELD_THREAD_ID : 'thread id',
    FIELD_PASSWORD : 'password'
}

FILE_VIEWING_STATS_MENU_DISPLAY_NONE = 0 # deprecated
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_ONLY = 1 # deprecated
FILE_VIEWING_STATS_MENU_DISPLAY_SUMMED_AND_THEN_SUBMENU = 2
FILE_VIEWING_STATS_MENU_DISPLAY_STACKED = 3
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_SUMMED = 4 # deprecated

FLAGS_NONE = 0

FLAGS_CENTER = 3

FLAGS_EXPAND_PERPENDICULAR = 4
FLAGS_EXPAND_BOTH_WAYS = 5
FLAGS_EXPAND_PERPENDICULAR_BUT_BOTH_WAYS_LATER = 6

FLAGS_EXPAND_BOTH_WAYS_POLITE = 7
FLAGS_EXPAND_BOTH_WAYS_SHY = 8

FLAGS_EXPAND_SIZER_PERPENDICULAR = 10
FLAGS_EXPAND_SIZER_BOTH_WAYS = 11

FLAGS_ON_LEFT = 12
FLAGS_ON_RIGHT = 13

FLAGS_CENTER_PERPENDICULAR = 15 # TODO: Collapse all this into something meaningful. We use this guy like 260+ times and it is basically a useless stub let's go
FLAGS_SIZER_CENTER = 16
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

IDLE_NOT_ON_SHUTDOWN = 0
IDLE_ON_SHUTDOWN = 1
IDLE_ON_SHUTDOWN_ASK_FIRST = 2

idle_string_lookup = {
    IDLE_NOT_ON_SHUTDOWN : 'do not run jobs on shutdown',
    IDLE_ON_SHUTDOWN : 'run jobs on shutdown if needed',
    IDLE_ON_SHUTDOWN_ASK_FIRST : 'run jobs on shutdown if needed, but ask first'
}

IMPORT_FOLDER_DELETE = 0
IMPORT_FOLDER_IGNORE = 1
IMPORT_FOLDER_MOVE = 2

import_folder_string_lookup = {
    IMPORT_FOLDER_DELETE : 'delete the source file',
    IMPORT_FOLDER_IGNORE : 'leave the source file alone, do not reattempt it',
    IMPORT_FOLDER_MOVE : 'move the source file'
}

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
MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER = 8

media_viewer_action_string_lookup = {
    MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE : 'show with native hydrus viewer',
    MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE_PAUSED : 'show as normal, but start paused -- obselete',
    MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED : 'show, but initially behind an embed button -- obselete',
    MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED : 'show, but initially behind an embed button, and start paused -- obselete',
    MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON : 'show an \'open externally\' button',
    MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY : 'do not show in the media viewer. on thumbnail activation, open externally',
    MEDIA_VIEWER_ACTION_DO_NOT_SHOW : 'do not show at all',
    MEDIA_VIEWER_ACTION_SHOW_WITH_MPV : 'show using mpv',
    MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER : 'show using Qt Media Player (EXPERIMENTAL, buggy, crashy!)'
}

unsupported_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, MEDIA_VIEWER_ACTION_DO_NOT_SHOW ]
static_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE ] + unsupported_media_actions
webp_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE ] + unsupported_media_actions
ugoira_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE ] + unsupported_media_actions
animated_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER ] + static_media_actions
audio_media_actions = [ MEDIA_VIEWER_ACTION_SHOW_WITH_MPV, MEDIA_VIEWER_ACTION_SHOW_WITH_QMEDIAPLAYER ] + unsupported_media_actions

# actions, can_start_paused, can_start_with_embed
static_full_support = ( static_media_actions, False, True )
webp_support = ( webp_media_actions, True, True )
ugoira_support = (ugoira_media_actions, True, True)
animated_full_support = ( animated_media_actions, True, True )
audio_full_support = ( audio_media_actions, True, True )
no_support = ( unsupported_media_actions, False, False )

media_viewer_capabilities = {
    HC.GENERAL_ANIMATION : animated_full_support,
    HC.GENERAL_IMAGE : static_full_support,
    HC.GENERAL_VIDEO : animated_full_support,
    HC.GENERAL_AUDIO : audio_full_support,
    HC.GENERAL_APPLICATION : no_support,
    HC.GENERAL_APPLICATION_ARCHIVE : no_support,
    HC.GENERAL_IMAGE_PROJECT : no_support
}

for mime in HC.SEARCHABLE_MIMES:
    
    if mime == HC.ANIMATION_WEBP:
        
        media_viewer_capabilities[ mime ] = webp_support
        
    if mime == HC.ANIMATION_UGOIRA:
        
        media_viewer_capabilities[ mime ] = ugoira_support
        
    elif mime in HC.VIEWABLE_ANIMATIONS:
        
        media_viewer_capabilities[ mime ] = animated_full_support
        
    elif mime in HC.IMAGES:
        
        media_viewer_capabilities[ mime ] = static_full_support
        
    elif mime in HC.VIDEO:
        
        media_viewer_capabilities[ mime ] = animated_full_support
        
    elif mime in HC.AUDIO:
        
        media_viewer_capabilities[ mime ] = audio_full_support
        
    elif mime in HC.VIEWABLE_IMAGE_PROJECT_FILES:
        
        media_viewer_capabilities[ mime ] = static_full_support
        
    else:
        
        media_viewer_capabilities[ mime ] = no_support
        

media_viewer_capabilities[ HC.APPLICATION_HYDRUS_UPDATE_CONTENT ] = no_support
media_viewer_capabilities[ HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS ] = no_support

MEDIA_VIEWER_SCALE_100 = 0
MEDIA_VIEWER_SCALE_MAX_REGULAR = 1
MEDIA_VIEWER_SCALE_TO_CANVAS = 2

media_viewer_scale_string_lookup = {
    MEDIA_VIEWER_SCALE_100 : 'show at 100%',
    MEDIA_VIEWER_SCALE_MAX_REGULAR : 'scale to the largest regular zoom that fits',
    MEDIA_VIEWER_SCALE_TO_CANVAS : 'scale to the canvas size'
}

NEW_PAGE_GOES_FAR_LEFT = 0
NEW_PAGE_GOES_LEFT_OF_CURRENT = 1
NEW_PAGE_GOES_RIGHT_OF_CURRENT = 2
NEW_PAGE_GOES_FAR_RIGHT = 3

new_page_goes_string_lookup = {
    NEW_PAGE_GOES_FAR_LEFT : 'the far left',
    NEW_PAGE_GOES_LEFT_OF_CURRENT : 'left of current page tab',
    NEW_PAGE_GOES_RIGHT_OF_CURRENT : 'right of current page tab',
    NEW_PAGE_GOES_FAR_RIGHT : 'the far right'
}

CLOSED_PAGE_FOCUS_GOES_LEFT = 0
CLOSED_PAGE_FOCUS_GOES_RIGHT = 1

closed_page_focus_string_lookup = {
    CLOSED_PAGE_FOCUS_GOES_LEFT : 'left of the closed page tab',
    CLOSED_PAGE_FOCUS_GOES_RIGHT : 'right of the closed page tab'
}

NETWORK_CONTEXT_GLOBAL = 0
NETWORK_CONTEXT_HYDRUS = 1
NETWORK_CONTEXT_DOMAIN = 2
NETWORK_CONTEXT_DOWNLOADER = 3
NETWORK_CONTEXT_DOWNLOADER_PAGE = 4
NETWORK_CONTEXT_SUBSCRIPTION = 5
NETWORK_CONTEXT_WATCHER_PAGE = 6

network_context_type_string_lookup = {
    NETWORK_CONTEXT_GLOBAL : 'global',
    NETWORK_CONTEXT_HYDRUS : 'hydrus service',
    NETWORK_CONTEXT_DOMAIN : 'web domain',
    NETWORK_CONTEXT_DOWNLOADER : 'downloader',
    NETWORK_CONTEXT_DOWNLOADER_PAGE : 'downloader page',
    NETWORK_CONTEXT_SUBSCRIPTION : 'subscription',
    NETWORK_CONTEXT_WATCHER_PAGE : 'watcher page'
}

network_context_type_description_lookup = {
    NETWORK_CONTEXT_GLOBAL : 'All network traffic, no matter the source or destination.',
    NETWORK_CONTEXT_HYDRUS : 'Network traffic going to or from a hydrus service.',
    NETWORK_CONTEXT_DOMAIN : 'Network traffic going to or from a web domain (or a subdomain).',
    NETWORK_CONTEXT_DOWNLOADER : 'Network traffic going through a downloader. This is no longer used.',
    NETWORK_CONTEXT_DOWNLOADER_PAGE : 'Network traffic going through a single downloader page. This is an ephemeral context--it will not be saved through a client restart. It is useful to throttle individual downloader pages so they give the db and other import pages time to do work.',
    NETWORK_CONTEXT_SUBSCRIPTION : 'Network traffic going through a subscription query. Each query gets its own network context, named \'[subscription name]: [query text]\'.',
    NETWORK_CONTEXT_WATCHER_PAGE : 'Network traffic going through a single watcher page. This is an ephemeral context--it will not be saved through a client restart. It is useful to throttle individual watcher pages so they give the db and other import pages time to do work.'
}

PAGE_FILE_COUNT_DISPLAY_ALL = 0
PAGE_FILE_COUNT_DISPLAY_NONE = 1
PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS = 2
PAGE_FILE_COUNT_DISPLAY_ALL_BUT_ONLY_IF_GREATER_THAN_ZERO = 3

page_file_count_display_string_lookup = {
    PAGE_FILE_COUNT_DISPLAY_ALL : 'for all pages',
    PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS : 'for import pages',
    PAGE_FILE_COUNT_DISPLAY_NONE : 'for no pages',
    PAGE_FILE_COUNT_DISPLAY_ALL_BUT_ONLY_IF_GREATER_THAN_ZERO : 'for all pages, but only if greater than zero'
}

PAGE_STATE_NORMAL = 0
PAGE_STATE_INITIALISING = 1
PAGE_STATE_SEARCHING = 2
PAGE_STATE_SEARCHING_CANCELLED = 3

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
SORT_FILES_BY_ARCHIVED_TIMESTAMP = 19
SORT_FILES_BY_HASH = 20
SORT_FILES_BY_PIXEL_HASH = 21
SORT_FILES_BY_BLURHASH = 22
SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS = 23
SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE = 24
SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED = 25
SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW = 26
SORT_FILES_BY_AVERAGE_COLOUR_HUE = 27

AVERAGE_COLOUR_FILE_SORTS = {
    SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS,
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE,
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED,
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW,
    SORT_FILES_BY_AVERAGE_COLOUR_HUE
}

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
    SORT_FILES_BY_LAST_VIEWED_TIME,
    SORT_FILES_BY_ARCHIVED_TIMESTAMP,
    SORT_FILES_BY_HASH,
    SORT_FILES_BY_PIXEL_HASH,
    SORT_FILES_BY_BLURHASH,
    SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS,
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE,
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED,
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW,
    SORT_FILES_BY_AVERAGE_COLOUR_HUE
}

system_sort_type_submetatype_string_lookup = {
    SORT_FILES_BY_NUM_COLLECTION_FILES : 'collections',
    SORT_FILES_BY_HEIGHT : 'dimensions',
    SORT_FILES_BY_NUM_PIXELS : 'dimensions',
    SORT_FILES_BY_RATIO : 'dimensions',
    SORT_FILES_BY_WIDTH : 'dimensions',
    SORT_FILES_BY_DURATION : 'duration',
    SORT_FILES_BY_FRAMERATE : 'duration',
    SORT_FILES_BY_NUM_FRAMES : 'duration',
    SORT_FILES_BY_APPROX_BITRATE : 'file',
    SORT_FILES_BY_FILESIZE : 'file',
    SORT_FILES_BY_HASH : 'file',
    SORT_FILES_BY_PIXEL_HASH : 'file',
    SORT_FILES_BY_BLURHASH : 'file',
    SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS : 'average colour',
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE : 'average colour',
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED : 'average colour',
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW : 'average colour',
    SORT_FILES_BY_AVERAGE_COLOUR_HUE : 'average colour',
    SORT_FILES_BY_MIME : 'file',
    SORT_FILES_BY_HAS_AUDIO : 'file',
    SORT_FILES_BY_RANDOM : None,
    SORT_FILES_BY_NUM_TAGS : 'tags',
    SORT_FILES_BY_IMPORT_TIME : 'time',
    SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP : 'time',
    SORT_FILES_BY_ARCHIVED_TIMESTAMP : 'time',
    SORT_FILES_BY_LAST_VIEWED_TIME : 'time',
    SORT_FILES_BY_MEDIA_VIEWS : 'views',
    SORT_FILES_BY_MEDIA_VIEWTIME : 'views'
}

sort_type_basic_string_lookup = {
    SORT_FILES_BY_DURATION : 'duration',
    SORT_FILES_BY_FRAMERATE : 'framerate',
    SORT_FILES_BY_NUM_FRAMES : 'number of frames',
    SORT_FILES_BY_HEIGHT : 'height',
    SORT_FILES_BY_NUM_COLLECTION_FILES : 'number of files in collection',
    SORT_FILES_BY_NUM_PIXELS : 'number of pixels',
    SORT_FILES_BY_AVERAGE_COLOUR_LIGHTNESS : 'lightness',
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATIC_MAGNITUDE : 'chromatic magnitude',
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_GREEN_RED : 'balance - green-red',
    SORT_FILES_BY_AVERAGE_COLOUR_CHROMATICITY_BLUE_YELLOW : 'balance - blue-yellow',
    SORT_FILES_BY_AVERAGE_COLOUR_HUE : 'hue',
    SORT_FILES_BY_RATIO : 'resolution ratio',
    SORT_FILES_BY_WIDTH : 'width',
    SORT_FILES_BY_APPROX_BITRATE : 'approximate bitrate',
    SORT_FILES_BY_FILESIZE : 'filesize',
    SORT_FILES_BY_MIME : 'filetype',
    SORT_FILES_BY_HAS_AUDIO : 'has audio',
    SORT_FILES_BY_IMPORT_TIME : 'import time',
    SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP : 'modified time',
    SORT_FILES_BY_ARCHIVED_TIMESTAMP : 'archived time',
    SORT_FILES_BY_LAST_VIEWED_TIME : 'last viewed time',
    SORT_FILES_BY_RANDOM : 'random',
    SORT_FILES_BY_HASH : 'hash - sha256',
    SORT_FILES_BY_PIXEL_HASH : 'hash - pixel hash',
    SORT_FILES_BY_BLURHASH : 'hash - blurhash',
    SORT_FILES_BY_NUM_TAGS : 'number of tags',
    SORT_FILES_BY_MEDIA_VIEWS : 'views',
    SORT_FILES_BY_MEDIA_VIEWTIME : 'viewtime'
}

sort_type_string_lookup = {}

for sort_type in SYSTEM_SORT_TYPES:
    
    ms = system_sort_type_submetatype_string_lookup[ sort_type ]
    s = sort_type_basic_string_lookup[ sort_type ]
    
    if ms is not None:
        
        s = '{}: {}'.format( ms, s )
        
    
    sort_type_string_lookup[ sort_type ] = s
    

special_sort_sort_override = {
    SORT_FILES_BY_WIDTH : 'dimensions 0',
    SORT_FILES_BY_HEIGHT : 'dimensions 1'
}

def magico_sort_sort( sort_type ):
    
    # we just want to sort by sort_type_string_lookup values tbh, EXCEPT we want to put width above height in the dimensions list
    
    if sort_type in special_sort_sort_override:
        
        return special_sort_sort_override[ sort_type ]
        
    else:
        
        return sort_type_string_lookup[ sort_type ]
        
    

SYSTEM_SORT_TYPES_SORT_CONTROL_SORTED = sorted( SYSTEM_SORT_TYPES, key = lambda sst: magico_sort_sort( sst ) )

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
STATUS_SUCCESSFUL_AND_CHILD_FILES = 9

status_string_lookup = {
    STATUS_UNKNOWN : 'unknown',
    STATUS_SUCCESSFUL_AND_NEW : 'successful',
    STATUS_SUCCESSFUL_BUT_REDUNDANT : 'already in db',
    STATUS_DELETED : 'deleted',
    STATUS_ERROR : 'error',
    STATUS_NEW : 'new',
    STATUS_PAUSED : 'paused',
    STATUS_VETOED : 'ignored',
    STATUS_SKIPPED : 'skipped',
    STATUS_SUCCESSFUL_AND_CHILD_FILES : 'created children'
}

SUCCESSFUL_IMPORT_STATES = { STATUS_SUCCESSFUL_AND_NEW, STATUS_SUCCESSFUL_BUT_REDUNDANT, STATUS_SUCCESSFUL_AND_CHILD_FILES }
UNSUCCESSFUL_IMPORT_STATES = { STATUS_DELETED, STATUS_ERROR, STATUS_VETOED }
FAILED_IMPORT_STATES = { STATUS_ERROR, STATUS_VETOED }

TAG_PRESENTATION_SEARCH_PAGE = 0
TAG_PRESENTATION_SEARCH_PAGE_MANAGE_TAGS = 1
TAG_PRESENTATION_MEDIA_VIEWER = 2
TAG_PRESENTATION_MEDIA_VIEWER_MANAGE_TAGS = 3

ZOOM_NEAREST = 0 # pixelly garbage
ZOOM_LINEAR = 1 # simple and quick
ZOOM_AREA = 2 # for shrinking without moire
ZOOM_CUBIC = 3 # for interpolating, pretty good
ZOOM_LANCZOS4 = 4 # for interpolating, noice

zoom_string_lookup = {
    ZOOM_NEAREST : 'nearest neighbour',
    ZOOM_LINEAR : 'bilinear interpolation',
    ZOOM_AREA : 'pixel area resampling',
    ZOOM_CUBIC : '4x4 bilinear interpolation',
    ZOOM_LANCZOS4 : '8x8 Lanczos interpolation'
}

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
        self.zoom_cog = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'zoom_cog.png' ) )
        self.eye = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'eye.png' ) )
        self.fullscreen_switch = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'fullscreen_switch.png' ) )
        self.open_externally = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'open_externally.png' ) )
        self.move = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'move.png' ) )
        self.move_cursor = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'move32x.png' ) )
        
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
        
        #self.listctrl = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'listctrl.png' ) )
        
        self.page_with_text = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'page_with_text.png' ) )
        
        self.copy = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'copy.png' ) )
        self.paste = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'paste.png' ) )
        
        self.eight_chan = QG.QPixmap( os.path.join( HC.STATIC_DIR, '8chan.png' ) )
        
        self.first = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'first.png' ) )
        self.previous = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'previous.png' ) )
        self.next_bmp = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'next.png' ) )
        self.last = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'last.png' ) )
        self.pair = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'pair.png' ) )
        

global_pixmaps = GlobalPixmaps.instance

class GlobalIcons( object ):
    
    my_instance = None
    
    def __init__( self ):
        
        self._Initialise()
        
    
    @staticmethod
    def instance() -> 'GlobalIcons':
        
        if GlobalIcons.my_instance is None:
            
            GlobalIcons.my_instance = GlobalIcons()
            
        
        return GlobalIcons.my_instance
        
    
    def _Initialise( self ):
                
        self.hydrus = QG.QIcon( os.path.join( HC.STATIC_DIR, 'hydrus_black_square.svg' ) )
        self.github = QG.QIcon( os.path.join( HC.STATIC_DIR, 'github.svg' ) )
        self.x = QG.QIcon( os.path.join( HC.STATIC_DIR, 'x.svg' ) )
        self.tumblr = QG.QIcon( os.path.join( HC.STATIC_DIR, 'tumblr.svg' ) )
        self.discord = QG.QIcon( os.path.join( HC.STATIC_DIR, 'discord.svg' ) )
        self.patreon = QG.QIcon( os.path.join( HC.STATIC_DIR, 'patreon.svg' ) )


global_icons = GlobalIcons.instance

DEFAULT_LOCAL_TAG_SERVICE_KEY = b'local tags'

DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY = b'downloader tags'

LOCAL_FILE_SERVICE_KEY = b'local files'

LOCAL_UPDATE_SERVICE_KEY = b'repository updates'

LOCAL_BOORU_SERVICE_KEY = b'local booru'

LOCAL_NOTES_SERVICE_KEY = b'local notes'

DEFAULT_FAVOURITES_RATING_SERVICE_KEY = b'favourites'

CLIENT_API_SERVICE_KEY = b'client api'

TRASH_SERVICE_KEY = b'trash'

COMBINED_LOCAL_MEDIA_SERVICE_KEY = b'all local media'
COMBINED_LOCAL_FILE_SERVICE_KEY = b'all local files'

COMBINED_FILE_SERVICE_KEY = b'all known files'

COMBINED_DELETED_FILE_SERVICE_KEY = b'all deleted files'

COMBINED_TAG_SERVICE_KEY = b'all known tags'

TEST_SERVICE_KEY = b'test service'
