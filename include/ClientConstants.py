from . import HydrusConstants as HC
import os
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

#

APPLICATION_COMMAND_TYPE_SIMPLE = 0
APPLICATION_COMMAND_TYPE_CONTENT = 1

BLANK_PHASH = b'\x80\x00\x00\x00\x00\x00\x00\x00' # first bit 1 but everything else 0 means only significant part of dct was [0,0], which represents flat colour

CAN_HIDE_MOUSE = True

FILTER_WHITELIST = 0
FILTER_BLACKLIST = 1

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

FILE_VIEWING_STATS_MENU_DISPLAY_NONE = 0
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_ONLY = 1
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_IN_SUBMENU = 2
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_STACKED = 3
FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_SUMMED = 4

FLAGS_NONE = 0

FLAGS_SMALL_INDENT = 1
FLAGS_BIG_INDENT = 2

FLAGS_CENTER = 3

FLAGS_EXPAND_PERPENDICULAR = 4
FLAGS_EXPAND_BOTH_WAYS = 5
FLAGS_EXPAND_DEPTH_ONLY = 6

FLAGS_EXPAND_BOTH_WAYS_POLITE = 7
FLAGS_EXPAND_BOTH_WAYS_SHY = 8

FLAGS_SIZER_CENTER = 9

FLAGS_EXPAND_SIZER_PERPENDICULAR = 10
FLAGS_EXPAND_SIZER_BOTH_WAYS = 11
FLAGS_EXPAND_SIZER_DEPTH_ONLY = 12

FLAGS_BUTTON_SIZER = 13

FLAGS_LONE_BUTTON = 14

FLAGS_VCENTER = 15
FLAGS_SIZER_VCENTER = 16
FLAGS_VCENTER_EXPAND_DEPTH_ONLY = 17

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

SHORTCUT_TYPE_KEYBOARD_CHARACTER = 0
SHORTCUT_TYPE_MOUSE = 1
SHORTCUT_TYPE_KEYBOARD_SPECIAL = 2
SHORTCUT_TYPE_NOT_ALLOWED = 3

SHORTCUT_PRESS_TYPE_PRESS = 0
SHORTCUT_PRESS_TYPE_RELEASE = 1
SHORTCUT_PRESS_TYPE_DOUBLE_CLICK = 2
SHORTCUT_PRESS_TYPE_DRAG = 3

shortcut_press_type_str_lookup = {}

shortcut_press_type_str_lookup[ SHORTCUT_PRESS_TYPE_PRESS ] = 'press'
shortcut_press_type_str_lookup[ SHORTCUT_PRESS_TYPE_RELEASE ] = 'release'
shortcut_press_type_str_lookup[ SHORTCUT_PRESS_TYPE_DOUBLE_CLICK ] = 'double'
shortcut_press_type_str_lookup[ SHORTCUT_PRESS_TYPE_DRAG ] = 'drag'

SHORTCUT_MODIFIER_CTRL = 0
SHORTCUT_MODIFIER_ALT = 1
SHORTCUT_MODIFIER_SHIFT = 2
SHORTCUT_MODIFIER_KEYPAD = 3
SHORTCUT_MODIFIER_GROUP_SWITCH = 4

SHORTCUT_KEY_SPECIAL_SPACE = 0
SHORTCUT_KEY_SPECIAL_BACKSPACE = 1
SHORTCUT_KEY_SPECIAL_TAB = 2
SHORTCUT_KEY_SPECIAL_RETURN = 3
SHORTCUT_KEY_SPECIAL_ENTER = 4
SHORTCUT_KEY_SPECIAL_PAUSE = 5
SHORTCUT_KEY_SPECIAL_ESCAPE = 6
SHORTCUT_KEY_SPECIAL_INSERT = 7
SHORTCUT_KEY_SPECIAL_DELETE = 8
SHORTCUT_KEY_SPECIAL_UP = 9
SHORTCUT_KEY_SPECIAL_DOWN = 10
SHORTCUT_KEY_SPECIAL_LEFT = 11
SHORTCUT_KEY_SPECIAL_RIGHT = 12
SHORTCUT_KEY_SPECIAL_HOME = 13
SHORTCUT_KEY_SPECIAL_END = 14
SHORTCUT_KEY_SPECIAL_PAGE_UP = 15
SHORTCUT_KEY_SPECIAL_PAGE_DOWN = 16
SHORTCUT_KEY_SPECIAL_F1 = 17
SHORTCUT_KEY_SPECIAL_F2 = 18
SHORTCUT_KEY_SPECIAL_F3 = 19
SHORTCUT_KEY_SPECIAL_F4 = 20
SHORTCUT_KEY_SPECIAL_F5 = 21
SHORTCUT_KEY_SPECIAL_F6 = 22
SHORTCUT_KEY_SPECIAL_F7 = 23
SHORTCUT_KEY_SPECIAL_F8 = 24
SHORTCUT_KEY_SPECIAL_F9 = 25
SHORTCUT_KEY_SPECIAL_F10 = 26
SHORTCUT_KEY_SPECIAL_F11 = 27
SHORTCUT_KEY_SPECIAL_F12 = 28

