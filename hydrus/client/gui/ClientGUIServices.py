import os

from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNetwork
from hydrus.core import HydrusNetworking
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTagArchive

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientServices
from hydrus.client.gui import ClientGUICommon
from hydrus.client.gui import ClientGUIControls
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIPanels
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.metadata import ClientRatings
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingJobs

class EditServersideService( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent: QW.QWidget, serverside_service: HydrusNetwork.ServerService ):
        
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
        
    
    def GetValue( self ) -> HydrusNetwork.ServerService:
        
        ( name, port, dictionary_part ) = self._service_panel.GetValue()
        
        dictionary = self._dictionary.Duplicate()
        
        dictionary.update( dictionary_part )
        
        for panel in self._panels:
            
            dictionary_part = panel.GetValue()
            
            dictionary.update( dictionary_part )
            
        
        return HydrusNetwork.GenerateService( self._service_key, self._service_type, name, port, dictionary )
        
    
    class _ServicePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent: QW.QWidget, name: str, port: int, dictionary ):
            
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
        
        def __init__( self, parent: QW.QWidget, dictionary ):
            
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
        
        def __init__( self, parent: QW.QWidget, dictionary ):
            
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
        
        def __init__( self, parent: QW.QWidget, dictionary ):
            
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
            
        
    
class ManageAccountTypesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, service_key ):
        
        self._admin_service = HG.client_controller.services_manager.GetService( service_key )
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._deletee_account_type_keys_to_new_account_type_keys = {}
        
        self._account_types_listctrl = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_ACCOUNT_TYPES.ID, 20, self._ConvertAccountTypeToTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._Add )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        response = self._admin_service.Request( HC.GET, 'account_types' )
        
        account_types = response[ 'account_types' ]
        
        self._account_types_listctrl.AddDatas( account_types )
            
        
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
        
        account_type = HydrusNetwork.AccountType.GenerateNewAccountTypeFromParameters( title, permissions, bandwidth_rules )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit account type' ) as dlg_edit:
            
            panel = ClientGUIScrolledPanelsEdit.EditAccountTypePanel( dlg_edit, self._admin_service.GetServiceType(), account_type )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.Accepted:
                
                new_account_type = panel.GetValue()
                
                self._account_types_listctrl.AddDatas( ( new_account_type, ) )
                
            
        
    
    
    def _ConvertAccountTypeToTuples( self, account_type ):
        
        title = account_type.GetTitle()
        
        display_tuple = ( title, )
        sort_tuple = ( title, )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            account_types_about_to_delete = self._account_types_listctrl.GetData( only_selected = True )
            
            all_account_types = set( self._account_types_listctrl.GetData() )
            
            account_types_can_move_to = all_account_types.difference( account_types_about_to_delete )
            
            if len( account_types_can_move_to ) == 0:
                
                QW.QMessageBox.critical( self, 'Error', 'You cannot delete every account type!' )
                
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
        
        datas = self._account_types_listctrl.GetData( only_selected = True )
        
        for account_type in datas:
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit account type' ) as dlg_edit:
                
                panel = ClientGUIScrolledPanelsEdit.EditAccountTypePanel( dlg_edit, self._admin_service.GetServiceType(), account_type )
                
                dlg_edit.SetPanel( panel )
                
                if dlg_edit.exec() == QW.QDialog.Accepted:
                    
                    edited_account_type = panel.GetValue()
                    
                    self._account_types_listctrl.ReplaceData( account_type, edited_account_type )
                    
                else:
                    
                    return
                    
                
            
        
    
    def CommitChanges( self ):
        
        account_types = self._account_types_listctrl.GetData()
        
        def key_transfer_not_collapsed():
            
            keys = set( self._deletee_account_type_keys_to_new_account_type_keys.keys() )
            values = set( self._deletee_account_type_keys_to_new_account_type_keys.values() )
            
            return HydrusData.SetsIntersect( keys, values )
            
        
        while key_transfer_not_collapsed():
            
            # some deletees are going to other deletees, so lets collapse
            
            deletee_account_type_keys = set( self._deletee_account_type_keys_to_new_account_type_keys.keys() )
            
            account_type_keys_tuples = list(self._deletee_account_type_keys_to_new_account_type_keys.items())
            
            for ( deletee_account_type_key, new_account_type_key ) in account_type_keys_tuples:
                
                if new_account_type_key in deletee_account_type_keys:
                    
                    better_new_account_type_key = self._deletee_account_type_keys_to_new_account_type_keys[ new_account_type_key ]
                    
                    self._deletee_account_type_keys_to_new_account_type_keys[ deletee_account_type_key ] = better_new_account_type_key
                    
                
            
        
        serialisable_deletee_account_type_keys_to_new_account_type_keys = HydrusSerialisable.SerialisableBytesDictionary( self._deletee_account_type_keys_to_new_account_type_keys )
        
        self._admin_service.Request( HC.POST, 'account_types', { 'account_types' : account_types, 'deletee_account_type_keys_to_new_account_type_keys' : serialisable_deletee_account_type_keys_to_new_account_type_keys } )
        
    
class ManageClientServicesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_MANAGE_SERVICES.ID, 25, self._ConvertServiceToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit)
        
        menu_items = []
        
        for service_type in HC.ADDREMOVABLE_SERVICES:
            
            service_string = HC.service_string_lookup[ service_type ]
            
            menu_items.append( ( 'normal', service_string, 'Add a new ' + service_string + '.', HydrusData.Call( self._Add, service_type ) ) )
            
        
        self._add_button = ClientGUICommon.MenuButton( self, 'add', menu_items = menu_items )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        #
        
        self._original_services = HG.client_controller.services_manager.GetServices()
        
        self._listctrl.AddDatas( self._original_services )
        
        self._listctrl.Sort()
        
        #
        
        add_remove_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( add_remove_hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( add_remove_hbox, self._edit_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( add_remove_hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, add_remove_hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
    
    def _Add( self, service_type ):
        
        service_key = HydrusData.GenerateKey()
        name = 'new service'
        
        service = ClientServices.GenerateService( service_key, service_type, name )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit service' ) as dlg:
            
            panel = self._EditPanel( dlg, service )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                new_service = panel.GetValue()
                
                HydrusSerialisable.SetNonDupeName( new_service, self._GetExistingNames() )
                
                self._listctrl.AddDatas( ( new_service, ) )
                
                self._listctrl.Sort()
                
            
        
    
    def _ConvertServiceToListCtrlTuples( self, service ):
        
        service_type = service.GetServiceType()
        name = service.GetName()
        
        deletable = service_type in HC.ADDREMOVABLE_SERVICES
        
        pretty_service_type = HC.service_string_lookup[ service_type ]
        
        if deletable:
            
            if service_type in HC.MUST_HAVE_AT_LEAST_ONE_SERVICES:
                
                pretty_deletable = 'must have at least one'
                
            else:
                
                pretty_deletable = 'yes'
                
            
        else:
            
            pretty_deletable = ''
            
        
        return ( ( name, pretty_service_type, pretty_deletable ), ( name, pretty_service_type, deletable ) )
        
    
    def _GetExistingNames( self ):
        
        services = self._listctrl.GetData()
        
        names = { service.GetName() for service in services }
        
        return names
        
    
    def _Delete( self ):
        
        all_services = self._listctrl.GetData()
        
        selected_services = self._listctrl.GetData( only_selected = True )
        
        deletable_services = [ service for service in selected_services if service.GetServiceType() in HC.ADDREMOVABLE_SERVICES ]
        
        for service_type in HC.MUST_HAVE_AT_LEAST_ONE_SERVICES:
            
            num_in_all = len( [ service for service in all_services if service.GetServiceType() == service_type ] )
            num_in_deletable = len( [ service for service in deletable_services if service.GetServiceType() == service_type ] )
            
            if num_in_deletable == num_in_all:
                
                message = 'Unfortunately, you must have at least one service of the type "{}". You cannot delete them all.'.format( HC.service_string_lookup[ service_type ] )
                
                QW.QMessageBox.information( self, "Information", message )
                
                return
                
            
        
        if len( deletable_services ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Delete the selected services?' )
            
            if result == QW.QDialog.Accepted:
                
                self._listctrl.DeleteDatas( deletable_services )
                
            
        
    
    def _Edit( self ):
        
        selected_services = self._listctrl.GetData( only_selected = True )
        
        try:
            
            for service in selected_services:
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit service' ) as dlg:
                    
                    panel = self._EditPanel( dlg, service )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        self._listctrl.DeleteDatas( ( service, ) )
                        
                        edited_service = panel.GetValue()
                        
                        HydrusSerialisable.SetNonDupeName( edited_service, self._GetExistingNames() )
                        
                        self._listctrl.AddDatas( ( edited_service, ) )
                        
                    else:
                        
                        return
                        
                    
                
            
        finally:
            
            self._listctrl.Sort()
            
        
    
    def CommitChanges( self ):
        
        services = self._listctrl.GetData()
        
        HG.client_controller.SetServices( services )
        
    
    def UserIsOKToOK( self ):
        
        services = self._listctrl.GetData()
        
        new_service_keys = { service.GetServiceKey() for service in services }
        
        deletee_service_names = [ service.GetName() for service in self._original_services if service.GetServiceKey() not in new_service_keys ]
        
        if len( deletee_service_names ) > 0:
            
            message = 'You are about to delete the following services:'
            message += os.linesep * 2
            message += os.linesep.join( deletee_service_names )
            message += os.linesep * 2
            message += 'Are you absolutely sure this is correct?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return False
                
            
        
        return True
        
    
    class _EditPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, service ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            duplicate_service = service.Duplicate()
            
            ( self._service_key, self._service_type, name, self._dictionary ) = duplicate_service.ToTuple()
            
            self._service_panel = self._ServicePanel( self, name )
            
            self._panels = []
            
            if self._service_type in HC.REMOTE_SERVICES:
                
                remote_panel = self._ServiceRemotePanel( self, self._service_type, self._dictionary )
                
                self._panels.append( remote_panel )
                
            
            if self._service_type in HC.RESTRICTED_SERVICES:
                
                self._panels.append( self._ServiceRestrictedPanel( self, self._service_key, remote_panel, self._service_type, self._dictionary ) )
                
            
            if self._service_type in HC.REAL_TAG_SERVICES:
                
                self._panels.append( self._ServiceTagPanel( self, self._dictionary ) )
                
            
            if self._service_type in ( HC.CLIENT_API_SERVICE, HC.LOCAL_BOORU ):
                
                self._panels.append( self._ServiceClientServerPanel( self, self._service_type, self._dictionary ) )
                
            
            if self._service_type in HC.RATINGS_SERVICES:
                
                self._panels.append( self._ServiceRatingsPanel( self, self._dictionary ) )
                
                if self._service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    self._panels.append( self._ServiceRatingsNumericalPanel( self, self._dictionary ) )
                    
                
            
            if self._service_type == HC.IPFS:
                
                self._panels.append( self._ServiceIPFSPanel( self, self._dictionary ) )
                
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._service_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            for panel in self._panels:
                
                QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            self.widget().setLayout( vbox )
            
        
        def _GetArchiveNameToDisplay( self, portable_hta_path, namespaces ):
            
            hta_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_hta_path )
            
            if len( namespaces ) == 0: name_to_display = hta_path
            else: name_to_display = hta_path + ' (' + ', '.join( HydrusData.ConvertUglyNamespacesToPrettyStrings( namespaces ) ) + ')'
            
            return name_to_display
            
        
        def EventArchiveAdd( self, event ):
            
            if self._archive_sync.GetCount() == 0:
                
                QW.QMessageBox.warning( self, 'Warning', 'Be careful with this tool! Syncing a lot of files to a large archive can take a very long time to initialise.' )
                
            
            text = 'Select the Hydrus Tag Archive\'s location.'
            
            with QP.FileDialog( self, message = text, acceptMode = QW.QFileDialog.AcceptOpen ) as dlg_file:
                
                if dlg_file.exec() == QW.QDialog.Accepted:
                    
                    hta_path = dlg_file.GetPath()
                    
                    portable_hta_path = HydrusPaths.ConvertAbsPathToPortablePath( hta_path )
                    
                    hta = HydrusTagArchive.HydrusTagArchive( hta_path )
                    
                    archive_namespaces = sorted( hta.GetNamespaces() )
                    
                    choice_tuples = [ ( HydrusData.ConvertUglyNamespaceToPrettyString( namespace ), namespace, False ) for namespace in archive_namespaces ]
                    
                    try:
                        
                        namespaces = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select namespaces', choice_tuples )
                        
                    except HydrusExceptions.CancelledException:
                        
                        return
                        
                    
                    name_to_display = self._GetArchiveNameToDisplay( portable_hta_path, namespaces )
                    
                    self._archive_sync.addItem( name_to_display, (portable_hta_path, namespaces) )
                    
                
            
        
        def EventArchiveEdit( self, event ):
            
            selection = self._archive_sync.GetSelection()
            
            if selection != -1:
                
                ( portable_hta_path, existing_namespaces ) = QP.GetClientData( self._archive_sync, selection )
                
                hta_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_hta_path )
                
                if not os.path.exists( hta_path ):
                    
                    QW.QMessageBox.critical( self, 'Error', 'This archive does not seem to exist any longer!' )
                    
                    return
                    
                
                hta = HydrusTagArchive.HydrusTagArchive( hta_path )
                
                archive_namespaces = sorted( hta.GetNamespaces() )
                
                choice_tuples = [ ( HydrusData.ConvertUglyNamespaceToPrettyString( namespace ), namespace, namespace in existing_namespaces ) for namespace in archive_namespaces ]
                
                try:
                    
                    namespaces = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select namespaces', choice_tuples )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
                name_to_display = self._GetArchiveNameToDisplay( portable_hta_path, namespaces )
                
                self._archive_sync.SetString( selection, name_to_display )
                self._archive_sync.SetClientData( selection, ( portable_hta_path, namespaces ) )
                
            
        
        def EventArchiveRemove( self, event ):
            
            selection = self._archive_sync.GetSelection()
            
            if selection != -1:
                
                self._archive_sync.Delete( selection )
                
            
        
        def GetValue( self ):
            
            name = self._service_panel.GetValue()
            
            dictionary = self._dictionary.Duplicate()
            
            for panel in self._panels:
                
                dictionary_part = panel.GetValue()
                
                dictionary.update( dictionary_part )
                
            
            return ClientServices.GenerateService( self._service_key, self._service_type, name, dictionary )
            
        
        class _ServicePanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, name ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'name' )
                
                self._name = QW.QLineEdit( self )
                
                #
                
                self._name.setText( name )
                
                #
                
                self.Add( self._name, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                name = self._name.text()
                
                if name == '':
                    
                    raise HydrusExceptions.VetoException( 'Please enter a name!' )
                    
                
                return name
                
            
        
        class _ServiceRemotePanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, service_type, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'network connection' )
                
                self._service_type = service_type
                
                credentials = dictionary[ 'credentials' ]
                
                self._host = QW.QLineEdit( self )
                self._port = QP.MakeQSpinBox( self, min=1, max=65535, width = 80 )
                
                self._test_address_button = ClientGUICommon.BetterButton( self, 'test address', self._TestAddress )
                
                #
                
                ( host, port ) = credentials.GetAddress()
                
                self._host.setText( host )
                self._port.setValue( port )
                
                #
                
                hbox = QP.HBoxLayout()
                
                QP.AddToLayout( hbox, self._host, CC.FLAGS_EXPAND_BOTH_WAYS )
                QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,':'), CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._port, CC.FLAGS_CENTER_PERPENDICULAR )
                
                wrapped_hbox = ClientGUICommon.WrapInText( hbox, self, 'address: ' )
                
                self.Add( wrapped_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                self.Add( self._test_address_button, CC.FLAGS_ON_RIGHT )
                
            
            def _TestAddress( self ):
                
                def qt_done( message ):
                    
                    if not self or not QP.isValid( self ):
                        
                        return
                        
                    
                    QW.QMessageBox.information( self, 'Information', message )
                    
                    self._test_address_button.setEnabled( True )
                    self._test_address_button.setText( 'test address' )
                    
                
                def do_it():
                    
                    ( host, port ) = credentials.GetAddress()
                    
                    url = scheme + host + ':' + str( port ) + '/' + request
                    
                    if self._service_type == HC.IPFS:
                        
                        network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
                        
                    else:
                        
                        network_job = ClientNetworkingJobs.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
                        
                    
                    network_job.OnlyTryConnectionOnce()
                    network_job.OverrideBandwidth()
                    
                    network_job.SetForLogin( True )
                    
                    HG.client_controller.network_engine.AddJob( network_job )
                    
                    try:
                        
                        network_job.WaitUntilDone()
                        
                        QP.CallAfter( qt_done, 'Looks good!' )
                        
                    except HydrusExceptions.NetworkException as e:
                        
                        QP.CallAfter( qt_done, 'Problem with that address: ' + str(e) )
                        
                    
                
                try:
                    
                    credentials = self.GetCredentials()
                    
                except HydrusExceptions.VetoException as e:
                    
                    message = str( e )
                    
                    if len( message ) > 0:
                        
                        QW.QMessageBox.critical( self, 'Error', message )
                        
                    
                    return
                    
                
                if self._service_type == HC.IPFS:
                    
                    scheme = 'http://'
                    request = 'api/v0/version'
                    
                else:
                    
                    scheme = 'https://'
                    request = ''
                    
                
                self._test_address_button.setEnabled( False )
                self._test_address_button.setText( 'testing\u2026' )
                
                HG.client_controller.CallToThread( do_it )
                
            
            def GetCredentials( self ):
                
                host = self._host.text()
                
                if host == '':
                    
                    raise HydrusExceptions.VetoException( 'Please enter a host!' )
                    
                
                port = self._port.value()
                
                return HydrusNetwork.Credentials( host, port )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                credentials = self.GetCredentials()
                
                dictionary_part[ 'credentials' ] = credentials
                
                return dictionary_part
                
            
        
        class _ServiceRestrictedPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, service_key, remote_panel, service_type, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'hydrus network' )
                
                self._service_key = service_key
                self._remote_panel = remote_panel
                self._service_type = service_type
                
                self._original_credentials = dictionary[ 'credentials' ]
                
                self._access_key = QW.QLineEdit( self )
                
                self._test_credentials_button = ClientGUICommon.BetterButton( self, 'test access key', self._TestCredentials )
                self._register = ClientGUICommon.BetterButton( self, 'fetch an access key with a registration key', self._GetAccessKeyFromRegistrationKey )
                
                #
                
                if self._original_credentials.HasAccessKey():
                    
                    self._access_key.setText( self._original_credentials.GetAccessKey().hex() )
                    
                
                #
                
                hbox = QP.HBoxLayout()
                
                QP.AddToLayout( hbox, self._register, CC.FLAGS_CENTER_PERPENDICULAR )
                QP.AddToLayout( hbox, self._test_credentials_button, CC.FLAGS_CENTER_PERPENDICULAR )
                
                wrapped_access_key = ClientGUICommon.WrapInText( self._access_key, self, 'access key: ' )
                
                self.Add( wrapped_access_key, CC.FLAGS_EXPAND_PERPENDICULAR )
                self.Add( hbox, CC.FLAGS_ON_RIGHT )
                
            
            def _GetAccessKeyFromRegistrationKey( self ):
                
                def qt_done():
                    
                    if not self or not QP.isValid( self ):
                        
                        return
                        
                    
                    self._register.setEnabled( True )
                    self._register.setText( 'fetch an access key with a registration key' )
                    
                
                def qt_setkey( access_key_encoded ):
                    
                    if not self or not QP.isValid( self ):
                        
                        return
                        
                    
                    self._access_key.setText( access_key_encoded )
                    
                    QW.QMessageBox.information( self, 'Information', 'Looks good!' )
                    
                
                def do_it( credentials, registration_key ):
                    
                    try:
                        
                        ( host, port ) = credentials.GetAddress()
                        
                        url = 'https://' + host + ':' + str( port ) + '/access_key?registration_key=' + registration_key.hex()
                        
                        network_job = ClientNetworkingJobs.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
                        
                        network_job.OnlyTryConnectionOnce()
                        network_job.OverrideBandwidth()
                        
                        network_job.SetForLogin( True )
                        
                        HG.client_controller.network_engine.AddJob( network_job )
                        
                        try:
                            
                            network_job.WaitUntilDone()
                            
                            network_bytes = network_job.GetContentBytes()
                            
                            parsed_request_args = HydrusNetwork.ParseNetworkBytesToParsedHydrusArgs( network_bytes )
                            
                            access_key_encoded = parsed_request_args[ 'access_key' ].hex()
                            
                            QP.CallAfter( qt_setkey, access_key_encoded )
                            
                        except Exception as e:
                            
                            HydrusData.PrintException( e )
                            
                            QP.CallAfter( QW.QMessageBox.critical, None, 'Error', 'Had a problem: '+str(e) )
                            
                        
                    finally:
                        
                        QP.CallAfter( qt_done )
                        
                    
                
                try:
                    
                    credentials = self._remote_panel.GetCredentials()
                    
                except HydrusExceptions.VetoException as e:
                    
                    message = str( e )
                    
                    if len( message ) > 0:
                        
                        QW.QMessageBox.critical( self, 'Error', message )
                        
                    
                    return
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter the registration key.' ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        registration_key_encoded = dlg.GetValue()
                        
                    else:
                        
                        return
                        
                    
                
                if registration_key_encoded[0] == 'r':
                    
                    registration_key_encoded = registration_key_encoded[1:]
                    
                
                if registration_key_encoded == 'init':
                    
                    registration_key = b'init'
                    
                else:
                    
                    try:
                        
                        registration_key = bytes.fromhex( registration_key_encoded )
                        
                    except:
                        
                        QW.QMessageBox.critical( self, 'Error', 'Could not parse that registration key!' )
                        
                        return
                        
                    
                
                self._register.setEnabled( False )
                self._register.setText( 'fetching\u2026' )
                
                HG.client_controller.CallToThread( do_it, credentials, registration_key )
                
            
            def _TestCredentials( self ):
                
                def qt_done( message ):
                    
                    if not self or not QP.isValid( self ):
                        
                        return
                        
                    
                    QW.QMessageBox.information( self, 'Information', message )
                    
                    self._test_credentials_button.setEnabled( True )
                    self._test_credentials_button.setText( 'test access key' )
                    
                    
                
                def do_it( credentials, service_type ):
                    
                    service = ClientServices.GenerateService( CC.TEST_SERVICE_KEY, service_type, 'test service' )
                    
                    service.SetCredentials( credentials )
                    
                    try:
                        
                        response = service.Request( HC.GET, 'access_key_verification' )
                        
                        if not response[ 'verified' ]:
                            
                            message = 'That access key was not recognised!'
                            
                        else:
                            
                            message = 'Everything looks ok!'
                            
                        
                    except HydrusExceptions.WrongServiceTypeException:
                        
                        message = 'Connection was made, but the service was not a {}.'.format( HC.service_string_lookup[ service_type ] )
                        
                    except HydrusExceptions.NetworkException as e:
                        
                        message = 'Network problem: {}'.format( e )
                        
                    except Exception as e:
                        
                        message = 'Unexpected error: {}'.format( e )
                        
                    finally:
                        
                        QP.CallAfter( qt_done, message )
                        
                    
                
                try:
                    
                    credentials = self.GetCredentials()
                    
                except HydrusExceptions.VetoException as e:
                    
                    message = str( e )
                    
                    if len( message ) > 0:
                        
                        QW.QMessageBox.critical( self, 'Error', message )
                        
                    
                    return
                    
                
                self._test_credentials_button.setEnabled( False )
                self._test_credentials_button.setText( 'fetching\u2026' )
                
                HG.client_controller.CallToThread( do_it, credentials, self._service_type )
                
            
            def GetCredentials( self ):
                
                credentials = self._remote_panel.GetCredentials()
                
                try:
                    
                    access_key = bytes.fromhex( self._access_key.text() )
                    
                except:
                    
                    raise HydrusExceptions.VetoException( 'Could not understand that access key!')
                    
                
                if len( access_key ) > 0:
                    
                    credentials.SetAccessKey( access_key )
                    
                
                return credentials
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                credentials = self.GetCredentials()
                
                if credentials != self._original_credentials:
                    
                    account = HydrusNetwork.Account.GenerateUnknownAccount()
                    
                    dictionary_part[ 'account' ] = HydrusNetwork.Account.GenerateSerialisableTupleFromAccount( account )
                    
                    network_context = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key )
                    
                    HG.client_controller.network_engine.session_manager.ClearSession( network_context )
                    
                
                dictionary_part[ 'credentials' ] = credentials
                
                return dictionary_part
                
            
        
        class _ServiceClientServerPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, service_type, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'client api' )
                
                self._client_server_options_panel = ClientGUICommon.StaticBox( self, 'options' )
                
                if service_type == HC.LOCAL_BOORU:
                    
                    name = 'local booru'
                    default_port = 45868
                    
                elif service_type == HC.CLIENT_API_SERVICE:
                    
                    name = 'client api'
                    default_port = 45869
                    
                
                port_name = '{} local port'.format( name )
                none_phrase = 'do not run {} service'.format( name )
                
                self._port = ClientGUICommon.NoneableSpinCtrl( self._client_server_options_panel, port_name, none_phrase = none_phrase, min = 1, max = 65535 )
                
                self._allow_non_local_connections = QW.QCheckBox( 'allow non-local connections', self._client_server_options_panel )
                self._allow_non_local_connections.setToolTip( 'Allow other computers on the network to talk to use service. If unchecked, only localhost can talk to it.' )
                
                self._use_https = QW.QCheckBox( 'use https', self._client_server_options_panel )
                self._use_https.setToolTip( 'Host the server using https instead of http. This uses a self-signed certificate, stored in your db folder, which is imperfect but better than straight http. Your software (e.g. web browser testing the Client API welcome page) may need to go through a manual \'approve this ssl certificate\' process before it can work. If you host your client on a real DNS domain and acquire your own signed certificate, you can replace the cert+key file pair with that.' )
                
                self._support_cors = QW.QCheckBox( 'support CORS headers', self._client_server_options_panel )
                self._support_cors.setToolTip( 'Have this server support Cross-Origin Resource Sharing, which allows web browsers to access it off other domains. Turn this on if you want to access this service through a web-based wrapper (e.g. a booru wrapper) hosted on another domain.' )
                
                self._log_requests = QW.QCheckBox( 'log requests', self._client_server_options_panel )
                self._log_requests.setToolTip( 'Hydrus server services will write a brief anonymous line to the log for every request made, but for the client services this tends to be a bit spammy. You probably want this off unless you are testing something.' )
                
                self._upnp = ClientGUICommon.NoneableSpinCtrl( self._client_server_options_panel, 'upnp port', none_phrase = 'do not forward port', max = 65535 )
                
                self._external_scheme_override = ClientGUICommon.NoneableTextCtrl( self._client_server_options_panel, message = 'scheme (http/https) override when copying external links' )
                self._external_host_override = ClientGUICommon.NoneableTextCtrl( self._client_server_options_panel, message = 'host override when copying external links' )
                self._external_port_override = ClientGUICommon.NoneableTextCtrl( self._client_server_options_panel, message = 'port override when copying external links' )
                
                self._external_port_override.setToolTip( 'Setting this to a non-none empty string will forego the \':\' in the URL.' )
                
                if service_type != HC.LOCAL_BOORU:
                    
                    self._external_scheme_override.hide()
                    self._external_host_override.hide()
                    self._external_port_override.hide()
                    
                
                self._bandwidth_rules = ClientGUIControls.BandwidthRulesCtrl( self._client_server_options_panel, dictionary[ 'bandwidth_rules' ] )
                
                #
                
                self._port.SetValue( default_port )
                self._upnp.SetValue( default_port )
                
                self._port.SetValue( dictionary[ 'port' ] )
                self._upnp.SetValue( dictionary[ 'upnp_port' ] )
                
                self._allow_non_local_connections.setChecked( dictionary[ 'allow_non_local_connections' ] )
                self._use_https.setChecked( dictionary[ 'use_https' ] )
                self._support_cors.setChecked( dictionary[ 'support_cors' ] )
                self._log_requests.setChecked( dictionary[ 'log_requests' ] )
                
                self._external_scheme_override.SetValue( dictionary[ 'external_scheme_override' ] )
                self._external_host_override.SetValue( dictionary[ 'external_host_override' ] )
                self._external_port_override.SetValue( dictionary[ 'external_port_override' ] )
                
                #
                
                self._client_server_options_panel.Add( self._port, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._client_server_options_panel.Add( self._allow_non_local_connections, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._client_server_options_panel.Add( self._use_https, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._client_server_options_panel.Add( self._support_cors, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._client_server_options_panel.Add( self._log_requests, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._client_server_options_panel.Add( self._upnp, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._client_server_options_panel.Add( self._external_scheme_override, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._client_server_options_panel.Add( self._external_host_override, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._client_server_options_panel.Add( self._external_port_override, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._client_server_options_panel.Add( self._bandwidth_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self.Add( self._client_server_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._allow_non_local_connections.clicked.connect( self._UpdateControls )
                
            
            def _UpdateControls( self ):
                
                if self._allow_non_local_connections.isChecked():
                    
                    self._upnp.SetValue( None )
                    
                    self._upnp.setEnabled( False )
                    
                else:
                    
                    self._upnp.setEnabled( True )
                    
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                dictionary_part[ 'port' ] = self._port.GetValue()
                dictionary_part[ 'upnp_port' ] = self._upnp.GetValue()
                dictionary_part[ 'allow_non_local_connections' ] = self._allow_non_local_connections.isChecked()
                dictionary_part[ 'use_https' ] = self._use_https.isChecked()
                dictionary_part[ 'support_cors' ] = self._support_cors.isChecked()
                dictionary_part[ 'log_requests' ] = self._log_requests.isChecked()
                dictionary_part[ 'external_scheme_override' ] = self._external_scheme_override.GetValue()
                dictionary_part[ 'external_host_override' ] = self._external_host_override.GetValue()
                dictionary_part[ 'external_port_override' ] = self._external_port_override.GetValue()
                dictionary_part[ 'bandwidth_rules' ] = self._bandwidth_rules.GetValue()
                
                return dictionary_part
                
            
        
        class _ServiceTagPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'tags' )
                
                self._st = ClientGUICommon.BetterStaticText( self )
                
                self._st.setText( 'This is a tag service. There are no additional options for it at present.' )
                
                #
                
                self.Add( self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                return dictionary_part
                
            
        
        class _ServiceRatingsPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'ratings' )
                
                self._shape = ClientGUICommon.BetterChoice( self )
                
                self._shape.addItem( 'circle', ClientRatings.CIRCLE )
                self._shape.addItem( 'square', ClientRatings.SQUARE )
                self._shape.addItem( 'star', ClientRatings.STAR )
                
                self._colour_ctrls = {}
                
                for colour_type in [ ClientRatings.LIKE, ClientRatings.DISLIKE, ClientRatings.NULL, ClientRatings.MIXED ]:
                    
                    border_ctrl = ClientGUICommon.BetterColourControl( self )
                    fill_ctrl = ClientGUICommon.BetterColourControl( self )
                    
                    border_ctrl.setMaximumWidth( 20 )
                    fill_ctrl.setMaximumWidth( 20 )
                    
                    self._colour_ctrls[ colour_type ] = ( border_ctrl, fill_ctrl )
                    
                
                #
                
                self._shape.SetValue( dictionary[ 'shape' ] )
                
                for ( colour_type, ( border_rgb, fill_rgb ) ) in dictionary[ 'colours' ]:
                    
                    ( border_ctrl, fill_ctrl ) = self._colour_ctrls[ colour_type ]
                    
                    border_ctrl.SetColour( QG.QColor( *border_rgb ) )
                    fill_ctrl.SetColour( QG.QColor( *fill_rgb ) )
                    
                
                #
                
                rows = []
                
                rows.append( ( 'shape: ', self._shape ) )
                
                for colour_type in [ ClientRatings.LIKE, ClientRatings.DISLIKE, ClientRatings.NULL, ClientRatings.MIXED ]:
                    
                    ( border_ctrl, fill_ctrl ) = self._colour_ctrls[ colour_type ]
                    
                    hbox = QP.HBoxLayout()
                    
                    QP.AddToLayout( hbox, border_ctrl, CC.FLAGS_CENTER_PERPENDICULAR )
                    QP.AddToLayout( hbox, fill_ctrl, CC.FLAGS_CENTER_PERPENDICULAR )
                    
                    if colour_type == ClientRatings.LIKE: colour_text = 'liked'
                    elif colour_type == ClientRatings.DISLIKE: colour_text = 'disliked'
                    elif colour_type == ClientRatings.NULL: colour_text = 'not rated'
                    elif colour_type == ClientRatings.MIXED: colour_text = 'a mixture of ratings'
                    
                    rows.append( ( 'border/fill for ' + colour_text + ': ', hbox ) )
                    
                
                gridbox = ClientGUICommon.WrapInGrid( self, rows )
                
                self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                dictionary_part[ 'shape' ] = self._shape.GetValue()
                
                dictionary_part[ 'colours' ] = {}
                
                for ( colour_type, ( border_ctrl, fill_ctrl ) ) in list(self._colour_ctrls.items()):
                    
                    border_colour = border_ctrl.GetColour()
                    
                    border_rgb = ( border_colour.red(), border_colour.green(), border_colour.blue() )
                    
                    fill_colour = fill_ctrl.GetColour()
                    
                    fill_rgb = ( fill_colour.red(), fill_colour.green(), fill_colour.blue() )
                    
                    dictionary_part[ 'colours' ][ colour_type ] = ( border_rgb, fill_rgb )
                    
                
                return dictionary_part
                
            
        
        class _ServiceRatingsNumericalPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'numerical ratings' )
                
                self._num_stars = QP.MakeQSpinBox( self, min=1, max=20 )
                self._allow_zero = QW.QCheckBox( self )
                
                #
                
                self._num_stars.setValue( dictionary['num_stars'] )
                self._allow_zero.setChecked( dictionary[ 'allow_zero' ] )
                
                #
                
                rows = []
                
                rows.append( ( 'number of \'stars\': ', self._num_stars ) )
                rows.append( ( 'allow a zero rating: ', self._allow_zero ) )
                
                gridbox = ClientGUICommon.WrapInGrid( self, rows )
                
                self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                num_stars = self._num_stars.value()
                allow_zero = self._allow_zero.isChecked()
                
                if num_stars == 1 and not allow_zero:
                    
                    allow_zero = True
                    
                
                dictionary_part[ 'num_stars' ] = num_stars
                dictionary_part[ 'allow_zero' ] = allow_zero
                
                return dictionary_part
                
            
        
        class _ServiceIPFSPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'ipfs' )
                
                interaction_panel = ClientGUIPanels.IPFSDaemonStatusAndInteractionPanel( self, self.parentWidget().GetValue )
                
                tts = 'This is an *experimental* IPFS filestore that will not copy files when they are pinned. IPFS will refer to files using their original location (i.e. your hydrus client\'s file folder(s)).'
                tts += os.linesep * 2
                tts += 'Only turn this on if you know what it is.'
                
                self._use_nocopy = QW.QCheckBox( self )
                
                self._use_nocopy.setToolTip( tts )
                
                portable_initial_dict = dict( dictionary[ 'nocopy_abs_path_translations' ] )
                
                abs_initial_dict = {}
                
                current_file_locations = HG.client_controller.client_files_manager.GetCurrentFileLocations()
                
                for ( portable_hydrus_path, ipfs_path ) in portable_initial_dict.items():
                    
                    hydrus_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_hydrus_path )
                    
                    if hydrus_path in current_file_locations:
                        
                        abs_initial_dict[ hydrus_path ] = ipfs_path
                        
                    
                
                for hydrus_path in current_file_locations:
                    
                    if hydrus_path not in abs_initial_dict:
                        
                        abs_initial_dict[ hydrus_path ] = ''
                        
                    
                
                help_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().help, self._ShowHelp )
                
                help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help for this path remapping control -->', QG.QColor( 0, 0, 255 ) )
                
                self._nocopy_abs_path_translations = ClientGUIStringControls.StringToStringDictControl( self, abs_initial_dict, key_name = 'hydrus path', value_name = 'ipfs path', allow_add_delete = False, edit_keys = False )
                
                self._multihash_prefix = QW.QLineEdit( self )
                
                tts = 'When you tell the client to copy a ipfs multihash to your clipboard, it will prefix it with whatever is set here.'
                tts += os.linesep * 2
                tts += 'Use this if you want to copy a full gateway url. For instance, you could put here:'
                tts += os.linesep * 2
                tts += 'http://127.0.0.1:8080/ipfs/'
                tts += os.linesep
                tts += '-or-'
                tts += os.linesep
                tts += 'http://ipfs.io/ipfs/'
                
                self._multihash_prefix.setToolTip( tts )
                
                #
                
                self._use_nocopy.setChecked( dictionary[ 'use_nocopy' ] )
                self._multihash_prefix.setText( dictionary[ 'multihash_prefix' ] )
                
                #
                
                rows = []
                
                rows.append( ( 'clipboard multihash url prefix: ', self._multihash_prefix ) )
                rows.append( ( 'use \'nocopy\' filestore for pinning: ', self._use_nocopy ) )
                
                gridbox = ClientGUICommon.WrapInGrid( self, rows )
                
                self.Add( interaction_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self.Add( help_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                self.Add( self._nocopy_abs_path_translations, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self._UpdateButtons()
                
                self._use_nocopy.clicked.connect( self._UpdateButtons )
                
            
            def _ShowHelp( self ):
                
                message = '\'nocopy\' is experimental and advanced!'
                message += os.linesep * 2
                message += 'In order to add a file through \'nocopy\', IPFS needs to be given a path that is beneath the directory in which its datastore is. Usually this is your USERDIR (default IPFS location is ~/.ipfs). Also, if your IPFS daemon runs on another computer, that path needs to be according to that machine\'s filesystem (and, perhaps, pointing to a shared folder that can stores your hydrus files).'
                message += os.linesep * 2
                message += 'If your hydrus client_files directory is not already in your USERDIR, you will need to make some symlinks and then put these paths in the control so hydrus knows how to translate the paths when it pins.'
                message += os.linesep * 2
                message += 'e.g. If you symlink E:\\hydrus\\files to C:\\users\\you\\ipfs_maps\\e_media, then put that same C:\\users\\you\\ipfs_maps\\e_media in the right column for that hydrus file location, and you _should_ be good.'
                
                QW.QMessageBox.information( self, 'Information', message )
                
            
            def _UpdateButtons( self ):
                
                if self._use_nocopy.isChecked():
                    
                    self._nocopy_abs_path_translations.setEnabled( True )
                    
                else:
                    
                    self._nocopy_abs_path_translations.setEnabled( False )
                    
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                dictionary_part[ 'use_nocopy' ] = self._use_nocopy.isChecked()
                
                abs_dict = self._nocopy_abs_path_translations.GetValue()
                
                portable_dict = {}
                
                for ( hydrus_path, ipfs_path ) in abs_dict.items():
                    
                    portable_hydrus_path = HydrusPaths.ConvertAbsPathToPortablePath( hydrus_path )
                    
                    portable_dict[ portable_hydrus_path ] = ipfs_path
                    
                
                dictionary_part[ 'nocopy_abs_path_translations' ] = portable_dict
                
                dictionary_part[ 'multihash_prefix' ] = self._multihash_prefix.text()
                
                return dictionary_part
                
            
        
    
class ManageServerServicesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, service_key ):
        
        self._clientside_admin_service = HG.client_controller.services_manager.GetService( service_key )
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._deletee_service_keys = []
        
        self._services_listctrl = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_SERVICES.ID, 20, data_to_tuples_func = self._ConvertServiceToTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'tag repository', 'Create a new tag repository.', self._AddTagRepository ) )
        menu_items.append( ( 'normal', 'file repository', 'Create a new file repository.', self._AddFileRepository ) )
        
        self._add_button = ClientGUICommon.MenuButton( self, 'add', menu_items )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        #
        
        response = self._clientside_admin_service.Request( HC.GET, 'services' )
        
        serverside_services = response[ 'services' ]
        
        self._services_listctrl.AddDatas( serverside_services )
        
        #self._services_listctrl.SortListItems( 0 )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._add_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._edit_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._services_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        self.widget().setLayout( vbox )
        
    
    def _ConvertServiceToTuples( self, service ):
        
        port = service.GetPort()
        name = service.GetName()
        service_type = service.GetServiceType()
        
        pretty_port = str( port )
        pretty_name = name
        pretty_service_type = HC.service_string_lookup[ service_type ]
        
        return ( ( pretty_port, pretty_name, pretty_service_type ), ( port, name, service_type ) )
        
    
    def _Add( self, service_type ):
        
        service_key = HydrusData.GenerateKey()
        
        port = self._GetNextPort()
        
        name = 'new service'
        
        dictionary = HydrusNetwork.GenerateDefaultServiceDictionary( service_type )
        
        service = HydrusNetwork.GenerateService( service_key, service_type, name, port, dictionary )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit serverside service' ) as dlg_edit:
            
            panel = EditServersideService( dlg_edit, service )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.exec() == QW.QDialog.Accepted:
                
                new_service = panel.GetValue()
                
                self._services_listctrl.SetNonDupeName( new_service )
                
                self._SetNonDupePort( new_service )
                
                self._services_listctrl.AddDatas( ( new_service, ) )
                
            
        
    
    def _AddFileRepository( self ):
        
        self._Add( HC.FILE_REPOSITORY )
        
    
    def _AddTagRepository( self ):
        
        self._Add( HC.TAG_REPOSITORY )
        
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            for service in self._services_listctrl.GetData( only_selected = True ):
                
                self._deletee_service_keys.append( service.GetServiceKey() )
                
            
            self._services_listctrl.DeleteSelected()
            
        
    
    def _Edit( self ):
        
        for service in self._services_listctrl.GetData( only_selected = True ):
            
            original_name = service.GetName()
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit serverside service' ) as dlg_edit:
                
                panel = EditServersideService( dlg_edit, service )
                
                dlg_edit.SetPanel( panel )
                
                result = dlg_edit.exec()
                
                if result == QW.QDialog.Accepted:
                    
                    edited_service = panel.GetValue()
                    
                    if edited_service.GetName() != original_name:
                        
                        self._services_listctrl.SetNonDupeName( edited_service )
                        
                    
                    self._SetNonDupePort( edited_service )
                    
                    self._services_listctrl.ReplaceData( service, edited_service )
                    
                elif dlg_edit.WasCancelled():
                    
                    break
                    
                
            
        
    
    def _GetNextPort( self ):
        
        existing_ports = [ service.GetPort() for service in self._services_listctrl.GetData() ]
        
        largest_port = max( existing_ports )
        
        next_port = largest_port
        
        while next_port in existing_ports:
            
            next_port = max( 1, ( next_port + 1 ) % 65536 )
            
        
        return next_port
        
    
    def _SetNonDupePort( self, new_service ):
        
        existing_ports = [ service.GetPort() for service in self._services_listctrl.GetData() if service.GetServiceKey() != new_service.GetServiceKey() ]
        
        new_port = new_service.GetPort()
        
        if new_port in existing_ports:
            
            next_port = self._GetNextPort()
            
            new_service.SetPort( next_port )
            
        
    
    def CheckValid( self ):
        
        services = self._services_listctrl.GetData()
        
        unique_ports = { service.GetPort() for service in services }
        
        if len( unique_ports ) < len( services ):
            
            raise HydrusExceptions.VetoException( 'It looks like some of those services share ports! Please give them unique ports!' )
            
        
    
    def CommitChanges( self ):
        
        services = self._services_listctrl.GetData()
        
        try:
            
            response = self._clientside_admin_service.Request( HC.POST, 'services', { 'services' : services } )
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
            raise HydrusExceptions.VetoException( 'There was an error: {}'.format( str( e ) ) )
            
        
        service_keys_to_access_keys = dict( response[ 'service_keys_to_access_keys' ] )
        
        admin_service_key = self._clientside_admin_service.GetServiceKey()
        
        with HG.dirty_object_lock:
            
            HG.client_controller.WriteSynchronous( 'update_server_services', admin_service_key, services, service_keys_to_access_keys, self._deletee_service_keys )
            
            HG.client_controller.RefreshServices()
            
        
    
class ReviewServicesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._notebook = ClientGUICommon.BetterNotebook( self )
        
        self._local_notebook = ClientGUICommon.BetterNotebook( self._notebook )
        self._remote_notebook = ClientGUICommon.BetterNotebook( self._notebook )
        
        self._notebook.addTab( self._local_notebook, 'local' )
        self._notebook.addTab( self._remote_notebook, 'remote' )
        
        self._InitialiseServices()
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_gui' )
        
    
    def _InitialiseServices( self ):
        
        lb = self._notebook.currentWidget()
        
        if lb.count() == 0:
            
            previous_service_key = CC.LOCAL_FILE_SERVICE_KEY
            
        else:
            
            page = lb.currentWidget().currentWidget()
            
            previous_service_key = page.GetServiceKey()
            
        
        QP.DeleteAllNotebookPages( self._local_notebook )
        QP.DeleteAllNotebookPages( self._remote_notebook )
        
        notebook_dict = {}
        
        services = self._controller.services_manager.GetServices()
        
        for service in services:
            
            service_type = service.GetServiceType()
            
            if service_type in HC.LOCAL_SERVICES: parent_notebook = self._local_notebook
            else: parent_notebook = self._remote_notebook
            
            if service_type == HC.TAG_REPOSITORY: service_type_name = 'tag repositories'
            elif service_type == HC.FILE_REPOSITORY: service_type_name = 'file repositories'
            elif service_type == HC.MESSAGE_DEPOT: service_type_name = 'message depots'
            elif service_type == HC.SERVER_ADMIN: service_type_name = 'administrative servers'
            elif service_type in HC.LOCAL_FILE_SERVICES: service_type_name = 'files'
            elif service_type == HC.LOCAL_TAG: service_type_name = 'tags'
            elif service_type == HC.LOCAL_RATING_LIKE: service_type_name = 'like/dislike ratings'
            elif service_type == HC.LOCAL_RATING_NUMERICAL: service_type_name = 'numerical ratings'
            elif service_type == HC.LOCAL_BOORU: service_type_name = 'booru'
            elif service_type == HC.CLIENT_API_SERVICE: service_type_name = 'client api'
            elif service_type == HC.IPFS: service_type_name = 'ipfs'
            else: continue
            
            if service_type_name not in notebook_dict:
                
                services_notebook = ClientGUICommon.BetterNotebook( parent_notebook )
                
                notebook_dict[ service_type_name ] = services_notebook
                
                parent_notebook.addTab( services_notebook, service_type_name )
                
            
            services_notebook = notebook_dict[ service_type_name ]
            
            page = ClientGUIPanels.ReviewServicePanel( services_notebook, service )
            
            if service.GetServiceKey() == previous_service_key:
                
                self._notebook.SelectPage( parent_notebook )
                parent_notebook.SelectPage( services_notebook )
                
                select = True
                
            else:
                
                select = False
                
            
            name = service.GetName()
            
            services_notebook.addTab( page, name )
            if select: services_notebook.setCurrentIndex( services_notebook.count() - 1 )
            
        
    
    def RefreshServices( self ):
        
        self._InitialiseServices()
        
    
