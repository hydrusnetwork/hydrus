from qtpy import QtWidgets as QW

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcutControls
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.panels.options import ClientGUIOptionsPanelBase
from hydrus.client.gui.widgets import ClientGUICommon

class ShortcutsPanel( ClientGUIOptionsPanelBase.OptionsPagePanel ):
    
    def __init__( self, parent, new_options, all_shortcuts: list[ ClientGUIShortcuts.ShortcutSet ] ):
        
        self._new_options = new_options
        
        call_mouse_buttons_primary_secondary = new_options.GetBoolean( 'call_mouse_buttons_primary_secondary' )
        shortcuts_merge_non_number_numpad = new_options.GetBoolean( 'shortcuts_merge_non_number_numpad' )
        
        self._have_edited_anything = False
        
        super().__init__( parent )
        
        help_button = ClientGUICommon.IconButton( self, CC.global_icons().help, self._ShowHelp )
        help_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Show help regarding editing shortcuts.' ) )
        
        self._call_mouse_buttons_primary_secondary = QW.QCheckBox( self )
        self._call_mouse_buttons_primary_secondary.setToolTip( ClientGUIFunctions.WrapToolTip( 'Useful if you swap your buttons around.' ) )
        
        self._shortcuts_merge_non_number_numpad = QW.QCheckBox( self )
        self._shortcuts_merge_non_number_numpad.setToolTip( ClientGUIFunctions.WrapToolTip( 'This means a "numpad" variant of Return/Home/Arrow etc.. is just counted as a normal one. Helps clear up a bunch of annoying keyboard mappings.' ) )
        
        reserved_panel = ClientGUICommon.StaticBox( self, 'built-in hydrus shortcut sets' )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_SHORTCUT_SETS.ID, self._GetDisplayTuple, self._GetSortTuple )
        
        self._reserved_shortcuts = ClientGUIListCtrl.BetterListCtrlTreeView( reserved_panel, 6, model, activation_callback = self._EditReserved )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._reserved_shortcuts, ( 32, 12 ) )
        
        self._reserved_shortcuts.setMinimumSize( min_width, min_height )
        
        self._edit_reserved_button = ClientGUICommon.BetterButton( reserved_panel, 'edit', self._EditReserved )
        self._restore_defaults_button = ClientGUICommon.BetterButton( reserved_panel, 'restore defaults', self._RestoreDefaults )
        
        #
        
        custom_panel = ClientGUICommon.StaticBox( self, 'custom user sets' )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_SHORTCUT_SETS.ID, self._GetDisplayTuple, self._GetSortTuple )
        
        self._custom_shortcuts = ClientGUIListCtrl.BetterListCtrlTreeView( custom_panel, 6, model, delete_key_callback = self._Delete, activation_callback = self._EditCustom )
        
        self._add_button = ClientGUICommon.BetterButton( custom_panel, 'add', self._Add )
        self._edit_custom_button = ClientGUICommon.BetterButton( custom_panel, 'edit', self._EditCustom )
        self._delete_button = ClientGUICommon.BetterButton( custom_panel, 'delete', self._Delete )
        
        #
        
        self._call_mouse_buttons_primary_secondary.setChecked( call_mouse_buttons_primary_secondary )
        self._shortcuts_merge_non_number_numpad.setChecked( shortcuts_merge_non_number_numpad )
        
        reserved_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        custom_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() not in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        
        self._reserved_shortcuts.SetData( reserved_shortcuts )
        
        self._reserved_shortcuts.Sort()
        
        self._original_custom_names = { shortcuts.GetName() for shortcuts in custom_shortcuts }
        
        self._custom_shortcuts.SetData( custom_shortcuts )
        
        self._custom_shortcuts.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'Treat all non-number numpad inputs as "normal": ', self._shortcuts_merge_non_number_numpad ) )
        rows.append( ( 'Replace "left/right"-click labels with "primary/secondary": ', self._call_mouse_buttons_primary_secondary ) )
        
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
        QP.AddToLayout( vbox, mouse_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, reserved_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, custom_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
    
    def _Add( self ):
        
        shortcut_set = ClientGUIShortcuts.ShortcutSet( 'new shortcuts' )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcuts' ) as dlg:
            
            call_mouse_buttons_primary_secondary = self._call_mouse_buttons_primary_secondary.isChecked()
            shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
            
            panel = ClientGUIShortcutControls.EditShortcutSetPanel( dlg, shortcut_set, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_shortcuts = panel.GetValue()
                
                existing_names = self._GetExistingCustomShortcutNames()
                
                new_shortcuts.SetNonDupeName( existing_names )
                
                self._custom_shortcuts.AddData( new_shortcuts, select_sort_and_scroll = True )
                
                self._have_edited_anything = True
                
            
        
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self._custom_shortcuts.DeleteSelected()
            
            self._have_edited_anything = True
            
        
    
    def _EditCustom( self ):
        
        data = self._custom_shortcuts.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        shortcuts = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcuts' ) as dlg:
            
            call_mouse_buttons_primary_secondary = self._call_mouse_buttons_primary_secondary.isChecked()
            shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
            
            panel = ClientGUIShortcutControls.EditShortcutSetPanel( dlg, shortcuts, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_shortcuts = panel.GetValue()
                
                existing_names = self._GetExistingCustomShortcutNames()
                
                existing_names.discard( shortcuts.GetName() )
                
                edited_shortcuts.SetNonDupeName( existing_names )
                
                self._custom_shortcuts.ReplaceData( shortcuts, edited_shortcuts, sort_and_scroll = True )
                
                self._have_edited_anything = True
                
            
        
    
    def _EditReserved( self ):
        
        data = self._reserved_shortcuts.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        shortcuts = data
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit shortcuts' ) as dlg:
            
            call_mouse_buttons_primary_secondary = self._call_mouse_buttons_primary_secondary.isChecked()
            shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
            
            panel = ClientGUIShortcutControls.EditShortcutSetPanel( dlg, shortcuts, call_mouse_buttons_primary_secondary, shortcuts_merge_non_number_numpad )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_shortcuts = panel.GetValue()
                
                self._reserved_shortcuts.ReplaceData( shortcuts, edited_shortcuts, sort_and_scroll = True )
                
                self._have_edited_anything = True
                
            
        
    
    def _GetDisplayTuple( self, shortcuts ):
        
        name = shortcuts.GetName()
        
        if name in ClientGUIShortcuts.shortcut_names_to_descriptions:
            
            pretty_name = ClientGUIShortcuts.shortcut_names_to_pretty_names[ name ]
            
        else:
            
            pretty_name = name
            
        
        size = len( shortcuts )
        
        return ( pretty_name, HydrusNumbers.ToHumanInt( size ) )
        
    
    def _GetExistingCustomShortcutNames( self ):
        
        return { shortcuts.GetName() for shortcuts in self._custom_shortcuts.GetData() }
        
    
    def _GetSortTuple( self, shortcuts ):
        
        name = shortcuts.GetName()
        
        if name in ClientGUIShortcuts.shortcut_names_to_descriptions:
            
            sort_name = ClientGUIShortcuts.shortcut_names_sorted.index( name )
            
        else:
            
            sort_name = name
            
        
        size = len( shortcuts )
        
        return ( sort_name, size )
        
    
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
            
            self._reserved_shortcuts.AddData( new_data, select_sort_and_scroll = True )
            
        else:
            
            message = 'Are you certain you want to restore the defaults for "{}"? Any custom shortcuts you have set will be wiped.'.format( name )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._reserved_shortcuts.ReplaceData( existing_data, new_data, sort_and_scroll = True )
                
            
        
    
    def _ShowHelp( self ):
        
        message = 'I am in the process of converting the multiple old messy shortcut systems to this single unified engine. Many actions are not yet available here, and mouse support is very limited. I expect to overwrite the reserved shortcut sets back to (new and expanded) defaults at least once more, so don\'t remap everything yet unless you are ok with doing it again.'
        message += '\n' * 2
        message += '---'
        message += '\n' * 2
        message += 'In hydrus, shortcuts are split into different sets that are active in different contexts. Depending on where the program focus is, multiple sets can be active at the same time. On a keyboard or mouse event, the active sets will be consulted one after another (typically from the smallest and most precise focus to the largest and broadest parent) until an action match is found.'
        message += '\n' * 2
        message += 'There are two kinds--ones built-in to hydrus, and custom sets that you turn on and off:'
        message += '\n' * 2
        message += 'The built-in shortcut sets are always active in their contexts--the \'main_gui\' one is always consulted when you hit a key on the main gui window, for instance. They have limited actions to choose from, appropriate to their context. If you would prefer to, say, open the manage tags dialog with Ctrl+F3, edit or add that entry in the \'media\' set and that new shortcut will apply anywhere you are focused on some particular media.'
        message += '\n' * 2
        message += 'Custom shortcuts sets are those you can create and rename at will. They are only ever active in the media viewer window, and only when you set them so from the top hover-window\'s keyboard icon. They are primarily meant for setting tags and ratings with shortcuts, and are intended to be turned on and off as you perform different \'filtering\' jobs--for instance, you might like to set the 1-5 keys to the different values of a five-star rating system, or assign a few simple keystrokes to a number of common tags.'
        message += '\n' * 2
        message += 'The built-in \'media\' set also supports tag and rating actions, if you would like some of those to always be active.'
        
        ClientGUIDialogsMessage.ShowInformation( self, message )
        
    
    def GetValue( self ):
        
        # a stub for wrapper panels/dialogs to check validity versus a normal editpanel
        return True
        
    
    def UpdateOptions( self ):
        
        call_mouse_buttons_primary_secondary = self._call_mouse_buttons_primary_secondary.isChecked()
        shortcuts_merge_non_number_numpad = self._shortcuts_merge_non_number_numpad.isChecked()
        
        self._new_options.SetBoolean( 'call_mouse_buttons_primary_secondary', call_mouse_buttons_primary_secondary )
        self._new_options.SetBoolean( 'shortcuts_merge_non_number_numpad', shortcuts_merge_non_number_numpad )
        
        if self._have_edited_anything:
            
            shortcut_sets = []
            
            shortcut_sets.extend( self._reserved_shortcuts.GetData() )
            shortcut_sets.extend( self._custom_shortcuts.GetData() )
            
            dupe_shortcut_sets = [ shortcut_set.Duplicate() for shortcut_set in shortcut_sets ]
            
            CG.client_controller.Write( 'serialisables_overwrite', [ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET ], dupe_shortcut_sets )
            
            ClientGUIShortcuts.shortcuts_manager().SetShortcutSets( shortcut_sets )
            
        
    
