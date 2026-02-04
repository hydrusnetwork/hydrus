import collections.abc

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.metadata import ClientGUITime
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUIBandwidth
from hydrus.client.gui.widgets import ClientGUICommon

class EditAccountTypePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, service_type: int, account_type: HydrusNetwork.AccountType ):
        
        super().__init__( parent )
        
        self._account_type_key = account_type.GetAccountTypeKey()
        title = account_type.GetTitle()
        permissions = account_type.GetPermissions()
        bandwidth_rules = account_type.GetBandwidthRules()
        
        auto_create_velocity = account_type.GetAutoCreateAccountVelocity()
        self._auto_create_history = account_type.GetAutoCreateAccountHistory()
        
        self._title = QW.QLineEdit( self )
        
        permission_choices = self._GeneratePermissionChoices( service_type )
        
        self._permission_controls = []
        
        self._permissions_panel = ClientGUICommon.StaticBox( self, 'permissions' )
        
        gridbox_rows = []
        
        for ( content_type, action_rows ) in permission_choices:
            
            choice_control = ClientGUICommon.BetterChoice( self._permissions_panel )
            
            for ( label, action ) in action_rows:
                
                choice_control.addItem( label, ( content_type, action ) )
                
            
            if content_type in permissions:
                
                selection_row = ( content_type, permissions[ content_type ] )
                
            else:
                
                selection_row = ( content_type, None )
                
            
            try:
                
                choice_control.SetValue( selection_row )
                
            except Exception as e:
                
                choice_control.SetValue( ( content_type, None ) )
                
            
            self._permission_controls.append( choice_control )
            
            gridbox_label = HC.content_type_string_lookup[ content_type ]
            
            gridbox_rows.append( ( gridbox_label, choice_control ) )
            
        
        gridbox = ClientGUICommon.WrapInGrid( self._permissions_panel, gridbox_rows )
        
        self._bandwidth_rules_control = ClientGUIBandwidth.BandwidthRulesCtrl( self, bandwidth_rules )
        
        self._auto_creation_box = ClientGUICommon.StaticBox( self, 'automatic account creation' )
        
        min_unit_value = 0
        max_unit_value = 65565
        min_time_delta = 60 * 60
        
        self._auto_create_velocity_control = ClientGUITime.VelocityCtrl( self._auto_creation_box, min_unit_value, max_unit_value, min_time_delta, days = True, hours = True, unit = 'accounts' )
        
        self._auto_create_history_st = ClientGUICommon.BetterStaticText( self._auto_creation_box, label = 'initialising' )
        
        #
        
        self._title.setText( title )
        
        self._auto_create_velocity_control.SetValue( auto_create_velocity )
        
        #
        
        intro = 'If you wish, you can allow new users to create their own accounts. They will be limited to a certain number over a particular time.'
        intro += '\n' * 2
        intro += 'Set to 0 to disable auto-creation.'
        
        st = ClientGUICommon.BetterStaticText( self._auto_creation_box, label = intro )
        st.setWordWrap( True )
        
        self._auto_creation_box.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._auto_creation_box.Add( self._auto_create_history_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._auto_creation_box.Add( self._auto_create_velocity_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        t_hbox = ClientGUICommon.WrapInText( self._title, self, 'title: ' )
        
        self._permissions_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, t_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, self._permissions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._bandwidth_rules_control, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._auto_creation_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._UpdateAutoCreationHistoryText()
        
        self._auto_create_velocity_control.velocityChanged.connect( self._UpdateAutoCreationHistoryText )
        
    
    def _GeneratePermissionChoices( self, service_type ):
        
        possible_permissions = HydrusNetwork.GetPossiblePermissions( service_type )
        
        permission_choices = []
        
        for ( content_type, possible_actions ) in possible_permissions:
            
            choices = []
            
            for action in possible_actions:
                
                choices.append( ( HC.permission_pair_string_lookup[ ( content_type, action ) ], action ) )
                
            
            permission_choices.append( ( content_type, choices ) )
            
        
        return permission_choices
        
    
    def _UpdateAutoCreationHistoryText( self ):
        
        ( accounts_per_time_delta, time_delta ) = self._auto_create_velocity_control.GetValue()
        
        text = ''
        
        if accounts_per_time_delta == 0:
            
            text = 'Auto-creation disabled. '
            
        
        num_created = self._auto_create_history.GetUsage( HC.BANDWIDTH_TYPE_DATA, time_delta )
        
        text += '{} auto-created in the past {}.'.format( HydrusNumbers.ToHumanInt( num_created ), HydrusTime.TimeDeltaToPrettyTimeDelta( time_delta ) )
        
        self._auto_create_history_st.setText( text )
        
    
    def GetValue( self ) -> HydrusNetwork.AccountType:
        
        title = self._title.text()
        
        permissions = {}
        
        for permission_control in self._permission_controls:
            
            ( content_type, action ) = permission_control.GetValue()
            
            if action is not None:
                
                permissions[ content_type ] = action
                
            
        
        bandwidth_rules = self._bandwidth_rules_control.GetValue()
        
        auto_creation_velocity = self._auto_create_velocity_control.GetValue()
        
        return HydrusNetwork.AccountType(
            account_type_key = self._account_type_key,
            title = title,
            permissions = permissions,
            bandwidth_rules = bandwidth_rules,
            auto_creation_velocity = auto_creation_velocity,
            auto_creation_history = self._auto_create_history
        )
        
    
class EditAccountTypesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, service_type, account_types ):
        
        self._service_type = service_type
        self._original_account_types = account_types
        
        super().__init__( parent )
        
        self._deletee_account_type_keys_to_new_account_type_keys = {}
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_ACCOUNT_TYPES.ID, self._ConvertAccountTypeToDataTuple, self._ConvertAccountTypeToSortTuple )
        
        self._account_types_listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self, 20, model, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._Add )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        self._account_types_listctrl.AddDatas( self._original_account_types )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._edit_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._account_types_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self ):
        
        title = 'new account type'
        permissions = {}
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        
        account_type = HydrusNetwork.AccountType.GenerateNewAccountType( title, permissions, bandwidth_rules )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit account type' ) as dlg_edit:
            
            panel = EditAccountTypePanel( dlg_edit, self._service_type, account_type )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_account_type = panel.GetValue()
                
                self._account_types_listctrl.AddData( new_account_type, select_sort_and_scroll = True )
                
            
        
    
    def _ConvertAccountTypeToDataTuple( self, account_type: HydrusNetwork.AccountType ):
        
        title = account_type.GetTitle()
        
        if account_type.IsNullAccount():
            
            title = '{} (cannot be edited)'.format( title )
            
        
        display_tuple = ( title, )
        
        return display_tuple
        
    
    _ConvertAccountTypeToSortTuple = _ConvertAccountTypeToDataTuple
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            account_types_about_to_delete = self._account_types_listctrl.GetData( only_selected = True )
            
            if True in ( at.IsNullAccount() for at in account_types_about_to_delete ):
                
                ClientGUIDialogsMessage.ShowWarning( self, 'You cannot delete the null account type!' )
                
                return
                
            
            all_real_account_types = set( [ at for at in self._account_types_listctrl.GetData() if not at.IsNullAccount() ] )
            
            account_types_can_move_to = all_real_account_types.difference( account_types_about_to_delete )
            
            if len( account_types_can_move_to ) == 0:
                
                ClientGUIDialogsMessage.ShowWarning( self, 'You cannot delete every account type!' )
                
                return
                
            
            for deletee_account_type in account_types_about_to_delete:
                
                if len( account_types_can_move_to ) > 1:
                    
                    deletee_title = deletee_account_type.GetTitle()
                    
                    choice_tuples = [ ( account_type.GetTitle(), account_type ) for account_type in account_types_can_move_to ]
                    
                    try:
                        
                        new_account_type = ClientGUIDialogsQuick.SelectFromList( self, 'what should deleted ' + deletee_title + ' accounts become?', choice_tuples )
                        
                    except HydrusExceptions.CancelledException:
                        
                        return
                        
                    
                else:
                    
                    ( new_account_type, ) = account_types_can_move_to
                    
                
                deletee_account_type_key = deletee_account_type.GetAccountTypeKey()
                new_account_type_key = new_account_type.GetAccountTypeKey()
                
                self._deletee_account_type_keys_to_new_account_type_keys[ deletee_account_type_key ] = new_account_type_key
                
            
            self._account_types_listctrl.DeleteSelected()
            
        
    
    def _Edit( self ):
        
        data = self._account_types_listctrl.GetTopSelectedData()
        
        if data is None:
            
            return
            
        
        account_type = data
        
        if account_type.IsNullAccount():
            
            ClientGUIDialogsMessage.ShowWarning( self, 'You cannot edit the null account type!' )
            
            return
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit account type' ) as dlg_edit:
            
            panel = EditAccountTypePanel( dlg_edit, self._service_type, account_type )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_account_type = panel.GetValue()
                
                self._account_types_listctrl.ReplaceData( account_type, edited_account_type, sort_and_scroll = True )
                
            
        
    
    def GetValue( self ):
        
        account_types = [ at for at in self._original_account_types if at.IsNullAccount() ]
        
        account_types.extend( [ at for at in self._account_types_listctrl.GetData() if not at.IsNullAccount() ] )
        
        def key_transfer_not_collapsed():
            
            keys = set( self._deletee_account_type_keys_to_new_account_type_keys.keys() )
            values = set( self._deletee_account_type_keys_to_new_account_type_keys.values() )
            
            return HydrusLists.SetsIntersect( keys, values )
            
        
        while key_transfer_not_collapsed():
            
            # some deletees are going to other deletees, so lets collapse
            
            deletee_account_type_keys = set( self._deletee_account_type_keys_to_new_account_type_keys.keys() )
            
            account_type_keys_tuples = list(self._deletee_account_type_keys_to_new_account_type_keys.items())
            
            for ( deletee_account_type_key, new_account_type_key ) in account_type_keys_tuples:
                
                if new_account_type_key in deletee_account_type_keys:
                    
                    better_new_account_type_key = self._deletee_account_type_keys_to_new_account_type_keys[ new_account_type_key ]
                    
                    self._deletee_account_type_keys_to_new_account_type_keys[ deletee_account_type_key ] = better_new_account_type_key
                    
                
            
        
        return ( account_types, self._deletee_account_type_keys_to_new_account_type_keys )
        
    
class ListAccountsPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, accounts: list[ HydrusNetwork.Account ] ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._service = CG.client_controller.services_manager.GetService( self._service_key )
        self._accounts = accounts
        
        self._accounts_box = ClientGUICommon.StaticBox( self, 'accounts' )
        
        self._account_list = ClientGUIListBoxes.BetterQListWidget( self._accounts_box )
        self._account_list.setSelectionMode( QW.QAbstractItemView.SelectionMode.ExtendedSelection )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._account_list, ( 74, 16 ) )
        
        self._account_list.setMinimumSize( min_width, min_height )
        
        modify_button = ClientGUICommon.BetterButton( self._accounts_box, 'modify selected', self._ModifyAccounts )
        
        #
        
        my_admin_account_key = self._service.GetAccount().GetAccountKey()
        
        accounts.sort( key = lambda a: ( a.GetAccountType().GetTitle(), a.GetAccountKey().hex() ) )
        
        for account in accounts:
            
            item = QW.QListWidgetItem()
            
            account_key = account.GetAccountKey()
            
            text = account.GetSingleLineTitle()
            
            if account_key == my_admin_account_key:
                
                text = 'THIS IS YOU: {}'.format( text )
                
            
            item.setText( text )
            
            item.setData( QC.Qt.ItemDataRole.UserRole, account )
            
            self._account_list.addItem( item )
            
        
        #
        
        self._accounts_box.Add( self._account_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._accounts_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, modify_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._account_list.itemDoubleClicked.connect( self._ModifyAccounts )
        
    
    def _ModifyAccounts( self ):
        
        accounts = self._account_list.GetData( only_selected = True )
        
        if len( accounts ) > 0:
            
            subject_account_identifiers = [ HydrusNetwork.AccountIdentifier( account_key = account.GetAccountKey() ) for account in accounts ]
            
            frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self.window().parentWidget(), 'manage accounts' )
            
            panel = ModifyAccountsPanel( frame, self._service_key, subject_account_identifiers )
            
            frame.SetPanel( panel )
            
        
    
