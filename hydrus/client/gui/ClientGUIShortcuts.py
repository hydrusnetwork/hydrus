import collections.abc
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusLists
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientData
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions

SHORTCUT_TYPE_KEYBOARD_CHARACTER = 0
SHORTCUT_TYPE_MOUSE = 1
SHORTCUT_TYPE_KEYBOARD_SPECIAL = 2
SHORTCUT_TYPE_NOT_ALLOWED = 3

SHORTCUT_PRESS_TYPE_PRESS = 0
SHORTCUT_PRESS_TYPE_RELEASE = 1
SHORTCUT_PRESS_TYPE_DOUBLE_CLICK = 2
SHORTCUT_PRESS_TYPE_DRAG = 3

shortcut_press_type_str_lookup = {
    SHORTCUT_PRESS_TYPE_PRESS: 'press',
    SHORTCUT_PRESS_TYPE_RELEASE: 'release',
    SHORTCUT_PRESS_TYPE_DOUBLE_CLICK: 'double',
    SHORTCUT_PRESS_TYPE_DRAG: 'drag'
}

SHORTCUT_MODIFIER_CTRL = 0
SHORTCUT_MODIFIER_ALT = 1
SHORTCUT_MODIFIER_SHIFT = 2
SHORTCUT_MODIFIER_KEYPAD = 3
SHORTCUT_MODIFIER_GROUP_SWITCH = 4
SHORTCUT_MODIFIER_META = 5 # This is 'Control' in macOS, which is for system level stuff. They use 'Command/Cmd' for Ctrl stuff, which is helpfully mapped to Ctrl in Qt, so you usually don't have to change anything. Just name nonsense

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
SHORTCUT_KEY_SPECIAL_MEDIA_PLAY_PAUSE = 29
SHORTCUT_KEY_SPECIAL_MEDIA_PREVIOUS = 30
SHORTCUT_KEY_SPECIAL_MEDIA_NEXT = 31
SHORTCUT_KEY_SPECIAL_MEDIA_VOLUME_DOWN = 32
SHORTCUT_KEY_SPECIAL_MEDIA_VOLUME_UP = 33
SHORTCUT_KEY_SPECIAL_MEDIA_VOLUME_MUTE_UNMUTE = 32
SHORTCUT_KEY_SPECIAL_EMPTY_MODIFIER = 33
SHORTCUT_KEY_SPECIAL_BACKTAB = 34

if HC.PLATFORM_MACOS:
    
    DELETE_KEYS_QT = ( QC.Qt.Key.Key_Backspace, QC.Qt.Key.Key_Delete )
    DELETE_KEYS_HYDRUS = ( SHORTCUT_KEY_SPECIAL_BACKSPACE, SHORTCUT_KEY_SPECIAL_DELETE )
    
else:
    
    DELETE_KEYS_QT = ( QC.Qt.Key.Key_Delete, )
    DELETE_KEYS_HYDRUS = ( SHORTCUT_KEY_SPECIAL_DELETE, )
    

special_key_shortcut_enum_lookup = {
    QC.Qt.Key.Key_Space : SHORTCUT_KEY_SPECIAL_SPACE,
    QC.Qt.Key.Key_Backspace : SHORTCUT_KEY_SPECIAL_BACKSPACE,
    QC.Qt.Key.Key_Tab : SHORTCUT_KEY_SPECIAL_TAB,
    QC.Qt.Key.Key_Backtab : SHORTCUT_KEY_SPECIAL_BACKTAB,
    QC.Qt.Key.Key_Return : SHORTCUT_KEY_SPECIAL_RETURN,
    QC.Qt.Key.Key_Enter : SHORTCUT_KEY_SPECIAL_ENTER,
    QC.Qt.Key.Key_Pause : SHORTCUT_KEY_SPECIAL_PAUSE,
    QC.Qt.Key.Key_Escape : SHORTCUT_KEY_SPECIAL_ESCAPE,
    QC.Qt.Key.Key_Insert : SHORTCUT_KEY_SPECIAL_INSERT,
    QC.Qt.Key.Key_Delete : SHORTCUT_KEY_SPECIAL_DELETE,
    QC.Qt.Key.Key_Up : SHORTCUT_KEY_SPECIAL_UP,
    QC.Qt.Key.Key_Down : SHORTCUT_KEY_SPECIAL_DOWN,
    QC.Qt.Key.Key_Left : SHORTCUT_KEY_SPECIAL_LEFT,
    QC.Qt.Key.Key_Right : SHORTCUT_KEY_SPECIAL_RIGHT,
    QC.Qt.Key.Key_Home : SHORTCUT_KEY_SPECIAL_HOME,
    QC.Qt.Key.Key_End : SHORTCUT_KEY_SPECIAL_END,
    QC.Qt.Key.Key_PageUp : SHORTCUT_KEY_SPECIAL_PAGE_UP,
    QC.Qt.Key.Key_PageDown : SHORTCUT_KEY_SPECIAL_PAGE_DOWN,
    QC.Qt.Key.Key_F1 : SHORTCUT_KEY_SPECIAL_F1,
    QC.Qt.Key.Key_F2 : SHORTCUT_KEY_SPECIAL_F2,
    QC.Qt.Key.Key_F3 : SHORTCUT_KEY_SPECIAL_F3,
    QC.Qt.Key.Key_F4 : SHORTCUT_KEY_SPECIAL_F4,
    QC.Qt.Key.Key_F5 : SHORTCUT_KEY_SPECIAL_F5,
    QC.Qt.Key.Key_F6 : SHORTCUT_KEY_SPECIAL_F6,
    QC.Qt.Key.Key_F7 : SHORTCUT_KEY_SPECIAL_F7,
    QC.Qt.Key.Key_F8 : SHORTCUT_KEY_SPECIAL_F8,
    QC.Qt.Key.Key_F9 : SHORTCUT_KEY_SPECIAL_F9,
    QC.Qt.Key.Key_F10 : SHORTCUT_KEY_SPECIAL_F10,
    QC.Qt.Key.Key_F11 : SHORTCUT_KEY_SPECIAL_F11,
    QC.Qt.Key.Key_F12 : SHORTCUT_KEY_SPECIAL_F12,
    QC.Qt.Key.Key_MediaTogglePlayPause : SHORTCUT_KEY_SPECIAL_MEDIA_PLAY_PAUSE,
    QC.Qt.Key.Key_MediaPlay : SHORTCUT_KEY_SPECIAL_MEDIA_PLAY_PAUSE,
    QC.Qt.Key.Key_MediaPause : SHORTCUT_KEY_SPECIAL_MEDIA_PLAY_PAUSE,
    QC.Qt.Key.Key_MediaPrevious : SHORTCUT_KEY_SPECIAL_MEDIA_PREVIOUS,
    QC.Qt.Key.Key_MediaNext : SHORTCUT_KEY_SPECIAL_MEDIA_NEXT,
    QC.Qt.Key.Key_VolumeDown : SHORTCUT_KEY_SPECIAL_MEDIA_VOLUME_DOWN,
    QC.Qt.Key.Key_VolumeUp : SHORTCUT_KEY_SPECIAL_MEDIA_VOLUME_UP,
    QC.Qt.Key.Key_VolumeMute : SHORTCUT_KEY_SPECIAL_MEDIA_VOLUME_MUTE_UNMUTE,
    QC.Qt.Key.Key_Control : SHORTCUT_KEY_SPECIAL_EMPTY_MODIFIER,
    QC.Qt.Key.Key_Shift : SHORTCUT_KEY_SPECIAL_EMPTY_MODIFIER,
    QC.Qt.Key.Key_Alt : SHORTCUT_KEY_SPECIAL_EMPTY_MODIFIER,
    QC.Qt.Key.Key_Meta : SHORTCUT_KEY_SPECIAL_EMPTY_MODIFIER
}

