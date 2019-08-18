from . import ClientConstants as CC
from . import ClientData
from . import ClientGUICommon
from . import ClientGUIFunctions
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusSerialisable
import wx

FLASHWIN_OK = False

if HC.PLATFORM_WINDOWS:
    
    try:
        
        import wx.lib.flashwin
        
        FLASHWIN_OK = True
        
    except Exception as e:
        
        pass
        
    
def ConvertKeyEventToShortcut( event ):
    
    key = event.KeyCode
    
    if ClientData.OrdIsSensibleASCII( key ) or key in list(CC.wxk_code_string_lookup.keys()):
        
        modifiers = []
        
        if event.AltDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_ALT )
            
        
        if event.CmdDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_CTRL )
            
        
        if event.ShiftDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_SHIFT )
            
        
        shortcut = Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, key, modifiers )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'key event caught: ' + repr( shortcut ) )
            
        
        return shortcut
        
    
    return None
    
def ConvertKeyEventToSimpleTuple( event ):
    
    modifier = wx.ACCEL_NORMAL
    
    if event.AltDown(): modifier = wx.ACCEL_ALT
    elif event.CmdDown(): modifier = wx.ACCEL_CTRL
    elif event.ShiftDown(): modifier = wx.ACCEL_SHIFT
    
    key = event.KeyCode
    
    return ( modifier, key )
    
def ConvertMouseEventToShortcut( event ):
    
    key = None
    
    if event.LeftDown() or event.LeftDClick():
        
        key = CC.SHORTCUT_MOUSE_LEFT
        
    elif event.MiddleDown() or event.MiddleDClick():
        
        key = CC.SHORTCUT_MOUSE_MIDDLE
        
    elif event.RightDown() or event.RightDClick():
        
        key = CC.SHORTCUT_MOUSE_RIGHT
        
    elif event.GetWheelRotation() > 0:
        
        key = CC.SHORTCUT_MOUSE_SCROLL_UP
        
    elif event.GetWheelRotation() < 0:
        
        key = CC.SHORTCUT_MOUSE_SCROLL_DOWN
        
    
    if key is not None:
        
        modifiers = []
        
        if event.AltDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_ALT )
            
        
        if event.CmdDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_CTRL )
            
        
        if event.ShiftDown():
            
            modifiers.append( CC.SHORTCUT_MODIFIER_SHIFT )
            
        
        shortcut = Shortcut( CC.SHORTCUT_TYPE_MOUSE, key, modifiers )
        
        if HG.gui_report_mode:
            
            HydrusData.ShowText( 'mouse event caught: ' + repr( shortcut ) )
            
        
        return shortcut
        
    
    return None
    
def IShouldCatchShortcutEvent( evt_handler, event = None, child_tlp_classes_who_can_pass_up = None ):
    
    if HC.PLATFORM_WINDOWS and FLASHWIN_OK:
        
        window = wx.FindWindowAtPointer()
        
        if window is not None and isinstance( window, wx.lib.flashwin.FlashWindow ):
            
            return False
            
        
    
    do_focus_test = True
    
    if event is not None and isinstance( event, wx.MouseEvent ):
        
        if event.GetEventType() == wx.wxEVT_MOUSEWHEEL:
            
            do_focus_test = False
            
        
    
    if do_focus_test:
        
        if not ClientGUIFunctions.WindowOrSameTLPChildHasFocus( evt_handler ):
            
            if child_tlp_classes_who_can_pass_up is not None:
                
                child_tlp_has_focus = ClientGUIFunctions.WindowOrAnyTLPChildHasFocus( evt_handler ) and isinstance( ClientGUIFunctions.GetFocusTLP(), child_tlp_classes_who_can_pass_up )
                
                if not child_tlp_has_focus:
                    
                    return False
                    
                
            else:
                
                return False
                
            
        
    
    return True
    
class Shortcut( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT
    SERIALISABLE_NAME = 'Shortcut'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, shortcut_type = None, shortcut_key = None, modifiers = None ):
        
        if shortcut_type is None:
            
            shortcut_type = CC.SHORTCUT_TYPE_KEYBOARD
            
        
        if shortcut_key is None:
            
            shortcut_key = wx.WXK_F7
            
        
        if modifiers is None:
            
            modifiers = []
            
        
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
            
        
        if self._shortcut_type == CC.SHORTCUT_TYPE_KEYBOARD:
            
            if self._shortcut_key in CC.wxk_code_string_lookup:
                
                components.append( CC.wxk_code_string_lookup[ self._shortcut_key ] )
                
            elif ClientData.OrdIsAlphaUpper( self._shortcut_key ):
                
                components.append( chr( self._shortcut_key + 32 ) ) # + 32 for converting ascii A -> a
                
            elif ClientData.OrdIsSensibleASCII( self._shortcut_key ):
                
                components.append( chr( self._shortcut_key ) )
                
            else:
                
                components.append( 'unknown key' )
                
            
        elif self._shortcut_type == CC.SHORTCUT_TYPE_MOUSE:
            
            components.append( CC.shortcut_mouse_string_lookup[ self._shortcut_key ] )
            
        
        return '+'.join( components )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT ] = Shortcut

