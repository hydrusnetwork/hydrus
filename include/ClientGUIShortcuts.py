from . import ClientConstants as CC
from . import ClientData
from . import ClientGUIFunctions
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusSerialisable
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

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

SHORTCUTS_RESERVED_NAMES = [ 'global', 'archive_delete_filter', 'duplicate_filter', 'media', 'main_gui', 'media_viewer_browser', 'media_viewer', 'media_viewer_media_window', 'preview_media_window' ]

SHORTCUTS_GLOBAL_ACTIONS = [ 'global_audio_mute', 'global_audio_unmute', 'global_audio_mute_flip', 'exit_application', 'exit_application_force_maintenance', 'restart_application' ]
SHORTCUTS_MEDIA_ACTIONS = [ 'manage_file_tags', 'manage_file_ratings', 'manage_file_urls', 'manage_file_notes', 'archive_file', 'inbox_file', 'delete_file', 'export_files', 'export_files_quick_auto_export', 'remove_file_from_view', 'open_file_in_external_program', 'open_selection_in_new_page', 'launch_the_archive_delete_filter', 'copy_bmp', 'copy_file', 'copy_path', 'copy_sha256_hash', 'get_similar_to_exact', 'get_similar_to_very_similar', 'get_similar_to_similar', 'get_similar_to_speculative', 'duplicate_media_set_alternate', 'duplicate_media_set_alternate_collections', 'duplicate_media_set_custom', 'duplicate_media_set_focused_better', 'duplicate_media_set_focused_king', 'duplicate_media_set_same_quality', 'open_known_url' ]
SHORTCUTS_MEDIA_VIEWER_ACTIONS = [ 'pause_media', 'pause_play_media', 'move_animation_to_previous_frame', 'move_animation_to_next_frame', 'switch_between_fullscreen_borderless_and_regular_framed_window', 'pan_up', 'pan_down', 'pan_left', 'pan_right', 'pan_top_edge', 'pan_bottom_edge', 'pan_left_edge', 'pan_right_edge', 'pan_vertical_center', 'pan_horizontal_center', 'zoom_in', 'zoom_out', 'switch_between_100_percent_and_canvas_zoom', 'flip_darkmode', 'close_media_viewer' ]
SHORTCUTS_MEDIA_VIEWER_BROWSER_ACTIONS = [ 'view_next', 'view_first', 'view_last', 'view_previous', 'pause_play_slideshow', 'show_menu', 'close_media_viewer' ]
SHORTCUTS_MAIN_GUI_ACTIONS = [ 'refresh', 'refresh_all_pages', 'refresh_page_of_pages_pages', 'new_page', 'new_page_of_pages', 'new_duplicate_filter_page', 'new_gallery_downloader_page', 'new_url_downloader_page', 'new_simple_downloader_page', 'new_watcher_downloader_page', 'synchronised_wait_switch', 'set_media_focus', 'paste_image_data', 'show_hide_splitters', 'set_search_focus', 'unclose_page', 'close_page', 'redo', 'undo', 'flip_darkmode', 'check_all_import_folders', 'flip_debug_force_idle_mode_do_not_set_this', 'show_and_focus_manage_tags_favourite_tags', 'show_and_focus_manage_tags_related_tags', 'show_and_focus_manage_tags_file_lookup_script_tags', 'show_and_focus_manage_tags_recent_tags', 'focus_media_viewer' ]
SHORTCUTS_DUPLICATE_FILTER_ACTIONS = [ 'duplicate_filter_this_is_better_and_delete_other', 'duplicate_filter_this_is_better_but_keep_both', 'duplicate_filter_exactly_the_same', 'duplicate_filter_alternates', 'duplicate_filter_false_positive', 'duplicate_filter_custom_action', 'duplicate_filter_skip', 'duplicate_filter_back', 'close_media_viewer' ]
SHORTCUTS_ARCHIVE_DELETE_FILTER_ACTIONS = [ 'archive_delete_filter_keep', 'archive_delete_filter_delete', 'archive_delete_filter_skip', 'archive_delete_filter_back', 'close_media_viewer' ]
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

