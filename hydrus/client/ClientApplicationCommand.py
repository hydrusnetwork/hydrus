import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG

SIMPLE_ARCHIVE_DELETE_FILTER_BACK = 0
SIMPLE_ARCHIVE_DELETE_FILTER_DELETE = 1
SIMPLE_ARCHIVE_DELETE_FILTER_KEEP = 2
SIMPLE_ARCHIVE_DELETE_FILTER_SKIP = 3
SIMPLE_ARCHIVE_FILE = 4
SIMPLE_CHECK_ALL_IMPORT_FOLDERS = 5
SIMPLE_CLOSE_MEDIA_VIEWER = 6
SIMPLE_CLOSE_PAGE = 7
LEGACY_SIMPLE_COPY_BMP = 8
LEGACY_SIMPLE_COPY_BMP_OR_FILE_IF_NOT_BMPABLE = 9
SIMPLE_COPY_FILES = 10
LEGACY_SIMPLE_COPY_MD5_HASH = 11
SIMPLE_COPY_FILE_PATHS = 12
LEGACY_SIMPLE_COPY_SHA1_HASH = 13
LEGACY_SIMPLE_COPY_SHA256_HASH = 14
LEGACY_SIMPLE_COPY_SHA512_HASH = 15
SIMPLE_DELETE_FILE = 16
SIMPLE_DUPLICATE_FILTER_ALTERNATES = 17
SIMPLE_DUPLICATE_FILTER_BACK = 18
SIMPLE_DUPLICATE_FILTER_CUSTOM_ACTION = 19
SIMPLE_DUPLICATE_FILTER_EXACTLY_THE_SAME = 20
SIMPLE_DUPLICATE_FILTER_FALSE_POSITIVE = 21
SIMPLE_DUPLICATE_FILTER_SKIP = 22
SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER = 23
SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH = 24
SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE = 25
SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE_COLLECTIONS = 26
SIMPLE_DUPLICATE_MEDIA_SET_CUSTOM = 27
SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_BETTER = 28
SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_KING = 29
SIMPLE_DUPLICATE_MEDIA_SET_SAME_QUALITY = 30
SIMPLE_EXIT_APPLICATION = 31
SIMPLE_EXPORT_FILES = 32
SIMPLE_EXPORT_FILES_QUICK_AUTO_EXPORT = 33
SIMPLE_FLIP_DARKMODE = 34
SIMPLE_FLIP_DEBUG_FORCE_IDLE_MODE_DO_NOT_SET_THIS = 35
SIMPLE_FOCUS_MEDIA_VIEWER = 36
LEGACY_SIMPLE_GET_SIMILAR_TO_EXACT = 37
LEGACY_SIMPLE_GET_SIMILAR_TO_SIMILAR = 38
LEGACY_SIMPLE_GET_SIMILAR_TO_SPECULATIVE = 39
LEGACY_SIMPLE_GET_SIMILAR_TO_VERY_SIMILAR = 40
SIMPLE_GLOBAL_AUDIO_MUTE = 41
SIMPLE_GLOBAL_AUDIO_MUTE_FLIP = 42
SIMPLE_GLOBAL_AUDIO_UNMUTE = 43
SIMPLE_HIDE_TO_SYSTEM_TRAY = 44
SIMPLE_INBOX_FILE = 45
SIMPLE_LAUNCH_MEDIA_VIEWER = 46
SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER = 47
SIMPLE_MANAGE_FILE_NOTES = 48
SIMPLE_MANAGE_FILE_RATINGS = 49
SIMPLE_MANAGE_FILE_TAGS = 50
SIMPLE_MANAGE_FILE_URLS = 51
SIMPLE_MOVE_ANIMATION_TO_NEXT_FRAME = 52
SIMPLE_MOVE_ANIMATION_TO_PREVIOUS_FRAME = 53
SIMPLE_NEW_DUPLICATE_FILTER_PAGE = 54
SIMPLE_NEW_GALLERY_DOWNLOADER_PAGE = 55
SIMPLE_NEW_PAGE = 56
SIMPLE_NEW_PAGE_OF_PAGES = 57
SIMPLE_NEW_SIMPLE_DOWNLOADER_PAGE = 58
SIMPLE_NEW_URL_DOWNLOADER_PAGE = 59
SIMPLE_NEW_WATCHER_DOWNLOADER_PAGE = 60
SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM = 61
SIMPLE_OPEN_KNOWN_URL = 62
SIMPLE_OPEN_SELECTION_IN_NEW_PAGE = 63
SIMPLE_PAN_BOTTOM_EDGE = 64
SIMPLE_PAN_DOWN = 65
SIMPLE_PAN_HORIZONTAL_CENTER = 66
SIMPLE_PAN_LEFT = 67
SIMPLE_PAN_LEFT_EDGE = 68
SIMPLE_PAN_RIGHT = 69
SIMPLE_PAN_RIGHT_EDGE = 70
SIMPLE_PAN_TOP_EDGE = 71
SIMPLE_PAN_UP = 72
SIMPLE_PAN_VERTICAL_CENTER = 73
SIMPLE_PAUSE_MEDIA = 74
SIMPLE_PAUSE_PLAY_MEDIA = 75
SIMPLE_PAUSE_PLAY_SLIDESHOW = 76
SIMPLE_REDO = 77
SIMPLE_REFRESH = 78
SIMPLE_REFRESH_ALL_PAGES = 79
SIMPLE_REFRESH_PAGE_OF_PAGES_PAGES = 80
SIMPLE_REMOVE_FILE_FROM_VIEW = 81
SIMPLE_RESTART_APPLICATION = 82
SIMPLE_SET_MEDIA_FOCUS = 83
SIMPLE_SET_SEARCH_FOCUS = 84
SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FAVOURITE_TAGS = 85
SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FILE_LOOKUP_SCRIPT_TAGS = 86
SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RECENT_TAGS = 87
SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RELATED_TAGS = 88
SIMPLE_SHOW_HIDE_SPLITTERS = 89
SIMPLE_SHOW_MENU = 90
SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM = 91
SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW = 92
SIMPLE_SYNCHRONISED_WAIT_SWITCH = 93
SIMPLE_UNCLOSE_PAGE = 94
SIMPLE_UNDELETE_FILE = 95
SIMPLE_UNDO = 96
SIMPLE_VIEW_FIRST = 97
SIMPLE_VIEW_LAST = 98
SIMPLE_VIEW_NEXT = 99
SIMPLE_VIEW_PREVIOUS = 100
SIMPLE_ZOOM_IN = 101
SIMPLE_ZOOM_OUT = 102
SIMPLE_EXIT_APPLICATION_FORCE_MAINTENANCE = 103
SIMPLE_ZOOM_IN_VIEWER_CENTER = 104
SIMPLE_ZOOM_OUT_VIEWER_CENTER = 105
SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM_VIEWER_CENTER = 106
SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_ALTERNATE_GROUP = 107
SIMPLE_DUPLICATE_MEDIA_DISSOLVE_ALTERNATE_GROUP = 108
SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_DUPLICATE_GROUP = 109
SIMPLE_DUPLICATE_MEDIA_DISSOLVE_DUPLICATE_GROUP = 110
SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_ALTERNATE_GROUP = 111
SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_DUPLICATE_GROUP = 112
SIMPLE_DUPLICATE_MEDIA_RESET_FOCUSED_POTENTIAL_SEARCH = 113
SIMPLE_DUPLICATE_MEDIA_RESET_POTENTIAL_SEARCH = 114
SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_POTENTIALS = 115
SIMPLE_DUPLICATE_MEDIA_REMOVE_POTENTIALS = 116
SIMPLE_DUPLICATE_MEDIA_SET_POTENTIAL = 117
SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FALSE_POSITIVES = 118
SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FOCUSED_FALSE_POSITIVES = 119
SIMPLE_RUN_ALL_EXPORT_FOLDERS = 120
SIMPLE_MOVE_PAGES_SELECTION_LEFT = 121
SIMPLE_MOVE_PAGES_SELECTION_RIGHT = 122
SIMPLE_MOVE_PAGES_SELECTION_HOME = 123
SIMPLE_MOVE_PAGES_SELECTION_END = 124
SIMPLE_REFRESH_RELATED_TAGS = 125
SIMPLE_AUTOCOMPLETE_FORCE_FETCH = 126
SIMPLE_AUTOCOMPLETE_IME_MODE = 127
SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_LEFT = 128
SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_RIGHT = 129
SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_LEFT = 130
SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_RIGHT = 131
SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_PREVIOUS = 132
SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_NEXT = 133
SIMPLE_MEDIA_SEEK_DELTA = 134
SIMPLE_GLOBAL_PROFILE_MODE_FLIP = 135
SIMPLE_GLOBAL_FORCE_ANIMATION_SCANBAR_SHOW = 136
SIMPLE_OPEN_COMMAND_PALETTE = 137
SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_MAX_ZOOM = 138
SIMPLE_SWITCH_BETWEEN_CANVAS_AND_MAX_ZOOM = 139
SIMPLE_ZOOM_MAX = 140
SIMPLE_ZOOM_CANVAS = 141
SIMPLE_ZOOM_100 = 142
SIMPLE_ZOOM_DEFAULT = 143
SIMPLE_SHOW_DUPLICATES = 144
SIMPLE_MANAGE_FILE_TIMESTAMPS = 145
SIMPLE_OPEN_FILE_IN_FILE_EXPLORER = 146
LEGACY_SIMPLE_COPY_LITTLE_BMP = 147
SIMPLE_MOVE_THUMBNAIL_FOCUS = 148
SIMPLE_SELECT_FILES = 149
SIMPLE_REARRANGE_THUMBNAILS = 150
SIMPLE_MAC_QUICKLOOK = 151
SIMPLE_COPY_URLS = 152
SIMPLE_OPEN_FILE_IN_WEB_BROWSER = 153
SIMPLE_OPEN_SELECTION_IN_NEW_DUPLICATES_FILTER_PAGE = 154
SIMPLE_OPEN_SIMILAR_LOOKING_FILES = 155
SIMPLE_COPY_FILE_HASHES = 156
SIMPLE_COPY_FILE_BITMAP = 157
SIMPLE_COPY_FILE_ID = 158
SIMPLE_COPY_FILE_SERVICE_FILENAMES = 159
SIMPLE_NATIVE_OPEN_FILE_PROPERTIES = 160
SIMPLE_NATIVE_OPEN_FILE_WITH_DIALOG = 161
SIMPLE_RELOAD_CURRENT_STYLESHEET = 162
SIMPLE_FLIP_ICC_PROFILE_APPLICATION = 163
SIMPLE_ZOOM_100_CENTER = 164
SIMPLE_ZOOM_CANVAS_VIEWER_CENTER = 165
SIMPLE_ZOOM_CANVAS_FILL_X = 166
SIMPLE_ZOOM_CANVAS_FILL_X_VIEWER_CENTER = 167
SIMPLE_ZOOM_CANVAS_FILL_Y = 168
SIMPLE_ZOOM_CANVAS_FILL_Y_VIEWER_CENTER = 169
SIMPLE_ZOOM_CANVAS_FILL_AUTO = 170
SIMPLE_ZOOM_CANVAS_FILL_AUTO_VIEWER_CENTER = 171
SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM = 172
SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM_VIEWER_CENTER = 173
SIMPLE_ZOOM_DEFAULT_VIEWER_CENTER = 174
SIMPLE_RESET_PAN_TO_CENTER = 175
SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB = 176
SIMPLE_ZOOM_TO_PERCENTAGE = 177
SIMPLE_ZOOM_TO_PERCENTAGE_CENTER = 178
SIMPLE_RESIZE_WINDOW_TO_MEDIA = 179
SIMPLE_RESIZE_WINDOW_TO_MEDIA_VIEWER_CENTER = 180
SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED = 181
SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER = 182
SIMPLE_OPEN_OPTIONS = 183
SIMPLE_DUPLICATE_MEDIA_CLEAR_INTERNAL_FALSE_POSITIVES = 184
SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB_AND_FOCUS_MEDIA = 185
SIMPLE_VIEW_RANDOM = 186
SIMPLE_UNDO_RANDOM = 187
SIMPLE_FOCUS_TAB_AND_MEDIA = 188
SIMPLE_DUPLICATE_FILTER_APPROVE_AUTO_RESOLUTION = 189
SIMPLE_DUPLICATE_FILTER_DENY_AUTO_RESOLUTION = 190
SIMPLE_FLIP_TRANSPARENCY_CHECKERBOARD_MEDIA_VIEWER = 191
SIMPLE_FLIP_TRANSPARENCY_CHECKERBOARD_MEDIA_VIEWER_DUPLICATE_FILTER = 192
SIMPLE_FLIP_TRANSPARENCY_CHECKERBOARD_GREENSCREEN = 193
SIMPLE_START_SLIDESHOW = 194

