import collections
import HydrusConstants as HC
import HydrusExceptions
import multipart
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

FLAGS_EXPAND_PERPENDICULAR = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_BOTH_WAYS = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Expand()
FLAGS_EXPAND_DEPTH_ONLY = wx.SizerFlags( 2 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_EXPAND_SIZER_PERPENDICULAR = wx.SizerFlags( 0 ).Expand()
FLAGS_EXPAND_SIZER_BOTH_WAYS = wx.SizerFlags( 2 ).Expand()
FLAGS_EXPAND_SIZER_DEPTH_ONLY = wx.SizerFlags( 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

FLAGS_BUTTON_SIZER = wx.SizerFlags( 0 ).Align( wx.ALIGN_RIGHT )

FLAGS_LONE_BUTTON = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_RIGHT )

FLAGS_MIXED = wx.SizerFlags( 0 ).Border( wx.ALL, 2 ).Align( wx.ALIGN_CENTER_VERTICAL )

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

THUMBNAIL_MARGIN = 2
THUMBNAIL_BORDER = 1

class GlobalBMPs( object ):
    
    @staticmethod
    def STATICInitialise():
        
        # these have to be created after the wxApp is instantiated, for silly GDI reasons
        
        GlobalBMPs.bold_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_bold.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.italic_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_italic.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.underline_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_underline.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.align_left_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_align_left.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.align_center_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_align_center.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.align_right_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_align_right.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.align_justify_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_align_justify.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.indent_less_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_indent_remove.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.indent_more_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'text_indent.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.font_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'font.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.colour_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'color_swatch.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.link_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'link.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.link_break_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'silk icons' + os.path.sep + 'link_break.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        
        GlobalBMPs.transparent_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'transparent.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.downloading_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'downloading.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.file_repository_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'file_repository_small.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.file_repository_pending_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'file_repository_pending_small.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.file_repository_petitioned_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'file_repository_petitioned_small.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.inbox_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'inbox.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.collection_bmp = wx.Image( HC.STATIC_DIR + os.path.sep + 'collection.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.dump_ok = wx.Image( HC.STATIC_DIR + os.path.sep + 'dump_ok.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.dump_recoverable = wx.Image( HC.STATIC_DIR + os.path.sep + 'dump_recoverable.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()
        GlobalBMPs.dump_fail = wx.Image( HC.STATIC_DIR + os.path.sep + 'dump_fail.png', type=wx.BITMAP_TYPE_PNG ).ConvertToBitmap()

LOCAL_TAG_SERVICE_KEY = 'local tags'

LOCAL_FILE_SERVICE_KEY = 'local files'

LOCAL_BOORU_SERVICE_KEY = 'local booru'

COMBINED_FILE_SERVICE_KEY = 'all known files'

COMBINED_TAG_SERVICE_KEY = 'all known tags'

        
    