# ok, the problem here is that I get key codes that are converted, so if someone does shift+1 on a US keyboard, this ends up with Shift+! same with ctrl+alt+ to get accented characters
# it isn't really a big deal since everything still lines up, but the QGuiApplicationPrivate::platformIntegration()->possibleKeys(e) to get some variant of 'yeah this is just !' seems unavailable for python
# it is basically a display bug, but it'd be nice to have it working right
def ConvertQtKeyToShortcutKey( key_qt ):
    
    if key_qt in special_key_shortcut_enum_lookup:
        
        key_ord = special_key_shortcut_enum_lookup[ key_qt ]
        
        return ( SHORTCUT_TYPE_KEYBOARD_SPECIAL, key_ord )
        
    else:
        
        try:
            
            key_ord = int( key_qt )
            
            key_chr = chr( key_ord )
            
            # this is turbo lower() that converts Scharfes S (beta) to 'ss'
            key_chr = key_chr.casefold()[0]
            
            casefold_key_ord = ord( key_chr )
            
            return ( SHORTCUT_TYPE_KEYBOARD_CHARACTER, casefold_key_ord )
            
        except:
            
            return ( SHORTCUT_TYPE_NOT_ALLOWED, key_ord )
            
        
    
def ConvertKeyEventToShortcut( event ):
    
    key_qt = event.key()
    
    ( shortcut_type, key_ord ) = ConvertQtKeyToShortcutKey( key_qt )
    
    if shortcut_type != SHORTCUT_TYPE_NOT_ALLOWED:
        
        modifiers = []
        
        if event.modifiers() & QC.Qt.AltModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_ALT )
            
        
        if HC.PLATFORM_MACOS:
            
            ctrl = QC.Qt.MetaModifier
            
        else:
            
            ctrl = QC.Qt.ControlModifier
            
        
        if event.modifiers() & ctrl:
            
            modifiers.append( SHORTCUT_MODIFIER_CTRL )
            
        
        if event.modifiers() & QC.Qt.ShiftModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_SHIFT )
            
        
        if event.modifiers() & QC.Qt.GroupSwitchModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_GROUP_SWITCH )
            
        
        if event.modifiers() & QC.Qt.KeypadModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_KEYPAD )
            
        
        shortcut_press_type = SHORTCUT_PRESS_TYPE_PRESS
        
        shortcut = Shortcut( shortcut_type, key_ord, shortcut_press_type, modifiers )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'key event caught: ' + repr( shortcut ) )
            
        
        return shortcut
        
    
    return None
    
def ConvertKeyEventToSimpleTuple( event ):
    
    modifier = QC.Qt.NoModifier
    
    if event.modifiers() & QC.Qt.AltModifier: modifier = QC.Qt.AltModifier
    elif event.modifiers() & QC.Qt.ControlModifier: modifier = QC.Qt.ControlModifier
    elif event.modifiers() & QC.Qt.ShiftModifier: modifier = QC.Qt.ShiftModifier
    elif event.modifiers() & QC.Qt.KeypadModifier: modifier = QC.Qt.KeypadModifier
    elif event.modifiers() & QC.Qt.GroupSwitchModifier: modifier = QC.Qt.GroupSwitchModifier
    
    key = event.key()
    
    return ( modifier, key )
    
