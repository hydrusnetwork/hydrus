import HydrusConstants as HC
import os
import wx
import wx.lib.newevent

ID_NULL = wx.NewId()

# timers

ID_TIMER_UPDATES = wx.NewId()

#

BLANK_PHASH = '\x80\x00\x00\x00\x00\x00\x00\x00' # first bit 1 but everything else 0 means only significant part of dct was [0,0], which represents flat colour

CAN_HIDE_MOUSE = True

# Hue is generally 200, Sat and Lum changes based on need
COLOUR_LIGHT_SELECTED = wx.Colour( 235, 248, 255 )
COLOUR_SELECTED = wx.Colour( 217, 242, 255 )
COLOUR_SELECTED_DARK = wx.Colour( 1, 17, 26 )
COLOUR_UNSELECTED = wx.Colour( 223, 227, 230 )

COLOUR_MESSAGE = wx.Colour( 230, 246, 255 )

SHORTCUT_HELP = '''You can set up many custom shortcuts in file->options->shortcuts. Please check that to see your current mapping.

Some shortcuts remain hardcoded, however:

- While Browsing -
Ctrl + A - Select all
Escape - Deselect all
Ctrl + C - Copy selected files to clipboard

- In Media Viewer -
Shift-LeftClick-Drag - Drag (in Filter)
Ctrl + MouseWheel - Zoom
Z - Zoom Full/Fit'''

COLLECT_BY_S = 0
COLLECT_BY_SV = 1
COLLECT_BY_SVC = 2
NO_COLLECTIONS = 3

COLLECTION_CHOICES = [ 'collect by series', 'collect by series-volume', 'collect by series-volume-chapter', 'no collections' ]

collection_enum_lookup = {}

collection_enum_lookup[ 'collect by series' ] = COLLECT_BY_S
collection_enum_lookup[ 'collect by series-volume' ] = COLLECT_BY_SV
collection_enum_lookup[ 'collect by series-volume-chapter' ] = COLLECT_BY_SVC
collection_enum_lookup[ 'no collections' ] = NO_COLLECTIONS

collection_string_lookup = {}

collection_string_lookup[ COLLECT_BY_S ] = 'collect by series'
collection_string_lookup[ COLLECT_BY_SV ] = 'collect by series-volume'
collection_string_lookup[ COLLECT_BY_SVC ] = 'collect by series-volume-chapter'
collection_string_lookup[ NO_COLLECTIONS ] = 'no collections'

if HC.PLATFORM_OSX:
    
    DELETE_KEYS = ( wx.WXK_BACK, wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE )
    
else:
    
    DELETE_KEYS = ( wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE )
    

DISCRIMINANT_INBOX = 0
DISCRIMINANT_LOCAL = 1
DISCRIMINANT_NOT_LOCAL = 2
DISCRIMINANT_ARCHIVE = 3
DISCRIMINANT_DOWNLOADING = 4
DISCRIMINANT_LOCAL_BUT_NOT_IN_TRASH = 5

DUMPER_NOT_DUMPED = 0
DUMPER_DUMPED_OK = 1
DUMPER_RECOVERABLE_ERROR = 2
DUMPER_UNRECOVERABLE_ERROR = 3

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

FLAGS_NONE = wx.SizerFlags( 0 )

FLAGS_SMALL_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 2 )
FLAGS_BIG_INDENT = wx.SizerFlags( 0 ).Border( wx.ALL, 10 )

FLAGS_CENTER = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Center()

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_DEPTH_ONLY = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_SIZER_CENTER = wx.SizerFlags( 2 ).Center()

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()
FLAGS_EXPAND_SIZER_DEPTH_ONLY = wx.SizerFlags( 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_BUTTON_SIZER = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )

FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_VCENTER = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )
FLAGS_SIZER_VCENTER = wx.SizerFlags( 0 ).Align( wx.ALIGN_CENTRE_VERTICAL )
FLAGS_VCENTER_EXPAND_DEPTH_ONLY = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

DAY = 0
WEEK = 1
MONTH = 2

RESTRICTION_MIN_RESOLUTION = 0
RESTRICTION_MAX_RESOLUTION = 1
RESTRICTION_MAX_FILE_SIZE = 2
RESTRICTION_ALLOWED_MIMES = 3

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

MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL = 0
MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL_PAUSED = 1
MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED = 2
MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED = 3
MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON = 4
MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY = 5
MEDIA_VIEWER_ACTION_DO_NOT_SHOW = 6