REARRANGE_THUMBNAILS_TYPE_FIXED = 0
REARRANGE_THUMBNAILS_TYPE_COMMAND = 1

MOVE_HOME = 0
MOVE_END = 1
MOVE_LEFT = 2
MOVE_RIGHT = 3
MOVE_UP = 4
MOVE_DOWN = 5
MOVE_PAGE_UP = 6
MOVE_PAGE_DOWN = 7
MOVE_TO_FOCUS = 8

move_enum_to_str_lookup = {
    MOVE_HOME : 'home',
    MOVE_END : 'end',
    MOVE_LEFT : 'left',
    MOVE_RIGHT : 'right',
    MOVE_UP : 'up',
    MOVE_DOWN : 'down',
    MOVE_PAGE_UP : 'page up',
    MOVE_PAGE_DOWN : 'page down',
    MOVE_TO_FOCUS : 'to focus'
}

SELECTION_STATUS_NORMAL = 0
SELECTION_STATUS_SHIFT = 1

selection_status_enum_to_str_lookup = {
    SELECTION_STATUS_NORMAL : 'move',
    SELECTION_STATUS_SHIFT : 'shift-select'
}

FILE_COMMAND_TARGET_FOCUSED_FILE = 0
FILE_COMMAND_TARGET_SELECTED_FILES = 1

file_command_target_enum_to_str_lookup = {
    FILE_COMMAND_TARGET_FOCUSED_FILE : 'focused file',
    FILE_COMMAND_TARGET_SELECTED_FILES : 'selected files'
}

BITMAP_TYPE_FULL = 0
BITMAP_TYPE_SOURCE_LOOKUPS = 1
BITMAP_TYPE_FULL_OR_FILE = 2
BITMAP_TYPE_THUMBNAIL = 3

bitmap_type_enum_to_str_lookup = {
    BITMAP_TYPE_FULL : 'full bitmap of image',
    BITMAP_TYPE_SOURCE_LOOKUPS : '1024x1024 scaled for quick source lookups',
    BITMAP_TYPE_FULL_OR_FILE : 'full bitmap; otherwise copy file',
    BITMAP_TYPE_THUMBNAIL : 'thumbnail bitmap',
}