def ConvertMouseEventToShortcut( event ):
    
    key = None
    
    shortcut_press_type = SHORTCUT_PRESS_TYPE_PRESS
    
    if event.type() == QC.QEvent.MouseButtonPress:
        
        if event.buttons() & QC.Qt.LeftButton:
            
            key = SHORTCUT_MOUSE_LEFT
            
        elif event.buttons() & QC.Qt.MiddleButton:
            
            key = SHORTCUT_MOUSE_MIDDLE
            
        elif event.buttons() & QC.Qt.RightButton:
            
            key = SHORTCUT_MOUSE_RIGHT
            
        
    elif event.type() in ( QC.QEvent.MouseButtonDblClick, QC.QEvent.MouseButtonRelease ):
        
        if event.type() == QC.QEvent.MouseButtonRelease:
            
            shortcut_press_type = SHORTCUT_PRESS_TYPE_RELEASE
            
        elif event.type() == QC.QEvent.MouseButtonDblClick:
            
            shortcut_press_type = SHORTCUT_PRESS_TYPE_DOUBLE_CLICK
            
        
        if event.button() == QC.Qt.LeftButton:
            
            key = SHORTCUT_MOUSE_LEFT
            
        elif event.button() == QC.Qt.MiddleButton:
            
            key = SHORTCUT_MOUSE_MIDDLE
            
        elif event.button() == QC.Qt.RightButton:
            
            key = SHORTCUT_MOUSE_RIGHT
            
        
    elif event.type() == QC.QEvent.Wheel:
        
        if event.angleDelta().y() > 0:
            
            key = SHORTCUT_MOUSE_SCROLL_UP
            
        elif event.angleDelta().y() < 0:
            
            key = SHORTCUT_MOUSE_SCROLL_DOWN
            
        
    
    if key is not None:
        
        modifiers = []
        
        if event.modifiers() & QC.Qt.AltModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_ALT )
            
        
        if event.modifiers() & QC.Qt.ControlModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_CTRL )
            
        
        if event.modifiers() & QC.Qt.ShiftModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_SHIFT )
            
        
        if event.modifiers() & QC.Qt.GroupSwitchModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_GROUP_SWITCH )
            
        
        if event.modifiers() & QC.Qt.KeypadModifier:
            
            modifiers.append( SHORTCUT_MODIFIER_KEYPAD )
            
        
        shortcut = Shortcut( SHORTCUT_TYPE_MOUSE, key, shortcut_press_type, modifiers )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'mouse event caught: ' + repr( shortcut ) )
            
        
        return shortcut
        
    
    return None
    
def AncestorShortcutsHandlers( widget: QW.QWidget ):
    
    shortcuts_handlers = []
    
    window = widget.window()
    
    if window == widget:
        
        return shortcuts_handlers
        
    
    widget = widget.parent()
    
    while True:
        
        child_shortcuts_handlers = [ child for child in widget.children() if isinstance( child, ShortcutsHandler ) ]
        
        shortcuts_handlers.extend( child_shortcuts_handlers )
        
        if widget == window:
            
            break
            
        
        widget = widget.parent()
        
        if widget is None:
            
            break
            
        
    
    return shortcuts_handlers
    
def IShouldCatchShortcutEvent( evt_handler, event = None, child_tlw_classes_who_can_pass_up = None ):
    
    do_focus_test = True
    
    if event is not None and isinstance( event, QG.QWheelEvent ):
        
        do_focus_test = False
        
        
    
    if do_focus_test:
        
        if not ClientGUIFunctions.TLWIsActive( evt_handler ):
            
            if child_tlw_classes_who_can_pass_up is not None:
                
                child_tlw_has_focus = ClientGUIFunctions.WidgetOrAnyTLWChildHasFocus( evt_handler ) and isinstance( QW.QApplication.activeWindow(), child_tlw_classes_who_can_pass_up )
                
                if not child_tlw_has_focus:
                    
                    return False
                    
                
            else:
                
                return False
                
            
        
    
    return True
    
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
            
        
        modifiers.sort()
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
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
        
    
    def GetShortcutType( self ):
        
        return self.shortcut_type
        
    
    def IsDoubleClick( self ):
        
        return self.shortcut_type == SHORTCUT_TYPE_MOUSE and self.shortcut_press_type == SHORTCUT_PRESS_TYPE_DOUBLE_CLICK
        
    
    def ToString( self ):
        
        components = []
        
        if SHORTCUT_MODIFIER_CTRL in self.modifiers:
            
            components.append( 'ctrl' )
            
        
        if SHORTCUT_MODIFIER_ALT in self.modifiers:
            
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
            
            action_name += shortcut_mouse_string_lookup[ self.shortcut_key ]
            
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
            
        
        components.append( action_name )
        
        s = '+'.join( components )
        
        if SHORTCUT_MODIFIER_KEYPAD in self.modifiers:
            
            s += ' (on numpad)'
            
        
        return s
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT ] = Shortcut