if HC.PLATFORM_MACOS:
    
    DELETE_KEYS = ( QC.Qt.Key_Backspace, QC.Qt.Key_Delete )
    
else:
    
    DELETE_KEYS = ( QC.Qt.Key_Delete, )
    

special_key_shortcut_enum_lookup = {}

special_key_shortcut_enum_lookup[ QC.Qt.Key_Space ] = SHORTCUT_KEY_SPECIAL_SPACE
special_key_shortcut_enum_lookup[ QC.Qt.Key_Backspace ] = SHORTCUT_KEY_SPECIAL_BACKSPACE
special_key_shortcut_enum_lookup[ QC.Qt.Key_Tab ] = SHORTCUT_KEY_SPECIAL_TAB
special_key_shortcut_enum_lookup[ QC.Qt.Key_Return ] = SHORTCUT_KEY_SPECIAL_RETURN
special_key_shortcut_enum_lookup[ QC.Qt.Key_Enter ] = SHORTCUT_KEY_SPECIAL_ENTER
special_key_shortcut_enum_lookup[ QC.Qt.Key_Pause ] = SHORTCUT_KEY_SPECIAL_PAUSE
special_key_shortcut_enum_lookup[ QC.Qt.Key_Escape ] = SHORTCUT_KEY_SPECIAL_ESCAPE
special_key_shortcut_enum_lookup[ QC.Qt.Key_Insert ] = SHORTCUT_KEY_SPECIAL_INSERT
special_key_shortcut_enum_lookup[ QC.Qt.Key_Delete ] = SHORTCUT_KEY_SPECIAL_DELETE
special_key_shortcut_enum_lookup[ QC.Qt.Key_Up ] = SHORTCUT_KEY_SPECIAL_UP
special_key_shortcut_enum_lookup[ QC.Qt.Key_Down ] = SHORTCUT_KEY_SPECIAL_DOWN
special_key_shortcut_enum_lookup[ QC.Qt.Key_Left ] = SHORTCUT_KEY_SPECIAL_LEFT
special_key_shortcut_enum_lookup[ QC.Qt.Key_Right ] = SHORTCUT_KEY_SPECIAL_RIGHT
special_key_shortcut_enum_lookup[ QC.Qt.Key_Home ] = SHORTCUT_KEY_SPECIAL_HOME
special_key_shortcut_enum_lookup[ QC.Qt.Key_End ] = SHORTCUT_KEY_SPECIAL_END
special_key_shortcut_enum_lookup[ QC.Qt.Key_PageUp ] = SHORTCUT_KEY_SPECIAL_PAGE_UP
special_key_shortcut_enum_lookup[ QC.Qt.Key_PageDown ] = SHORTCUT_KEY_SPECIAL_PAGE_DOWN
special_key_shortcut_enum_lookup[ QC.Qt.Key_F1 ] = SHORTCUT_KEY_SPECIAL_F1
special_key_shortcut_enum_lookup[ QC.Qt.Key_F2 ] = SHORTCUT_KEY_SPECIAL_F2
special_key_shortcut_enum_lookup[ QC.Qt.Key_F3 ] = SHORTCUT_KEY_SPECIAL_F3
special_key_shortcut_enum_lookup[ QC.Qt.Key_F4 ] = SHORTCUT_KEY_SPECIAL_F4
special_key_shortcut_enum_lookup[ QC.Qt.Key_F5 ] = SHORTCUT_KEY_SPECIAL_F5
special_key_shortcut_enum_lookup[ QC.Qt.Key_F6 ] = SHORTCUT_KEY_SPECIAL_F6
special_key_shortcut_enum_lookup[ QC.Qt.Key_F7 ] = SHORTCUT_KEY_SPECIAL_F7
special_key_shortcut_enum_lookup[ QC.Qt.Key_F8 ] = SHORTCUT_KEY_SPECIAL_F8
special_key_shortcut_enum_lookup[ QC.Qt.Key_F9 ] = SHORTCUT_KEY_SPECIAL_F9
special_key_shortcut_enum_lookup[ QC.Qt.Key_F10 ] = SHORTCUT_KEY_SPECIAL_F10
special_key_shortcut_enum_lookup[ QC.Qt.Key_F11 ] = SHORTCUT_KEY_SPECIAL_F11
special_key_shortcut_enum_lookup[ QC.Qt.Key_F12 ] = SHORTCUT_KEY_SPECIAL_F12