simple_enum_to_str_lookup = {
    SIMPLE_ARCHIVE_DELETE_FILTER_BACK : 'archive/delete filter: back',
    SIMPLE_ARCHIVE_DELETE_FILTER_DELETE : 'archive/delete filter: delete',
    SIMPLE_ARCHIVE_DELETE_FILTER_KEEP : 'archive/delete filter: keep',
    SIMPLE_ARCHIVE_DELETE_FILTER_SKIP : 'archive/delete filter: skip',
    SIMPLE_ARCHIVE_FILE : 'archive file',
    SIMPLE_CHECK_ALL_IMPORT_FOLDERS : 'check all import folders now',
    SIMPLE_CLOSE_MEDIA_VIEWER : 'close media viewer',
    SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB : 'close media viewer and focus the tab the media came from, if possible',
    SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB_AND_FOCUS_MEDIA : 'close media viewer and focus the tab the media came from, if possible, and focus the media',
    SIMPLE_FOCUS_TAB_AND_MEDIA : 'focus the tab the media came from, if possible, and focus the media',
    SIMPLE_CLOSE_PAGE : 'close page',
    LEGACY_SIMPLE_COPY_BMP : 'copy bmp of image',
    LEGACY_SIMPLE_COPY_LITTLE_BMP : 'copy small bmp of image for quick source lookups',
    LEGACY_SIMPLE_COPY_BMP_OR_FILE_IF_NOT_BMPABLE : 'copy bmp of image; otherwise copy file',
    SIMPLE_COPY_FILES : 'copy file',
    SIMPLE_COPY_FILE_PATHS : 'copy file paths',
    LEGACY_SIMPLE_COPY_MD5_HASH : 'copy md5 hash',
    LEGACY_SIMPLE_COPY_SHA1_HASH : 'copy sha1 hash',
    LEGACY_SIMPLE_COPY_SHA256_HASH : 'copy sha256 hash',
    LEGACY_SIMPLE_COPY_SHA512_HASH : 'copy sha512 hash',
    SIMPLE_COPY_FILE_SERVICE_FILENAMES : 'copy ipfs multihash',
    SIMPLE_COPY_FILE_HASHES : 'copy file hashes',
    SIMPLE_COPY_FILE_ID : 'copy file id',
    SIMPLE_COPY_FILE_BITMAP : 'copy file bitmap',
    SIMPLE_DELETE_FILE : 'delete file',
    SIMPLE_DUPLICATE_FILTER_ALTERNATES : 'duplicate filter: set as alternates',
    SIMPLE_DUPLICATE_FILTER_BACK : 'duplicate filter: back',
    SIMPLE_DUPLICATE_FILTER_CUSTOM_ACTION : 'duplicate filter: do custom action',
    SIMPLE_DUPLICATE_FILTER_EXACTLY_THE_SAME : 'duplicate filter: set as the same',
    SIMPLE_DUPLICATE_FILTER_FALSE_POSITIVE : 'duplicate filter: set as not related/false positive',
    SIMPLE_DUPLICATE_FILTER_SKIP : 'duplicate filter: skip',
    SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER : 'duplicate filter: this is better, delete other',
    SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH : 'duplicate filter: this is better, keep both',
    SIMPLE_DUPLICATE_FILTER_APPROVE_AUTO_RESOLUTION : 'duplicate filter: approve auto-resolution pair',
    SIMPLE_DUPLICATE_FILTER_DENY_AUTO_RESOLUTION : 'duplicate filter: deny auto-resolution pair',
    SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE : 'file relationships: set files as alternates',
    SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE_COLLECTIONS : 'file relationships: set collects as separate alternate groups',
    SIMPLE_DUPLICATE_MEDIA_SET_CUSTOM : 'file relationships: do custom action',
    SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_BETTER : 'file relationships: the focused file is a better duplicate',
    SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_KING : 'file relationships: set the focused file as king duplicate',
    SIMPLE_DUPLICATE_MEDIA_SET_SAME_QUALITY : 'file relationships: set files as the same quality duplicates',
    SIMPLE_EXIT_APPLICATION : 'exit program: close',
    SIMPLE_EXPORT_FILES : 'export these files',
    SIMPLE_EXPORT_FILES_QUICK_AUTO_EXPORT : 'export these files (quick auto-export)',
    SIMPLE_FLIP_DARKMODE : 'flip fixed darkmode colours',
    SIMPLE_FLIP_DEBUG_FORCE_IDLE_MODE_DO_NOT_SET_THIS : 'force debug idle mode (do not use this!)',
    SIMPLE_FOCUS_MEDIA_VIEWER : 'keyboard focus: to the media viewer',
    LEGACY_SIMPLE_GET_SIMILAR_TO_EXACT : 'show similar files: 0 (exact)',
    LEGACY_SIMPLE_GET_SIMILAR_TO_SIMILAR : 'show similar files: 4 (similar)',
    LEGACY_SIMPLE_GET_SIMILAR_TO_SPECULATIVE : 'show similar files: 8 (speculative)',
    LEGACY_SIMPLE_GET_SIMILAR_TO_VERY_SIMILAR : 'show similar files: 2 (very similar)',
    SIMPLE_GLOBAL_AUDIO_MUTE : 'mute global audio',
    SIMPLE_GLOBAL_AUDIO_MUTE_FLIP : 'mute/unmute global audio',
    SIMPLE_GLOBAL_AUDIO_UNMUTE : 'unmute global audio',
    SIMPLE_HIDE_TO_SYSTEM_TRAY : 'hide to system tray',
    SIMPLE_INBOX_FILE : 'inbox file',
    SIMPLE_LAUNCH_MEDIA_VIEWER : 'launch the media viewer',
    SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER : 'launch the archive/delete filter',
    SIMPLE_MANAGE_FILE_NOTES : 'manage file notes',
    SIMPLE_MANAGE_FILE_RATINGS : 'manage file ratings',
    SIMPLE_MANAGE_FILE_TAGS : 'manage file tags',
    SIMPLE_MANAGE_FILE_TIMESTAMPS : 'manage file times',
    SIMPLE_MANAGE_FILE_URLS : 'manage file urls',
    SIMPLE_MOVE_PAGES_SELECTION_LEFT : 'move page selection left (cycles up through page of pages at boundaries)',
    SIMPLE_MOVE_PAGES_SELECTION_RIGHT : 'move page selection right (cycles up through page of pages at boundaries)',
    SIMPLE_MOVE_PAGES_SELECTION_HOME : 'move selection to leftmost page',
    SIMPLE_MOVE_PAGES_SELECTION_END : 'move selection to rightmost page',
    SIMPLE_MOVE_ANIMATION_TO_NEXT_FRAME : 'move animation one frame forward',
    SIMPLE_MOVE_ANIMATION_TO_PREVIOUS_FRAME : 'move animation one frame back',
    SIMPLE_NEW_DUPLICATE_FILTER_PAGE : 'open a new page: duplicate filter',
    SIMPLE_NEW_GALLERY_DOWNLOADER_PAGE : 'open a new page: gallery downloader',
    SIMPLE_NEW_PAGE : 'open a new page: choose a page',
    SIMPLE_NEW_PAGE_OF_PAGES : 'open a new page: page of pages',
    SIMPLE_NEW_SIMPLE_DOWNLOADER_PAGE : 'open a new page: simple downloader',
    SIMPLE_NEW_URL_DOWNLOADER_PAGE : 'open a new page: url downloader',
    SIMPLE_NEW_WATCHER_DOWNLOADER_PAGE : 'open a new page: thread watcher',
    SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM : 'open file in external program',
    SIMPLE_OPEN_FILE_IN_FILE_EXPLORER : 'open file in file explorer',
    SIMPLE_OPEN_FILE_IN_WEB_BROWSER : 'open file in web browser',
    SIMPLE_OPEN_KNOWN_URL : 'open known url',
    SIMPLE_OPEN_SELECTION_IN_NEW_PAGE : 'open files in a new page',
    SIMPLE_OPEN_SELECTION_IN_NEW_DUPLICATES_FILTER_PAGE : 'open files in a new duplicates filter page',
    SIMPLE_OPEN_SIMILAR_LOOKING_FILES : 'open similar looking files in a new page',
    SIMPLE_PAN_BOTTOM_EDGE : 'pan file to bottom edge',
    SIMPLE_PAN_DOWN : 'pan file down',
    SIMPLE_PAN_HORIZONTAL_CENTER : 'pan file left/right to center',
    SIMPLE_PAN_LEFT : 'pan file left',
    SIMPLE_PAN_LEFT_EDGE : 'pan file to left edge',
    SIMPLE_PAN_RIGHT : 'pan file right',
    SIMPLE_PAN_RIGHT_EDGE : 'pan file to right edge',
    SIMPLE_PAN_TOP_EDGE : 'pan file to top edge',
    SIMPLE_PAN_UP : 'pan file up',
    SIMPLE_PAN_VERTICAL_CENTER : 'pan file up/down to center',
    SIMPLE_PAUSE_MEDIA : 'pause media',
    SIMPLE_PAUSE_PLAY_MEDIA : 'pause/play media',
    SIMPLE_PAUSE_PLAY_SLIDESHOW : 'pause/play slideshow',
    SIMPLE_REDO : 'redo (limited support)',
    SIMPLE_REFRESH : 'refresh page search/sort',
    SIMPLE_REFRESH_ALL_PAGES : 'refresh all pages',
    SIMPLE_REFRESH_PAGE_OF_PAGES_PAGES : 'refresh all pages on current page of pages',
    SIMPLE_REMOVE_FILE_FROM_VIEW : 'remove file from current view',
    SIMPLE_RESTART_APPLICATION : 'exit program: restart',
    SIMPLE_RUN_ALL_EXPORT_FOLDERS : 'run all export folders now',
    SIMPLE_SET_MEDIA_FOCUS : 'keyboard focus: to the thumbnail grid',
    SIMPLE_SET_SEARCH_FOCUS : 'keyboard focus: to the default text entry of page/dialog',
    SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FAVOURITE_TAGS : 'keyboard focus: to manage tags\' favourite tags',
    SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FILE_LOOKUP_SCRIPT_TAGS : 'keyboard focus: to manage tags\' file lookup scripts',
    SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RECENT_TAGS : 'keyboard focus: to manage tags\' recent tags',
    SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RELATED_TAGS : 'keyboard focus: to manage tags\' related tags',
    SIMPLE_REFRESH_RELATED_TAGS : 'refresh manage tags\' related tags with thorough duration',
    SIMPLE_SHOW_HIDE_SPLITTERS : 'show/hide the left page panel and preview canvas',
    SIMPLE_SHOW_MENU : 'show menu',
    SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM : 'zoom: switch between 100% and canvas fit',
    SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_MAX_ZOOM : 'zoom: switch between 100% and max zoom',
    SIMPLE_SWITCH_BETWEEN_CANVAS_AND_MAX_ZOOM : 'zoom: switch between canvas fit and max zoom',
    SIMPLE_ZOOM_100 : 'zoom: 100%',
    SIMPLE_ZOOM_CANVAS : 'zoom: canvas fit',
    SIMPLE_ZOOM_CANVAS_VIEWER_CENTER : 'zoom to fit canvas with forced media viewer center',
    SIMPLE_ZOOM_DEFAULT : 'zoom: default',
    SIMPLE_ZOOM_DEFAULT_VIEWER_CENTER : 'zoom: default with forced media viewer center',
    SIMPLE_RESET_PAN_TO_CENTER : 'recenter media',
    SIMPLE_RESIZE_WINDOW_TO_MEDIA : 'resize window to fit current media perfectly',
    SIMPLE_RESIZE_WINDOW_TO_MEDIA_VIEWER_CENTER : 'resize window to fit current media perfectly and recenter it in the viewer',
    SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED : 'resize window to fit current media zoomed to a specific percent',
    SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER : 'resize window to fit media at specified zoom and recenter it in the viewer',
    SIMPLE_ZOOM_MAX : 'zoom: max',
    SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW : 'switch between fullscreen borderless and regular framed window',
    SIMPLE_SYNCHRONISED_WAIT_SWITCH : 'switch between searching a page immediately on new tags and waiting',
    SIMPLE_UNCLOSE_PAGE : 'restore the most recently closed page',
    SIMPLE_UNDELETE_FILE : 'undelete file',
    SIMPLE_UNDO : 'undo (limited support)',
    SIMPLE_VIEW_FIRST : 'media navigation: first',
    SIMPLE_VIEW_LAST : 'media navigation: last',
    SIMPLE_VIEW_NEXT : 'media navigation: next',
    SIMPLE_VIEW_PREVIOUS : 'media navigation: previous',
    SIMPLE_VIEW_RANDOM : 'media navigation: random',
    SIMPLE_UNDO_RANDOM : 'media navigation: undo random',
    SIMPLE_ZOOM_IN : 'zoom: in',
    SIMPLE_ZOOM_OUT : 'zoom: out',
    SIMPLE_ZOOM_TO_PERCENTAGE : 'zoom: set to percentage',
    SIMPLE_ZOOM_TO_PERCENTAGE_CENTER : 'zoom: set to percentage with forced media viewer center',
    SIMPLE_ZOOM_100_CENTER : 'zoom to 100% with forced media viewer center',
    SIMPLE_ZOOM_CANVAS_FILL_X : 'fill canvas horizontally',
    SIMPLE_ZOOM_CANVAS_FILL_X_VIEWER_CENTER : 'fill canvas horizontally with forced media viewer center',
    SIMPLE_ZOOM_CANVAS_FILL_Y : 'fill canvas vertically',
    SIMPLE_ZOOM_CANVAS_FILL_Y_VIEWER_CENTER : 'fill canvas vertically with forced media viewer center',
    SIMPLE_ZOOM_CANVAS_FILL_AUTO : 'auto-fill closest dimension',
    SIMPLE_ZOOM_CANVAS_FILL_AUTO_VIEWER_CENTER : 'auto-fill closest dimension with forced media viewer center',
    SIMPLE_EXIT_APPLICATION_FORCE_MAINTENANCE : 'exit program: close and force shutdown maintenance',
    SIMPLE_ZOOM_IN_VIEWER_CENTER : 'zoom: in with forced media viewer center',
    SIMPLE_ZOOM_OUT_VIEWER_CENTER : 'zoom: out with forced media viewer center',
    SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM_VIEWER_CENTER : 'zoom: switch 100% and canvas fit with forced media viewer center',
    SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM : 'zoom: switch 100% and canvas fit/fill',
    SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM_VIEWER_CENTER : 'zoom: switch 100% and canvas fit/fill with forced media viewer center',
    SIMPLE_SHOW_DUPLICATES : 'file relationships: show',
    SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_ALTERNATE_GROUP : 'file relationships: dissolve alternate group (just focused file)',
    SIMPLE_DUPLICATE_MEDIA_DISSOLVE_ALTERNATE_GROUP : 'file relationships: completely dissolve alternate groups',
    SIMPLE_DUPLICATE_MEDIA_DISSOLVE_FOCUSED_DUPLICATE_GROUP : 'file relationships: dissolve duplicate group (just focused file)',
    SIMPLE_DUPLICATE_MEDIA_DISSOLVE_DUPLICATE_GROUP : 'file relationships: completely dissolve duplicate groups',
    SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_ALTERNATE_GROUP : 'file relationships: remove from alternate group (just focused file)',
    SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_FROM_DUPLICATE_GROUP : 'file relationships: remove from duplicate group (just focused file)',
    SIMPLE_DUPLICATE_MEDIA_RESET_FOCUSED_POTENTIAL_SEARCH : 'file relationships: reset potential search (just focused file)',
    SIMPLE_DUPLICATE_MEDIA_RESET_POTENTIAL_SEARCH : 'file relationships: reset potential searches',
    SIMPLE_DUPLICATE_MEDIA_REMOVE_FOCUSED_POTENTIALS : 'file relationships: remove from potential duplicate pairs (just focused file)',
    SIMPLE_DUPLICATE_MEDIA_REMOVE_POTENTIALS : 'file relationships: remove files from potential duplicate pairs',
    SIMPLE_DUPLICATE_MEDIA_SET_POTENTIAL : 'file relationships: set files as potential duplicates',
    SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FALSE_POSITIVES : 'file relationships: delete all false positives',
    SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FOCUSED_FALSE_POSITIVES : 'file relationships: clear all false positives (just focused file)',
    SIMPLE_DUPLICATE_MEDIA_CLEAR_INTERNAL_FALSE_POSITIVES : 'file relationships: delete false positives within selection',
    SIMPLE_AUTOCOMPLETE_FORCE_FETCH : 'force-fetch tag autocomplete results',
    SIMPLE_AUTOCOMPLETE_IME_MODE : 'flip IME-friendly mode on/off (this disables extra shortcut processing so you can do IME popup stuff)',
    SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_LEFT : 'if input is empty, move left one autocomplete dropdown tab',
    SIMPLE_AUTOCOMPLETE_IF_EMPTY_TAB_RIGHT : 'if input is empty, move right one autocomplete dropdown tab',
    SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_LEFT : 'if input & results list are empty, move to left one service page',
    SIMPLE_AUTOCOMPLETE_IF_EMPTY_PAGE_RIGHT : 'if input & results list are empty, move to right one service page',
    SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_PREVIOUS : 'if input & results list are empty and in media viewer manage tags dialog, move to previous media',
    SIMPLE_AUTOCOMPLETE_IF_EMPTY_MEDIA_NEXT : 'if input & results list are empty and in media viewer manage tags dialog, move to previous media',
    SIMPLE_MEDIA_SEEK_DELTA : 'seek media',
    SIMPLE_GLOBAL_PROFILE_MODE_FLIP : 'flip profile mode on/off',
    SIMPLE_GLOBAL_FORCE_ANIMATION_SCANBAR_SHOW : 'force the animation scanbar to show (flip on/off)',
    SIMPLE_OPEN_COMMAND_PALETTE : 'open the command palette',
    SIMPLE_MOVE_THUMBNAIL_FOCUS : 'move the thumbnail focus',
    SIMPLE_SELECT_FILES : 'select files',
    SIMPLE_REARRANGE_THUMBNAILS : 'move thumbnails',
    SIMPLE_MAC_QUICKLOOK : 'open quick look for selected file (macOS only)',
    SIMPLE_COPY_URLS : 'copy file known urls',
    SIMPLE_NATIVE_OPEN_FILE_PROPERTIES : 'open file properties',
    SIMPLE_NATIVE_OPEN_FILE_WITH_DIALOG : 'open in another program',
    SIMPLE_RELOAD_CURRENT_STYLESHEET : 'reload current qss stylesheet',
    SIMPLE_FLIP_ICC_PROFILE_APPLICATION : 'flip apply image ICC Profile colour adjustments',
    SIMPLE_FLIP_TRANSPARENCY_CHECKERBOARD_MEDIA_VIEWER : 'flip drawing transparency as checkerboard in media viewer',
    SIMPLE_FLIP_TRANSPARENCY_CHECKERBOARD_MEDIA_VIEWER_DUPLICATE_FILTER : 'flip drawing transparency as checkerboard in media viewer (duplicate filter)',
    SIMPLE_FLIP_TRANSPARENCY_CHECKERBOARD_GREENSCREEN : 'flip between drawing transparency and checkerboard and greenscreen',
    SIMPLE_OPEN_OPTIONS : 'open the options dialog'
}