special_key_shortcut_str_lookup = {
    SHORTCUT_KEY_SPECIAL_SPACE : 'space',
    SHORTCUT_KEY_SPECIAL_BACKSPACE : 'backspace',
    SHORTCUT_KEY_SPECIAL_TAB : 'tab',
    SHORTCUT_KEY_SPECIAL_BACKTAB : 'backtab',
    SHORTCUT_KEY_SPECIAL_RETURN : 'return',
    SHORTCUT_KEY_SPECIAL_ENTER : 'enter',
    SHORTCUT_KEY_SPECIAL_PAUSE : 'pause',
    SHORTCUT_KEY_SPECIAL_ESCAPE : 'escape',
    SHORTCUT_KEY_SPECIAL_INSERT : 'insert',
    SHORTCUT_KEY_SPECIAL_DELETE : 'delete',
    SHORTCUT_KEY_SPECIAL_UP : 'up',
    SHORTCUT_KEY_SPECIAL_DOWN : 'down',
    SHORTCUT_KEY_SPECIAL_LEFT : 'left',
    SHORTCUT_KEY_SPECIAL_RIGHT : 'right',
    SHORTCUT_KEY_SPECIAL_HOME : 'home',
    SHORTCUT_KEY_SPECIAL_END : 'end',
    SHORTCUT_KEY_SPECIAL_PAGE_DOWN : 'page down',
    SHORTCUT_KEY_SPECIAL_PAGE_UP : 'page up',
    SHORTCUT_KEY_SPECIAL_F1 : 'f1',
    SHORTCUT_KEY_SPECIAL_F2 : 'f2',
    SHORTCUT_KEY_SPECIAL_F3 : 'f3',
    SHORTCUT_KEY_SPECIAL_F4 : 'f4',
    SHORTCUT_KEY_SPECIAL_F5 : 'f5',
    SHORTCUT_KEY_SPECIAL_F6 : 'f6',
    SHORTCUT_KEY_SPECIAL_F7 : 'f7',
    SHORTCUT_KEY_SPECIAL_F8 : 'f8',
    SHORTCUT_KEY_SPECIAL_F9 : 'f9',
    SHORTCUT_KEY_SPECIAL_F10 : 'f10',
    SHORTCUT_KEY_SPECIAL_F11 : 'f11',
    SHORTCUT_KEY_SPECIAL_F12 : 'f12',
    SHORTCUT_KEY_SPECIAL_MEDIA_PLAY_PAUSE : 'media: play/pause',
    SHORTCUT_KEY_SPECIAL_MEDIA_PREVIOUS : 'media: previous',
    SHORTCUT_KEY_SPECIAL_MEDIA_NEXT : 'media: next',
    SHORTCUT_KEY_SPECIAL_MEDIA_VOLUME_DOWN : 'volume down',
    SHORTCUT_KEY_SPECIAL_MEDIA_VOLUME_UP : 'volume up',
    SHORTCUT_KEY_SPECIAL_MEDIA_VOLUME_MUTE_UNMUTE : 'volume mute/unmute',
    SHORTCUT_KEY_SPECIAL_EMPTY_MODIFIER : 'nothing'
}

SHORTCUT_MOUSE_LEFT = 0
SHORTCUT_MOUSE_RIGHT = 1
SHORTCUT_MOUSE_MIDDLE = 2
SHORTCUT_MOUSE_SCROLL_UP = 3
SHORTCUT_MOUSE_SCROLL_DOWN = 4
SHORTCUT_MOUSE_SCROLL_LEFT = 5
SHORTCUT_MOUSE_SCROLL_RIGHT = 6
SHORTCUT_MOUSE_BACK = 7
SHORTCUT_MOUSE_FORWARD = 8
SHORTCUT_MOUSE_TASK = 9

SHORTCUT_MOUSE_CLICKS = { SHORTCUT_MOUSE_LEFT, SHORTCUT_MOUSE_MIDDLE, SHORTCUT_MOUSE_RIGHT, SHORTCUT_MOUSE_BACK, SHORTCUT_MOUSE_FORWARD, SHORTCUT_MOUSE_TASK }

qt_mouse_buttons_to_hydrus_mouse_buttons = {
    QC.Qt.MouseButton.LeftButton : SHORTCUT_MOUSE_LEFT,
    QC.Qt.MouseButton.MiddleButton : SHORTCUT_MOUSE_MIDDLE,
    QC.Qt.MouseButton.RightButton : SHORTCUT_MOUSE_RIGHT,
    QC.Qt.MouseButton.BackButton : SHORTCUT_MOUSE_BACK,
    QC.Qt.MouseButton.ForwardButton : SHORTCUT_MOUSE_FORWARD,
    QC.Qt.MouseButton.TaskButton : SHORTCUT_MOUSE_TASK
}

shortcut_mouse_string_lookup = {
    SHORTCUT_MOUSE_LEFT : 'left-click',
    SHORTCUT_MOUSE_RIGHT : 'right-click',
    SHORTCUT_MOUSE_MIDDLE : 'middle-click',
    SHORTCUT_MOUSE_BACK : 'back',
    SHORTCUT_MOUSE_FORWARD : 'forward',
    SHORTCUT_MOUSE_TASK : 'task button',
    SHORTCUT_MOUSE_SCROLL_UP : 'scroll up',
    SHORTCUT_MOUSE_SCROLL_DOWN : 'scroll down',
    SHORTCUT_MOUSE_SCROLL_LEFT : 'scroll left',
    SHORTCUT_MOUSE_SCROLL_RIGHT : 'scroll right'
}

def get_shortcut_mouse_string( shortcut_key: int, call_mouse_buttons_primary_secondary_override: typing.Optional[ bool ] = None ):
    
    if call_mouse_buttons_primary_secondary_override is None:
        
        try:
            
            call_mouse_buttons_primary_secondary = CG.client_controller.new_options.GetBoolean( 'call_mouse_buttons_primary_secondary' )
            
        except:
            
            call_mouse_buttons_primary_secondary = False
            
        
    else:
        
        call_mouse_buttons_primary_secondary = call_mouse_buttons_primary_secondary_override
        
    
    if call_mouse_buttons_primary_secondary:
        
        if shortcut_key == SHORTCUT_MOUSE_LEFT:
            
            return 'primary-click'
            
        elif shortcut_key == SHORTCUT_MOUSE_RIGHT:
            
            return 'secondary-click'
            
        
    
    return shortcut_mouse_string_lookup[ shortcut_key ]
    

shortcut_names_to_pretty_names = {
    'global' : 'global',
    'main_gui' : 'the main window',
    'tags_autocomplete' : 'tag autocomplete',
    'media' : 'media actions, either thumbnails or the viewer',
    'thumbnails' : 'thumbnails',
    'media_viewer' : 'media viewers - all',
    'media_viewer_browser' : 'media viewers - \'normal\' browser',
    'archive_delete_filter' : 'media viewers - archive/delete filter',
    'duplicate_filter' : 'media viewers - duplicate filter',
    'preview_media_window' : 'the actual media in a preview window (mouse only)',
    'media_viewer_media_window' : 'the actual media in a media viewer (mouse only)',
}

shortcut_names_sorted = [
    'global',
    'main_gui',
    'tags_autocomplete',
    'media',
    'thumbnails',
    'media_viewer',
    'media_viewer_browser',
    'archive_delete_filter',
    'duplicate_filter',
    'preview_media_window',
    'media_viewer_media_window'
]

shortcut_names_to_descriptions = {
    'global' : 'Actions for the whole program. Should work in the main gui or a media viewer.',
    'archive_delete_filter' : 'Navigation actions for the media viewer during an archive/delete filter. Mouse shortcuts should work.',
    'duplicate_filter' : 'Navigation actions for the media viewer during a duplicate filter. Mouse shortcuts should work.',
    'media' : 'Actions to alter metadata for media in the media viewer or the thumbnail grid.',
    'thumbnails' : 'Actions that interact with the grid of thumbnails in a normal file page.',
    'main_gui' : 'Actions to control pages in the main window of the program.',
    'tags_autocomplete' : 'Actions to control tag autocomplete when its input text box is focused.',
    'media_viewer_browser' : 'Navigation actions for the regular browsable media viewer.',
    'media_viewer' : 'Zoom and pan and player actions for any media viewer.',
    'media_viewer_media_window' : 'Actions for any video or audio player in a media viewer window. Mouse only!',
    'preview_media_window' : 'Actions for any video or audio player in a preview window. Mouse only!'
}

# shortcut commands

SHORTCUTS_RESERVED_NAMES = [ 'global', 'archive_delete_filter', 'duplicate_filter', 'media', 'thumbnails', 'tags_autocomplete', 'main_gui', 'media_viewer_browser', 'media_viewer', 'media_viewer_media_window', 'preview_media_window' ]

SHORTCUTS_GLOBAL_ACTIONS = [
    CAC.SIMPLE_GLOBAL_AUDIO_MUTE,
    CAC.SIMPLE_GLOBAL_AUDIO_UNMUTE,
    CAC.SIMPLE_GLOBAL_AUDIO_MUTE_FLIP,
    CAC.SIMPLE_EXIT_APPLICATION,
    CAC.SIMPLE_EXIT_APPLICATION_FORCE_MAINTENANCE,
    CAC.SIMPLE_RESTART_APPLICATION,
    CAC.SIMPLE_HIDE_TO_SYSTEM_TRAY,
    CAC.SIMPLE_GLOBAL_PROFILE_MODE_FLIP,
    CAC.SIMPLE_GLOBAL_FORCE_ANIMATION_SCANBAR_SHOW
]

