from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIFunctions
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusSerialisable
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP

# ok, the problem here is that I get key codes that are converted, so if someone does shift+1 on a US keyboard, this ends up with Shift+! same with ctrl+alt+ to get accented characters
# it isn't really a big deal since everything still lines up, but the QGuiApplicationPrivate::platformIntegration()->possibleKeys(e) to get some variant of 'yeah this is just !' seems unavailable for python
# it is basically a display bug, but it'd be nice to have it working right
def ConvertQtKeyToShortcutKey( key_qt ):
    
    if key_qt in CC.special_key_shortcut_enum_lookup:
        
        key_ord = CC.special_key_shortcut_enum_lookup[ key_qt ]
        
        return ( CC.SHORTCUT_TYPE_KEYBOARD_SPECIAL, key_ord )
        
    else:
        
        try:
            
            key_ord = int( key_qt )
            
            key_chr = chr( key_ord )
            
            # this is turbo lower() that converts Scharfes S (beta) to 'ss'
            key_chr = key_chr.casefold()[0]
            
            casefold_key_ord = ord( key_chr )
            
            return ( CC.SHORTCUT_TYPE_KEYBOARD_CHARACTER, casefold_key_ord )
            
        except:
            
            return ( CC.SHORTCUT_TYPE_NOT_ALLOWED, key_ord )
            
        
    
