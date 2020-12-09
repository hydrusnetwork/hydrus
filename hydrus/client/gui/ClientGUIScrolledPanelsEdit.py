import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNetwork
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDuplicates
from hydrus.client.gui import ClientGUICommon
from hydrus.client.gui import ClientGUIControls
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIImport
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUIMPV
from hydrus.client.gui import ClientGUITags
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.importing import ClientImportOptions
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags

class EditAccountTypePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, service_type: int, account_type: HydrusNetwork.AccountType ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        ( self._account_type_key, title, permissions, bandwidth_rules ) = account_type.ToTuple()
        
        self._title = QW.QLineEdit( self )
        
        permission_choices = self._GeneratePermissionChoices( service_type )
        
        self._permission_controls = []
        
        self._permissions_panel = ClientGUICommon.StaticBox( self, 'permissions' )
        
        gridbox_rows = []
        
        for ( content_type, action_rows ) in permission_choices:
            
            choice_control = ClientGUICommon.BetterChoice( self._permissions_panel )
            
            for ( label, action ) in action_rows:
                
                choice_control.addItem( label, (content_type, action) )
                
            
            if content_type in permissions:
                
                selection_row = ( content_type, permissions[ content_type ] )
                
            else:
                
                selection_row = ( content_type, None )
                
            
            try:
                
                choice_control.SetValue( selection_row )
                
            except:
                
                choice_control.SetValue( ( content_type, None ) )
                
            
            self._permission_controls.append( choice_control )
            
            gridbox_label = HC.content_type_string_lookup[ content_type ]
            
            gridbox_rows.append( ( gridbox_label, choice_control ) )
            
        
        gridbox = ClientGUICommon.WrapInGrid( self._permissions_panel, gridbox_rows )
        
        self._bandwidth_rules_control = ClientGUIControls.BandwidthRulesCtrl( self, bandwidth_rules )
        
        #
        
        self._title.setText( title )
        
        #
        
        t_hbox = ClientGUICommon.WrapInText( self._title, self, 'title: ' )
        
        self._permissions_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, t_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._permissions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._bandwidth_rules_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def _GeneratePermissionChoices( self, service_type ):
        
        possible_permissions = HydrusNetwork.GetPossiblePermissions( service_type )
        
        permission_choices = []
        
        for ( content_type, possible_actions ) in possible_permissions:
            
            choices = []
            
            for action in possible_actions:
                
                choices.append( ( HC.permission_pair_string_lookup[ ( content_type, action ) ], action ) )
                
            
            permission_choices.append( ( content_type, choices ) )
            
        
        return permission_choices
        
    
    def GetValue( self ) -> HydrusNetwork.AccountType:
        
        title = self._title.text()
        
        permissions = {}
        
        for permission_control in self._permission_controls:
            
            ( content_type, action ) = permission_control.GetValue()
            
            if action is not None:
                
                permissions[ content_type ] = action
                
            
        
        bandwidth_rules = self._bandwidth_rules_control.GetValue()
        
        return HydrusNetwork.AccountType.GenerateAccountTypeFromParameters( self._account_type_key, title, permissions, bandwidth_rules )
        
    
class EditChooseMultiple( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, choice_tuples: list ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._checkboxes = QP.CheckListBox( self )
        
        self._checkboxes.setMinimumSize( QC.QSize( 320, 420 ) )
        
        try:
            
            choice_tuples.sort()
            
        except TypeError:
            
            try:
                
                choice_tuples.sort( key = lambda t: t[0] )
                
            except TypeError:
                
                pass # fugg
                
            
        
        for ( index, ( label, data, selected ) ) in enumerate( choice_tuples ):
            
            self._checkboxes.Append( label, data )
            
            if selected:
                
                self._checkboxes.Check( index )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._checkboxes, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ) -> list:
        
        return self._checkboxes.GetChecked()
        
    
class EditDefaultTagImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, url_classes, parsers, url_class_keys_to_parser_keys, file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._url_classes = url_classes
        self._parsers = parsers
        self._url_class_keys_to_parser_keys = url_class_keys_to_parser_keys
        self._parser_keys_to_parsers = { parser.GetParserKey() : parser for parser in self._parsers }
        
        self._url_class_keys_to_tag_import_options = dict( url_class_keys_to_tag_import_options )
        
        #
        
        show_downloader_options = True
        
        self._file_post_default_tag_import_options_button = ClientGUIImport.TagImportOptionsButton( self, file_post_default_tag_import_options, show_downloader_options )
        self._watchable_default_tag_import_options_button = ClientGUIImport.TagImportOptionsButton( self, watchable_default_tag_import_options, show_downloader_options )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, CGLC.COLUMN_LIST_DEFAULT_TAG_IMPORT_OPTIONS.ID, 15, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Clear, activation_callback = self._Edit )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl_panel.AddButton( 'copy', self._Copy, enabled_check_func = self._OnlyOneTIOSelected )
        self._list_ctrl_panel.AddButton( 'paste', self._Paste, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddButton( 'clear', self._Clear, enabled_only_on_selection = True )
        
        #
        
        eligible_url_classes = [ url_class for url_class in url_classes if url_class.GetURLType() in ( HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE ) and url_class.GetClassKey() in self._url_class_keys_to_parser_keys ]
        
        self._list_ctrl.AddDatas( eligible_url_classes )
        
        self._list_ctrl.Sort()
        
        #
        
        rows = []
        
        rows.append( ( 'default for file posts: ', self._file_post_default_tag_import_options_button ) )
        rows.append( ( 'default for watchable urls: ', self._watchable_default_tag_import_options_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, url_class ):
        
        url_class_key = url_class.GetClassKey()
        
        name = url_class.GetName()
        url_type = url_class.GetURLType()
        defaults_set = url_class_key in self._url_class_keys_to_tag_import_options
        
        pretty_name = name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        if defaults_set:
            
            pretty_default_set = 'yes'
            
        else:
            
            pretty_default_set = ''
            
        
        display_tuple = ( pretty_name, pretty_url_type, pretty_default_set )
        sort_tuple = ( name, pretty_url_type, defaults_set )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Clear( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear default tag import options for all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            url_classes_to_clear = self._list_ctrl.GetData( only_selected = True )
            
            for url_class in url_classes_to_clear:
                
                url_class_key = url_class.GetClassKey()
                
                if url_class_key in self._url_class_keys_to_tag_import_options:
                    
                    del self._url_class_keys_to_tag_import_options[ url_class_key ]
                    
                
            
            self._list_ctrl.UpdateDatas( url_classes_to_clear )
            
        
    
    def _Copy( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_tag_import_options:
                
                tag_import_options = self._url_class_keys_to_tag_import_options[ url_class_key ]
                
                json_string = tag_import_options.DumpToString()
                
                HG.client_controller.pub( 'clipboard', 'text', json_string )
                
            
        
    
    def _Edit( self ):
        
        url_classes_to_edit = self._list_ctrl.GetData( only_selected = True )
        
        for url_class in url_classes_to_edit:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag import options' ) as dlg:
                
                tag_import_options = self._GetDefaultTagImportOptions( url_class )
                show_downloader_options = True
                
                panel = EditTagImportOptionsPanel( dlg, tag_import_options, show_downloader_options )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    url_class_key = url_class.GetClassKey()
                    
                    tag_import_options = panel.GetValue()
                    
                    self._url_class_keys_to_tag_import_options[ url_class_key ] = tag_import_options
                    
                else:
                    
                    break
                    
                
            
        
        self._list_ctrl.UpdateDatas( url_classes_to_edit )
        
    
    def _GetDefaultTagImportOptions( self, url_class ):
        
        url_class_key = url_class.GetClassKey()
        
        if url_class_key in self._url_class_keys_to_tag_import_options:
            
            tag_import_options = self._url_class_keys_to_tag_import_options[ url_class_key ]
            
        else:
            
            url_type = url_class.GetURLType()
            
            if url_type == HC.URL_TYPE_POST:
                
                tag_import_options = self._file_post_default_tag_import_options_button.GetValue()
                
            elif url_type == HC.URL_TYPE_WATCHABLE:
                
                tag_import_options = self._watchable_default_tag_import_options_button.GetValue()
                
            else:
                
                raise HydrusExceptions.URLClassException( 'Could not find tag import options for that kind of URL Class!' )
                
            
        
        return tag_import_options
        
    
    def _OnlyOneTIOSelected( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetClassKey()
            
            if url_class_key in self._url_class_keys_to_tag_import_options:
                
                return True
                
            
        
        return False
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            tag_import_options = HydrusSerialisable.CreateFromString( raw_text )
            
            if not isinstance( tag_import_options, ClientImportOptions.TagImportOptions ):
                
                raise Exception( 'Not a Tag Import Options!' )
                
            
            for url_class in self._list_ctrl.GetData( only_selected = True ):
                
                url_class_key = url_class.GetClassKey()
                
                self._url_class_keys_to_tag_import_options[ url_class_key ] = tag_import_options.Duplicate()
                
            
            self._list_ctrl.UpdateDatas()
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
            HydrusData.ShowException( e )
            
        
    
    def GetValue( self ):
        
        file_post_default_tag_import_options = self._file_post_default_tag_import_options_button.GetValue()
        watchable_default_tag_import_options = self._watchable_default_tag_import_options_button.GetValue()
        
        return ( file_post_default_tag_import_options, watchable_default_tag_import_options, self._url_class_keys_to_tag_import_options )
        
    
class EditDeleteFilesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, media, default_reason, suggested_file_service_key = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._media = ClientMedia.FlattenMedia( media )
        
        self._question_is_already_resolved = False
        
        self._simple_description = ClientGUICommon.BetterStaticText( self, label = 'init' )
        
        self._permitted_action_choices = []
        
        self._InitialisePermittedActionChoices( suggested_file_service_key = suggested_file_service_key )
        
        self._action_radio = ClientGUICommon.BetterRadioBox( self, choices = self._permitted_action_choices, vertical = True )
        
        self._action_radio.Select( 0 )
        
        self._reason_panel = ClientGUICommon.StaticBox( self, 'reason' )
        
        permitted_reason_choices = []
        
        permitted_reason_choices.append( ( default_reason, default_reason ) )
        
        for s in HG.client_controller.new_options.GetStringList( 'advanced_file_deletion_reasons' ):
            
            permitted_reason_choices.append( ( s, s ) )
            
        
        permitted_reason_choices.append( ( 'custom', None ) )
        
        self._reason_radio = ClientGUICommon.BetterRadioBox( self._reason_panel, choices = permitted_reason_choices, vertical = True )
        
        self._reason_radio.Select( 0 )
        
        self._custom_reason = QW.QLineEdit( self._reason_panel )
        
        #
        
        ( file_service_key, hashes, description ) = self._action_radio.GetValue()
        
        self._simple_description.setText( description )
        
        if HG.client_controller.new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ):
            
            if len( self._permitted_action_choices ) == 1:
                
                self._action_radio.hide()
                
            else:
                
                self._simple_description.hide()
                
            
        else:
            
            self._action_radio.hide()
            self._reason_panel.hide()
            
        
        self._action_radio.radioBoxChanged.connect( self._UpdateControls )
        self._reason_radio.radioBoxChanged.connect( self._UpdateControls )
        
        self._UpdateControls()
        
        #
        
        self._reason_panel.Add( self._reason_radio, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'custom reason: ', self._custom_reason ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._reason_panel, rows )
        
        self._reason_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._simple_description, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._action_radio, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._reason_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def _GetReason( self ):
        
        reason = self._reason_radio.GetValue()
        
        if reason is None:
            
            reason = self._custom_reason.text()
            
        
        return reason
        
    
    def _InitialisePermittedActionChoices( self, suggested_file_service_key = None ):
        
        possible_file_service_keys = []
        
        if suggested_file_service_key is None:
            
            suggested_file_service_key = CC.LOCAL_FILE_SERVICE_KEY
            
        
        if suggested_file_service_key == CC.LOCAL_FILE_SERVICE_KEY:
            
            possible_file_service_keys.append( CC.LOCAL_FILE_SERVICE_KEY )
            possible_file_service_keys.append( CC.TRASH_SERVICE_KEY )
            possible_file_service_keys.append( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
        elif suggested_file_service_key == CC.TRASH_SERVICE_KEY:
            
            possible_file_service_keys.append( CC.TRASH_SERVICE_KEY )
            possible_file_service_keys.append( CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
            
        else:
            
            possible_file_service_keys.append( suggested_file_service_key )
            
        
        keys_to_hashes = { possible_file_service_key : [ m.GetHash() for m in self._media if possible_file_service_key in m.GetLocationsManager().GetCurrent() ] for possible_file_service_key in possible_file_service_keys }
        
        for possible_file_service_key in possible_file_service_keys:
            
            hashes = keys_to_hashes[ possible_file_service_key ]
            
            num_to_delete = len( hashes )
            
            if len( hashes ) > 0:
                
                if possible_file_service_key == CC.LOCAL_FILE_SERVICE_KEY:
                    
                    if not HC.options[ 'confirm_trash' ]:
                        
                        # this dialog will never show
                        self._question_is_already_resolved = True
                        
                    
                    if num_to_delete == 1: text = 'Send this file to the trash?'
                    else: text = 'Send these ' + HydrusData.ToHumanInt( num_to_delete ) + ' files to the trash?'
                    
                elif possible_file_service_key == CC.TRASH_SERVICE_KEY:
                    
                    if num_to_delete == 1: text = 'Permanently delete this file?'
                    else: text = 'Permanently delete these ' + HydrusData.ToHumanInt( num_to_delete ) + ' files?'
                    
                elif possible_file_service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
                    
                    # do a physical delete, skipping trash
                    # this is only a valid option when local delete has some values, but it applies to both local and trash, hence the combined local fsk
                    
                    if CC.LOCAL_FILE_SERVICE_KEY in keys_to_hashes and len( keys_to_hashes[ CC.LOCAL_FILE_SERVICE_KEY ] ) > 0:
                        
                        possible_file_service_key = 'physical_delete'
                        
                        if num_to_delete == 1: text = 'Permanently delete this file?'
                        else: text = 'Permanently delete these ' + HydrusData.ToHumanInt( num_to_delete ) + ' files?'
                        
                    else:
                        
                        continue
                        
                    
                else:
                    
                    if num_to_delete == 1: text = 'Admin-delete this file?'
                    else: text = 'Admin-delete these ' + HydrusData.ToHumanInt( num_to_delete ) + ' files?'
                    
                
                self._permitted_action_choices.append( ( text, ( possible_file_service_key, hashes, text ) ) )
                
            
        
        if HG.client_controller.new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ):
            
            hashes = [ m.GetHash() for m in self._media if CC.COMBINED_LOCAL_FILE_SERVICE_KEY in m.GetLocationsManager().GetCurrent() ]
            
            num_to_delete = len( hashes )
            
            if len( hashes ) > 0:
                
                if num_to_delete == 1:
                    
                    text = 'Permanently delete this file and do not save a deletion record?'
                    
                else:
                    
                    text = 'Permanently delete these ' + HydrusData.ToHumanInt( num_to_delete ) + ' files and do not save a deletion record?'
                    
                
                self._permitted_action_choices.append( ( text, ( 'clear_delete', hashes, text ) ) )
                
            
        
        if len( self._permitted_action_choices ) == 0:
            
            raise HydrusExceptions.CancelledException( 'No valid delete choices!' )
            
        
    
    def _UpdateControls( self ):
        
        ( file_service_key, hashes, description ) = self._action_radio.GetValue()
        
        reason_permitted = file_service_key in ( CC.LOCAL_FILE_SERVICE_KEY, 'physical_delete' )
        
        if reason_permitted:
            
            self._reason_radio.setEnabled( True )
            
        else:
            
            self._reason_radio.setEnabled( False )
            self._custom_reason.setEnabled( False )
            
        
        reason = self._reason_radio.GetValue()
        
        if reason is None:
            
            self._custom_reason.setEnabled( True )
            
        else:
            
            self._custom_reason.setEnabled( False )
            
        
    
    def GetValue( self ):
        
        involves_physical_delete = False
        
        ( file_service_key, hashes, description ) = self._action_radio.GetValue()
        
        reason = self._GetReason()
        
        local_file_services = ( CC.LOCAL_FILE_SERVICE_KEY, CC.TRASH_SERVICE_KEY )
        
        if file_service_key in local_file_services:
            
            # split them into bits so we don't hang the gui with a huge delete transaction
            
            chunks_of_hashes = HydrusData.SplitListIntoChunks( hashes, 64 )
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes, reason = reason ) for chunk_of_hashes in chunks_of_hashes ]
            
            jobs = [ { file_service_key : [ content_update ] } for content_update in content_updates ]
            
            if file_service_key == CC.TRASH_SERVICE_KEY:
                
                involves_physical_delete = True
                
            
        elif file_service_key == 'physical_delete':
            
            chunks_of_hashes = HydrusData.SplitListIntoChunks( hashes, 64 )
            
            jobs = []
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes, reason = reason ) for chunk_of_hashes in chunks_of_hashes ]
            
            jobs.extend( [ { CC.LOCAL_FILE_SERVICE_KEY : [ content_update ] } for content_update in content_updates ] )
            jobs.extend( [ { CC.TRASH_SERVICE_KEY: [ content_update ] } for content_update in content_updates ] )
            
            involves_physical_delete = True
            
        elif file_service_key == 'clear_delete':
            
            chunks_of_hashes = list( HydrusData.SplitListIntoChunks( hashes, 64 ) ) # iterator, so list it to use it more than once, jej
            
            jobs = []
            
            # no reason, since pointless
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, chunk_of_hashes ) for chunk_of_hashes in chunks_of_hashes ]
            
            jobs.extend( [ { CC.LOCAL_FILE_SERVICE_KEY : [ content_update ] } for content_update in content_updates ] )
            jobs.extend( [ { CC.TRASH_SERVICE_KEY: [ content_update ] } for content_update in content_updates ] )
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', chunk_of_hashes ) ) for chunk_of_hashes in chunks_of_hashes ]
            
            jobs.extend( [ { CC.COMBINED_LOCAL_FILE_SERVICE_KEY: [ content_update ] } for content_update in content_updates ] )
            
            involves_physical_delete = True
            
        else:
            
            content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes, reason = 'admin' ) ]
            
            jobs = [ { file_service_key : content_updates } ]
            
        
        return ( involves_physical_delete, jobs )
        
    
    def QuestionIsAlreadyResolved( self ):
        
        return self._question_is_already_resolved
        
    
class EditDuplicateActionOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, duplicate_action, duplicate_action_options, for_custom_action = False ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._duplicate_action = duplicate_action
        
        #
        
        tag_services_panel = ClientGUICommon.StaticBox( self, 'tag services' )
        
        tag_services_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( tag_services_panel )
        
        self._tag_service_actions = ClientGUIListCtrl.BetterListCtrl( tag_services_listctrl_panel, CGLC.COLUMN_LIST_DUPLICATE_ACTION_OPTIONS_TAG_SERVICES.ID, 5, self._ConvertTagDataToListCtrlTuple, delete_key_callback = self._DeleteTag, activation_callback = self._EditTag )
        
        tag_services_listctrl_panel.SetListCtrl( self._tag_service_actions )
        
        tag_services_listctrl_panel.AddButton( 'add', self._AddTag )
        tag_services_listctrl_panel.AddButton( 'edit', self._EditTag, enabled_only_on_selection = True )
        tag_services_listctrl_panel.AddButton( 'delete', self._DeleteTag, enabled_only_on_selection = True )
        
        #
        
        rating_services_panel = ClientGUICommon.StaticBox( self, 'rating services' )
        
        rating_services_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( rating_services_panel )
        
        self._rating_service_actions = ClientGUIListCtrl.BetterListCtrl( rating_services_listctrl_panel, CGLC.COLUMN_LIST_DUPLICATE_ACTION_OPTIONS_RATING_SERVICES.ID, 5, self._ConvertRatingDataToListCtrlTuple, delete_key_callback = self._DeleteRating, activation_callback = self._EditRating )
        
        rating_services_listctrl_panel.SetListCtrl( self._rating_service_actions )
        
        rating_services_listctrl_panel.AddButton( 'add', self._AddRating )
        if self._duplicate_action == HC.DUPLICATE_BETTER: # because there is only one valid action otherwise
            
            rating_services_listctrl_panel.AddButton( 'edit', self._EditRating, enabled_only_on_selection = True )
            
        rating_services_listctrl_panel.AddButton( 'delete', self._DeleteRating, enabled_only_on_selection = True )
        
        #
        
        self._sync_archive = QW.QCheckBox( self )
        
        self._sync_urls_action = ClientGUICommon.BetterChoice( self )
        
        self._sync_urls_action.addItem( 'sync nothing', None )
        
        if self._duplicate_action == HC.DUPLICATE_BETTER:
            
            self._sync_urls_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_COPY], HC.CONTENT_MERGE_ACTION_COPY )
            
        
        self._sync_urls_action.addItem( HC.content_merge_string_lookup[ HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE], HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE )
        
        #
        
        ( tag_service_options, rating_service_options, sync_archive, sync_urls_action ) = duplicate_action_options.ToTuple()
        
        services_manager = HG.client_controller.services_manager
        
        self._service_keys_to_tag_options = { service_key : ( action, tag_filter ) for ( service_key, action, tag_filter ) in tag_service_options if services_manager.ServiceExists( service_key ) }
        
        self._tag_service_actions.SetData( list( self._service_keys_to_tag_options.keys() ) )
        
        self._tag_service_actions.Sort()
        
        self._service_keys_to_rating_options = { service_key : action for ( service_key, action ) in rating_service_options if services_manager.ServiceExists( service_key ) }
        
        self._rating_service_actions.SetData( list( self._service_keys_to_rating_options.keys() ) )
        
        self._rating_service_actions.Sort()
        
        self._sync_archive.setChecked( sync_archive )
        
        #
        
        if self._duplicate_action in ( HC.DUPLICATE_ALTERNATE, HC.DUPLICATE_FALSE_POSITIVE ) and not for_custom_action:
            
            self._sync_urls_action.setEnabled( False )
            
            self._sync_urls_action.SetValue( None )
            
        else:
            
            self._sync_urls_action.SetValue( sync_urls_action )
            
        
        #
        
        tag_services_panel.Add( tag_services_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        rating_services_panel.Add( rating_services_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, tag_services_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, rating_services_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        rows = []
        
        rows.append( ( 'if one file is archived, archive the other as well: ', self._sync_archive ) )
        rows.append( ( 'sync known urls?: ', self._sync_urls_action ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def _AddRating( self ):
        
        services_manager = HG.client_controller.services_manager
        
        choice_tuples = []
        
        for service in services_manager.GetServices( ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ):
            
            service_key = service.GetServiceKey()
            
            if service_key not in self._service_keys_to_rating_options:
                
                name = service.GetName()
                
                choice_tuples.append( ( name, service_key ) )
                
            
        
        if len( choice_tuples ) == 0:
            
            QW.QMessageBox.critical( self, 'Error', 'You have no more tag or rating services to add! Try editing the existing ones instead!' )
            
        else:
            
            try:
                
                service_key = ClientGUIDialogsQuick.SelectFromList( self, 'select service', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                service = services_manager.GetService( service_key )
                
                if service.GetServiceType() == HC.TAG_REPOSITORY:
                    
                    possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                    
                else:
                    
                    possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                    
                
                choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            else:
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            self._service_keys_to_rating_options[ service_key ] = action
            
            self._rating_service_actions.AddDatas( ( service_key, ) )
            
            self._rating_service_actions.Sort()
            
        
    
    def _AddTag( self ):
        
        services_manager = HG.client_controller.services_manager
        
        choice_tuples = []
        
        for service in services_manager.GetServices( HC.REAL_TAG_SERVICES ):
            
            service_key = service.GetServiceKey()
            
            if service_key not in self._service_keys_to_tag_options:
                
                name = service.GetName()
                
                choice_tuples.append( ( name, service_key ) )
                
            
        
        if len( choice_tuples ) == 0:
            
            QW.QMessageBox.critical( self, 'Error', 'You have no more tag or rating services to add! Try editing the existing ones instead!' )
            
        else:
            
            try:
                
                service_key = ClientGUIDialogsQuick.SelectFromList( self, 'select service', choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                service = services_manager.GetService( service_key )
                
                if service.GetServiceType() == HC.TAG_REPOSITORY:
                    
                    possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                    
                else:
                    
                    possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                    
                
                choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            else:
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            tag_filter = ClientTags.TagFilter()
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
                
                namespaces = HG.client_controller.network_engine.domain_manager.GetParserNamespaces()
                
                panel = ClientGUITags.EditTagFilterPanel( dlg_3, tag_filter, namespaces = namespaces )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.exec() == QW.QDialog.Accepted:
                    
                    tag_filter = panel.GetValue()
                    
                    self._service_keys_to_tag_options[ service_key ] = ( action, tag_filter )
                    
                    self._tag_service_actions.AddDatas( ( service_key, ) )
                    
                    self._tag_service_actions.Sort()
                    
                
            
        
    
    def _ConvertRatingDataToListCtrlTuple( self, service_key ):
        
        action = self._service_keys_to_rating_options[ service_key ]
        
        try:
            
            service_name = HG.client_controller.services_manager.GetName( service_key )
            
        except HydrusExceptions.DataMissing:
            
            service_name = 'missing service!'
            
        
        pretty_action = HC.content_merge_string_lookup[ action ]
        
        display_tuple = ( service_name, pretty_action )
        sort_tuple = ( service_name, pretty_action )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertTagDataToListCtrlTuple( self, service_key ):
        
        ( action, tag_filter ) = self._service_keys_to_tag_options[ service_key ]
        
        try:
            
            service_name = HG.client_controller.services_manager.GetName( service_key )
            
        except HydrusExceptions.DataMissing:
            
            service_name = 'missing service!'
            
        
        pretty_action = HC.content_merge_string_lookup[ action ]
        pretty_tag_filter = tag_filter.ToPermittedString()
        
        display_tuple = ( service_name, pretty_action, pretty_tag_filter )
        sort_tuple = ( service_name, pretty_action, pretty_tag_filter )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteRating( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            for service_key in self._rating_service_actions.GetData( only_selected = True ):
                
                del self._service_keys_to_rating_options[ service_key ]
                
            
            self._rating_service_actions.DeleteSelected()
            
        
    
    def _DeleteTag( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            for service_key in self._tag_service_actions.GetData( only_selected = True ):
                
                del self._service_keys_to_tag_options[ service_key ]
                
            
            self._tag_service_actions.DeleteSelected()
            
        
    
    def _EditRating( self ):
        
        service_keys = self._rating_service_actions.GetData( only_selected = True )
        
        for service_key in service_keys:
            
            action = self._service_keys_to_rating_options[ service_key ]
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
                choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    break
                    
                
            else: # This shouldn't get fired because the edit button is hidden, but w/e
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            self._service_keys_to_rating_options[ service_key ] = action
            
            self._rating_service_actions.UpdateDatas( ( service_key, ) )
            
            self._rating_service_actions.Sort()
            
        
    
    def _EditTag( self ):
        
        service_keys = self._tag_service_actions.GetData( only_selected = True )
        
        for service_key in service_keys:
            
            ( action, tag_filter ) = self._service_keys_to_tag_options[ service_key ]
            
            if self._duplicate_action == HC.DUPLICATE_BETTER:
                
                possible_actions = [ HC.CONTENT_MERGE_ACTION_COPY, HC.CONTENT_MERGE_ACTION_MOVE, HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE ]
                
                choice_tuples = [ ( HC.content_merge_string_lookup[ action ], action ) for action in possible_actions ]
                
                try:
                    
                    action = ClientGUIDialogsQuick.SelectFromList( self, 'select action', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    break
                    
                
            else:
                
                action = HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE
                
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
                
                namespaces = HG.client_controller.network_engine.domain_manager.GetParserNamespaces()
                
                panel = ClientGUITags.EditTagFilterPanel( dlg_3, tag_filter, namespaces = namespaces )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.exec() == QW.QDialog.Accepted:
                    
                    tag_filter = panel.GetValue()
                    
                    self._service_keys_to_tag_options[ service_key ] = ( action, tag_filter )
                    
                    self._tag_service_actions.UpdateDatas( ( service_key, ) )
                    
                    self._tag_service_actions.Sort()
                    
                else:
                    
                    break
                    
                
            
        
    
    def GetValue( self ) -> ClientDuplicates.DuplicateActionOptions:
        
        tag_service_actions = [ ( service_key, action, tag_filter ) for ( service_key, ( action, tag_filter ) ) in self._service_keys_to_tag_options.items() ]
        rating_service_actions = [ ( service_key, action ) for ( service_key, action ) in self._service_keys_to_rating_options.items() ]
        sync_archive = self._sync_archive.isChecked()
        sync_urls_action = self._sync_urls_action.GetValue()
        
        duplicate_action_options = ClientDuplicates.DuplicateActionOptions( tag_service_actions, rating_service_actions, sync_archive, sync_urls_action )
        
        return duplicate_action_options
        
    
class EditFileImportOptions( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, file_import_options: ClientImportOptions.FileImportOptions, show_downloader_options: bool ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowHelp )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', QG.QColor( 0, 0, 255 ) )
        
        #
        
        pre_import_panel = ClientGUICommon.StaticBox( self, 'pre-import checks' )
        
        self._exclude_deleted = QW.QCheckBox( pre_import_panel )
        
        self._do_not_check_known_urls_before_importing = QW.QCheckBox( pre_import_panel )
        self._do_not_check_hashes_before_importing = QW.QCheckBox( pre_import_panel )
        
        tt = 'If hydrus recognises a file\'s URL or hash, it can decide to skip downloading it if it believes it already has it or previously deleted it.'
        tt += os.linesep * 2
        tt += 'This is usually a great way to reduce bandwidth, but if you believe the clientside url mappings or serverside hashes are inaccurate and the file is being wrongly skipped, turn these on to force a download.'
        
        self._do_not_check_known_urls_before_importing.setToolTip( tt )
        self._do_not_check_hashes_before_importing.setToolTip( tt )
        
        self._allow_decompression_bombs = QW.QCheckBox( pre_import_panel )
        
        self._min_size = ClientGUIControls.NoneableBytesControl( pre_import_panel )
        self._min_size.SetValue( 5 * 1024 )
        
        self._max_size = ClientGUIControls.NoneableBytesControl( pre_import_panel )
        self._max_size.SetValue( 100 * 1024 * 1024 )
        
        self._max_gif_size = ClientGUIControls.NoneableBytesControl( pre_import_panel )
        self._max_gif_size.SetValue( 32 * 1024 * 1024 )
        
        self._min_resolution = ClientGUICommon.NoneableSpinCtrl( pre_import_panel, num_dimensions = 2 )
        self._min_resolution.SetValue( ( 50, 50 ) )
        
        self._max_resolution = ClientGUICommon.NoneableSpinCtrl( pre_import_panel, num_dimensions = 2 )
        self._max_resolution.SetValue( ( 8192, 8192 ) )
        
        #
        
        post_import_panel = ClientGUICommon.StaticBox( self, 'post-import actions' )
        
        self._auto_archive = QW.QCheckBox( post_import_panel )
        self._associate_source_urls = QW.QCheckBox( post_import_panel )
        
        tt = 'If the parser discovers and additional source URL for another site (e.g. "This file on wewbooru was originally posted to Bixiv [here]."), should that URL be associated with the final URL? Should it be trusted to make \'already in db/previously deleted\' determinations?'
        tt += os.linesep * 2
        tt += 'You should turn this off if the site supplies bad (incorrect or imprecise or malformed) source urls.'
        
        self._associate_source_urls.setToolTip( tt )
        
        #
        
        presentation_panel = ClientGUICommon.StaticBox( self, 'presentation options' )
        
        self._present_new_files = QW.QCheckBox( presentation_panel )
        self._present_already_in_inbox_files = QW.QCheckBox( presentation_panel )
        self._present_already_in_archive_files = QW.QCheckBox( presentation_panel )
        
        #
        
        ( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution ) = file_import_options.GetPreImportOptions()
        
        self._exclude_deleted.setChecked( exclude_deleted )
        self._do_not_check_known_urls_before_importing.setChecked( do_not_check_known_urls_before_importing )
        self._do_not_check_hashes_before_importing.setChecked( do_not_check_hashes_before_importing )
        self._allow_decompression_bombs.setChecked( allow_decompression_bombs )
        self._min_size.SetValue( min_size )
        self._max_size.SetValue( max_size )
        self._max_gif_size.SetValue( max_gif_size )
        self._min_resolution.SetValue( min_resolution )
        self._max_resolution.SetValue( max_resolution )
        
        #
        
        ( automatic_archive, associate_source_urls ) = file_import_options.GetPostImportOptions()
        
        self._auto_archive.setChecked( automatic_archive )
        self._associate_source_urls.setChecked( associate_source_urls )
        
        #
        
        ( present_new_files, present_already_in_inbox_files, present_already_in_archive_files ) = file_import_options.GetPresentationOptions()
        
        self._present_new_files.setChecked( present_new_files )
        self._present_already_in_inbox_files.setChecked( present_already_in_inbox_files )
        self._present_already_in_archive_files.setChecked( present_already_in_archive_files )
        
        #
        
        rows = []
        
        rows.append( ( 'exclude previously deleted files: ', self._exclude_deleted ) )
        
        if show_downloader_options and HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            rows.append( ( 'do not skip downloading because of known urls: ', self._do_not_check_known_urls_before_importing ) )
            rows.append( ( 'do not skip downloading because of hashes: ', self._do_not_check_hashes_before_importing ) )
            
        else:
            
            self._do_not_check_known_urls_before_importing.setVisible( False )
            self._do_not_check_hashes_before_importing.setVisible( False )
            
        
        rows.append( ( 'allow decompression bombs: ', self._allow_decompression_bombs ) )
        rows.append( ( 'minimum filesize: ', self._min_size ) )
        rows.append( ( 'maximum filesize: ', self._max_size ) )
        rows.append( ( 'maximum gif filesize: ', self._max_gif_size ) )
        rows.append( ( 'minimum resolution: ', self._min_resolution ) )
        rows.append( ( 'maximum resolution: ', self._max_resolution ) )
        
        gridbox = ClientGUICommon.WrapInGrid( pre_import_panel, rows )
        
        pre_import_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'archive all imports: ', self._auto_archive ) )
        
        if show_downloader_options and HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            rows.append( ( 'associate (and trust) additional source urls: ', self._associate_source_urls ) )
            
        else:
            
            self._associate_source_urls.setVisible( False )
            
        
        gridbox = ClientGUICommon.WrapInGrid( post_import_panel, rows )
        
        post_import_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'present new files', self._present_new_files ) )
        rows.append( ( 'present \'already in db\' files in inbox', self._present_already_in_inbox_files ) )
        rows.append( ( 'present \'already in db\' files in archive', self._present_already_in_archive_files ) )
        
        gridbox = ClientGUICommon.WrapInGrid( presentation_panel, rows )
        
        presentation_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, pre_import_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, post_import_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, presentation_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def _ShowHelp( self ):
        
        help_message = '''-exclude previously deleted files-

If this is set and an incoming file has already been seen and deleted before by this client, the import will be abandoned. This is useful to make sure you do not keep importing and deleting the same bad files over and over. Files currently in the trash count as deleted.

-allow decompression bombs-

Some images, called Decompression Bombs, consume huge amounts of memory and CPU time (typically multiple GB and 30s+) to render. These can be malicious attacks or accidentally inelegant compressions of very large images (typically 100MegaPixel+ pngs). Keep this unchecked to catch and disallow them before they blat your computer.

-max gif size-

Some artists and over-enthusiastic fans re-encode popular webms into gif, typically so they can be viewed on simpler platforms like older phones. These people do not know what they are doing and generate 20MB, 100MB, even 220MB(!) gif files that they then upload to the boorus. Most hydrus users do not want these duplicate, bloated, bad-paletted, and CPU-laggy files on their clients, so this can probit them.

-archive all imports-

If this is set, all successful imports will be archived rather than sent to the inbox. This applies to files 'already in db' as well (these would otherwise retain their existing inbox status unaltered).

-presentation options-

For regular import pages, 'presentation' means if the imported file's thumbnail will be added. For quieter queues like subscriptions, it determines if the file will be in any popup message button.

If you have a very large (10k+ files) file import page, consider hiding some or all of its thumbs to reduce ui lag and increase overall import speed.'''
        
        QW.QMessageBox.information( self, 'Information', help_message )
        
    
    def GetValue( self ) -> ClientImportOptions.FileImportOptions:
        
        exclude_deleted = self._exclude_deleted.isChecked()
        do_not_check_known_urls_before_importing = self._do_not_check_known_urls_before_importing.isChecked()
        do_not_check_hashes_before_importing = self._do_not_check_hashes_before_importing.isChecked()
        allow_decompression_bombs = self._allow_decompression_bombs.isChecked()
        min_size = self._min_size.GetValue()
        max_size = self._max_size.GetValue()
        max_gif_size = self._max_gif_size.GetValue()
        min_resolution = self._min_resolution.GetValue()
        max_resolution = self._max_resolution.GetValue()
        
        automatic_archive = self._auto_archive.isChecked()
        associate_source_urls = self._associate_source_urls.isChecked()
        
        present_new_files = self._present_new_files.isChecked()
        present_already_in_inbox_files = self._present_already_in_inbox_files.isChecked()
        present_already_in_archive_files = self._present_already_in_archive_files.isChecked()
        
        file_import_options = ClientImportOptions.FileImportOptions()
        
        file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        file_import_options.SetPostImportOptions( automatic_archive, associate_source_urls )
        file_import_options.SetPresentationOptions( present_new_files, present_already_in_inbox_files, present_already_in_archive_files )
        
        return file_import_options
        
    
class EditFileNotesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, names_to_notes: typing.Dict[ str, str ] ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_names = set()
        
        self._notebook = QW.QTabWidget( self )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._notebook, ( 80, 14 ) )
        
        self._notebook.setMinimumSize( min_width, min_height )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._AddNote )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit current name', self._EditName )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete current note', self._DeleteNote )
        
        #
        
        if len( names_to_notes ) == 0:
            
            self._AddNotePanel( 'notes', '' )
            
        else:
            
            names = sorted( names_to_notes.keys() )
            
            for name in names:
                
                note = names_to_notes[ name ]
                
                self._original_names.add( name )
                
                self._AddNotePanel( name, note )
                
            
        
        first_panel = self._notebook.widget( 0 )
        
        self._notebook.setCurrentIndex( 0 )
        
        HG.client_controller.CallAfterQtSafe( first_panel, first_panel.setFocus, QC.Qt.OtherFocusReason )
        HG.client_controller.CallAfterQtSafe( first_panel, first_panel.moveCursor, QG.QTextCursor.End )
        
        #
        
        button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( button_hbox, self._add_button )
        QP.AddToLayout( button_hbox, self._edit_button )
        QP.AddToLayout( button_hbox, self._delete_button )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, button_hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media' ] )
        
    
    def _AddNote( self ):
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        existing_names = set( names_to_notes.keys() )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the name for the note.', allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                name = dlg.GetValue()
                
                name = HydrusData.GetNonDupeName( name, existing_names )
                
                self._AddNotePanel( name, '' )
                
            
        
    
    def _AddNotePanel( self, name, note ):
        
        control = QW.QPlainTextEdit( self._notebook )
        
        control.setPlainText( note )
        
        self._notebook.addTab( control, name )
        
        self._notebook.setCurrentWidget( control )
        
        HG.client_controller.CallAfterQtSafe( control, control.setFocus, QC.Qt.OtherFocusReason )
        HG.client_controller.CallAfterQtSafe( control, control.moveCursor, QG.QTextCursor.End )
        
        self._UpdateButtons()
        
    
    def _DeleteNote( self ):
        
        text = 'Delete this note?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.Accepted:
            
            index = self._notebook.currentIndex()
            
            panel = self._notebook.currentWidget()
            
            self._notebook.removeTab( index )
            
            panel.deleteLater()
            
            self._UpdateButtons()
            
        
    
    def _EditName( self ):
        
        index = self._notebook.currentIndex()
        
        name = self._notebook.tabText( index )
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        existing_names = set( names_to_notes.keys() )
        
        existing_names.discard( name )
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter the name for the note.', allow_blank = False, default = name ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                name = dlg.GetValue()
                
                name = HydrusData.GetNonDupeName( name, existing_names )
                
                self._notebook.setTabText( index, name )
                
            
        
    
    def _UpdateButtons( self ):
        
        can_edit = self._notebook.count() > 0
        
        self._edit_button.setEnabled( can_edit )
        self._delete_button.setEnabled( can_edit )
        
    
    def GetValue( self ) -> typing.Tuple[ typing.Dict[ str, str ], typing.Set[ str ] ]:
        
        names_to_notes = { self._notebook.tabText( i ) : self._notebook.widget( i ).toPlainText() for i in range( self._notebook.count() ) }
        
        deletee_names = { name for name in self._original_names if name not in names_to_notes }
        
        return ( names_to_notes, deletee_names )
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        data = command.GetData()
        
        if command.IsSimpleCommand():
            
            action = data
            
            if action == CAC.SIMPLE_MANAGE_FILE_NOTES:
                
                self._OKParent()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    def UserIsOKToOK( self ):
        
        ( names_to_notes, deletee_names ) = self.GetValue()
        
        empty_note_names = sorted( ( name for ( name, note ) in names_to_notes.items() if note == '' ) )
        
        if len( empty_note_names ) > 0:
            
            message = 'These notes are empty, and will not be saved--is this ok?'
            message += os.linesep * 2
            message += ', '.join( empty_note_names )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return False
                
            
        
        return True
        
    
class EditFrameLocationPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, info ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_info = info
        
        self._remember_size = QW.QCheckBox( 'remember size', self )
        self._remember_position = QW.QCheckBox( 'remember position', self )
        
        self._last_size = ClientGUICommon.NoneableSpinCtrl( self, 'last size', none_phrase = 'none set', min = 100, max = 1000000, unit = None, num_dimensions = 2 )
        self._last_position = ClientGUICommon.NoneableSpinCtrl( self, 'last position', none_phrase = 'none set', min = -1000000, max = 1000000, unit = None, num_dimensions = 2 )
        
        self._default_gravity_x = ClientGUICommon.BetterChoice( self )
        
        self._default_gravity_x.addItem( 'by default, expand to width of parent', 1 )
        self._default_gravity_x.addItem( 'by default, expand width as much as needed', -1 )
        
        self._default_gravity_y = ClientGUICommon.BetterChoice( self )
        
        self._default_gravity_y.addItem( 'by default, expand to height of parent', 1 )
        self._default_gravity_y.addItem( 'by default, expand height as much as needed', -1 )
        
        self._default_position = ClientGUICommon.BetterChoice( self )
        
        self._default_position.addItem( 'by default, position off the top-left corner of parent', 'topleft')
        self._default_position.addItem( 'by default, position centered on the parent', 'center')
        
        self._maximised = QW.QCheckBox( 'start maximised', self )
        self._fullscreen = QW.QCheckBox( 'start fullscreen', self )
        
        #
        
        ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = self._original_info
        
        self._remember_size.setChecked( remember_size )
        self._remember_position.setChecked( remember_position )
        
        self._last_size.SetValue( last_size )
        self._last_position.SetValue( last_position )
        
        ( x, y ) = default_gravity
        
        self._default_gravity_x.SetValue( x )
        self._default_gravity_y.SetValue( y )
        
        self._default_position.SetValue( default_position )
        
        self._maximised.setChecked( maximised )
        self._fullscreen.setChecked( fullscreen )
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'Setting frame location info for ' + name + '.'
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._remember_size, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._remember_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._last_size, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._last_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._default_gravity_x, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._default_gravity_y, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._default_position, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._maximised, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._fullscreen, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = self._original_info
        
        remember_size = self._remember_size.isChecked()
        remember_position = self._remember_position.isChecked()
        
        last_size = self._last_size.GetValue()
        last_position = self._last_position.GetValue()
        
        x = self._default_gravity_x.GetValue()
        y = self._default_gravity_y.GetValue()
        
        default_gravity = [ x, y ]
        
        default_position = self._default_position.GetValue()
        
        maximised = self._maximised.isChecked()
        fullscreen = self._fullscreen.isChecked()
        
        return ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
        
    
class EditMediaViewOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, info ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_info = info
        
        ( self._mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality ) ) = self._original_info
        
        ( possible_show_actions, can_start_paused, can_start_with_embed ) = CC.media_viewer_capabilities[ self._mime ]
        
        self._media_show_action = ClientGUICommon.BetterChoice( self )
        self._media_start_paused = QW.QCheckBox( self )
        self._media_start_with_embed = QW.QCheckBox( self )
        self._preview_show_action = ClientGUICommon.BetterChoice( self )
        self._preview_start_paused = QW.QCheckBox( self )
        self._preview_start_with_embed = QW.QCheckBox( self )
        
        for action in possible_show_actions:
            
            if action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV and not ClientGUIMPV.MPV_IS_AVAILABLE:
                
                continue
                
            
            s = CC.media_viewer_action_string_lookup[ action ]
            
            if action == CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV and self._mime in ( HC.IMAGE_GIF, HC.GENERAL_ANIMATION ):
                
                s += ' (will show image gifs with native viewer)'
                
            
            self._media_show_action.addItem( s, action )
            
            if action != CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY:
                
                self._preview_show_action.addItem( s, action )
                
            
        
        self._media_show_action.currentIndexChanged.connect( self.EventActionChange )
        self._preview_show_action.currentIndexChanged.connect( self.EventActionChange )
        
        self._media_scale_up = ClientGUICommon.BetterChoice( self )
        self._media_scale_down = ClientGUICommon.BetterChoice( self )
        self._preview_scale_up = ClientGUICommon.BetterChoice( self )
        self._preview_scale_down = ClientGUICommon.BetterChoice( self )
        
        for scale_action in ( CC.MEDIA_VIEWER_SCALE_100, CC.MEDIA_VIEWER_SCALE_MAX_REGULAR, CC.MEDIA_VIEWER_SCALE_TO_CANVAS ):
            
            text = CC.media_viewer_scale_string_lookup[ scale_action ]
            
            self._media_scale_up.addItem( text, scale_action )
            self._preview_scale_up.addItem( text, scale_action )
            
            self._media_scale_down.addItem( text, scale_action )
            self._preview_scale_down.addItem( text, scale_action )
            
        
        self._exact_zooms_only = QW.QCheckBox( 'only permit half and double zooms', self )
        self._exact_zooms_only.setToolTip( 'This limits zooms to 25%, 50%, 100%, 200%, 400%, and so on. It makes for fast resize and is useful for files that often have flat colours and hard edges, which often scale badly otherwise. The \'canvas fit\' zoom will still be inserted.' )
        
        self._scale_up_quality = ClientGUICommon.BetterChoice( self )
        
        for zoom in ( CC.ZOOM_NEAREST, CC.ZOOM_LINEAR, CC.ZOOM_CUBIC, CC.ZOOM_LANCZOS4 ):
            
            self._scale_up_quality.addItem( CC.zoom_string_lookup[ zoom], zoom )
            
        
        self._scale_down_quality = ClientGUICommon.BetterChoice( self )
        
        for zoom in ( CC.ZOOM_NEAREST, CC.ZOOM_LINEAR, CC.ZOOM_AREA ):
            
            self._scale_down_quality.addItem( CC.zoom_string_lookup[ zoom], zoom )
            
        
        #
        
        self._media_show_action.SetValue( media_show_action )
        self._media_start_paused.setChecked( media_start_paused )
        self._media_start_with_embed.setChecked( media_start_with_embed )
        
        self._preview_show_action.SetValue( preview_show_action )
        self._preview_start_paused.setChecked( preview_start_paused )
        self._preview_start_with_embed.setChecked( preview_start_with_embed )
        
        self._media_scale_up.SetValue( media_scale_up )
        self._media_scale_down.SetValue( media_scale_down )
        self._preview_scale_up.SetValue( preview_scale_up )
        self._preview_scale_down.SetValue( preview_scale_down )
        
        self._exact_zooms_only.setChecked( exact_zooms_only )
        
        self._scale_up_quality.SetValue( scale_up_quality )
        self._scale_down_quality.SetValue( scale_down_quality )
        
        #
        
        vbox = QP.VBoxLayout()
        
        text = 'Setting media view options for ' + HC.mime_string_lookup[ self._mime ] + '.'
        
        if not ClientGUIMPV.MPV_IS_AVAILABLE:
            
            text += ' MPV is not available for this client.'
            
        
        QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'media viewer show action: ', self._media_show_action ) )
        rows.append( ( 'media starts paused: ', self._media_start_paused ) )
        rows.append( ( 'media starts covered with an embed button: ', self._media_start_with_embed ) )
        rows.append( ( 'preview viewer show action: ', self._preview_show_action ) )
        rows.append( ( 'preview starts paused: ', self._preview_start_paused ) )
        rows.append( ( 'preview starts covered with an embed button: ', self._preview_start_with_embed ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if set( possible_show_actions ).isdisjoint( { CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV } ):
            
            self._media_scale_up.hide()
            self._media_scale_down.hide()
            self._preview_scale_up.hide()
            self._preview_scale_down.hide()
            
            self._exact_zooms_only.setVisible( False )
            
            self._scale_up_quality.hide()
            self._scale_down_quality.hide()
            
        else:
            
            rows = []
            
            rows.append( ( 'if the media is smaller than the media viewer canvas: ', self._media_scale_up ) )
            rows.append( ( 'if the media is larger than the media viewer canvas: ', self._media_scale_down ) )
            rows.append( ( 'if the media is smaller than the preview canvas: ', self._preview_scale_up) )
            rows.append( ( 'if the media is larger than the preview canvas: ', self._preview_scale_down ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, self._exact_zooms_only, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, 'Nearest neighbour is fast and ugly, 8x8 lanczos and area resampling are slower but beautiful.' ), CC.FLAGS_CENTER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._scale_up_quality, self, '>100% (interpolation) quality:' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText( self._scale_down_quality, self, '<100% (decimation) quality:' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        if self._mime == HC.APPLICATION_FLASH:
            
            self._scale_up_quality.setEnabled( False )
            self._scale_down_quality.setEnabled( False )
            
        
        self.widget().setLayout( vbox )
        
        self._UpdateControls()
        
    
    def _UpdateControls( self ):
        
        media_ok = self._media_show_action.GetValue() not in CC.unsupported_media_actions
        preview_ok = self._preview_show_action.GetValue() not in CC.unsupported_media_actions
        
        if media_ok or preview_ok:
            
            self._exact_zooms_only.setEnabled( True )
            
            self._scale_up_quality.setEnabled( True )
            self._scale_down_quality.setEnabled( True )
            
        else:
            
            self._exact_zooms_only.setEnabled( False )
            
            self._scale_up_quality.setEnabled( False )
            self._scale_down_quality.setEnabled( False )
            
        
        if media_ok:
            
            self._media_scale_up.setEnabled( True )
            self._media_scale_down.setEnabled( True )
            
            self._media_start_paused.setEnabled( True )
            self._media_start_with_embed.setEnabled( True )
            
        else:
            
            self._media_scale_up.setEnabled( False )
            self._media_scale_down.setEnabled( False )
            
            self._media_start_paused.setEnabled( False )
            self._media_start_with_embed.setEnabled( False )
            
        
        if preview_ok:
            
            self._preview_scale_up.setEnabled( True )
            self._preview_scale_down.setEnabled( True )
            
            self._preview_start_paused.setEnabled( True )
            self._preview_start_with_embed.setEnabled( True )
            
        else:
            
            self._preview_scale_up.setEnabled( False )
            self._preview_scale_down.setEnabled( False )
            
            self._preview_start_paused.setEnabled( False )
            self._preview_start_with_embed.setEnabled( False )
            
        
        is_application = self._mime == HC.GENERAL_APPLICATION or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_APPLICATION ]
        is_image = self._mime == HC.GENERAL_IMAGE or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_IMAGE ]
        is_audio = self._mime == HC.GENERAL_AUDIO or self._mime in HC.general_mimetypes_to_mime_groups[ HC.GENERAL_AUDIO ]
        
        if not is_image:
            
            self._scale_up_quality.setEnabled( False )
            self._scale_down_quality.setEnabled( False )
            
        
        if is_image or is_application:
            
            self._media_start_paused.setEnabled( False )
            self._preview_start_paused.setEnabled( False )
            
        
        if is_audio:
            
            self._media_scale_up.setEnabled( False )
            self._media_scale_down.setEnabled( False )
            self._preview_scale_up.setEnabled( False )
            self._preview_scale_down.setEnabled( False )
            
        
    
    def EventActionChange( self, index ):
        
        self._UpdateControls()
        
    
    def GetValue( self ):
        
        media_show_action = self._media_show_action.GetValue()
        media_start_paused = self._media_start_paused.isChecked()
        media_start_with_embed = self._media_start_with_embed.isChecked()
        
        preview_show_action = self._preview_show_action.GetValue()
        preview_start_paused = self._preview_start_paused.isChecked()
        preview_start_with_embed = self._preview_start_with_embed.isChecked()
        
        media_scale_up = self._media_scale_up.GetValue()
        media_scale_down = self._media_scale_down.GetValue()
        preview_scale_up = self._preview_scale_up.GetValue()
        preview_scale_down = self._preview_scale_down.GetValue()
        
        exact_zooms_only = self._exact_zooms_only.isChecked()
        
        scale_up_quality = self._scale_up_quality.GetValue()
        scale_down_quality = self._scale_down_quality.GetValue()
        
        zoom_info = ( media_scale_up, media_scale_down, preview_scale_up, preview_scale_down, exact_zooms_only, scale_up_quality, scale_down_quality )
        
        return ( self._mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info )
        
    
class EditNoneableIntegerPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, value: HC.noneable_int, message = '', none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1, num_dimensions = 1 ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._value = ClientGUICommon.NoneableSpinCtrl( self, message = message, none_phrase = none_phrase, min = min, max = max, unit = unit, multiplier = multiplier, num_dimensions = num_dimensions )
        
        self._value.SetValue( value )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._value, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ) -> HC.noneable_int:
        
        return self._value.GetValue()
        
    
class EditRegexFavourites( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, regex_favourites ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        regex_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._regexes = ClientGUIListCtrl.BetterListCtrl( regex_listctrl_panel, CGLC.COLUMN_LIST_REGEX_FAVOURITES.ID, 8, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        regex_listctrl_panel.SetListCtrl( self._regexes )
        
        regex_listctrl_panel.AddButton( 'add', self._Add )
        regex_listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        regex_listctrl_panel.AddDeleteButton()
        
        #
        
        self._regexes.SetData( regex_favourites )
        
        self._regexes.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, regex_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        current_data = self._regexes.GetData()
        
        with ClientGUIDialogs.DialogTextEntry( self, 'Enter regex.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                regex_phrase = dlg.GetValue()
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter description.' ) as dlg_2:
                    
                    if dlg_2.exec() == QW.QDialog.Accepted:
                        
                        description = dlg_2.GetValue()
                        
                        row = ( regex_phrase, description )
                        
                        if row in current_data:
                            
                            QW.QMessageBox.warning( self, 'Warning', 'That regex and description are already in the list!' )
                            
                            return
                            
                        
                        self._regexes.AddDatas( ( row, ) )
                        
                    
                
            
        
    
    def _ConvertDataToListCtrlTuples( self, row ):
        
        ( regex_phrase, description ) = row
        
        display_tuple = ( regex_phrase, description )
        sort_tuple = ( regex_phrase, description )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        rows = self._regexes.GetData( only_selected = True )
        
        for row in rows:
            
            ( regex_phrase, description ) = row
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Update regex.', default = regex_phrase ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    regex_phrase = dlg.GetValue()
                    
                    with ClientGUIDialogs.DialogTextEntry( self, 'Update description.', default = description ) as dlg_2:
                        
                        if dlg_2.exec() == QW.QDialog.Accepted:
                            
                            description = dlg_2.GetValue()
                            
                            edited_row = ( regex_phrase, description )
                            
                            self._regexes.DeleteDatas( ( row, ) )
                            
                            self._regexes.AddDatas( ( edited_row, ) )
                            
                        
                    
                else:
                    
                    break
                    
                
            
        
        self._regexes.Sort()
        
    
    def GetValue( self ):
        
        return self._regexes.GetData()
        
    
class EditTagImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, tag_import_options: ClientImportOptions.TagImportOptions, show_downloader_options: bool, allow_default_selection: bool = False ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._show_downloader_options = show_downloader_options
        
        self._service_keys_to_service_tag_import_options_panels = {}
        
        #
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowHelp )
        help_button.setToolTip( 'Show help regarding these tag options.' )
        
        #
        
        default_panel = ClientGUICommon.StaticBox( self, 'default options' )
        
        self._is_default = QW.QCheckBox( default_panel )
        
        tt = 'If this is checked, the client will refer to the defaults (as set under "network->downloaders->manage default tag import options") for the appropriate tag import options at the time of import.'
        tt += os.linesep * 2
        tt += 'It is easier to manage tag import options by relying on the defaults, since any change in the single default location will update all the eventual import queues that refer to those defaults, whereas having specific options for every subscription or downloader means making an update to the blacklist or tag filter needs to be repeated dozens or hundreds of times.'
        tt += os.linesep * 2
        tt += 'But if you are doing a one-time import that has some unusual tag rules, uncheck this and set those specific rules here.'
        
        self._is_default.setToolTip( tt )
        
        self._load_default_options = ClientGUICommon.BetterButton( default_panel, 'load one of the default options', self._LoadDefaultOptions )
        
        #
        
        self._specific_options_panel = QW.QWidget( self )
        
        #
        
        downloader_options_panel = ClientGUICommon.StaticBox( self._specific_options_panel, 'fetch options' )
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db = QW.QCheckBox( downloader_options_panel )
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db = QW.QCheckBox( downloader_options_panel )
        
        tag_blacklist = tag_import_options.GetTagBlacklist()
        
        message = 'If a file about to be downloaded has a tag on the site that this blacklist blocks, the file will not be downloaded and imported. If you want to stop \'scat\' or \'gore\', just type them into the list.'
        message += os.linesep * 2
        message += 'This system tests the all tags that are parsed from the site, not any other tags the files may have in different places. Siblings of all those tags will also be tested. If none of your tag services have excellent siblings, it is worth adding multiple versions of your tag, just to catch different sites terms. Link up \'gore\', \'guro\', \'violence\', etc...'
        message += os.linesep * 2
        message += 'Additionally, unnamespaced rules will apply to namespaced tags. \'metroid\' in the blacklist will catch \'series:metroid\' as parsed from a site.'
        message += os.linesep * 2
        message += 'It is worth doing a small test here, just to make sure it is all set up how you want.'
        
        self._tag_blacklist_button = ClientGUITags.TagFilterButton( downloader_options_panel, message, tag_blacklist, only_show_blacklist = True )
        
        self._tag_whitelist = list( tag_import_options.GetTagWhitelist() )
        
        self._tag_whitelist_button = ClientGUICommon.BetterButton( downloader_options_panel, 'whitelist', self._EditWhitelist )
        
        self._UpdateTagWhitelistLabel()
        
        self._services_vbox = QP.VBoxLayout()
        
        #
        
        self._is_default.setChecked( tag_import_options.IsDefault() )
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB() )
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB() )
        
        self._InitialiseServices( tag_import_options )
        
        self._SetValue( tag_import_options )
        
        #
        
        rows = []
        
        rows.append( ( 'rely on the appropriate default tag import options at the time of import: ', self._is_default ) )
        
        gridbox = ClientGUICommon.WrapInGrid( default_panel, rows )
        
        if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            st = ClientGUICommon.BetterStaticText( default_panel, label = 'Most of the time, you want to rely on the default tag import options!' )
            
            st.setObjectName( 'HydrusWarning' )
            
            default_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        default_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        default_panel.Add( self._load_default_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if not allow_default_selection:
            
            default_panel.hide()
            
        
        #
        
        rows = []
        
        rows.append( ( 'fetch tags even if url recognised and file already in db: ', self._fetch_tags_even_if_url_recognised_and_file_already_in_db ) )
        rows.append( ( 'fetch tags even if hash recognised and file already in db: ', self._fetch_tags_even_if_hash_recognised_and_file_already_in_db ) )
        rows.append( ( 'set file blacklist: ', self._tag_blacklist_button ) )
        rows.append( ( 'set file whitelist: ', self._tag_whitelist_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( downloader_options_panel, rows )
        
        downloader_options_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if not self._show_downloader_options:
            
            downloader_options_panel.hide()
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, downloader_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._services_vbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._specific_options_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, default_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._specific_options_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.addStretch( 1 )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._is_default.clicked.connect( self._UpdateIsDefault )
        
        self._UpdateIsDefault()
        
    
    def _EditWhitelist( self ):
        
        message = 'If you add tags here, then any file importing with these options must have at least one of these tags from the download source. You can mix it with a blacklist--both will apply in turn.'
        message += os.linesep * 2
        message += 'This is usually easier and faster to do just by adding tags to the downloader query (e.g. "artistname desired_tag"), so reserve this for downloaders that do not work on tags or where you want to whitelist multiple tags.'
        
        with ClientGUIDialogs.DialogInputTags( self, CC.COMBINED_TAG_SERVICE_KEY, list( self._tag_whitelist ), expand_parents = False, message = message ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._tag_whitelist = dlg.GetTags()
                
                self._UpdateTagWhitelistLabel()
                
            
        
    
    def _InitialiseServices( self, tag_import_options ):
        
        services = HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            
            service_tag_import_options = tag_import_options.GetServiceTagImportOptions( service_key )
            
            panel = EditServiceTagImportOptionsPanel( self._specific_options_panel, service_key, service_tag_import_options, show_downloader_options = self._show_downloader_options )
            
            self._service_keys_to_service_tag_import_options_panels[ service_key ] = panel
            
            QP.AddToLayout( self._services_vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
    
    def _LoadDefaultOptions( self ):
        
        domain_manager = HG.client_controller.network_engine.domain_manager
        
        ( file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_default_tag_import_options ) = domain_manager.GetDefaultTagImportOptions()
        
        choice_tuples = []
        
        choice_tuples.append( ( 'file post default', file_post_default_tag_import_options ) )
        choice_tuples.append( ( 'watchable default', watchable_default_tag_import_options ) )
        
        if len( url_class_keys_to_default_tag_import_options ) > 0:
            
            choice_tuples.append( ( '----', None ) )
            
            url_classes = domain_manager.GetURLClasses()
            
            url_class_keys_to_url_classes = { url_class.GetClassKey() : url_class for url_class in url_classes }
            
            url_class_names_and_default_tag_import_options = sorted( ( ( url_class_keys_to_url_classes[ url_class_key ].GetName(), url_class_keys_to_default_tag_import_options[ url_class_key ] ) for url_class_key in list( url_class_keys_to_default_tag_import_options.keys() ) if url_class_key in url_class_keys_to_url_classes ) )
            
            choice_tuples.extend( url_class_names_and_default_tag_import_options )
            
        
        try:
            
            default_tag_import_options = ClientGUIDialogsQuick.SelectFromList( self, 'Select which default', choice_tuples, sort_tuples = False )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if default_tag_import_options is None:
            
            return
            
        
        self._SetValue( default_tag_import_options )
        
    
    def _SetValue( self, tag_import_options: ClientImportOptions.TagImportOptions ):
        
        self._is_default.setChecked( tag_import_options.IsDefault() )
        
        self._tag_blacklist_button.SetValue( tag_import_options.GetTagBlacklist() )
        
        self._tag_whitelist = list( tag_import_options.GetTagWhitelist() )
        
        self._UpdateTagWhitelistLabel()
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB() )
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB() )
        
        for ( service_key, panel ) in self._service_keys_to_service_tag_import_options_panels.items():
            
            service_tag_import_options = tag_import_options.GetServiceTagImportOptions( service_key )
            
            panel.SetValue( service_tag_import_options )
            
        
        self._UpdateIsDefault()
        
    
    def _ShowHelp( self ):
        
        message = '''Here you can select which kinds of tags you would like applied to the files that are imported.

If this import context can fetch and parse tags from a remote location (such as a gallery downloader, which may provide 'creator' or 'series' tags, amongst others), then the namespaces it provides will be listed here with checkboxes--simply check which ones you are interested in for the tag services you want them to be applied to and it will all occur as the importer processes its files.

In these cases, if the URL has been previously downloaded and the client knows its file is already in the database, the client will usually not make a new network request to fetch the file's tags. This allows for quick reprocessing/skipping of previously seen items in large download queues and saves bandwidth. If you however wish to purposely fetch tags for files you have previously downloaded, you can also force tag fetching for these 'already in db' files.

I strongly recommend that you only ever turn this 'fetch tags even...' option for one-time jobs. It is typically only useful if you download some files and realised you forgot to set the tag parsing options you like--you can set the fetch option on and 'try again' the files to force the downloader to fetch the tags.

You can also set some fixed 'explicit' tags (like, say, 'read later' or 'from my unsorted folder' or 'pixiv subscription') to be applied to all imported files.

---

Please note that once you know what tags you like, you can (and should) set up the 'default' values for these tag import options under _network->downloaders->manage default tag import options_, both globally and on a per-parser basis. If you always want all the tags going to 'my tags', this is easy to set up there, and you won't have to put it in every time.'''
        
        QW.QMessageBox.information( self, 'Information', message )
        
    
    def _UpdateIsDefault( self ):
        
        is_default = self._is_default.isChecked()
        
        show_specific_options = not is_default
        
        self._specific_options_panel.setVisible( show_specific_options )
        
        if not show_specific_options:
            
            self.window().adjustSize()
            
        
    
    def _UpdateTagWhitelistLabel( self ):
        
        if len( self._tag_whitelist ) == 0:
            
            label = 'no whitelist'
            
        else:
            
            label = 'whitelist of {} tags'.format( HydrusData.ToHumanInt( len( self._tag_whitelist ) ) )
            
        
        self._tag_whitelist_button.setText( label )
        
    
    def GetValue( self ) -> ClientImportOptions.TagImportOptions:
        
        is_default = self._is_default.isChecked()
        
        if is_default:
            
            tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
            
        else:
            
            fetch_tags_even_if_url_recognised_and_file_already_in_db = self._fetch_tags_even_if_url_recognised_and_file_already_in_db.isChecked()
            fetch_tags_even_if_hash_recognised_and_file_already_in_db = self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.isChecked()
            
            service_keys_to_service_tag_import_options = { service_key : panel.GetValue() for ( service_key, panel ) in list( self._service_keys_to_service_tag_import_options_panels.items() ) }
            
            tag_blacklist = self._tag_blacklist_button.GetValue()
            tag_whitelist = list( self._tag_whitelist )
            
            tag_import_options = ClientImportOptions.TagImportOptions( fetch_tags_even_if_url_recognised_and_file_already_in_db = fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db = fetch_tags_even_if_hash_recognised_and_file_already_in_db, tag_blacklist = tag_blacklist, tag_whitelist = tag_whitelist, service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
            
        
        return tag_import_options
        
    
class EditSelectFromListPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, choice_tuples: list, value_to_select = None, sort_tuples = True ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._list = QW.QListWidget( self )
        self._list.itemDoubleClicked.connect( self.EventSelect )
        
        #
        
        selected_a_value = False
        
        if sort_tuples:
            
            try:
                
                choice_tuples.sort()
                
            except TypeError:
                
                try:
                    
                    choice_tuples.sort( key = lambda t: t[0] )
                    
                except TypeError:
                    
                    pass # fugg
                    
                
            
        
        for ( i, ( label, value ) ) in enumerate( choice_tuples ):
            
            item = QW.QListWidgetItem()
            item.setText( label )
            item.setData( QC.Qt.UserRole, value )
            self._list.addItem( item )
            
            if value_to_select is not None and value_to_select == value:
                
                QP.ListWidgetSetSelection( self._list, i )
                
                selected_a_value = True
                
            
        
        if not selected_a_value:
            
            QP.ListWidgetSetSelection( self._list, 0 )
            
        
        #
        
        max_label_width_chars = max( ( len( label ) for ( label, value ) in choice_tuples ) )
        
        width_chars = min( 64, max_label_width_chars + 2 )
        height_chars = min( max( 6, len( choice_tuples ) ), 36 )
        
        ( width_px, height_px ) = ClientGUIFunctions.ConvertTextToPixels( self._list, ( width_chars, height_chars ) )
        
        row_height_px = self._list.sizeHintForRow( 0 )
        
        if row_height_px != -1:
            
            height_px = row_height_px * height_chars
            
        
        # wew lad, but it 'works'
        # formalise this and make a 'stretchy qlistwidget' class
        self._list.sizeHint = lambda: QC.QSize( width_px, height_px )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def EventSelect( self, item ):
        
        self.parentWidget().DoOK()
        
    
    def GetValue( self ):
        
        selection = QP.ListWidgetGetSelection( self._list ) 
        
        return QP.GetClientData( self._list, selection )
        
    
class EditSelectFromListButtonsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, choices, message = '' ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._data = None
        
        vbox = QP.VBoxLayout()
        
        if message != '':
            
            st = ClientGUICommon.BetterStaticText( self, label = message )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        first_focused = False
        
        for ( text, data, tooltip ) in choices:
            
            button = ClientGUICommon.BetterButton( self, text, self._ButtonChoice, data )
            
            button.setToolTip( tooltip )
            
            QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            if not first_focused:
                
                HG.client_controller.CallAfterQtSafe( button, button.setFocus, QC.Qt.OtherFocusReason)
                
                first_focused = True
                
            
        
        self.widget().setLayout( vbox )
        
    
    def _ButtonChoice( self, data ):
        
        self._data = data
        
        self.parentWidget().DoOK()
        
    
    def GetValue( self ):
        
        return self._data
        
    
class EditServiceTagImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, service_tag_import_options: ClientImportOptions.ServiceTagImportOptions, show_downloader_options: bool = True ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._service_key = service_key
        self._show_downloader_options = show_downloader_options
        
        name = HG.client_controller.services_manager.GetName( self._service_key )
        
        main_box = ClientGUICommon.StaticBox( self, name )
        
        #
        
        ( get_tags, get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, self._only_add_existing_tags_filter, self._get_tags_overwrite_deleted, self._additional_tags_overwrite_deleted ) = service_tag_import_options.ToTuple()
        
        #
        
        menu_items = self._GetCogIconMenuItems()
        
        cog_button = ClientGUICommon.MenuBitmapButton( main_box, CC.global_pixmaps().cog, menu_items )
        
        #
        
        downloader_options_panel = ClientGUICommon.StaticBox( main_box, 'tag parsing' )
        
        self._get_tags_checkbox = QW.QCheckBox( 'get tags', downloader_options_panel )
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            message = None
            
        else:
            
            message = 'Here you can filter which tags are applied to the files being imported in this context. This typically means those tags on a booru file page beside the file, but other contexts provide tags from different locations and quality.'
            message += os.linesep * 2
            message += 'The namespace checkboxes on the left are compiled from what all your current parsers say they can do and are simply for convenience. It is worth doing some smaller tests with a new download source to make sure you know what it can provide and what you actually want.'
            message += os.linesep * 2
            message += 'Once you are happy, you might want to say \'only "character:", "creator:" and "series:" tags\', or \'everything _except_ "species:" tags\'. This tag filter can get complicated if you want it to--check the help button in the top-right for more information.'
            
        
        self._get_tags_filter_button = ClientGUITags.TagFilterButton( downloader_options_panel, message, get_tags_filter, label_prefix = 'adding: ' )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._get_tags_checkbox, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._get_tags_filter_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        downloader_options_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._additional_button = ClientGUICommon.BetterButton( main_box, 'additional tags', self._DoAdditionalTags )
        
        #
        
        self._get_tags_checkbox.setChecked( get_tags )
        
        #
        
        if not self._show_downloader_options:
            
            downloader_options_panel.hide()
            
        
        main_box.Add( cog_button, CC.FLAGS_ON_RIGHT )
        main_box.Add( downloader_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        main_box.Add( self._additional_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, main_box, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._UpdateAdditionalTagsButtonLabel()
        
        self._UpdateGetTags()
        
        #
        
        self._get_tags_checkbox.clicked.connect( self._UpdateGetTags )
        
    
    def _DoAdditionalTags( self ):
        
        message = 'Any tags you enter here will be applied to every file that passes through this import context.'
        
        with ClientGUIDialogs.DialogInputTags( self, self._service_key, list( self._additional_tags ), message = message, show_display_decorators = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._additional_tags = dlg.GetTags()
                
            
        
        self._UpdateAdditionalTagsButtonLabel()
        
    
    def _EditOnlyAddExistingTagsFilter( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit already-exist filter' ) as dlg:
            
            namespaces = HG.client_controller.network_engine.domain_manager.GetParserNamespaces()
            
            message = 'If you do not want the \'only add tags that already exist\' option to apply to all tags coming in, set a filter here for the tags you _want_ to be exposed to this test.'
            message += os.linesep * 2
            message += 'For instance, if you only want the wash of messy unnamespaced tags to be exposed to the test, then set a simple whitelist for only \'unnamespaced\'.'
            message += os.linesep * 2
            message += 'This is obviously a complicated idea, so make sure you test it on a small scale before you try anything big.'
            message += os.linesep * 2
            message += 'Clicking ok on this dialog will automatically turn on the already-exists filter if it is off.'
            
            panel = ClientGUITags.EditTagFilterPanel( dlg, self._only_add_existing_tags_filter, namespaces = namespaces, message = message )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._only_add_existing_tags_filter = panel.GetValue()
                
                self._only_add_existing_tags = True
                
            
        
    
    def _GetCogIconMenuItems( self ):
        
        menu_items = []
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_to_new_files' )
        
        menu_items.append( ( 'check', 'apply tags to new files', 'Apply tags to new files.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_to_already_in_inbox' )
        
        menu_items.append( ( 'check', 'apply tags to files already in inbox', 'Apply tags to files that are already in the db and in the inbox.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_to_already_in_archive' )
        
        menu_items.append( ( 'check', 'apply tags to files already in archive', 'Apply tags to files that are already in the db and archived.', check_manager ) )
        
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        if self._show_downloader_options:
            
            check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_get_tags_overwrite_deleted' )
            
            menu_items.append( ( 'check', 'parsed tags overwrite previously deleted tags', 'Tags parsed and filtered will overwrite the deleted record.', check_manager ) )
            
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_additional_tags_overwrite_deleted' )
        
        menu_items.append( ( 'check', 'additional tags overwrite previously deleted tags', 'The manually added tags will overwrite the deleted record.', check_manager ) )
        
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        check_manager = ClientGUICommon.CheckboxManagerBoolean( self, '_only_add_existing_tags' )
        
        menu_items.append( ( 'check', 'only add tags that already exist', 'Only add tags to this service if they have non-zero count.', check_manager ) )
        
        menu_items.append( ( 'normal', 'set a filter for already-exist test', 'Tell the already-exist test to only work on a subset of tags.', self._EditOnlyAddExistingTagsFilter ) )
        
        return menu_items
        
    
    def _UpdateAdditionalTagsButtonLabel( self ):
        
        button_label = HydrusData.ToHumanInt( len( self._additional_tags ) ) + ' additional tags'
        
        self._additional_button.setText( button_label )
        
    
    def _UpdateGetTags( self ):
        
        get_tags = self._get_tags_checkbox.isChecked()
        
        should_enable_filter = get_tags
        
        self._get_tags_filter_button.setEnabled( should_enable_filter )
        
    
    def GetValue( self ) -> ClientImportOptions.ServiceTagImportOptions:
        
        get_tags = self._get_tags_checkbox.isChecked()
        
        get_tags_filter = self._get_tags_filter_button.GetValue()
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = get_tags, get_tags_filter = get_tags_filter, additional_tags = self._additional_tags, to_new_files = self._to_new_files, to_already_in_inbox = self._to_already_in_inbox, to_already_in_archive = self._to_already_in_archive, only_add_existing_tags = self._only_add_existing_tags, only_add_existing_tags_filter = self._only_add_existing_tags_filter, get_tags_overwrite_deleted = self._get_tags_overwrite_deleted, additional_tags_overwrite_deleted = self._additional_tags_overwrite_deleted )
        
        return service_tag_import_options
        
    
    def SetValue( self, service_tag_import_options: ClientImportOptions.ServiceTagImportOptions ):
        
        ( get_tags, get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, self._only_add_existing_tags_filter, self._get_tags_overwrite_deleted, self._additional_tags_overwrite_deleted ) = service_tag_import_options.ToTuple()
        
        self._get_tags_checkbox.setChecked( get_tags )
        
        self._get_tags_filter_button.SetValue( get_tags_filter )
        
        self._UpdateGetTags()
        
        self._UpdateAdditionalTagsButtonLabel()
        
    
class EditTagSummaryGeneratorPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, tag_summary_generator: ClientGUITags.TagSummaryGenerator ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        show_panel = ClientGUICommon.StaticBox( self, 'shows' )
        
        self._show = QW.QCheckBox( show_panel )
        
        edit_panel = ClientGUICommon.StaticBox( self, 'edit' )
        
        self._background_colour = ClientGUICommon.AlphaColourControl( edit_panel )
        self._text_colour = ClientGUICommon.AlphaColourControl( edit_panel )
        
        self._namespaces_listbox = ClientGUIListBoxes.QueueListBox( edit_panel, 8, self._ConvertNamespaceToListBoxString, self._AddNamespaceInfo, self._EditNamespaceInfo )
        
        self._separator = QW.QLineEdit( edit_panel )
        
        example_panel = ClientGUICommon.StaticBox( self, 'example' )
        
        self._example_tags = QW.QPlainTextEdit( example_panel )
        
        self._test_result = QW.QLineEdit( example_panel )
        self._test_result.setReadOnly( True )
        
        #
        
        ( background_colour, text_colour, namespace_info, separator, example_tags, show ) = tag_summary_generator.ToTuple()
        
        self._show.setChecked( show )
        
        self._background_colour.SetValue( background_colour )
        self._text_colour.SetValue( text_colour )
        self._namespaces_listbox.AddDatas( namespace_info )
        self._separator.setText( separator )
        self._example_tags.setPlainText( os.linesep.join( example_tags ) )
        
        self._UpdateTest()
        
        #
        
        rows = []
        
        rows.append( ( 'currently shows (turn off to hide): ', self._show ) )
        
        gridbox = ClientGUICommon.WrapInGrid( show_panel, rows )
        
        show_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'background colour: ', self._background_colour ) )
        rows.append( ( 'text colour: ', self._text_colour ) )
        
        gridbox = ClientGUICommon.WrapInGrid( edit_panel, rows )
        
        edit_panel.Add( ClientGUICommon.BetterStaticText( edit_panel, 'The colours only work for the thumbnails right now!' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        edit_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        edit_panel.Add( self._namespaces_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        edit_panel.Add( ClientGUICommon.WrapInText( self._separator, edit_panel, 'separator' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        example_panel.Add( ClientGUICommon.BetterStaticText( example_panel, 'Enter some newline-separated tags here to see what your current object would generate.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        example_panel.Add( self._example_tags, CC.FLAGS_EXPAND_BOTH_WAYS )
        example_panel.Add( self._test_result, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, show_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, edit_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, example_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._show.clicked.connect( self._UpdateTest )
        self._separator.textChanged.connect( self._UpdateTest )
        self._example_tags.textChanged.connect( self._UpdateTest )
        self._namespaces_listbox.listBoxChanged.connect( self._UpdateTest )
        
    
    def _AddNamespaceInfo( self ):
        
        namespace = ''
        prefix = ''
        separator = ', '
        
        namespace_info = ( namespace, prefix, separator )
        
        return self._EditNamespaceInfo( namespace_info )
        
    
    def _ConvertNamespaceToListBoxString( self, namespace_info ):
        
        ( namespace, prefix, separator ) = namespace_info
        
        if namespace == '':
            
            pretty_namespace = 'unnamespaced'
            
        else:
            
            pretty_namespace = namespace
            
        
        pretty_prefix = prefix
        pretty_separator = separator
        
        return pretty_namespace + ' | prefix: "' + pretty_prefix + '" | separator: "' + pretty_separator + '"'
        
    
    def _EditNamespaceInfo( self, namespace_info ):
        
        ( namespace, prefix, separator ) = namespace_info
        
        message = 'Edit namespace.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, namespace, allow_blank = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                namespace = dlg.GetValue()
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
        message = 'Edit prefix.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, prefix, allow_blank = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                prefix = dlg.GetValue()
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
        message = 'Edit separator.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message, separator, allow_blank = True ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                separator = dlg.GetValue()
                
                namespace_info = ( namespace, prefix, separator )
                
                return namespace_info
                
            else:
                
                raise HydrusExceptions.VetoException()
                
            
        
    
    def _UpdateTest( self ):
        
        tag_summary_generator = self.GetValue()
        
        self._test_result.setText( tag_summary_generator.GenerateExampleSummary() )
        
    
    def GetValue( self ) -> ClientGUITags.TagSummaryGenerator:
        
        show = self._show.isChecked()
        
        background_colour = self._background_colour.GetValue()
        text_colour = self._text_colour.GetValue()
        namespace_info = self._namespaces_listbox.GetData()
        separator = self._separator.text()
        example_tags = HydrusTags.CleanTags( HydrusText.DeserialiseNewlinedTexts( self._example_tags.toPlainText() ) )
        
        return ClientGUITags.TagSummaryGenerator( background_colour, text_colour, namespace_info, separator, example_tags, show )
        
    
class TagSummaryGeneratorButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent: QW.QWidget, tag_summary_generator: ClientGUITags.TagSummaryGenerator ):
        
        label = tag_summary_generator.GenerateExampleSummary()
        
        ClientGUICommon.BetterButton.__init__( self, parent, label, self._Edit )
        
        self._tag_summary_generator = tag_summary_generator
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit tag summary' ) as dlg:
            
            panel = EditTagSummaryGeneratorPanel( dlg, self._tag_summary_generator )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._tag_summary_generator = panel.GetValue()
                
                self.setText( self._tag_summary_generator.GenerateExampleSummary() )
                
            
        
    
    def GetValue( self ) -> ClientGUITags.TagSummaryGenerator:
        
        return self._tag_summary_generator
        
    