class ShortcutSet( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET
    SERIALISABLE_NAME = 'Shortcut Set'
    SERIALISABLE_VERSION = 2
    
    def __init__( self, name ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
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
            
            services_manager = HG.client_controller.services_manager
            
            for ( modifier, key, ( serialisable_service_key, data ) ) in serialisable_keyboard_actions:
                
                # no longer updating modifier, as that was wx legacy
                
                modifiers = []
                
                shortcut = Shortcut( SHORTCUT_TYPE_KEYBOARD_CHARACTER, key, SHORTCUT_PRESS_TYPE_PRESS, modifiers )
                
                if serialisable_service_key is None:
                    
                    command = ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, data )
                    
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
                        
                    
                    command = ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, content_type, action, value ) )
                    
                
                shortcuts_to_commands[ shortcut ] = command
                
            
            new_serialisable_info = ( ( shortcut.GetSerialisableTuple(), command.GetSerialisableTuple() ) for ( shortcut, command ) in list(shortcuts_to_commands.items()) )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetCommand( self, shortcut ):
        
        if shortcut in self._shortcuts_to_commands:
            
            return self._shortcuts_to_commands[ shortcut ]
            
        else:
            
            return None
            
        
    
    def GetShortcuts( self, simple_command ):
        
        shortcuts = []
        
        for ( shortcut, command ) in self._shortcuts_to_commands.items():
            
            if command.GetCommandType() == CC.APPLICATION_COMMAND_TYPE_SIMPLE and command.GetData() == simple_command:
                
                shortcuts.append( shortcut )
                
            
        
        return shortcuts
        
    
    def SetCommand( self, shortcut, command ):
        
        self._shortcuts_to_commands[ shortcut ] = command
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET ] = ShortcutSet

class ShortcutsHandler( QC.QObject ):
    
    def __init__( self, parent: QW.QWidget, initial_shortcuts_names = None, catch_mouse = False, ignore_activating_mouse_click = False ):
        
        QC.QObject.__init__( self, parent )
        
        self._catch_mouse = catch_mouse
        
        if initial_shortcuts_names is None:
            
            initial_shortcuts_names = []
            
        
        self._parent = parent
        self._parent.installEventFilter( self )
        self._shortcuts_names = list( initial_shortcuts_names )
        
        self._ignore_activating_mouse_click = ignore_activating_mouse_click
        
        self._frame_activated_time = 0.0
        
        if self._catch_mouse and self._ignore_activating_mouse_click:
            
            self._deactivation_catcher = ShortcutsDeactivationCatcher( self, parent )
            
        
    
    def _ProcessShortcut( self, shortcut: Shortcut ):
        
        shortcut_processed = False
        
        command = HG.client_controller.shortcuts_manager.GetCommand( self._shortcuts_names, shortcut )
        
        if command is None and shortcut.IsDoubleClick():
            
            # ok, so user double-clicked
            # if a parent wants to catch this (for instance the media viewer when we double-click a video), then we want that parent to have it
            # but if no parent wants it, we can try converting it to a single-click to see if that does anything
            
            ancestor_shortcuts_handlers = AncestorShortcutsHandlers( self._parent )
            
            all_ancestor_shortcut_names = HydrusData.MassUnion( [ ancestor_shortcuts_handler.GetShortcutNames() for ancestor_shortcuts_handler in ancestor_shortcuts_handlers ] )
            
            ancestor_command = HG.client_controller.shortcuts_manager.GetCommand( all_ancestor_shortcut_names, shortcut )
            
            if ancestor_command is None:
                
                if HG.shortcut_report_mode:
                    
                    message = 'Shortcut "' + shortcut.ToString() + '" did not match any command. The single click version is now being attempted.'
                    
                    HydrusData.ShowText( message )
                    
                
                shortcut = shortcut.ConvertToSingleClick()
                
                command = HG.client_controller.shortcuts_manager.GetCommand( self._shortcuts_names, shortcut )
                
            else:
                
                if HG.shortcut_report_mode:
                    
                    message = 'Shortcut "' + shortcut.ToString() + '" did not match any command. A parent seems to want it, however, so the single click version will not be attempted.'
                    
                    HydrusData.ShowText( message )
                    
                
            
        
        if command is not None:
            
            command_processed = self._parent.ProcessApplicationCommand( command )
            
            if command_processed:
                
                shortcut_processed = True
                
            
            if HG.shortcut_report_mode:
                
                message = 'Shortcut "' + shortcut.ToString() + '" matched to command "' + command.ToString() + '" on ' + repr( self._parent ) + '.'
                
                if command_processed:
                    
                    message += ' It was processed.'
                    
                else:
                    
                    message += ' It was not processed.'
                    
                
                HydrusData.ShowText( message )
                
            
        
        return shortcut_processed
        
    
    def eventFilter( self, watched, event ):
        
        if event.type() == QC.QEvent.KeyPress:
            
            i_should_catch_shortcut_event = IShouldCatchShortcutEvent( self._parent, event = event )
            
            shortcut = ConvertKeyEventToShortcut( event )
            
            if shortcut is not None:
                
                if HG.shortcut_report_mode:
                    
                    message = 'Key shortcut "' + shortcut.ToString() + '" passing through ' + repr( self._parent ) + '.'
                    
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
            
            if event.type() in ( QC.QEvent.MouseButtonPress, QC.QEvent.MouseButtonRelease, QC.QEvent.MouseButtonDblClick, QC.QEvent.Wheel ):
                
                if event.type() != QC.QEvent.Wheel and self._ignore_activating_mouse_click and not HydrusData.TimeHasPassedPrecise( self._frame_activated_time + 0.1 ):
                    
                    if event.type() == QC.QEvent.MouseButtonRelease:
                        
                        self._frame_activated_time = 0.0
                        
                    
                    return False
                    
                
                i_should_catch_shortcut_event = IShouldCatchShortcutEvent( self._parent, event = event )
                
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
            
        
    
    def GetCustomShortcutNames( self ):
        
        custom_names = [ name for name in self._shortcuts_names if name not in SHORTCUTS_RESERVED_NAMES ]
        
        custom_names.sort()
        
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
        
    
    def FrameActivated( self ):
        
        self._frame_activated_time = HydrusData.GetNowPrecise()
        
    