special_key_shortcut_str_lookup = {}

special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_SPACE ] = 'space'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_BACKSPACE ] = 'backspace'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_TAB ] = 'tab'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_RETURN ] = 'return'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_ENTER ] = 'enter'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_PAUSE ] = 'pause'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_ESCAPE ] = 'escape'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_INSERT ] = 'insert'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_DELETE ] = 'delete'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_UP ] = 'up'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_DOWN ] = 'down'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_LEFT ] = 'left'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_RIGHT ] = 'right'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_HOME ] = 'home'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_END ] = 'end'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_PAGE_DOWN ] = 'page down'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_PAGE_UP ] = 'page up'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F1 ] = 'f1'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F2 ] = 'f2'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F3 ] = 'f3'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F4 ] = 'f4'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F5 ] = 'f5'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F6 ] = 'f6'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F7 ] = 'f7'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F8 ] = 'f8'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F9 ] = 'f9'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F10 ] = 'f10'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F11 ] = 'f11'
special_key_shortcut_str_lookup[ SHORTCUT_KEY_SPECIAL_F12 ] = 'f12'

SHORTCUT_MOUSE_LEFT = 0
SHORTCUT_MOUSE_RIGHT = 1
SHORTCUT_MOUSE_MIDDLE = 2
SHORTCUT_MOUSE_SCROLL_UP = 3
SHORTCUT_MOUSE_SCROLL_DOWN = 4
SHORTCUT_MOUSE_SCROLL_LEFT = 5
SHORTCUT_MOUSE_SCROLL_RIGHT = 6

shortcut_mouse_string_lookup = {}

shortcut_mouse_string_lookup[ SHORTCUT_MOUSE_LEFT ] = 'left-click'
shortcut_mouse_string_lookup[ SHORTCUT_MOUSE_RIGHT ] = 'right-click'
shortcut_mouse_string_lookup[ SHORTCUT_MOUSE_MIDDLE ] = 'middle-click'
shortcut_mouse_string_lookup[ SHORTCUT_MOUSE_SCROLL_UP ] = 'scroll up'
shortcut_mouse_string_lookup[ SHORTCUT_MOUSE_SCROLL_DOWN ] = 'scroll down'
shortcut_mouse_string_lookup[ SHORTCUT_MOUSE_SCROLL_LEFT ] = 'scroll left'
shortcut_mouse_string_lookup[ SHORTCUT_MOUSE_SCROLL_RIGHT ] = 'scroll right'

SHORTCUTS_RESERVED_NAMES = [ 'global', 'archive_delete_filter', 'duplicate_filter', 'media', 'main_gui', 'media_viewer_browser', 'media_viewer', 'media_viewer_media_window', 'preview_media_window' ]

shortcut_names_to_descriptions = {}

shortcut_names_to_descriptions[ 'global' ] = 'Actions for the whole program. Should work in the main gui or a media viewer.'
shortcut_names_to_descriptions[ 'archive_delete_filter' ] = 'Navigation actions for the media viewer during an archive/delete filter. Mouse shortcuts should work.'
shortcut_names_to_descriptions[ 'duplicate_filter' ] = 'Navigation actions for the media viewer during a duplicate filter. Mouse shortcuts should work.'
shortcut_names_to_descriptions[ 'media' ] = 'Actions to alter metadata for media in the media viewer or the thumbnail grid.'
shortcut_names_to_descriptions[ 'main_gui' ] = 'Actions to control pages in the main window of the program.'
shortcut_names_to_descriptions[ 'media_viewer_browser' ] = 'Navigation actions for the regular browsable media viewer.'
shortcut_names_to_descriptions[ 'media_viewer' ] = 'Zoom and pan and player actions for any media viewer.'
shortcut_names_to_descriptions[ 'media_viewer_media_window' ] = 'Actions for any video or audio player in a media viewer window.'
shortcut_names_to_descriptions[ 'preview_media_window' ] = 'Actions for any video or audio player in a preview window.'