SHORTCUTS_MEDIA_ACTIONS = [
    CAC.SIMPLE_MANAGE_FILE_TAGS,
    CAC.SIMPLE_MANAGE_FILE_RATINGS,
    CAC.SIMPLE_MANAGE_FILE_URLS,
    CAC.SIMPLE_MANAGE_FILE_NOTES,
    CAC.SIMPLE_MANAGE_FILE_TIMESTAMPS,
    CAC.SIMPLE_ARCHIVE_FILE,
    CAC.SIMPLE_INBOX_FILE,
    CAC.SIMPLE_DELETE_FILE,
    CAC.SIMPLE_UNDELETE_FILE,
    CAC.SIMPLE_EXPORT_FILES,
    CAC.SIMPLE_EXPORT_FILES_QUICK_AUTO_EXPORT,
    CAC.SIMPLE_REMOVE_FILE_FROM_VIEW,
    CAC.SIMPLE_OPEN_FILE_IN_EXTERNAL_PROGRAM,
    CAC.SIMPLE_OPEN_FILE_IN_FILE_EXPLORER,
    CAC.SIMPLE_OPEN_FILE_IN_WEB_BROWSER,
    CAC.SIMPLE_OPEN_SELECTION_IN_NEW_PAGE,
    CAC.SIMPLE_OPEN_SELECTION_IN_NEW_DUPLICATES_FILTER_PAGE,
    CAC.SIMPLE_OPEN_SIMILAR_LOOKING_FILES,
    CAC.SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER,
    CAC.SIMPLE_COPY_FILE_BITMAP,
    CAC.SIMPLE_COPY_FILES,
    CAC.SIMPLE_COPY_FILE_PATHS,
    CAC.SIMPLE_COPY_FILE_HASHES,
    CAC.SIMPLE_COPY_FILE_SERVICE_FILENAMES,
    CAC.SIMPLE_COPY_FILE_ID,
    CAC.SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE,
    CAC.SIMPLE_DUPLICATE_MEDIA_SET_ALTERNATE_COLLECTIONS,
    CAC.SIMPLE_DUPLICATE_MEDIA_SET_CUSTOM,
    CAC.SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_BETTER,
    CAC.SIMPLE_DUPLICATE_MEDIA_SET_FOCUSED_KING,
    CAC.SIMPLE_DUPLICATE_MEDIA_SET_SAME_QUALITY,
    CAC.SIMPLE_DUPLICATE_MEDIA_SET_POTENTIAL,
    CAC.SIMPLE_SHOW_DUPLICATES,
    CAC.SIMPLE_OPEN_KNOWN_URL,
    CAC.SIMPLE_COPY_URLS,
    CAC.SIMPLE_NATIVE_OPEN_FILE_PROPERTIES,
    CAC.SIMPLE_NATIVE_OPEN_FILE_WITH_DIALOG,
    CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_DUPLICATE_GROUP,
    CAC.SIMPLE_DUPLICATE_MEDIA_DISSOLVE_ALTERNATE_GROUP,
    CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_ALL_FALSE_POSITIVES,
    CAC.SIMPLE_DUPLICATE_MEDIA_CLEAR_INTERNAL_FALSE_POSITIVES,
    CAC.SIMPLE_DUPLICATE_MEDIA_RESET_POTENTIAL_SEARCH,
    CAC.SIMPLE_DUPLICATE_MEDIA_REMOVE_POTENTIALS,
]

SHORTCUTS_MEDIA_VIEWER_ACTIONS = [
    CAC.SIMPLE_PAUSE_MEDIA,
    CAC.SIMPLE_PAUSE_PLAY_MEDIA,
    CAC.SIMPLE_MEDIA_SEEK_DELTA,
    CAC.SIMPLE_MOVE_ANIMATION_TO_PREVIOUS_FRAME,
    CAC.SIMPLE_MOVE_ANIMATION_TO_NEXT_FRAME,
    CAC.SIMPLE_SWITCH_BETWEEN_FULLSCREEN_BORDERLESS_AND_REGULAR_FRAMED_WINDOW,
    CAC.SIMPLE_PAN_UP,
    CAC.SIMPLE_PAN_DOWN,
    CAC.SIMPLE_PAN_LEFT,
    CAC.SIMPLE_PAN_RIGHT,
    CAC.SIMPLE_PAN_TOP_EDGE,
    CAC.SIMPLE_PAN_BOTTOM_EDGE,
    CAC.SIMPLE_PAN_LEFT_EDGE,
    CAC.SIMPLE_PAN_RIGHT_EDGE,
    CAC.SIMPLE_PAN_VERTICAL_CENTER,
    CAC.SIMPLE_PAN_HORIZONTAL_CENTER,
    CAC.SIMPLE_ZOOM_IN,
    CAC.SIMPLE_ZOOM_OUT,
    CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_ZOOM,
    CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM,
    CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_CANVAS_FIT_AND_FILL_ZOOM_VIEWER_CENTER,
    CAC.SIMPLE_SWITCH_BETWEEN_100_PERCENT_AND_MAX_ZOOM,
    CAC.SIMPLE_SWITCH_BETWEEN_CANVAS_AND_MAX_ZOOM,
    CAC.SIMPLE_ZOOM_100,
    CAC.SIMPLE_ZOOM_100_CENTER,
    CAC.SIMPLE_ZOOM_CANVAS,
    CAC.SIMPLE_ZOOM_CANVAS_VIEWER_CENTER,
    CAC.SIMPLE_ZOOM_DEFAULT,
    CAC.SIMPLE_ZOOM_DEFAULT_VIEWER_CENTER,
    CAC.SIMPLE_ZOOM_CANVAS_FILL_X,
    CAC.SIMPLE_ZOOM_CANVAS_FILL_X_VIEWER_CENTER,
    CAC.SIMPLE_ZOOM_CANVAS_FILL_Y,
    CAC.SIMPLE_ZOOM_CANVAS_FILL_Y_VIEWER_CENTER,
    CAC.SIMPLE_ZOOM_CANVAS_FILL_AUTO,
    CAC.SIMPLE_ZOOM_CANVAS_FILL_AUTO_VIEWER_CENTER,
    CAC.SIMPLE_ZOOM_MAX,
    CAC.SIMPLE_ZOOM_TO_PERCENTAGE,
    CAC.SIMPLE_ZOOM_TO_PERCENTAGE_CENTER,
    CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA,
    CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_VIEWER_CENTER,
    CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED,
    CAC.SIMPLE_RESIZE_WINDOW_TO_MEDIA_ZOOMED_VIEWER_CENTER,
    CAC.SIMPLE_FLIP_DARKMODE,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB_AND_FOCUS_MEDIA,
    CAC.SIMPLE_FOCUS_TAB_AND_MEDIA,
    CAC.SIMPLE_FLIP_ICC_PROFILE_APPLICATION,
    CAC.SIMPLE_RESET_PAN_TO_CENTER
]

SHORTCUTS_MEDIA_VIEWER_BROWSER_ACTIONS = [
    CAC.SIMPLE_VIEW_NEXT,
    CAC.SIMPLE_VIEW_FIRST,
    CAC.SIMPLE_VIEW_LAST,
    CAC.SIMPLE_VIEW_PREVIOUS,
    CAC.SIMPLE_VIEW_RANDOM,
    CAC.SIMPLE_UNDO_RANDOM,
    CAC.SIMPLE_PAUSE_PLAY_SLIDESHOW,
    CAC.SIMPLE_SHOW_MENU,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB_AND_FOCUS_MEDIA,
    CAC.SIMPLE_FOCUS_TAB_AND_MEDIA
]

SHORTCUTS_MAIN_GUI_ACTIONS = [
    CAC.SIMPLE_REFRESH,
    CAC.SIMPLE_REFRESH_ALL_PAGES,
    CAC.SIMPLE_REFRESH_PAGE_OF_PAGES_PAGES,
    CAC.SIMPLE_NEW_PAGE,
    CAC.SIMPLE_NEW_PAGE_OF_PAGES,
    CAC.SIMPLE_NEW_DUPLICATE_FILTER_PAGE,
    CAC.SIMPLE_NEW_GALLERY_DOWNLOADER_PAGE,
    CAC.SIMPLE_NEW_URL_DOWNLOADER_PAGE,
    CAC.SIMPLE_NEW_SIMPLE_DOWNLOADER_PAGE,
    CAC.SIMPLE_NEW_WATCHER_DOWNLOADER_PAGE,
    CAC.SIMPLE_SET_MEDIA_FOCUS,
    CAC.SIMPLE_SHOW_HIDE_SPLITTERS,
    CAC.SIMPLE_SET_SEARCH_FOCUS,
    CAC.SIMPLE_UNCLOSE_PAGE,
    CAC.SIMPLE_CLOSE_PAGE,
    CAC.SIMPLE_REDO,
    CAC.SIMPLE_UNDO,
    CAC.SIMPLE_FLIP_DARKMODE,
    CAC.SIMPLE_RUN_ALL_EXPORT_FOLDERS,
    CAC.SIMPLE_CHECK_ALL_IMPORT_FOLDERS,
    CAC.SIMPLE_FLIP_DEBUG_FORCE_IDLE_MODE_DO_NOT_SET_THIS,
    CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FAVOURITE_TAGS,
    CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RELATED_TAGS,
    CAC.SIMPLE_REFRESH_RELATED_TAGS,
    CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_FILE_LOOKUP_SCRIPT_TAGS,
    CAC.SIMPLE_SHOW_AND_FOCUS_MANAGE_TAGS_RECENT_TAGS,
    CAC.SIMPLE_FOCUS_MEDIA_VIEWER,
    CAC.SIMPLE_MOVE_PAGES_SELECTION_LEFT,
    CAC.SIMPLE_MOVE_PAGES_SELECTION_RIGHT,
    CAC.SIMPLE_MOVE_PAGES_SELECTION_HOME,
    CAC.SIMPLE_MOVE_PAGES_SELECTION_END,
    CAC.SIMPLE_OPEN_COMMAND_PALETTE,
    CAC.SIMPLE_RELOAD_CURRENT_STYLESHEET,
    CAC.SIMPLE_OPEN_OPTIONS
]

SHORTCUTS_TAGS_AUTOCOMPLETE_ACTIONS = [
    CAC.SIMPLE_SYNCHRONISED_WAIT_SWITCH,
    CAC.SIMPLE_AUTOCOMPLETE_FORCE_FETCH,
    CAC.SIMPLE_AUTOCOMPLETE_IME_MODE
]