def ConvertKeyEventToShortcut( event ):
    
    key_qt = event.key()
    
    ( shortcut_type, key_ord ) = ConvertQtKeyToShortcutKey( key_qt )
    
    if shortcut_type != CC.SHORTCUT_TYPE_NOT_ALLOWED:
        
        modifiers = []
        
        if event.modifiers() & QC.Qt.AltModifier:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_ALT )
            
        
        if HC.PLATFORM_MACOS:
            
            ctrl = QC.Qt.MetaModifier
            
        else:
            
            ctrl = QC.Qt.ControlModifier
            
        
        if event.modifiers() & ctrl:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_CTRL )
            
        
        if event.modifiers() & QC.Qt.ShiftModifier:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_SHIFT )
            
        
        if event.modifiers() & QC.Qt.GroupSwitchModifier:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_GROUP_SWITCH )
            
        
        if event.modifiers() & QC.Qt.KeypadModifier:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_KEYPAD )
            
        
        shortcut = Shortcut( shortcut_type, key_ord, modifiers )
        
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
    
    if ( event.type() == QC.QEvent.MouseButtonPress and event.buttons() & QC.Qt.LeftButton ) or ( event.type() == QC.QEvent.MouseButtonDblClick and event.button() == QC.Qt.LeftButton ):
        
        key = CC.SHORTCUT_MOUSE_LEFT
        
    elif ( event.type() == QC.QEvent.MouseButtonPress and event.buttons() & QC.Qt.MiddleButton ) or ( event.type() == QC.QEvent.MouseButtonDblClick and event.button() == QC.Qt.MiddleButton ):
        
        key = CC.SHORTCUT_MOUSE_MIDDLE
        
    elif ( event.type() == QC.QEvent.MouseButtonPress and event.buttons() & QC.Qt.RightButton ) or ( event.type() == QC.QEvent.MouseButtonDblClick and event.button() == QC.Qt.RightButton ):
        
        key = CC.SHORTCUT_MOUSE_RIGHT
        
    elif event.type() == QC.QEvent.Wheel and event.angleDelta().y() > 0:
        
        key = CC.SHORTCUT_MOUSE_SCROLL_UP
        
    elif event.type() == QC.QEvent.Wheel and event.angleDelta().y() < 0:
        
        key = CC.SHORTCUT_MOUSE_SCROLL_DOWN
        
    
    if key is not None:
        
        modifiers = []
        
        if event.modifiers() & QC.Qt.AltModifier:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_ALT )
            
        
        if event.modifiers() & QC.Qt.ControlModifier:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_CTRL )
            
        
        if event.modifiers() & QC.Qt.ShiftModifier:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_SHIFT )
            
        
        if event.modifiers() & QC.Qt.GroupSwitchModifier:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_GROUP_SWITCH )
            
        
        if event.modifiers() & QC.Qt.KeypadModifier:
            
            modifiers.append( CC.SHORTCUT_MODIFIER_KEYPAD )
            
        
        shortcut = Shortcut( CC.SHORTCUT_TYPE_MOUSE, key, modifiers )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'mouse event caught: ' + repr( shortcut ) )
            
        
        return shortcut
        
    
    return None
    
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
    SERIALISABLE_VERSION = 2
    
    def __init__( self, shortcut_type = None, shortcut_key = None, modifiers = None ):
        
        if shortcut_type is None:
            
            shortcut_type = CC.SHORTCUT_TYPE_KEYBOARD_SPECIAL
            
        
        if shortcut_key is None:
            
            shortcut_key = CC.SHORTCUT_KEY_SPECIAL_F7
            
        
        if modifiers is None:
            
            modifiers = []
            
        
        if shortcut_type == CC.SHORTCUT_TYPE_KEYBOARD_CHARACTER and ClientData.OrdIsAlphaUpper( shortcut_key ):
            
            shortcut_key += 32 # convert A to a
            
        
        modifiers.sort()
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._shortcut_type = shortcut_type
        self._shortcut_key = shortcut_key
        self._modifiers = modifiers
        
    
    def __eq__( self, other ):
        
        return self.__hash__() == other.__hash__()
        
    
    def __hash__( self ):
        
        return ( self._shortcut_type, self._shortcut_key, tuple( self._modifiers ) ).__hash__()
        
    
    def __repr__( self ):
        
        return 'Shortcut: ' + self.ToString()
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self._shortcut_type, self._shortcut_key, self._modifiers )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._shortcut_type, self._shortcut_key, self._modifiers ) = serialisable_info
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            # these are dicts that convert fixed wx enums to new stuff
            wx_to_qt_flat_conversion = {
                32 : CC.SHORTCUT_KEY_SPECIAL_SPACE,
                8 : CC.SHORTCUT_KEY_SPECIAL_BACKSPACE,
                9 : CC.SHORTCUT_KEY_SPECIAL_TAB,
                13 : CC.SHORTCUT_KEY_SPECIAL_RETURN,
                310 : CC.SHORTCUT_KEY_SPECIAL_PAUSE,
                27 : CC.SHORTCUT_KEY_SPECIAL_ESCAPE,
                322 : CC.SHORTCUT_KEY_SPECIAL_INSERT,
                127 : CC.SHORTCUT_KEY_SPECIAL_DELETE,
                315 : CC.SHORTCUT_KEY_SPECIAL_UP,
                317 : CC.SHORTCUT_KEY_SPECIAL_DOWN,
                314 : CC.SHORTCUT_KEY_SPECIAL_LEFT,
                316 : CC.SHORTCUT_KEY_SPECIAL_RIGHT,
                313 : CC.SHORTCUT_KEY_SPECIAL_HOME,
                312 : CC.SHORTCUT_KEY_SPECIAL_END,
                367 : CC.SHORTCUT_KEY_SPECIAL_PAGE_DOWN,
                366 : CC.SHORTCUT_KEY_SPECIAL_PAGE_UP,
                340 : CC.SHORTCUT_KEY_SPECIAL_F1,
                341 : CC.SHORTCUT_KEY_SPECIAL_F2,
                342 : CC.SHORTCUT_KEY_SPECIAL_F3,
                343 : CC.SHORTCUT_KEY_SPECIAL_F4,
                344 : CC.SHORTCUT_KEY_SPECIAL_F5,
                345 : CC.SHORTCUT_KEY_SPECIAL_F6,
                346 : CC.SHORTCUT_KEY_SPECIAL_F7,
                347 : CC.SHORTCUT_KEY_SPECIAL_F8,
                348 : CC.SHORTCUT_KEY_SPECIAL_F9,
                349 : CC.SHORTCUT_KEY_SPECIAL_F10,
                350 : CC.SHORTCUT_KEY_SPECIAL_F11,
                351 : CC.SHORTCUT_KEY_SPECIAL_F12
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
                377 : CC.SHORTCUT_KEY_SPECIAL_UP,
                379 : CC.SHORTCUT_KEY_SPECIAL_DOWN,
                376 : CC.SHORTCUT_KEY_SPECIAL_LEFT,
                378 : CC.SHORTCUT_KEY_SPECIAL_RIGHT,
                375 : CC.SHORTCUT_KEY_SPECIAL_HOME,
                382 : CC.SHORTCUT_KEY_SPECIAL_END,
                381 : CC.SHORTCUT_KEY_SPECIAL_PAGE_DOWN,
                380 : CC.SHORTCUT_KEY_SPECIAL_PAGE_UP,
                385 : CC.SHORTCUT_KEY_SPECIAL_DELETE,
                370 : CC.SHORTCUT_KEY_SPECIAL_ENTER
                }
            
            ( shortcut_type, shortcut_key, modifiers ) = old_serialisable_info
            
            if shortcut_type == CC.SHORTCUT_TYPE_KEYBOARD_CHARACTER:
                
                if shortcut_key in wx_to_qt_flat_conversion:
                    
                    shortcut_type = CC.SHORTCUT_TYPE_KEYBOARD_SPECIAL
                    shortcut_key = wx_to_qt_flat_conversion[ shortcut_key ]
                    
                elif shortcut_key in wx_to_qt_numpad_ascii_conversion:
                    
                    shortcut_key = wx_to_qt_numpad_ascii_conversion[ shortcut_key ]
                    
                    modifiers = list( modifiers )
                    
                    modifiers.append( CC.SHORTCUT_MODIFIER_KEYPAD )
                    
                    modifiers.sort()
                    
                elif shortcut_key in wx_to_qt_numpad_conversion:
                    
                    shortcut_type = CC.SHORTCUT_TYPE_KEYBOARD_SPECIAL
                    shortcut_key = wx_to_qt_numpad_conversion[ shortcut_key ]
                    
                    modifiers = list( modifiers )
                    
                    modifiers.append( CC.SHORTCUT_MODIFIER_KEYPAD )
                    
                    modifiers.sort()
                    
                
            
            if shortcut_type == CC.SHORTCUT_TYPE_KEYBOARD_CHARACTER:
                
                if ClientData.OrdIsAlphaUpper( shortcut_key ):
                    
                    shortcut_key += 32 # convert 'A' to 'a'
                    
                
            
            new_serialisable_info = ( shortcut_type, shortcut_key, modifiers )
            
            return ( 2, new_serialisable_info )
            
        
    
    def GetShortcutType( self ):
        
        return self._shortcut_type
        
    
    def ToString( self ):
        
        components = []
        
        if CC.SHORTCUT_MODIFIER_CTRL in self._modifiers:
            
            components.append( 'ctrl' )
            
        
        if CC.SHORTCUT_MODIFIER_ALT in self._modifiers:
            
            components.append( 'alt' )
            
        
        if CC.SHORTCUT_MODIFIER_SHIFT in self._modifiers:
            
            components.append( 'shift' )
            
        
        if CC.SHORTCUT_MODIFIER_GROUP_SWITCH in self._modifiers:
            
            components.append( 'Mode_switch' )
            
        
        if self._shortcut_type == CC.SHORTCUT_TYPE_MOUSE and self._shortcut_key in CC.shortcut_mouse_string_lookup:
            
            components.append( CC.shortcut_mouse_string_lookup[ self._shortcut_key ] )
            
        elif self._shortcut_type == CC.SHORTCUT_TYPE_KEYBOARD_SPECIAL and self._shortcut_key in CC.special_key_shortcut_str_lookup:
            
            components.append( CC.special_key_shortcut_str_lookup[ self._shortcut_key ] )
            
        elif self._shortcut_type == CC.SHORTCUT_TYPE_KEYBOARD_CHARACTER:
            
            try:
                
                if ClientData.OrdIsAlphaUpper( self._shortcut_key ):
                    
                    components.append( chr( self._shortcut_key + 32 ) ) # + 32 for converting ascii A -> a
                    
                else:
                    
                    components.append( chr( self._shortcut_key ) )
                    
                
            except:
                
                components.append( 'unknown key: {}'.format( repr( self._shortcut_key ) ) )
                
            
        else:
            
            components.append( 'unknown key: {}'.format( repr( self._shortcut_key ) ) )
            
        
        s = '+'.join( components )
        
        if CC.SHORTCUT_MODIFIER_KEYPAD in self._modifiers:
            
            s += ' (on numpad)'
            
        
        return s
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT ] = Shortcut