# shortcut commands

SHORTCUTS_GLOBAL_ACTIONS = [ 'global_audio_mute', 'global_audio_unmute', 'global_audio_mute_flip', 'exit_application', 'exit_application_force_maintenance', 'restart_application' ]
SHORTCUTS_MEDIA_ACTIONS = [ 'manage_file_tags', 'manage_file_ratings', 'manage_file_urls', 'manage_file_notes', 'archive_file', 'inbox_file', 'delete_file', 'export_files', 'export_files_quick_auto_export', 'remove_file_from_view', 'open_file_in_external_program', 'open_selection_in_new_page', 'launch_the_archive_delete_filter', 'copy_bmp', 'copy_file', 'copy_path', 'copy_sha256_hash', 'get_similar_to_exact', 'get_similar_to_very_similar', 'get_similar_to_similar', 'get_similar_to_speculative', 'duplicate_media_set_alternate', 'duplicate_media_set_alternate_collections', 'duplicate_media_set_custom', 'duplicate_media_set_focused_better', 'duplicate_media_set_focused_king', 'duplicate_media_set_same_quality', 'open_known_url' ]
SHORTCUTS_MEDIA_VIEWER_ACTIONS = [ 'pause_media', 'pause_play_media', 'move_animation_to_previous_frame', 'move_animation_to_next_frame', 'switch_between_fullscreen_borderless_and_regular_framed_window', 'pan_up', 'pan_down', 'pan_left', 'pan_right', 'pan_top_edge', 'pan_bottom_edge', 'pan_left_edge', 'pan_right_edge', 'pan_vertical_center', 'pan_horizontal_center', 'zoom_in', 'zoom_out', 'switch_between_100_percent_and_canvas_zoom', 'flip_darkmode' ]
SHORTCUTS_MEDIA_VIEWER_BROWSER_ACTIONS = [ 'view_next', 'view_first', 'view_last', 'view_previous', 'pause_play_slideshow', 'show_menu' ]
SHORTCUTS_MAIN_GUI_ACTIONS = [ 'refresh', 'refresh_all_pages', 'refresh_page_of_pages_pages', 'new_page', 'new_page_of_pages', 'new_duplicate_filter_page', 'new_gallery_downloader_page', 'new_url_downloader_page', 'new_simple_downloader_page', 'new_watcher_downloader_page', 'synchronised_wait_switch', 'set_media_focus', 'show_hide_splitters', 'set_search_focus', 'unclose_page', 'close_page', 'redo', 'undo', 'flip_darkmode', 'check_all_import_folders', 'flip_debug_force_idle_mode_do_not_set_this', 'show_and_focus_manage_tags_favourite_tags', 'show_and_focus_manage_tags_related_tags', 'show_and_focus_manage_tags_file_lookup_script_tags', 'show_and_focus_manage_tags_recent_tags', 'focus_media_viewer' ]
SHORTCUTS_DUPLICATE_FILTER_ACTIONS = [ 'duplicate_filter_this_is_better_and_delete_other', 'duplicate_filter_this_is_better_but_keep_both', 'duplicate_filter_exactly_the_same', 'duplicate_filter_alternates', 'duplicate_filter_false_positive', 'duplicate_filter_custom_action', 'duplicate_filter_skip', 'duplicate_filter_back' ]
SHORTCUTS_ARCHIVE_DELETE_FILTER_ACTIONS = [ 'archive_delete_filter_keep', 'archive_delete_filter_delete', 'archive_delete_filter_skip', 'archive_delete_filter_back' ]
SHORTCUTS_MEDIA_VIEWER_VIDEO_AUDIO_PLAYER_ACTIONS = [ 'pause_media', 'pause_play_media', 'open_file_in_external_program', 'close_media_viewer' ]
SHORTCUTS_PREVIEW_VIDEO_AUDIO_PLAYER_ACTIONS = [ 'pause_media', 'pause_play_media', 'open_file_in_external_program', 'launch_media_viewer' ]

simple_shortcut_name_to_action_lookup = {}