SHORTCUTS_DUPLICATE_FILTER_ACTIONS = [
    CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_AND_DELETE_OTHER,
    CAC.SIMPLE_DUPLICATE_FILTER_THIS_IS_BETTER_BUT_KEEP_BOTH,
    CAC.SIMPLE_DUPLICATE_FILTER_EXACTLY_THE_SAME,
    CAC.SIMPLE_DUPLICATE_FILTER_ALTERNATES,
    CAC.SIMPLE_DUPLICATE_FILTER_FALSE_POSITIVE,
    CAC.SIMPLE_DUPLICATE_FILTER_CUSTOM_ACTION,
    CAC.SIMPLE_DUPLICATE_FILTER_SKIP,
    CAC.SIMPLE_DUPLICATE_FILTER_BACK,
    CAC.SIMPLE_DUPLICATE_FILTER_APPROVE_AUTO_RESOLUTION,
    CAC.SIMPLE_DUPLICATE_FILTER_DENY_AUTO_RESOLUTION,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER,
    CAC.SIMPLE_VIEW_NEXT
]

SHORTCUTS_ARCHIVE_DELETE_FILTER_ACTIONS = [
    CAC.SIMPLE_ARCHIVE_DELETE_FILTER_KEEP,
    CAC.SIMPLE_ARCHIVE_DELETE_FILTER_DELETE,
    CAC.SIMPLE_ARCHIVE_DELETE_FILTER_SKIP,
    CAC.SIMPLE_ARCHIVE_DELETE_FILTER_BACK,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER
]

SHORTCUTS_MEDIA_VIEWER_VIDEO_AUDIO_PLAYER_ACTIONS = [
    CAC.SIMPLE_PAUSE_MEDIA,
    CAC.SIMPLE_PAUSE_PLAY_MEDIA,
    CAC.SIMPLE_MEDIA_SEEK_DELTA,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB,
    CAC.SIMPLE_CLOSE_MEDIA_VIEWER_AND_FOCUS_TAB_AND_FOCUS_MEDIA,
    CAC.SIMPLE_FOCUS_TAB_AND_MEDIA
]

SHORTCUTS_PREVIEW_VIDEO_AUDIO_PLAYER_ACTIONS = [
    CAC.SIMPLE_PAUSE_MEDIA,
    CAC.SIMPLE_PAUSE_PLAY_MEDIA,
    CAC.SIMPLE_MEDIA_SEEK_DELTA,
    CAC.SIMPLE_LAUNCH_MEDIA_VIEWER
]

SHORTCUTS_THUMBNAILS_ACTIONS = [
    CAC.SIMPLE_LAUNCH_MEDIA_VIEWER,
    CAC.SIMPLE_LAUNCH_THE_ARCHIVE_DELETE_FILTER,
    CAC.SIMPLE_SELECT_FILES,
    CAC.SIMPLE_MOVE_THUMBNAIL_FOCUS,
    CAC.SIMPLE_REARRANGE_THUMBNAILS,
    CAC.SIMPLE_MAC_QUICKLOOK
]

simple_shortcut_name_to_action_lookup = {
    'global' : SHORTCUTS_GLOBAL_ACTIONS,
    'media' : SHORTCUTS_MEDIA_ACTIONS,
    'media_viewer' : SHORTCUTS_MEDIA_VIEWER_ACTIONS,
    'media_viewer_browser' : SHORTCUTS_MEDIA_VIEWER_BROWSER_ACTIONS,
    'main_gui' : SHORTCUTS_MAIN_GUI_ACTIONS,
    'tags_autocomplete' : SHORTCUTS_TAGS_AUTOCOMPLETE_ACTIONS,
    'duplicate_filter' : SHORTCUTS_DUPLICATE_FILTER_ACTIONS + SHORTCUTS_MEDIA_ACTIONS + SHORTCUTS_MEDIA_VIEWER_ACTIONS,
    'archive_delete_filter' : SHORTCUTS_ARCHIVE_DELETE_FILTER_ACTIONS,
    'media_viewer_media_window' : SHORTCUTS_MEDIA_VIEWER_VIDEO_AUDIO_PLAYER_ACTIONS,
    'preview_media_window' : SHORTCUTS_PREVIEW_VIDEO_AUDIO_PLAYER_ACTIONS,
    'thumbnails' : SHORTCUTS_THUMBNAILS_ACTIONS,
    'custom' : SHORTCUTS_MEDIA_ACTIONS + SHORTCUTS_MEDIA_VIEWER_ACTIONS
}

simple_shortcut_name_to_action_lookup = { key : HydrusLists.DedupeList( value ) for ( key, value ) in simple_shortcut_name_to_action_lookup.items() }

CUMULATIVE_MOUSEWARP_MANHATTAN_LENGTH = 0

def AncestorShortcutsHandlers( widget: QW.QWidget ):
    
    shortcuts_handlers = []
    
    window = widget.window()
    
    if window == widget:
        
        return shortcuts_handlers
        
    
    widget = widget.parentWidget()
    
    if widget is None:
        
        return shortcuts_handlers
        
    
    while True:
        
        child_shortcuts_handlers = [ child for child in widget.children() if isinstance( child, ShortcutsHandler ) ]
        
        shortcuts_handlers.extend( child_shortcuts_handlers )
        
        if widget == window:
            
            break
            
        
        widget = widget.parentWidget()
        
        if widget is None:
            
            break
            
        
    
    return shortcuts_handlers
    

# ok, the problem here is that I get key codes that are converted, so if someone does shift+1 on a US keyboard, this ends up with Shift+! same with ctrl+alt+ to get accented characters
# it isn't really a big deal since everything still lines up, but the QGuiApplicationPrivate::platformIntegration()->possibleKeys(e) to get some variant of 'yeah this is just !' seems unavailable for python
# it is basically a display bug, but it'd be nice to have it working right
def ConvertQtKeyToShortcutKey( key_qt ):
    
    if key_qt in special_key_shortcut_enum_lookup:
        
        key_ord = special_key_shortcut_enum_lookup[ key_qt ]
        
        return ( SHORTCUT_TYPE_KEYBOARD_SPECIAL, key_ord )
        
    else:
        
        key_ord = int( key_qt )
        
        try:
            
            if key_ord == 0:
                
                raise Exception( 'Shortcut caught a null key' ) # I think this is like 'release alt' or some weird code
                
            
            key_chr = chr( key_ord )
            
            # this is turbo lower() that converts Scharfes S (beta) to 'ss'
            key_chr = key_chr.casefold()[0]
            
            casefold_key_ord = ord( key_chr )
            
            return ( SHORTCUT_TYPE_KEYBOARD_CHARACTER, casefold_key_ord )
            
        except:
            
            if HG.shortcut_report_mode:
                
                HydrusData.ShowText( f'This key ord was not allowed: {key_ord}' )
                
            
            return ( SHORTCUT_TYPE_NOT_ALLOWED, key_ord )
            
        
    

def ConvertKeyEventToShortcut( event, shortcuts_merge_non_number_numpad_override = None ):
    
    key_qt = event.key()
    
    ( shortcut_type, key_ord ) = ConvertQtKeyToShortcutKey( key_qt )
    
    if shortcut_type != SHORTCUT_TYPE_NOT_ALLOWED:
        
        modifiers = []
        
        if event.modifiers() & QC.Qt.KeyboardModifier.AltModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_ALT )
            
        
        if event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_CTRL )
            
        
        if event.modifiers() & QC.Qt.KeyboardModifier.MetaModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_META )
            
        
        if event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_SHIFT )
            
        
        if event.modifiers() & QC.Qt.KeyboardModifier.GroupSwitchModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_GROUP_SWITCH )
            
        
        if event.modifiers() & QC.Qt.KeyboardModifier.KeypadModifier:
            
            do_it = True
            
            if shortcuts_merge_non_number_numpad_override is None:
                
                try:
                    
                    shortcuts_merge_non_number_numpad = CG.client_controller.new_options.GetBoolean( 'shortcuts_merge_non_number_numpad' )
                    
                except:
                    
                    shortcuts_merge_non_number_numpad = True
                    
                
            else:
                
                shortcuts_merge_non_number_numpad = shortcuts_merge_non_number_numpad_override
                
            
            if shortcuts_merge_non_number_numpad:
                
                it_is_a_number = ord( '0' ) <= key_ord <= ord( '9' )
                
                if not it_is_a_number:
                    
                    do_it = False
                    
                
            
            if do_it:
                
                modifiers.append( SHORTCUT_MODIFIER_KEYPAD )
                
            
        
        shortcut_press_type = SHORTCUT_PRESS_TYPE_PRESS
        
        shortcut = Shortcut( shortcut_type, key_ord, shortcut_press_type, modifiers )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'key event caught: ' + repr( shortcut ) )
            
        
        return shortcut
        
    
    return None
    

