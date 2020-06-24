import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client.gui import ClientGUIACDropdown
from hydrus.client.gui import ClientGUICommon
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIListCtrl
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP

def ManageShortcuts( win: QW.QWidget ):
    
    shortcuts_manager = ClientGUIShortcuts.shortcuts_manager()
    
    all_shortcuts = shortcuts_manager.GetShortcutSets()
    
    with ClientGUITopLevelWindowsPanels.DialogEdit( win, 'manage shortcuts' ) as dlg:
        
        panel = EditShortcutsPanel( dlg, all_shortcuts )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            shortcut_sets = panel.GetValue()
            
            dupe_shortcut_sets = [ shortcut_set.Duplicate() for shortcut_set in shortcut_sets ]
            
            HG.client_controller.Write( 'serialisables_overwrite', [ HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET ], dupe_shortcut_sets )
            
            shortcuts_manager.SetShortcutSets( shortcut_sets )
            
        
    
class ApplicationCommandWidget( ClientGUIScrolledPanels.EditPanel ):
    
    COMMAND_TYPE_PANEL_SIMPLE = 0
    COMMAND_TYPE_PANEL_TAG = 1
    COMMAND_TYPE_PANEL_RATING_LIKE = 2
    COMMAND_TYPE_PANEL_RATING_NUMERICAL = 3
    COMMAND_TYPE_PANEL_RATING_NUMERICAL_INCDEC = 4
    
    def __init__( self, parent, command, shortcuts_name ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._current_ratings_like_service = None
        self._current_ratings_numerical_service = None
        
        #
        
        is_custom_or_media = shortcuts_name not in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES or shortcuts_name == 'media'
        
        self._command_type_choice = ClientGUICommon.BetterChoice( self )
        
        self._command_type_choice.addItem( 'simple command', self.COMMAND_TYPE_PANEL_SIMPLE )
        
        if is_custom_or_media:
            
            self._command_type_choice.addItem( 'tag command', self.COMMAND_TYPE_PANEL_TAG )
            self._command_type_choice.addItem( 'like/dislike rating command', self.COMMAND_TYPE_PANEL_RATING_LIKE )
            self._command_type_choice.addItem( 'numerical rating command', self.COMMAND_TYPE_PANEL_RATING_NUMERICAL )
            self._command_type_choice.addItem( 'numerical rating increment/decrement command', self.COMMAND_TYPE_PANEL_RATING_NUMERICAL_INCDEC )
            
        else:
            
            self._command_type_choice.hide()
            
        
        if shortcuts_name in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES:
            
            choices = ClientGUIShortcuts.simple_shortcut_name_to_action_lookup[ shortcuts_name ]
            
        else:
            
            choices = ClientGUIShortcuts.simple_shortcut_name_to_action_lookup[ 'custom' ]
            
        
        choices = sorted( choices )
        
        self._simple_actions = QW.QComboBox( self )
        self._simple_actions.addItems( choices )
        
        #
        
        self._flip_or_set_action = ClientGUICommon.BetterChoice( self )
        
        self._flip_or_set_action.addItem( 'set', HC.CONTENT_UPDATE_SET )
        self._flip_or_set_action.addItem( 'flip on and off', HC.CONTENT_UPDATE_FLIP )
        
        self._flip_or_set_action.SetValue( HC.CONTENT_UPDATE_SET )
        
        #
        
        self._tag_panel = QW.QWidget( self )
        
        self._tag_service_keys = QW.QComboBox( self._tag_panel )
        
        self._tag_value = QW.QLineEdit()
        self._tag_value.setReadOnly( True )
        
        expand_parents = False
        
        self._tag_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._tag_panel, self.SetTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, CC.COMBINED_TAG_SERVICE_KEY )
        
        #
        
        self._ratings_like_panel = QW.QWidget( self )
        
        self._ratings_like_service_keys = QW.QComboBox( self._ratings_like_panel )
        self._ratings_like_service_keys.currentIndexChanged.connect( self._SetActions )
        self._ratings_like_like = QW.QRadioButton( 'like', self._ratings_like_panel )
        self._ratings_like_dislike = QW.QRadioButton( 'dislike', self._ratings_like_panel )
        self._ratings_like_remove = QW.QRadioButton( 'remove rating', self._ratings_like_panel )
        
        #
        
        self._ratings_numerical_panel = QW.QWidget( self )
        
        self._ratings_numerical_service_keys = QW.QComboBox( self._ratings_numerical_panel )
        self._ratings_numerical_service_keys.currentIndexChanged.connect( self._SetActions )
        self._ratings_numerical_slider = QP.LabelledSlider( self._ratings_numerical_panel )
        self._ratings_numerical_remove = QW.QCheckBox( 'remove rating', self._ratings_numerical_panel )
        
        #
        
        self._ratings_numerical_incdec_panel = QW.QWidget( self )
        
        self._ratings_numerical_incdec_service_keys = QW.QComboBox( self._ratings_numerical_incdec_panel )
        
        self._ratings_numerical_incdec = ClientGUICommon.BetterChoice( self._ratings_numerical_incdec_panel )
        
        self._ratings_numerical_incdec.addItem( HC.content_update_string_lookup[ HC.CONTENT_UPDATE_INCREMENT ], HC.CONTENT_UPDATE_INCREMENT )
        self._ratings_numerical_incdec.addItem( HC.content_update_string_lookup[ HC.CONTENT_UPDATE_DECREMENT ], HC.CONTENT_UPDATE_DECREMENT )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
        
        for service in services:
            
            service_name = service.GetName()
            service_key = service.GetServiceKey()
            
            service_type = service.GetServiceType()
            
            if service_type in HC.REAL_TAG_SERVICES:
                
                self._tag_service_keys.addItem( service_name, service_key )
                
            elif service_type == HC.LOCAL_RATING_LIKE:
                
                self._ratings_like_service_keys.addItem( service_name, service_key )
                
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                self._ratings_numerical_service_keys.addItem( service_name, service_key )
                self._ratings_numerical_incdec_service_keys.addItem( service_name, service_key )
                
            
        
        self._SetActions()
        
        #
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            QP.SetStringSelection( self._simple_actions, action )
            
            self._command_type_choice.SetValue( self.COMMAND_TYPE_PANEL_SIMPLE )
            
        else:
            
            ( service_key, content_type, action, value ) = data
            
            
            if HG.client_controller.services_manager.ServiceExists( service_key ):
                
                self._service = HG.client_controller.services_manager.GetService( service_key )
                
            else:
                
                QW.QMessageBox.warning( self, 'Warning', 'The service that this command relies upon no longer exists! This command will reset to a default form.' )
                
                local_tag_services = list( HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, ) ) )
                
                self._service = local_tag_services[0]
                
                content_type = HC.CONTENT_TYPE_MAPPINGS
                action = HC.CONTENT_UPDATE_SET
                
                value = 'tag'
                
            
            service_name = self._service.GetName()
            service_type = self._service.GetServiceType()
            
            self._flip_or_set_action.SetValue( action )
            
            if service_type in HC.REAL_TAG_SERVICES:
                
                QP.SetStringSelection( self._tag_service_keys, service_name )
                
                self._tag_value.setText( value )
                
                self._command_type_choice.SetValue( self.COMMAND_TYPE_PANEL_TAG )
                
            elif service_type == HC.LOCAL_RATING_LIKE:
                
                QP.SetStringSelection( self._ratings_like_service_keys, service_name )
                
                self._SetActions()
                
                if value is None:
                    
                    self._ratings_like_remove.setChecked( True )
                    
                elif value == True:
                    
                    self._ratings_like_like.setChecked( True )
                    
                elif value == False:
                    
                    self._ratings_like_dislike.setChecked( True )
                    
                
                self._command_type_choice.SetValue( self.COMMAND_TYPE_PANEL_RATING_LIKE )
                
            elif service_type == HC.LOCAL_RATING_NUMERICAL:
                
                if action in ( HC.CONTENT_UPDATE_SET, HC.CONTENT_UPDATE_FLIP ):
                    
                    QP.SetStringSelection( self._ratings_numerical_service_keys, service_name )
                    
                    self._SetActions()
                    
                    if value is None:
                        
                        self._ratings_numerical_remove.setChecked( True )
                        
                    else:
                        
                        num_stars = self._current_ratings_numerical_service.GetNumStars()
                        
                        slider_value = int( round( value * num_stars ) )
                        
                        self._ratings_numerical_slider.SetValue( slider_value )
                        
                    
                    self._command_type_choice.SetValue( self.COMMAND_TYPE_PANEL_RATING_NUMERICAL )
                    
                elif action in ( HC.CONTENT_UPDATE_INCREMENT, HC.CONTENT_UPDATE_DECREMENT ):
                    
                    QP.SetStringSelection( self._ratings_numerical_incdec_service_keys, service_name )
                    
                    self._ratings_numerical_incdec.SetValue( action )
                    
                    self._command_type_choice.SetValue( self.COMMAND_TYPE_PANEL_RATING_NUMERICAL_INCDEC )
                    
                
            
        
        #
        
        tag_sub_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( tag_sub_vbox, self._tag_value, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( tag_sub_vbox, self._tag_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        tag_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( tag_hbox, self._tag_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( tag_hbox, tag_sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._tag_panel.setLayout( tag_hbox )
        
        ratings_like_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_like, CC.FLAGS_VCENTER )
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_dislike, CC.FLAGS_VCENTER )
        QP.AddToLayout( ratings_like_hbox, self._ratings_like_remove, CC.FLAGS_VCENTER )
        
        self._ratings_like_panel.setLayout( ratings_like_hbox )
        
        ratings_numerical_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( ratings_numerical_hbox, self._ratings_numerical_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( ratings_numerical_hbox, self._ratings_numerical_slider, CC.FLAGS_VCENTER )
        QP.AddToLayout( ratings_numerical_hbox, self._ratings_numerical_remove, CC.FLAGS_VCENTER )
        
        self._ratings_numerical_panel.setLayout( ratings_numerical_hbox )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._ratings_numerical_incdec_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
        QP.AddToLayout( hbox, self._ratings_numerical_incdec, CC.FLAGS_VCENTER )
        
        self._ratings_numerical_incdec_panel.setLayout( hbox )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._command_type_choice, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._simple_actions, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._flip_or_set_action, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._ratings_like_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._ratings_numerical_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._ratings_numerical_incdec_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._UpdateVisibleControls()
        
        #
        
        self._command_type_choice.currentIndexChanged.connect( self._UpdateVisibleControls )
        
    
    def _GetSimple( self ):
        
        action = self._simple_actions.currentText()
        
        if action == '':
            
            raise HydrusExceptions.VetoException( 'Please select an action!' )
            
        else:
            
            return ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, action )
            
        
    
    def _GetRatingsLike( self ):
        
        selection = self._ratings_like_service_keys.currentIndex()
        
        if selection != -1:
            
            service_key = QP.GetClientData( self._ratings_like_service_keys, selection )
            
            action = self._flip_or_set_action.GetValue()
            
            if self._ratings_like_like.isChecked():
                
                value = 1.0
                
            elif self._ratings_like_dislike.isChecked():
                
                value = 0.0
                
            else:
                
                value = None
                
            
            return ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, value ) )
            
        else:
            
            raise HydrusExceptions.VetoException( 'Please select a rating service!' )
            
        
    
    def _GetRatingsNumerical( self ):
        
        selection = self._ratings_numerical_service_keys.currentIndex()
        
        if selection != -1:
            
            service_key = QP.GetClientData( self._ratings_numerical_service_keys, selection )
            
            action = self._flip_or_set_action.GetValue()
            
            if self._ratings_numerical_remove.isChecked():
                
                value = None
                
            else:
                
                value = self._ratings_numerical_slider.GetValue()
                
                num_stars = self._current_ratings_numerical_service.GetNumStars()
                allow_zero = self._current_ratings_numerical_service.AllowZero()
                
                if allow_zero:
                    
                    value = value / num_stars
                    
                else:
                    
                    value = ( value - 1 ) / ( num_stars - 1 )
                    
                
            
            return ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, value ) )
            
        else:
            
            raise HydrusExceptions.VetoException( 'Please select a rating service!' )
            
        
    
    def _GetRatingsNumericalIncDec( self ):
        
        selection = self._ratings_numerical_incdec_service_keys.currentIndex()
        
        if selection != -1:
            
            service_key = QP.GetClientData( self._ratings_numerical_incdec_service_keys, selection )
            
            action = self._ratings_numerical_incdec.GetValue()
            
            value = 1
            
            return ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, value ) )
            
        else:
            
            raise HydrusExceptions.VetoException( 'Please select a rating service!' )
            
        
    
    def _GetTag( self ):
        
        selection = self._tag_service_keys.currentIndex()
        
        if selection != -1:
            
            service_key = QP.GetClientData( self._tag_service_keys, selection )
            
            action = self._flip_or_set_action.GetValue()
            
            value = self._tag_value.text()
            
            if value == '':
                
                raise HydrusExceptions.VetoException( 'Please enter a tag!' )
                
            
            return ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_MAPPINGS, action, value ) )
            
        else:
            
            raise HydrusExceptions.VetoException( 'Please select a tag service!' )
            
        
    
    def _SetActions( self ):
        
        if self._ratings_like_service_keys.count() > 0:
            
            selection = self._ratings_like_service_keys.currentIndex()
            
            if selection != -1:
                
                service_key = QP.GetClientData( self._ratings_like_service_keys, selection )
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
                self._current_ratings_like_service = service
                
            
        
        if self._ratings_numerical_service_keys.count() > 0:
            
            selection = self._ratings_numerical_service_keys.currentIndex()
            
            if selection != -1:
                
                service_key = QP.GetClientData( self._ratings_numerical_service_keys, selection )
                
                service = HG.client_controller.services_manager.GetService( service_key )
                
                self._current_ratings_numerical_service = service
                
                num_stars = service.GetNumStars()
                
                allow_zero = service.AllowZero()
                
                if allow_zero:
                    
                    minimum = 0
                    
                else:
                    
                    minimum = 1
                    
                
                self._ratings_numerical_slider.SetRange( minimum, num_stars )
                
            
        
    
    def _UpdateVisibleControls( self ):
        
        self._simple_actions.hide()
        self._flip_or_set_action.hide()
        self._tag_panel.hide()
        self._ratings_like_panel.hide()
        self._ratings_numerical_panel.hide()
        self._ratings_numerical_incdec_panel.hide()
        
        command_type = self._command_type_choice.GetValue()
        
        if command_type == self.COMMAND_TYPE_PANEL_SIMPLE:
            
            self._simple_actions.show()
            
        elif command_type in ( self.COMMAND_TYPE_PANEL_TAG, self.COMMAND_TYPE_PANEL_RATING_LIKE, self.COMMAND_TYPE_PANEL_RATING_NUMERICAL ):
            
            self._flip_or_set_action.show()
            
            if command_type == self.COMMAND_TYPE_PANEL_TAG:
                
                self._tag_panel.show()
                
            elif command_type == self.COMMAND_TYPE_PANEL_RATING_LIKE:
                
                self._ratings_like_panel.show()
                
            elif command_type == self.COMMAND_TYPE_PANEL_RATING_NUMERICAL:
                
                self._ratings_numerical_panel.show()
                
            
        elif command_type == self.COMMAND_TYPE_PANEL_RATING_NUMERICAL_INCDEC:
            
            self._ratings_numerical_incdec_panel.show()
            
        
    
    def GetValue( self ):
        
        command_type = self._command_type_choice.GetValue()
        
        if command_type == self.COMMAND_TYPE_PANEL_SIMPLE:
            
            return self._GetSimple()
            
        elif command_type == self.COMMAND_TYPE_PANEL_TAG:
            
            return self._GetTag()
            
        elif command_type == self.COMMAND_TYPE_PANEL_RATING_LIKE:
            
            return self._GetRatingsLike()
            
        elif command_type == self.COMMAND_TYPE_PANEL_RATING_NUMERICAL:
            
            return self._GetRatingsNumerical()
            
        elif command_type == self.COMMAND_TYPE_PANEL_RATING_NUMERICAL_INCDEC:
            
            return self._GetRatingsNumericalIncDec()
            
        
    
    def SetTags( self, tags ):
        
        if len( tags ) > 0:
            
            tag = list( tags )[0]
            
            self._tag_value.setText( tag )
            
        
    
class EditShortcutAndCommandPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, shortcut, command, shortcuts_name ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        self._shortcut_panel = ClientGUICommon.StaticBox( self, 'shortcut' )
        
        self._shortcut = ShortcutWidget( self._shortcut_panel )
        
        self._command_panel = ClientGUICommon.StaticBox( self, 'command' )
        
        self._command = ApplicationCommandWidget( self._command_panel, command, shortcuts_name )
        
        #
        
        self._shortcut.SetValue( shortcut )
        
        #
        
        self._shortcut_panel.Add( self._shortcut, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._command_panel.Add( self._command, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._shortcut_panel, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self, '\u2192' ), CC.FLAGS_VCENTER )
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
        
        self._shortcuts = ClientGUIListCtrl.BetterListCtrl( self._shortcuts_panel, 'shortcuts', 20, 20, [ ( 'shortcut', 20 ), ( 'command', -1 ) ], data_to_tuples_func = self._ConvertSortTupleToPrettyTuple, delete_key_callback = self.RemoveShortcuts, activation_callback = self.EditShortcuts )
        
        self._shortcuts_panel.SetListCtrl( self._shortcuts )
        
        self._shortcuts_panel.AddImportExportButtons( ( ClientGUIShortcuts.ShortcutSet, ), self._AddShortcutSet, custom_get_callable = self._GetSelectedShortcutSet )
        
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
            
        
        self._shortcuts.AddDatas( shortcuts )
        
        self._shortcuts.Sort( 1 )
        
        #
        
        action_buttons = QP.HBoxLayout()
        
        QP.AddToLayout( action_buttons, self._add, CC.FLAGS_VCENTER )
        QP.AddToLayout( action_buttons, self._edit, CC.FLAGS_VCENTER )
        QP.AddToLayout( action_buttons, self._remove, CC.FLAGS_VCENTER )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._name, self, 'name: ' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if name in ClientGUIShortcuts.shortcut_names_to_descriptions:
            
            description_text = ClientGUIShortcuts.shortcut_names_to_descriptions[ name ]
            
            description = ClientGUICommon.BetterStaticText( self, description_text, description_text )
            
            description.setWordWrap( True )
            
            QP.AddToLayout( vbox, description, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, self._shortcuts_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, action_buttons, CC.FLAGS_BUTTON_SIZER )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertSortTupleToPrettyTuple( self, shortcut_tuple ):
        
        ( shortcut, command ) = shortcut_tuple
        
        display_tuple = ( shortcut.ToString(), command.ToString() )
        sort_tuple = display_tuple
        
        return ( display_tuple, sort_tuple )
        
    
    def _AddShortcutSet( self, shortcut_set: ClientGUIShortcuts.ShortcutSet ):
        
        self._shortcuts.AddDatas( shortcut_set )
        
    
    def _GetSelectedShortcutSet( self ):
        
        name = self._name.text()
        
        shortcut_set = ClientGUIShortcuts.ShortcutSet( name )
        
        for ( shortcut, command ) in self._shortcuts.GetData( only_selected = True ):
            
            shortcut_set.SetCommand( shortcut, command )
            
        
        return shortcut_set
        
    
    def AddShortcut( self ):
        
        shortcut = ClientGUIShortcuts.Shortcut()
        command = ClientData.ApplicationCommand()
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
            
            shortcut_set.SetCommand( shortcut, command )
            
        
        return shortcut_set
        
    
    def RemoveShortcuts( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            self._shortcuts.DeleteSelected()
            
        
    
class EditShortcutsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, all_shortcuts ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowHelp )
        help_button.setToolTip( 'Show help regarding editing shortcuts.' )
        
        reserved_panel = ClientGUICommon.StaticBox( self, 'built-in hydrus shortcut sets' )
        
        self._reserved_shortcuts = ClientGUIListCtrl.BetterListCtrl( reserved_panel, 'reserved_shortcuts', 6, 30, [ ( 'name', -1 ), ( 'number of shortcuts', 20 ) ], data_to_tuples_func = self._GetTuples, activation_callback = self._EditReserved )
        
        self._reserved_shortcuts.setMinimumSize( QC.QSize( 320, 200 ) )
        
        self._edit_reserved_button = ClientGUICommon.BetterButton( reserved_panel, 'edit', self._EditReserved )
        self._restore_defaults_button = ClientGUICommon.BetterButton( reserved_panel, 'restore defaults', self._RestoreDefaults )
        
        #
        
        custom_panel = ClientGUICommon.StaticBox( self, 'custom user sets' )
        
        self._custom_shortcuts = ClientGUIListCtrl.BetterListCtrl( custom_panel, 'custom_shortcuts', 6, 30, [ ( 'name', -1 ), ( 'number of shortcuts', 20 ) ], data_to_tuples_func = self._GetTuples, delete_key_callback = self._Delete, activation_callback = self._EditCustom )
        
        self._add_button = ClientGUICommon.BetterButton( custom_panel, 'add', self._Add )
        self._edit_custom_button = ClientGUICommon.BetterButton( custom_panel, 'edit', self._EditCustom )
        self._delete_button = ClientGUICommon.BetterButton( custom_panel, 'delete', self._Delete )
        
        if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            custom_panel.hide()
            
        
        #
        
        reserved_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        custom_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() not in ClientGUIShortcuts.SHORTCUTS_RESERVED_NAMES ]
        
        self._reserved_shortcuts.AddDatas( reserved_shortcuts )
        
        self._reserved_shortcuts.Sort( 0 )
        
        self._original_custom_names = set()
        
        for shortcuts in custom_shortcuts:
            
            self._custom_shortcuts.AddDatas( ( shortcuts, ) )
            
            self._original_custom_names.add( shortcuts.GetName() )
            
        
        self._custom_shortcuts.Sort( 0 )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._edit_reserved_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( button_hbox, self._restore_defaults_button, CC.FLAGS_VCENTER )
        
        reserved_panel.Add( self._reserved_shortcuts, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        reserved_panel.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( button_hbox, self._edit_custom_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( button_hbox, self._delete_button, CC.FLAGS_VCENTER )
        
        custom_panel_message = 'Custom shortcuts are advanced. They apply to the media viewer and must be turned on to take effect.'
        
        st = ClientGUICommon.BetterStaticText( custom_panel, custom_panel_message )
        st.setWordWrap( True )
        
        custom_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        custom_panel.Add( self._custom_shortcuts, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        custom_panel.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_button, CC.FLAGS_LONE_BUTTON )
        QP.AddToLayout( vbox, reserved_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, custom_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
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
            sort_name = ClientGUIShortcuts.shortcut_names_to_sort_order[ name ]
            
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
            
            QW.QMessageBox.information( self, 'Information', 'It looks like your client was missing the "{}" shortcut set! It will now be restored.'.format( name ) )
            
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
        
        QW.QMessageBox.information( self, 'Information', message )
        
    
    def GetValue( self ) -> typing.List[ ClientGUIShortcuts.ShortcutSet ]:
        
        shortcut_sets = []
        
        shortcut_sets.extend( self._reserved_shortcuts.GetData() )
        shortcut_sets.extend( self._custom_shortcuts.GetData() )
        
        return shortcut_sets
        
    
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
        
        QP.AddToLayout( gridbox, self._mouse_radio, CC.FLAGS_VCENTER )
        QP.AddToLayout( gridbox, self._mouse_shortcut, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( gridbox, self._keyboard_radio, CC.FLAGS_VCENTER )
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
        
        QP.AddToLayout( layout, self._button, CC.FLAGS_VCENTER )
        QP.AddToLayout( layout, self._press_or_release, CC.FLAGS_VCENTER )
        
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
        
    
