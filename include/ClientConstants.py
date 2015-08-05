import collections
import HydrusConstants as HC
import HydrusExceptions
import os
import sys
import threading
import traceback
import wx

ID_NULL = wx.NewId()

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

- In Fullscreen -
Shift-LeftClick-Drag - Drag (in Filter)
Ctrl + MouseWheel - Zoom
Z - Zoom Full/Fit'''

CLIENT_DESCRIPTION = '''This client is the media management application of the hydrus software suite.'''

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

DISCRIMINANT_INBOX = 0
DISCRIMINANT_LOCAL = 1
DISCRIMINANT_NOT_LOCAL = 2
DISCRIMINANT_ARCHIVE = 3
DISCRIMINANT_DOWNLOADING = 3

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

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

DAY = 0
WEEK = 1
MONTH = 2

RESTRICTION_MIN_RESOLUTION = 0
RESTRICTION_MAX_RESOLUTION = 1
RESTRICTION_MAX_FILE_SIZE = 2
RESTRICTION_ALLOWED_MIMES = 3

SHUTDOWN_TIMESTAMP_VACUUM = 0
SHUTDOWN_TIMESTAMP_FATTEN_AC_CACHE = 1
SHUTDOWN_TIMESTAMP_DELETE_ORPHANS = 2

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

SORT_CHOICES = []

SORT_CHOICES.append( ( 'system', SORT_BY_SMALLEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_LARGEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_SHORTEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_LONGEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_NEWEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_OLDEST ) )
SORT_CHOICES.append( ( 'system', SORT_BY_MIME ) )
SORT_CHOICES.append( ( 'system', SORT_BY_RANDOM ) )

sort_enum_lookup = {}

sort_enum_lookup[ 'smallest first' ] = SORT_BY_SMALLEST
sort_enum_lookup[ 'largest first' ] = SORT_BY_LARGEST
sort_enum_lookup[ 'shortest first' ] = SORT_BY_SHORTEST
sort_enum_lookup[ 'longest first' ] = SORT_BY_LONGEST
sort_enum_lookup[ 'newest first' ] = SORT_BY_NEWEST
sort_enum_lookup[ 'oldest first' ] = SORT_BY_OLDEST
sort_enum_lookup[ 'order by mime' ] = SORT_BY_MIME
sort_enum_lookup[ 'random order' ] = SORT_BY_RANDOM

sort_string_lookup = {}

sort_string_lookup[ SORT_BY_SMALLEST ] = 'smallest first'
sort_string_lookup[ SORT_BY_LARGEST ] = 'largest first'
sort_string_lookup[ SORT_BY_SHORTEST ] = 'shortest first'
sort_string_lookup[ SORT_BY_LONGEST ] = 'longest first'
sort_string_lookup[ SORT_BY_NEWEST ] = 'newest first'
sort_string_lookup[ SORT_BY_OLDEST ] = 'oldest first'
sort_string_lookup[ SORT_BY_MIME ] = 'mime'
sort_string_lookup[ SORT_BY_RANDOM ] = 'random order'

STATUS_UNKNOWN = 0
STATUS_SUCCESSFUL = 1
STATUS_REDUNDANT = 2
STATUS_DELETED = 3
STATUS_FAILED = 4
STATUS_NEW = 5
STATUS_PAUSED = 5

status_string_lookup = {}

status_string_lookup[ STATUS_UNKNOWN ] = ''
status_string_lookup[ STATUS_SUCCESSFUL ] = 'successful'
status_string_lookup[ STATUS_REDUNDANT ] = 'already in db'
status_string_lookup[ STATUS_DELETED ] = 'deleted'
status_string_lookup[ STATUS_FAILED ] = 'failed'
status_string_lookup[ STATUS_NEW ] = 'new'
status_string_lookup[ STATUS_PAUSED ] = 'paused'

THUMBNAIL_MARGIN = 2
THUMBNAIL_BORDER = 1

class GlobalBMPs( object ):
    
    @staticmethod
    def STATICInitialise():
        
        # these have to be created after the wxApp is instantiated, for silly GDI reasons
        
        GlobalBMPs.bold = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'text_bold.png' )
        GlobalBMPs.italic = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'text_italic.png' )
        GlobalBMPs.underline = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'text_underline.png' )
        
        GlobalBMPs.align_left = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'text_align_left.png' )
        GlobalBMPs.align_center = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'text_align_center.png' )
        GlobalBMPs.align_right = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'text_align_right.png' )
        GlobalBMPs.align_justify = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'text_align_justify.png' )
        
        GlobalBMPs.indent_less = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'text_indent_remove.png' )
        GlobalBMPs.indent_more = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'text_indent.png' )
        
        GlobalBMPs.font = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'font.png' )
        GlobalBMPs.colour = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'color_swatch.png' )
        
        GlobalBMPs.link = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'link.png' )
        GlobalBMPs.link_break = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'link_break.png' )
        
        GlobalBMPs.transparent = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'transparent.png' )
        GlobalBMPs.downloading = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'downloading.png' )
        GlobalBMPs.file_repository = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'file_repository_small.png' )
        GlobalBMPs.file_repository_pending = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'file_repository_pending_small.png' )
        GlobalBMPs.file_repository_petitioned = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'file_repository_petitioned_small.png' )
        
        GlobalBMPs.collection = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'collection.png' )
        GlobalBMPs.inbox = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'inbox.png' )
        GlobalBMPs.trash = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'trash.png' )
        
        GlobalBMPs.archive = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'archive.png' )
        GlobalBMPs.to_inbox = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'to_inbox.png' )
        GlobalBMPs.delete = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'trash.png' )
        GlobalBMPs.trash_delete = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'delete.png' )
        GlobalBMPs.undelete = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'undelete.png' )
        GlobalBMPs.zoom_in = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'zoom_in.png' )
        GlobalBMPs.zoom_out = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'zoom_out.png' )
        GlobalBMPs.zoom_switch = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'zoom_switch.png' )
        GlobalBMPs.fullscreen_switch = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'fullscreen_switch.png' )
        GlobalBMPs.open_externally = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'open_externally.png' )
        
        GlobalBMPs.dump_ok = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'dump_ok.png' )
        GlobalBMPs.dump_recoverable = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'dump_recoverable.png' )
        GlobalBMPs.dump_fail = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'dump_fail.png' )
        
        GlobalBMPs.pause = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'pause.png' )
        GlobalBMPs.play = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'play.png' )
        GlobalBMPs.stop = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'stop.png' )
        
        GlobalBMPs.seed_cache = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'seed_cache.png' )
        
        GlobalBMPs.eight_chan = wx.Bitmap( HC.STATIC_DIR + os.path.sep + '8chan.png' )
        GlobalBMPs.twitter = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'twitter.png' )
        GlobalBMPs.tumblr = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'tumblr.png' )
        
        GlobalBMPs.first = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'first.png' )
        GlobalBMPs.previous = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'previous.png' )
        GlobalBMPs.next = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'next.png' )
        GlobalBMPs.last = wx.Bitmap( HC.STATIC_DIR + os.path.sep + 'last.png' )
        

LOCAL_TAG_SERVICE_KEY = 'local tags'

LOCAL_FILE_SERVICE_KEY = 'local files'

LOCAL_BOORU_SERVICE_KEY = 'local booru'

TRASH_SERVICE_KEY = 'trash'

COMBINED_FILE_SERVICE_KEY = 'all known files'

COMBINED_TAG_SERVICE_KEY = 'all known tags'