def ConvertKeyEventToSimpleTuple( event ):
    
    modifier = QC.Qt.KeyboardModifier.NoModifier
    
    if event.modifiers() & QC.Qt.KeyboardModifier.AltModifier:
        
        modifier = QC.Qt.KeyboardModifier.AltModifier
        
    elif event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier:
        
        modifier = QC.Qt.KeyboardModifier.ControlModifier
        
    elif event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier:
        
        modifier = QC.Qt.KeyboardModifier.ShiftModifier
        
    elif event.modifiers() & QC.Qt.KeyboardModifier.KeypadModifier:
        
        modifier = QC.Qt.KeyboardModifier.KeypadModifier
        
    elif event.modifiers() & QC.Qt.KeyboardModifier.GroupSwitchModifier:
        
        modifier = QC.Qt.KeyboardModifier.GroupSwitchModifier
        
    elif event.modifiers() & QC.Qt.KeyboardModifier.MetaModifier:
        
        modifier = QC.Qt.KeyboardModifier.MetaModifier
        
    
    key = event.key()
    
    return ( modifier, key )
    

GLOBAL_MOUSE_SCROLL_DELTA_FOR_TRACKPADS = 0
ONE_TICK_ON_A_NORMAL_MOUSE_IN_EIGHTS_OF_A_DEGREE = 15 * 8 # fifteen degrees, in eighths of a degree

def ConvertMouseEventToShortcut( event: typing.Union[ QG.QMouseEvent, QG.QWheelEvent ] ):
    
    key = None
    
    shortcut_press_type = SHORTCUT_PRESS_TYPE_PRESS
    
    if event.type() == QC.QEvent.Type.MouseButtonPress:
        
        for ( qt_button, hydrus_button ) in qt_mouse_buttons_to_hydrus_mouse_buttons.items():
            
            if event.buttons() & qt_button:
                
                key = hydrus_button
                
                break
                
            
        
    elif event.type() in ( QC.QEvent.Type.MouseButtonDblClick, QC.QEvent.Type.MouseButtonRelease ):
        
        if event.type() == QC.QEvent.Type.MouseButtonRelease:
            
            shortcut_press_type = SHORTCUT_PRESS_TYPE_RELEASE
            
        elif event.type() == QC.QEvent.Type.MouseButtonDblClick:
            
            shortcut_press_type = SHORTCUT_PRESS_TYPE_DOUBLE_CLICK
            
        
        for ( qt_button, hydrus_button ) in qt_mouse_buttons_to_hydrus_mouse_buttons.items():
            
            if event.button() == qt_button:
                
                key = hydrus_button
                
                break
                
            
        
    elif event.type() == QC.QEvent.Type.Wheel:
        
        angle_delta_point = event.angleDelta()
        
        if angle_delta_point is None:
            
            return None
            
        
        angle_delta = angle_delta_point.y()
        
        # we used to do QP.WheelEventIsSynthesised here (event.source() == QC.Qt.MouseEventSynthesizedBySystem and event.pointerType() != QG.QPointingDevice.PointerType.Generic), but it seems some normal mice produce a billion small wheel events for smoothscroll gubbins or something, lfg
        # so let's just try this tech for everyone
        if abs( angle_delta ) < ONE_TICK_ON_A_NORMAL_MOUSE_IN_EIGHTS_OF_A_DEGREE:
            
            # likely using a trackpad to generate artificial wheel events
            
            global GLOBAL_MOUSE_SCROLL_DELTA_FOR_TRACKPADS
            
            GLOBAL_MOUSE_SCROLL_DELTA_FOR_TRACKPADS += angle_delta
            
            if abs( GLOBAL_MOUSE_SCROLL_DELTA_FOR_TRACKPADS ) > ONE_TICK_ON_A_NORMAL_MOUSE_IN_EIGHTS_OF_A_DEGREE:
                
                angle_delta = GLOBAL_MOUSE_SCROLL_DELTA_FOR_TRACKPADS
                
                GLOBAL_MOUSE_SCROLL_DELTA_FOR_TRACKPADS = 0
                
            else:
                
                return None
                
            
        
        if angle_delta > 0:
            
            key = SHORTCUT_MOUSE_SCROLL_UP
            
        elif angle_delta < 0:
            
            key = SHORTCUT_MOUSE_SCROLL_DOWN
            
        
    
    if key is not None:
        
        modifiers = []
        
        if event.modifiers() & QC.Qt.KeyboardModifier.AltModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_ALT )
            
        
        if event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_CTRL )
            
        
        if event.modifiers() & QC.Qt.KeyboardModifier.MetaModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_META )
            
        
        if event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_SHIFT )
            
        
        if event.modifiers() & QC.Qt.KeyboardModifier.GroupSwitchModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_GROUP_SWITCH )
            
        
        shortcut = Shortcut( SHORTCUT_TYPE_MOUSE, key, shortcut_press_type, modifiers )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'mouse event caught: ' + repr( shortcut ) )
            
        
        return shortcut
        
    
    return None
    

def IShouldCatchShortcutEvent( event_handler_owner: QC.QObject, event_catcher: QW.QWidget, event: typing.Optional[ QC.QEvent ] = None, child_tlw_classes_who_can_pass_up: typing.Optional[ collections.abc.Collection[ type ] ] = None ):
    
    do_focus_test = True
    
    if event is not None:
        
        # the event happened to somewhere else, most likely a hover window of a media viewer
        # should we intercept that event that happened somewhere else?
        if event_handler_owner != event_catcher:
            
            # don't pass clicks up
            if event.type() in ( QC.QEvent.Type.MouseButtonPress, QC.QEvent.Type.MouseButtonRelease, QC.QEvent.Type.MouseButtonDblClick ):
                
                return False
                
            
            # don't pass wheels that happen to legit controls that want to eat it, like a list, when the catcher is a window
            if event.type() == QC.QEvent.Type.Wheel:
                
                widget_under_mouse = event_catcher.childAt( event_catcher.mapFromGlobal( QG.QCursor.pos() ) )
                
                if widget_under_mouse is not None:
                    
                    mouse_scroll_over_window_greyspace = widget_under_mouse == event_catcher and event_catcher.isWindow()
                    
                    if not mouse_scroll_over_window_greyspace:
                        
                        return False
                        
                    
                
            
        
        if event.type() == QC.QEvent.Type.Wheel:
            
            do_focus_test = False
            
        
    
    do_focus_test = False # lmao, why this here? I guess it got turned off
    
    if do_focus_test:
        
        if not ClientGUIFunctions.TLWIsActive( event_handler_owner ):
            
            if child_tlw_classes_who_can_pass_up is not None:
                
                child_tlw_has_focus = ClientGUIFunctions.WidgetOrAnyTLWChildHasFocus( event_handler_owner ) and isinstance( QW.QApplication.activeWindow(), child_tlw_classes_who_can_pass_up )
                
                if not child_tlw_has_focus:
                    
                    return False
                    
                
            else:
                
                return False
                
            
        
    
    return True
    

def KeyPressEventIsACopy( event: QG.QKeyEvent ):
    
    ctrl = event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier
    
    key_code = event.key()
    
    return ctrl and key_code in ( ord( 'C' ), ord( 'c' ), QC.Qt.Key.Key_Insert )
    

def KeyPressEventIsAPaste( event: QG.QKeyEvent ):
    
    ctrl = event.modifiers() & QC.Qt.KeyboardModifier.ControlModifier
    shift = event.modifiers() & QC.Qt.KeyboardModifier.ShiftModifier
    
    key_code = event.key()
    
    return ( ctrl and key_code in ( ord( 'V' ), ord( 'v' ) ) ) or ( shift and key_code == QC.Qt.Key.Key_Insert )
    