legacy_simple_str_to_enum_lookup = {
    'archive_delete_filter_back' : SIMPLE_ARCHIVE_DELETE_FILTER_BACK,
    'archive_delete_filter_delete' : SIMPLE_ARCHIVE_DELETE_FILTER_DELETE,
    'archive_delete_filter_keep' : SIMPLE_ARCHIVE_DELETE_FILTER_KEEP,
    'archive_delete_filter_skip' : SIMPLE_ARCHIVE_DELETE_FILTER_SKIP,
    'archive_file' : SIMPLE_ARCHIVE_FILE,
    'check_all_import_folders' : SIMPLE_CHECK_ALL_IMPORT_FOLDERS,
    'close_media_viewer' : SIMPLE_CLOSE_MEDIA_VIEWER,
    'close_page' : SIMPLE_CLOSE_PAGE,
    'copy_bmp' : LEGACY_SIMPLE_COPY_BMP,
    'copy_bmp_or_file_if_not_bmpable' : LEGACY_SIMPLE_COPY_BMP_OR_FILE_IF_NOT_BMPABLE,
    'copy_file' : SIMPLE_COPY_FILES,
    'copy_md5_hash' : LEGACY_SIMPLE_COPY_MD5_HASH,
    'copy_path' : SIMPLE_COPY_FILE_PATHS,
    'copy_sha1_hash' : LEGACY_SIMPLE_COPY_SHA1_HASH,
    'copy_sha256_hash' : LEGACY_SIMPLE_COPY_SHA256_HASH,
    'copy_sha512_hash' : LEGACY_SIMPLE_COPY_SHA512_HASH,
    'delete_file' : SIMPLE_DELETE_FILE,
    'duplicate_filter_alternates' : SIMPLE_DUPLICATE_FILTER_ALTERNATES,
    'duplicate_filter_back' : SIMPLE_DUPLICATE_FILTER_BACK,
    'duplicate_filter_custom_action' : SIMPLE_DUPLICATE_FILTER_CUSTOM_ACTION,
    'duplicate_filter_exactly_the_same' : SIMPLE_DUPLICATE_FILTER_EXACTLY_THE_SAME,
    'duplicate_filter_false_positive' : SIMPLE_DUPLICATE_FILTER_FALSE_POSITIVE,
    'duplicate_filter_skip' : SIMPLE_DUPLICATE_FILTER_SKIP,
    'duplicate_filter_this_is_better_and_delete_other' : SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER,
    'duplicate_filter_this_is_better_but_keep_both' : SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH,
    'duplicate_media_set_alternate' : SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE,
    'duplicate_media_set_alternate_collections' : SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE_COLLECTIONS,
    'duplicate_media_set_custom' : SIMPLE_DUPLICATE_MEDIA_SET_CUSTOM,
    'duplicate_media_set_focused_better' : SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_BETTER,
    'duplicate_media_set_focused_king' : SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_KING,
    'duplicate_media_set_same_quality' : SIMPLE_DUPLICATE_MEDIA_SET_SAME_QUALITY,
    'exit_application' : SIMPLE_EXIT_APPLICATION,
    'exit_application_force_maintenance' : SIMPLE_EXIT_APPLICATION_FORCE_MAINTENANCE,
    'export_files' : SIMPLE_EXPORT_FILES,
    'export_files_quick_auto_export' : SIMPLE_EXPORT_FILES_QUICK_AUTO_EXPORT,
    'flip_darkmode' : SIMPLE_FLIP_DARKMODE,
    'flip_debug_force_idle_mode_do_not_set_this' : SIMPLE_FLIP_DEBUG_FORCE_IDLE_MODE_DO_NOT_SET_THIS,
    'focus_media_viewer' : SIMPLE_FOCUS_MEDIA_VIEWER,
    'get_similar_to_exact' : LEGACY_SIMPLE_GET_SIMILAR_TO_EXACT,
    'get_similar_to_similar' : LEGACY_SIMPLE_GET_SIMILAR_TO_SIMILAR,
    'get_similar_to_speculative' : LEGACY_SIMPLE_GET_SIMILAR_TO_SPECULATIVE,
    'get_similar_to_very_similar' : LEGACY_SIMPLE_GET_SIMILAR_TO_VERY_SIMILAR,
    'global_audio_mute' : SIMPLE_GLOBAL_AUDIO_MUTE,
    'global_audio_mute_flip' : SIMPLE_GLOBAL_AUDIO_MUTE_FLIP,
    'global_audio_unmute' : SIMPLE_GLOBAL_AUDIO_UNMUTE,
    'hide_to_system_tray' : SIMPLE_HIDE_TO_SYSTEM_TRAY,
    'inbox_file' : SIMPLE_INBOX_FILE,
    'launch_media_viewer' : SIMPLE_LAUNCH_MEDIA_VIEWER,
    'launch_the_archive_delete_filter' : SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER,
    'manage_file_notes' : SIMPLE_MANAGE_FILE_NOTES,
    'manage_file_ratings' : SIMPLE_MANAGE_FILE_RATINGS,
    'manage_file_tags' : SIMPLE_MANAGE_FILE_TAGS,
    'manage_file_urls' : SIMPLE_MANAGE_FILE_URLS,
    'move_animation_to_next_frame' : SIMPLE_MOVE_ANIMATION_TO_NEXT_FRAME,
    'move_animation_to_previous_frame' : SIMPLE_MOVE_ANIMATION_TO_PREVIOUS_FRAME,
    'new_duplicate_filter_page' : SIMPLE_NEW_DUPLICATE_FILTER_PAGE,
    'new_gallery_downloader_page' : SIMPLE_NEW_GALLERY_DOWNLOADER_PAGE,
    'new_page' : SIMPLE_NEW_PAGE,
    'new_page_of_pages' : SIMPLE_NEW_PAGE_OF_PAGES,
    'new_simple_downloader_page' : SIMPLE_NEW_SIMPLE_DOWNLOADER_PAGE,
    'new_url_downloader_page' : SIMPLE_NEW_URL_DOWNLOADER_PAGE,
    'new_watcher_downloader_page' : SIMPLE_NEW_WATCHER_DOWNLOADER_PAGE,
    'open_file_in_external_program' : SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM,
    'open_known_url' : SIMPLE_OPEN_KNOWN_URL,
    'open_selection_in_new_page' : SIMPLE_OPEN_SELECTION_IN_NEW_PAGE,
    'pan_bottom_edge' : SIMPLE_PAN_BOTTOM_EDGE,
    'pan_down' : SIMPLE_PAN_DOWN,
    'pan_horizontal_center' : SIMPLE_PAN_HORIZONTAL_CENTER,
    'pan_left' : SIMPLE_PAN_LEFT,
    'pan_left_edge' : SIMPLE_PAN_LEFT_EDGE,
    'pan_right' : SIMPLE_PAN_RIGHT,
    'pan_right_edge' : SIMPLE_PAN_RIGHT_EDGE,
    'pan_top_edge' : SIMPLE_PAN_TOP_EDGE,
    'pan_up' : SIMPLE_PAN_UP,
    'pan_vertical_center' : SIMPLE_PAN_VERTICAL_CENTER,
    'pause_media' : SIMPLE_PAUSE_MEDIA,
    'pause_play_media' : SIMPLE_PAUSE_PLAY_MEDIA,
    'pause_play_slideshow' : SIMPLE_PAUSE_PLAY_SLIDESHOW,
    'redo' : SIMPLE_REDO,
    'refresh' : SIMPLE_REFRESH,
    'refresh_all_pages' : SIMPLE_REFRESH_ALL_PAGES,
    'refresh_page_of_pages_pages' : SIMPLE_REFRESH_PAGE_OF_PAGES_PAGES,
    'remove_file_from_view' : SIMPLE_REMOVE_FILE_FROM_VIEW,
    'restart_application' : SIMPLE_RESTART_APPLICATION,
    'set_media_focus' : SIMPLE_SET_MEDIA_FOCUS,
    'set_search_focus' : SIMPLE_SET_SEARCH_FOCUS,
    'show_and_focus_manage_tags_favourite_tags' : SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FAVOURITE_TAGS,
    'show_and_focus_manage_tags_file_lookup_script_tags' : SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FILE_LOOKUP_SCRIPT_TAGS,
    'show_and_focus_manage_tags_recent_tags' : SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RECENT_TAGS,
    'show_and_focus_manage_tags_related_tags' : SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RELATED_TAGS,
    'show_hide_splitters' : SIMPLE_SHOW_HIDE_SPLITTERS,
    'show_menu' : SIMPLE_SHOW_MENU,
    'switch_between_100_percent_and_canvas_zoom' : SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM,
    'switch_between_100_percent_and_canvas_fit_and_fill_zoom' : SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM,
    'switch_between_fullscreen_borderless_and_regular_framed_window' : SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW,
    'synchronised_wait_switch' : SIMPLE_SYNCHRONISED_WAIT_SWITCH,
    'unclose_page' : SIMPLE_UNCLOSE_PAGE,
    'undelete_file' : SIMPLE_UNDELETE_FILE,
    'undo' : SIMPLE_UNDO,
    'view_first' : SIMPLE_VIEW_FIRST,
    'view_last' : SIMPLE_VIEW_LAST,
    'view_next' : SIMPLE_VIEW_NEXT,
    'view_previous' : SIMPLE_VIEW_PREVIOUS,
    'view_random' : SIMPLE_VIEW_RANDOM,
    'undo_random' : SIMPLE_UNDO_RANDOM,
    'zoom_in' : SIMPLE_ZOOM_IN,
    'zoom_out' : SIMPLE_ZOOM_OUT,
    'focus_media_thumbnail' : SIMPLE_FOCUS_TAB_AND_MEDIA
}