media_viewer_action_string_lookup = {}

media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL ] = 'show as normal'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL_PAUSED ] = 'show as normal, but start paused'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED ] = 'show, but initially behind an embed button'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED ] = 'show, but initially behind an embed button, and start paused'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON ] = 'show an \'open externally\' button'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY ] = 'do not show in the media viewer. on thumbnail activation, open externally'
media_viewer_action_string_lookup[ MEDIA_VIEWER_ACTION_DO_NOT_SHOW ] = 'do not show at all'

static_full_support = [ MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY ]
animated_full_support = [ MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL_PAUSED, MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED_PAUSED, MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY ]
no_support = [ MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, MEDIA_VIEWER_ACTION_DO_NOT_SHOW ]

media_viewer_capabilities = {}

media_viewer_capabilities[ HC.IMAGE_JPEG ] = static_full_support
media_viewer_capabilities[ HC.IMAGE_PNG ] = static_full_support
media_viewer_capabilities[ HC.IMAGE_GIF ] = animated_full_support

if HC.PLATFORM_WINDOWS:
    
    media_viewer_capabilities[ HC.APPLICATION_FLASH ] = [ MEDIA_VIEWER_ACTION_SHOW_AS_NORMAL, MEDIA_VIEWER_ACTION_SHOW_BEHIND_EMBED, MEDIA_VIEWER_ACTION_SHOW_OPEN_EXTERNALLY_BUTTON, MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY, MEDIA_VIEWER_ACTION_DO_NOT_SHOW ]
    
else:
    
    media_viewer_capabilities[ HC.APPLICATION_FLASH ] = no_support
    

media_viewer_capabilities[ HC.APPLICATION_PDF ] = no_support
media_viewer_capabilities[ HC.VIDEO_AVI ] = animated_full_support
media_viewer_capabilities[ HC.VIDEO_FLV ] = animated_full_support
media_viewer_capabilities[ HC.VIDEO_MOV ] = animated_full_support
media_viewer_capabilities[ HC.VIDEO_MP4 ] = animated_full_support
media_viewer_capabilities[ HC.VIDEO_MKV ] = animated_full_support
media_viewer_capabilities[ HC.VIDEO_WEBM ] = animated_full_support
media_viewer_capabilities[ HC.VIDEO_MPEG ] = animated_full_support
media_viewer_capabilities[ HC.VIDEO_WMV ] = animated_full_support
media_viewer_capabilities[ HC.AUDIO_MP3 ] = no_support
media_viewer_capabilities[ HC.AUDIO_OGG ] = no_support
media_viewer_capabilities[ HC.AUDIO_FLAC ] = no_support
media_viewer_capabilities[ HC.AUDIO_WMA ] = no_support
media_viewer_capabilities[ HC.APPLICATION_HYDRUS_UPDATE_CONTENT ] = no_support
media_viewer_capabilities[ HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS ] = no_support

MEDIA_VIEWER_SCALE_100 = 0
MEDIA_VIEWER_SCALE_MAX_REGULAR = 1
MEDIA_VIEWER_SCALE_TO_CANVAS = 2

media_viewer_scale_string_lookup = {}

media_viewer_scale_string_lookup[ MEDIA_VIEWER_SCALE_100 ] = 'show at 100%'
media_viewer_scale_string_lookup[ MEDIA_VIEWER_SCALE_MAX_REGULAR ] = 'scale to the largest regular zoom that fits'
media_viewer_scale_string_lookup[ MEDIA_VIEWER_SCALE_TO_CANVAS ] = 'scale to the canvas size'

SHUTDOWN_TIMESTAMP_VACUUM = 0
SHUTDOWN_TIMESTAMP_FATTEN_AC_CACHE = 1
SHUTDOWN_TIMESTAMP_DELETE_ORPHANS = 2

( SizeChangedEvent, EVT_SIZE_CHANGED ) = wx.lib.newevent.NewCommandEvent()