class ShortcutPanel( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._mouse_radio = wx.RadioButton( self, style = wx.RB_GROUP, label = 'mouse' )
        self._mouse_shortcut = ShortcutMouse( self, self._mouse_radio )
        
        self._keyboard_radio = wx.RadioButton( self, label = 'keyboard' )
        self._keyboard_shortcut = ShortcutKeyboard( self, self._keyboard_radio )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( ClientGUICommon.BetterStaticText( self, 'Mouse events only work for the duplicate and archive/delete filters atm!' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        gridbox = wx.FlexGridSizer( 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        gridbox.Add( self._mouse_radio, CC.FLAGS_VCENTER )
        gridbox.Add( self._mouse_shortcut, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._keyboard_radio, CC.FLAGS_VCENTER )
        gridbox.Add( self._keyboard_shortcut, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox.Add( gridbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def GetValue( self ):
        
        if self._mouse_radio.GetValue() == True:
            
            return self._mouse_shortcut.GetValue()
            
        else:
            
            return self._keyboard_shortcut.GetValue()
            
        
    
    def SetValue( self, shortcut ):
        
        if shortcut.GetShortcutType() == CC.SHORTCUT_TYPE_MOUSE:
            
            self._mouse_radio.SetValue( True )
            self._mouse_shortcut.SetValue( shortcut )
            
        else:
            
            self._keyboard_radio.SetValue( True )
            self._keyboard_shortcut.SetValue( shortcut )
            
        
    
class ShortcutKeyboard( wx.TextCtrl ):
    
    def __init__( self, parent, related_radio = None ):
        
        self._shortcut = Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, wx.WXK_F7, [] )
        
        self._related_radio = related_radio
        
        wx.TextCtrl.__init__( self, parent, style = wx.TE_PROCESS_ENTER )
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._SetShortcutString()
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString()
        
        wx.TextCtrl.SetValue( self, display_string )
        
    
    def EventKeyDown( self, event ):
        
        shortcut = ConvertKeyEventToShortcut( event )
        
        if shortcut is not None:
            
            self._shortcut = shortcut
            
            if self._related_radio is not None:
                
                self._related_radio.SetValue( True )
                
            
            self._SetShortcutString()
            
        
    
    def GetValue( self ):
        
        return self._shortcut
        
    
    def SetValue( self, shortcut ):
        
        self._shortcut = shortcut
        
        self._SetShortcutString()
        
    
class ShortcutMouse( wx.Button ):
    
    def __init__( self, parent, related_radio = None ):
        
        self._shortcut = Shortcut( CC.SHORTCUT_TYPE_MOUSE, CC.SHORTCUT_MOUSE_LEFT, [] )
        
        self._related_radio = related_radio
        
        wx.Button.__init__( self, parent )
        
        self.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse )
        
        self._SetShortcutString()
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString()
        
        self.SetLabel( display_string )
        
    
    def EventMouse( self, event ):
        
        self.SetFocus()
        
        shortcut = ConvertMouseEventToShortcut( event )
        
        if shortcut is not None:
            
            self._shortcut = shortcut
            
            if self._related_radio is not None:
                
                self._related_radio.SetValue( True )
                
            
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
                
                if modifier not in CC.shortcut_wx_to_hydrus_lookup:
                    
                    modifiers = []
                    
                else:
                    
                    modifiers = [ CC.shortcut_wx_to_hydrus_lookup[ modifier ] ]
                    
                
                shortcut = Shortcut( CC.SHORTCUT_TYPE_KEYBOARD, key, modifiers )
                
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

class ShortcutsHandler( object ):
    
    def __init__( self, parent, initial_shortcuts_names = None ):
        
        if initial_shortcuts_names is None:
            
            initial_shortcuts_names = []
            
        
        self._parent = parent
        self._shortcuts_names = list( initial_shortcuts_names )
        
        self._parent.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        #self._parent.Bind( wx.EVT_MOUSE_EVENTS, self.EventMouse ) # let's not mess with this until we are doing something clever with it
        
    
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
        
    
    def EventCharHook( self, event ):
        
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
                    
                    return
                    
                
            
        
        event.Skip()
        
    
    def EventMouse( self, event ):
        
        shortcut = ConvertMouseEventToShortcut( event )
        
        if shortcut is not None:
            
            shortcut_processed = self._ProcessShortcut( shortcut )
            
            if shortcut_processed:
                
                return
                
            
        
        event.Skip()
        
    
    def AddShortcuts( self, shortcuts_name ):
        
        if shortcuts_name not in self._shortcuts_names:
            
            self._shortcuts_names.append( shortcuts_name )
            
        
    
    def RemoveShortcuts( self, shortcuts_name ):
        
        if shortcuts_name in self._shortcuts_names:
            
            self._shortcuts_names.remove( shortcuts_name )
            
        
    
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
        
    