class Shortcut( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT
    SERIALISABLE_NAME = 'Shortcut'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, shortcut_type = None, shortcut_key = None, shortcut_press_type = None, modifiers = None ):
        
        if shortcut_type is None:
            
            shortcut_type = SHORTCUT_TYPE_KEYBOARD_SPECIAL
            
        
        if shortcut_key is None:
            
            shortcut_key = SHORTCUT_KEY_SPECIAL_F7
            
        
        if shortcut_press_type is None:
            
            shortcut_press_type = SHORTCUT_PRESS_TYPE_PRESS
            
        
        if modifiers is None:
            
            modifiers = []
            
        
        if shortcut_type == SHORTCUT_TYPE_KEYBOARD_CHARACTER and ClientData.OrdIsAlphaUpper( shortcut_key ):
            
            shortcut_key += 32 # convert A to a
            
        
        modifiers = sorted( modifiers )
        
        super().__init__()
        
        self.shortcut_type = shortcut_type
        self.shortcut_key = shortcut_key
        self.shortcut_press_type = shortcut_press_type
        self.modifiers = modifiers
        
    
    def __eq__( self, other ):
        
        if isinstance( other, Shortcut ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self.shortcut_type, self.shortcut_key, self.shortcut_press_type, tuple( self.modifiers ) ).__hash__()
        
    
    def __repr__( self ):
        
        return 'Shortcut: ' + self.ToString()
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self.shortcut_type, self.shortcut_key, self.shortcut_press_type, self.modifiers )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self.shortcut_type, self.shortcut_key, self.shortcut_press_type, self.modifiers ) = serialisable_info
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            # these are dicts that convert fixed wx enums to new stuff
            wx_to_qt_flat_conversion = {
                32 : SHORTCUT_KEY_SPECIAL_SPACE,
                8 : SHORTCUT_KEY_SPECIAL_BACKSPACE,
                9 : SHORTCUT_KEY_SPECIAL_TAB,
                13 : SHORTCUT_KEY_SPECIAL_RETURN,
                310 : SHORTCUT_KEY_SPECIAL_PAUSE,
                27 : SHORTCUT_KEY_SPECIAL_ESCAPE,
                322 : SHORTCUT_KEY_SPECIAL_INSERT,
                127 : SHORTCUT_KEY_SPECIAL_DELETE,
                315 : SHORTCUT_KEY_SPECIAL_UP,
                317 : SHORTCUT_KEY_SPECIAL_DOWN,
                314 : SHORTCUT_KEY_SPECIAL_LEFT,
                316 : SHORTCUT_KEY_SPECIAL_RIGHT,
                313 : SHORTCUT_KEY_SPECIAL_HOME,
                312 : SHORTCUT_KEY_SPECIAL_END,
                367 : SHORTCUT_KEY_SPECIAL_PAGE_DOWN,
                366 : SHORTCUT_KEY_SPECIAL_PAGE_UP,
                340 : SHORTCUT_KEY_SPECIAL_F1,
                341 : SHORTCUT_KEY_SPECIAL_F2,
                342 : SHORTCUT_KEY_SPECIAL_F3,
                343 : SHORTCUT_KEY_SPECIAL_F4,
                344 : SHORTCUT_KEY_SPECIAL_F5,
                345 : SHORTCUT_KEY_SPECIAL_F6,
                346 : SHORTCUT_KEY_SPECIAL_F7,
                347 : SHORTCUT_KEY_SPECIAL_F8,
                348 : SHORTCUT_KEY_SPECIAL_F9,
                349 : SHORTCUT_KEY_SPECIAL_F10,
                350 : SHORTCUT_KEY_SPECIAL_F11,
                351 : SHORTCUT_KEY_SPECIAL_F12
            }
            
            # regular keys, but numpad, that are tracked in wx by combined unique enum
            wx_to_qt_numpad_ascii_conversion = {
                324 : ord( '0' ),
                325 : ord( '1' ),
                326 : ord( '2' ),
                327 : ord( '3' ),
                328 : ord( '4' ),
                329 : ord( '5' ),
                330 : ord( '6' ),
                331 : ord( '7' ),
                332 : ord( '8' ),
                333 : ord( '9' ),
                388 : ord( '+' ),
                392 : ord( '/' ),
                390 : ord( '-' ),
                387 : ord( '*' ),
                391 : ord( '.' )
                }
            
            wx_to_qt_numpad_conversion = {
                377 : SHORTCUT_KEY_SPECIAL_UP,
                379 : SHORTCUT_KEY_SPECIAL_DOWN,
                376 : SHORTCUT_KEY_SPECIAL_LEFT,
                378 : SHORTCUT_KEY_SPECIAL_RIGHT,
                375 : SHORTCUT_KEY_SPECIAL_HOME,
                382 : SHORTCUT_KEY_SPECIAL_END,
                381 : SHORTCUT_KEY_SPECIAL_PAGE_DOWN,
                380 : SHORTCUT_KEY_SPECIAL_PAGE_UP,
                385 : SHORTCUT_KEY_SPECIAL_DELETE,
                370 : SHORTCUT_KEY_SPECIAL_ENTER
                }
            
            ( shortcut_type, shortcut_key, modifiers ) = old_serialisable_info
            
            if shortcut_type == SHORTCUT_TYPE_KEYBOARD_CHARACTER:
                
                if shortcut_key in wx_to_qt_flat_conversion:
                    
                    shortcut_type = SHORTCUT_TYPE_KEYBOARD_SPECIAL
                    shortcut_key = wx_to_qt_flat_conversion[ shortcut_key ]
                    
                elif shortcut_key in wx_to_qt_numpad_ascii_conversion:
                    
                    shortcut_key = wx_to_qt_numpad_ascii_conversion[ shortcut_key ]
                    
                    modifiers = list( modifiers )
                    
                    modifiers.append( SHORTCUT_MODIFIER_KEYPAD )
                    
                    modifiers.sort()
                    
                elif shortcut_key in wx_to_qt_numpad_conversion:
                    
                    shortcut_type = SHORTCUT_TYPE_KEYBOARD_SPECIAL
                    shortcut_key = wx_to_qt_numpad_conversion[ shortcut_key ]
                    
                    modifiers = list( modifiers )
                    
                    modifiers.append( SHORTCUT_MODIFIER_KEYPAD )
                    
                    modifiers.sort()
                    
                
            
            if shortcut_type == SHORTCUT_TYPE_KEYBOARD_CHARACTER:
                
                if ClientData.OrdIsAlphaUpper( shortcut_key ):
                    
                    shortcut_key += 32 # convert 'A' to 'a'
                    
                
            
            new_serialisable_info = ( shortcut_type, shortcut_key, modifiers )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( shortcut_type, shortcut_key, modifiers ) = old_serialisable_info
            
            shortcut_press_type = SHORTCUT_PRESS_TYPE_PRESS
            
            new_serialisable_info = ( shortcut_type, shortcut_key, shortcut_press_type, modifiers )
            
            return ( 3, new_serialisable_info )
            
        
    
    def ConvertToSingleClick( self ):
        
        if self.IsDoubleClick():
            
            new_shortcut = self.Duplicate()
            
            new_shortcut.shortcut_press_type = SHORTCUT_PRESS_TYPE_PRESS
            
            return new_shortcut
            
        
        return self
        
    
    def GetSearchShortcuts( self, shortcuts_merge_non_number_numpad_override = None ) -> set[ "Shortcut" ]:
        
        search_shortcuts = { self }
        
        if shortcuts_merge_non_number_numpad_override is None:
            
            try:
                
                shortcuts_merge_non_number_numpad = CG.client_controller.new_options.GetBoolean( 'shortcuts_merge_non_number_numpad' )
                
            except:
                
                shortcuts_merge_non_number_numpad = False
                
        else:
            
            shortcuts_merge_non_number_numpad = shortcuts_merge_non_number_numpad_override
            
        
        if shortcuts_merge_non_number_numpad:
            
            it_is_a_number = ord( '0' ) <= self.shortcut_key <= ord( '9' )
            
            if not it_is_a_number:
                
                numpad_alternate = self.Duplicate()
                
                if SHORTCUT_MODIFIER_KEYPAD not in numpad_alternate.modifiers:
                    
                    numpad_alternate.modifiers.append( SHORTCUT_MODIFIER_KEYPAD )
                    
                    search_shortcuts.add( numpad_alternate )
                    
                
            
        
        return search_shortcuts
        
    
    def GetShortcutType( self ):
        
        return self.shortcut_type
        
    
    def IsAppropriateForPressRelease( self ):
        
        return self.shortcut_key in SHORTCUT_MOUSE_CLICKS and self.shortcut_press_type != SHORTCUT_PRESS_TYPE_DOUBLE_CLICK
        
    
    def IsDoubleClick( self ):
        
        return self.shortcut_type == SHORTCUT_TYPE_MOUSE and self.shortcut_press_type == SHORTCUT_PRESS_TYPE_DOUBLE_CLICK
        
    
    def ToString( self, call_mouse_buttons_primary_secondary_override = None ):
        
        components = []
        
        for_menu = False # I think this ⌘ stuff is only really for short menu labels, which we don't really do anyway, so disabled for now
        
        if HC.PLATFORM_MACOS and for_menu: 
            
            modifier_chain_separator = ''
            modifier_mouse_separator = '-'
            modifier_key_separator = ''
            
            if SHORTCUT_MODIFIER_META in self.modifiers:
                
                components.append( '\u2303' ) # ⌃, 'Control'
                
            
            if SHORTCUT_MODIFIER_CTRL in self.modifiers:
                
                components.append( '\u2318' ) # ⌘, 'Command'
                
            
            if SHORTCUT_MODIFIER_ALT in self.modifiers:
                
                components.append( '\u2325' ) # ⌥, 'Option'
                
            
            if SHORTCUT_MODIFIER_SHIFT in self.modifiers:
                
                components.append( '\u21e7' ) # ⇧, 'Shift'
                
            
        else:
            
            modifier_chain_separator = '+'
            modifier_mouse_separator = '+'
            modifier_key_separator = '+'
            
            if SHORTCUT_MODIFIER_META in self.modifiers:
                
                components.append( 'control' )
                
            
            if SHORTCUT_MODIFIER_CTRL in self.modifiers:
                
                if HC.PLATFORM_MACOS:
                    
                    components.append( 'command' )
                    
                else:
                    
                    components.append( 'ctrl' )
                    
                
            
            if SHORTCUT_MODIFIER_ALT in self.modifiers:
                
                if HC.PLATFORM_MACOS:
                    
                    components.append( 'option' )
                    
                else:
                    
                    components.append( 'alt' )
                    
                
            
            if SHORTCUT_MODIFIER_SHIFT in self.modifiers:
                
                components.append( 'shift' )
                
            
        
        if SHORTCUT_MODIFIER_GROUP_SWITCH in self.modifiers:
            
            components.append( 'Mode_switch' )
            
        
        if self.shortcut_press_type != SHORTCUT_PRESS_TYPE_PRESS:
            
            action_name = '{} '.format( shortcut_press_type_str_lookup[ self.shortcut_press_type ] )
            
        else:
            
            action_name = ''
            
        
        if self.shortcut_type == SHORTCUT_TYPE_MOUSE and self.shortcut_key in shortcut_mouse_string_lookup:
            
            action_name += get_shortcut_mouse_string( self.shortcut_key, call_mouse_buttons_primary_secondary_override = call_mouse_buttons_primary_secondary_override )
            
        elif self.shortcut_type == SHORTCUT_TYPE_KEYBOARD_SPECIAL and self.shortcut_key in special_key_shortcut_str_lookup:
            
            action_name += special_key_shortcut_str_lookup[ self.shortcut_key ]
            
        elif self.shortcut_type == SHORTCUT_TYPE_KEYBOARD_CHARACTER:
            
            try:
                
                if ClientData.OrdIsAlphaUpper( self.shortcut_key ):
                    
                    action_name += chr( self.shortcut_key + 32 ) # + 32 for converting ascii A -> a
                    
                else:
                    
                    action_name += chr( self.shortcut_key )
                    
                
            except:
                
                action_name += 'unknown key: {}'.format( repr( self.shortcut_key ) )
                
            
        else:
            
            action_name += 'unknown key: {}'.format( repr( self.shortcut_key ) )
            
        
        if len( components ) > 0:
            
            action_separator_to_use = modifier_mouse_separator if self.shortcut_type == SHORTCUT_TYPE_MOUSE else modifier_key_separator
            
            s = f'{modifier_chain_separator.join( components )}{action_separator_to_use}{action_name}'
            
        else:
            
            s = action_name
            
        
        if SHORTCUT_MODIFIER_KEYPAD in self.modifiers:
            
            s += ' (on numpad)'
            
        
        return s
        
    
    def TryToIncrementKey( self ):
        
        if self.shortcut_type == SHORTCUT_TYPE_KEYBOARD_CHARACTER:
            
            new_shortcut_key = self.shortcut_key + 1
            
            if ClientData.OrdIsAlphaLower( new_shortcut_key ) or ClientData.OrdIsNumber( new_shortcut_key ):
                
                self.shortcut_key = new_shortcut_key
                
                return
                
            
        elif self.shortcut_type == SHORTCUT_TYPE_KEYBOARD_SPECIAL:
            
            new_shortcut_key = self.shortcut_key + 1
            
            if new_shortcut_key in special_key_shortcut_str_lookup:
                
                self.shortcut_key = new_shortcut_key
                
                return
                
            
        
        raise HydrusExceptions.VetoException( 'Sorry, cannot increment that shortcut!' )
        
    

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT ] = Shortcut