class ReviewAccountsPanel( QW.QWidget ):
    
    accountsFetchFinished = QC.Signal()
    accountsFetchStarted = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, account_identifiers: collections.abc.Collection[ HydrusNetwork.AccountIdentifier ] ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._service = CG.client_controller.services_manager.GetService( self._service_key )
        self._account_identifiers = account_identifiers
        
        self._done_first_fetch = False
        self._accounts_loaded = False
        self._account_keys_to_accounts = {}
        self._account_keys_to_account_info = {}
        
        self._accounts_box = ClientGUICommon.StaticBox( self, 'accounts' )
        
        self._status_st = ClientGUICommon.BetterStaticText( self._accounts_box )
        
        self._account_list = ClientGUICommon.BetterCheckBoxList( self._accounts_box )
        self._account_list.setSelectionMode( QW.QAbstractItemView.SelectionMode.SingleSelection )
        
        min_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._account_list, 74 )
        
        self._account_list.setMinimumWidth( min_width )
        
        height_num_rows = min( max( 6, len( account_identifiers ) ), 20 )
        
        self._account_list.SetHeightNumChars( height_num_rows )
        
        self._account_info_box = QW.QTextEdit( self._accounts_box )
        self._account_info_box.setReadOnly( True )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._account_info_box, ( 16, 8 ) )
        
        self._account_info_box.setMinimumHeight( min_height )
        
        self._copy_checked_account_keys_button = ClientGUICommon.BetterButton( self._accounts_box, 'copy checked account ids', self._CopyCheckedAccountKeys )
        
        #
        
        self._accounts_box.Add( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._accounts_box.Add( self._account_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._accounts_box.Add( self._account_info_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._accounts_box.Add( self._copy_checked_account_keys_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._accounts_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.setLayout( vbox )
        
        #
        
        self._account_list.itemClicked.connect( self._AccountClicked )
        
    
    def _AccountClicked( self ):
        
        selected_indices = sorted( self._account_list.GetSelectedIndices() )
        
        if len( selected_indices ) > 0:
            
            item = self._account_list.item( selected_indices[0] )
            
            account_info_components = []
            
            account_key = item.data( QC.Qt.ItemDataRole.UserRole )
            
            my_admin_account = self._service.GetAccount()
            
            if account_key == my_admin_account.GetAccountKey():
                
                account_info_components.append( 'THIS IS YOU' )
                
            
            if account_key in self._account_keys_to_accounts:
                
                account = self._account_keys_to_accounts[ account_key ]
                
                account_info_components.append( account.ToString() )
                account_info_components.append( account.GetExpiresString() )
                account_info_components.append( account.GetStatusInfo()[1] )
                
                ( message, message_created ) = account.GetMessageAndTimestamp()
                
                if message != '':
                    
                    account_info_components.append( 'Message: {}'.format( message ) )
                    
                else:
                    
                    account_info_components.append( 'No message set.' )
                    
                
                if account_key in self._account_keys_to_account_info:
                    
                    account_info = self._account_keys_to_account_info[ account_key ]
                    
                    if isinstance( account_info, dict ):
                        
                        keys_in_order = sorted( account_info.keys() )
                        
                        account_info_components.append( '\n'.join( ( '{}: {}'.format( key, account_info[ key ] ) for key in keys_in_order ) ) )
                        
                    else:
                        
                        account_info_components.append( str( account_info ) )
                        
                    
                else:
                    
                    account_info_components.append( 'Could not find info for this account!' )
                    
                
            else:
                
                account_info_components.append( 'Could not find this account!' )
                
            
            joiner = '\n' * 2
            
            account_info = joiner.join( account_info_components )
            
        else:
            
            account_info = ''
            
        
        self._account_info_box.setText( account_info )
        
    
    def _CopyCheckedAccountKeys( self ):
        
        checked_account_keys = self.GetCheckedAccountKeys()
        
        if len( checked_account_keys ) > 0:
            
            account_keys_text = '\n'.join( ( account_key.hex() for account_key in checked_account_keys ) )
            
            CG.client_controller.pub( 'clipboard', 'text', account_keys_text )
            
        
    
    def _RefreshAccounts( self ):
        
        # TODO: so, rework this guy, and modifyaccounts parent, to not hold account_identifiers, but account_keys. have an async lookup convert contents to account keys before launching this guy
        
        account_identifiers = self._account_identifiers
        service = self._service
        
        pre_refresh_selected_account_keys = { item.data( QC.Qt.ItemDataRole.UserRole ) for item in self._account_list.selectedItems() }
        
        checked_account_keys = self.GetCheckedAccountKeys()
        
        def work_callable():
            
            account_errors = set()
            
            account_keys_to_accounts = {}
            account_keys_to_account_info = {}
            
            for account_identifier in account_identifiers:
                
                try:
                    
                    result = service.Request( HC.GET, 'other_account', { 'subject_identifier' : account_identifier } )
                    
                except Exception as e:
                    
                    account_errors.add( str( e ) )
                    
                    continue
                    
                
                if 'account' in result:
                    
                    account = result[ 'account' ]
                    
                    subject_account_key = account.GetAccountKey()
                    
                    if subject_account_key in account_keys_to_accounts:
                        
                        continue
                        
                    
                    account_keys_to_accounts[ subject_account_key ] = account
                    
                    try:
                        
                        response = self._service.Request( HC.GET, 'account_info', { 'subject_account_key' : subject_account_key } )
                        
                    except Exception as e:
                        
                        HydrusData.PrintException( e )
                        
                        continue
                        
                    
                    account_info = response[ 'account_info' ]
                    
                    account_keys_to_account_info[ subject_account_key ] = account_info
                    
                
            
            return ( account_keys_to_accounts, account_keys_to_account_info, account_errors )
            
        
        def publish_callable( result ):
            
            ( self._account_keys_to_accounts, self._account_keys_to_account_info, account_errors ) = result
            
            if len( account_errors ) > 0:
                
                account_errors = sorted( account_errors )
                
                ClientGUIDialogsMessage.ShowInformation( self, 'Errors were encountered during account fetch:{}{}'.format( '\n' * 2, '\n'.join( account_errors ) ) )
                
            
            if not self._done_first_fetch:
                
                # if we launched with CPU-expensive mapping identifiers, let's move to nice account ids for future refreshes
                
                self._account_identifiers = [ HydrusNetwork.AccountIdentifier( account_key = account_key ) for account_key in self._account_keys_to_accounts.keys() ]
                
            
            #
            
            account_keys_sorted = sorted(
                list( self._account_keys_to_accounts.keys() ),
                key = lambda sak: ( self._account_keys_to_accounts[ sak ].GetAccountType().GetTitle(), sak.hex() )
            )
            
            my_admin_account = self._service.GetAccount()
            
            my_admin_account_key = my_admin_account.GetAccountKey()
            
            for account_key in account_keys_sorted:
                
                item = QW.QListWidgetItem()
                
                item.setFlags( item.flags() | QC.Qt.ItemFlag.ItemIsUserCheckable )
                
                account = self._account_keys_to_accounts[ account_key ]
                
                text = account.GetSingleLineTitle()
                
                if account_key == my_admin_account_key:
                    
                    text = 'THIS IS YOU: {}'.format( text )
                    
                
                item.setText( text )
                
                if not self._done_first_fetch or account_key in checked_account_keys:
                    
                    item.setCheckState( QC.Qt.CheckState.Checked )
                    
                else:
                    
                    item.setCheckState( QC.Qt.CheckState.Unchecked )
                    
                
                item.setData( QC.Qt.ItemDataRole.UserRole, account_key )
                
                self._account_list.addItem( item )
                
                if account_key in pre_refresh_selected_account_keys:
                    
                    item.setSelected( True )
                    
                
            
            #
            
            self._status_st.setVisible( False )
            self._status_st.setText( '' )
            
            if self._account_list.count() > 0:
                
                if len( self._account_list.selectedItems() ) == 0:
                    
                    self._account_list.item( 0 ).setSelected( True )
                    
                
                self._AccountClicked()
                
            
            self._accounts_loaded = True
            self._done_first_fetch = True
            
            self.accountsFetchFinished.emit()
            
        
        self._status_st.setVisible( True )
        self._status_st.setText( 'fetching accounts' + HC.UNICODE_ELLIPSIS )
        
        self._accounts_loaded = False
        
        self._account_list.clear()
        
        self._account_info_box.clear()
        
        self._account_keys_to_accounts = {}
        self._account_keys_to_account_info = {}
        
        self.accountsFetchStarted.emit()
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def AccountsLoaded( self ):
        
        return self._accounts_loaded
        
    
    def GetCheckedAccountKeys( self ):
        
        account_keys = set()
        
        for i in range( self._account_list.count() ):
            
            item = self._account_list.item( i )
            
            if item.checkState() == QC.Qt.CheckState.Checked:
                
                account_keys.add( item.data( QC.Qt.ItemDataRole.UserRole ) )
                
            
        
        return account_keys
        
    
    def GetCheckedAccounts( self ):
        
        checked_account_keys = self.GetCheckedAccountKeys()
        
        return { self._account_keys_to_accounts[ account_key ] for account_key in checked_account_keys }
        
    
    def RefreshAccounts( self ):
        
        self._RefreshAccounts()
        
    
    def UncheckAccountKey( self, account_key: bytes ):
        
        for i in range( self._account_list.count() ):
            
            item = self._account_list.item( i )
            
            checked_account_key = item.data( QC.Qt.ItemDataRole.UserRole )
            
            if checked_account_key == account_key:
                
                item.setCheckState( QC.Qt.CheckState.Unchecked )
                
                return
                
            
        
    
    def UncheckNullAccount( self ):
        
        for i in range( self._account_list.count() ):
            
            item = self._account_list.item( i )
            
            account_key = item.data( QC.Qt.ItemDataRole.UserRole )
            
            account = self._account_keys_to_accounts[ account_key ]
            
            if account.IsNullAccount():
                
                item.setCheckState( QC.Qt.CheckState.Unchecked )
                
                return
                
            
        
    

class ModifyAccountsPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, service_key: bytes, subject_identifiers: collections.abc.Collection[ HydrusNetwork.AccountIdentifier ]  ):
        
        super().__init__( parent )
        
        self._service_key = service_key
        self._service = CG.client_controller.services_manager.GetService( service_key )
        self._subject_identifiers = subject_identifiers
        self._account_types = []
        
        #
        
        self._account_panel = ReviewAccountsPanel( self, service_key, subject_identifiers )
        
        #
        
        self._message_panel = ClientGUICommon.StaticBox( self, 'message' )
        
        self._message_text = QW.QLineEdit( self._message_panel )
        
        self._set_message_button = ClientGUICommon.BetterButton( self._message_panel, 'set message', self._DoSetMessage )
        
        #
        
        self._expiration_panel = ClientGUICommon.StaticBox( self, 'change expiration' )
        
        self._add_to_expires = ClientGUICommon.BetterChoice( self._expiration_panel )
        
        for ( label, value ) in HC.lifetimes:
            
            if value is not None:
                
                self._add_to_expires.addItem( label, value )
                
            
        
        self._add_to_expires_button = ClientGUICommon.BetterButton( self._expiration_panel, 'ok', self._AddToExpires )
        
        self._set_expires = ClientGUICommon.BetterChoice( self._expiration_panel )
        
        for ( label, value ) in HC.lifetimes:
            
            self._set_expires.addItem( label, value )
            
        
        self._set_expires_button = ClientGUICommon.BetterButton( self._expiration_panel, 'ok', self._SetExpires )
        
        #
        
        self._account_types_panel = ClientGUICommon.StaticBox( self, 'set to account type' )
        
        self._account_types_choice = ClientGUICommon.BetterChoice( self._account_types_panel )
        
        self._account_types_button = ClientGUICommon.BetterButton( self._account_types_panel, 'set to type', self._DoAccountType )
        
        #
        
        self._ban_panel = ClientGUICommon.StaticBox( self, 'bans' )
        
        self._ban_reason = QW.QLineEdit( self._ban_panel )
        
        self._ban_expires = ClientGUICommon.BetterChoice( self._ban_panel )
        
        for ( label, value ) in HC.lifetimes:
            
            self._ban_expires.addItem( label, value )
            
        
        self._ban_button = ClientGUICommon.BetterButton( self._ban_panel, 'ban account', self._DoBan )
        self._unban_button = ClientGUICommon.BetterButton( self._ban_panel, 'unban account', self._DoUnban )
        
        self._delete_all_account_content_button = ClientGUICommon.BetterButton( self._ban_panel, '! delete all account content !', self._DoDeleteAllAccountContent )
        
        #
        
        self._add_to_expires.SetValue( 3 * 31 * 86400 ) # three months
        
        self._set_expires.SetValue( 3 * 31 * 86400 ) # three months
        
        #
        
        gridbox_rows = []
        
        gridbox_rows.append( ( 'message:', self._message_text ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._message_panel, gridbox_rows )
        
        self._message_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._message_panel.Add( self._set_message_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        add_to_expires_box = QP.HBoxLayout()
        
        QP.AddToLayout( add_to_expires_box, QW.QLabel( 'add to expires: ', self._expiration_panel ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( add_to_expires_box, self._add_to_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( add_to_expires_box, self._add_to_expires_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        set_expires_box = QP.HBoxLayout()
        
        QP.AddToLayout( set_expires_box, QW.QLabel( 'set expires to: ', self._expiration_panel ), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( set_expires_box, self._set_expires, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( set_expires_box, self._set_expires_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._expiration_panel.Add( add_to_expires_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._expiration_panel.Add( set_expires_box, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        account_types_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( account_types_hbox, self._account_types_choice, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( account_types_hbox, self._account_types_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._account_types_panel.Add( account_types_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        gridbox_rows = []
        
        gridbox_rows.append( ( 'ban reason:', self._ban_reason ) )
        gridbox_rows.append( ( 'ban expiration:', self._ban_expires ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._ban_panel, gridbox_rows )
        
        self._ban_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._ban_panel.Add( self._ban_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._ban_panel.Add( self._unban_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._ban_panel.Add( self._delete_all_account_content_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        self._modification_status = ClientGUICommon.BetterStaticText( self )
        
        QP.AddToLayout( vbox, self._modification_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._account_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._message_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._account_types_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._expiration_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._ban_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._account_panel.accountsFetchStarted.connect( self._DisableUIForRefresh )
        self._account_panel.accountsFetchFinished.connect( self._EnableUIAfterRefresh )
        
        #
        
        self._InitialiseAccountTypes()
        
        self._account_panel.RefreshAccounts()
        
    
    def _AddToExpires( self ):
        
        expires_delta = self._add_to_expires.GetValue()
        
        self._account_panel.UncheckNullAccount()
        
        subject_accounts = self._account_panel.GetCheckedAccounts()
        
        num_unchecked = 0
        
        for subject_account in subject_accounts:
            
            if subject_account.GetExpires() is None:
                
                self._account_panel.UncheckAccountKey( subject_account.GetAccountKey() )
                
                num_unchecked += 1
                
            
        
        if num_unchecked > 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, '{} accounts do not expire, so could not have time added!'.format( HydrusNumbers.ToHumanInt( num_unchecked ) ) )
            
        
        subject_accounts = self._account_panel.GetCheckedAccounts()
        
        if len( subject_accounts ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'No accounts selected for action!' )
            
            return
            
        
        message = 'Add {} to expiry for {} accounts?'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( expires_delta ), HydrusNumbers.ToHumanInt( len( subject_accounts ) ) )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        subject_account_keys_and_current_expires = [ ( subject_account.GetAccountKey(), subject_account.GetExpires() ) for subject_account in subject_accounts ]
        
        subject_account_keys_and_new_expires = [ ( subject_account_key, current_expires + expires_delta ) for ( subject_account_key, current_expires ) in subject_account_keys_and_current_expires ]
        
        self._DoExpires( subject_account_keys_and_new_expires )
        
    
    def _DisableUIForJob( self, message ):
        
        self.setEnabled( False )
        
        self._modification_status.setVisible( True )
        
        self._modification_status.setText( message )
        
    
    def _DisableUIForRefresh( self ):
        
        self._DisableUIForJob( 'refreshing accounts' + HC.UNICODE_ELLIPSIS )
        
    
    def _DoAccountType( self ):
        
        self._account_panel.UncheckNullAccount()
        
        subject_account_keys = self._account_panel.GetCheckedAccountKeys()
        
        if len( subject_account_keys ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'No accounts selected for action!' )
            
            return
            
        
        service = self._service
        
        account_type = self._account_types_choice.GetValue()
        
        message = 'Set {} accounts to "{}" type?'.format( HydrusNumbers.ToHumanInt( len( subject_account_keys ) ), account_type.GetTitle() )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        account_type_key = account_type.GetAccountTypeKey()
        
        def work_callable():
            
            for subject_account_key in subject_account_keys:
                
                service.Request( HC.POST, 'modify_account_account_type', { 'subject_account_key' : subject_account_key, 'account_type_key' : account_type_key } )
                
            
            return 1
            
        
        def publish_callable( gumpf ):
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Done!' )
            
            self._account_panel.RefreshAccounts()
            
        
        self._DisableUIForJob( 'setting new account type' + HC.UNICODE_ELLIPSIS )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _DoBan( self ):
        
        self._account_panel.UncheckNullAccount()
        
        subject_accounts = self._account_panel.GetCheckedAccounts()
        
        if len( subject_accounts ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'No accounts selected for action!' )
            
            return
            
        
        some_are_banned =  True in ( subject_account.IsBanned() for subject_account in subject_accounts )
        
        if some_are_banned:
            
            message = 'Some of these selected accounts are already banned. Sure you want to overwrite the bans?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        subject_account_keys = [ subject_account.GetAccountKey() for subject_account in subject_accounts ]
        
        reason = self._ban_reason.text()
        
        if reason == '':
            
            ClientGUIDialogsMessage.ShowInformation( self, 'The ban reason is empty!' )
            
            return
            
        
        message = 'Ban {} account(s)? All of their pending petitions will be deleted serverside.'.format( HydrusNumbers.ToHumanInt( len( subject_account_keys ) ) )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        expires = self._ban_expires.GetValue()
        
        if expires is not None:
            
            expires += HydrusTime.GetNow()
            
        
        service = self._service
        
        def work_callable():
            
            for subject_account_key in subject_account_keys:
                
                service.Request( HC.POST, 'modify_account_ban', { 'subject_account_key' : subject_account_key, 'reason' : reason, 'expires' : expires } )
                
            
            return 1
            
        
        def publish_callable( gumpf ):
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Done!' )
            
            self._account_panel.RefreshAccounts()
            
        
        self._DisableUIForJob( 'banning' + HC.UNICODE_ELLIPSIS )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _DoDeleteAllAccountContent( self ):
        
        self._account_panel.UncheckNullAccount()
        
        subject_accounts = self._account_panel.GetCheckedAccounts()
        
        if len( subject_accounts ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'No accounts selected for action!' )
            
            return
            
        
        subject_account_keys = [ subject_account.GetAccountKey() for subject_account in subject_accounts ]
        
        message = 'Are you absolutely sure you want to delete all uploads for {} accounts? This will delete everything the user(s) have uploaded since the anonymisation date.'.format( HydrusNumbers.ToHumanInt( len( subject_account_keys ) ) )
        
        if self._service.GetServiceType() == HC.TAG_REPOSITORY:
            
            message += '\n' * 2
            message += 'Note that if the user never had permission to add siblings and parents on their own (i.e. they could only ever _petition_ to add them), then their petitioned siblings and parents will not be deleted (janitor accounts take ownership of siblings and parents when they approve them).'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        service = self._service
        
        def work_callable():
            
            all_deleted_ok = True
            
            for subject_account_key in subject_account_keys:
                
                response = service.Request( HC.POST, 'modify_account_delete_all_content', { 'subject_account_key' : subject_account_key } )
                
                if response is not None and isinstance( response, dict ) and 'everything_was_deleted' in response:
                    
                    everything_was_deleted = response[ 'everything_was_deleted' ]
                    
                    if not everything_was_deleted:
                        
                        all_deleted_ok = False
                        
                    
                
            
            return all_deleted_ok
            
        
        def publish_callable( all_deleted_ok ):
            
            if all_deleted_ok:
                
                message = 'Everything deleted!'
                
            else:
                
                message = 'Not everything was deleted--this may be a big account. You can keep trying to chip away at what needs to be deleted, or wait for hydev to figure out a solution for big accounts.'
                
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
            self._account_panel.RefreshAccounts()
            
        
        self._DisableUIForJob( 'deleting' + HC.UNICODE_ELLIPSIS )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _DoExpires( self, subject_account_keys_and_new_expires ):
        
        if len( subject_account_keys_and_new_expires ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'No accounts selected for action!' )
            
            return
            
        
        service = self._service
        
        def work_callable():
            
            for ( subject_account_key, new_expires ) in subject_account_keys_and_new_expires:
                
                service.Request( HC.POST, 'modify_account_expires', { 'subject_account_key' : subject_account_key, 'expires' : new_expires } )
                
            
            return 1
            
        
        def publish_callable( gumpf ):
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Done!' )
            
            self._account_panel.RefreshAccounts()
            
        
        self._DisableUIForJob( 'setting new expiry' + HC.UNICODE_ELLIPSIS )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _DoSetMessage( self ):
        
        self._account_panel.UncheckNullAccount()
        
        subject_accounts = self._account_panel.GetCheckedAccounts()
        
        if len( subject_accounts ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'No accounts selected for action!' )
            
            return
            
        
        message = self._message_text.text()
        
        if message == '':
            
            yn_message = 'Clear message for {} accounts?'.format( HydrusNumbers.ToHumanInt( len( subject_accounts ) ) )
            
        else:
            
            yn_message = 'Set this message for {} accounts?'.format( HydrusNumbers.ToHumanInt( len( subject_accounts ) ) )
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, yn_message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        subject_account_keys = [ subject_account.GetAccountKey() for subject_account in subject_accounts ]
        
        service = self._service
        
        def work_callable():
            
            for subject_account_key in subject_account_keys:
                
                service.Request( HC.POST, 'modify_account_set_message', { 'subject_account_key' : subject_account_key, 'message': message } )
                
            
            return 1
            
        
        def publish_callable( gumpf ):
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Done!' )
            
            self._account_panel.RefreshAccounts()
            
        
        self._DisableUIForJob( 'setting message' + HC.UNICODE_ELLIPSIS )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _DoUnban( self ):
        
        self._account_panel.UncheckNullAccount()
        
        subject_accounts = self._account_panel.GetCheckedAccounts()
        
        if len( subject_accounts ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'No accounts selected for action!' )
            
            return
            
        
        subject_accounts = [ subject_account for subject_account in subject_accounts if subject_account.IsBanned() ]
        
        if len( subject_accounts ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'None of the selected accounts are banned!' )
            
            return
            
        
        subject_account_keys = [ subject_account.GetAccountKey() for subject_account in subject_accounts ]
        
        message = 'Unban {} accounts?'.format( HydrusNumbers.ToHumanInt( len( subject_account_keys ) ) )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        service = self._service
        
        def work_callable():
            
            for subject_account_key in subject_account_keys:
                
                service.Request( HC.POST, 'modify_account_unban', { 'subject_account_key' : subject_account_key } )
                
            
            return 1
            
        
        def publish_callable( gumpf ):
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Done!' )
            
            self._account_panel.RefreshAccounts()
            
        
        self._DisableUIForJob( 'unbanning' + HC.UNICODE_ELLIPSIS )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _EnableUIAfterRefresh( self ):
        
        self._modification_status.setVisible( False )
        
        self._modification_status.setText( '' )
        
        self.setEnabled( True )
        
    
    def _InitialiseAccountTypes( self ):
        
        service = self._service
        
        def work_callable():
            
            response = service.Request( HC.GET, 'account_types' )
            
            account_types = response[ 'account_types' ]
            
            return account_types
            
        
        def publish_callable( result ):
            
            self._account_types = result
            
            self._account_types_choice.setEnabled( True )
            self._account_types_button.setEnabled( True )
            
            self._account_types.sort( key = lambda at: str( at ) )
            
            for account_type in self._account_types:
                
                if account_type.IsNullAccount():
                    
                    continue
                    
                
                self._account_types_choice.addItem( str( account_type ), account_type )
                
            
        
        self._account_types_choice.setEnabled( False )
        self._account_types_button.setEnabled( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _SetExpires( self ):
        
        self._account_panel.UncheckNullAccount()
        
        expires = self._set_expires.GetValue()
        
        if expires is not None:
            
            expires += HydrusTime.GetNow()
            
        
        subject_account_keys_and_new_expires = [ ( subject_account_key, expires ) for subject_account_key in self._account_panel.GetCheckedAccountKeys() ]
        
        if len( subject_account_keys_and_new_expires ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'No accounts selected for action!' )
            
            return
            
        
        message = 'Set expiry to {} for {} accounts?'.format( HydrusTime.TimestampToPrettyExpires( expires ), HydrusNumbers.ToHumanInt( len( subject_account_keys_and_new_expires ) ) )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.DialogCode.Accepted:
            
            return
            
        
        self._DoExpires( subject_account_keys_and_new_expires )
        
    
