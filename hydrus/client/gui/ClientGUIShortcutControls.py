import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.widgets import ClientGUIApplicationCommand
from hydrus.client.gui.widgets import ClientGUICommon

def ManageShortcuts( win: QW.QWidget ):
    
    shortcuts_manager = ClientGUIShortcuts.shortcuts_manager()
    
    call_mouse_buttons_primary_secondary = CG.client_controller.new_options.GetBoolean( 'call_mouse_buttons_primary_secondary' )
    shortcuts_merge_non_number_numpad = CG.client_controller.new_options.GetBoolean( 'shortcuts_merge_non_number_numpad' )
    
    all_shortcuts = shortcuts_manager.GetShortcutSets()
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, 'manage shortcuts' ) as dlg:
        
        panel = EditShortcutsPanel( dlg, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad, all_shortcuts )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            ( call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad, shortcut_sets ) = panel.GetValue()
            
            CG.client_controller.new_options.SetBoolean( 'call_mouse_buttons_primary_secondary', call_mouse_buttons_primary_secondary )
            
            ClientGUIShortcuts.SetMouseLabels( call_mouse_buttons_primary_secondary )
            
            CG.client_controller.new_options.SetBoolean( 'shortcuts_merge_non_number_numpad', shortcuts_merge_non_number_numpad )
            
            dupe_shortcut_sets = [ shortcut_set.Duplicate() for shortcut_set in shortcut_sets ]
            
            CG.client_controller.Write( 'serialisables_overwrite', [ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET ], dupe_shortcut_sets )
            
            shortcuts_manager.SetShortcutSets( shortcut_sets )
            
        
    
class EditShortcutAndCommandPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, shortcut, command, shortcuts_name ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        self._shortcut_panel = ClientGUICommon.StaticBox( self, 'shortcut' )
        
        self._shortcut = ShortcutWidget( self._shortcut_panel )
        
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
    
    def __init__( self, parent, shortcuts: ClientGUIShortcuts.ShortcutSet ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._name = QW.QLineEdit( self )
        
        self._shortcuts_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._shortcuts = ClientGUIListCtrl.BetterListCtrl( self._shortcuts_panel, CGLC.COLUMN_LIST_SHORTCUTS.ID, 20, data_to_tuples_func = self._ConvertSortTupleToPrettyTuple, delete_key_callback = self.RemoveShortcuts, activation_callback = self.EditShortcuts )
        
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
        
        QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._name, self, 'name: ' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if name in ClientGUIShortcuts.shortcut_names_to_descriptions:
            
            description_text = ClientGUIShortcuts.shortcut_names_to_descriptions[ name ]
            
            description = ClientGUICommon.BetterStaticText( self, description_text, description_text )
            
            description.setWordWrap( True )
            
            QP.AddToLayout( vbox, description, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, self._shortcuts_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, action_buttons, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertSortTupleToPrettyTuple( self, shortcut_tuple ):
        
        ( shortcut, command ) = shortcut_tuple
        
        display_tuple = ( shortcut.ToString(), command.ToString() )
        sort_tuple = display_tuple
        
        return ( display_tuple, sort_tuple )
        
    
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
                
                self._shortcuts.AddDatas( [ ( addee_shortcut, command ) ] )
                
                all_existing_shortcuts.add( addee_shortcut )
                
            
        
        self._shortcuts.Sort()
        
        if num_not_added > 0:
            
            message = 'Not every shortcut could find a new key to use, sorry!'
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
    
    def AddShortcut( self ):
        
        shortcut = ClientGUIShortcuts.Shortcut()
        command = CAC.ApplicationCommand()
        name = self._name.text()
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcut command' ) as dlg:
            
            panel = EditShortcutAndCommandPanel( dlg, shortcut, command, name )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ( shortcut, command ) = panel.GetValue()
                
                data = ( shortcut, command )
                
                self._shortcuts.AddDatas( ( data, ) )
                
            
        
    
    def EditShortcuts( self ):
        
        name = self._name.text()
        
        for data in self._shortcuts.GetData( only_selected = True ):
        
            ( shortcut, command ) = data
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcut command' ) as dlg:
                
                panel = EditShortcutAndCommandPanel( dlg, shortcut, command, name )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    ( new_shortcut, new_command ) = panel.GetValue()
                    
                    new_data = ( new_shortcut, new_command )
                    
                    self._shortcuts.ReplaceData( data, new_data )
                    
                else:
                    
                    break
                    
                
            
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        if self._this_is_custom and name in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES:
            
            raise HydrusExceptions.VetoException( 'That name is reserved--please pick another!' )
            
        
        shortcut_set = ClientGUIShortcuts.ShortcutSet( name )
        
        for ( shortcut, command ) in self._shortcuts.GetData():
            
            dupe_command = shortcut_set.GetCommand( shortcut )
            
            if dupe_command is not None:
                
                message = 'The shortcut:'
                message += os.linesep * 2
                message += shortcut.ToString()
                message += os.linesep * 2
                message += 'is mapped twice:'
                message += os.linesep * 2
                message += command.ToString()
                message += os.linesep * 2
                message += dupe_command.ToString()
                message += os.linesep * 2
                message += 'The system only supports one command per shortcut in a set for now, please remove one.'
                
                raise HydrusExceptions.VetoException( message )
                
            
            shortcut_set.SetCommand( shortcut, command )
            
        
        return shortcut_set
        
    
    def RemoveShortcuts( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            self._shortcuts.DeleteSelected()
            
        
    
class EditShortcutsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad, all_shortcuts ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowHelp )
        help_button.setToolTip( 'Show help regarding editing shortcuts.' )
        
        self._call_mouse_buttons_primary_secondary = QW.QCheckBox( self )
        self._call_mouse_buttons_primary_secondary.setToolTip( 'Useful if you swap your buttons around.' )
        
        self._shortcuts_merge_non_number_numpad = QW.QCheckBox( self )
        self._shortcuts_merge_non_number_numpad.setToolTip( 'This means a "numpad" variant of Return/Home/Arrow etc.. is just counted as a normal one. Helps clear up a bunch of annoying keyboard mappings.' )
        
        reserved_panel = ClientGUICommon.StaticBox( self, 'built-in hydrus shortcut sets' )
        
        self._reserved_shortcuts = ClientGUIListCtrl.BetterListCtrl( reserved_panel, CGLC.COLUMN_LIST_SHORTCUT_SETS.ID, 6, data_to_tuples_func = self._GetTuples, activation_callback = self._EditReserved )
        
        self._reserved_shortcuts.setMinimumSize( QC.QSize( 320, 200 ) )
        
        self._edit_reserved_button = ClientGUICommon.BetterButton( reserved_panel, 'edit', self._EditReserved )
        self._restore_defaults_button = ClientGUICommon.BetterButton( reserved_panel, 'restore defaults', self._RestoreDefaults )
        
        #
        
        custom_panel = ClientGUICommon.StaticBox( self, 'custom user sets' )
        
        self._custom_shortcuts = ClientGUIListCtrl.BetterListCtrl( custom_panel, CGLC.COLUMN_LIST_SHORTCUT_SETS.ID, 6, data_to_tuples_func = self._GetTuples, delete_key_callback = self._Delete, activation_callback = self._EditCustom )
        
        self._add_button = ClientGUICommon.BetterButton( custom_panel, 'add', self._Add )
        self._edit_custom_button = ClientGUICommon.BetterButton( custom_panel, 'edit', self._EditCustom )
        self._delete_button = ClientGUICommon.BetterButton( custom_panel, 'delete', self._Delete )
        
        if not CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            custom_panel.hide()
            
        
        #
        
        self._call_mouse_buttons_primary_secondary.setChecked( call_mouse_buttons_primary_secondary )
        self._shortcuts_merge_non_number_numpad.setChecked( shortcuts_merge_non_number_numpad )
        
        reserved_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        custom_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() not in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        
        self._reserved_shortcuts.AddDatas( reserved_shortcuts )
        
        self._reserved_shortcuts.Sort()
        
        self._original_custom_names = set()
        
        for shortcuts in custom_shortcuts:
            
            self._custom_shortcuts.AddDatas( ( shortcuts, ) )
            
            self._original_custom_names.add( shortcuts.GetName() )
            
        
        self._custom_shortcuts.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'Treat all non-number numpad inputs as "normal": ', self._shortcuts_merge_non_number_numpad ) )
        rows.append( ( 'Replace "left/right"-click with "primary/secondary": ', self._call_mouse_buttons_primary_secondary ) )
        
        mouse_gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._edit_reserved_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._restore_defaults_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        reserved_panel.Add( self._reserved_shortcuts, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        reserved_panel.Add( button_hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._edit_custom_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( button_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        custom_panel_message = 'Custom shortcuts are advanced. They apply to the media viewer and must be turned on to take effect.'
        
        st = ClientGUICommon.BetterStaticText( custom_panel, custom_panel_message )
        st.setWordWrap( True )
        
        custom_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        custom_panel.Add( self._custom_shortcuts, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        custom_panel.Add( button_hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, mouse_gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, reserved_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, custom_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._call_mouse_buttons_primary_secondary.clicked.connect( self._UpdateMouseLabels )
        self._shortcuts_merge_non_number_numpad.clicked.connect( self._TempSaveNumpadMerge )
        
    
    def _Add( self ):
        
        shortcut_set = ClientGUIShortcuts.ShortcutSet( 'new shortcuts' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcuts' ) as dlg:
            
            panel = EditShortcutSetPanel( dlg, shortcut_set )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_shortcuts = panel.GetValue()
                
                self._custom_shortcuts.AddDatas( ( new_shortcuts, ) )
                
            
        
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            self._custom_shortcuts.DeleteSelected()
            
        
    
    def _EditCustom( self ):
        
        all_selected = self._custom_shortcuts.GetData( only_selected = True )
        
        for shortcuts in all_selected:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcuts' ) as dlg:
                
                panel = EditShortcutSetPanel( dlg, shortcuts )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_shortcuts = panel.GetValue()
                    
                    self._custom_shortcuts.ReplaceData( shortcuts, edited_shortcuts )
                    
                else:
                    
                    break
                    
                
            
        
    
    def _EditReserved( self ):
        
        all_selected = self._reserved_shortcuts.GetData( only_selected = True )
        
        for shortcuts in all_selected:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcuts' ) as dlg:
                
                panel = EditShortcutSetPanel( dlg, shortcuts )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_shortcuts = panel.GetValue()
                    
                    self._reserved_shortcuts.ReplaceData( shortcuts, edited_shortcuts )
                    
                else:
                    
                    break
                    
                
            
        
    
    def _GetTuples( self, shortcuts ):
        
        name = shortcuts.GetName()
        
        if name in ClientGUIShortcuts.shortcut_names_to_descriptions:
            
            pretty_name = ClientGUIShortcuts.shortcut_names_to_pretty_names[ name ]
            sort_name = ClientGUIShortcuts.shortcut_names_sorted.index( name )
            
        else:
            
            pretty_name = name
            sort_name = name
            
        
        size = len( shortcuts )
        
        display_tuple = ( pretty_name, HydrusData.ToHumanInt( size ) )
        sort_tuple = ( sort_name, size )
        
        return ( display_tuple, sort_tuple )
        
    
    def _RestoreDefaults( self ):
        
        from hydrus.client import ClientDefaults
        
        defaults = ClientDefaults.GetDefaultShortcuts()
        
        names_to_sets = { shortcut_set.GetName() : shortcut_set for shortcut_set in defaults }
        
        choice_tuples = [ ( name, name ) for name in names_to_sets ]
        
        try:
            
            name = ClientGUIDialogsQuick.SelectFromList( self, 'select which default to restore', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        new_data = names_to_sets[ name ]
        
        existing_data = None
        
        for data in self._reserved_shortcuts.GetData():
            
            if data.GetName() == name:
                
                existing_data = data
                
                break
                
            
        
        if existing_data is None:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'It looks like your client was missing the "{}" shortcut set! It will now be restored.'.format( name ) )
            
            self._reserved_shortcuts.AddDatas( ( new_data, ) )
            
        else:
            
            message = 'Are you certain you want to restore the defaults for "{}"? Any custom shortcuts you have set will be wiped.'.format( name )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.Accepted:
                
                self._reserved_shortcuts.ReplaceData( existing_data, new_data )
                
            
        
    
    def _ShowHelp( self ):
        
        message = 'I am in the process of converting the multiple old messy shortcut systems to this single unified engine. Many actions are not yet available here, and mouse support is very limited. I expect to overwrite the reserved shortcut sets back to (new and expanded) defaults at least once more, so don\'t remap everything yet unless you are ok with doing it again.'
        message += os.linesep * 2
        message += '---'
        message += os.linesep * 2
        message += 'In hydrus, shortcuts are split into different sets that are active in different contexts. Depending on where the program focus is, multiple sets can be active at the same time. On a keyboard or mouse event, the active sets will be consulted one after another (typically from the smallest and most precise focus to the largest and broadest parent) until an action match is found.'
        message += os.linesep * 2
        message += 'There are two kinds--ones built-in to hydrus, and custom sets that you turn on and off:'
        message += os.linesep * 2
        message += 'The built-in shortcut sets are always active in their contexts--the \'main_gui\' one is always consulted when you hit a key on the main gui window, for instance. They have limited actions to choose from, appropriate to their context. If you would prefer to, say, open the manage tags dialog with Ctrl+F3, edit or add that entry in the \'media\' set and that new shortcut will apply anywhere you are focused on some particular media.'
        message += os.linesep * 2
        message += 'Custom shortcuts sets are those you can create and rename at will. They are only ever active in the media viewer window, and only when you set them so from the top hover-window\'s keyboard icon. They are primarily meant for setting tags and ratings with shortcuts, and are intended to be turned on and off as you perform different \'filtering\' jobs--for instance, you might like to set the 1-5 keys to the different values of a five-star rating system, or assign a few simple keystrokes to a number of common tags.'
        message += os.linesep * 2
        message += 'The built-in \'media\' set also supports tag and rating actions, if you would like some of those to always be active.'
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def _TempSaveNumpadMerge( self ):
        
        # this is dumb, but we do want the behaviour to change instantly so this dialog reflects it, so there we go
        
        shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
        
        CG.client_controller.new_options.SetBoolean( 'shortcuts_merge_non_number_numpad', shortcuts_merge_non_number_numpad )
        
    
    def _UpdateMouseLabels( self ):
        
        swap_labels = self._call_mouse_buttons_primary_secondary.isChecked()
        
        ClientGUIShortcuts.SetMouseLabels( swap_labels )
        
    
    def GetValue( self ) -> typing.Tuple[ bool, bool, typing.List[ ClientGUIShortcuts.ShortcutSet ] ]:
        
        call_mouse_buttons_primary_secondary = self._call_mouse_buttons_primary_secondary.isChecked()
        shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
        
        shortcut_sets = []
        
        shortcut_sets.extend( self._reserved_shortcuts.GetData() )
        shortcut_sets.extend( self._custom_shortcuts.GetData() )
        
        return ( call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad, shortcut_sets )
        
    
class ShortcutWidget( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._mouse_radio = QW.QRadioButton( 'mouse', self )
        self._mouse_shortcut = MouseShortcutWidget( self )
        
        self._keyboard_radio = QW.QRadioButton( 'keyboard', self )
        self._keyboard_shortcut = KeyboardShortcutWidget( self )
        
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
            
        
    
class KeyboardShortcutWidget( QW.QLineEdit ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent ):
        
        self._shortcut = ClientGUIShortcuts.Shortcut()
        
        QW.QLineEdit.__init__( self, parent )
        
        self._SetShortcutString()
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString()
        
        self.setText( display_string )
        
    
    def keyPressEvent( self, event ):
        
        shortcut = ClientGUIShortcuts.ConvertKeyEventToShortcut( event )
        
        if shortcut is not None:
            
            self._shortcut = shortcut
            
            self._SetShortcutString()
            
            self.valueChanged.emit()
            
        
    
    def GetValue( self ):
        
        return self._shortcut
        
    
    def SetValue( self, shortcut ):
        
        self._shortcut = shortcut
        
        self._SetShortcutString()
        
    
class MouseShortcutWidget( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._button = MouseShortcutButton( self )
        
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
    
    def __init__( self, parent ):
        
        self._shortcut = ClientGUIShortcuts.Shortcut( ClientGUIShortcuts.SHORTCUT_TYPE_MOUSE, ClientGUIShortcuts.SHORTCUT_MOUSE_LEFT, ClientGUIShortcuts.SHORTCUT_PRESS_TYPE_PRESS, [] )
        
        self._press_instead_of_release = True
        
        QW.QPushButton.__init__( self, parent )
        
        self._SetShortcutString()
        
    
    def _ProcessMouseEvent( self, event ):
        
        self.setFocus( QC.Qt.OtherFocusReason )
        
        shortcut = ClientGUIShortcuts.ConvertMouseEventToShortcut( event )
        
        if shortcut is not None:
            
            self._shortcut = shortcut
            
            self._SetShortcutString()
            
            self.valueChanged.emit()
            
        
    
    def _SetShortcutString( self ):
        
        display_string = self._shortcut.ToString()
        
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
        
    