SORT_BY_SMALLEST = 0
SORT_BY_LARGEST = 1
SORT_BY_SHORTEST = 2
SORT_BY_LONGEST = 3
SORT_BY_NEWEST = 4
SORT_BY_OLDEST = 5
SORT_BY_MIME = 6
SORT_BY_RANDOM = 7
SORT_BY_LEXICOGRAPHIC_ASC = 8
SORT_BY_LEXICOGRAPHIC_DESC = 9
SORT_BY_INCIDENCE_ASC = 10
SORT_BY_INCIDENCE_DESC = 11
SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC = 12
SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC = 13
SORT_BY_INCIDENCE_NAMESPACE_ASC = 14
SORT_BY_INCIDENCE_NAMESPACE_DESC = 15
SORT_BY_WIDTH_ASC = 16
SORT_BY_WIDTH_DESC = 17
SORT_BY_HEIGHT_ASC = 18
SORT_BY_HEIGHT_DESC = 19
SORT_BY_RATIO_ASC = 20
SORT_BY_RATIO_DESC = 21
SORT_BY_NUM_PIXELS_ASC = 22
SORT_BY_NUM_PIXELS_DESC = 23

SORT_CHOICES = []

SORT_CHOICES.append( ( 'system', SORT_BY_SMALLEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_LARGEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_SHORTEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_LONGEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_NEWEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_OLDEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_WIDTH_ASC ) )
SORT_CHOICES.append( ( 'system', SORT_BY_WIDTH_DESC ) )
SORT_CHOICES.append( ( 'system', SORT_BY_HEIGHT_ASC ) )
SORT_CHOICES.append( ( 'system', SORT_BY_HEIGHT_DESC ) )
SORT_CHOICES.append( ( 'system', SORT_BY_RATIO_DESC ) )
SORT_CHOICES.append( ( 'system', SORT_BY_RATIO_ASC ) )
SORT_CHOICES.append( ( 'system', SORT_BY_NUM_PIXELS_ASC ) )
SORT_CHOICES.append( ( 'system', SORT_BY_NUM_PIXELS_DESC ) )
SORT_CHOICES.append( ( 'system', SORT_BY_MIME ) )
SORT_CHOICES.append( ( 'system', SORT_BY_RANDOM ) )

sort_string_lookup = {}

sort_string_lookup[ SORT_BY_SMALLEST ] = 'smallest filesize first'
sort_string_lookup[ SORT_BY_LARGEST ] = 'largest filesize first'
sort_string_lookup[ SORT_BY_SHORTEST ] = 'shortest duration first'
sort_string_lookup[ SORT_BY_LONGEST ] = 'longest duration first'
sort_string_lookup[ SORT_BY_NEWEST ] = 'most recently imported first'
sort_string_lookup[ SORT_BY_OLDEST ] = 'least recently imported first'
sort_string_lookup[ SORT_BY_MIME ] = 'mime'
sort_string_lookup[ SORT_BY_RANDOM ] = 'random order'
sort_string_lookup[ SORT_BY_WIDTH_ASC ] = 'least wide first'
sort_string_lookup[ SORT_BY_WIDTH_DESC ] = 'most wide first'
sort_string_lookup[ SORT_BY_HEIGHT_ASC ] = 'least tall first'
sort_string_lookup[ SORT_BY_HEIGHT_DESC ] = 'most tall first'
sort_string_lookup[ SORT_BY_RATIO_ASC ] = 'tallest ratio first'
sort_string_lookup[ SORT_BY_RATIO_DESC ] = 'widest ratio first'
sort_string_lookup[ SORT_BY_NUM_PIXELS_ASC ] = 'fewest pixels first'
sort_string_lookup[ SORT_BY_NUM_PIXELS_DESC ] = 'most pixels first'

STATUS_UNKNOWN = 0
STATUS_SUCCESSFUL = 1
STATUS_REDUNDANT = 2
STATUS_DELETED = 3
STATUS_FAILED = 4
STATUS_NEW = 5
STATUS_PAUSED = 6
STATUS_UNINTERESTING_MIME = 7
STATUS_SKIPPED = 8

status_string_lookup = {}

status_string_lookup[ STATUS_UNKNOWN ] = ''
status_string_lookup[ STATUS_SUCCESSFUL ] = 'successful'
status_string_lookup[ STATUS_REDUNDANT ] = 'already in db'
status_string_lookup[ STATUS_DELETED ] = 'deleted'
status_string_lookup[ STATUS_FAILED ] = 'failed'
status_string_lookup[ STATUS_NEW ] = 'new'
status_string_lookup[ STATUS_PAUSED ] = 'paused'
status_string_lookup[ STATUS_UNINTERESTING_MIME ] = 'uninteresting mime'
status_string_lookup[ STATUS_SKIPPED ] = 'skipped'

THUMBNAIL_MARGIN = 2
THUMBNAIL_BORDER = 1

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

