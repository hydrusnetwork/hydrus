from . import ClientConstants as CC
from . import ClientDefaults
from . import ClientDownloading
from . import ClientDuplicates
from . import ClientImporting
from . import ClientGUICommon
from . import ClientGUIControls
from . import ClientGUIDialogs
from . import ClientGUIDialogsQuick
from . import ClientGUIFunctions
from . import ClientGUIImport
from . import ClientGUIListBoxes
from . import ClientGUIListCtrl
from . import ClientGUIMenus
from . import ClientGUIScrolledPanels
from . import ClientGUIFileSeedCache
from . import ClientGUIGallerySeedLog
from . import ClientGUIMPV
from . import ClientGUITags
from . import ClientGUITime
from . import ClientGUITopLevelWindows
from . import ClientImportFileSeeds
from . import ClientImportOptions
from . import ClientImportSubscriptions
from . import ClientMedia
from . import ClientNetworkingContexts
from . import ClientNetworkingDomain
from . import ClientParsing
from . import ClientPaths
from . import ClientSearch
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNetwork
from . import HydrusSerialisable
from . import HydrusTags
from . import HydrusText
import os
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
from . import QtPorting as QP

class EditAccountTypePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, service_type, account_type ):
        
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
        
    
    def GetValue( self ):
        
        title = self._title.text()
        
        permissions = {}
        
        for permission_control in self._permission_controls:
            
            ( content_type, action ) = permission_control.GetValue()
            
            if action is not None:
                
                permissions[ content_type ] = action
                
            
        
        bandwidth_rules = self._bandwidth_rules_control.GetValue()
        
        return HydrusNetwork.AccountType.GenerateAccountTypeFromParameters( self._account_type_key, title, permissions, bandwidth_rules )
        
    
class EditBandwidthRulesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, bandwidth_rules, summary = '' ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._bandwidth_rules_ctrl = ClientGUIControls.BandwidthRulesCtrl( self, bandwidth_rules )
        
        vbox = QP.VBoxLayout()
        
        if summary != '':
            
            st = ClientGUICommon.BetterStaticText( self, summary )
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, self._bandwidth_rules_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        return self._bandwidth_rules_ctrl.GetValue()
        
    
class EditChooseMultiple( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, choice_tuples ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._checkboxes = QP.CheckListBox( self )
        
        self._checkboxes.setMinimumSize( QP.TupleToQSize( (320,420) ) )
        
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
        
    
    def GetValue( self ):
        
        return self._checkboxes.GetChecked()
        
    
class EditCookiePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, name, value, domain, path, expires ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._name = QW.QLineEdit( self )
        self._value = QW.QLineEdit( self )
        self._domain = QW.QLineEdit( self )
        self._path = QW.QLineEdit( self )
        
        expires_panel = ClientGUICommon.StaticBox( self, 'expires' )
        
        self._expires_st = ClientGUICommon.BetterStaticText( expires_panel )
        self._expires_st_utc = ClientGUICommon.BetterStaticText( expires_panel )
        self._expires_time_delta = ClientGUITime.TimeDeltaButton( expires_panel, min = 1200, days = True, hours = True, minutes = True )
        
        #
        
        self._name.setText( name )
        self._value.setText( value )
        self._domain.setText( domain )
        self._path.setText( path )
        
        self._expires = expires
        
        self._expires_time_delta.SetValue( 30 * 86400 )
        
        #
        
        rows = []
        
        rows.append( ( 'Actual expires as UTC Timestamp: ', self._expires_st_utc ) )
        rows.append( ( 'Set expires as a delta from now: ', self._expires_time_delta ) )
        
        gridbox = ClientGUICommon.WrapInGrid( expires_panel, rows )
        
        expires_panel.Add( self._expires_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        expires_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'value: ', self._value ) )
        rows.append( ( 'domain: ', self._domain ) )
        rows.append( ( 'path: ', self._path ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, expires_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._UpdateExpiresText()
        
        self._expires_time_delta.timeDeltaChanged.connect( self.EventTimeDelta )
        
    
    def _UpdateExpiresText( self ):
        
        self._expires_st.setText( HydrusData.ConvertTimestampToPrettyExpires(self._expires) )
        self._expires_st_utc.setText( str(self._expires) )
        
    
    def EventTimeDelta( self ):
        
        time_delta = self._expires_time_delta.GetValue()
        
        expires = HydrusData.GetNow() + time_delta
        
        self._expires = expires
        
        self._UpdateExpiresText()
        
    
    def GetValue( self ):
        
        name = self._name.text()
        value = self._value.text()
        domain = self._domain.text()
        path = self._path.text()
        expires = self._expires
        
        return ( name, value, domain, path, expires )
        
    
class EditDefaultTagImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, url_classes, parsers, url_class_keys_to_parser_keys, file_post_default_tag_import_options, watchable_default_tag_import_options, url_class_keys_to_tag_import_options ):
        
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
        
        columns = [ ( 'url class', -1 ), ( 'url type', 12 ), ( 'defaults set?', 15 ) ]
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, 'default_tag_import_options', 15, 36, columns, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Clear, activation_callback = self._Edit )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl_panel.AddButton( 'copy', self._Copy, enabled_check_func = self._OnlyOneTIOSelected )
        self._list_ctrl_panel.AddButton( 'paste', self._Paste, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddButton( 'clear', self._Clear, enabled_only_on_selection = True )
        
        #
        
        eligible_url_classes = [ url_class for url_class in url_classes if url_class.GetURLType() in ( HC.URL_TYPE_POST, HC.URL_TYPE_WATCHABLE ) and url_class.GetMatchKey() in self._url_class_keys_to_parser_keys ]
        
        self._list_ctrl.AddDatas( eligible_url_classes )
        
        self._list_ctrl.Sort( 1 )
        
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
        
        url_class_key = url_class.GetMatchKey()
        
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
                
                url_class_key = url_class.GetMatchKey()
                
                if url_class_key in self._url_class_keys_to_tag_import_options:
                    
                    del self._url_class_keys_to_tag_import_options[ url_class_key ]
                    
                
            
            self._list_ctrl.UpdateDatas( url_classes_to_clear )
            
        
    
    def _Copy( self ):
        
        selected = self._list_ctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            url_class = selected[0]
            
            url_class_key = url_class.GetMatchKey()
            
            if url_class_key in self._url_class_keys_to_tag_import_options:
                
                tag_import_options = self._url_class_keys_to_tag_import_options[ url_class_key ]
                
                json_string = tag_import_options.DumpToString()
                
                HG.client_controller.pub( 'clipboard', 'text', json_string )
                
            
        
    
    def _Edit( self ):
        
        url_classes_to_edit = self._list_ctrl.GetData( only_selected = True )
        
        for url_class in url_classes_to_edit:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit tag import options' ) as dlg:
                
                tag_import_options = self._GetDefaultTagImportOptions( url_class )
                show_downloader_options = True
                
                panel = EditTagImportOptionsPanel( dlg, tag_import_options, show_downloader_options )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    url_class_key = url_class.GetMatchKey()
                    
                    tag_import_options = panel.GetValue()
                    
                    self._url_class_keys_to_tag_import_options[ url_class_key ] = tag_import_options
                    
                else:
                    
                    break
                    
                
            
        
        self._list_ctrl.UpdateDatas( url_classes_to_edit )
        
    
    def _GetDefaultTagImportOptions( self, url_class ):
        
        url_class_key = url_class.GetMatchKey()
        
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
            
            url_class_key = url_class.GetMatchKey()
            
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
                
                url_class_key = url_class.GetMatchKey()
                
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
    
    def __init__( self, parent, media, default_reason, suggested_file_service_key = None ):
        
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
        
    
class EditDomainManagerInfoPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, url_classes, network_contexts_to_custom_header_dicts ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._notebook = QW.QTabWidget( self )
        
        self._url_classes_panel = EditURLClassesPanel( self._notebook, url_classes )
        self._network_contexts_to_custom_header_dicts_panel = EditNetworkContextCustomHeadersPanel( self._notebook, network_contexts_to_custom_header_dicts )
        
        self._notebook.addTab( self._url_classes_panel, 'url classes' )
        self._notebook.setCurrentWidget( self._url_classes_panel )
        self._notebook.addTab( self._network_contexts_to_custom_header_dicts_panel, 'custom headers' )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        url_classes = self._url_classes_panel.GetValue()
        network_contexts_to_custom_header_dicts = self._network_contexts_to_custom_header_dicts_panel.GetValue()
        
        return ( url_classes, network_contexts_to_custom_header_dicts )
        
    
class EditDownloaderDisplayPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, network_engine, gugs, gug_keys_to_display, url_classes, url_class_keys_to_display ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._gugs = gugs
        self._gug_keys_to_gugs = { gug.GetGUGKey() : gug for gug in self._gugs }
        
        self._url_classes = url_classes
        self._url_class_keys_to_url_classes = { url_class.GetMatchKey() : url_class for url_class in self._url_classes }
        
        self._network_engine = network_engine
        
        #
        
        self._notebook = QW.QTabWidget( self )
        
        #
        
        self._gug_display_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        columns = [ ( 'downloader', -1 ), ( 'show in main selector list?', 29 ) ]
        
        self._gug_display_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._gug_display_list_ctrl_panel, 'gug_keys_to_display', 15, 36, columns, self._ConvertGUGDisplayDataToListCtrlTuples, activation_callback = self._EditGUGDisplay )
        
        self._gug_display_list_ctrl_panel.SetListCtrl( self._gug_display_list_ctrl )
        
        self._gug_display_list_ctrl_panel.AddButton( 'edit', self._EditGUGDisplay, enabled_only_on_selection = True )
        
        #
        
        self._url_display_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        columns = [ ( 'url class', -1 ), ( 'url type', 20 ), ( 'display on media viewer?', 36 ) ]
        
        self._url_display_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._url_display_list_ctrl_panel, 'url_class_keys_to_display', 15, 36, columns, self._ConvertURLDisplayDataToListCtrlTuples, activation_callback = self._EditURLDisplay )
        
        self._url_display_list_ctrl_panel.SetListCtrl( self._url_display_list_ctrl )
        
        self._url_display_list_ctrl_panel.AddButton( 'edit', self._EditURLDisplay, enabled_only_on_selection = True )
        
        #
        
        listctrl_data = []
        
        for ( gug_key, gug ) in list(self._gug_keys_to_gugs.items()):
            
            display = gug_key in gug_keys_to_display
            
            listctrl_data.append( ( gug_key, display ) )
            
        
        self._gug_display_list_ctrl.AddDatas( listctrl_data )
        
        self._gug_display_list_ctrl.Sort( 1 )
        
        #
        
        listctrl_data = []
        
        for ( url_class_key, url_class ) in list(self._url_class_keys_to_url_classes.items()):
            
            display = url_class_key in url_class_keys_to_display
            
            listctrl_data.append( ( url_class_key, display ) )
            
        
        self._url_display_list_ctrl.AddDatas( listctrl_data )
        
        self._url_display_list_ctrl.Sort( 1 )
        
        #
        
        self._notebook.addTab( self._gug_display_list_ctrl_panel, 'downloaders selector' )
        self._notebook.setCurrentWidget( self._gug_display_list_ctrl_panel )
        self._notebook.addTab( self._url_display_list_ctrl_panel, 'media viewer urls' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertGUGDisplayDataToListCtrlTuples( self, data ):
        
        ( gug_key, display ) = data
        
        gug = self._gug_keys_to_gugs[ gug_key ]
        
        name = gug.GetName()
        
        pretty_name = name
        
        if display:
            
            pretty_display = 'yes'
            
        else:
            
            pretty_display = 'no'
            
        
        display_tuple = ( pretty_name, pretty_display )
        sort_tuple = ( name, display )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertURLDisplayDataToListCtrlTuples( self, data ):
        
        ( url_class_key, display ) = data
        
        url_class = self._url_class_keys_to_url_classes[ url_class_key ]
        
        url_class_name = url_class.GetName()
        url_type = url_class.GetURLType()
        
        pretty_name = url_class_name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        if display:
            
            pretty_display = 'yes'
            
        else:
            
            pretty_display = 'no'
            
        
        display_tuple = ( pretty_name, pretty_url_type, pretty_display )
        sort_tuple = ( url_class_name, pretty_url_type, display )
        
        return ( display_tuple, sort_tuple )
        
    
    def _EditGUGDisplay( self ):
        
        for data in self._gug_display_list_ctrl.GetData( only_selected = True ):
            
            ( gug_key, display ) = data
            
            name = self._gug_keys_to_gugs[ gug_key ].GetName()
            
            message = 'Show "{}" in the main selector list?'.format( name )
            
            result, closed_by_user = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Show in the first list?', check_for_cancelled = True )
            
            if not closed_by_user:
                
                display = result == QW.QDialog.Accepted
                
                self._gug_display_list_ctrl.DeleteDatas( ( data, ) )
                
                new_data = ( gug_key, display )
                
                self._gug_display_list_ctrl.AddDatas( ( new_data, ) )
                
            else:
                
                break
                
            
        
        self._gug_display_list_ctrl.Sort()
        
    
    def _EditURLDisplay( self ):
        
        for data in self._url_display_list_ctrl.GetData( only_selected = True ):
            
            ( url_class_key, display ) = data
            
            url_class_name = self._url_class_keys_to_url_classes[ url_class_key ].GetName()
            
            message = 'Show ' + url_class_name + ' in the media viewer?'
            
            result, closed_by_user = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'Show in the media viewer?', check_for_cancelled = True )
            
            if not closed_by_user:
                
                display = result == QW.QDialog.Accepted
                
                self._url_display_list_ctrl.DeleteDatas( ( data, ) )
                
                new_data = ( url_class_key, display )
                
                self._url_display_list_ctrl.AddDatas( ( new_data, ) )
                
            else:
                
                break
                
            
        
        self._url_display_list_ctrl.Sort()
        
    
    def GetValue( self ):
        
        gug_keys_to_display = { gug_key for ( gug_key, display ) in self._gug_display_list_ctrl.GetData() if display }
        url_class_keys_to_display = { url_class_key for ( url_class_key, display ) in self._url_display_list_ctrl.GetData() if display }
        
        return ( gug_keys_to_display, url_class_keys_to_display )
        
    
class EditDuplicateActionOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, duplicate_action, duplicate_action_options, for_custom_action = False ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._duplicate_action = duplicate_action
        
        #
        
        tag_services_panel = ClientGUICommon.StaticBox( self, 'tag services' )
        
        tag_services_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( tag_services_panel )
        
        columns = [ ( 'service name', 24 ), ( 'action', 36 ), ( 'tags merged', -1 ) ]
        
        self._tag_service_actions = ClientGUIListCtrl.BetterListCtrl( tag_services_listctrl_panel, 'duplicate_action_options_tag_services', 5, 36, columns, self._ConvertTagDataToListCtrlTuple, delete_key_callback = self._DeleteTag, activation_callback = self._EditTag )
        
        tag_services_listctrl_panel.SetListCtrl( self._tag_service_actions )
        
        tag_services_listctrl_panel.AddButton( 'add', self._AddTag )
        tag_services_listctrl_panel.AddButton( 'edit', self._EditTag, enabled_only_on_selection = True )
        tag_services_listctrl_panel.AddButton( 'delete', self._DeleteTag, enabled_only_on_selection = True )
        
        #
        
        rating_services_panel = ClientGUICommon.StaticBox( self, 'rating services' )
        
        rating_services_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( rating_services_panel )
        
        columns = [ ( 'service name', -1 ), ( 'action', 36 ) ]
        
        self._rating_service_actions = ClientGUIListCtrl.BetterListCtrl( rating_services_listctrl_panel, 'duplicate_action_options_rating_services', 5, 24, columns, self._ConvertRatingDataToListCtrlTuple, delete_key_callback = self._DeleteRating, activation_callback = self._EditRating )
        
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
        
        self._service_keys_to_tag_options = { service_key : ( action, tag_filter ) for ( service_key, action, tag_filter ) in tag_service_options }
        
        self._tag_service_actions.SetData( list( self._service_keys_to_tag_options.keys() ) )
        
        self._tag_service_actions.Sort()
        
        self._service_keys_to_rating_options = { service_key : action for ( service_key, action ) in rating_service_options }
        
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
        
        for service in services_manager.GetServices( [ HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ] ):
            
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
        
        for service in services_manager.GetServices( [ HC.LOCAL_TAG, HC.TAG_REPOSITORY ] ):
            
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
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
                
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
        
        service_name = HG.client_controller.services_manager.GetName( service_key )
        pretty_action = HC.content_merge_string_lookup[ action ]
        
        display_tuple = ( service_name, pretty_action )
        sort_tuple = ( service_name, pretty_action )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertTagDataToListCtrlTuple( self, service_key ):
        
        ( action, tag_filter ) = self._service_keys_to_tag_options[ service_key ]
        
        service_name = HG.client_controller.services_manager.GetName( service_key )
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
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit which tags will be merged' ) as dlg_3:
                
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
                    
                
            
        
    
    def GetValue( self ):
        
        tag_service_actions = [ ( service_key, action, tag_filter ) for ( service_key, ( action, tag_filter ) ) in self._service_keys_to_tag_options.items() ]
        rating_service_actions = [ ( service_key, action ) for ( service_key, action ) in self._service_keys_to_rating_options.items() ]
        sync_archive = self._sync_archive.isChecked()
        sync_urls_action = self._sync_urls_action.GetValue()
        
        duplicate_action_options = ClientDuplicates.DuplicateActionOptions( tag_service_actions, rating_service_actions, sync_archive, sync_urls_action )
        
        return duplicate_action_options
        
    