class ShortcutPanel( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._mouse_radio = QW.QRadioButton( 'mouse', self )
        self._mouse_shortcut = ShortcutMouse( self, self._mouse_radio )
        
        self._keyboard_radio = QW.QRadioButton( 'keyboard', self )
        self._keyboard_shortcut = ShortcutKeyboard( self, self._keyboard_radio )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,'Mouse events only work for the duplicate and archive/delete filters atm!'), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        gridbox = QP.GridLayout( cols = 2 )
        
        gridbox.setColumnStretch( 1, 1 )
        
        QP.AddToLayout( gridbox, self._mouse_radio, CC.FLAGS_VCENTER )
        QP.AddToLayout( gridbox, self._mouse_shortcut, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._keyboard_radio, CC.FLAGS_VCENTER )
        QP.AddToLayout( gridbox, self._keyboard_shortcut, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def GetValue( self ):
        
        if self._mouse_radio.isChecked():
            
            return self._mouse_shortcut.GetValue()
            
        else:
            
            return self._keyboard_shortcut.GetValue()
            
        
    
    def SetValue( self, shortcut ):
        
        if shortcut.GetShortcutType() == CC.SHORTCUT_TYPE_MOUSE:
            
            self._mouse_radio.setChecked( True )
            self._mouse_shortcut.SetValue( shortcut )
            
        else:
            
            self._keyboard_radio.setChecked( True )
            self._keyboard_shortcut.SetValue( shortcut )
            
        
    
class ShortcutKeyboard( QW.QLineEdit ):
    
    def __init__( self, parent, related_radio = None ):
        
        self._shortcut = Shortcut()
        
        self._related_radio = related_radio
        
        QW.QLineEdit.__init__( self, parent )
        
        self._SetShortcutString()
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString()
        
        self.setText( display_string )
        
    
    def keyPressEvent( self, event ):
        
        shortcut = ConvertKeyEventToShortcut( event )
        
        if shortcut is not None:
            
            self._shortcut = shortcut
            
            if self._related_radio is not None:
                
                self._related_radio.setChecked( True )
                
            
            self._SetShortcutString()
            
        
    
    def GetValue( self ):
        
        return self._shortcut
        
    
    def SetValue( self, shortcut ):
        
        self._shortcut = shortcut
        
        self._SetShortcutString()
        
    
class ShortcutMouse( QW.QPushButton ):
    
    def __init__( self, parent, related_radio = None ):
        
        self._shortcut = Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_LEFT, [] )
        
        self._related_radio = related_radio
        
        QW.QPushButton.__init__( self, parent )
        
        self._SetShortcutString()
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString()
        
        self.setText( display_string )
        
    
    def mousePressEvent( self, event ):
        
        self.EventMouse( event )
        
    def mouseDoubleClickEvent( self, event ):
        
        self.EventMouse( event )
    
    def EventMouse( self, event ):
        
        self.setFocus( QC.Qt.OtherFocusReason )
        
        shortcut = ConvertMouseEventToShortcut( event )
        
        if shortcut is not None:
            
            self._shortcut = shortcut
            
            if self._related_radio is not None:
                
                self._related_radio.setChecked( True )
                
            
            self._SetShortcutString()
            
        
    
    def GetValue( self ):
        
        return self._shortcut
        
    
    def SetValue( self, shortcut ):
        
        self._shortcut = shortcut
        
        self._SetShortcutString()
        
    

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
                
                shortcut = Shortcut( CC.SHORTCUT_TYPE_KEYBOARD_CHARACTER, key, modifiers )
                
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
                    
                    if service_type in HC.TAG_SERVICES:
                        
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
    
    def __init__( self, parent, initial_shortcuts_names = None ):
        
        QC.QObject.__init__( self, parent )
        
        if initial_shortcuts_names is None:
            
            initial_shortcuts_names = []
            
        
        self._parent = parent
        self._parent.installEventFilter( self )
        self._shortcuts_names = list( initial_shortcuts_names )
        
    
    def _ProcessShortcut( self, shortcut ):
        
        shortcut_processed = False
        
        command = HG.client_controller.GetCommandFromShortcut( self._shortcuts_names, shortcut )
        
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
            
            shortcut = ConvertKeyEventToShortcut( event )
            
            if shortcut is not None:
                
                if HG.shortcut_report_mode:
                    
                    message = 'Key shortcut "' + shortcut.ToString() + '" passing through ' + repr( self._parent ) + '.'
                    
                    if IShouldCatchShortcutEvent( self._parent, event = event ):
                        
                        message += ' I am in a state to catch it.'
                        
                    else:
                        
                        message += ' I am not in a state to catch it.'
                        
                    
                    HydrusData.ShowText( message )
                    
                
                if IShouldCatchShortcutEvent( self._parent, event = event ):
                    
                    shortcut_processed = self._ProcessShortcut( shortcut )
                    
                    if shortcut_processed:
                        
                        return True
                        
                    
                
            
        return False
        
    
    def AddShortcuts( self, shortcut_set_name ):
        
        if shortcut_set_name not in self._shortcuts_names:
            
            self._shortcuts_names.append( shortcut_set_name )
            
        
    
    def RemoveShortcuts( self, shortcut_set_name ):
        
        if shortcut_set_name in self._shortcuts_names:
            
            self._shortcuts_names.remove( shortcut_set_name )
            
        
    
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
        
        for name in shortcuts_names:
            
            if name in self._shortcuts:
                
                command = self._shortcuts[ name ].GetCommand( shortcut )
                
                if command is not None:
                    
                    if HG.gui_report_mode:
                        
                        HydrusData.ShowText( 'command matched: ' + repr( command ) )
                        
                    
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
        
    
