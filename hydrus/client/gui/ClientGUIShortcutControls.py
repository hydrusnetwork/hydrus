import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUIApplicationCommand
from hydrus.client.gui.widgets import ClientGUICommon

class EditShortcutAndCommandPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, shortcut, command, shortcuts_name, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad ):
        
        super().__init__( parent )
        
        #
        
        self._shortcut_panel = ClientGUICommon.StaticBox( self, 'shortcut' )
        
        self._shortcut = ShortcutWidget( self._shortcut_panel, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad )
        
        self._command_panel = ClientGUICommon.StaticBox( self, 'command' )
        
        self._command = ClientGUIApplicationCommand.ApplicationCommandWidget( self._command_panel, command, shortcuts_name )
        
        #
        
        self._shortcut.SetValue( shortcut )
        
        #
        
        self._shortcut_panel.Add( self._shortcut, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._command_panel.Add( self._command, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._shortcut_panel, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, '\u2192' ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._command_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( hbox )
        
    
    def GetValue( self ):
        
        shortcut = self._shortcut.GetValue()
        
        command = self._command.GetValue()
        
        return ( shortcut, command )
        
    

class EditShortcutSetPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, shortcuts: ClientGUIShortcuts.ShortcutSet, call_mouse_buttons_primary_secondary: bool, shortcuts_merge_non_number_numpad: bool ):
        
        super().__init__( parent )
        
        self._name = QW.QLineEdit( self )
        
        self._call_mouse_buttons_primary_secondary = call_mouse_buttons_primary_secondary
        self._shortcuts_merge_non_number_numpad = shortcuts_merge_non_number_numpad
        
        self._shortcuts_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_SHORTCUTS.ID, self._ConvertShortcutTupleToDisplayTuple, self._ConvertShortcutTupleToSortTuple )
        
        self._shortcuts = ClientGUIListCtrl.BetterListCtrlTreeView( self._shortcuts_panel, 20, model, delete_key_callback = self.RemoveShortcuts, activation_callback = self.EditShortcuts )
        
        self._shortcuts_panel.SetListCtrl( self._shortcuts )
        
        self._shortcuts_panel.AddImportExportButtons( ( ClientGUIShortcuts.ShortcutSet, ), self._AddShortcutSet, custom_get_callable = self._GetSelectedShortcutSet, and_duplicate_button = False )
        
        tt = 'Click this to replicate the current selection of commands with "incremented" shortcuts. If you want to create a list of "set rating to 1, 2, 3" or "set tag" commands, use this.'
        
        self._shortcuts_panel.AddButton( 'special duplicate', self._SpecialDuplicate, enabled_only_on_selection = True, tooltip = tt )
        
        self._shortcuts.setMinimumSize( QC.QSize( 360, 480 ) )
        
        self._add = QW.QPushButton( 'add', self )
        self._add.clicked.connect( self.AddShortcut )
        
        self._edit = QW.QPushButton( 'edit', self )
        self._edit.clicked.connect( self.EditShortcuts )
        
        self._remove = QW.QPushButton( 'remove', self )
        self._remove.clicked.connect( self.RemoveShortcuts )
        
        #
        
        name = shortcuts.GetName()
        
        self._name.setText( name )
        
        self._this_is_custom = True
        
        if name in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES:
            
            self._this_is_custom = False
            
            self._name.setEnabled( False )
            
        
        self._shortcuts.AddDatas( shortcuts.GetShortcutsAndCommands() )
        
        self._shortcuts.Sort()
        
        #
        
        action_buttons = QP.HBoxLayout()
        
        QP.AddToLayout( action_buttons, self._add, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( action_buttons, self._edit, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( action_buttons, self._remove, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        message = 'Please note the shortcut system does not support multiple commands per shortcut yet. If there are shortcut duplicates in this list, only one command will ever fire.'
        
        st = ClientGUICommon.BetterStaticText( self, label = message )
        
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if name in ClientGUIShortcuts.shortcut_names_to_descriptions:
            
            description_text = ClientGUIShortcuts.shortcut_names_to_descriptions[ name ]
            
            description = ClientGUICommon.BetterStaticText( self, description_text, description_text )
            
            description.setWordWrap( True )
            
            QP.AddToLayout( vbox, description, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, self._shortcuts_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, action_buttons, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertShortcutTupleToDisplayTuple( self, shortcut_tuple ):
        
        ( shortcut, command ) = shortcut_tuple
        
        shortcut = typing.cast( ClientGUIShortcuts.Shortcut, shortcut )
        command = typing.cast( CAC.ApplicationCommand, command )
        
        return ( shortcut.ToString( call_mouse_buttons_primary_secondary_override = self._call_mouse_buttons_primary_secondary ), command.ToString() )
        
    
    _ConvertShortcutTupleToSortTuple = _ConvertShortcutTupleToDisplayTuple
    
    def _AddShortcutSet( self, shortcut_set: ClientGUIShortcuts.ShortcutSet ):
        
        self._shortcuts.AddDatas( shortcut_set.GetShortcutsAndCommands() )
        
    
    def _GetSelectedShortcutSet( self ) -> ClientGUIShortcuts.ShortcutSet:
        
        name = self._name.text()
        
        shortcut_set = ClientGUIShortcuts.ShortcutSet( name )
        
        for ( shortcut, command ) in self._shortcuts.GetData( only_selected = True ):
            
            shortcut_set.SetCommand( shortcut, command )
            
        
        return shortcut_set
        
    
    def _SpecialDuplicate( self ):
        
        all_existing_shortcuts = { shortcut for ( shortcut, command ) in self._shortcuts.GetData() }
        
        shortcut_set = self._GetSelectedShortcutSet()
        
        num_not_added = 0
        
        add_rows = []
        
        for ( shortcut, command ) in shortcut_set.GetShortcutsAndCommands():
            
            addee_shortcut = shortcut.Duplicate()
            command = command.Duplicate()
            
            while addee_shortcut in all_existing_shortcuts:
                
                try:
                    
                    addee_shortcut.TryToIncrementKey()
                    
                except HydrusExceptions.VetoException:
                    
                    num_not_added += 1
                    
                    break
                    
                
            
            if addee_shortcut not in all_existing_shortcuts:
                
                add_rows.append( ( addee_shortcut, command ) )
                
                all_existing_shortcuts.add( addee_shortcut )
                
            
        
        self._shortcuts.AddDatas( add_rows, select_sort_and_scroll = True )
        
        if num_not_added > 0:
            
            message = 'Not every shortcut could find a new key to use, sorry!'
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
    
    def AddShortcut( self ):
        
        shortcut = ClientGUIShortcuts.Shortcut()
        command = CAC.ApplicationCommand()
        name = self._name.text()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcut command' ) as dlg:
            
            panel = EditShortcutAndCommandPanel( dlg, shortcut, command, name, self._call_mouse_buttons_primary_secondary, self._shortcuts_merge_non_number_numpad )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( shortcut, command ) = panel.GetValue()
                
                data = ( shortcut, command )
                
                self._shortcuts.AddData( data, select_sort_and_scroll = True )
                
            
        
    
    def EditShortcuts( self ):
        
        data = self._shortcuts.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        ( shortcut, command ) = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcut command' ) as dlg:
            
            name = self._name.text()
            
            panel = EditShortcutAndCommandPanel( dlg, shortcut, command, name, self._call_mouse_buttons_primary_secondary, self._shortcuts_merge_non_number_numpad )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                ( new_shortcut, new_command ) = panel.GetValue()
                
                new_data = ( new_shortcut, new_command )
                
                self._shortcuts.ReplaceData( data, new_data, sort_and_scroll = True )
                
            
        
    
    
    def GetValue( self ):
        
        name = self._name.text()
        
        if self._this_is_custom and name in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES:
            
            raise HydrusExceptions.VetoException( 'That name is reserved--please pick another!' )
            
        
        shortcut_set = ClientGUIShortcuts.ShortcutSet( name )
        
        for ( shortcut, command ) in self._shortcuts.GetData():
            
            dupe_command = shortcut_set.GetCommand( shortcut )
            
            if dupe_command is not None:
                
                message = 'The shortcut:'
                message += '\n' * 2
                message += shortcut.ToString()
                message += '\n' * 2
                message += 'is mapped twice:'
                message += '\n' * 2
                message += command.ToString()
                message += '\n' * 2
                message += dupe_command.ToString()
                message += '\n' * 2
                message += 'The system only supports one command per shortcut in a set for now, please remove one.'
                
                raise HydrusExceptions.VetoException( message )
                
            
            shortcut_set.SetCommand( shortcut, command )
            
        
        return shortcut_set
        
    
    def RemoveShortcuts( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._shortcuts.DeleteSelected()
            
        
    

class ShortcutWidget( QW.QWidget ):
    
    def __init__( self, parent, call_mouse_buttons_primary_secondary: bool, shortcuts_merge_non_number_numpad: bool ):
        
        super().__init__( parent )
        
        self._mouse_radio = QW.QRadioButton( 'mouse', self )
        self._mouse_shortcut = MouseShortcutWidget( self, call_mouse_buttons_primary_secondary )
        
        self._keyboard_radio = QW.QRadioButton( 'keyboard', self )
        self._keyboard_shortcut = KeyboardShortcutWidget( self, shortcuts_merge_non_number_numpad )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, 'Mouse events only work for some windows, mostly media viewer stuff, atm!' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        gridbox = QP.GridLayout( cols = 2 )
        
        gridbox.setColumnStretch( 1, 1 )
        
        QP.AddToLayout( gridbox, self._mouse_radio, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, self._mouse_shortcut, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._keyboard_radio, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( gridbox, self._keyboard_shortcut, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        self._mouse_shortcut.valueChanged.connect( self._mouse_radio.click )
        self._keyboard_shortcut.valueChanged.connect( self._keyboard_radio.click )
        
    
    def GetValue( self ):
        
        if self._mouse_radio.isChecked():
            
            return self._mouse_shortcut.GetValue()
            
        else:
            
            return self._keyboard_shortcut.GetValue()
            
        
    
    def SetValue( self, shortcut ):
        
        if shortcut.GetShortcutType() == ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE:
            
            self._mouse_radio.setChecked( True )
            self._mouse_shortcut.SetValue( shortcut )
            
        else:
            
            self._keyboard_radio.setChecked( True )
            self._keyboard_shortcut.SetValue( shortcut )
            
            ClientGUIFunctions.SetFocusLater( self._keyboard_shortcut )
            
        
    

class KeyboardShortcutWidget( QW.QLineEdit ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, shortcuts_merge_non_number_numpad: bool ):
        
        self._shortcuts_merge_non_number_numpad = shortcuts_merge_non_number_numpad
        self._shortcut = ClientGUIShortcuts.Shortcut()
        
        super().__init__( parent )
        
        self._SetShortcutString()
        
        self.setReadOnly( True )
        
        self.installEventFilter( self )
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString()
        
        self.setText( display_string )
        
    
    def eventFilter( self, watched, event ) -> bool:
        
        if event.type() == QC.QEvent.Type.KeyPress:
            
            shortcut = ClientGUIShortcuts.ConvertKeyEventToShortcut( event, shortcuts_merge_non_number_numpad_override = self._shortcuts_merge_non_number_numpad )
            
            if shortcut is not None:
                
                self._shortcut = shortcut
                
                self._SetShortcutString()
                
                self.valueChanged.emit()
                
            
            return True
            
        
        return super().eventFilter( watched, event )
        
    
    def GetValue( self ):
        
        return self._shortcut
        
    
    def SetValue( self, shortcut ):
        
        self._shortcut = shortcut
        
        self._SetShortcutString()
        
    

class MouseShortcutWidget( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, call_mouse_buttons_primary_secondary: bool ):
        
        super().__init__( parent )
        
        self._button = MouseShortcutButton( self, call_mouse_buttons_primary_secondary )
        
        self._press_or_release = ClientGUICommon.BetterChoice( self )
        
        self._press_or_release.addItem( 'press', ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS )
        self._press_or_release.addItem( 'release', ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_RELEASE )
        
        layout = QP.HBoxLayout()
        
        QP.AddToLayout( layout, self._button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( layout, self._press_or_release, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( layout )
        
        self._press_or_release.currentIndexChanged.connect( self._NewChoice )
        self._button.valueChanged.connect( self._ButtonValueChanged )
        
    
    def _ButtonValueChanged( self ):
        
        self._press_or_release.setEnabled( self._button.GetValue().IsAppropriateForPressRelease() )
        
        self.valueChanged.emit()
        
    
    def _NewChoice( self ):
        
        data = self._press_or_release.GetValue()
        
        press_instead_of_release = data == ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS
        
        self._button.SetPressInsteadOfRelease( press_instead_of_release )
        
        self.valueChanged.emit()
        
    
    def GetValue( self ):
        
        return self._button.GetValue()
        
    
    def SetValue( self, shortcut ):
        
        self.blockSignals( True )
        
        self._button.SetValue( shortcut )
        
        self._press_or_release.SetValue( shortcut.shortcut_press_type )
        
        self.blockSignals( False )
        
    
class MouseShortcutButton( QW.QPushButton ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent, call_mouse_buttons_primary_secondary ):
        
        self._call_mouse_buttons_primary_secondary = call_mouse_buttons_primary_secondary
        
        self._shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] )
        
        self._press_instead_of_release = True
        
        super().__init__( parent )
        
        self._SetShortcutString()
        
    
    def _ProcessMouseEvent( self, event ):
        
        self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
        
        shortcut = ClientGUIShortcuts.ConvertMouseEventToShortcut( event )
        
        if shortcut is not None:
            
            self._shortcut = shortcut
            
            self._SetShortcutString()
            
            self.valueChanged.emit()
            
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString( call_mouse_buttons_primary_secondary_override = self._call_mouse_buttons_primary_secondary )
        
        self.setText( display_string )
        
    
    def mousePressEvent( self, event ):
        
        if self._press_instead_of_release:
            
            self._ProcessMouseEvent( event )
            
        
    
    def mouseReleaseEvent( self, event ):
        
        if not self._press_instead_of_release:
            
            self._ProcessMouseEvent( event )
            
        
    
    def mouseDoubleClickEvent( self, event ):
        
        self._ProcessMouseEvent( event )
        
    
    def wheelEvent( self, event ):
        
        self._ProcessMouseEvent( event )
        
    
    def GetValue( self ) -> ClientGUIShortcuts.Shortcut:
        
        return self._shortcut
        
    
    def SetPressInsteadOfRelease( self, press_instead_of_release ):
        
        self._press_instead_of_release = press_instead_of_release
        
        if self._shortcut.IsAppropriateForPressRelease():
            
            self._shortcut = self._shortcut.Duplicate()
            
            if self._press_instead_of_release:
                
                self._shortcut.shortcut_press_type = ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS
                
            else:
                
                self._shortcut.shortcut_press_type = ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_RELEASE
                
            
            self._SetShortcutString()
            
            self.valueChanged.emit()
            
        
    
    def SetValue( self, shortcut: ClientGUIShortcuts.Shortcut ):
        
        self._shortcut = shortcut.Duplicate()
        
        self._SetShortcutString()
        
        self.valueChanged.emit()
        
    