class GlobalBMPs( object ):
    
    @staticmethod
    def STATICInitialise():
        
        # these have to be created after the wxApp is instantiated, for silly GDI reasons
        
        GlobalBMPs.bold = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'text_bold.png' ) )
        GlobalBMPs.italic = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'text_italic.png' ) )
        GlobalBMPs.underline = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'text_underline.png' ) )
        
        GlobalBMPs.align_left = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'text_align_left.png' ) )
        GlobalBMPs.align_center = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'text_align_center.png' ) )
        GlobalBMPs.align_right = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'text_align_right.png' ) )
        GlobalBMPs.align_justify = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'text_align_justify.png' ) )
        
        GlobalBMPs.indent_less = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'text_indent_remove.png' ) )
        GlobalBMPs.indent_more = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'text_indent.png' ) )
        
        GlobalBMPs.font = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'font.png' ) )
        GlobalBMPs.colour = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'color_swatch.png' ) )
        
        GlobalBMPs.link = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'link.png' ) )
        GlobalBMPs.link_break = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'link_break.png' ) )
        
        GlobalBMPs.transparent = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'transparent.png' ) )
        GlobalBMPs.downloading = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'downloading.png' ) )
        GlobalBMPs.file_repository = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'file_repository_small.png' ) )
        GlobalBMPs.file_repository_pending = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'file_repository_pending_small.png' ) )
        GlobalBMPs.file_repository_petitioned = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'file_repository_petitioned_small.png' ) )
        GlobalBMPs.ipfs = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'ipfs_small.png' ) )
        GlobalBMPs.ipfs_pending = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'ipfs_pending_small.png' ) )
        GlobalBMPs.ipfs_petitioned = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'ipfs_petitioned_small.png' ) )
        
        GlobalBMPs.collection = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'collection.png' ) )
        GlobalBMPs.inbox = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'inbox.png' ) )
        GlobalBMPs.trash = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'trash.png' ) )
        
        GlobalBMPs.archive = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'archive.png' ) )
        GlobalBMPs.to_inbox = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'to_inbox.png' ) )
        GlobalBMPs.delete = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'trash.png' ) )
        GlobalBMPs.trash_delete = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'delete.png' ) )
        GlobalBMPs.undelete = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'undelete.png' ) )
        GlobalBMPs.zoom_in = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'zoom_in.png' ) )
        GlobalBMPs.zoom_out = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'zoom_out.png' ) )
        GlobalBMPs.zoom_switch = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'zoom_switch.png' ) )
        GlobalBMPs.fullscreen_switch = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'fullscreen_switch.png' ) )
        GlobalBMPs.open_externally = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'open_externally.png' ) )
        
        GlobalBMPs.dump_ok = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'dump_ok.png' ) )
        GlobalBMPs.dump_recoverable = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'dump_recoverable.png' ) )
        GlobalBMPs.dump_fail = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'dump_fail.png' ) )
        
        GlobalBMPs.cog = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'cog.png' ) )
        GlobalBMPs.check = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'check.png' ) )
        GlobalBMPs.pause = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'pause.png' ) )
        GlobalBMPs.play = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'play.png' ) )
        GlobalBMPs.stop = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'stop.png' ) )
        
        GlobalBMPs.seed_cache = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'seed_cache.png' ) )
        
        GlobalBMPs.eight_chan = wx.Bitmap( os.path.join( HC.STATIC_DIR, '8chan.png' ) )
        GlobalBMPs.twitter = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'twitter.png' ) )
        GlobalBMPs.tumblr = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'tumblr.png' ) )
        GlobalBMPs.discord = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'discord.png' ) )
        GlobalBMPs.patreon = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'patreon.png' ) )
        
        GlobalBMPs.first = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'first.png' ) )
        GlobalBMPs.previous = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'previous.png' ) )
        GlobalBMPs.next = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'next.png' ) )
        GlobalBMPs.last = wx.Bitmap( os.path.join( HC.STATIC_DIR, 'last.png' ) )
        

LOCAL_TAG_SERVICE_KEY = 'local tags'

LOCAL_FILE_SERVICE_KEY = 'local files'

LOCAL_UPDATE_SERVICE_KEY = 'repository updates'

LOCAL_BOORU_SERVICE_KEY = 'local booru'

TRASH_SERVICE_KEY = 'trash'

COMBINED_LOCAL_FILE_SERVICE_KEY = 'all local files'

COMBINED_FILE_SERVICE_KEY = 'all known files'

COMBINED_TAG_SERVICE_KEY = 'all known tags'