APPLICATION_COMMAND_TYPE_SIMPLE = 0
APPLICATION_COMMAND_TYPE_CONTENT = 1

class ApplicationCommand( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_APPLICATION_COMMAND
    SERIALISABLE_NAME = 'Application Command'
    SERIALISABLE_VERSION = 7
    
    def __init__( self, command_type = None, data = None ):
        
        if command_type is None:
            
            command_type = APPLICATION_COMMAND_TYPE_SIMPLE
            
            data = ( SIMPLE_ARCHIVE_FILE, None )
            
        
        super().__init__()
        
        self._command_type = command_type
        self._data: typing.Any = data
        
    
    def __eq__( self, other ):
        
        if isinstance( other, ApplicationCommand ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        if self._command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
            
            ( simple_action, simple_data ) = self._data
            
            # we are out here
            if simple_action == SIMPLE_COPY_FILE_SERVICE_FILENAMES:
                
                comparison_simple_data = tuple( sorted( simple_data.items() ) )
                
                return ( self._command_type, ( simple_action, comparison_simple_data ) ).__hash__()
                
            
        
        return ( self._command_type, self._data ).__hash__()
        
    
    def __repr__( self ):
        
        return self.ToString()
        
    
    def _GetSerialisableInfo( self ):
        
        # TODO: I recently moved to the data_dict here so the simple type could have serialisables in its 'simple_data', let's move the content command type to this too
        # I don't _think_ this was an overcomplicated mistake, but it is a little ugly atm
        # it'll be better when all working on the same system. perhaps command_type too
        # and maybe ditch the object's self._data variable too, which is crushed as anything. maybe just have a serialisable dict mate
        #
        # 2024-04 update: I'd also like a way to store arbitrary numbers of bytes objects! if we can store service_key(s!) or whatever without extra effort, in a SerialisableBytesDict,
        # we can have all sorts of service or 'load favourite search' stuff without the headache
        # So yeah I think ditch the _data thing, move more towards a SerialisableDict as our normal data-holding guy, and then we refer to that as we do jobs
        # yeah if I instead move to a kwargs init for this whole object, then I can store whatever as long as it is serialisable. ditch the tuples, move to words
        #
        # also update __hash__ to be non-borked in this situation
        
        if self._command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
            
            ( simple_action, simple_data ) = self._data
            
            data_dict = HydrusSerialisable.SerialisableDictionary()
            
            data_dict[ 'simple_action' ] = simple_action
            data_dict[ 'simple_data' ] = simple_data
            
            serialisable_data = data_dict.GetSerialisableTuple()
            
        elif self._command_type == APPLICATION_COMMAND_TYPE_CONTENT:
            
            ( service_key, content_type, action, value ) = self._data
            
            if content_type == HC.CONTENT_TYPE_FILES and value is not None and isinstance( value, bytes ):
                
                value = value.hex()
                
            
            serialisable_data = ( service_key.hex(), content_type, action, value )
            
        else:
            
            raise NotImplementedError( 'Unknown command type!' )
            
        
        return ( self._command_type, serialisable_data )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._command_type, serialisable_data ) = serialisable_info
        
        if self._command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
            
            data_dict = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_data )
            
            simple_action = data_dict[ 'simple_action' ]
            simple_data = data_dict[ 'simple_data' ]
            
            if isinstance( simple_data, list ):
                
                simple_data = tuple( simple_data )
                
            
            self._data = ( simple_action, simple_data )
            
        elif self._command_type == APPLICATION_COMMAND_TYPE_CONTENT:
            
            ( serialisable_service_key, content_type, action, value ) = serialisable_data
            
            if content_type == HC.CONTENT_TYPE_FILES and value is not None and isinstance( value, str ):
                
                try:
                    
                    value = bytes.fromhex( value )
                    
                except Exception as e:
                    
                    value = None
                    
                
            
            self._data = ( bytes.fromhex( serialisable_service_key ), content_type, action, value )
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( command_type, serialisable_data ) = old_serialisable_info
            
            if command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
                
                if serialisable_data == 'duplicate_filter_this_is_better':
                    
                    serialisable_data = 'duplicate_filter_this_is_better_and_delete_other'
                    
                elif serialisable_data == 'duplicate_filter_not_dupes':
                    
                    serialisable_data = 'duplicate_filter_false_positive'
                    
                
            
            new_serialisable_info = ( command_type, serialisable_data )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( command_type, serialisable_data ) = old_serialisable_info
            
            if command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
                
                if serialisable_data in legacy_simple_str_to_enum_lookup:
                    
                    serialisable_data = legacy_simple_str_to_enum_lookup[ serialisable_data ]
                    
                else:
                    
                    serialisable_data = SIMPLE_ARCHIVE_FILE
                    
                
            
            new_serialisable_info = ( command_type, serialisable_data )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( command_type, serialisable_data ) = old_serialisable_info
            
            if command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
                
                serialisable_data = ( serialisable_data, None )
                
            
            new_serialisable_info = ( command_type, serialisable_data )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( command_type, serialisable_data ) = old_serialisable_info
            
            if command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
                
                ( simple_action, simple_data ) = serialisable_data
                
                data_dict = HydrusSerialisable.SerialisableDictionary()
                
                data_dict[ 'simple_action' ] = simple_action
                data_dict[ 'simple_data' ] = simple_data
                
                serialisable_data = data_dict.GetSerialisableTuple()
                
            
            new_serialisable_info = ( command_type, serialisable_data )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( command_type, serialisable_data ) = old_serialisable_info
            
            if command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
                
                data_dict = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_data )
                
                simple_action = data_dict[ 'simple_action' ]
                
                if simple_action in ( LEGACY_SIMPLE_GET_SIMILAR_TO_EXACT, LEGACY_SIMPLE_GET_SIMILAR_TO_VERY_SIMILAR, LEGACY_SIMPLE_GET_SIMILAR_TO_SIMILAR, LEGACY_SIMPLE_GET_SIMILAR_TO_SPECULATIVE ):
                    
                    hamming_distance = 0
                    
                    if simple_action == LEGACY_SIMPLE_GET_SIMILAR_TO_EXACT:
                        
                        hamming_distance = 0
                        
                    elif simple_action == LEGACY_SIMPLE_GET_SIMILAR_TO_VERY_SIMILAR:
                        
                        hamming_distance = 2
                        
                    elif simple_action == LEGACY_SIMPLE_GET_SIMILAR_TO_SIMILAR:
                        
                        hamming_distance = 4
                        
                    elif simple_action == LEGACY_SIMPLE_GET_SIMILAR_TO_SPECULATIVE:
                        
                        hamming_distance = 8
                        
                    
                    data_dict[ 'simple_action' ] = SIMPLE_OPEN_SIMILAR_LOOKING_FILES
                    data_dict[ 'simple_data' ] = hamming_distance
                    
                
                serialisable_data = data_dict.GetSerialisableTuple()
                
            
            new_serialisable_info = ( command_type, serialisable_data )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( command_type, serialisable_data ) = old_serialisable_info
            
            if command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
                
                data_dict = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_data )
                
                simple_action = data_dict[ 'simple_action' ]
                
                if simple_action in ( LEGACY_SIMPLE_COPY_SHA256_HASH, LEGACY_SIMPLE_COPY_MD5_HASH, LEGACY_SIMPLE_COPY_SHA1_HASH, LEGACY_SIMPLE_COPY_SHA512_HASH ):
                    
                    file_command_target = FILE_COMMAND_TARGET_SELECTED_FILES
                    
                    hash_type = 'sha256'
                    
                    if simple_action == LEGACY_SIMPLE_COPY_SHA256_HASH:
                        
                        hash_type = 'sha256'
                        
                    elif simple_action == LEGACY_SIMPLE_COPY_MD5_HASH:
                        
                        hash_type = 'md5'
                        
                    elif simple_action == LEGACY_SIMPLE_COPY_SHA1_HASH:
                        
                        hash_type = 'sha1'
                        
                    elif simple_action == LEGACY_SIMPLE_COPY_SHA512_HASH:
                        
                        hash_type = 'sha512'
                        
                    
                    data_dict[ 'simple_action' ] = SIMPLE_COPY_FILE_HASHES
                    data_dict[ 'simple_data' ] = ( file_command_target, hash_type )
                    
                elif simple_action in ( LEGACY_SIMPLE_COPY_BMP, LEGACY_SIMPLE_COPY_LITTLE_BMP, LEGACY_SIMPLE_COPY_BMP_OR_FILE_IF_NOT_BMPABLE ):
                    
                    bitmap_type = BITMAP_TYPE_FULL
                    
                    if simple_action == LEGACY_SIMPLE_COPY_BMP:
                        
                        bitmap_type = BITMAP_TYPE_FULL
                        
                    elif simple_action == LEGACY_SIMPLE_COPY_LITTLE_BMP:
                        
                        bitmap_type = BITMAP_TYPE_SOURCE_LOOKUPS
                        
                    elif simple_action == LEGACY_SIMPLE_COPY_BMP_OR_FILE_IF_NOT_BMPABLE:
                        
                        bitmap_type = BITMAP_TYPE_FULL_OR_FILE
                        
                    
                    data_dict[ 'simple_action' ] = SIMPLE_COPY_FILE_BITMAP
                    data_dict[ 'simple_data' ] = bitmap_type
                    
                elif simple_action in ( SIMPLE_COPY_FILES, SIMPLE_COPY_FILE_PATHS ):
                    
                    data_dict[ 'simple_data' ] = FILE_COMMAND_TARGET_SELECTED_FILES
                    
                
                serialisable_data = data_dict.GetSerialisableTuple()
                
            
            new_serialisable_info = ( command_type, serialisable_data )
            
            return ( 7, new_serialisable_info )
            
        
    
    def GetCommandType( self ):
        
        return self._command_type
        
    
    def GetSimpleAction( self ) -> int:
        
        if self._command_type != APPLICATION_COMMAND_TYPE_SIMPLE:
            
            raise Exception( 'Not a simple command!' )
            
        
        ( simple_action, simple_data ) = self._data
        
        return simple_action
        
    
    def GetSimpleData( self ) -> typing.Any:
        
        if self._command_type != APPLICATION_COMMAND_TYPE_SIMPLE:
            
            raise Exception( 'Not a simple command!' )
            
        
        ( simple_action, simple_data ) = self._data
        
        return simple_data
        
    
    def GetContentAction( self ):
        
        if self._command_type != APPLICATION_COMMAND_TYPE_CONTENT:
            
            raise Exception( 'Not a content command!' )
            
        
        ( service_key, content_type, action, value ) = self._data
        
        return action
        
    
    def GetContentServiceKey( self ):
        
        if self._command_type != APPLICATION_COMMAND_TYPE_CONTENT:
            
            raise Exception( 'Not a content command!' )
            
        
        ( service_key, content_type, action, value ) = self._data
        
        return service_key
        
    
    def GetContentValue( self ):
        
        if self._command_type != APPLICATION_COMMAND_TYPE_CONTENT:
            
            raise Exception( 'Not a content command!' )
            
        
        ( service_key, content_type, action, value ) = self._data
        
        return value
        
    
    def IsSimpleCommand( self ):
        
        return self._command_type == APPLICATION_COMMAND_TYPE_SIMPLE
        
    
    def IsContentCommand( self ):
        
        return self._command_type == APPLICATION_COMMAND_TYPE_CONTENT
        
    
    def ToString( self ):
        
        try:
            
            if self._command_type == APPLICATION_COMMAND_TYPE_SIMPLE:
                
                action = self.GetSimpleAction()
                
                s = simple_enum_to_str_lookup[ action ]
                
                if action == SIMPLE_SHOW_DUPLICATES:
                    
                    duplicate_type = self.GetSimpleData()
                    
                    s = f'{s} {HC.duplicate_type_string_lookup[ duplicate_type ]}'
                    
                elif action == SIMPLE_MEDIA_SEEK_DELTA:
                    
                    ( direction, ms ) = self.GetSimpleData()
                    
                    direction_s = 'back' if direction == -1 else 'forwards'
                    
                    ms_s = HydrusTime.TimeDeltaToPrettyTimeDelta( HydrusTime.SecondiseMSFloat( ms ) )
                    
                    s = f'{s} ({direction_s} {ms_s})'
                    
                elif action == SIMPLE_OPEN_SIMILAR_LOOKING_FILES:
                    
                    hamming_distance = self.GetSimpleData()
                    
                    if hamming_distance is None:
                        
                        pass
                        
                    elif hamming_distance in CC.hamming_string_lookup:
                        
                        s = f'{s} ({hamming_distance} - {CC.hamming_string_lookup[ hamming_distance ]})'
                        
                    else:
                        
                        s = f'{s} ({hamming_distance})'
                        
                    
                elif action == SIMPLE_COPY_FILE_HASHES:
                    
                    ( file_command_target, hash_type ) = self.GetSimpleData()
                    
                    s = f'{s} ({hash_type}, {file_command_target_enum_to_str_lookup[ file_command_target ]})'
                    
                elif action == SIMPLE_COPY_FILE_BITMAP:
                    
                    bitmap_type = self.GetSimpleData()
                    
                    s = f'{s} ({bitmap_type_enum_to_str_lookup[ bitmap_type ]})'
                    
                elif action in ( SIMPLE_COPY_FILES, SIMPLE_COPY_FILE_PATHS, SIMPLE_COPY_FILE_ID ):
                    
                    file_command_target = self.GetSimpleData()
                    
                    s = f'{s} ({file_command_target_enum_to_str_lookup[ file_command_target ]})'
                    
                elif action == SIMPLE_COPY_FILE_SERVICE_FILENAMES:
                    
                    hacky_ipfs_dict = self.GetSimpleData()
                    
                    try:
                        
                        file_command_target_string = file_command_target_enum_to_str_lookup[ hacky_ipfs_dict[ 'file_command_target' ] ]
                        
                    except Exception as e:
                        
                        file_command_target_string = 'unknown'
                        
                    
                    try:
                        
                        ipfs_service_key = hacky_ipfs_dict[ 'ipfs_service_key' ]
                        
                        name = CG.client_controller.services_manager.GetName( ipfs_service_key )
                        
                    except Exception as e:
                        
                        name = 'unknown service'
                        
                    
                    s = f'{s} ({name}, {file_command_target_string})'
                    
                elif action == SIMPLE_MOVE_THUMBNAIL_FOCUS:
                    
                    ( move_direction, selection_status ) = self.GetSimpleData()
                    
                    s = f'{s} ({selection_status_enum_to_str_lookup[selection_status]} {move_enum_to_str_lookup[move_direction]})'
                    
                elif action == SIMPLE_SELECT_FILES:
                    
                    file_filter = self.GetSimpleData()
                    
                    s = f'{s} ({file_filter.ToString()})'
                    
                elif action == SIMPLE_REARRANGE_THUMBNAILS:
                    
                    ( rearrange_type, rearrange_data ) = self.GetSimpleData()
                    
                    if rearrange_type == REARRANGE_THUMBNAILS_TYPE_COMMAND:
                        
                        s = f'{s} ({move_enum_to_str_lookup[ rearrange_data ]})'
                        
                    elif rearrange_type == REARRANGE_THUMBNAILS_TYPE_FIXED:
                        
                        s = f'{s} (to index {HydrusNumbers.ToHumanInt(rearrange_data)})'
                        
                    
                
                return s
                
            elif self._command_type == APPLICATION_COMMAND_TYPE_CONTENT:
                
                ( service_key, content_type, action, value ) = self._data
                
                components = []
                
                components.append( HC.content_update_string_lookup[ action ] )
                components.append( HC.content_type_string_lookup[ content_type ] )
                
                value_string = ''
                
                if content_type == HC.CONTENT_TYPE_RATINGS:
                    
                    if action in ( HC.CONTENT_UPDATE_SET, HC.CONTENT_UPDATE_FLIP ):
                        
                        value_string = 'uncertain rating, "{}"'.format( value )
                        
                        if CG.client_controller is not None and CG.client_controller.IsBooted():
                            
                            try:
                                
                                service = CG.client_controller.services_manager.GetService( service_key )
                                
                                value_string = service.ConvertNoneableRatingToString( value )
                                
                            except HydrusExceptions.DataMissing:
                                
                                pass
                                
                            
                        
                    else:
                        
                        value_string = '' # only 1 up/down allowed atm
                        
                    
                elif content_type == HC.CONTENT_TYPE_FILES and value is not None:
                    
                    try:
                        
                        from_name = CG.client_controller.services_manager.GetName( value )
                        
                        value_string = '(from {})'.format( from_name )
                        
                    except Exception as e:
                        
                        value_string = ''
                        
                    
                elif value is not None:
                    
                    value_string = '"{}"'.format( value )
                    
                
                if len( value_string ) > 0:
                    
                    components.append( value_string )
                    
                
                if content_type == HC.CONTENT_TYPE_FILES:
                    
                    components.append( 'to' )
                    
                else:
                    
                    components.append( 'for' )
                    
                
                services_manager = CG.client_controller.services_manager
                
                if services_manager.ServiceExists( service_key ):
                    
                    service = services_manager.GetService( service_key )
                    
                    components.append( service.GetName() )
                    
                else:
                    
                    components.append( 'unknown service!' )
                    
                
                return ' '.join( components )
                
            
        except Exception as e:
            
            return 'Unknown Application Command: ' + repr( ( self._command_type, self._data ) )
            
        
    
    @staticmethod
    def STATICCreateSimpleCommand( simple_action, simple_data = None ) -> "ApplicationCommand":
        
        return ApplicationCommand( APPLICATION_COMMAND_TYPE_SIMPLE, ( simple_action, simple_data ) )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_APPLICATION_COMMAND ] = ApplicationCommand

class ApplicationCommandProcessorMixin( object ):
    
    def ProcessApplicationCommand( self, command: ApplicationCommand ):
        
        # TODO: eventually expand this guy to do the main if and have separate methods for 'do simple command( action )' and 'do complex command( command )', then objects just implement that
        # only thing they need to do is return False if they don't eat the command, or we move to Qt style event processing and set command.ignore() or similar
        # then we can hang debug stuff off this shared code and so on
        
        raise NotImplementedError()
        
    