class ShortcutSet( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET
    SERIALISABLE_NAME = 'Shortcut Set'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name ):
        
        super().__init__( name )
        
        self._shortcuts_to_commands = {}
        
    
    def __iter__( self ):
        
        for ( shortcut, command ) in list( self._shortcuts_to_commands.items() ):
            
            yield ( shortcut, command )
            
        
    
    def __len__( self ):
        
        return len( self._shortcuts_to_commands )
        
    
    def _GetSerialisableInfo( self ):
        
        return [ ( shortcut.GetSerialisableTuple(), command.GetSerialisableTuple() ) for ( shortcut, command ) in list(self._shortcuts_to_commands.items()) ]
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        for ( serialisable_shortcut, serialisable_command ) in serialisable_info:
            
            shortcut = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_shortcut )
            command = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_command )
            
            self._shortcuts_to_commands[ shortcut ] = command
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_mouse_actions, serialisable_keyboard_actions ) = old_serialisable_info
            
            shortcuts_to_commands = {}
            
            # this never stored mouse actions, so skip
            
            services_manager = CG.client_controller.services_manager
            
            for ( modifier, key, ( serialisable_service_key, data ) ) in serialisable_keyboard_actions:
                
                # no longer updating modifier, as that was wx legacy
                
                modifiers = []
                
                shortcut = Shortcut( SHORTCUT_TYPE_KEYBOARD_CHARACTER, key, SHORTCUT_PRESS_TYPE_PRESS, modifiers )
                
                if serialisable_service_key is None:
                    
                    command = CAC.ApplicationCommand.STATICCreateSimpleCommand( data )
                    
                else:
                    
                    service_key = bytes.fromhex( serialisable_service_key )
                    
                    if not services_manager.ServiceExists( service_key ):
                        
                        continue
                        
                    
                    action = HC.CONTENT_UPDATE_FLIP
                    
                    value = data
                    
                    service = services_manager.GetService( service_key )
                    
                    service_type = service.GetServiceType()
                    
                    if service_type in HC.REAL_TAG_SERVICES:
                        
                        content_type = HC.CONTENT_TYPE_MAPPINGS
                        
                    elif service_type in HC.RATINGS_SERVICES:
                        
                        content_type = HC.CONTENT_TYPE_RATINGS
                        
                    else:
                        
                        continue
                        
                    
                    command = CAC.ApplicationCommand( CAC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, content_type, action, value ) )
                    
                
                shortcuts_to_commands[ shortcut ] = command
                
            
            new_serialisable_info = ( ( shortcut.GetSerialisableTuple(), command.GetSerialisableTuple() ) for ( shortcut, command ) in list(shortcuts_to_commands.items()) )
            
            return ( 2, new_serialisable_info )
            
        
    
    def DeleteShortcut( self, shortcut: Shortcut ):
        
        if shortcut in self._shortcuts_to_commands:
            
            del self._shortcuts_to_commands[ shortcut ]
            
        
    
    def GetCommand( self, shortcut: Shortcut, shortcuts_merge_non_number_numpad_override = None ):
        
        for s in shortcut.GetSearchShortcuts( shortcuts_merge_non_number_numpad_override = shortcuts_merge_non_number_numpad_override ):
            
            if s in self._shortcuts_to_commands:
                
                return self._shortcuts_to_commands[ s ]
                
            
        
        return None
        
    
    def GetShortcuts( self, simple_action: int ):
        
        shortcuts = []
        
        for ( shortcut, command ) in self._shortcuts_to_commands.items():
            
            if command.IsSimpleCommand() and command.GetSimpleAction() == simple_action:
                
                shortcuts.append( shortcut )
                
            
        
        return shortcuts
        
    
    def GetShortcutsAndCommands( self ):
        
        return list( self._shortcuts_to_commands.items() )
        
    
    def HasCommand( self, shortcut: Shortcut ):
        
        return self.GetCommand( shortcut ) is not None
        
    
    def SetCommand( self, shortcut: Shortcut, command: CAC.ApplicationCommand ):
        
        self._shortcuts_to_commands[ shortcut ] = command
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET ] = ShortcutSet