class ShortcutsDeactivationCatcher( QC.QObject ):
    
    def __init__( self, shortcuts_handler: ShortcutsHandler, widget: QW.QWidget ):
        
        QC.QObject.__init__( self, shortcuts_handler )
        
        self._shortcuts_handler = shortcuts_handler
        
        widget.window().installEventFilter( self )
        
    
    def eventFilter( self, watched, event ):
        
        if event.type() == QC.QEvent.WindowActivate:
            
            self._shortcuts_handler.FrameActivated()
            
        
        return False
        
    
class ShortcutsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._shortcuts = {}
        
        self._RefreshShortcuts()
        
        self._controller.sub( self, 'RefreshShortcuts', 'notify_new_shortcuts_data' )
        
    
    def _RefreshShortcuts( self ):
        
        self._shortcuts = {}
        
        all_shortcuts = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
        
        for shortcuts in all_shortcuts:
            
            self._shortcuts[ shortcuts.GetName() ] = shortcuts
            
        
    
    def GetCommand( self, shortcuts_names, shortcut ):
        
        # process more specific shortcuts with higher priority
        shortcuts_names = list( shortcuts_names )
        shortcuts_names.reverse()
        
        for name in shortcuts_names:
            
            if name in self._shortcuts:
                
                command = self._shortcuts[ name ].GetCommand( shortcut )
                
                if command is not None:
                    
                    if HG.shortcut_report_mode:
                        
                        HydrusData.ShowText( 'Shortcut "{}" matched on "{}" set to "{}" command.'.format( shortcut.ToString(), name, repr( command ) ) )
                        
                    
                    return command
                    
                
            
        
        return None
        
    
    def GetNamesToShortcuts( self, simple_command ):
        
        names_to_shortcuts = {}
        
        for ( name, shortcut_set ) in self._shortcuts.items():
            
            shortcuts = shortcut_set.GetShortcuts( simple_command )
            
            if len( shortcuts ) > 0:
                
                names_to_shortcuts[ name ] = shortcuts
                
            
        
        return names_to_shortcuts
        
    
    def RefreshShortcuts( self ):
        
        self._RefreshShortcuts()
        
        HG.client_controller.pub( 'notify_new_shortcuts_gui' )
        
    