simple_shortcut_name_to_action_lookup[ 'global' ] = SHORTCUTS_GLOBAL_ACTIONS
simple_shortcut_name_to_action_lookup[ 'media' ] = SHORTCUTS_MEDIA_ACTIONS
simple_shortcut_name_to_action_lookup[ 'media_viewer' ] = SHORTCUTS_MEDIA_VIEWER_ACTIONS
simple_shortcut_name_to_action_lookup[ 'media_viewer_browser' ] = SHORTCUTS_MEDIA_VIEWER_BROWSER_ACTIONS
simple_shortcut_name_to_action_lookup[ 'main_gui' ] = SHORTCUTS_MAIN_GUI_ACTIONS
simple_shortcut_name_to_action_lookup[ 'duplicate_filter' ] = SHORTCUTS_DUPLICATE_FILTER_ACTIONS + SHORTCUTS_MEDIA_ACTIONS + SHORTCUTS_MEDIA_VIEWER_ACTIONS
simple_shortcut_name_to_action_lookup[ 'archive_delete_filter' ] = SHORTCUTS_ARCHIVE_DELETE_FILTER_ACTIONS
simple_shortcut_name_to_action_lookup[ 'media_viewer_media_window' ] = SHORTCUTS_MEDIA_VIEWER_VIDEO_AUDIO_PLAYER_ACTIONS
simple_shortcut_name_to_action_lookup[ 'preview_media_window' ] = SHORTCUTS_PREVIEW_VIDEO_AUDIO_PLAYER_ACTIONS
simple_shortcut_name_to_action_lookup[ 'custom' ] = SHORTCUTS_MEDIA_ACTIONS + SHORTCUTS_MEDIA_VIEWER_ACTIONS

SHUTDOWN_TIMESTAMP_VACUUM = 0
SHUTDOWN_TIMESTAMP_FATTEN_AC_CACHE = 1
SHUTDOWN_TIMESTAMP_DELETE_ORPHANS = 2

SORT_BY_LEXICOGRAPHIC_ASC = 8
SORT_BY_LEXICOGRAPHIC_DESC = 9
SORT_BY_INCIDENCE_ASC = 10
SORT_BY_INCIDENCE_DESC = 11
SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC = 12
SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC = 13
SORT_BY_INCIDENCE_NAMESPACE_ASC = 14
SORT_BY_INCIDENCE_NAMESPACE_DESC = 15
SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_ASC = 16
SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_DESC = 17

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

SORT_ASC = 0
SORT_DESC = 1

SORT_CHOICES = []