class ShortcutsHandler( QC.QObject ):
    
    def __init__( self, parent: QW.QWidget, command_processor: CAC.ApplicationCommandProcessorMixin, initial_shortcuts_names: collections.abc.Collection[ str ], alternate_filter_target = None, catch_mouse = False, ignore_activating_mouse_click = False ):
        
        super().__init__( parent )
        
        self._catch_mouse = catch_mouse
        
        self._last_click_down_position = QC.QPoint( 0, 0 )
        
        filter_target = parent
        
        if alternate_filter_target is not None:
            
            filter_target = alternate_filter_target
            
        
        self._filter_target = filter_target
        
        self._parent = parent
        self._command_processor = command_processor
        self._filter_target.installEventFilter( self )
        self._shortcuts_names = list( initial_shortcuts_names )
        
        self._ignore_activating_mouse_click = ignore_activating_mouse_click
        self._activating_wait_job = None
        
        self._frame_activated_time = 0.0
        self._parent_currently_activated = True
        
        if self._catch_mouse and self._ignore_activating_mouse_click:
            
            self._deactivation_catcher = ShortcutsDeactivationCatcher( self, parent )
            
        
    
    def _ProcessShortcut( self, shortcut: Shortcut ):
        
        shortcut_processed = False
        
        command = shortcuts_manager().GetCommand( self._shortcuts_names, shortcut )
        
        if command is None and shortcut.IsDoubleClick():
            
            # ok, so user double-clicked
            # if a parent wants to catch this (for instance the media viewer when we double-click a video), then we want that parent to have it
            # but if no parent wants it, we can try converting it to a single-click to see if that does anything
            
            ancestor_shortcuts_handlers = AncestorShortcutsHandlers( self._parent )
            
            all_ancestor_shortcut_names = HydrusLists.MassUnion( [ ancestor_shortcuts_handler.GetShortcutNames() for ancestor_shortcuts_handler in ancestor_shortcuts_handlers ] )
            
            ancestor_command = shortcuts_manager().GetCommand( all_ancestor_shortcut_names, shortcut )
            
            if ancestor_command is None:
                
                if HG.shortcut_report_mode:
                    
                    message = 'Shortcut "' + shortcut.ToString() + '" did not match any command. The single click version is now being attempted.'
                    
                    HydrusData.ShowText( message )
                    
                
                shortcut = shortcut.ConvertToSingleClick()
                
                command = shortcuts_manager().GetCommand( self._shortcuts_names, shortcut )
                
            else:
                
                if HG.shortcut_report_mode:
                    
                    message = 'Shortcut "' + shortcut.ToString() + '" did not match any command. A parent seems to want it, however, so the single click version will not be attempted.'
                    
                    HydrusData.ShowText( message )
                    
                
            
        
        if command is not None:
            
            command_processed = self._command_processor.ProcessApplicationCommand( command )
            
            if command_processed:
                
                shortcut_processed = True
                
            
            if HG.shortcut_report_mode:
                
                message = 'Shortcut "{}" matched to command "{}" on {}.'.format( shortcut.ToString(), command.ToString(), repr( self._parent ) )
                
                if command_processed:
                    
                    message += ' It was processed.'
                    
                else:
                    
                    message += ' It was not processed.'
                    
                
                HydrusData.ShowText( message )
                
            
        
        return shortcut_processed
        
    
    def AddWindowToFilter( self, win: QW.QWidget ):
        
        win.installEventFilter( self )
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.KeyPress:
                
                i_should_catch_shortcut_event = IShouldCatchShortcutEvent( self._filter_target, watched, event = event )
                
                shortcut = ConvertKeyEventToShortcut( event )
                
                if shortcut is not None:
                    
                    if HG.shortcut_report_mode:
                        
                        message = 'Key shortcut "{}" passing through {}.'.format( shortcut.ToString(), repr( self._parent ) )
                        
                        if i_should_catch_shortcut_event:
                            
                            message += ' I am in a state to catch it.'
                            
                        else:
                            
                            message += ' I am not in a state to catch it.'
                            
                        
                        HydrusData.ShowText( message )
                        
                    
                    if i_should_catch_shortcut_event:
                        
                        shortcut_processed = self._ProcessShortcut( shortcut )
                        
                        if shortcut_processed:
                            
                            event.accept()
                            
                            return True
                            
                        
                    
                
            elif self._catch_mouse:
                
                if event.type() in ( QC.QEvent.Type.MouseButtonPress, QC.QEvent.Type.MouseButtonRelease, QC.QEvent.Type.MouseButtonDblClick, QC.QEvent.Type.Wheel ):
                    
                    global CUMULATIVE_MOUSEWARP_MANHATTAN_LENGTH
                    
                    if event.type() == QC.QEvent.Type.MouseButtonPress:
                        
                        event = typing.cast( QG.QMouseEvent, event )
                        
                        self._last_click_down_position = event.globalPosition().toPoint()
                        
                        CUMULATIVE_MOUSEWARP_MANHATTAN_LENGTH = 0
                        
                    
                    #if event.type() != QC.QEvent.Type.Wheel and self._ignore_activating_mouse_click and not HydrusTime.TimeHasPassedPrecise( self._frame_activated_time + 0.017 ):
                    if event.type() != QC.QEvent.Type.Wheel and self._ignore_activating_mouse_click and not self._parent_currently_activated:
                        
                        if event.type() == QC.QEvent.Type.MouseButtonRelease and self._activating_wait_job is not None:
                            
                            # first completed click in the time window sets us active instantly
                            self._activating_wait_job.Cancel()
                            
                            self._parent_currently_activated = True
                            
                        
                        return False
                        
                    
                    if event.type() == QC.QEvent.Type.MouseButtonRelease:
                        
                        event = typing.cast( QG.QMouseEvent, event )
                        
                        release_press_pos = event.globalPosition().toPoint()
                        
                        delta = release_press_pos - self._last_click_down_position
                        
                        approx_distance = delta.manhattanLength() + CUMULATIVE_MOUSEWARP_MANHATTAN_LENGTH
                        
                        # if mouse release is some distance from mouse down (i.e. we are ending a drag), then don't fire off a release command
                        
                        if approx_distance > 20:
                            
                            return False
                            
                        
                    
                    i_should_catch_shortcut_event = IShouldCatchShortcutEvent( self._filter_target, watched, event = event )
                    
                    shortcut = ConvertMouseEventToShortcut( event )
                    
                    if shortcut is not None:
                        
                        if HG.shortcut_report_mode:
                            
                            message = 'Mouse Press shortcut "' + shortcut.ToString() + '" passing through ' + repr( self._parent ) + '.'
                            
                            if i_should_catch_shortcut_event:
                                
                                message += ' I am in a state to catch it.'
                                
                            else:
                                
                                message += ' I am not in a state to catch it.'
                                
                            
                            HydrusData.ShowText( message )
                            
                        
                        if i_should_catch_shortcut_event:
                            
                            shortcut_processed = self._ProcessShortcut( shortcut )
                            
                            if shortcut_processed:
                                
                                event.accept()
                                
                                return True
                                
                            
                        
                    
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
    def AddShortcuts( self, shortcut_set_name ):
        
        if shortcut_set_name not in self._shortcuts_names:
            
            reserved_names = [ name for name in self._shortcuts_names if name in SHORTCUTS_RESERVED_NAMES ]
            custom_names = [ name for name in self._shortcuts_names if name not in SHORTCUTS_RESERVED_NAMES ]
            
            if shortcut_set_name in SHORTCUTS_RESERVED_NAMES:
                
                reserved_names.append( shortcut_set_name )
                
            else:
                
                custom_names.append( shortcut_set_name )
                
            
            self._shortcuts_names = reserved_names + custom_names
            
        
    
    def FlipShortcuts( self, shortcut_set_name ):
        
        if shortcut_set_name in self._shortcuts_names:
            
            self.RemoveShortcuts( shortcut_set_name )
            
        else:
            
            self.AddShortcuts( shortcut_set_name )
            
        
    
    def FrameActivated( self ):
        
        def do_it():
            
            self._parent_currently_activated = True
            
        
        self._activating_wait_job = CG.client_controller.CallLater( 0.2, do_it )
        
    
    def FrameDeactivated( self ):
        
        if self._activating_wait_job is not None:
            
            self._activating_wait_job.Cancel()
            
        
        self._parent_currently_activated = False
        
    
    def GetCustomShortcutNames( self ):
        
        custom_names = sorted( ( name for name in self._shortcuts_names if name not in SHORTCUTS_RESERVED_NAMES ) )
        
        return custom_names
        
    
    def GetShortcutNames( self ):
        
        return list( self._shortcuts_names )
        
    
    def HasShortcuts( self, shortcut_set_name ):
        
        return shortcut_set_name in self._shortcuts_names
        
    
    def ProcessShortcut( self, shortcut ):
        
        return self._ProcessShortcut( shortcut )
        
    
    def RemoveShortcuts( self, shortcut_set_name ):
        
        if shortcut_set_name in self._shortcuts_names:
            
            self._shortcuts_names.remove( shortcut_set_name )
            
        
    
    def SetShortcuts( self, shortcut_set_names ):
        
        self._shortcuts_names = list( shortcut_set_names )
        
    

class ShortcutsDeactivationCatcher( QC.QObject ):
    
    def __init__( self, shortcuts_handler: ShortcutsHandler, widget: QW.QWidget ):
        
        super().__init__( shortcuts_handler )
        
        self._shortcuts_handler = shortcuts_handler
        
        widget.window().installEventFilter( self )
        
    
    def eventFilter( self, watched, event ):
        
        try:
            
            if event.type() == QC.QEvent.Type.WindowActivate:
                
                self._shortcuts_handler.FrameActivated()
                
            elif event.type() == QC.QEvent.Type.WindowDeactivate:
                
                self._shortcuts_handler.FrameDeactivated()
                
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            return True
            
        
        return False
        
    
class ShortcutsManager( QC.QObject ):
    
    shortcutsChanged = QC.Signal()
    
    my_instance = None
    
    def __init__( self, shortcut_sets = None ):
        
        parent = CGC.core()
        
        super().__init__( parent )
        
        self._names_to_shortcut_sets = {}
        
        if shortcut_sets is not None:
            
            self.SetShortcutSets( shortcut_sets )
            
        
        ShortcutsManager.my_instance = self
        
    
    @staticmethod
    def instance() -> 'ShortcutsManager':
        
        if ShortcutsManager.my_instance is None:
            
            raise Exception( 'ShortcutsManager is not yet initialised!' )
            
        else:
            
            return ShortcutsManager.my_instance
            
        
    
    def GetCommand( self, shortcuts_names: collections.abc.Iterable[ str ], shortcut: Shortcut ):
        
        # process more specific shortcuts with higher priority
        shortcuts_names = list( shortcuts_names )
        shortcuts_names.reverse()
        
        for name in shortcuts_names:
            
            if name in self._names_to_shortcut_sets:
                
                command = self._names_to_shortcut_sets[ name ].GetCommand( shortcut )
                
                if command is not None:
                    
                    if HG.shortcut_report_mode:
                        
                        HydrusData.ShowText( 'Shortcut "{}" matched on "{}" set to "{}" command.'.format( shortcut.ToString(), name, repr( command ) ) )
                        
                    
                    return command
                    
                
            
        
        return None
        
    
    def GetNamesToShortcuts( self, simple_command: int ):
        
        names_to_shortcuts = {}
        
        for ( name, shortcut_set ) in self._names_to_shortcut_sets.items():
            
            shortcuts = shortcut_set.GetShortcuts( simple_command )
            
            if len( shortcuts ) > 0:
                
                names_to_shortcuts[ name ] = shortcuts
                
            
        
        return names_to_shortcuts
        
    
    def GetShortcutSets( self ) -> list[ ShortcutSet ]:
        
        return list( self._names_to_shortcut_sets.values() )
        
    
    def SetShortcutSets( self, shortcut_sets: collections.abc.Iterable[ ShortcutSet ] ):
        
        self._names_to_shortcut_sets = { shortcut_set.GetName() : shortcut_set for shortcut_set in shortcut_sets }
        
        self.shortcutsChanged.emit()
        
    
shortcuts_manager = ShortcutsManager.instance

def shortcuts_manager_initialised():
    
    return ShortcutsManager.my_instance is not None
    