class EditFileImportOptions( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, file_import_options, show_downloader_options ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalPixmaps.help, self._ShowHelp )
        
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
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_BUTTON_SIZER )
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
        
    
    def GetValue( self ):
        
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
        
    
class EditFrameLocationPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, info ):
        
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
        
    
class EditGUGPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, gug ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_gug = gug
        
        self._name = QW.QLineEdit( self )
        
        self._url_template = QW.QLineEdit( self )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._url_template, 74 )
        
        QP.SetMinClientSize( self._url_template, (min_width,-1) )
        
        self._replacement_phrase = QW.QLineEdit( self )
        self._search_terms_separator = QW.QLineEdit( self )
        self._initial_search_text = QW.QLineEdit( self )
        self._example_search_text = QW.QLineEdit( self )
        
        self._example_url = QW.QLineEdit( self )
        self._example_url.setReadOnly( True )
        self._matched_url_class = QW.QLineEdit( self )
        self._matched_url_class.setReadOnly( True )
        
        #
        
        name = gug.GetName()
        
        ( url_template, replacement_phrase, search_terms_separator, example_search_text ) = gug.GetURLTemplateVariables()
        
        initial_search_text = gug.GetInitialSearchText()
        
        self._name.setText( name )
        self._url_template.setText( url_template )
        self._replacement_phrase.setText( replacement_phrase )
        self._search_terms_separator.setText( search_terms_separator )
        self._initial_search_text.setText( initial_search_text )
        self._example_search_text.setText( example_search_text )
        
        self._UpdateExampleURL()
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'url template: ', self._url_template) )
        rows.append( ( 'replacement phrase: ', self._replacement_phrase ) )
        rows.append( ( 'search terms separator: ', self._search_terms_separator ) )
        rows.append( ( 'initial search text (to prompt user): ', self._initial_search_text ) )
        rows.append( ( 'example search text: ', self._example_search_text ) )
        rows.append( ( 'example url: ', self._example_url ) )
        rows.append( ( 'matches as a: ', self._matched_url_class ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._url_template.textChanged.connect( self._UpdateExampleURL )
        self._replacement_phrase.textChanged.connect( self._UpdateExampleURL )
        self._search_terms_separator.textChanged.connect( self._UpdateExampleURL )
        self._example_search_text.textChanged.connect( self._UpdateExampleURL )
        
    
    def _GetValue( self ):
        
        gug_key = self._original_gug.GetGUGKey()
        name = self._name.text()
        url_template = self._url_template.text()
        replacement_phrase = self._replacement_phrase.text()
        search_terms_separator = self._search_terms_separator.text()
        initial_search_text = self._initial_search_text.text()
        example_search_text = self._example_search_text.text()
        
        gug = ClientNetworkingDomain.GalleryURLGenerator( name, gug_key = gug_key, url_template = url_template, replacement_phrase = replacement_phrase, search_terms_separator = search_terms_separator, initial_search_text = initial_search_text, example_search_text = example_search_text )
        
        return gug
        
    
    def _UpdateExampleURL( self ):
        
        gug = self._GetValue()
        
        try:
            
            example_url = gug.GetExampleURL()
            
            example_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( example_url )
            
            self._example_url.setText( example_url )
            
        except ( HydrusExceptions.GUGException, HydrusExceptions.URLClassException ) as e:
            
            reason = str( e )
            
            self._example_url.setText( 'Could not generate - ' + reason )
            
            example_url = None
            
        
        if example_url is None:
            
            self._matched_url_class.setText( '' )
            
        else:
            
            url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( example_url )
            
            if url_class is None:
                
                url_class_text = 'Did not match a known url class.'
                
            else:
                
                url_class_text = 'Matched ' + url_class.GetName() + ' url class.'
                
            
            self._matched_url_class.setText( url_class_text )
            
        
    
    def GetValue( self ):
        
        gug = self._GetValue()
        
        try:
            
            gug.GetExampleURL()
            
        except HydrusExceptions.GUGException:
            
            raise HydrusExceptions.VetoException( 'Please ensure your generator can make an example url!' )
            
        
        return gug
        
    
class EditNGUGPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, ngug, available_gugs ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_ngug = ngug
        self._available_gugs = available_gugs
        
        self._available_gugs.sort( key = lambda g: g.GetName() )
        
        self._name = QW.QLineEdit( self )
        
        self._initial_search_text = QW.QLineEdit( self )
        
        self._gug_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'gug name', 24 ), ( 'available?', 20 ) ]
        
        self._gug_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._gug_list_ctrl_panel, 'ngug_gugs', 30, 74, columns, self._ConvertGUGDataToListCtrlTuples, use_simple_delete = True )
        
        self._gug_list_ctrl_panel.SetListCtrl( self._gug_list_ctrl )
        
        self._add_button = ClientGUICommon.BetterButton( self._gug_list_ctrl_panel, 'add', self._AddGUGButtonClick )
        
        self._gug_list_ctrl_panel.AddWindow( self._add_button )
        self._gug_list_ctrl_panel.AddDeleteButton()
        
        #
        
        name = ngug.GetName()
        
        initial_search_text = ngug.GetInitialSearchText()
        
        self._name.setText( name )
        self._initial_search_text.setText( initial_search_text )
        
        gug_keys_and_names = ngug.GetGUGKeysAndNames()
        
        self._gug_list_ctrl.AddDatas( gug_keys_and_names )
        
        self._gug_list_ctrl.Sort( 0 )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'initial search text (to prompt user): ', self._initial_search_text ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._gug_list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AddGUG( self, gug ):
        
        gug_key_and_name = gug.GetGUGKeyAndName()
        
        self._gug_list_ctrl.AddDatas( ( gug_key_and_name, ) )
        
    
    def _AddGUGButtonClick( self ):
        
        existing_gug_keys = { gug_key for ( gug_key, gug_name ) in self._gug_list_ctrl.GetData() }
        existing_gug_names = { gug_name for ( gug_key, gug_name ) in self._gug_list_ctrl.GetData() }
        
        choice_tuples = [ ( gug.GetName(), gug, False ) for gug in self._available_gugs if gug.GetName() not in existing_gug_names and gug.GetGUGKey() not in existing_gug_keys ]
        
        if len( choice_tuples ) == 0:
            
            QW.QMessageBox.critical( self, 'Error', 'No remaining gugs available!' )
            
            return
            
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'choose gugs' ) as dlg:
            
            panel = EditChooseMultiple( dlg, choice_tuples )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                chosen_gugs = panel.GetValue()
                
                for gug in chosen_gugs:
                    
                    self._AddGUG( gug )
                    
                
            
        
    
    def _ConvertGUGDataToListCtrlTuples( self, gug_key_and_name ):
        
        ( gug_key, gug_name ) = gug_key_and_name
        
        name = gug_name
        pretty_name = name
        
        available = gug_key in ( gug.GetGUGKey() for gug in self._available_gugs ) or gug_name in ( gug.GetName() for gug in self._available_gugs )
        
        if available:
            
            pretty_available = 'yes'
            
        else:
            
            pretty_available = 'no'
            
        
        display_tuple = ( pretty_name, pretty_available )
        sort_tuple = ( name, available )
        
        return ( display_tuple, sort_tuple )
        
    
    def GetValue( self ):
        
        gug_key = self._original_ngug.GetGUGKey()
        name = self._name.text()
        initial_search_text = self._initial_search_text.text()
        
        gug_keys_and_names = self._gug_list_ctrl.GetData()
        
        ngug = ClientNetworkingDomain.NestedGalleryURLGenerator( name, gug_key = gug_key, initial_search_text = initial_search_text, gug_keys_and_names = gug_keys_and_names )
        
        ngug.RepairGUGs( self._available_gugs )
        
        return ngug
        
    
class EditGUGsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, gugs ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_gugs.html' ) )
        
        menu_items.append( ( 'normal', 'open the gugs help', 'Open the help page for gugs in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalPixmaps.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', QG.QColor( 0, 0, 255 ) )
        
        #
        
        self._notebook = QW.QTabWidget( self )
        
        #
        
        self._gug_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        columns = [ ( 'name', 24 ), ( 'example url', -1 ), ( 'gallery url class?', 20 ) ]
        
        self._gug_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._gug_list_ctrl_panel, 'gugs', 30, 74, columns, self._ConvertGUGToListCtrlTuples, delete_key_callback = self._DeleteGUG, activation_callback = self._EditGUG )
        
        self._gug_list_ctrl_panel.SetListCtrl( self._gug_list_ctrl )
        
        self._gug_list_ctrl_panel.AddButton( 'add', self._AddNewGUG )
        self._gug_list_ctrl_panel.AddButton( 'edit', self._EditGUG, enabled_only_on_selection = True )
        self._gug_list_ctrl_panel.AddDeleteButton()
        self._gug_list_ctrl_panel.AddSeparator()
        self._gug_list_ctrl_panel.AddImportExportButtons( ( ClientNetworkingDomain.GalleryURLGenerator, ), self._AddGUG )
        self._gug_list_ctrl_panel.AddSeparator()
        self._gug_list_ctrl_panel.AddDefaultsButton( ClientDefaults.GetDefaultSingleGUGs, self._AddGUG )
        
        #
        
        self._ngug_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        columns = [ ( 'name', 24 ), ( 'gugs', -1 ), ( 'missing gugs', 14 ) ]
        
        self._ngug_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._ngug_list_ctrl_panel, 'ngugs', 20, 64, columns, self._ConvertNGUGToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditNGUG )
        
        self._ngug_list_ctrl_panel.SetListCtrl( self._ngug_list_ctrl )
        
        self._ngug_list_ctrl_panel.AddButton( 'add', self._AddNewNGUG )
        self._ngug_list_ctrl_panel.AddButton( 'edit', self._EditNGUG, enabled_only_on_selection = True )
        self._ngug_list_ctrl_panel.AddDeleteButton()
        self._ngug_list_ctrl_panel.AddSeparator()
        self._ngug_list_ctrl_panel.AddImportExportButtons( ( ClientNetworkingDomain.NestedGalleryURLGenerator, ), self._AddNGUG )
        self._ngug_list_ctrl_panel.AddSeparator()
        self._ngug_list_ctrl_panel.AddDefaultsButton( ClientDefaults.GetDefaultNGUGs, self._AddNGUG )
        
        #
        
        single_gugs = [ gug for gug in gugs if isinstance( gug, ClientNetworkingDomain.GalleryURLGenerator ) ]
        
        self._gug_list_ctrl.AddDatas( single_gugs )
        
        self._gug_list_ctrl.Sort( 0 )
        
        ngugs = [ gug for gug in gugs if isinstance( gug, ClientNetworkingDomain.NestedGalleryURLGenerator ) ]
        
        self._ngug_list_ctrl.AddDatas( ngugs )
        
        self._ngug_list_ctrl.Sort( 0 )
        
        #
        
        self._notebook.addTab( self._gug_list_ctrl_panel, 'gallery url generators' )
        self._notebook.setCurrentWidget( self._gug_list_ctrl_panel )
        self._notebook.addTab( self._ngug_list_ctrl_panel, 'nested gallery url generators' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_BUTTON_SIZER )
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AddNewGUG( self ):
        
        gug = ClientNetworkingDomain.GalleryURLGenerator( 'new gallery url generator' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit gallery url generator' ) as dlg:
            
            panel = EditGUGPanel( dlg, gug )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                gug = panel.GetValue()
                
                self._AddGUG( gug )
                
                self._gug_list_ctrl.Sort()
                
            
        
    
    def _AddNewNGUG( self ):
        
        ngug = ClientNetworkingDomain.NestedGalleryURLGenerator( 'new nested gallery url generator' )
        
        available_gugs = self._gug_list_ctrl.GetData()
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit nested gallery url generator' ) as dlg:
            
            panel = EditNGUGPanel( dlg, ngug, available_gugs )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ngug = panel.GetValue()
                
                self._AddNGUG( ngug )
                
                self._ngug_list_ctrl.Sort()
                
            
        
    
    def _AddGUG( self, gug ):
        
        HydrusSerialisable.SetNonDupeName( gug, self._GetExistingNames() )
        
        gug.RegenerateGUGKey()
        
        self._gug_list_ctrl.AddDatas( ( gug, ) )
        
    
    def _AddNGUG( self, ngug ):
        
        HydrusSerialisable.SetNonDupeName( ngug, self._GetExistingNames() )
        
        ngug.RegenerateGUGKey()
        
        self._ngug_list_ctrl.AddDatas( ( ngug, ) )
        
    
    def _ConvertGUGToListCtrlTuples( self, gug ):
        
        name = gug.GetName()
        example_url = gug.GetExampleURL()
        
        try:
            
            example_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( example_url )
            
            url_class = HG.client_controller.network_engine.domain_manager.GetURLClass( example_url )
            
        except:
            
            example_url = 'unable to parse example url'
            url_class = None
            
        
        if url_class is None:
            
            gallery_url_class = False
            pretty_gallery_url_class = ''
            
        else:
            
            gallery_url_class = True
            pretty_gallery_url_class = url_class.GetName()
            
        
        pretty_name = name
        pretty_example_url = example_url
        
        display_tuple = ( pretty_name, pretty_example_url, pretty_gallery_url_class )
        sort_tuple = ( name, example_url, gallery_url_class )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertNGUGToListCtrlTuples( self, ngug ):
        
        existing_names = { gug.GetName() for gug in self._gug_list_ctrl.GetData() }
        
        name = ngug.GetName()
        gugs = ngug.GetGUGNames()
        missing = len( set( gugs ).difference( existing_names ) ) > 0
        
        pretty_name = name
        pretty_gugs = ', '.join( gugs )
        
        if missing:
            
            pretty_missing = 'yes'
            
        else:
            
            pretty_missing = ''
            
        
        sort_gugs = len( gugs )
        
        display_tuple = ( pretty_name, pretty_gugs, pretty_missing )
        sort_tuple = ( name, sort_gugs, missing )
        
        return ( display_tuple, sort_tuple )
        
    
    def _DeleteGUG( self ):
        
        ngugs = self._ngug_list_ctrl.GetData()
        
        deletees = self._gug_list_ctrl.GetData( only_selected = True )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            for deletee in deletees:
                
                deletee_ngug_key = deletee.GetGUGKey()
                
                affected_ngug_names = []
                
                for ngug in ngugs:
                    
                    if deletee_ngug_key in ngug.GetGUGKeys():
                        
                        affected_ngug_names.append( ngug.GetName() )
                        
                    
                
                if len( affected_ngug_names ) > 0:
                    
                    affected_ngug_names.sort()
                    
                    message = 'The GUG "' + deletee.GetName() + '" is in the NGUGs:'
                    message += os.linesep * 2
                    message += os.linesep.join( affected_ngug_names )
                    message += os.linesep * 2
                    message += 'Deleting this GUG will ultimately remove it from those NGUGs--are you sure that is ok?'
                    
                    result = ClientGUIDialogsQuick.GetYesNo( self, message )
                    
                    if result != QW.QDialog.Accepted:
                        
                        break
                        
                    
                
                self._gug_list_ctrl.DeleteDatas( ( deletee, ) )
                
            
        
    
    def _EditGUG( self ):
        
        for gug in self._gug_list_ctrl.GetData( only_selected = True ):
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit gallery url generator' ) as dlg:
                
                panel = EditGUGPanel( dlg, gug )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._gug_list_ctrl.DeleteDatas( ( gug, ) )
                    
                    gug = panel.GetValue()
                    
                    HydrusSerialisable.SetNonDupeName( gug, self._GetExistingNames() )
                    
                    self._gug_list_ctrl.AddDatas( ( gug, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._gug_list_ctrl.Sort()
        
    
    def _EditNGUG( self ):
        
        available_gugs = self._gug_list_ctrl.GetData()
        
        for ngug in self._ngug_list_ctrl.GetData( only_selected = True ):
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit nested gallery url generator' ) as dlg:
                
                panel = EditNGUGPanel( dlg, ngug, available_gugs )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._ngug_list_ctrl.DeleteDatas( ( ngug, ) )
                    
                    ngug = panel.GetValue()
                    
                    HydrusSerialisable.SetNonDupeName( ngug, self._GetExistingNames() )
                    
                    self._ngug_list_ctrl.AddDatas( ( ngug, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._ngug_list_ctrl.Sort()
        
    
    def _GetExistingNames( self ):
        
        gugs = self._gug_list_ctrl.GetData()
        ngugs = self._ngug_list_ctrl.GetData()
        
        names = { gug.GetName() for gug in gugs }
        names.update( ( ngug.GetName() for ngug in ngugs ) )
        
        return names
        
    
    def GetValue( self ):
        
        gugs = list( self._gug_list_ctrl.GetData() )
        
        ngugs = self._ngug_list_ctrl.GetData()
        
        for ngug in ngugs:
            
            ngug.RepairGUGs( gugs )
            
        
        gugs.extend( ngugs )
        
        return gugs
        
    
class EditMediaViewOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, info ):
        
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
                
            
            self._media_show_action.addItem( CC.media_viewer_action_string_lookup[ action ], action )
            
            if action != CC.MEDIA_VIEWER_ACTION_DO_NOT_SHOW_ON_ACTIVATION_OPEN_EXTERNALLY:
                
                self._preview_show_action.addItem( CC.media_viewer_action_string_lookup[ action ], action )
                
            
        
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
        
        if len( set( possible_show_actions ).intersection( { CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV } ) ) == 0:
            
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
            
            QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,'Nearest neighbour is fast and ugly, 8x8 lanczos and area resampling are slower but beautiful.'), CC.FLAGS_VCENTER )
            
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText(self._scale_up_quality,self,'>100% (interpolation) quality:'), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, ClientGUICommon.WrapInText(self._scale_down_quality,self,'<100% (decimation) quality:'), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
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
        
    
class EditNetworkContextPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, network_context, limited_types = None, allow_default = True ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        if limited_types is None:
            
            limited_types = ( CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_DOMAIN, CC.NETWORK_CONTEXT_HYDRUS, CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, CC.NETWORK_CONTEXT_SUBSCRIPTION, CC.NETWORK_CONTEXT_WATCHER_PAGE )
            
        
        self._context_type = ClientGUICommon.BetterChoice( self )
        
        for ct in limited_types:
            
            self._context_type.addItem( CC.network_context_type_string_lookup[ ct], ct )
            
        
        self._context_type_info = ClientGUICommon.BetterStaticText( self )
        
        self._context_data_text = QW.QLineEdit( self )
        
        self._context_data_services = ClientGUICommon.BetterChoice( self )
        
        for service in HG.client_controller.services_manager.GetServices( HC.REPOSITORIES ):
            
            self._context_data_services.addItem( service.GetName(), service.GetServiceKey() )
            
        
        self._context_data_subscriptions = ClientGUICommon.BetterChoice( self )
        
        self._context_data_none = QW.QCheckBox( 'No specific data--acts as default.', self )
        
        if not allow_default:
            
            self._context_data_none.setVisible( False )
            
        
        names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION )
        
        for name in names:
            
            self._context_data_subscriptions.addItem( name, name )
            
        
        #
        
        self._context_type.SetValue( network_context.context_type )
        
        self._Update()
        
        context_type = network_context.context_type
        
        if network_context.context_data is None:
            
            self._context_data_none.setChecked( True )
            
        else:
            
            if context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                self._context_data_text.setText( network_context.context_data )
                
            elif context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                self._context_data_services.SetValue( network_context.context_data )
                
            elif context_type == CC.NETWORK_CONTEXT_SUBSCRIPTION:
                
                self._context_data_subscriptions.SetValue( network_context.context_data )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._context_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_type_info, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_data_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_data_services, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_data_subscriptions, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._context_data_none, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._context_type.currentIndexChanged.connect( self._Update )
        
    
    def _Update( self ):
        
        self._context_type_info.setText( CC.network_context_type_description_lookup[self._context_type.GetValue()] )
        
        context_type = self._context_type.GetValue()
        
        self._context_data_text.setEnabled( False )
        self._context_data_services.setEnabled( False )
        self._context_data_subscriptions.setEnabled( False )
        
        if context_type in ( CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_DOWNLOADER_PAGE, CC.NETWORK_CONTEXT_WATCHER_PAGE ):
            
            self._context_data_none.setChecked( True )
            
        else:
            
            self._context_data_none.setChecked( False )
            
            if context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                self._context_data_text.setEnabled( True )
                
            elif context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                self._context_data_services.setEnabled( True )
                
            elif context_type == CC.NETWORK_CONTEXT_SUBSCRIPTION:
                
                self._context_data_subscriptions.setEnabled( True )
                
            
        
    
    def GetValue( self ):
        
        context_type = self._context_type.GetValue()
        
        if self._context_data_none.isChecked():
            
            context_data = None
            
        else:
            
            if context_type == CC.NETWORK_CONTEXT_DOMAIN:
                
                context_data = self._context_data_text.text()
                
            elif context_type == CC.NETWORK_CONTEXT_HYDRUS:
                
                context_data = self._context_data_services.GetValue()
                
            elif context_type == CC.NETWORK_CONTEXT_SUBSCRIPTION:
                
                context_data = self._context_data_subscriptions.GetValue()
                
            
        
        return ClientNetworkingContexts.NetworkContext( context_type, context_data )
        
    
class EditNetworkContextCustomHeadersPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, network_contexts_to_custom_header_dicts ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'context', 24 ), ( 'header', 30 ), ( 'approved?', 12 ), ( 'reason', -1 ) ]
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, 'network_contexts_custom_headers', 15, 40, columns, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl_panel.AddButton( 'add', self._Add )
        self._list_ctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddDeleteButton()
        
        self._list_ctrl.Sort( 0 )
        
        #
        
        for ( network_context, custom_header_dict ) in list(network_contexts_to_custom_header_dicts.items()):
            
            for ( key, ( value, approved, reason ) ) in list(custom_header_dict.items()):
                
                data = ( network_context, ( key, value ), approved, reason )
                
                self._list_ctrl.AddDatas( ( data, ) )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, 'hostname.com' )
        key = 'Authorization'
        value = 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='
        approved = ClientNetworkingDomain.VALID_APPROVED
        reason = 'EXAMPLE REASON: HTTP header login--needed for access.'
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit header' ) as dlg:
            
            panel = self._EditPanel( dlg, network_context, key, value, approved, reason )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                ( network_context, key, value, approved, reason ) = panel.GetValue()
                
                data = ( network_context, ( key, value ), approved, reason )
                
                self._list_ctrl.AddDatas( ( data, ) )
                
            
        
    
    def _ConvertDataToListCtrlTuples( self, data ):
        
        ( network_context, ( key, value ), approved, reason ) = data
        
        pretty_network_context = network_context.ToString()
        
        pretty_key_value = key + ': ' + value
        
        pretty_approved = ClientNetworkingDomain.valid_str_lookup[ approved ]
        
        pretty_reason = reason
        
        display_tuple = ( pretty_network_context, pretty_key_value, pretty_approved, pretty_reason )
        
        sort_tuple = ( pretty_network_context, ( key, value ), pretty_approved, reason )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        for data in self._list_ctrl.GetData( only_selected = True ):
            
            ( network_context, ( key, value ), approved, reason ) = data
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit header' ) as dlg:
                
                panel = self._EditPanel( dlg, network_context, key, value, approved, reason )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._list_ctrl.DeleteDatas( ( data, ) )
                    
                    ( network_context, key, value, approved, reason ) = panel.GetValue()
                    
                    new_data = ( network_context, ( key, value ), approved, reason )
                    
                    self._list_ctrl.AddDatas( ( new_data, ) )
                    
                else:
                    
                    break
                    
                
            
        
    
    def GetValue( self ):
        
        network_contexts_to_custom_header_dicts = collections.defaultdict( dict )
        
        for ( network_context, ( key, value ), approved, reason ) in self._list_ctrl.GetData():
            
            network_contexts_to_custom_header_dicts[ network_context ][ key ] = ( value, approved, reason )
            
        
        return network_contexts_to_custom_header_dicts
        
    
    class _EditPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, network_context, key, value, approved, reason ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            self._network_context = ClientGUICommon.NetworkContextButton( self, network_context, limited_types = ( CC.NETWORK_CONTEXT_GLOBAL, CC.NETWORK_CONTEXT_DOMAIN ), allow_default = False )
            
            self._key = QW.QLineEdit( self )
            self._value = QW.QLineEdit( self )
            
            self._approved = ClientGUICommon.BetterChoice( self )
            
            for a in ( ClientNetworkingDomain.VALID_APPROVED, ClientNetworkingDomain.VALID_DENIED, ClientNetworkingDomain.VALID_UNKNOWN ):
                
                self._approved.addItem( ClientNetworkingDomain.valid_str_lookup[ a], a )
                
            
            self._reason = QW.QLineEdit( self )
            
            width = ClientGUIFunctions.ConvertTextToPixelWidth( self._reason, 60 )
            self._reason.setMinimumWidth( width )
            
            #
            
            self._key.setText( key )
            
            self._value.setText( value )
            
            self._approved.SetValue( approved )
            
            self._reason.setText( reason )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._network_context, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._key, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._value, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._approved, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._reason, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.widget().setLayout( vbox )
            
        
        def GetValue( self ):
            
            network_context = self._network_context.GetValue()
            key = self._key.text()
            value = self._value.text()
            approved = self._approved.GetValue()
            reason = self._reason.text()
            
            return ( network_context, key, value, approved, reason )
            
        
    
class EditNoneableIntegerPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, value, message = '', none_phrase = 'no limit', min = 0, max = 1000000, unit = None, multiplier = 1, num_dimensions = 1 ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._value = ClientGUICommon.NoneableSpinCtrl( self, message = message, none_phrase = none_phrase, min = min, max = max, unit = unit, multiplier = multiplier, num_dimensions = num_dimensions )
        
        self._value.SetValue( value )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._value, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        return self._value.GetValue()
        
    
class EditRegexFavourites( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, regex_favourites ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        regex_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'regex phrase', 24 ), ( 'description', -1 ) ]
        
        self._regexes = ClientGUIListCtrl.BetterListCtrl( regex_listctrl_panel, 'regex_favourites', 8, 48, columns, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
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
        
    
class EditServersideService( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, serverside_service ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        duplicate_serverside_service = serverside_service.Duplicate()
        
        ( self._service_key, self._service_type, name, port, self._dictionary ) = duplicate_serverside_service.ToTuple()
        
        self._service_panel = self._ServicePanel( self, name, port, self._dictionary )
        
        self._panels = []
        
        if self._service_type in HC.RESTRICTED_SERVICES:
            
            self._panels.append( self._ServiceRestrictedPanel( self, self._dictionary ) )
            
            if self._service_type == HC.FILE_REPOSITORY:
                
                self._panels.append( self._ServiceFileRepositoryPanel( self, self._dictionary ) )
                
            
            if self._service_type == HC.SERVER_ADMIN:
                
                self._panels.append( self._ServiceServerAdminPanel( self, self._dictionary ) )
                
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._service_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for panel in self._panels:
            
            QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        ( name, port, dictionary_part ) = self._service_panel.GetValue()
        
        dictionary = self._dictionary.Duplicate()
        
        dictionary.update( dictionary_part )
        
        for panel in self._panels:
            
            dictionary_part = panel.GetValue()
            
            dictionary.update( dictionary_part )
            
        
        return HydrusNetwork.GenerateService( self._service_key, self._service_type, name, port, dictionary )
        
    
    class _ServicePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, name, port, dictionary ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'basic information' )
            
            self._name = QW.QLineEdit( self )
            self._port = QP.MakeQSpinBox( self, min=1, max=65535 )
            self._upnp_port = ClientGUICommon.NoneableSpinCtrl( self, 'external upnp port', none_phrase = 'do not forward port', min = 1, max = 65535 )
            
            self._bandwidth_tracker_st = ClientGUICommon.BetterStaticText( self )
            
            #
            
            self._name.setText( name )
            self._port.setValue( port )
            
            upnp_port = dictionary[ 'upnp_port' ]
            
            self._upnp_port.SetValue( upnp_port )
            
            bandwidth_tracker = dictionary[ 'bandwidth_tracker' ]
            
            bandwidth_text = bandwidth_tracker.GetCurrentMonthSummary()
            
            self._bandwidth_tracker_st.setText( bandwidth_text )
            
            #
            
            rows = []
            
            rows.append( ( 'name: ', self._name ) )
            rows.append( ( 'port: ', self._port ) )
            rows.append( ( 'upnp port: ', self._upnp_port ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self.Add( self._bandwidth_tracker_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        def GetValue( self ):
            
            dictionary_part = {}
            
            name = self._name.text()
            port = self._port.value()
            
            upnp_port = self._upnp_port.GetValue()
            
            dictionary_part[ 'upnp_port' ] = upnp_port
            
            return ( name, port, dictionary_part )
            
        
    
    class _ServiceRestrictedPanel( QW.QWidget ):
        
        def __init__( self, parent, dictionary ):
            
            QW.QWidget.__init__( self, parent )
            
            bandwidth_rules = dictionary[ 'bandwidth_rules' ]
            
            self._bandwidth_rules = ClientGUIControls.BandwidthRulesCtrl( self, bandwidth_rules )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._bandwidth_rules, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
        
        def GetValue( self ):
            
            dictionary_part = {}
            
            dictionary_part[ 'bandwidth_rules' ] = self._bandwidth_rules.GetValue()
            
            return dictionary_part
            
        
    
    class _ServiceFileRepositoryPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, dictionary ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'file repository' )
            
            self._log_uploader_ips = QW.QCheckBox( self )
            self._max_storage = ClientGUIControls.NoneableBytesControl( self, initial_value = 5 * 1024 * 1024 * 1024 )
            
            #
            
            log_uploader_ips = dictionary[ 'log_uploader_ips' ]
            max_storage = dictionary[ 'max_storage' ]
            
            self._log_uploader_ips.setChecked( log_uploader_ips )
            self._max_storage.SetValue( max_storage )
            
            #
            
            rows = []
            
            rows.append( ( 'log file uploader IP addresses?: ', self._log_uploader_ips ) )
            rows.append( ( 'max file storage: ', self._max_storage ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        def GetValue( self ):
            
            dictionary_part = {}
            
            log_uploader_ips = self._log_uploader_ips.isChecked()
            max_storage = self._max_storage.GetValue()
            
            dictionary_part[ 'log_uploader_ips' ] = log_uploader_ips
            dictionary_part[ 'max_storage' ] = max_storage
            
            return dictionary_part
            
        
    
    class _ServiceServerAdminPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, dictionary ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'server-wide bandwidth' )
            
            self._bandwidth_tracker_st = ClientGUICommon.BetterStaticText( self )
            
            bandwidth_rules = dictionary[ 'server_bandwidth_rules' ]
            
            self._bandwidth_rules = ClientGUIControls.BandwidthRulesCtrl( self, bandwidth_rules )
            
            #
            
            bandwidth_tracker = dictionary[ 'server_bandwidth_tracker' ]
            
            bandwidth_text = bandwidth_tracker.GetCurrentMonthSummary()
            
            self._bandwidth_tracker_st.setText( bandwidth_text )
            
            #
            
            self.Add( self._bandwidth_tracker_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._bandwidth_rules, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        def GetValue( self ):
            
            dictionary_part = {}
            
            bandwidth_rules = self._bandwidth_rules.GetValue()
            
            dictionary_part[ 'server_bandwidth_rules' ] = bandwidth_rules
            
            return dictionary_part
            
        
    
class EditSubscriptionPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, subscription ):
        
        subscription = subscription.Duplicate()
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_subscription = subscription
        
        #
        
        self._name = QW.QLineEdit( self )
        self._delay_st = ClientGUICommon.BetterStaticText( self )
        
        #
        
        ( name, gug_key_and_name, queries, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, self._no_work_until, self._no_work_until_reason ) = subscription.ToTuple()
        
        self._query_panel = ClientGUICommon.StaticBox( self, 'site and queries' )
        
        self._gug_key_and_name = ClientGUIImport.GUGKeyAndNameSelector( self._query_panel, gug_key_and_name )
        
        queries_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._query_panel )
        
        columns = [ ( 'name/query', 20 ), ( 'paused', 8 ), ( 'status', 8 ), ( 'last new file time', 20 ), ( 'last check time', 20 ), ( 'next check time', 20 ), ( 'file velocity', 20 ), ( 'recent delays', 20 ), ( 'items', 13 ) ]
        
        self._queries = ClientGUIListCtrl.BetterListCtrl( queries_panel, 'subscription_queries', 10, 20, columns, self._ConvertQueryToListCtrlTuples, use_simple_delete = True, activation_callback = self._EditQuery )
        
        queries_panel.SetListCtrl( self._queries )
        
        queries_panel.AddButton( 'add', self._AddQuery )
        queries_panel.AddButton( 'copy queries', self._CopyQueries, enabled_only_on_selection = True )
        queries_panel.AddButton( 'paste queries', self._PasteQueries )
        queries_panel.AddButton( 'edit', self._EditQuery, enabled_only_on_selection = True )
        queries_panel.AddDeleteButton()
        queries_panel.AddSeparator()
        queries_panel.AddButton( 'pause/play', self._PausePlay, enabled_only_on_selection = True )
        queries_panel.AddButton( 'retry failed', self._RetryFailed, enabled_check_func = self._ListCtrlCanRetryFailed )
        queries_panel.AddButton( 'retry ignored', self._RetryIgnored, enabled_check_func = self._ListCtrlCanRetryIgnored )
        queries_panel.AddButton( 'check now', self._CheckNow, enabled_check_func = self._ListCtrlCanCheckNow )
        queries_panel.AddButton( 'reset cache', self._ResetCache, enabled_check_func = self._ListCtrlCanResetCache )
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            queries_panel.AddSeparator()
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'show', 'Show quality info.', self._ShowQualityInfo ) )
            menu_items.append( ( 'normal', 'copy csv data to clipboard', 'Copy quality info to clipboard.', self._CopyQualityInfo ) )
            
            queries_panel.AddMenuButton( 'quality info', menu_items, enabled_only_on_selection = True )
            
        
        self._checker_options = ClientGUIImport.CheckerOptionsButton( self._query_panel, checker_options, update_callable = self._CheckerOptionsUpdated )
        
        #
        
        self._file_limits_panel = ClientGUICommon.StaticBox( self, 'file limits' )
        
        message = '''****Subscriptions are not for large one-time syncs****

tl;dr: Do not change the checker options or file limits until you really know what you are doing. The limits are now only 1000 (10000 in advanced mode) anyway, but you should leave them at 100/100.

A subscription will start at a site's newest files and keep searching further and further back into the past. It will stop naturally if it reaches the end of results or starts to see files it saw in a previous check (and so assumes it has 'caught up' to where it was before). It will stop 'artificially' if it finds enough new files to hit the file limits here.

Unless you have a very special reason, it is important to keep these file limit numbers low. Being automated, subscriptions typically run when you are not looking at the client, and if they go wrong, it is good to have some brakes to stop them going very wrong.

First of all, making sure you only get a few dozen or hundred on the first check means you do not spend twenty minutes fetching all the search's thousands of file URLs that you may well have previously downloaded, but it is even more important for regular checks, where the sub is trying to find where it got to before: if a site changes its URL format (say from artistname.deviantart.com to deviantart.com/artistname) or changes its markup or otherwise starts delivering unusual results, the subscription may not realise it is seeing the wrong urls and will keep syncing until it hits its regular limit. If the periodic limit is 100, this is no big deal--you'll likely get a popup message out of it and might need to update the respective downloader--but if it were 60000 (or infinite, and the site were somehow serving you random/full results!), you could run into a huge problem completely by accident.

Subscription sync searches are somewhat 'fragile' (they cannot pause/resume the gallery pagewalk, only completely cancel), so it is best if they are short--say, no more than five pages. It is better for a sub to pick up a small number of new files every few weeks than trying to catch up in a giant rush once a year.

If you are not experienced with subscriptions, I strongly suggest you set these to something like 100 for the first check and 100 thereafter, which is likely your default. This works great for typical artist and character queries.

If you want to get all of an artist's files from a site, use the manual gallery download page first. A good routine is to check that you have the right search text and it all works correctly and that you know what tags you want, and then once that big queue is fully downloaded synced, start a new sub with the same settings to continue checking for anything posted in future.'''
        
        help_button = ClientGUICommon.BetterBitmapButton( self._file_limits_panel, CC.GlobalPixmaps.help, QW.QMessageBox.information, None, 'Information', message )
        
        help_hbox_1 = ClientGUICommon.WrapInText( help_button, self._file_limits_panel, 'help about file limits -->', QG.QColor( 0, 0, 255 ) )
        
        message = '''****Hitting the normal/periodic limit may or may not be a big deal****

If one of your subscriptions hits the file limit just doing a normal sync, you will get a little popup telling you. It is likely because of:

1) The query has not run in a while, or many new files were suddenly posted, so the backlog of to-be-synced files has built up.

2) The site has changed how it formats file post urls, so the subscription thinks it is seeing new files when it truly is not.

If 1 is true, you might want to increase its periodic limit a little, or speed up its checking times, and fill in whatever gap of files you missing with a manual download page.

But if 2 is--and is also perhaps accompanied by many 'could not parse' errors--the maintainer for the site's download parser (hydrus dev or whoever), would be interested in knowing what has happened so they can roll out a fix.'.'''
        
        help_button = ClientGUICommon.BetterBitmapButton( self._file_limits_panel, CC.GlobalPixmaps.help, QW.QMessageBox.information, None, 'Information', message )
        
        help_hbox_2 = ClientGUICommon.WrapInText( help_button, self._file_limits_panel, 'help about hitting the normal file limit -->', QG.QColor( 0, 0, 255 ) )
        
        if HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            limits_max = 10000
            
        else:
            
            limits_max = 1000
            
        
        self._initial_file_limit = QP.MakeQSpinBox( self._file_limits_panel, min=1, max=limits_max )
        self._initial_file_limit.setToolTip( 'The first sync will add no more than this many URLs.' )
        
        self._periodic_file_limit = QP.MakeQSpinBox( self._file_limits_panel, min=1, max=limits_max )
        self._periodic_file_limit.setToolTip( 'Normal syncs will add no more than this many URLs, stopping early if they find several URLs the query has seen before.' )
        
        self._file_presentation_panel = ClientGUICommon.StaticBox( self, 'presentation' )
        
        self._show_a_popup_while_working = QW.QCheckBox( self._file_presentation_panel )
        self._show_a_popup_while_working.setToolTip( 'Careful with this! Leave it on to begin with, just in case it goes wrong!' )
        
        self._publish_files_to_popup_button = QW.QCheckBox( self._file_presentation_panel )
        self._publish_files_to_page = QW.QCheckBox( self._file_presentation_panel )
        self._publish_label_override = ClientGUICommon.NoneableTextCtrl( self._file_presentation_panel, none_phrase = 'no, use subscription name' )
        self._merge_query_publish_events = QW.QCheckBox( self._file_presentation_panel )
        
        tt = 'This is great to merge multiple subs to a combined location!'
        
        self._publish_label_override.setToolTip( tt )
        
        tt = 'If unchecked, each query will produce its own \'subscription_name: query\' button or page.'
        
        self._merge_query_publish_events.setToolTip( tt )
        
        #
        
        self._control_panel = ClientGUICommon.StaticBox( self, 'control' )
        
        self._paused = QW.QCheckBox( self._control_panel )
        
        #
        
        show_downloader_options = True
        
        self._file_import_options = ClientGUIImport.FileImportOptionsButton( self, file_import_options, show_downloader_options )
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self, tag_import_options, show_downloader_options, allow_default_selection = True )
        
        #
        
        self._name.setText( name )
        
        self._queries.AddDatas( queries )
        
        self._queries.Sort()
        
        self._initial_file_limit.setValue( initial_file_limit )
        self._periodic_file_limit.setValue( periodic_file_limit )
        
        ( show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events ) = subscription.GetPresentationOptions()
        
        self._show_a_popup_while_working.setChecked( show_a_popup_while_working )
        self._publish_files_to_popup_button.setChecked( publish_files_to_popup_button )
        self._publish_files_to_page.setChecked( publish_files_to_page )
        self._publish_label_override.SetValue( publish_label_override )
        self._merge_query_publish_events.setChecked( merge_query_publish_events )
        
        self._paused.setChecked( paused )
        
        #
        
        self._query_panel.Add( self._gug_key_and_name, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._query_panel.Add( queries_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._query_panel.Add( self._checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'on first check, get at most this many files: ', self._initial_file_limit ) )
        rows.append( ( 'on normal checks, get at most this many newer files: ', self._periodic_file_limit ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._file_limits_panel, rows )
        
        self._file_limits_panel.Add( help_hbox_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._file_limits_panel.Add( help_hbox_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._file_limits_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'show a popup while working: ', self._show_a_popup_while_working ) )
        rows.append( ( 'publish new files to a popup button: ', self._publish_files_to_popup_button ) )
        rows.append( ( 'publish new files to a page: ', self._publish_files_to_page ) )
        rows.append( ( 'publish to a specific label: ', self._publish_label_override ) )
        rows.append( ( 'publish all queries to the same page/popup button: ', self._merge_query_publish_events ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._file_presentation_panel, rows )
        
        self._file_presentation_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'currently paused: ', self._paused ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._control_panel, rows )
        
        self._control_panel.Add( gridbox, CC.FLAGS_LONE_BUTTON )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, ClientGUICommon.WrapInText(self._name,self,'name: '), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._delay_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._query_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._control_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_limits_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_presentation_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        self._UpdateDelayText()
        
    
    def _AddQuery( self ):
        
        gug_key_and_name = self._gug_key_and_name.GetValue()
        
        initial_search_text = HG.client_controller.network_engine.domain_manager.GetInitialSearchText( gug_key_and_name )
        
        query = ClientImportSubscriptions.SubscriptionQuery( initial_search_text )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit subscription query' ) as dlg:
            
            panel = EditSubscriptionQueryPanel( dlg, query )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                query = panel.GetValue()
                
                query_text = query.GetQueryText()
                
                if query_text in self._GetCurrentQueryTexts():
                    
                    QW.QMessageBox.warning( self, 'Warning', 'You already have a query for "'+query_text+'", so nothing new has been added.' )
                    
                    return
                    
                
                self._queries.AddDatas( ( query, ) )
                
            
        
    
    def _CheckerOptionsUpdated( self, checker_options ):
        
        for query in self._queries.GetData():
            
            query.UpdateNextCheckTime( checker_options )
            
        
        self._queries.UpdateDatas()
        
    
    def _CheckNow( self ):
        
        selected_queries = self._queries.GetData( only_selected = True )
        
        for query in selected_queries:
            
            query.CheckNow()
            
        
        self._queries.UpdateDatas( selected_queries )
        
        self._queries.Sort()
        
        self._no_work_until = 0
        
        self._UpdateDelayText()
        
    
    def _ConvertQueryToListCtrlTuples( self, query ):
        
        ( query_text, check_now, last_check_time, next_check_time, paused, status ) = query.ToTuple()
        
        name = query.GetHumanName()
        pretty_name = name
        
        if paused:
            
            pretty_paused = 'yes'
            
        else:
            
            pretty_paused = ''
            
        
        if status == ClientImporting.CHECKER_STATUS_OK:
            
            pretty_status = 'ok'
            
        else:
            
            pretty_status = 'dead'
            
        
        file_seed_cache = query.GetFileSeedCache()
        
        last_new_file_time = file_seed_cache.GetLatestAddedTime()
        
        if last_new_file_time is None or last_new_file_time == 0:
            
            pretty_last_new_file_time = 'n/a'
            
        else:
            
            pretty_last_new_file_time = HydrusData.TimestampToPrettyTimeDelta( last_new_file_time )
            
        
        if last_check_time is None or last_check_time == 0:
            
            pretty_last_check_time = '(initial check has not yet occurred)'
            
        else:
            
            pretty_last_check_time = HydrusData.TimestampToPrettyTimeDelta( last_check_time )
            
        
        pretty_next_check_time = query.GetNextCheckStatusString()
        
        checker_options = self._checker_options.GetValue()
        
        file_velocity = checker_options.GetRawCurrentVelocity( query.GetFileSeedCache(), last_check_time )
        pretty_file_velocity = checker_options.GetPrettyCurrentVelocity( query.GetFileSeedCache(), last_check_time, no_prefix = True )
        
        estimate = query.GetBandwidthWaitingEstimate( self._original_subscription.GetName() )
        
        if estimate == 0:
            
            pretty_delay = ''
            delay = 0
            
        else:
            
            pretty_delay = 'bandwidth: ' + HydrusData.TimeDeltaToPrettyTimeDelta( estimate )
            delay = estimate
            
        
        ( file_status, simple_status, ( num_done, num_total ) ) = file_seed_cache.GetStatus()
        
        items = ( num_total, num_done )
        
        pretty_items = simple_status
        
        sort_last_new_file_time = ClientGUIListCtrl.SafeNoneInt( last_new_file_time )
        sort_last_check_time = ClientGUIListCtrl.SafeNoneInt( last_check_time )
        sort_next_check_time = ClientGUIListCtrl.SafeNoneInt( next_check_time )
        
        display_tuple = ( pretty_name, pretty_paused, pretty_status, pretty_last_new_file_time, pretty_last_check_time, pretty_next_check_time, pretty_file_velocity, pretty_delay, pretty_items )
        sort_tuple = ( name, paused, status, sort_last_new_file_time, sort_last_check_time, sort_next_check_time, file_velocity, delay, items )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopyQueries( self ):
        
        query_texts = []
        
        for query in self._queries.GetData( only_selected = True ):
            
            query_texts.append( query.GetQueryText() )
            
        
        clipboard_text = os.linesep.join( query_texts )
        
        if len( clipboard_text ) > 0:
            
            HG.client_controller.pub( 'clipboard', 'text', clipboard_text )
            
        
    
    def _EditQuery( self ):
        
        selected_queries = self._queries.GetData( only_selected = True )
        
        for old_query in selected_queries:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit subscription query' ) as dlg:
                
                panel = EditSubscriptionQueryPanel( dlg, old_query )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_query = panel.GetValue()
                    
                    edited_query_text = edited_query.GetQueryText()
                    
                    if edited_query_text != old_query.GetQueryText() and edited_query_text in self._GetCurrentQueryTexts():
                        
                        QW.QMessageBox.warning( self, 'Warning', 'You already have a query for "'+edited_query_text+'"! The edit you just made will not be saved.' )
                        
                        break
                        
                    
                    self._queries.DeleteDatas( ( old_query, ) )
                    
                    self._queries.AddDatas( ( edited_query, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._queries.Sort()
        
    
    def _GetCurrentQueryTexts( self ):
        
        query_strings = set()
        
        for query in self._queries.GetData():
            
            query_strings.add( query.GetQueryText() )
            
        
        return query_strings
        
    
    def _CopyQualityInfo( self ):
        
        data = self._GetQualityInfo()
        
        data_strings = []
        
        for ( name, num_inbox, num_archived, num_deleted ) in data:
            
            if num_archived + num_deleted > 0:
                
                percent = HydrusData.ConvertFloatToPercentage( num_archived / ( num_archived + num_deleted ) )
                
            else:
                
                percent = '0.0%'
                
            
            data_string = '{},{},{},{},{}'.format( name, HydrusData.ToHumanInt( num_inbox ), HydrusData.ToHumanInt( num_archived ), HydrusData.ToHumanInt( num_deleted ), percent )
            
            data_strings.append( data_string )
            
        
        text = os.linesep.join( data_strings )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _GetQualityInfo( self ):
        
        data = []
        
        for query in self._queries.GetData( only_selected = True ):
            
            fsc = query.GetFileSeedCache()
            
            hashes = fsc.GetHashes()
            
            media_results = HG.client_controller.Read( 'media_results', hashes )
            
            num_inbox = 0
            num_archived = 0
            num_deleted = 0
            
            for media_result in media_results:
                
                lm = media_result.GetLocationsManager()
                
                if lm.IsLocal() and not lm.IsTrashed():
                    
                    if media_result.GetInbox():
                        
                        num_inbox += 1
                        
                    else:
                        
                        num_archived += 1
                        
                    
                else:
                    
                    num_deleted += 1
                    
                
            
            data.append( ( query.GetHumanName(), num_inbox, num_archived, num_deleted ) )
            
        
        return data
        
    
    def _ShowQualityInfo( self ):
        
        data = self._GetQualityInfo()
        
        data_strings = []
        
        for ( name, num_inbox, num_archived, num_deleted ) in data:
            
            data_string = '{}: inbox {} | archive {} | deleted {}'.format( name, HydrusData.ToHumanInt( num_inbox ), HydrusData.ToHumanInt( num_archived ), HydrusData.ToHumanInt( num_deleted ) )
            
            if num_archived + num_deleted > 0:
                
                data_string += ' | good {}'.format( HydrusData.ConvertFloatToPercentage( num_archived / ( num_archived + num_deleted ) ) )
                
            
            data_strings.append( data_string )
            
        
        message = os.linesep.join( data_strings )
        
        QW.QMessageBox.information( self, 'Information', message )
        
    
    def _ListCtrlCanCheckNow( self ):
        
        for query in self._queries.GetData( only_selected = True ):
            
            if query.CanCheckNow():
                
                return True
                
            
        
        return False
        
    
    def _ListCtrlCanResetCache( self ):
        
        for query in self._queries.GetData( only_selected = True ):
            
            if not query.IsInitialSync():
                
                return True
                
            
        
        return False
        
    
    def _ListCtrlCanRetryFailed( self ):
        
        for query in self._queries.GetData( only_selected = True ):
            
            if query.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _ListCtrlCanRetryIgnored( self ):
        
        for query in self._queries.GetData( only_selected = True ):
            
            if query.CanRetryIgnored():
                
                return True
                
            
        
        return False
        
    
    def _PasteQueries( self ):
        
        message = 'This will add new queries by pulling them from your clipboard. It assumes they are currently in your clipboard and newline separated. Is that ok?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
        try:
            
            text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            query_texts = HydrusText.DeserialiseNewlinedTexts( text )
            
            current_query_texts = self._GetCurrentQueryTexts()
            
            already_existing_query_texts = list( current_query_texts.intersection( query_texts ) )
            new_query_texts = list( set( query_texts ).difference( current_query_texts ) )
            
            already_existing_query_texts.sort()
            new_query_texts.sort()
            
            if len( already_existing_query_texts ) > 0:
                
                if len( already_existing_query_texts ) > 50:
                    
                    message = '{} queries were already in the subscription, so they need not be added.'.format( HydrusData.ToHumanInt( len( already_existing_query_texts ) ) )
                    
                else:
                    
                    if len( already_existing_query_texts ) > 5:
                        
                        aeqt_separator = ', '
                        
                    else:
                        
                        aeqt_separator = os.linesep
                        
                    
                    message = 'The queries:'
                    message += os.linesep * 2
                    message += aeqt_separator.join( already_existing_query_texts )
                    message += os.linesep * 2
                    message += 'Were already in the subscription, so they need not be added.'
                    
                
                if len( new_query_texts ) > 0:
                    
                    if len( new_query_texts ) > 50:
                        
                        message = '{} queries were new and will be added.'.format( HydrusData.ToHumanInt( len( new_query_texts ) ) )
                        
                    else:
                        
                        if len( new_query_texts ) > 5:
                            
                            nqt_separator = ', '
                            
                        else:
                            
                            nqt_separator = os.linesep
                            
                        
                        message += os.linesep * 2
                        message += 'The queries:'
                        message += os.linesep * 2
                        message += nqt_separator.join( new_query_texts )
                        message += os.linesep * 2
                        message += 'Were new and will be added.'
                        
                    
                
                QW.QMessageBox.information( self, 'Information', message )
                
            
            queries = [ ClientImportSubscriptions.SubscriptionQuery( query_text ) for query_text in new_query_texts ]
            
            self._queries.AddDatas( queries )
            
        except:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
        
    
    def _PausePlay( self ):
        
        selected_queries = self._queries.GetData( only_selected = True )
        
        for query in selected_queries:
            
            query.PausePlay()
            
        
        self._queries.UpdateDatas( selected_queries )
        
    
    def _ResetCache( self ):
        
        message = 'Resetting these queries will delete all their cached urls, meaning when the subscription next runs, they will have to download all those links over again. This may be expensive in time and data. Only do this if you know what it means. Do you want to do it?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            selected_queries = self._queries.GetData( only_selected = True )
            
            for query in selected_queries:
                
                query.Reset()
                
            
            self._queries.UpdateDatas( selected_queries )
            
        
    
    def _RetryFailed( self ):
        
        selected_queries = self._queries.GetData( only_selected = True )
        
        for query in selected_queries:
            
            query.RetryFailures()
            
        
        self._queries.UpdateDatas( selected_queries )
        
        self._no_work_until = 0
        
        self._UpdateDelayText()
        
    
    def _RetryIgnored( self ):
        
        selected_queries = self._queries.GetData( only_selected = True )
        
        for query in selected_queries:
            
            query.RetryIgnored()
            
        
        self._queries.UpdateDatas( selected_queries )
        
    
    def _UpdateDelayText( self ):
        
        if HydrusData.TimeHasPassed( self._no_work_until ):
            
            status = 'no recent errors'
            
        else:
            
            status = 'delayed--retrying ' + HydrusData.TimestampToPrettyTimeDelta( self._no_work_until, just_now_threshold = 0 ) + ' because: ' + self._no_work_until_reason
            
        
        self._delay_st.setText( status )
        
    
    def GetValue( self ):
        
        name = self._name.text()
        
        subscription = ClientImportSubscriptions.Subscription( name )
        
        gug_key_and_name = self._gug_key_and_name.GetValue()
        
        queries = self._queries.GetData()
        
        initial_file_limit = self._initial_file_limit.value()
        periodic_file_limit = self._periodic_file_limit.value()
        
        paused = self._paused.isChecked()
        
        checker_options = self._checker_options.GetValue()
        file_import_options = self._file_import_options.GetValue()
        tag_import_options = self._tag_import_options.GetValue()
        
        subscription.SetTuple( gug_key_and_name, queries, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, self._no_work_until )
        
        show_a_popup_while_working = self._show_a_popup_while_working.isChecked()
        publish_files_to_popup_button = self._publish_files_to_popup_button.isChecked()
        publish_files_to_page = self._publish_files_to_page.isChecked()
        publish_label_override = self._publish_label_override.GetValue()
        merge_query_publish_events = self._merge_query_publish_events.isChecked()
        
        subscription.SetPresentationOptions( show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events )
        
        return subscription
        
    
class EditSubscriptionQueryPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, query ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._original_query = query
        
        self._status_st = ClientGUICommon.BetterStaticText( self )
        
        st_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._status_st, 50 )
        
        self._status_st.setMinimumWidth( st_width )
        
        self._display_name = ClientGUICommon.NoneableTextCtrl( self, none_phrase = 'show query text' )
        self._query_text = QW.QLineEdit( self )
        self._check_now = QW.QCheckBox( self )
        self._paused = QW.QCheckBox( self )
        
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self, HG.client_controller )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self, HG.client_controller, True, True )
        
        tag_import_options = self._original_query.GetTagImportOptions()
        show_downloader_options = False # just for additional tags, no parsing gubbins needed
        
        self._tag_import_options = ClientGUIImport.TagImportOptionsButton( self, tag_import_options, show_downloader_options )
        
        #
        
        ( query_text, check_now, self._last_check_time, self._next_check_time, paused, self._status ) = self._original_query.ToTuple()
        
        display_name = self._original_query.GetDisplayName()
        
        self._display_name.SetValue( display_name )
        
        self._query_text.setText( query_text )
        
        self._check_now.setChecked( check_now )
        
        self._paused.setChecked( paused )
        
        self._file_seed_cache = self._original_query.GetFileSeedCache().Duplicate()
        
        self._file_seed_cache_control.SetFileSeedCache( self._file_seed_cache )
        
        self._gallery_seed_log = self._original_query.GetGallerySeedLog().Duplicate()
        
        self._gallery_seed_log_control.SetGallerySeedLog( self._gallery_seed_log )
        
        #
        
        rows = []
        
        rows.append( ( 'optional display name: ', self._display_name ) )
        rows.append( ( 'query text: ', self._query_text ) )
        rows.append( ( 'check now: ', self._check_now ) )
        rows.append( ( 'paused: ', self._paused ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_import_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._check_now.clicked.connect( self._UpdateStatus )
        self._paused.clicked.connect( self._UpdateStatus )
        
        self._UpdateStatus()
        
        self._query_text.selectAll()
        
        QP.CallAfter( self._query_text.setFocus, QC.Qt.OtherFocusReason )
        
    
    def _GetValue( self ):
        
        query = self._original_query.Duplicate()
        
        query.SetQueryAndSeeds( self._query_text.text(), self._file_seed_cache, self._gallery_seed_log )
        
        query.SetPaused( self._paused.isChecked() )
        
        query.SetCheckNow( self._check_now.isChecked() )
        
        query.SetDisplayName( self._display_name.GetValue() )
        
        query.SetTagImportOptions( self._tag_import_options.GetValue() )
        
        return query
        
    
    def _UpdateStatus( self ):
        
        query = self._GetValue()
        
        self._status_st.setText( 'next check: '+query.GetNextCheckStatusString() )
        
    
    def GetValue( self ):
        
        query = self._GetValue()
        
        return query
        
    
class EditSubscriptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, subscriptions, subs_are_globally_paused = False ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        #
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'getting_started_subscriptions.html' ) )
        
        menu_items.append( ( 'normal', 'open the html subscriptions help', 'Open the help page for subscriptions in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalPixmaps.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', QG.QColor( 0, 0, 255 ) )
        
        subscriptions_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', -1 ), ( 'source', 20 ), ( 'query status', 25 ), ( 'last new file time', 20 ), ( 'last checked', 20 ), ( 'recent error/delay?', 20 ), ( 'items', 13 ), ( 'paused', 8 ) ]
        
        self._subscriptions = ClientGUIListCtrl.BetterListCtrl( subscriptions_panel, 'subscriptions', 12, 20, columns, self._ConvertSubscriptionToListCtrlTuples, use_simple_delete = True, activation_callback = self.Edit )
        
        subscriptions_panel.SetListCtrl( self._subscriptions )
        
        subscriptions_panel.AddButton( 'add', self.Add )
        subscriptions_panel.AddButton( 'edit', self.Edit, enabled_only_on_selection = True )
        subscriptions_panel.AddDeleteButton()
        
        subscriptions_panel.AddSeparator()
        
        subscriptions_panel.AddImportExportButtons( ( ClientImportSubscriptions.Subscription, ), self._AddSubscription )
        
        subscriptions_panel.NewButtonRow()
        
        subscriptions_panel.AddButton( 'merge', self.Merge, enabled_check_func = self._CanMerge )
        subscriptions_panel.AddButton( 'separate', self.Separate, enabled_check_func = self._CanSeparate )
        
        subscriptions_panel.AddSeparator()
        
        subscriptions_panel.AddButton( 'pause/resume', self.PauseResume, enabled_only_on_selection = True )
        subscriptions_panel.AddButton( 'retry failures', self.RetryFailures, enabled_check_func = self._CanRetryFailures )
        subscriptions_panel.AddButton( 'retry ignored', self.RetryIgnored, enabled_check_func = self._CanRetryIgnored )
        subscriptions_panel.AddButton( 'scrub delays', self.ScrubDelays, enabled_check_func = self._CanScrubDelays )
        subscriptions_panel.AddButton( 'check queries now', self.CheckNow, enabled_check_func = self._CanCheckNow )
        
        subscriptions_panel.AddButton( 'reset', self.Reset, enabled_check_func = self._CanReset )
        
        subscriptions_panel.NewButtonRow()
        
        subscriptions_panel.AddButton( 'select subscriptions', self.SelectSubscriptions )
        subscriptions_panel.AddButton( 'overwrite checker timings', self.SetCheckerOptions, enabled_only_on_selection = True )
        subscriptions_panel.AddButton( 'overwrite tag import options', self.SetTagImportOptions, enabled_only_on_selection = True )
        
        #
        
        self._subscriptions.AddDatas( subscriptions )
        
        self._subscriptions.Sort( 0 )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_BUTTON_SIZER )
        
        message = 'Subscriptions do not work well if they get too large! If any sub has >200,000 items, separate it into smaller pieces immediately!'
        
        st = ClientGUICommon.BetterStaticText( self, message )
        QP.SetForegroundColour( st, ( 127, 0, 0 ) )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if subs_are_globally_paused:
            
            message = 'SUBSCRIPTIONS ARE CURRENTLY GLOBALLY PAUSED! CHECK THE NETWORK MENU TO UNPAUSE THEM.'
            
            st = ClientGUICommon.BetterStaticText( self, message )
            QP.SetForegroundColour( st, (127,0,0) )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        QP.AddToLayout( vbox, subscriptions_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _AddSubscription( self, subscription ):
        
        subscription.SetNonDupeName( self._GetExistingNames() )
        
        self._subscriptions.AddDatas( ( subscription, ) )
        
    
    def _CanCheckNow( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanCheckNow() for subscription in subscriptions )
        
    
    def _CanMerge( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        # only subs with queries can be merged
        
        mergeable_subscriptions = [ subscription for subscription in subscriptions if len( subscription.GetQueries() ) > 0 ]
        
        unique_gug_names = { subscription.GetGUGKeyAndName()[1] for subscription in mergeable_subscriptions }
        
        # if there are fewer, there must be dupes, so we must be able to merge
        
        return len( unique_gug_names ) < len( subscriptions )
        
    
    def _CanReset( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanReset() for subscription in subscriptions )
        
    
    def _CanRetryFailures( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanRetryFailures() for subscription in subscriptions )
        
    
    def _CanRetryIgnored( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanRetryIgnored() for subscription in subscriptions )
        
    
    def _CanScrubDelays( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        return True in ( subscription.CanScrubDelay() for subscription in subscriptions )
        
    
    def _CanSeparate( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        if len( subscriptions ) != 1:
            
            return False
            
        
        subscription = subscriptions[0]
        
        if len( subscription.GetQueries() ) > 1:
            
            return True
            
        
        return False
        
    
    def _ConvertSubscriptionToListCtrlTuples( self, subscription ):
        
        ( name, gug_key_and_name, queries, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, no_work_until, no_work_until_reason ) = subscription.ToTuple()
        
        pretty_site = gug_key_and_name[1]
        
        period = 100
        pretty_period = 'fix this'
        
        if len( queries ) > 0:
            
            last_new_file_time = max( ( query.GetLatestAddedTime() for query in queries ) )
            
            last_checked = max( ( query.GetLastChecked() for query in queries ) )
            
            
        else:
            
            last_new_file_time = 0
            
            last_checked = 0
            
        
        if last_new_file_time is None or last_new_file_time == 0:
            
            pretty_last_new_file_time = 'n/a'
            
        else:
            
            pretty_last_new_file_time = HydrusData.TimestampToPrettyTimeDelta( last_new_file_time )
            
        
        if last_checked is None or last_checked == 0:
            
            pretty_last_checked = 'n/a'
            
        else:
            
            pretty_last_checked = HydrusData.TimestampToPrettyTimeDelta( last_checked )
            
        
        #
        
        num_queries = len( queries )
        num_dead = 0
        num_paused = 0
        
        for query in queries:
            
            if query.IsDead():
                
                num_dead += 1
                
            elif query.IsPaused():
                
                num_paused += 1
                
            
        
        num_ok = num_queries - ( num_dead + num_paused )
        
        status = ( num_queries, num_paused, num_dead )
        
        if num_queries == 0:
            
            pretty_status = 'no queries'
            
        else:
            
            status_components = [ HydrusData.ToHumanInt( num_ok ) + ' working' ]
            
            if num_paused > 0:
                
                status_components.append( HydrusData.ToHumanInt( num_paused ) + ' paused' )
                
            
            if num_dead > 0:
                
                status_components.append( HydrusData.ToHumanInt( num_dead ) + ' dead' )
                
            
            pretty_status = ', '.join( status_components )
            
        
        #
        
        if HydrusData.TimeHasPassed( no_work_until ):
            
            ( min_estimate, max_estimate ) = subscription.GetBandwidthWaitingEstimateMinMax()
            
            if max_estimate == 0: # don't seem to be any delays of any kind
                
                pretty_delay = ''
                delay = 0
                
            elif min_estimate == 0: # some are good to go, but there are delays
                
                pretty_delay = 'bandwidth: some ok, some up to ' + HydrusData.TimeDeltaToPrettyTimeDelta( max_estimate )
                delay = max_estimate
                
            else:
                
                if min_estimate == max_estimate: # probably just one query, and it is delayed
                    
                    pretty_delay = 'bandwidth: up to ' + HydrusData.TimeDeltaToPrettyTimeDelta( max_estimate )
                    delay = max_estimate
                    
                else:
                    
                    pretty_delay = 'bandwidth: from ' + HydrusData.TimeDeltaToPrettyTimeDelta( min_estimate ) + ' to ' + HydrusData.TimeDeltaToPrettyTimeDelta( max_estimate )
                    delay = max_estimate
                    
                
            
        else:
            
            pretty_delay = 'delayed--retrying ' + HydrusData.TimestampToPrettyTimeDelta( no_work_until, just_now_threshold = 0 ) + ' - because: ' + no_work_until_reason
            delay = HydrusData.GetTimeDeltaUntilTime( no_work_until )
            
        
        file_seed_caches = [ query.GetFileSeedCache() for query in queries ]
        
        ( queries_status, queries_simple_status, ( num_done, num_total ) ) = ClientImportFileSeeds.GenerateFileSeedCachesStatus( file_seed_caches )
        
        items = ( num_total, num_done )
        
        pretty_items = queries_simple_status
        
        if paused:
            
            pretty_paused = 'yes'
            
        else:
            
            pretty_paused = ''
            
        
        sort_last_new_file_time = ClientGUIListCtrl.SafeNoneInt( last_new_file_time )
        sort_last_checked = ClientGUIListCtrl.SafeNoneInt( last_checked )
        
        display_tuple = ( name, pretty_site, pretty_status, pretty_last_new_file_time, pretty_last_checked, pretty_delay, pretty_items, pretty_paused )
        sort_tuple = ( name, pretty_site, status, sort_last_new_file_time, sort_last_checked, delay, items, paused )
        
        return ( display_tuple, sort_tuple )
        
    
    def _GetExistingNames( self ):
        
        subscriptions = self._subscriptions.GetData()
        
        names = { subscription.GetName() for subscription in subscriptions }
        
        return names
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for subscription in self._subscriptions.GetData( only_selected = True ):
            
            to_export.append( subscription )
            
        
        if len( to_export ) == 0:
            
            return None
            
        elif len( to_export ) == 1:
            
            return to_export[0]
            
        else:
            
            return to_export
            
        
    
    def _ImportObject( self, obj ):
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                self._ImportObject( sub_obj )
                
            
        else:
            
            if isinstance( obj, ClientImportSubscriptions.Subscription ):
                
                subscription = obj
                
                subscription.SetNonDupeName( self._GetExistingNames() )
                
                self._subscriptions.AddDatas( ( subscription, ) )
                
            else:
                
                QW.QMessageBox.warning( self, 'Warning', 'That was not a subscription--it was a: '+type(obj).__name__ )
                
            
        
    
    def Add( self ):
        
        gug_key_and_name = HG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName()
        
        empty_subscription = ClientImportSubscriptions.Subscription( 'new subscription', gug_key_and_name = gug_key_and_name )
        
        frame_key = 'edit_subscription_dialog'
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit subscription', frame_key ) as dlg_edit:
            
            panel = EditSubscriptionPanel( dlg_edit, empty_subscription )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.Accepted:
                
                new_subscription = panel.GetValue()
                
                self._AddSubscription( new_subscription )
                
                self._subscriptions.Sort()
                
            
        
    
    def CheckNow( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subscriptions:
            
            subscription.CheckNow()
            
        
        self._subscriptions.UpdateDatas( subscriptions )
        
    
    def Edit( self ):
        
        subs_to_edit = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subs_to_edit:
            
            frame_key = 'edit_subscription_dialog'
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit subscription', frame_key ) as dlg:
                
                original_name = subscription.GetName()
                
                panel = EditSubscriptionPanel( dlg, subscription )
                
                dlg.SetPanel( panel )
                
                result = dlg.exec()
                
                if result == QW.QDialog.Accepted:
                    
                    self._subscriptions.DeleteDatas( ( subscription, ) )
                    
                    edited_subscription = panel.GetValue()
                    
                    edited_subscription.SetNonDupeName( self._GetExistingNames() )
                    
                    self._subscriptions.AddDatas( ( edited_subscription, ) )
                    
                elif dlg.WasCancelled():
                    
                    break
                    
                
            
        
        self._subscriptions.Sort()
        
    
    def GetValue( self ):
        
        subscriptions = self._subscriptions.GetData()
        
        return subscriptions
        
    
    def Merge( self ):
        
        message = 'Are you sure you want to merge the selected subscriptions? This will combine all selected subscriptions that share the same downloader, wrapping all their different queries into one subscription.'
        message += os.linesep * 2
        message += 'This is a big operation, so if it does not do what you expect, hit cancel afterwards!'
        message += os.linesep * 2
        message += 'Please note that all other subscription settings settings (like paused status and file limits and tag options) will be merged as well, so double-check your merged subs\' settings afterwards.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            original_subs = self._subscriptions.GetData( only_selected = True )
            
            potential_mergees = [ sub.Duplicate() for sub in original_subs ]
            
            mergeable_groups = []
            merged_subs = []
            unmergeable_subs = []
            
            while len( potential_mergees ) > 0:
                
                potential_primary = potential_mergees.pop()
                
                ( mergeables_with_our_primary, not_mergeable_with_our_primary ) = potential_primary.GetMergeable( potential_mergees )
                
                if len( mergeables_with_our_primary ) > 0:
                    
                    mergeable_group = []
                    
                    mergeable_group.append( potential_primary )
                    mergeable_group.extend( mergeables_with_our_primary )
                    
                    mergeable_groups.append( mergeable_group )
                    
                else:
                    
                    unmergeable_subs.append( potential_primary )
                    
                
                potential_mergees = not_mergeable_with_our_primary
                
            
            if len( mergeable_groups ) == 0:
                
                QW.QMessageBox.information( self, 'Information', 'Unfortunately, none of those subscriptions appear to be mergeable!' )
                
                return
                
            
            for mergeable_group in mergeable_groups:
                
                mergeable_group.sort( key = lambda sub: sub.GetName() )
                
                choice_tuples = [ ( sub.GetName(), sub ) for sub in mergeable_group ]
                
                try:
                    
                    primary_sub = ClientGUIDialogsQuick.SelectFromList( self, 'select the primary subscription--into which to merge the others', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
                mergeable_group.remove( primary_sub )
                
                primary_sub.Merge( mergeable_group )
                
                primary_sub_name = primary_sub.GetName()
                
                message = primary_sub_name + ' was able to merge ' + HydrusData.ToHumanInt( len( mergeable_group ) ) + ' other subscriptions. If you wish to change its name, do so here.'
                
                with ClientGUIDialogs.DialogTextEntry( self, message, default = primary_sub_name ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        name = dlg.GetValue()
                        
                        primary_sub.SetName( name )
                        
                    
                    # don't care about a cancel here--we'll take that as 'I didn't want to change its name', not 'abort'
                    
                
                merged_subs.append( primary_sub )
                
            
            # we are ready to do it
            
            self._subscriptions.DeleteDatas( original_subs )
            
            self._subscriptions.AddDatas( unmergeable_subs )
            
            for merged_sub in merged_subs:
                
                merged_sub.SetNonDupeName( self._GetExistingNames() )
                
                self._subscriptions.AddDatas( ( merged_sub, ) )
                
            
            self._subscriptions.Sort()
            
        
    
    def PauseResume( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subscriptions:
            
            subscription.PauseResume()
            
        
        self._subscriptions.UpdateDatas( subscriptions )
        
    
    def Reset( self ):
        
        message = 'Resetting these subscriptions will delete all their remembered urls, meaning when they next run, they will try to download them all over again. This may be expensive in time and data. Only do it if you are willing to wait. Do you want to do it?'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            subscriptions = self._subscriptions.GetData( only_selected = True )
            
            for subscription in subscriptions:
                
                subscription.Reset()
                
            
            self._subscriptions.UpdateDatas( subscriptions )
            
        
    
    def RetryFailures( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subscriptions:
            
            subscription.RetryFailures()
            
        
        self._subscriptions.UpdateDatas( subscriptions )
        
    
    def RetryIgnored( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subscriptions:
            
            subscription.RetryIgnored()
            
        
        self._subscriptions.UpdateDatas( subscriptions )
        
    
    def ScrubDelays( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        for subscription in subscriptions:
            
            subscription.ScrubDelay()
            
        
        self._subscriptions.UpdateDatas( subscriptions )
        
    
    def SelectSubscriptions( self ):
        
        message = 'This selects subscriptions based on query text. Please enter some search text, and any subscription that has a query that includes that text will be selected.'
        
        with ClientGUIDialogs.DialogTextEntry( self, message ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                search_text = dlg.GetValue()
                
                self._subscriptions.clearSelection()
                
                selectee_subscriptions = []
                
                for subscription in self._subscriptions.GetData():
                    
                    if subscription.HasQuerySearchTextFragment( search_text ):
                        
                        selectee_subscriptions.append( subscription )
                        
                    
                
                self._subscriptions.SelectDatas( selectee_subscriptions )
                
            
        
    
    def Separate( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        if len( subscriptions ) != 1:
            
            QW.QMessageBox.critical( self, 'Error', 'Separate only works if one subscription is selected!' )
            
            return
            
        
        subscription = subscriptions[0]
        
        num_queries = len( subscription.GetQueries() )
        
        if num_queries <= 1:
            
            QW.QMessageBox.critical( self, 'Error', 'Separate only works if the selected subscription has more than one query!' )
            
            return
            
        
        if num_queries > 100:
            
            message = 'This is a large subscription. It is difficult to separate it on a per-query basis, so instead the system will automatically cut it into two halves. Is this ok?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return
                
            
            action = 'half'
            
        elif num_queries > 2:
            
            message = 'Are you sure you want to separate the selected subscriptions? Separating breaks merged subscriptions apart into smaller pieces.'
            yes_tuples = [ ( 'break it in half', 'half' ), ( 'break it all into single-query subscriptions', 'whole' ), ( 'only extract some of the subscription', 'part' ) ]
            
            with ClientGUIDialogs.DialogYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    action = dlg.GetValue()
                    
                else:
                    
                    return
                    
                
            
        else:
            
            action = 'whole'
            
        
        want_post_merge = False
        
        if action == 'part':
            
            queries = subscription.GetQueries()
            
            choice_tuples = [ ( query.GetHumanName(), query, False ) for query in queries ]
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'select the queries to extract' ) as dlg:
                
                panel = EditChooseMultiple( dlg, choice_tuples )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    queries_to_extract = panel.GetValue()
                    
                else:
                    
                    return
                    
                
            
            if len( queries_to_extract ) == num_queries: # the madman selected them all
                
                action = 'whole'
                
            elif len( queries_to_extract ) > 1:
                
                yes_tuples = [ ( 'one new merged subscription', True ), ( 'many subscriptions with only one query', False ) ]
                
                message = 'Do you want the extracted queries to be a new merged subscription, or many subscriptions with only one query?'
                
                with ClientGUIDialogs.DialogYesYesNo( self, message, yes_tuples = yes_tuples, no_label = 'forget it' ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        want_post_merge = dlg.GetValue()
                        
                    else:
                        
                        return
                        
                    
                
            
        
        if action != 'half':
            
            if want_post_merge:
                
                message = 'Please enter the name for the new subscription.'
                
            else:
                
                message = 'Please enter the base name for the new subscriptions. They will be named \'[NAME]: query\'.'
                
            
            with ClientGUIDialogs.DialogTextEntry( self, message, default = subscription.GetName() ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    name = dlg.GetValue()
                    
                else:
                    
                    return
                    
                
            
        
        # ok, let's do it
        
        final_subscriptions = []
        
        self._subscriptions.DeleteDatas( ( subscription, ) )
        
        if action == 'whole':
            
            final_subscriptions.extend( subscription.Separate( name ) )
            
        elif action == 'part':
            
            extracted_subscriptions = list( subscription.Separate( name, queries_to_extract ) )
            
            if want_post_merge:
                
                # it is ok to do a blind merge here since they all share the same settings and will get a new name
                
                primary_sub = extracted_subscriptions.pop()
                
                primary_sub.Merge( extracted_subscriptions )
                
                primary_sub.SetName( name )
                
                final_subscriptions.append( primary_sub )
                
            else:
                
                final_subscriptions.extend( extracted_subscriptions )
                
            
            final_subscriptions.append( subscription )
            
        elif action == 'half':
            
            queries = subscription.GetQueries()
            
            queries_to_extract = queries[ : len( queries ) // 2 ]
            
            name = subscription.GetName()
            
            extracted_subscriptions = list( subscription.Separate( name, queries_to_extract ) )
            
            primary_sub = extracted_subscriptions.pop()
            
            primary_sub.Merge( extracted_subscriptions )
            
            primary_sub.SetName( '{} (A)'.format( name ) )
            subscription.SetName( '{} (B)'.format( name ) )
            
            final_subscriptions.append( primary_sub )
            final_subscriptions.append( subscription )
            
        
        for final_subscription in final_subscriptions:
            
            final_subscription.SetNonDupeName( self._GetExistingNames() )
            
            self._subscriptions.AddDatas( ( final_subscription, ) )
            
        
        self._subscriptions.Sort()
        
    
    def SetCheckerOptions( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        if len( subscriptions ) == 0:
            
            return
            
        
        checker_options = ClientDefaults.GetDefaultCheckerOptions( 'artist subscription' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit check timings' ) as dlg:
            
            panel = ClientGUITime.EditCheckerOptions( dlg, checker_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                checker_options = panel.GetValue()
                
                for subscription in subscriptions:
                    
                    subscription.SetCheckerOptions( checker_options )
                    
                
                self._subscriptions.UpdateDatas( subscriptions )
                
            
        
    
    def SetTagImportOptions( self ):
        
        subscriptions = self._subscriptions.GetData( only_selected = True )
        
        if len( subscriptions ) == 0:
            
            return
            
        
        tag_import_options = HG.client_controller.network_engine.domain_manager.GetDefaultTagImportOptionsForPosts()
        show_downloader_options = True
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit tag import options' ) as dlg:
            
            panel = EditTagImportOptionsPanel( dlg, tag_import_options, show_downloader_options, allow_default_selection = True )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                tag_import_options = panel.GetValue()
                
                for subscription in subscriptions:
                    
                    subscription.SetTagImportOptions( tag_import_options )
                    
                
                self._subscriptions.UpdateDatas( subscriptions )
                
            
        
    
class EditTagDisplayManagerPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_display_manager ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._tag_services = ClientGUICommon.BetterNotebook( self )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._tag_services, 100 )
        
        self._tag_services.setMinimumWidth( min_width )
        
        #
        
        services = list( HG.client_controller.services_manager.GetServices( ( HC.COMBINED_TAG, HC.TAG_REPOSITORY, HC.LOCAL_TAG ) ) )
        
        services.sort( key = lambda s: s.GetName() )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_services, tag_display_manager, service_key )
            
            select = service_key == CC.COMBINED_TAG_SERVICE_KEY
            
            self._tag_services.addTab( page, name )
            if select: self._tag_services.setCurrentWidget( page )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        intro = 'Please note this new system is under construction. It is neither completely functional nor as efficient as intended.'
        
        st = ClientGUICommon.BetterStaticText( self, intro )
        st.setWordWrap( True )
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._tag_services, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        tag_display_manager = ClientTags.TagDisplayManager()
        
        for page in self._tag_services.GetPages():
            
            ( service_key, tag_display_types_to_tag_filters ) = page.GetValue()
            
            for ( tag_display_type, tag_filter ) in tag_display_types_to_tag_filters.items():
                
                tag_display_manager.SetTagFilter( tag_display_type, service_key, tag_filter )
                
            
        
        return tag_display_manager
        
    
    class _Panel( QW.QWidget ):
        
        def __init__( self, parent, tag_display_manager, service_key ):
            
            QW.QWidget.__init__( self, parent )
            
            single_tag_filter = tag_display_manager.GetTagFilter( ClientTags.TAG_DISPLAY_SINGLE_MEDIA, service_key )
            selection_tag_filter = tag_display_manager.GetTagFilter( ClientTags.TAG_DISPLAY_SELECTION_LIST, service_key )
            
            self._service_key = service_key
            
            #
            
            message = 'This filters which tags will show on \'single\' file views such as the media viewer and thumbnail banners.'
            
            self._single_tag_filter_button = ClientGUITags.TagFilterButton( self, message, single_tag_filter, label_prefix = 'tags shown: ' )
            
            message = 'This filters which tags will show on \'selection\' file views such as the \'selection tags\' list on regular search pages.'
            
            self._selection_tag_filter_button = ClientGUITags.TagFilterButton( self, message, selection_tag_filter, label_prefix = 'tags shown: ' )
            
            #
            
            rows = []
            
            rows.append( ( 'Tag filter for single file views: ', self._single_tag_filter_button ) )
            rows.append( ( 'Tag filter for multiple file views: ', self._selection_tag_filter_button ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = QP.VBoxLayout()
            
            if self._service_key == CC.COMBINED_TAG_SERVICE_KEY:
                
                message = 'These filters apply to all tag services.'
                
                QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, message ), CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            QP.AddToLayout( vbox, gridbox )
            
            self.setLayout( vbox )
            
        
        def GetValue( self ):
            
            tag_display_types_to_tag_filters = {}
            
            tag_display_types_to_tag_filters[ ClientTags.TAG_DISPLAY_SINGLE_MEDIA ] = self._single_tag_filter_button.GetValue()
            tag_display_types_to_tag_filters[ ClientTags.TAG_DISPLAY_SELECTION_LIST ] = self._selection_tag_filter_button.GetValue()
            
            return ( self._service_key, tag_display_types_to_tag_filters )
            
        
    
class EditTagImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_import_options, show_downloader_options, allow_default_selection = False ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._show_downloader_options = show_downloader_options
        
        self._service_keys_to_service_tag_import_options_panels = {}
        
        #
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalPixmaps.help, self._ShowHelp )
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
        
        message = 'Any tag that this filter _excludes_ will be considered a blacklisted tag and will stop the file importing.'
        message += os.linesep * 2
        message += 'So if you only want to stop \'scat\' or \'gore\', just add them to the simple blacklist and hit ok. It is worth doing a small test, just to make sure it is all set up how you want.'
        
        self._tag_filter_button = ClientGUITags.TagFilterButton( downloader_options_panel, message, tag_blacklist, is_blacklist = True )
        
        self._services_vbox = QP.VBoxLayout()
        
        #
        
        self._is_default.setChecked( tag_import_options.IsDefault() )
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB() )
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB() )
        
        self._InitialiseServices( tag_import_options )
        
        #
        
        rows = []
        
        rows.append( ( 'rely on the appropriate default tag import options at the time of import: ', self._is_default ) )
        
        gridbox = ClientGUICommon.WrapInGrid( default_panel, rows )
        
        default_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        default_panel.Add( self._load_default_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if not allow_default_selection:
            
            default_panel.hide()
            
        
        #
        
        rows = []
        
        rows.append( ( 'fetch tags even if url recognised and file already in db: ', self._fetch_tags_even_if_url_recognised_and_file_already_in_db ) )
        rows.append( ( 'fetch tags even if hash recognised and file already in db: ', self._fetch_tags_even_if_hash_recognised_and_file_already_in_db ) )
        rows.append( ( 'set file blacklist: ', self._tag_filter_button ) )
        
        gridbox = ClientGUICommon.WrapInGrid( downloader_options_panel, rows )
        
        downloader_options_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        if not self._show_downloader_options:
            
            downloader_options_panel.hide()
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, downloader_options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._services_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self._specific_options_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_button, CC.FLAGS_LONE_BUTTON )
        QP.AddToLayout( vbox, default_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._specific_options_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._is_default.clicked.connect( self._UpdateIsDefault )
        
        self._UpdateIsDefault()
        
    
    def _InitialiseServices( self, tag_import_options ):
        
        services = HG.client_controller.services_manager.GetServices( HC.TAG_SERVICES, randomised = False )
        
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
            
            url_class_keys_to_url_classes = { url_class.GetMatchKey() : url_class for url_class in url_classes }
            
            url_class_names_and_default_tag_import_options = [ ( url_class_keys_to_url_classes[ url_class_key ].GetName(), url_class_keys_to_default_tag_import_options[ url_class_key ] ) for url_class_key in list( url_class_keys_to_default_tag_import_options.keys() ) if url_class_key in url_class_keys_to_url_classes ]
            
            url_class_names_and_default_tag_import_options.sort()
            
            choice_tuples.extend( url_class_names_and_default_tag_import_options )
            
        
        try:
            
            default_tag_import_options = ClientGUIDialogsQuick.SelectFromList( self, 'Select which default', choice_tuples, sort_tuples = False )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if default_tag_import_options is None:
            
            return
            
        
        self._SetValue( default_tag_import_options )
        
    
    def _SetValue( self, tag_import_options ):
        
        self._is_default.setChecked( tag_import_options.IsDefault() )
        
        self._tag_filter_button.SetValue( tag_import_options.GetTagBlacklist() )
        
        self._fetch_tags_even_if_url_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB() )
        self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.setChecked( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB() )
        
        for ( service_key, panel ) in list(self._service_keys_to_service_tag_import_options_panels.items()):
            
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
        
        self._specific_options_panel.setEnabled( show_specific_options )
        
    
    def GetValue( self ):
        
        is_default = self._is_default.isChecked()
        
        if is_default:
            
            tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
            
        else:
            
            fetch_tags_even_if_url_recognised_and_file_already_in_db = self._fetch_tags_even_if_url_recognised_and_file_already_in_db.isChecked()
            fetch_tags_even_if_hash_recognised_and_file_already_in_db = self._fetch_tags_even_if_hash_recognised_and_file_already_in_db.isChecked()
            
            service_keys_to_service_tag_import_options = {service_key : panel.GetValue() for (service_key, panel) in list( self._service_keys_to_service_tag_import_options_panels.items() )}
            
            tag_blacklist = self._tag_filter_button.GetValue()
            
            tag_import_options = ClientImportOptions.TagImportOptions( fetch_tags_even_if_url_recognised_and_file_already_in_db = fetch_tags_even_if_url_recognised_and_file_already_in_db, fetch_tags_even_if_hash_recognised_and_file_already_in_db = fetch_tags_even_if_hash_recognised_and_file_already_in_db, tag_blacklist = tag_blacklist, service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
            
        
        return tag_import_options
        
    
class EditSelectFromListPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, choice_tuples, value_to_select = None, sort_tuples = True ):
        
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
    
    def __init__( self, parent, choices ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._data = None
        
        vbox = QP.VBoxLayout()
        
        first_focused = False
        
        for ( text, data, tooltip ) in choices:
            
            button = ClientGUICommon.BetterButton( self, text, self._ButtonChoice, data )
            
            button.setToolTip( tooltip )
            
            QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            if not first_focused:
                
                QP.CallAfter( button.setFocus, QC.Qt.OtherFocusReason)
                
                first_focused = True
                
            
        
        self.widget().setLayout( vbox )
        
    
    def _ButtonChoice( self, data ):
        
        self._data = data
        
        self.parentWidget().DoOK()
        
    
    def GetValue( self ):
        
        return self._data
        
    
class EditServiceTagImportOptionsPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, service_key, service_tag_import_options, show_downloader_options = True ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._service_key = service_key
        
        name = HG.client_controller.services_manager.GetName( self._service_key )
        
        main_box = ClientGUICommon.StaticBox( self, name )
        
        #
        
        ( get_tags, get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, self._only_add_existing_tags_filter ) = service_tag_import_options.ToTuple()
        
        #
        
        menu_items = self._GetCogIconMenuItems()
        
        cog_button = ClientGUICommon.MenuBitmapButton( main_box, CC.GlobalPixmaps.cog, menu_items )
        
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
        
        QP.AddToLayout( hbox, self._get_tags_checkbox, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._get_tags_filter_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        downloader_options_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._additional_button = ClientGUICommon.BetterButton( main_box, 'additional tags', self._DoAdditionalTags )
        
        #
        
        self._get_tags_checkbox.setChecked( get_tags )
        
        #
        
        if not show_downloader_options:
            
            downloader_options_panel.hide()
            
        
        main_box.Add( cog_button, CC.FLAGS_LONE_BUTTON )
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
        
        with ClientGUIDialogs.DialogInputTags( self, self._service_key, list( self._additional_tags ), message = message ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._additional_tags = dlg.GetTags()
                
            
        
        self._UpdateAdditionalTagsButtonLabel()
        
    
    def _EditOnlyAddExistingTagsFilter( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit already-exist filter' ) as dlg:
            
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
        
    
    def GetValue( self ):
        
        get_tags = self._get_tags_checkbox.isChecked()
        
        get_tags_filter = self._get_tags_filter_button.GetValue()
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = get_tags, get_tags_filter = get_tags_filter, additional_tags = self._additional_tags, to_new_files = self._to_new_files, to_already_in_inbox = self._to_already_in_inbox, to_already_in_archive = self._to_already_in_archive, only_add_existing_tags = self._only_add_existing_tags, only_add_existing_tags_filter = self._only_add_existing_tags_filter )
        
        return service_tag_import_options
        
    
    def SetValue( self, service_tag_import_options ):
        
        ( get_tags, get_tags_filter, self._additional_tags, self._to_new_files, self._to_already_in_inbox, self._to_already_in_archive, self._only_add_existing_tags, self._only_add_existing_tags_filter ) = service_tag_import_options.ToTuple()
        
        self._get_tags_checkbox.setChecked( get_tags )
        
        self._get_tags_filter_button.SetValue( get_tags_filter )
        
        self._UpdateGetTags()
        
        self._UpdateAdditionalTagsButtonLabel()
        
    
class EditTagSummaryGeneratorPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, tag_summary_generator ):
        
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
        
    
    def GetValue( self ):
        
        show = self._show.isChecked()
        
        background_colour = self._background_colour.GetValue()
        text_colour = self._text_colour.GetValue()
        namespace_info = self._namespaces_listbox.GetData()
        separator = self._separator.text()
        example_tags = HydrusTags.CleanTags( HydrusText.DeserialiseNewlinedTexts( self._example_tags.toPlainText() ) )
        
        return ClientGUITags.TagSummaryGenerator( background_colour, text_colour, namespace_info, separator, example_tags, show )
        
    
class TagSummaryGeneratorButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, tag_summary_generator ):
        
        label = tag_summary_generator.GenerateExampleSummary()
        
        ClientGUICommon.BetterButton.__init__( self, parent, label, self._Edit )
        
        self._tag_summary_generator = tag_summary_generator
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit tag summary' ) as dlg:
            
            panel = EditTagSummaryGeneratorPanel( dlg, self._tag_summary_generator )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                self._tag_summary_generator = panel.GetValue()
                
                self.setText( self._tag_summary_generator.GenerateExampleSummary() )
                
            
        
    
    def GetValue( self ):
        
        return self._tag_summary_generator
        
    
class EditURLClassPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, url_class: ClientNetworkingDomain.URLClass ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )

        self._update_already_in_progress = False # Used to avoid infinite recursion on control updates.
        
        self._original_url_class = url_class
        
        self._name = QW.QLineEdit( self )
        
        self._url_type = ClientGUICommon.BetterChoice( self )
        
        for url_type in ( HC.URL_TYPE_POST, HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE, HC.URL_TYPE_FILE ):
            
            self._url_type.addItem( HC.url_type_string_lookup[ url_type ], url_type )
            
        
        self._preferred_scheme = ClientGUICommon.BetterChoice( self )
        
        self._preferred_scheme.addItem( 'http', 'http' )
        self._preferred_scheme.addItem( 'https', 'https' )
        
        self._netloc = QW.QLineEdit( self )
        
        self._alphabetise_get_parameters = QW.QCheckBox( self )
        
        tt = 'Normally, to ensure the same URLs are merged, hydrus will alphabetise GET parameters as part of the normalisation process.'
        tt += os.linesep * 2
        tt += 'Almost all servers support GET params in any order. One or two do not. Uncheck this if you know there is a problem.'
        
        self._alphabetise_get_parameters.setToolTip( tt )
        
        self._match_subdomains = QW.QCheckBox( self )
        
        tt = 'Should this class apply to subdomains as well?'
        tt += os.linesep * 2
        tt += 'For instance, if this url class has domain \'example.com\', should it match a url with \'boards.example.com\' or \'artistname.example.com\'?'
        tt += os.linesep * 2
        tt += 'Any subdomain starting with \'www\' is automatically matched, so do not worry about having to account for that.'
        
        self._match_subdomains.setToolTip( tt )
        
        self._keep_matched_subdomains = QW.QCheckBox( self )
        
        tt = 'Should this url keep its matched subdomains when it is normalised?'
        tt += os.linesep * 2
        tt += 'This is typically useful for direct file links that are often served on a numbered CDN subdomain like \'img3.example.com\' but are also valid on the neater main domain.'
        
        self._keep_matched_subdomains.setToolTip( tt )
        
        self._can_produce_multiple_files = QW.QCheckBox( self )
        
        tt = 'If checked, the client will not rely on instances of this URL class to predetermine \'already in db\' or \'previously deleted\' outcomes. This is important for post types like pixiv pages (which can ultimately be manga, and represent many pages) and tweets (which can have multiple images).'
        tt += os.linesep * 2
        tt += 'Most booru-type Post URLs only produce one file per URL and should not have this checked. Checking this avoids some bad logic where the client would falsely think it if it had seen one file at the URL, it had seen them all, but it then means the client has to download those pages\' content again whenever it sees them (so it can check against the direct File URLs, which are always considered one-file each).'
        
        self._can_produce_multiple_files.setToolTip( tt )
        
        self._should_be_associated_with_files = QW.QCheckBox( self )
        
        tt = 'If checked, the client will try to remember this url with any files it ends up importing. It will present this url in \'known urls\' ui across the program.'
        tt += os.linesep * 2
        tt += 'If this URL is a File or Post URL and the client comes across it after having already downloaded it once, it can skip the redundant download since it knows it already has (or has already deleted) the file once before.'
        tt += os.linesep * 2
        tt += 'Turning this on is only useful if the URL is non-ephemeral (i.e. the URL will produce the exact same file(s) in six months\' time). It is usually not appropriate for booru gallery or thread urls, which alter regularly, but is for static Post URLs or some fixed doujin galleries.'
        
        self._should_be_associated_with_files.setToolTip( tt )
        
        #
        
        path_components_panel = ClientGUICommon.StaticBox( self, 'path components' )
        
        self._path_components = ClientGUIListBoxes.QueueListBox( path_components_panel, 6, self._ConvertPathComponentRowToString, self._AddPathComponent, self._EditPathComponent )
        
        #
        
        parameters_panel = ClientGUICommon.StaticBox( self, 'parameters' )
        
        parameters_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( parameters_panel )
        
        columns = [ ( 'key', 14 ), ( 'value', -1 ) ]
        
        self._parameters = ClientGUIListCtrl.BetterListCtrl( parameters_listctrl_panel, 'url_class_path_components', 5, 45, columns, self._ConvertParameterToListCtrlTuples, delete_key_callback = self._DeleteParameters, activation_callback = self._EditParameters )
        
        parameters_listctrl_panel.SetListCtrl( self._parameters )
        
        parameters_listctrl_panel.AddButton( 'add', self._AddParameters )
        parameters_listctrl_panel.AddButton( 'edit', self._EditParameters, enabled_only_on_selection = True )
        parameters_listctrl_panel.AddDeleteButton()
        
        #
        
        self._next_gallery_page_panel = ClientGUICommon.StaticBox( self, 'next gallery page' )
        
        self._next_gallery_page_choice = ClientGUICommon.BetterChoice( self._next_gallery_page_panel )
        
        self._next_gallery_page_delta = QP.MakeQSpinBox( self._next_gallery_page_panel, min=1, max=65536 )
        
        #
        
        self._example_url = QW.QLineEdit( self )
        
        self._example_url_classes = ClientGUICommon.BetterStaticText( self )
        
        self._normalised_url = QW.QLineEdit( self )
        self._normalised_url.setReadOnly( True )
        
        tt = 'The same url can be expressed in different ways. The parameters can be reordered, and descriptive \'sugar\' like "/123456/bodysuit-samus_aran" can be altered at a later date, say to "/123456/bodysuit-green_eyes-samus_aran". In order to collapse all the different expressions of a url down to a single comparable form, the client will \'normalise\' them based on the essential definitions in their url class. Parameters will be alphebatised and non-defined elements will be removed.'
        tt += os.linesep * 2
        tt += 'All normalisation will switch to the preferred scheme (http/https). The alphabetisation of parameters and stripping out of non-defined elements will occur for all URLs except Gallery URLs or Watchable URLs that do not use an API Lookup. (In general, you can define gallery and watchable urls a little more loosely since they generally do not need to be compared, but if you will be saving it with a file or need to perform some regex transformation into an API URL, you\'ll want a rigorously defined url class that will normalise to something reliable and pretty.)'
        
        self._normalised_url.setToolTip( tt )
        
        ( url_type, preferred_scheme, netloc, path_components, parameters, api_lookup_converter, send_referral_url, referral_url_converter, example_url ) = url_class.ToTuple()
        
        self._send_referral_url = ClientGUICommon.BetterChoice( self )
        
        for send_referral_url_type in ClientNetworkingDomain.SEND_REFERRAL_URL_TYPES:
            
            self._send_referral_url.addItem( ClientNetworkingDomain.send_referral_url_string_lookup[ send_referral_url_type ], send_referral_url_type )
            
        
        tt = 'Do not change this unless you know you need to. It fixes complicated problems.'
        
        self._send_referral_url.setToolTip( tt )
        
        self._referral_url_converter = ClientGUIControls.StringConverterButton( self, referral_url_converter )
        
        tt = 'This will generate a referral URL from the original URL. If the URL needs a referral URL, and you can infer what that would be from just this URL, this will let hydrus download this URL without having to previously visit the referral URL (e.g. letting the user drag-and-drop import). It also lets you set up alternate referral URLs for perculiar situations.'
        
        self._referral_url_converter.setToolTip( tt )
        
        self._referral_url = QW.QLineEdit()
        self._referral_url.setReadOnly( True )
        
        self._api_lookup_converter = ClientGUIControls.StringConverterButton( self, api_lookup_converter )
        
        tt = 'This will let you generate an alternate URL for the client to use for the actual download whenever it encounters a URL in this class. You must have a separate URL class to match the API type (which will link to parsers).'
        
        self._api_lookup_converter.setToolTip( tt )
        
        self._api_url = QW.QLineEdit( self )
        self._api_url.setReadOnly( True )
        
        self._next_gallery_page_url = QW.QLineEdit( self )
        self._next_gallery_page_url.setReadOnly( True )
        
        #
        
        name = url_class.GetName()
        
        self._name.setText( name )
        
        self._url_type.SetValue( url_type )
        
        self._preferred_scheme.SetValue( preferred_scheme )
        
        self._netloc.setText( netloc )
        
        ( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, can_produce_multiple_files, should_be_associated_with_files ) = url_class.GetURLBooleans()
        
        self._alphabetise_get_parameters.setChecked( alphabetise_get_parameters )
        self._match_subdomains.setChecked( match_subdomains )
        self._keep_matched_subdomains.setChecked( keep_matched_subdomains )
        self._can_produce_multiple_files.setChecked( can_produce_multiple_files )
        self._should_be_associated_with_files.setChecked( should_be_associated_with_files )
        
        self._path_components.AddDatas( path_components )
        
        self._parameters.AddDatas( list(parameters.items()) )
        
        self._parameters.Sort()
        
        self._example_url.setText( example_url )
        
        example_url_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._example_url, 75 )
        
        self._example_url.setMinimumWidth( example_url_width )
        
        self._send_referral_url.SetValue( send_referral_url )
        
        ( gallery_index_type, gallery_index_identifier, gallery_index_delta ) = url_class.GetGalleryIndexValues()
        
        # this preps it for the upcoming update
        self._next_gallery_page_choice.addItem( 'initialisation', ( gallery_index_type, gallery_index_identifier ) )
        self._next_gallery_page_choice.setCurrentIndex( 0 )
        
        self._next_gallery_page_delta.setValue( gallery_index_delta )
        
        self._UpdateControls()
        
        #
        
        path_components_panel.Add( self._path_components, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        parameters_panel.Add( parameters_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._next_gallery_page_choice, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._next_gallery_page_delta, CC.FLAGS_VCENTER )
        
        self._next_gallery_page_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'name: ', self._name ) )
        rows.append( ( 'url type: ', self._url_type ) )
        rows.append( ( 'preferred scheme: ', self._preferred_scheme ) )
        rows.append( ( 'network location: ', self._netloc ) )
        rows.append( ( 'alphabetise GET parameters?: ', self._alphabetise_get_parameters ) )
        rows.append( ( 'match subdomains?: ', self._match_subdomains ) )
        rows.append( ( 'keep matched subdomains?: ', self._keep_matched_subdomains ) )
        rows.append( ( 'can produce multiple files: ', self._can_produce_multiple_files ) )
        rows.append( ( 'should associate a \'known url\' with resulting files: ', self._should_be_associated_with_files ) )
        
        gridbox_1 = ClientGUICommon.WrapInGrid( self, rows )
        
        rows = []
        
        rows.append( ( 'example url: ', self._example_url ) )
        rows.append( ( 'normalised url: ', self._normalised_url ) )
        rows.append( ( 'send referral url?: ', self._send_referral_url ) )
        rows.append( ( 'optional referral url converter: ', self._referral_url_converter ) )
        rows.append( ( 'referral url: ', self._referral_url ) )
        rows.append( ( 'optional api url converter: ', self._api_lookup_converter ) )
        rows.append( ( 'api url: ', self._api_url ) )
        rows.append( ( 'next gallery page url: ', self._next_gallery_page_url ) )
        
        gridbox_2 = ClientGUICommon.WrapInGrid( self, rows )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, gridbox_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, path_components_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, parameters_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._next_gallery_page_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._example_url_classes, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, gridbox_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._preferred_scheme.currentIndexChanged.connect( self._UpdateControls )
        self._netloc.textChanged.connect( self._UpdateControls )
        self._alphabetise_get_parameters.clicked.connect( self._UpdateControls )
        self._match_subdomains.clicked.connect( self._UpdateControls )
        self._keep_matched_subdomains.clicked.connect( self._UpdateControls )
        self._can_produce_multiple_files.clicked.connect( self._UpdateControls )
        self._next_gallery_page_choice.currentIndexChanged.connect( self._UpdateControls )
        self._next_gallery_page_delta.valueChanged.connect( self._UpdateControls )
        self._example_url.textChanged.connect( self._UpdateControls )
        self._path_components.listBoxChanged.connect( self._UpdateControls )
        self._url_type.currentIndexChanged.connect( self.EventURLTypeUpdate )
        self._send_referral_url.currentIndexChanged.connect( self._UpdateControls )
        self._referral_url_converter.stringConverterUpdate.connect( self._UpdateControls )
        self._api_lookup_converter.stringConverterUpdate.connect( self._UpdateControls )
        
        self._should_be_associated_with_files.clicked.connect( self.EventAssociationUpdate )
        
    
    def _AddParameters( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'edit the key', placeholder = 'key', allow_blank = False ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                key = dlg.GetValue()
                
            else:
                
                return
                
            
        
        existing_keys = self._GetExistingKeys()
        
        if key in existing_keys:
            
            QW.QMessageBox.critical( self, 'Error', 'That key already exists!' )
            
            return
            
        
        string_match = ClientParsing.StringMatch()
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit value' ) as dlg:
            
            panel = ClientGUIControls.EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                string_match = panel.GetValue()
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter optional \'default\' value for this parameter, which will be filled in if missing. Leave blank for none (recommended).', allow_blank = True ) as dlg_default:
                    
                    if dlg_default.exec() == QW.QDialog.Accepted:
                        
                        default = dlg_default.GetValue()
                        
                        if default == '':
                            
                            default = None
                            
                        elif not string_match.Matches( default ):
                            
                            QW.QMessageBox.warning( self, 'Warning', 'That default does not match the given rule! Clearing it to none!' )
                            
                            default = None
                            
                        
                    else:
                        
                        return
                        
                    
                
            else:
                
                return
                
            
        
        data = ( key, ( string_match, default ) )
        
        self._parameters.AddDatas( ( data, ) )
        
        self._parameters.Sort()
        
        self._UpdateControls()
        
    
    def _AddPathComponent( self ):
        
        string_match = ClientParsing.StringMatch()
        default = None
        
        return self._EditPathComponent( ( string_match, default ) )
        
    
    def _ConvertParameterToListCtrlTuples( self, data ):
        
        ( key, ( string_match, default ) ) = data
        
        pretty_key = key
        pretty_string_match = string_match.ToString()
        
        if default is not None:
            
            pretty_string_match += ' (default "' + default + '")'
            
        
        sort_key = pretty_key
        sort_string_match = pretty_string_match
        
        display_tuple = ( pretty_key, pretty_string_match )
        sort_tuple = ( sort_key, sort_string_match )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertPathComponentRowToString( self, row ):
        
        ( string_match, default ) = row
        
        s = string_match.ToString()
        
        if default is not None:
            
            s += ' (default "' + default + '")'
            
        
        return s
        
    
    def _DeleteParameters( self ):
        
        self._parameters.ShowDeleteSelectedDialog()
        
        self._UpdateControls()
        
    
    def _EditParameters( self ):
        
        selected_params = self._parameters.GetData( only_selected = True )
        
        for parameter in selected_params:
            
            ( original_key, ( original_string_match, original_default ) ) = parameter
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the key', default = original_key, allow_blank = False ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    key = dlg.GetValue()
                    
                else:
                    
                    return
                    
                
            
            if key != original_key:
                
                existing_keys = self._GetExistingKeys()
                
                if key in existing_keys:
                    
                    QW.QMessageBox.critical( self, 'Error', 'That key already exists!' )
                    
                    return
                    
                
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit value' ) as dlg:
                
                panel = ClientGUIControls.EditStringMatchPanel( dlg, original_string_match )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    string_match = panel.GetValue()
                    
                    if original_default is None:
                        
                        original_default = ''
                        
                    
                    with ClientGUIDialogs.DialogTextEntry( self, 'Enter optional \'default\' value for this parameter, which will be filled in if missing. Leave blank for none (recommended).', default = original_default, allow_blank = True ) as dlg_default:
                        
                        if dlg_default.exec() == QW.QDialog.Accepted:
                            
                            default = dlg_default.GetValue()
                            
                            if default == '':
                                
                                default = None
                                
                            elif not string_match.Matches( default ):
                                
                                QW.QMessageBox.warning( self, 'Warning', 'That default does not match the given rule! Clearing it to none!' )
                                
                                default = None
                                
                            
                        else:
                            
                            return
                            
                        
                    
                else:
                    
                    return
                    
                
            
            self._parameters.DeleteDatas( ( parameter, ) )
            
            new_parameter = ( key, ( string_match, default ) )
            
            self._parameters.AddDatas( ( new_parameter, ) )
            
        
        self._parameters.Sort()
        
        self._UpdateControls()
        
    
    def _EditPathComponent( self, row ):
        
        ( string_match, default ) = row
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit path component' ) as dlg:
            
            panel = ClientGUIControls.EditStringMatchPanel( dlg, string_match )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_string_match = panel.GetValue()
                
                if default is None:
                    
                    default = ''
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter optional \'default\' value for this path component, which will be filled in if missing. Leave blank for none (recommended).', default = default, allow_blank = True ) as dlg_default:
                    
                    if dlg_default.exec() == QW.QDialog.Accepted:
                        
                        new_default = dlg_default.GetValue()
                        
                        if new_default == '':
                            
                            new_default = None
                            
                        elif not string_match.Matches( new_default ):
                            
                            QW.QMessageBox.warning( self, 'Warning', 'That default does not match the given rule! Clearing it to none!' )
                            
                            new_default = None
                            
                        
                        new_row = ( new_string_match, new_default )
                        
                        QP.CallAfter( self._UpdateControls ) # seems sometimes this doesn't kick in naturally
                        
                        return new_row
                        
                    
                
            
            raise HydrusExceptions.VetoException()
            
        
    
    def _GetExistingKeys( self ):
        
        params = self._parameters.GetData()
        
        keys = { key for ( key, string_match ) in params }
        
        return keys
        
    
    def _GetValue( self ):
        
        url_class_key = self._original_url_class.GetMatchKey()
        name = self._name.text()
        url_type = self._url_type.GetValue()
        preferred_scheme = self._preferred_scheme.GetValue()
        netloc = self._netloc.text()
        path_components = self._path_components.GetData()
        parameters = dict( self._parameters.GetData() )
        api_lookup_converter = self._api_lookup_converter.GetValue()
        send_referral_url = self._send_referral_url.GetValue()
        referral_url_converter = self._referral_url_converter.GetValue()
        
        ( gallery_index_type, gallery_index_identifier ) = self._next_gallery_page_choice.GetValue()
        gallery_index_delta = self._next_gallery_page_delta.value()
        
        example_url = self._example_url.text()
        
        url_class = ClientNetworkingDomain.URLClass( name, url_class_key = url_class_key, url_type = url_type, preferred_scheme = preferred_scheme, netloc = netloc, path_components = path_components, parameters = parameters, api_lookup_converter = api_lookup_converter, send_referral_url = send_referral_url, referral_url_converter = referral_url_converter, gallery_index_type = gallery_index_type, gallery_index_identifier = gallery_index_identifier, gallery_index_delta = gallery_index_delta, example_url = example_url )
        
        match_subdomains = self._match_subdomains.isChecked()
        keep_matched_subdomains = self._keep_matched_subdomains.isChecked()
        alphabetise_get_parameters = self._alphabetise_get_parameters.isChecked()
        can_produce_multiple_files = self._can_produce_multiple_files.isChecked()
        should_be_associated_with_files = self._should_be_associated_with_files.isChecked()
        
        url_class.SetURLBooleans( match_subdomains, keep_matched_subdomains, alphabetise_get_parameters, can_produce_multiple_files, should_be_associated_with_files )
        
        return url_class
        
    
    def _UpdateControls( self ):
        
        # we need to regen possible next gallery page choices before we fetch current value and update everything else
        
        if self._update_already_in_progress: return # Could use blockSignals but this way I don't have to block signals on individual controls

        self._update_already_in_progress = True
        
        if self._url_type.GetValue() == HC.URL_TYPE_GALLERY:
            
            self._next_gallery_page_panel.setEnabled( True )
            
            choices = [ ( 'no next gallery page info set', ( None, None ) ) ]
            
            for ( index, ( string_match, default ) ) in enumerate( self._path_components.GetData() ):
                
                if True in ( string_match.Matches( n ) for n in ( '0', '1', '10', '100', '42' ) ):
                    
                    choices.append( ( HydrusData.ConvertIntToPrettyOrdinalString( index + 1 ) + ' path component', ( ClientNetworkingDomain.GALLERY_INDEX_TYPE_PATH_COMPONENT, index ) ) )
                    
                
            
            for ( index, ( key, ( string_match, default ) ) ) in enumerate( self._parameters.GetData() ):
                
                if True in ( string_match.Matches( n ) for n in ( '0', '1', '10', '100', '42' ) ):
                    
                    choices.append( ( key + ' parameter', ( ClientNetworkingDomain.GALLERY_INDEX_TYPE_PARAMETER, key ) ) )
                    
                
            
            existing_choice = self._next_gallery_page_choice.GetValue()
            
            self._next_gallery_page_choice.clear()
            
            for ( name, data ) in choices:
                
                self._next_gallery_page_choice.addItem( name, data )
                
            
            self._next_gallery_page_choice.SetValue( existing_choice ) # this should fail to ( None, None )
            
            ( gallery_index_type, gallery_index_identifier ) = self._next_gallery_page_choice.GetValue() # what was actually set?
            
            if gallery_index_type is None:
                
                self._next_gallery_page_delta.setEnabled( False )
                
            else:
                
                self._next_gallery_page_delta.setEnabled( True )
                
            
        else:
            
            self._next_gallery_page_panel.setEnabled( False )
            
        
        #
        
        url_class = self._GetValue()
        
        url_type = url_class.GetURLType()
        
        if url_type == HC.URL_TYPE_POST:
            
            self._can_produce_multiple_files.setEnabled( True )
            
        else:
            
            self._can_produce_multiple_files.setEnabled( False )
            
        
        if url_class.ClippingIsAppropriate():
            
            if self._match_subdomains.isChecked():
                
                self._keep_matched_subdomains.setEnabled( True )
                
            else:
                
                self._keep_matched_subdomains.setChecked( False )
                self._keep_matched_subdomains.setEnabled( False )
                
            
        else:
            
            self._keep_matched_subdomains.setEnabled( False )
            
        
        try:
            
            example_url = self._example_url.text()
            
            self._referral_url_converter.SetExampleString( example_url )
            self._api_lookup_converter.SetExampleString( example_url )
            
            url_class.Test( example_url )
            
            self._example_url_classes.setText( 'Example matches ok!' )
            QP.SetForegroundColour( self._example_url_classes, (0,128,0) )
            
            normalised = url_class.Normalise( example_url )
            
            self._normalised_url.setText( normalised )
            
            if url_class.UsesAPIURL():
                
                self._send_referral_url.setEnabled( False )
                self._referral_url_converter.setEnabled( False )
                
                self._referral_url.setText( 'Not used, as API converter will redirect.' )
                
            else:
                
                self._send_referral_url.setEnabled( True )
                self._referral_url_converter.setEnabled( True )
                
                send_referral_url = self._send_referral_url.GetValue()
                
                if send_referral_url in ( ClientNetworkingDomain.SEND_REFERRAL_URL_ONLY_IF_PROVIDED, ClientNetworkingDomain.SEND_REFERRAL_URL_NEVER ):
                    
                    self._referral_url_converter.setEnabled( False )
                    
                else:
                    
                    self._referral_url_converter.setEnabled( True )
                    
                
                if send_referral_url == ClientNetworkingDomain.SEND_REFERRAL_URL_CONVERTER_IF_NONE_PROVIDED:
                    
                    referral_url = url_class.GetReferralURL( normalised, None )
                    
                    referral_url = 'normal referral url -or- {}'.format( referral_url )
                    
                else:
                    
                    referral_url = url_class.GetReferralURL( normalised, 'normal referral url' )
                    
                
                if referral_url is None:
                    
                    self._referral_url.setText( 'None' )
                    
                else:
                    
                    self._referral_url.setText( referral_url )
                    
                
            
            try:
                
                if url_class.UsesAPIURL():
                    
                    api_lookup_url = url_class.GetAPIURL( normalised )
                    
                else:
                    
                    api_lookup_url = 'none set'
                    
                
                self._api_url.setText( api_lookup_url )
                
            except HydrusExceptions.StringConvertException as e:
                
                reason = str( e )
                
                self._api_url.setText( 'Could not convert - ' + reason )
                
            
            try:
                
                if url_class.CanGenerateNextGalleryPage():
                    
                    next_gallery_page_url = url_class.GetNextGalleryPage( normalised )
                    
                else:
                    
                    next_gallery_page_url = 'none set'
                    
                
                self._next_gallery_page_url.setText( next_gallery_page_url )
                
            except Exception as e:
                
                reason = str( e )
                
                self._next_gallery_page_url.setText( 'Could not convert - ' + reason )
                
            
        except HydrusExceptions.URLClassException as e:
            
            reason = str( e )
            
            self._example_url_classes.setText( 'Example does not match - '+reason )
            QP.SetForegroundColour( self._example_url_classes, (128,0,0) )
            
            self._normalised_url.setText( '' )
            self._api_url.setText( '' )

        self._update_already_in_progress = False
        
    
    def EventAssociationUpdate( self ):
        
        if self._should_be_associated_with_files.isChecked():
            
            if self._url_type.GetValue() in ( HC.URL_TYPE_GALLERY, HC.URL_TYPE_WATCHABLE ):
                
                message = 'Please note that it is only appropriate to associate a Gallery or Watchable URL with a file if that URL is non-ephemeral. It is only appropriate if the exact same URL will definitely give the same files in six months\' time (like a fixed doujin chapter gallery).'
                message += os.linesep * 2
                message += 'If you are not sure what this means, turn this back off.'
                
                QW.QMessageBox.information( self, 'Information', message )
                
            
        else:
            
            if self._url_type.GetValue() in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
                
                message = 'Hydrus uses these file associations to make sure not to re-download the same file when it comes across the same URL in future. It is only appropriate to not associate a file or post url with a file if that url is particularly ephemeral, such as if the URL includes a non-removable random key that becomes invalid after a few minutes.'
                message += os.linesep * 2
                message += 'If you are not sure what this means, turn this back on.'
                
                QW.QMessageBox.information( self, 'Information', message )
            
        
    def EventURLTypeUpdate( self, event ):
        
        url_type = self._url_type.GetValue()
        
        if url_type in ( HC.URL_TYPE_FILE, HC.URL_TYPE_POST ):
            
            self._should_be_associated_with_files.setChecked( True )
            
        else:
            
            self._should_be_associated_with_files.setChecked( False )
            
        
        self._UpdateControls()
        
    
    def GetValue( self ):
        
        url_class = self._GetValue()
        
        try:
            
            url_class.Test( self._example_url.text() )
            
        except HydrusExceptions.URLClassException:
            
            raise HydrusExceptions.VetoException( 'Please enter an example url that matches the given rules!' )
            
        
        return url_class
        
    
class EditURLClassesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, url_classes ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientPaths.LaunchPathInWebBrowser, os.path.join( HC.HELP_DIR, 'downloader_url_classes.html' ) )
        
        menu_items.append( ( 'normal', 'open the url classes help', 'Open the help page for url classes in your web browser.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalPixmaps.help, menu_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this panel -->', QG.QColor( 0, 0, 255 ) )
        
        self._url_class_checker = QW.QLineEdit( self )
        self._url_class_checker.textChanged.connect( self.EventURLClassCheckerText )
        
        self._url_class_checker_st = ClientGUICommon.BetterStaticText( self )
        
        self._list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'name', 36 ), ( 'type', 20 ), ( 'example (normalised) url', -1 ) ]
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._list_ctrl_panel, 'url_classes', 15, 40, columns, self._ConvertDataToListCtrlTuples, use_simple_delete = True, activation_callback = self._Edit )
        
        self._list_ctrl_panel.SetListCtrl( self._list_ctrl )
        
        self._list_ctrl_panel.AddButton( 'add', self._Add )
        self._list_ctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        self._list_ctrl_panel.AddDeleteButton()
        self._list_ctrl_panel.AddSeparator()
        self._list_ctrl_panel.AddImportExportButtons( ( ClientNetworkingDomain.URLClass, ), self._AddURLClass )
        self._list_ctrl_panel.AddSeparator()
        self._list_ctrl_panel.AddDefaultsButton( ClientDefaults.GetDefaultURLClasses, self._AddURLClass )
        
        #
        
        self._list_ctrl.AddDatas( url_classes )
        
        self._list_ctrl.Sort( 0 )
        
        #
        
        url_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( url_hbox, self._url_class_checker, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( url_hbox, self._url_class_checker_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, help_hbox, CC.FLAGS_BUTTON_SIZER )
        QP.AddToLayout( vbox, url_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._list_ctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._UpdateURLClassCheckerText()
        
    
    def _Add( self ):
        
        url_class = ClientNetworkingDomain.URLClass( 'new url class' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit url class' ) as dlg:
            
            panel = EditURLClassPanel( dlg, url_class )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                url_class = panel.GetValue()
                
                self._AddURLClass( url_class )
                
                self._list_ctrl.Sort()
                
            
        
    
    def _AddURLClass( self, url_class ):
        
        HydrusSerialisable.SetNonDupeName( url_class, self._GetExistingNames() )
        
        url_class.RegenerateMatchKey()
        
        self._list_ctrl.AddDatas( ( url_class, ) )
        
    
    def _ConvertDataToListCtrlTuples( self, url_class ):
        
        name = url_class.GetName()
        url_type = url_class.GetURLType()
        example_url = url_class.Normalise( url_class.GetExampleURL() )
        
        pretty_name = name
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        pretty_example_url = example_url
        
        display_tuple = ( pretty_name, pretty_url_type, pretty_example_url )
        sort_tuple = ( name, url_type, example_url )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Edit( self ):
        
        for url_class in self._list_ctrl.GetData( only_selected = True ):
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit url class' ) as dlg:
                
                panel = EditURLClassPanel( dlg, url_class )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    self._list_ctrl.DeleteDatas( ( url_class, ) )
                    
                    url_class = panel.GetValue()
                    
                    HydrusSerialisable.SetNonDupeName( url_class, self._GetExistingNames() )
                    
                    self._list_ctrl.AddDatas( ( url_class, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._list_ctrl.Sort()
        
    
    def _GetExistingNames( self ):
        
        url_classes = self._list_ctrl.GetData()
        
        names = { url_class.GetName() for url_class in url_classes }
        
        return names
        
    
    def _UpdateURLClassCheckerText( self ):
        
        url = self._url_class_checker.text()
        
        if url == '':
            
            text = '<-- Enter a URL here to see which url class it currently matches!'
            
        else:
            
            url_classes = self.GetValue()
            
            domain_manager = ClientNetworkingDomain.NetworkDomainManager()
            
            domain_manager.Initialise()
            
            domain_manager.SetURLClasses( url_classes )
            
            try:
                
                url_class = domain_manager.GetURLClass( url )
                
                if url_class is None:
                    
                    text = 'No match!'
                    
                else:
                    
                    text = 'Matches "' + url_class.GetName() + '"'
                    
                
            except HydrusExceptions.URLClassException as e:
                
                text = str( e )
                
            
        
        self._url_class_checker_st.setText( text )
        
    
    def EventURLClassCheckerText( self, text ):
        
        self._UpdateURLClassCheckerText()
        
    
    def GetValue( self ):
        
        url_classes = self._list_ctrl.GetData()
        
        return url_classes
        
    
class EditURLClassLinksPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, network_engine, url_classes, parsers, url_class_keys_to_parser_keys ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._url_classes = url_classes
        self._url_class_keys_to_url_classes = { url_class.GetMatchKey() : url_class for url_class in self._url_classes }
        
        self._parsers = parsers
        self._parser_keys_to_parsers = { parser.GetParserKey() : parser for parser in self._parsers }
        
        self._network_engine = network_engine
        
        #
        
        self._notebook = QW.QTabWidget( self )
        
        #
        
        columns = [ ( 'url class', -1 ), ( 'api url class', 36 ) ]
        
        self._api_pairs_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._notebook, 'url_class_api_pairs', 10, 36, columns, self._ConvertAPIPairDataToListCtrlTuples )
        
        #
        
        self._parser_list_ctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._notebook )
        
        columns = [ ( 'url class', -1 ), ( 'url type', 20 ), ( 'parser', 36 ) ]
        
        self._parser_list_ctrl = ClientGUIListCtrl.BetterListCtrl( self._parser_list_ctrl_panel, 'url_class_keys_to_parser_keys', 24, 36, columns, self._ConvertParserDataToListCtrlTuples, activation_callback = self._EditParser )
        
        self._parser_list_ctrl_panel.SetListCtrl( self._parser_list_ctrl )
        
        self._parser_list_ctrl_panel.AddButton( 'edit', self._EditParser, enabled_only_on_selection = True )
        self._parser_list_ctrl_panel.AddButton( 'clear', self._ClearParser, enabled_check_func = self._LinksOnCurrentSelection )
        self._parser_list_ctrl_panel.AddButton( 'try to fill in gaps based on example urls', self._TryToLinkURLClassesAndParsers, enabled_check_func = self._GapsExist )
        
        #
        
        api_pairs = ClientNetworkingDomain.ConvertURLClassesIntoAPIPairs( url_classes )
        
        self._api_pairs_list_ctrl.AddDatas( api_pairs )
        
        self._api_pairs_list_ctrl.Sort( 0 )
        
        # anything that goes to an api url will be parsed by that api's parser--it can't have its own
        api_pair_unparsable_url_classes = set()
        
        for ( a, b ) in api_pairs:
            
            api_pair_unparsable_url_classes.add( a )
            
        
        #
        
        listctrl_data = []
        
        for url_class in url_classes:
            
            if not url_class.IsParsable() or url_class in api_pair_unparsable_url_classes:
                
                continue
                
            
            url_class_key = url_class.GetMatchKey()
            
            if url_class_key in url_class_keys_to_parser_keys:
                
                parser_key = url_class_keys_to_parser_keys[ url_class_key ]
                
            else:
                
                parser_key = None
                
            
            listctrl_data.append( ( url_class_key, parser_key ) )
            
        
        self._parser_list_ctrl.AddDatas( listctrl_data )
        
        self._parser_list_ctrl.Sort( 1 )
        
        #
        
        self._notebook.addTab( self._parser_list_ctrl_panel, 'parser links' )
        self._notebook.addTab( self._api_pairs_list_ctrl, 'api link review' )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    def _ClearParser( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Clear all the selected linked parsers?' )
        
        if result == QW.QDialog.Accepted:
            
            for data in self._parser_list_ctrl.GetData( only_selected = True ):
                
                self._parser_list_ctrl.DeleteDatas( ( data, ) )
                
                ( url_class_key, parser_key ) = data
                
                new_data = ( url_class_key, None )
                
                self._parser_list_ctrl.AddDatas( ( new_data, ) )
                
            
            self._parser_list_ctrl.Sort()
            
        
    
    def _ConvertAPIPairDataToListCtrlTuples( self, data ):
        
        ( a, b ) = data
        
        a_name = a.GetName()
        b_name = b.GetName()
        
        pretty_a_name = a_name
        pretty_b_name = b_name
        
        display_tuple = ( pretty_a_name, pretty_b_name )
        sort_tuple = ( a_name, b_name )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ConvertParserDataToListCtrlTuples( self, data ):
        
        ( url_class_key, parser_key ) = data
        
        url_class = self._url_class_keys_to_url_classes[ url_class_key ]
        
        url_class_name = url_class.GetName()
        
        url_type = url_class.GetURLType()
        
        if parser_key is None:
            
            parser_name = ''
            
        else:
            
            parser = self._parser_keys_to_parsers[ parser_key ]
            
            parser_name = parser.GetName()
            
        
        pretty_url_class_name = url_class_name
        
        pretty_url_type = HC.url_type_string_lookup[ url_type ]
        
        pretty_parser_name = parser_name
        
        display_tuple = ( pretty_url_class_name, pretty_url_type, pretty_parser_name )
        sort_tuple = ( url_class_name, pretty_url_type, parser_name )
        
        return ( display_tuple, sort_tuple )
        
    
    def _EditParser( self ):
        
        if len( self._parsers ) == 0:
            
            QW.QMessageBox.information( self, 'Information', 'Unfortunately, you do not have any parsers, so none can be linked to your url classes. Please create some!' )
            
            return
            
        
        for data in self._parser_list_ctrl.GetData( only_selected = True ):
            
            ( url_class_key, parser_key ) = data
            
            url_class = self._url_class_keys_to_url_classes[ url_class_key ]
            
            choice_tuples = [ ( parser.GetName(), parser ) for parser in self._parsers ]
            
            try:
                
                parser = ClientGUIDialogsQuick.SelectFromList( self, 'select parser for ' + url_class.GetName(), choice_tuples )
                
            except HydrusExceptions.CancelledException:
                
                break
                
            
            self._parser_list_ctrl.DeleteDatas( ( data, ) )
            
            new_data = ( url_class_key, parser.GetParserKey() )
            
            self._parser_list_ctrl.AddDatas( ( new_data, ) )
            
        
        self._parser_list_ctrl.Sort()
        
    
    def _GapsExist( self ):
        
        return None in ( parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData() )
        
    
    def _LinksOnCurrentSelection( self ):
        
        non_none_parser_keys = [ parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData( only_selected = True ) if parser_key is not None ]
        
        return len( non_none_parser_keys ) > 0
        
    
    def _TryToLinkURLClassesAndParsers( self ):
        
        existing_url_class_keys_to_parser_keys = { url_class_key : parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData() if parser_key is not None }
        
        new_url_class_keys_to_parser_keys = ClientNetworkingDomain.NetworkDomainManager.STATICLinkURLClassesAndParsers( self._url_classes, self._parsers, existing_url_class_keys_to_parser_keys )
        
        if len( new_url_class_keys_to_parser_keys ) > 0:
            
            removees = []
            
            for row in self._parser_list_ctrl.GetData():
                
                ( url_class_key, parser_key ) = row
                
                if url_class_key in new_url_class_keys_to_parser_keys:
                    
                    removees.append( row )
                    
                
            
            self._parser_list_ctrl.DeleteDatas( removees )
            
            self._parser_list_ctrl.AddDatas( list(new_url_class_keys_to_parser_keys.items()) )
            
            self._parser_list_ctrl.Sort()
            
        
    
    def GetValue( self ):
        
        url_class_keys_to_parser_keys = { url_class_key : parser_key for ( url_class_key, parser_key ) in self._parser_list_ctrl.GetData() if parser_key is not None }
        
        return url_class_keys_to_parser_keys
        
    