SORT_CHOICES.append( ( 'system', SORT_FILES_BY_FILESIZE ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_DURATION ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_IMPORT_TIME ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_FILE_MODIFIED_TIMESTAMP ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_MIME ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_RANDOM ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_WIDTH ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_HEIGHT ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_RATIO ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_NUM_PIXELS ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_NUM_TAGS ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_MEDIA_VIEWS ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_MEDIA_VIEWTIME ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_APPROX_BITRATE ) )
SORT_CHOICES.append( ( 'system', SORT_FILES_BY_HAS_AUDIO ) )

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
    
    @staticmethod
    def STATICInitialise():
        
        # These probably *could* be created even before QApplication is constructed, but it can't hurt to wait until that's done.
        
        GlobalPixmaps.bold = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_bold.png' ) )
        GlobalPixmaps.italic = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_italic.png' ) )
        GlobalPixmaps.underline = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_underline.png' ) )
        
        GlobalPixmaps.align_left = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_align_left.png' ) )
        GlobalPixmaps.align_center = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_align_center.png' ) )
        GlobalPixmaps.align_right = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_align_right.png' ) )
        GlobalPixmaps.align_justify = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_align_justify.png' ) )
        
        GlobalPixmaps.indent_less = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_indent_remove.png' ) )
        GlobalPixmaps.indent_more = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'text_indent.png' ) )
        
        GlobalPixmaps.font = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'font.png' ) )
        GlobalPixmaps.colour = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'color_swatch.png' ) )
        
        GlobalPixmaps.link = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'link.png' ) )
        GlobalPixmaps.link_break = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'link_break.png' ) )
        
        GlobalPixmaps.drag = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'drag.png' ) )
        
        GlobalPixmaps.transparent = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'transparent.png' ) )
        GlobalPixmaps.downloading = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'downloading.png' ) )
        GlobalPixmaps.file_repository = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_repository_small.png' ) )
        GlobalPixmaps.file_repository_pending = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_repository_pending_small.png' ) )
        GlobalPixmaps.file_repository_petitioned = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_repository_petitioned_small.png' ) )
        GlobalPixmaps.ipfs = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'ipfs_small.png' ) )
        GlobalPixmaps.ipfs_pending = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'ipfs_pending_small.png' ) )
        GlobalPixmaps.ipfs_petitioned = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'ipfs_petitioned_small.png' ) )
        
        GlobalPixmaps.collection = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'collection.png' ) )
        GlobalPixmaps.inbox = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'inbox.png' ) )
        GlobalPixmaps.trash = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'trash.png' ) )
        
        GlobalPixmaps.refresh = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'refresh.png' ) )
        GlobalPixmaps.archive = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'archive.png' ) )
        GlobalPixmaps.to_inbox = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'to_inbox.png' ) )
        GlobalPixmaps.delete = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'trash.png' ) )
        GlobalPixmaps.trash_delete = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'delete.png' ) )
        GlobalPixmaps.undelete = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'undelete.png' ) )
        GlobalPixmaps.zoom_in = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'zoom_in.png' ) )
        GlobalPixmaps.zoom_out = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'zoom_out.png' ) )
        GlobalPixmaps.zoom_switch = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'zoom_switch.png' ) )
        GlobalPixmaps.fullscreen_switch = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'fullscreen_switch.png' ) )
        GlobalPixmaps.open_externally = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'open_externally.png' ) )
        
        GlobalPixmaps.dump_ok = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'dump_ok.png' ) )
        GlobalPixmaps.dump_recoverable = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'dump_recoverable.png' ) )
        GlobalPixmaps.dump_fail = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'dump_fail.png' ) )
        
        GlobalPixmaps.cog = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'cog.png' ) )
        GlobalPixmaps.family = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'family.png' ) )
        GlobalPixmaps.keyboard = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'keyboard.png' ) )
        GlobalPixmaps.help = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'help.png' ) )
        
        GlobalPixmaps.check = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'check.png' ) )
        GlobalPixmaps.pause = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'pause.png' ) )
        GlobalPixmaps.play = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'play.png' ) )
        GlobalPixmaps.stop = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'stop.png' ) )
        
        GlobalPixmaps.sound = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'sound.png' ) )
        GlobalPixmaps.mute = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'mute.png' ) )
        
        GlobalPixmaps.file_pause = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_pause.png' ) )
        GlobalPixmaps.file_play = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'file_play.png' ) )
        GlobalPixmaps.gallery_pause = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'gallery_pause.png' ) )
        GlobalPixmaps.gallery_play = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'gallery_play.png' ) )
        
        GlobalPixmaps.highlight = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'highlight.png' ) )
        GlobalPixmaps.clear_highlight = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'clear_highlight.png' ) )
        
        GlobalPixmaps.listctrl = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'listctrl.png' ) )
        
        GlobalPixmaps.copy = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'copy.png' ) )
        GlobalPixmaps.paste = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'paste.png' ) )
        
        GlobalPixmaps.eight_kun = QG.QPixmap( os.path.join( HC.STATIC_DIR, '8kun.png' ) )
        GlobalPixmaps.twitter = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'twitter.png' ) )
        GlobalPixmaps.tumblr = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'tumblr.png' ) )
        GlobalPixmaps.discord = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'discord.png' ) )
        GlobalPixmaps.patreon = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'patreon.png' ) )
        
        GlobalPixmaps.first = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'first.png' ) )
        GlobalPixmaps.previous = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'previous.png' ) )
        GlobalPixmaps.next_bmp = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'next.png' ) )
        GlobalPixmaps.last = QG.QPixmap( os.path.join( HC.STATIC_DIR, 'last.png' ) )
        

DEFAULT_LOCAL_TAG_SERVICE_KEY = b'local tags'

LOCAL_FILE_SERVICE_KEY = b'local files'

LOCAL_UPDATE_SERVICE_KEY = b'repository updates'

LOCAL_BOORU_SERVICE_KEY = b'local booru'

LOCAL_NOTES_SERVICE_KEY = b'local notes'

CLIENT_API_SERVICE_KEY = b'client api'

TRASH_SERVICE_KEY = b'trash'

COMBINED_LOCAL_FILE_SERVICE_KEY = b'all local files'

COMBINED_FILE_SERVICE_KEY = b'all known files'

COMBINED_TAG_SERVICE_KEY = b'all known tags'

TEST_SERVICE_KEY = b'test service'
