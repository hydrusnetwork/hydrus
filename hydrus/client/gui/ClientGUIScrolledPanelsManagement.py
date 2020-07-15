import collections
import os
import random
import re
import traceback
import urllib.parse

from qtpy import QtCore as QC
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
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.client import ClientApplicationCommand as CAC
from hydrus.client import ClientConstants as CC
from hydrus.client.media import ClientMedia
from hydrus.client import ClientRatings
from hydrus.client import ClientServices
from hydrus.client.gui import ClientGUIACDropdown
from hydrus.client.gui import ClientGUICommon
from hydrus.client.gui import ClientGUIControls
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIImport
from hydrus.client.gui import ClientGUIPanels
from hydrus.client.gui import ClientGUISearch
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUIStyle
from hydrus.client.gui import ClientGUITime
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingJobs
from hydrus.client.networking import ClientNetworkingSessions

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
        
        QP.AddToLayout( hbox, self._add_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._edit_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._delete_button, CC.FLAGS_VCENTER )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._account_types_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_BUTTON_SIZER )
        
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
            
            account_types_can_move_to = list( all_account_types - account_types_about_to_delete )
            
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
            
            return len( keys.intersection( values ) ) > 0
            
        
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
        
        QP.AddToLayout( add_remove_hbox, self._add_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( add_remove_hbox, self._edit_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( add_remove_hbox, self._delete_button, CC.FLAGS_VCENTER )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, add_remove_hbox, CC.FLAGS_BUTTON_SIZER )
        
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
            
        
        return ( ( pretty_service_type, name, pretty_deletable ), ( pretty_service_type, name, deletable ) )
        
    
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
                    
                    with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'select namespaces' ) as dlg:
                        
                        panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
                        
                        dlg.SetPanel( panel )
                        
                        if dlg.exec() == QW.QDialog.Accepted:
                            
                            namespaces = panel.GetValue()
                            
                        else:
                            
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
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'select namespaces' ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        namespaces = panel.GetValue()
                        
                    else:
                        
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
                QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText(self,':'), CC.FLAGS_VCENTER )
                QP.AddToLayout( hbox, self._port, CC.FLAGS_VCENTER )
                
                wrapped_hbox = ClientGUICommon.WrapInText( hbox, self, 'address: ' )
                
                self.Add( wrapped_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                self.Add( self._test_address_button, CC.FLAGS_LONE_BUTTON )
                
            
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
                
                QP.AddToLayout( hbox, self._register, CC.FLAGS_VCENTER )
                QP.AddToLayout( hbox, self._test_credentials_button, CC.FLAGS_VCENTER )
                
                wrapped_access_key = ClientGUICommon.WrapInText( self._access_key, self, 'access key: ' )
                
                self.Add( wrapped_access_key, CC.FLAGS_EXPAND_PERPENDICULAR )
                self.Add( hbox, CC.FLAGS_BUTTON_SIZER )
                
            
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
                    
                    QP.AddToLayout( hbox, border_ctrl, CC.FLAGS_VCENTER )
                    QP.AddToLayout( hbox, fill_ctrl, CC.FLAGS_VCENTER )
                    
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
                
            
        
    
class ManageOptionsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._new_options = HG.client_controller.new_options
        
        self._listbook = ClientGUICommon.ListBook( self )
        
        self._listbook.AddPage( 'gui', 'gui', self._GUIPanel( self._listbook ) ) # leave this at the top, to make it default page
        self._listbook.AddPage( 'gui pages', 'gui pages', self._GUIPagesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'connection', 'connection', self._ConnectionPanel( self._listbook ) )
        self._listbook.AddPage( 'external programs', 'external programs', self._ExternalProgramsPanel( self._listbook ) )
        self._listbook.AddPage( 'files and trash', 'files and trash', self._FilesAndTrashPanel( self._listbook ) )
        self._listbook.AddPage( 'file viewing statistics', 'file viewing statistics', self._FileViewingStatisticsPanel( self._listbook ) )
        self._listbook.AddPage( 'speed and memory', 'speed and memory', self._SpeedAndMemoryPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'maintenance and processing', 'maintenance and processing', self._MaintenanceAndProcessingPanel( self._listbook ) )
        self._listbook.AddPage( 'media', 'media', self._MediaPanel( self._listbook ) )
        self._listbook.AddPage( 'audio', 'audio', self._AudioPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'system tray', 'system tray', self._SystemTrayPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'default system predicates', 'default system predicates', self._DefaultFileSystemPredicatesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'colours', 'colours', self._ColoursPanel( self._listbook ) )
        self._listbook.AddPage( 'regex favourites', 'regex favourites', self._RegexPanel( self._listbook ) )
        self._listbook.AddPage( 'sort/collect', 'sort/collect', self._SortCollectPanel( self._listbook ) )
        self._listbook.AddPage( 'downloading', 'downloading', self._DownloadingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'duplicates', 'duplicates', self._DuplicatesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'importing', 'importing', self._ImportingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'style', 'style', self._StylePanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag presentation', 'tag presentation', self._TagPresentationPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag suggestions', 'tag suggestions', self._TagSuggestionsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tags', 'tags', self._TagsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'thumbnails', 'thumbnails', self._ThumbnailsPanel( self._listbook, self._new_options ) )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
    
    class _AudioPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #self._media_viewer_uses_its_own_audio_volume = QW.QCheckBox( self )
            self._preview_uses_its_own_audio_volume = QW.QCheckBox( self )
            
            self._has_audio_label = QW.QLineEdit( self )
            
            #
            
            tt = 'If unchecked, this media canvas will use the \'global\' audio volume slider. If checked, this media canvas will have its own separate one.'
            tt += os.linesep * 2
            tt += 'Keep this on if you would like the preview viewer to be quieter than the main media viewer.'
            
            #self._media_viewer_uses_its_own_audio_volume.setChecked( self._new_options.GetBoolean( 'media_viewer_uses_its_own_audio_volume' ) )
            self._preview_uses_its_own_audio_volume.setChecked( self._new_options.GetBoolean( 'preview_uses_its_own_audio_volume' ) )
            
            #self._media_viewer_uses_its_own_audio_volume.setToolTip( tt )
            self._preview_uses_its_own_audio_volume.setToolTip( tt )
            
            self._has_audio_label.setText( self._new_options.GetString( 'has_audio_label' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'The preview window has its own volume: ', self._preview_uses_its_own_audio_volume ) )
            #rows.append( ( 'The media viewer has its own volume: ', self._media_viewer_uses_its_own_audio_volume ) )
            rows.append( ( 'Label for files with audio: ', self._has_audio_label ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            #self._new_options.SetBoolean( 'media_viewer_uses_its_own_audio_volume', self._media_viewer_uses_its_own_audio_volume.isChecked() )
            self._new_options.SetBoolean( 'preview_uses_its_own_audio_volume', self._preview_uses_its_own_audio_volume.isChecked() )
            
            self._new_options.SetString( 'has_audio_label', self._has_audio_label.text() )
            
        
    
    class _ColoursPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            coloursets_panel = ClientGUICommon.StaticBox( self, 'coloursets' )
            
            self._current_colourset = ClientGUICommon.BetterChoice( coloursets_panel )
            
            self._current_colourset.addItem( 'default', 'default' )
            self._current_colourset.addItem( 'darkmode', 'darkmode' )
            
            self._current_colourset.SetValue( self._new_options.GetString( 'current_colourset' ) )
            
            self._notebook = QW.QTabWidget( coloursets_panel )
            
            self._gui_colours = {}
            
            for colourset in ( 'default', 'darkmode' ):
                
                self._gui_colours[ colourset ] = {}
                
                colour_panel = QW.QWidget( self._notebook )
                
                colour_types = []
                
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND )
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND_SELECTED )
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND_REMOTE )
                colour_types.append( CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED )
                colour_types.append( CC.COLOUR_THUMB_BORDER )
                colour_types.append( CC.COLOUR_THUMB_BORDER_SELECTED )
                colour_types.append( CC.COLOUR_THUMB_BORDER_REMOTE )
                colour_types.append( CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED )
                colour_types.append( CC.COLOUR_THUMBGRID_BACKGROUND )
                colour_types.append( CC.COLOUR_AUTOCOMPLETE_BACKGROUND )
                colour_types.append( CC.COLOUR_MEDIA_BACKGROUND )
                colour_types.append( CC.COLOUR_MEDIA_TEXT )
                colour_types.append( CC.COLOUR_TAGS_BOX )
                
                for colour_type in colour_types:
                    
                    ctrl = ClientGUICommon.BetterColourControl( colour_panel )
                    
                    ctrl.setMaximumWidth( 20 )
                    
                    ctrl.SetColour( self._new_options.GetColour( colour_type, colourset ) )
                    
                    self._gui_colours[ colourset ][ colour_type ] = ctrl
                    
                
                #
                
                rows = []
                
                hbox = QP.HBoxLayout()
                
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND], CC.FLAGS_VCENTER )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_SELECTED], CC.FLAGS_VCENTER )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_REMOTE], CC.FLAGS_VCENTER )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED], CC.FLAGS_VCENTER )
                
                rows.append( ( 'thumbnail background (local: normal/selected, remote: normal/selected): ', hbox ) )
                
                hbox = QP.HBoxLayout()
                
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER], CC.FLAGS_VCENTER )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_SELECTED], CC.FLAGS_VCENTER )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_REMOTE], CC.FLAGS_VCENTER )
                QP.AddToLayout( hbox, self._gui_colours[colourset][CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED], CC.FLAGS_VCENTER )
                
                rows.append( ( 'thumbnail border (local: normal/selected, remote: normal/selected): ', hbox ) )
                
                rows.append( ( 'thumbnail grid background: ', self._gui_colours[ colourset ][ CC.COLOUR_THUMBGRID_BACKGROUND ] ) )
                rows.append( ( 'autocomplete background: ', self._gui_colours[ colourset ][ CC.COLOUR_AUTOCOMPLETE_BACKGROUND ] ) )
                rows.append( ( 'media viewer background: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_BACKGROUND ] ) )
                rows.append( ( 'media viewer text: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_TEXT ] ) )
                rows.append( ( 'tags box background: ', self._gui_colours[ colourset ][ CC.COLOUR_TAGS_BOX ] ) )
                
                gridbox = ClientGUICommon.WrapInGrid( colour_panel, rows )
                
                colour_panel.setLayout( gridbox )
                
                select = colourset == 'default'
                
                self._notebook.addTab( colour_panel, colourset )
                if select: self._notebook.setCurrentWidget( colour_panel )
                
            
            #
            
            coloursets_panel.Add( ClientGUICommon.WrapInText( self._current_colourset, coloursets_panel, 'current colourset: ' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            coloursets_panel.Add( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, coloursets_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            for colourset in self._gui_colours:
                
                for ( colour_type, ctrl ) in list(self._gui_colours[ colourset ].items()):
                    
                    colour = ctrl.GetColour()
                    
                    self._new_options.SetColour( colour_type, colourset, colour )
                    
                
            
            self._new_options.SetString( 'current_colourset', self._current_colourset.GetValue() )
            
        
    
    class _ConnectionPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            general = ClientGUICommon.StaticBox( self, 'general' )
            
            self._verify_regular_https = QW.QCheckBox( general )
            
            if self._new_options.GetBoolean( 'advanced_mode' ):
                
                network_timeout_min = 1
                network_timeout_max = 86400 * 30
                
                error_wait_time_min = 1
                error_wait_time_max = 86400 * 30
                
                max_network_jobs_max = 1000
                
                max_network_jobs_per_domain_max = 100
                
            else:
                
                network_timeout_min = 3
                network_timeout_max = 600
                
                error_wait_time_min = 3
                error_wait_time_max = 1800
                
                max_network_jobs_max = 30
                
                max_network_jobs_per_domain_max = 5
                
            
            self._network_timeout = QP.MakeQSpinBox( general, min = network_timeout_min, max = network_timeout_max )
            self._network_timeout.setToolTip( 'If a network connection cannot be made in this duration or, if once started, it experiences uninterrupted inactivity for six times this duration, it will be abandoned.' )
            
            self._connection_error_wait_time = QP.MakeQSpinBox( general, min = error_wait_time_min, max = error_wait_time_max )
            self._connection_error_wait_time.setToolTip( 'If a network connection times out as above, it will wait increasing multiples of this base time before retrying.' )
            
            self._serverside_bandwidth_wait_time = QP.MakeQSpinBox( general, min = error_wait_time_min, max = error_wait_time_max )
            self._serverside_bandwidth_wait_time.setToolTip( 'If a server returns a failure status code indicating it is short on bandwidth, the network job will wait increasing multiples of this base time before retrying.' )
            
            self._domain_network_infrastructure_error_velocity = ClientGUITime.VelocityCtrl( general, 0, 100, 30, hours = True, minutes = True, seconds = True, per_phrase = 'within', unit = 'errors' )
            
            self._max_network_jobs = QP.MakeQSpinBox( general, min = 1, max = max_network_jobs_max )
            self._max_network_jobs_per_domain = QP.MakeQSpinBox( general, min = 1, max = max_network_jobs_per_domain_max )
            
            #
            
            proxy_panel = ClientGUICommon.StaticBox( self, 'proxy settings' )
            
            self._http_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel )
            self._https_proxy = ClientGUICommon.NoneableTextCtrl( proxy_panel )
            
            #
            
            self._verify_regular_https.setChecked( self._new_options.GetBoolean( 'verify_regular_https' ) )
            
            self._http_proxy.SetValue( self._new_options.GetNoneableString( 'http_proxy' ) )
            self._https_proxy.SetValue( self._new_options.GetNoneableString( 'https_proxy' ) )
            
            self._network_timeout.setValue( self._new_options.GetInteger( 'network_timeout' ) )
            self._connection_error_wait_time.setValue( self._new_options.GetInteger( 'connection_error_wait_time' ) )
            self._serverside_bandwidth_wait_time.setValue( self._new_options.GetInteger( 'serverside_bandwidth_wait_time' ) )
            
            number = self._new_options.GetInteger( 'domain_network_infrastructure_error_number' )
            time_delta = self._new_options.GetInteger( 'domain_network_infrastructure_error_time_delta' )
            
            self._domain_network_infrastructure_error_velocity.SetValue( ( number, time_delta ) )
            
            self._max_network_jobs.setValue( self._new_options.GetInteger( 'max_network_jobs' ) )
            self._max_network_jobs_per_domain.setValue( self._new_options.GetInteger( 'max_network_jobs_per_domain' ) )
            
            #
            
            if self._new_options.GetBoolean( 'advanced_mode' ):
                
                label = 'As you are in advanced mode, these options have very low and high limits. Be very careful about lowering delay time or raising max number of connections too far, as things will break.'
                
                st = ClientGUICommon.BetterStaticText( general, label = label )
                st.setObjectName( 'HydrusWarning' )
                
                st.setWordWrap( True )
                
                general.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            rows = []
            
            rows.append( ( 'network timeout (seconds): ', self._network_timeout ) )
            rows.append( ( 'connection error retry wait (seconds): ', self._connection_error_wait_time ) )
            rows.append( ( 'serverside bandwidth retry wait (seconds): ', self._serverside_bandwidth_wait_time ) )
            rows.append( ( 'Halt new jobs as long as this many network infrastructure errors on their domain (0 for never wait): ', self._domain_network_infrastructure_error_velocity ) )
            rows.append( ( 'max number of simultaneous active network jobs: ', self._max_network_jobs ) )
            rows.append( ( 'max number of simultaneous active network jobs per domain: ', self._max_network_jobs_per_domain ) )
            rows.append( ( 'BUGFIX: verify regular https traffic:', self._verify_regular_https ) )
            
            gridbox = ClientGUICommon.WrapInGrid( general, rows )
            
            general.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            text = 'Enter strings such as "http://ip:port" or "http://user:pass@ip:port". It should take affect immediately on dialog ok.'
            text += os.linesep * 2
            
            if ClientNetworkingSessions.SOCKS_PROXY_OK:
                
                text += 'It looks like you have socks support! You should also be able to enter (socks4 or) "socks5://ip:port".'
                text += os.linesep
                text += 'Use socks4a or socks5h to force remote DNS resolution, on the proxy server.'
                
            else:
                
                text += 'It does not look like you have socks support! If you want it, try adding "pysocks" (or "requests[socks]")!'
                
            
            st = ClientGUICommon.BetterStaticText( proxy_panel, text )
            
            st.setWordWrap( True )
            
            proxy_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'http: ', self._http_proxy ) )
            rows.append( ( 'https: ', self._https_proxy ) )
            
            gridbox = ClientGUICommon.WrapInGrid( proxy_panel, rows )
            
            proxy_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, general, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, proxy_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'verify_regular_https', self._verify_regular_https.isChecked() )
            
            self._new_options.SetNoneableString( 'http_proxy', self._http_proxy.GetValue() )
            self._new_options.SetNoneableString( 'https_proxy', self._https_proxy.GetValue() )
            
            self._new_options.SetInteger( 'network_timeout', self._network_timeout.value() )
            self._new_options.SetInteger( 'connection_error_wait_time', self._connection_error_wait_time.value() )
            self._new_options.SetInteger( 'serverside_bandwidth_wait_time', self._serverside_bandwidth_wait_time.value() )
            self._new_options.SetInteger( 'max_network_jobs', self._max_network_jobs.value() )
            self._new_options.SetInteger( 'max_network_jobs_per_domain', self._max_network_jobs_per_domain.value() )
            
            ( number, time_delta ) = self._domain_network_infrastructure_error_velocity.GetValue()
            
            self._new_options.SetInteger( 'domain_network_infrastructure_error_number', number )
            self._new_options.SetInteger( 'domain_network_infrastructure_error_time_delta', time_delta )
            
        
    
    class _DownloadingPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            gallery_downloader = ClientGUICommon.StaticBox( self, 'gallery downloader' )
            
            gug_key_and_name = HG.client_controller.network_engine.domain_manager.GetDefaultGUGKeyAndName()
            
            self._default_gug = ClientGUIImport.GUGKeyAndNameSelector( gallery_downloader, gug_key_and_name )
            
            self._gallery_page_wait_period_pages = QP.MakeQSpinBox( gallery_downloader, min=1, max=120 )
            self._gallery_file_limit = ClientGUICommon.NoneableSpinCtrl( gallery_downloader, none_phrase = 'no limit', min = 1, max = 1000000 )
            
            self._highlight_new_query = QW.QCheckBox( gallery_downloader )
            
            #
            
            subscriptions = ClientGUICommon.StaticBox( self, 'subscriptions' )
            
            self._gallery_page_wait_period_subscriptions = QP.MakeQSpinBox( subscriptions, min=1, max=30 )
            self._max_simultaneous_subscriptions = QP.MakeQSpinBox( subscriptions, min=1, max=100 )
            
            self._subscription_file_error_cancel_threshold = ClientGUICommon.NoneableSpinCtrl( subscriptions, min = 1, max = 1000000, unit = 'errors' )
            self._subscription_file_error_cancel_threshold.setToolTip( 'This is a simple patch and will be replaced with a better "retry network errors later" system at some point, but is useful to increase if you have subs to unreliable websites.' )
            
            self._process_subs_in_random_order = QW.QCheckBox( subscriptions )
            self._process_subs_in_random_order.setToolTip( 'Processing in random order is useful whenever bandwidth is tight, as it stops an \'aardvark\' subscription from always getting first whack at what is available. Otherwise, they will be processed in alphabetical order.' )
            
            checker_options = self._new_options.GetDefaultSubscriptionCheckerOptions()
            
            self._subscription_checker_options = ClientGUIImport.CheckerOptionsButton( subscriptions, checker_options )
            
            #
            
            watchers = ClientGUICommon.StaticBox( self, 'watchers' )
            
            self._watcher_page_wait_period = QP.MakeQSpinBox( watchers, min=1, max=120 )
            self._highlight_new_watcher = QW.QCheckBox( watchers )
            
            checker_options = self._new_options.GetDefaultWatcherCheckerOptions()
            
            self._watcher_checker_options = ClientGUIImport.CheckerOptionsButton( watchers, checker_options )
            
            #
            
            misc = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._pause_character = QW.QLineEdit( misc )
            self._stop_character = QW.QLineEdit( misc )
            self._show_new_on_file_seed_short_summary = QW.QCheckBox( misc )
            self._show_deleted_on_file_seed_short_summary = QW.QCheckBox( misc )
            
            if self._new_options.GetBoolean( 'advanced_mode' ):
                
                delay_min = 1
                
            else:
                
                delay_min = 600
                
            
            self._subscription_network_error_delay = ClientGUITime.TimeDeltaButton( misc, min = delay_min, days = True, hours = True, minutes = True, seconds = True )
            self._subscription_other_error_delay = ClientGUITime.TimeDeltaButton( misc, min = delay_min, days = True, hours = True, minutes = True, seconds = True )
            self._downloader_network_error_delay = ClientGUITime.TimeDeltaButton( misc, min = delay_min, days = True, hours = True, minutes = True, seconds = True )
            
            #
            
            gallery_page_tt = 'Gallery page fetches are heavy requests with unusual fetch-time requirements. It is important they not wait too long, but it is also useful to throttle them:'
            gallery_page_tt += os.linesep * 2
            gallery_page_tt += '- So they do not compete with file downloads for bandwidth, leading to very unbalanced 20/4400-type queues.'
            gallery_page_tt += os.linesep
            gallery_page_tt += '- So you do not get 1000 items in your queue before realising you did not like that tag anyway.'
            gallery_page_tt += os.linesep
            gallery_page_tt += '- To give servers a break (some gallery pages can be CPU-expensive to generate).'
            gallery_page_tt += os.linesep * 2
            gallery_page_tt += 'These delays/lots are per-domain.'
            gallery_page_tt += os.linesep * 2
            gallery_page_tt += 'If you do not understand this stuff, you can just leave it alone.'
            
            self._gallery_page_wait_period_pages.setValue( self._new_options.GetInteger( 'gallery_page_wait_period_pages' ) )
            self._gallery_page_wait_period_pages.setToolTip( gallery_page_tt )
            self._gallery_file_limit.SetValue( HC.options['gallery_file_limit'] )
            
            self._highlight_new_query.setChecked( self._new_options.GetBoolean( 'highlight_new_query' ) )
            
            self._gallery_page_wait_period_subscriptions.setValue( self._new_options.GetInteger( 'gallery_page_wait_period_subscriptions' ) )
            self._gallery_page_wait_period_subscriptions.setToolTip( gallery_page_tt )
            self._max_simultaneous_subscriptions.setValue( self._new_options.GetInteger( 'max_simultaneous_subscriptions' ) )
            
            self._subscription_file_error_cancel_threshold.SetValue( self._new_options.GetNoneableInteger( 'subscription_file_error_cancel_threshold' ) )
            
            self._process_subs_in_random_order.setChecked( self._new_options.GetBoolean( 'process_subs_in_random_order' ) )
            
            self._pause_character.setText( self._new_options.GetString( 'pause_character' ) )
            self._stop_character.setText( self._new_options.GetString( 'stop_character' ) )
            self._show_new_on_file_seed_short_summary.setChecked( self._new_options.GetBoolean( 'show_new_on_file_seed_short_summary' ) )
            self._show_deleted_on_file_seed_short_summary.setChecked( self._new_options.GetBoolean( 'show_deleted_on_file_seed_short_summary' ) )
            
            self._watcher_page_wait_period.setValue( self._new_options.GetInteger( 'watcher_page_wait_period' ) )
            self._watcher_page_wait_period.setToolTip( gallery_page_tt )
            self._highlight_new_watcher.setChecked( self._new_options.GetBoolean( 'highlight_new_watcher' ) )
            
            self._subscription_network_error_delay.SetValue( self._new_options.GetInteger( 'subscription_network_error_delay' ) )
            self._subscription_other_error_delay.SetValue( self._new_options.GetInteger( 'subscription_other_error_delay' ) )
            self._downloader_network_error_delay.SetValue( self._new_options.GetInteger( 'downloader_network_error_delay' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Default download source:', self._default_gug ) )
            rows.append( ( 'If new query entered and no current highlight, highlight the new query:', self._highlight_new_query ) )
            rows.append( ( 'Additional fixed time (in seconds) to wait between gallery page fetches:', self._gallery_page_wait_period_pages ) )
            rows.append( ( 'By default, stop searching once this many files are found:', self._gallery_file_limit ) )
            
            gridbox = ClientGUICommon.WrapInGrid( gallery_downloader, rows )
            
            gallery_downloader.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Additional fixed time (in seconds) to wait between gallery page fetches:', self._gallery_page_wait_period_subscriptions ) )
            rows.append( ( 'Maximum number of subscriptions that can sync simultaneously:', self._max_simultaneous_subscriptions ) )
            rows.append( ( 'If a subscription has this many failed file imports, stop and continue later:', self._subscription_file_error_cancel_threshold ) )
            rows.append( ( 'Sync subscriptions in random order:', self._process_subs_in_random_order ) )
            
            gridbox = ClientGUICommon.WrapInGrid( subscriptions, rows )
            
            subscriptions.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            subscriptions.Add( self._subscription_checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Additional fixed time (in seconds) to wait between watcher checks:', self._watcher_page_wait_period ) )
            rows.append( ( 'If new watcher entered and no current highlight, highlight the new watcher:', self._highlight_new_watcher ) )
            
            gridbox = ClientGUICommon.WrapInGrid( watchers, rows )
            
            watchers.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            watchers.Add( self._watcher_checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Pause character:', self._pause_character ) )
            rows.append( ( 'Stop character:', self._stop_character ) )
            rows.append( ( 'Show a \'N\' (for \'new\') count on short file import summaries:', self._show_new_on_file_seed_short_summary ) )
            rows.append( ( 'Show a \'D\' (for \'deleted\') count on short file import summaries:', self._show_deleted_on_file_seed_short_summary ) )
            rows.append( ( 'Delay time on a gallery/watcher network error:', self._downloader_network_error_delay ) )
            rows.append( ( 'Delay time on a subscription network error:', self._subscription_network_error_delay ) )
            rows.append( ( 'Delay time on a subscription other error:', self._subscription_other_error_delay ) )
            
            gridbox = ClientGUICommon.WrapInGrid( misc, rows )
            
            misc.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, gallery_downloader, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, subscriptions, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, watchers, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, misc, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            HG.client_controller.network_engine.domain_manager.SetDefaultGUGKeyAndName( self._default_gug.GetValue() )
            
            self._new_options.SetInteger( 'gallery_page_wait_period_pages', self._gallery_page_wait_period_pages.value() )
            HC.options[ 'gallery_file_limit' ] = self._gallery_file_limit.GetValue()
            self._new_options.SetBoolean( 'highlight_new_query', self._highlight_new_query.isChecked() )
            
            self._new_options.SetInteger( 'gallery_page_wait_period_subscriptions', self._gallery_page_wait_period_subscriptions.value() )
            self._new_options.SetInteger( 'max_simultaneous_subscriptions', self._max_simultaneous_subscriptions.value() )
            self._new_options.SetNoneableInteger( 'subscription_file_error_cancel_threshold', self._subscription_file_error_cancel_threshold.GetValue() )
            self._new_options.SetBoolean( 'process_subs_in_random_order', self._process_subs_in_random_order.isChecked() )
            
            self._new_options.SetInteger( 'watcher_page_wait_period', self._watcher_page_wait_period.value() )
            self._new_options.SetBoolean( 'highlight_new_watcher', self._highlight_new_watcher.isChecked() )
            
            self._new_options.SetDefaultWatcherCheckerOptions( self._watcher_checker_options.GetValue() )
            self._new_options.SetDefaultSubscriptionCheckerOptions( self._subscription_checker_options.GetValue() )
            
            self._new_options.SetString( 'pause_character', self._pause_character.text() )
            self._new_options.SetString( 'stop_character', self._stop_character.text() )
            self._new_options.SetBoolean( 'show_new_on_file_seed_short_summary', self._show_new_on_file_seed_short_summary.isChecked() )
            self._new_options.SetBoolean( 'show_deleted_on_file_seed_short_summary', self._show_deleted_on_file_seed_short_summary.isChecked() )
            
            self._new_options.SetInteger( 'subscription_network_error_delay', self._subscription_network_error_delay.GetValue() )
            self._new_options.SetInteger( 'subscription_other_error_delay', self._subscription_other_error_delay.GetValue() )
            self._new_options.SetInteger( 'downloader_network_error_delay', self._downloader_network_error_delay.GetValue() )
            
        
    
    class _DuplicatesPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            weights_panel = ClientGUICommon.StaticBox( self, 'duplicate filter comparison score weights' )
            
            self._duplicate_comparison_score_higher_jpeg_quality = QP.MakeQSpinBox( weights_panel, min=0, max=100 )
            self._duplicate_comparison_score_much_higher_jpeg_quality = QP.MakeQSpinBox( weights_panel, min=0, max=100 )
            self._duplicate_comparison_score_higher_filesize = QP.MakeQSpinBox( weights_panel, min=0, max=100 )
            self._duplicate_comparison_score_much_higher_filesize = QP.MakeQSpinBox( weights_panel, min=0, max=100 )
            self._duplicate_comparison_score_higher_resolution = QP.MakeQSpinBox( weights_panel, min=0, max=100 )
            self._duplicate_comparison_score_much_higher_resolution = QP.MakeQSpinBox( weights_panel, min=0, max=100 )
            self._duplicate_comparison_score_more_tags = QP.MakeQSpinBox( weights_panel, min=0, max=100 )
            self._duplicate_comparison_score_older = QP.MakeQSpinBox( weights_panel, min=0, max=100 )
            
            self._duplicate_filter_max_batch_size = QP.MakeQSpinBox( self, min = 10, max = 1024 )
            
            #
            
            self._duplicate_comparison_score_higher_jpeg_quality.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_jpeg_quality' ) )
            self._duplicate_comparison_score_much_higher_jpeg_quality.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality' ) )
            self._duplicate_comparison_score_higher_filesize.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_filesize' ) )
            self._duplicate_comparison_score_much_higher_filesize.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_filesize' ) )
            self._duplicate_comparison_score_higher_resolution.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_higher_resolution' ) )
            self._duplicate_comparison_score_much_higher_resolution.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_much_higher_resolution' ) )
            self._duplicate_comparison_score_more_tags.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_more_tags' ) )
            self._duplicate_comparison_score_older.setValue( self._new_options.GetInteger( 'duplicate_comparison_score_older' ) )
            
            self._duplicate_filter_max_batch_size.setValue( self._new_options.GetInteger( 'duplicate_filter_max_batch_size' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Score for jpeg with non-trivially higher jpeg quality:', self._duplicate_comparison_score_higher_jpeg_quality ) )
            rows.append( ( 'Score for jpeg with significantly higher jpeg quality:', self._duplicate_comparison_score_much_higher_jpeg_quality ) )
            rows.append( ( 'Score for file with non-trivially higher filesize:', self._duplicate_comparison_score_higher_filesize ) )
            rows.append( ( 'Score for file with significantly higher filesize:', self._duplicate_comparison_score_much_higher_filesize ) )
            rows.append( ( 'Score for file with higher resolution (as num pixels):', self._duplicate_comparison_score_higher_resolution ) )
            rows.append( ( 'Score for file with significantly higher resolution (as num pixels):', self._duplicate_comparison_score_much_higher_resolution ) )
            rows.append( ( 'Score for file with more tags:', self._duplicate_comparison_score_more_tags ) )
            rows.append( ( 'Score for file with non-trivially earlier import time:', self._duplicate_comparison_score_older ) )
            
            gridbox = ClientGUICommon.WrapInGrid( weights_panel, rows )
            
            label = 'When processing potential duplicate pairs in the duplicate filter, the client tries to present the \'best\' file first. It judges the two files on a variety of potential differences, each with a score. The file with the greatest total score is presented first. Here you can tinker with these scores.'
            
            st = ClientGUICommon.BetterStaticText( weights_panel, label )
            st.setWordWrap( True )
            
            weights_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            weights_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, weights_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Max size of duplicate filter pair batches:', self._duplicate_filter_max_batch_size ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'duplicate_comparison_score_higher_jpeg_quality', self._duplicate_comparison_score_higher_jpeg_quality.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_jpeg_quality', self._duplicate_comparison_score_much_higher_jpeg_quality.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_higher_filesize', self._duplicate_comparison_score_higher_filesize.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_filesize', self._duplicate_comparison_score_much_higher_filesize.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_higher_resolution', self._duplicate_comparison_score_higher_resolution.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_much_higher_resolution', self._duplicate_comparison_score_much_higher_resolution.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_more_tags', self._duplicate_comparison_score_more_tags.value() )
            self._new_options.SetInteger( 'duplicate_comparison_score_older', self._duplicate_comparison_score_older.value() )
            
            self._new_options.SetInteger( 'duplicate_filter_max_batch_size', self._duplicate_filter_max_batch_size.value() )
            
        
    
    class _DefaultFileSystemPredicatesPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            self._always_show_system_everything = QW.QCheckBox( 'show system:everything even if total files is over 10,000', self )
            self._always_show_system_everything.setToolTip( 'After users get some experience with the program and a larger collection, they tend to have less use for system:everything.' )
            
            self._always_show_system_everything.setChecked( self._new_options.GetBoolean( 'always_show_system_everything' ) )
            
            self._filter_inbox_and_archive_predicates = QW.QCheckBox( 'hide inbox and archive system predicates if either has no files', self )
            
            self._filter_inbox_and_archive_predicates.setChecked( self._new_options.GetBoolean( 'filter_inbox_and_archive_predicates' ) )
            
            self._file_system_predicate_age = ClientGUISearch.PanelPredicateSystemAgeDelta( self )
            self._file_system_predicate_duration = ClientGUISearch.PanelPredicateSystemDuration( self )
            self._file_system_predicate_height = ClientGUISearch.PanelPredicateSystemHeight( self )
            self._file_system_predicate_limit = ClientGUISearch.PanelPredicateSystemLimit( self )
            self._file_system_predicate_mime = ClientGUISearch.PanelPredicateSystemMime( self )
            self._file_system_predicate_num_pixels = ClientGUISearch.PanelPredicateSystemNumPixels( self )
            self._file_system_predicate_num_tags = ClientGUISearch.PanelPredicateSystemNumTags( self )
            self._file_system_predicate_num_words = ClientGUISearch.PanelPredicateSystemNumWords( self )
            self._file_system_predicate_ratio = ClientGUISearch.PanelPredicateSystemRatio( self )
            self._file_system_predicate_similar_to = ClientGUISearch.PanelPredicateSystemSimilarTo( self )
            self._file_system_predicate_size = ClientGUISearch.PanelPredicateSystemSize( self )
            self._file_system_predicate_width = ClientGUISearch.PanelPredicateSystemWidth( self )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._always_show_system_everything, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._filter_inbox_and_archive_predicates, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_age, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_duration, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_height, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_mime, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_num_pixels, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_num_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_num_words, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_ratio, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_similar_to, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_size, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_system_predicate_width, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'always_show_system_everything', self._always_show_system_everything.isChecked() )
            self._new_options.SetBoolean( 'filter_inbox_and_archive_predicates', self._filter_inbox_and_archive_predicates.isChecked() )
            
            system_predicates = HC.options[ 'file_system_predicates' ]
            
            system_predicates[ 'age' ] = self._file_system_predicate_age.GetInfo()
            system_predicates[ 'duration' ] = self._file_system_predicate_duration.GetInfo()
            system_predicates[ 'hamming_distance' ] = self._file_system_predicate_similar_to.GetInfo()[1]
            system_predicates[ 'height' ] = self._file_system_predicate_height.GetInfo()
            system_predicates[ 'limit' ] = self._file_system_predicate_limit.GetInfo()
            system_predicates[ 'mime' ] = self._file_system_predicate_mime.GetInfo()
            system_predicates[ 'num_pixels' ] = self._file_system_predicate_num_pixels.GetInfo()
            system_predicates[ 'num_tags' ] = self._file_system_predicate_num_tags.GetInfo()
            system_predicates[ 'num_words' ] = self._file_system_predicate_num_words.GetInfo()
            system_predicates[ 'ratio' ] = self._file_system_predicate_ratio.GetInfo()
            system_predicates[ 'size' ] = self._file_system_predicate_size.GetInfo()
            system_predicates[ 'width' ] = self._file_system_predicate_width.GetInfo()
            
            HC.options[ 'file_system_predicates' ] = system_predicates
            
        
    
    class _ExternalProgramsPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            mime_panel = ClientGUICommon.StaticBox( self, '\'open externally\' launch paths' )
            
            self._web_browser_path = QW.QLineEdit( mime_panel )
            
            self._mime_launch_listctrl = ClientGUIListCtrl.BetterListCtrl( mime_panel, CGLC.COLUMN_LIST_EXTERNAL_PROGRAMS.ID, 15, self._ConvertMimeToListCtrlTuples, activation_callback = self._EditMimeLaunch )
            
            #
            
            web_browser_path = self._new_options.GetNoneableString( 'web_browser_path' )
            
            if web_browser_path is not None:
                
                self._web_browser_path.setText( web_browser_path )
                
            
            for mime in HC.SEARCHABLE_MIMES:
                
                launch_path = self._new_options.GetMimeLaunch( mime )
                
                self._mime_launch_listctrl.AddDatas( [ ( mime, launch_path ) ] )
                
            
            self._mime_launch_listctrl.Sort()
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'Setting a specific web browser path here--like \'C:\\program files\\firefox\\firefox.exe "%path%"\'--can help with the \'share->open->in web browser\' command, which is buggy working with OS defaults, particularly on Windows. It also fixes #anchors, which are dropped in some OSes using default means. Use the same %path% format for the \'open externally\' commands below.'
            
            st = ClientGUICommon.BetterStaticText( mime_panel, text )
            st.setWordWrap( True )
            
            mime_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Manual web browser launch path: ', self._web_browser_path ) )
            
            gridbox = ClientGUICommon.WrapInGrid( mime_panel, rows )
            
            mime_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            mime_panel.Add( self._mime_launch_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            QP.AddToLayout( vbox, mime_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _ConvertMimeToListCtrlTuples( self, data ):
            
            ( mime, launch_path ) = data
            
            pretty_mime = HC.mime_string_lookup[ mime ]
            
            if launch_path is None:
                
                pretty_launch_path = 'default: ' + HydrusPaths.GetDefaultLaunchPath()
                
            else:
                
                pretty_launch_path = launch_path
                
            
            display_tuple = ( pretty_mime, pretty_launch_path )
            sort_tuple = display_tuple
            
            return ( display_tuple, sort_tuple )
            
        
        def _EditMimeLaunch( self ):
            
            for ( mime, launch_path ) in self._mime_launch_listctrl.GetData( only_selected = True ):
                
                message = 'Enter the new launch path for ' + HC.mime_string_lookup[ mime ]
                message += os.linesep * 2
                message += 'Hydrus will insert the file\'s full path wherever you put %path%, even multiple times!'
                message += os.linesep * 2
                message += 'Set as blank to reset to default.'
                
                if launch_path is None:
                    
                    default = 'program "%path%"'
                    
                else:
                    
                    default = launch_path
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, message, default = default, allow_blank = True ) as dlg:
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        new_launch_path = dlg.GetValue()
                        
                        if new_launch_path == '':
                            
                            new_launch_path = None
                            
                        
                        if new_launch_path not in ( launch_path, default ):
                            
                            self._mime_launch_listctrl.DeleteDatas( [ ( mime, launch_path ) ] )
                            
                            self._mime_launch_listctrl.AddDatas( [ ( mime, new_launch_path ) ] )
                            
                        
                    else:
                        
                        break
                        
                    
                
            
            self._mime_launch_listctrl.Sort()
            
        
        def UpdateOptions( self ):
            
            web_browser_path = self._web_browser_path.text()
            
            if web_browser_path == '':
                
                web_browser_path = None
                
            
            self._new_options.SetNoneableString( 'web_browser_path', web_browser_path )
            
            for ( mime, launch_path ) in self._mime_launch_listctrl.GetData():
                
                self._new_options.SetMimeLaunch( mime, launch_path )
                
            
        
    
    class _FilesAndTrashPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._export_location = QP.DirPickerCtrl( self )
            
            self._file_system_waits_on_wakeup = QW.QCheckBox( self )
            self._file_system_waits_on_wakeup.setToolTip( 'This is useful if your hydrus is stored on a NAS that takes a few seconds to get going after your machine resumes from sleep.' )
            
            self._delete_to_recycle_bin = QW.QCheckBox( self )
            
            self._confirm_trash = QW.QCheckBox( self )
            self._confirm_archive = QW.QCheckBox( self )
            
            self._remove_filtered_files = QW.QCheckBox( self )
            self._remove_trashed_files = QW.QCheckBox( self )
            
            self._trash_max_age = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no age limit', min = 0, max = 8640 )
            self._trash_max_size = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no size limit', min = 0, max = 20480 )
            
            advanced_file_deletion_panel = ClientGUICommon.StaticBox( self, 'advanced file deletion and custom reasons' )
            
            self._use_advanced_file_deletion_dialog = QW.QCheckBox( advanced_file_deletion_panel )
            self._use_advanced_file_deletion_dialog.setToolTip( 'If this is set, the client will present a more complicated file deletion confirmation dialog that will permit you to set your own deletion reason and perform \'clean\' deletes that leave no deletion record (making later re-import easier).' )
            
            self._advanced_file_deletion_reasons = ClientGUIListBoxes.QueueListBox( advanced_file_deletion_panel, 5, str, add_callable = self._AddAFDR, edit_callable = self._EditAFDR )
            
            #
            
            if HC.options[ 'export_path' ] is not None:
                
                abs_path = HydrusPaths.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
                
                if abs_path is not None:
                    
                    self._export_location.SetPath( abs_path )
                    
                
            
            self._file_system_waits_on_wakeup.setChecked( self._new_options.GetBoolean( 'file_system_waits_on_wakeup' ) )
            
            self._delete_to_recycle_bin.setChecked( HC.options[ 'delete_to_recycle_bin' ] )
            
            self._confirm_trash.setChecked( HC.options[ 'confirm_trash' ] )
            
            self._confirm_archive.setChecked( HC.options[ 'confirm_archive' ] )
            
            self._remove_filtered_files.setChecked( HC.options[ 'remove_filtered_files' ] )
            self._remove_trashed_files.setChecked( HC.options[ 'remove_trashed_files' ] )
            self._trash_max_age.SetValue( HC.options[ 'trash_max_age' ] )
            self._trash_max_size.SetValue( HC.options[ 'trash_max_size' ] )
            
            self._use_advanced_file_deletion_dialog.setChecked( self._new_options.GetBoolean( 'use_advanced_file_deletion_dialog' ) )
            
            self._use_advanced_file_deletion_dialog.clicked.connect( self._UpdateAdvancedControls )
            
            self._advanced_file_deletion_reasons.AddDatas( self._new_options.GetStringList( 'advanced_file_deletion_reasons' ) )
            
            self._UpdateAdvancedControls()
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'If you set the default export directory blank, the client will use \'hydrus_export\' under the current user\'s home directory.'
            
            QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText(self,text), CC.FLAGS_CENTER )
            
            rows = []
            
            rows.append( ( 'Confirm sending files to trash: ', self._confirm_trash ) )
            rows.append( ( 'Confirm sending more than one file to archive or inbox: ', self._confirm_archive ) )
            rows.append( ( 'Wait 15s after computer resume before accessing files: ', self._file_system_waits_on_wakeup ) )
            rows.append( ( 'When deleting files or folders, send them to the OS\'s recycle bin: ', self._delete_to_recycle_bin ) )
            rows.append( ( 'Remove files from view when they are filtered: ', self._remove_filtered_files ) )
            rows.append( ( 'Remove files from view when they are sent to the trash: ', self._remove_trashed_files ) )
            rows.append( ( 'Number of hours a file can be in the trash before being deleted: ', self._trash_max_age ) )
            rows.append( ( 'Maximum size of trash (MB): ', self._trash_max_size ) )
            rows.append( ( 'Default export directory: ', self._export_location ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Use the advanced file deletion dialog: ', self._use_advanced_file_deletion_dialog ) )
            
            gridbox = ClientGUICommon.WrapInGrid( advanced_file_deletion_panel, rows )
            
            advanced_file_deletion_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            advanced_file_deletion_panel.Add( self._advanced_file_deletion_reasons, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            QP.AddToLayout( vbox, advanced_file_deletion_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _AddAFDR( self ):
            
            reason = 'I do not like the file.'
            
            return self._EditAFDR( reason )
            
        
        def _EditAFDR( self, reason ):
            
            with ClientGUIDialogs.DialogTextEntry( self, 'enter the reason', default = reason, allow_blank = False ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    reason = dlg.GetValue()
                    
                    return reason
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
        
        def _UpdateAdvancedControls( self ):
            
            if self._use_advanced_file_deletion_dialog.isChecked():
                
                self._advanced_file_deletion_reasons.setEnabled( True )
                
            else:
                
                self._advanced_file_deletion_reasons.setEnabled( False )
                
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'export_path' ] = HydrusPaths.ConvertAbsPathToPortablePath( self._export_location.GetPath() )
            
            self._new_options.SetBoolean( 'file_system_waits_on_wakeup', self._file_system_waits_on_wakeup.isChecked() )
            
            HC.options[ 'delete_to_recycle_bin' ] = self._delete_to_recycle_bin.isChecked()
            HC.options[ 'confirm_trash' ] = self._confirm_trash.isChecked()
            HC.options[ 'confirm_archive' ] = self._confirm_archive.isChecked()
            HC.options[ 'remove_filtered_files' ] = self._remove_filtered_files.isChecked()
            HC.options[ 'remove_trashed_files' ] = self._remove_trashed_files.isChecked()
            HC.options[ 'trash_max_age' ] = self._trash_max_age.GetValue()
            HC.options[ 'trash_max_size' ] = self._trash_max_size.GetValue()
            
            self._new_options.SetBoolean( 'use_advanced_file_deletion_dialog', self._use_advanced_file_deletion_dialog.isChecked() )
            
            self._new_options.SetStringList( 'advanced_file_deletion_reasons', self._advanced_file_deletion_reasons.GetData() )
            
        
    
    class _FileViewingStatisticsPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._file_viewing_statistics_active = QW.QCheckBox( self )
            self._file_viewing_statistics_active_on_dupe_filter = QW.QCheckBox( self )
            self._file_viewing_statistics_media_min_time = ClientGUICommon.NoneableSpinCtrl( self )
            self._file_viewing_statistics_media_max_time = ClientGUICommon.NoneableSpinCtrl( self )
            self._file_viewing_statistics_preview_min_time = ClientGUICommon.NoneableSpinCtrl( self )
            self._file_viewing_statistics_preview_max_time = ClientGUICommon.NoneableSpinCtrl( self )
            
            self._file_viewing_stats_menu_display = ClientGUICommon.BetterChoice( self )
            
            self._file_viewing_stats_menu_display.addItem( 'do not show', CC.FILE_VIEWING_STATS_MENU_DISPLAY_NONE )
            self._file_viewing_stats_menu_display.addItem( 'show media', CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_ONLY )
            self._file_viewing_stats_menu_display.addItem( 'show media, and put preview in a submenu', CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_IN_SUBMENU )
            self._file_viewing_stats_menu_display.addItem( 'show media and preview in two lines', CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_STACKED )
            self._file_viewing_stats_menu_display.addItem( 'show media and preview combined', CC.FILE_VIEWING_STATS_MENU_DISPLAY_MEDIA_AND_PREVIEW_SUMMED )
            
            #
            
            self._file_viewing_statistics_active.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active' ) )
            self._file_viewing_statistics_active_on_dupe_filter.setChecked( self._new_options.GetBoolean( 'file_viewing_statistics_active_on_dupe_filter' ) )
            self._file_viewing_statistics_media_min_time.SetValue( self._new_options.GetNoneableInteger( 'file_viewing_statistics_media_min_time' ) )
            self._file_viewing_statistics_media_max_time.SetValue( self._new_options.GetNoneableInteger( 'file_viewing_statistics_media_max_time' ) )
            self._file_viewing_statistics_preview_min_time.SetValue( self._new_options.GetNoneableInteger( 'file_viewing_statistics_preview_min_time' ) )
            self._file_viewing_statistics_preview_max_time.SetValue( self._new_options.GetNoneableInteger( 'file_viewing_statistics_preview_max_time' ) )
            
            self._file_viewing_stats_menu_display.SetValue( self._new_options.GetInteger( 'file_viewing_stats_menu_display' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Enable file viewing statistics tracking?:', self._file_viewing_statistics_active ) )
            rows.append( ( 'Enable file viewing statistics tracking on the duplicate filter?:', self._file_viewing_statistics_active_on_dupe_filter ) )
            rows.append( ( 'Min time to view on media viewer to count as a view (seconds):', self._file_viewing_statistics_media_min_time ) )
            rows.append( ( 'Cap any view on the media viewer to this maximum time (seconds):', self._file_viewing_statistics_media_max_time ) )
            rows.append( ( 'Min time to view on preview viewer to count as a view (seconds):', self._file_viewing_statistics_preview_min_time ) )
            rows.append( ( 'Cap any view on the preview viewer to this maximum time (seconds):', self._file_viewing_statistics_preview_max_time ) )
            rows.append( ( 'Show media/preview viewing stats on media right-click menus?:', self._file_viewing_stats_menu_display ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            vbox.addStretch( 1 )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'file_viewing_statistics_active', self._file_viewing_statistics_active.isChecked() )
            self._new_options.SetBoolean( 'file_viewing_statistics_active_on_dupe_filter', self._file_viewing_statistics_active_on_dupe_filter.isChecked() )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_media_min_time', self._file_viewing_statistics_media_min_time.GetValue() )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_media_max_time', self._file_viewing_statistics_media_max_time.GetValue() )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_preview_min_time', self._file_viewing_statistics_preview_min_time.GetValue() )
            self._new_options.SetNoneableInteger( 'file_viewing_statistics_preview_max_time', self._file_viewing_statistics_preview_max_time.GetValue() )
            
            self._new_options.SetInteger( 'file_viewing_stats_menu_display', self._file_viewing_stats_menu_display.GetValue() )
            
        
    
    class _GUIPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._main_gui_panel = ClientGUICommon.StaticBox( self, 'main window' )
            
            self._main_gui_title = QW.QLineEdit( self._main_gui_panel )
            
            self._confirm_client_exit = QW.QCheckBox( self._main_gui_panel )
            
            self._activate_window_on_tag_search_page_activation = QW.QCheckBox( self._main_gui_panel )
            
            tt = 'Middle-clicking one or more tags in a taglist will cause the creation of a new search page for those tags. If you do this from the media viewer or a child manage tags dialog, do you want to switch immediately to the main gui?'
            
            self._activate_window_on_tag_search_page_activation.setToolTip( tt )
            
            #
            
            self._popup_panel = ClientGUICommon.StaticBox( self, 'popup window toaster' )
            
            self._popup_message_character_width = QP.MakeQSpinBox( self._popup_panel, min = 16, max = 256 )
            
            self._popup_message_force_min_width = QW.QCheckBox( self._popup_panel )
            
            self._hide_message_manager_on_gui_iconise = QW.QCheckBox( self._popup_panel )
            self._hide_message_manager_on_gui_iconise.setToolTip( 'If your message manager does not automatically minimise with your main gui, try this. It can lead to unusual show and positioning behaviour on window managers that do not support it, however.' )
            
            self._hide_message_manager_on_gui_deactive = QW.QCheckBox( self._popup_panel )
            self._hide_message_manager_on_gui_deactive.setToolTip( 'If your message manager stays up after you minimise the program to the system tray using a custom window manager, try this out! It hides the popup messages as soon as the main gui loses focus.' )
            
            #
            
            self._misc_panel = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._always_show_iso_time = QW.QCheckBox( self._misc_panel )
            tt = 'In many places across the program (typically import status lists), the client will state a timestamp as "5 days ago". If you would prefer a standard ISO string, like "2018-03-01 12:40:23", check this.'
            self._always_show_iso_time.setToolTip( tt )
            
            self._discord_dnd_fix = QW.QCheckBox( self._misc_panel )
            self._discord_dnd_fix.setToolTip( 'This makes small file drag-and-drops a little laggier in exchange for discord support.' )
            
            self._secret_discord_dnd_fix = QW.QCheckBox( self._misc_panel )
            self._secret_discord_dnd_fix.setToolTip( 'This saves the lag but is potentially dangerous, as it (may) treat the from-db-files-drag as a move rather than a copy and hence only works when the drop destination will not consume the files. It requires an additional secret Alternate key to unlock.' )
            
            self._notify_client_api_cookies = QW.QCheckBox( self._misc_panel )
            self._notify_client_api_cookies.setToolTip( 'This will make a short-lived popup message every time you get new cookie information over the Client API.' )
            
            self._use_qt_file_dialogs = QW.QCheckBox( self._misc_panel )
            self._use_qt_file_dialogs.setToolTip( 'If you get crashes opening file/directory dialogs, try this.' )
            
            #
            
            frame_locations_panel = ClientGUICommon.StaticBox( self, 'frame locations' )
            
            self._frame_locations = ClientGUIListCtrl.BetterListCtrl( frame_locations_panel, CGLC.COLUMN_LIST_FRAME_LOCATIONS.ID, 15, data_to_tuples_func = lambda x: (self._GetPrettyFrameLocationInfo( x ), self._GetPrettyFrameLocationInfo( x )), activation_callback = self.EditFrameLocations )
            
            self._frame_locations_edit_button = QW.QPushButton( 'edit', frame_locations_panel )
            self._frame_locations_edit_button.clicked.connect( self.EditFrameLocations )
            
            #
            
            self._new_options = HG.client_controller.new_options
            
            self._main_gui_title.setText( self._new_options.GetString( 'main_gui_title' ) )
            
            self._confirm_client_exit.setChecked( HC.options[ 'confirm_client_exit' ] )
            
            self._activate_window_on_tag_search_page_activation.setChecked( self._new_options.GetBoolean( 'activate_window_on_tag_search_page_activation' ) )
            
            self._always_show_iso_time.setChecked( self._new_options.GetBoolean( 'always_show_iso_time' ) )
            
            self._popup_message_character_width.setValue( self._new_options.GetInteger( 'popup_message_character_width' ) )
            
            self._popup_message_force_min_width.setChecked( self._new_options.GetBoolean( 'popup_message_force_min_width' ) )
            
            self._discord_dnd_fix.setChecked( self._new_options.GetBoolean( 'discord_dnd_fix' ) )
            
            self._secret_discord_dnd_fix.setChecked( self._new_options.GetBoolean( 'secret_discord_dnd_fix' ) )
            
            self._hide_message_manager_on_gui_iconise.setChecked( self._new_options.GetBoolean( 'hide_message_manager_on_gui_iconise' ) )
            self._hide_message_manager_on_gui_deactive.setChecked( self._new_options.GetBoolean( 'hide_message_manager_on_gui_deactive' ) )
            
            self._notify_client_api_cookies.setChecked( self._new_options.GetBoolean( 'notify_client_api_cookies' ) )
            
            self._use_qt_file_dialogs.setChecked( self._new_options.GetBoolean( 'use_qt_file_dialogs' ) )
            
            for ( name, info ) in self._new_options.GetFrameLocations():
                
                listctrl_list = QP.ListsToTuples( [ name ] + list( info ) )
                
                self._frame_locations.AddDatas( ( listctrl_list, ) )
                
            
            #self._frame_locations.SortListItems( col = 0 )
            
            #
            
            rows = []
            
            rows.append( ( 'Main gui title: ', self._main_gui_title ) )
            rows.append( ( 'Confirm client exit: ', self._confirm_client_exit ) )
            rows.append( ( 'Switch to main window when opening tag search page from media viewer: ', self._activate_window_on_tag_search_page_activation ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._main_gui_panel, rows )
            
            self._main_gui_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Approximate max width of popup messages (in characters): ', self._popup_message_character_width ) )
            rows.append( ( 'Make a short-lived popup on cookie updates through the Client API: ', self._notify_client_api_cookies ) )
            rows.append( ( 'BUGFIX: Hide the popup toaster when the main gui is minimised: ', self._hide_message_manager_on_gui_iconise ) )
            rows.append( ( 'BUGFIX: Hide the popup toaster when the main gui loses focus: ', self._hide_message_manager_on_gui_deactive ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._popup_panel, rows )
            
            self._popup_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Prefer ISO time ("2018-03-01 12:40:23") to "5 days ago": ', self._always_show_iso_time ) )
            rows.append( ( 'BUGFIX: Force this width as the minimum width for all popup messages: ', self._popup_message_force_min_width ) )
            rows.append( ( 'BUGFIX: Discord file drag-and-drop fix (works for <=25, <200MB file DnDs): ', self._discord_dnd_fix ) )
            rows.append( ( 'EXPERIMENTAL BUGFIX: Secret discord file drag-and-drop fix: ', self._secret_discord_dnd_fix ) )
            rows.append( ( 'ANTI-CRASH BUGFIX: Use Qt file/directory selection dialogs, rather than OS native: ', self._use_qt_file_dialogs ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            self._misc_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            text = 'Here you can override the current and default values for many frame and dialog sizing and positioning variables.'
            text += os.linesep
            text += 'This is an advanced control. If you aren\'t confident of what you are doing here, come back later!'
            
            frame_locations_panel.Add( QW.QLabel( text, frame_locations_panel ), CC.FLAGS_EXPAND_PERPENDICULAR )
            frame_locations_panel.Add( self._frame_locations, CC.FLAGS_EXPAND_BOTH_WAYS )
            frame_locations_panel.Add( self._frame_locations_edit_button, CC.FLAGS_LONE_BUTTON )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._main_gui_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, self._popup_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, self._misc_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, frame_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _GetPrettyFrameLocationInfo( self, listctrl_list ):
            
            pretty_listctrl_list = []
            
            for item in listctrl_list:
                
                pretty_listctrl_list.append( str( item ) )
                
            
            return pretty_listctrl_list
            
        
        def EditFrameLocations( self ):
            
            for listctrl_list in self._frame_locations.GetData( only_selected = True ):
                
                title = 'set frame location information'
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsEdit.EditFrameLocationPanel( dlg, listctrl_list )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        new_listctrl_list = panel.GetValue()
                        
                        self._frame_locations.ReplaceData( listctrl_list, new_listctrl_list )
                        
                    
                
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'confirm_client_exit' ] = self._confirm_client_exit.isChecked()
            
            self._new_options.SetBoolean( 'always_show_iso_time', self._always_show_iso_time.isChecked() )
            
            self._new_options.SetBoolean( 'activate_window_on_tag_search_page_activation', self._activate_window_on_tag_search_page_activation.isChecked() )
            
            self._new_options.SetInteger( 'popup_message_character_width', self._popup_message_character_width.value() )
            
            self._new_options.SetBoolean( 'popup_message_force_min_width', self._popup_message_force_min_width.isChecked() )
            
            title = self._main_gui_title.text()
            
            self._new_options.SetString( 'main_gui_title', title )
            
            HG.client_controller.pub( 'main_gui_title', title )
            
            self._new_options.SetBoolean( 'notify_client_api_cookies', self._notify_client_api_cookies.isChecked() )
            self._new_options.SetBoolean( 'discord_dnd_fix', self._discord_dnd_fix.isChecked() )
            self._new_options.SetBoolean( 'secret_discord_dnd_fix', self._secret_discord_dnd_fix.isChecked() )
            self._new_options.SetBoolean( 'hide_message_manager_on_gui_iconise', self._hide_message_manager_on_gui_iconise.isChecked() )
            self._new_options.SetBoolean( 'hide_message_manager_on_gui_deactive', self._hide_message_manager_on_gui_deactive.isChecked() )
            self._new_options.SetBoolean( 'use_qt_file_dialogs', self._use_qt_file_dialogs.isChecked() )
            
            for listctrl_list in self._frame_locations.GetData():
                
                ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
                
                self._new_options.SetFrameLocation( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
                
            
        
    
    class _GUIPagesPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            self._sessions_panel = ClientGUICommon.StaticBox( self, 'sessions' )
            
            self._default_gui_session = QW.QComboBox( self._sessions_panel )
            
            self._last_session_save_period_minutes = QP.MakeQSpinBox( self._sessions_panel, min = 1, max = 1440 )
            
            self._only_save_last_session_during_idle = QW.QCheckBox( self._sessions_panel )
            
            self._only_save_last_session_during_idle.setToolTip( 'This is useful if you usually have a very large session (200,000+ files/import items open) and a client that is always on.' )
            
            self._number_of_gui_session_backups = QP.MakeQSpinBox( self._sessions_panel, min = 1, max = 32 )
            
            self._number_of_gui_session_backups.setToolTip( 'The client keeps multiple rolling backups of your gui sessions. If you have very large sessions, you might like to reduce this number.' )
            
            #
            
            self._pages_panel = ClientGUICommon.StaticBox( self, 'pages' )
            
            self._default_new_page_goes = ClientGUICommon.BetterChoice( self._pages_panel )
            
            for value in [ CC.NEW_PAGE_GOES_FAR_LEFT, CC.NEW_PAGE_GOES_LEFT_OF_CURRENT, CC.NEW_PAGE_GOES_RIGHT_OF_CURRENT, CC.NEW_PAGE_GOES_FAR_RIGHT ]:
                
                self._default_new_page_goes.addItem( CC.new_page_goes_string_lookup[ value], value )
                
            
            self._notebook_tabs_on_left = QW.QCheckBox( self._pages_panel )
            
            self._total_pages_warning = QP.MakeQSpinBox( self._pages_panel, min=5, max=500 )
            
            self._reverse_page_shift_drag_behaviour = QW.QCheckBox( self._pages_panel )
            self._reverse_page_shift_drag_behaviour.setToolTip( 'By default, holding down shift when you drop off a page tab means the client will not \'chase\' the page tab. This makes this behaviour default, with shift-drop meaning to chase.' )
            
            #
            
            self._page_names_panel = ClientGUICommon.StaticBox( self._pages_panel, 'page tab names' )
            
            self._max_page_name_chars = QP.MakeQSpinBox( self._page_names_panel, min=1, max=256 )
            self._elide_page_tab_names = QW.QCheckBox( self._page_names_panel )
            
            self._page_file_count_display = ClientGUICommon.BetterChoice( self._page_names_panel )
            
            for display_type in ( CC.PAGE_FILE_COUNT_DISPLAY_ALL, CC.PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS, CC.PAGE_FILE_COUNT_DISPLAY_NONE ):
                
                self._page_file_count_display.addItem( CC.page_file_count_display_string_lookup[ display_type], display_type )
                
            
            self._import_page_progress_display = QW.QCheckBox( self._page_names_panel )
            
            #
            
            self._controls_panel = ClientGUICommon.StaticBox( self, 'controls' )
            
            self._autocomplete_float_main_gui = QW.QCheckBox( self._controls_panel )
            self._autocomplete_float_frames = QW.QCheckBox( self._controls_panel )
            
            self._ac_read_list_height_num_chars = QP.MakeQSpinBox( self._controls_panel, min = 1, max = 128 )
            self._ac_write_list_height_num_chars = QP.MakeQSpinBox( self._controls_panel, min = 1, max = 128 )
            
            self._set_search_focus_on_page_change = QW.QCheckBox( self._controls_panel )
            
            self._hide_preview = QW.QCheckBox( self._controls_panel )
            
            #
            
            gui_session_names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
            
            if 'last session' not in gui_session_names:
                
                gui_session_names.insert( 0, 'last session' )
                
            
            self._default_gui_session.addItem( 'just a blank page', None )
            
            for name in gui_session_names:
                
                self._default_gui_session.addItem( name, name )
                
            
            try:
                
                QP.SetStringSelection( self._default_gui_session, HC.options['default_gui_session'] )
                
            except:
                
                self._default_gui_session.setCurrentIndex( 0 )
                
            
            self._last_session_save_period_minutes.setValue( self._new_options.GetInteger( 'last_session_save_period_minutes' ) )
            
            self._only_save_last_session_during_idle.setChecked( self._new_options.GetBoolean( 'only_save_last_session_during_idle' ) )
            
            self._number_of_gui_session_backups.setValue( self._new_options.GetInteger( 'number_of_gui_session_backups' ) )
            
            self._default_new_page_goes.SetValue( self._new_options.GetInteger( 'default_new_page_goes' ) )
            
            self._notebook_tabs_on_left.setChecked( self._new_options.GetBoolean( 'notebook_tabs_on_left' ) )
            
            self._max_page_name_chars.setValue( self._new_options.GetInteger( 'max_page_name_chars' ) )
            
            self._elide_page_tab_names.setChecked( self._new_options.GetBoolean( 'elide_page_tab_names' ) )
            
            self._page_file_count_display.SetValue( self._new_options.GetInteger( 'page_file_count_display' ) )
            
            self._import_page_progress_display.setChecked( self._new_options.GetBoolean( 'import_page_progress_display' ) )
            
            self._total_pages_warning.setValue( self._new_options.GetInteger( 'total_pages_warning' ) )
            
            self._reverse_page_shift_drag_behaviour.setChecked( self._new_options.GetBoolean( 'reverse_page_shift_drag_behaviour' ) )
            
            self._autocomplete_float_main_gui.setChecked( self._new_options.GetBoolean( 'autocomplete_float_main_gui' ) )
            self._autocomplete_float_frames.setChecked( self._new_options.GetBoolean( 'autocomplete_float_frames' ) )
            
            self._ac_read_list_height_num_chars.setValue( self._new_options.GetInteger( 'ac_read_list_height_num_chars' ) )
            self._ac_write_list_height_num_chars.setValue( self._new_options.GetInteger( 'ac_write_list_height_num_chars' ) )
            
            self._set_search_focus_on_page_change.setChecked( self._new_options.GetBoolean( 'set_search_focus_on_page_change' ) )
            
            self._hide_preview.setChecked( HC.options[ 'hide_preview' ] )
            
            #
            
            rows = []
            
            rows.append( ( 'Default session on startup: ', self._default_gui_session ) )
            rows.append( ( 'If \'last session\' above, autosave it how often (minutes)?', self._last_session_save_period_minutes ) )
            rows.append( ( 'If \'last session\' above, only autosave during idle time?', self._only_save_last_session_during_idle ) )
            rows.append( ( 'Number of session backups to keep: ', self._number_of_gui_session_backups ) )
            
            sessions_gridbox = ClientGUICommon.WrapInGrid( self._sessions_panel, rows )
            
            self._sessions_panel.Add( sessions_gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            rows = []
            
            rows.append( ( 'By default, put new page tabs on (requires restart): ', self._default_new_page_goes ) )
            rows.append( ( 'Line notebook tabs down the left: ', self._notebook_tabs_on_left ) )
            rows.append( ( 'Reverse page tab shift-drag behaviour: ', self._reverse_page_shift_drag_behaviour ) )
            rows.append( ( 'Warn at this many total pages: ', self._total_pages_warning ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._pages_panel, rows )
            
            rows = []
            
            rows.append( ( 'Max characters to display in a page name: ', self._max_page_name_chars ) )
            rows.append( ( 'When there are too many tabs to fit, \'...\' elide their names so they fit: ', self._elide_page_tab_names ) )
            rows.append( ( 'Show page file count after its name: ', self._page_file_count_display ) )
            rows.append( ( 'Show import page x/y progress after its name: ', self._import_page_progress_display ) )
            
            page_names_gridbox = ClientGUICommon.WrapInGrid( self._page_names_panel, rows )
            
            label = 'If you have enough pages in a row, left/right arrows will appear to navigate them back and forth.'
            label += os.linesep
            label += 'Due to an unfortunate Qt issue, the tab bar will scroll so the current tab is right-most visible whenever a page is renamed.'
            label += os.linesep
            label += 'Therefore, if you set pages to have current file count or import progress in their name (which will update from time to time), do not put import pages in a long row of tabs, as it will reset scroll position on every progress update.'
            label += os.linesep
            label += 'Just make some nested \'page of pages\' so they are not all in the same row.'
            
            st = ClientGUICommon.BetterStaticText( self._page_names_panel, label )
            
            st.setWordWrap( True )
            
            self._page_names_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._page_names_panel.Add( page_names_gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._pages_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self._pages_panel.Add( self._page_names_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Autocomplete results float in main gui: ', self._autocomplete_float_main_gui ) )
            rows.append( ( 'Autocomplete results float in other windows: ', self._autocomplete_float_frames ) )
            rows.append( ( '\'Read\' autocomplete list height: ', self._ac_read_list_height_num_chars ) )
            rows.append( ( '\'Write\' autocomplete list height: ', self._ac_write_list_height_num_chars ) )
            rows.append( ( 'When switching to a page, focus its text input field (if any): ', self._set_search_focus_on_page_change ) )
            rows.append( ( 'Hide the bottom-left preview window: ', self._hide_preview ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._controls_panel, rows )
            
            self._controls_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._sessions_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, self._pages_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._controls_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'default_gui_session' ] = self._default_gui_session.currentText()
            
            self._new_options.SetBoolean( 'notebook_tabs_on_left', self._notebook_tabs_on_left.isChecked() )
            
            self._new_options.SetInteger( 'last_session_save_period_minutes', self._last_session_save_period_minutes.value() )
            
            self._new_options.SetInteger( 'number_of_gui_session_backups', self._number_of_gui_session_backups.value() )
            
            self._new_options.SetBoolean( 'only_save_last_session_during_idle', self._only_save_last_session_during_idle.isChecked() )
            
            self._new_options.SetInteger( 'default_new_page_goes', self._default_new_page_goes.GetValue() )
            
            self._new_options.SetInteger( 'max_page_name_chars', self._max_page_name_chars.value() )
            
            self._new_options.SetBoolean( 'elide_page_tab_names', self._elide_page_tab_names.isChecked() )
            
            self._new_options.SetInteger( 'page_file_count_display', self._page_file_count_display.GetValue() )
            self._new_options.SetBoolean( 'import_page_progress_display', self._import_page_progress_display.isChecked() )
            
            self._new_options.SetInteger( 'total_pages_warning', self._total_pages_warning.value() )
            
            self._new_options.SetBoolean( 'reverse_page_shift_drag_behaviour', self._reverse_page_shift_drag_behaviour.isChecked() )
            
            self._new_options.SetBoolean( 'autocomplete_float_main_gui', self._autocomplete_float_main_gui.isChecked() )
            self._new_options.SetBoolean( 'autocomplete_float_frames', self._autocomplete_float_frames.isChecked() )
            
            self._new_options.SetInteger( 'ac_read_list_height_num_chars', self._ac_read_list_height_num_chars.value() )
            self._new_options.SetInteger( 'ac_write_list_height_num_chars', self._ac_write_list_height_num_chars.value() )
            
            self._new_options.SetBoolean( 'set_search_focus_on_page_change', self._set_search_focus_on_page_change.isChecked() )
            
            HC.options[ 'hide_preview' ] = self._hide_preview.isChecked()
            
        
    
    class _ImportingPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            default_fios = ClientGUICommon.StaticBox( self, 'default file import options' )
            
            from hydrus.client.gui import ClientGUIImport
            
            show_downloader_options = True
            
            quiet_file_import_options = self._new_options.GetDefaultFileImportOptions( 'quiet' )
            
            self._quiet_fios = ClientGUIImport.FileImportOptionsButton( default_fios, quiet_file_import_options, show_downloader_options )
            
            loud_file_import_options = self._new_options.GetDefaultFileImportOptions( 'loud' )
            
            self._loud_fios = ClientGUIImport.FileImportOptionsButton( default_fios, loud_file_import_options, show_downloader_options )
            
            #
            
            rows = []
            
            rows.append( ( 'For \'quiet\' import contexts like import folders and subscriptions:', self._quiet_fios ) )
            rows.append( ( 'For import contexts that work on pages:', self._loud_fios ) )
            
            gridbox = ClientGUICommon.WrapInGrid( default_fios, rows )
            
            default_fios.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, default_fios, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetDefaultFileImportOptions( 'quiet', self._quiet_fios.GetValue() )
            self._new_options.SetDefaultFileImportOptions( 'loud', self._loud_fios.GetValue() )
            
        
    
    class _MaintenanceAndProcessingPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._jobs_panel = ClientGUICommon.StaticBox( self, 'when to run high cpu jobs' )
            self._file_maintenance_panel = ClientGUICommon.StaticBox( self, 'file maintenance' )
            self._vacuum_panel = ClientGUICommon.StaticBox( self, 'vacuum' )
            
            self._idle_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'idle' )
            self._shutdown_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'shutdown' )
            
            #
            
            self._idle_normal = QW.QCheckBox( self._idle_panel )
            self._idle_normal.clicked.connect( self._EnableDisableIdleNormal )
            
            self._idle_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, '', min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore normal browsing' )
            self._idle_mouse_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, '', min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore mouse movements' )
            self._idle_cpu_max = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, '', min = 5, max = 99, unit = '%', none_phrase = 'ignore cpu usage' )
            
            #
            
            self._idle_shutdown = ClientGUICommon.BetterChoice( self._shutdown_panel )
            
            for idle_id in ( CC.IDLE_NOT_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN_ASK_FIRST ):
                
                self._idle_shutdown.addItem( CC.idle_string_lookup[ idle_id], idle_id )
                
            
            self._idle_shutdown.currentIndexChanged.connect( self._EnableDisableIdleShutdown )
            
            self._idle_shutdown_max_minutes = QP.MakeQSpinBox( self._shutdown_panel, min=1, max=1440 )
            self._shutdown_work_period = ClientGUITime.TimeDeltaButton( self._shutdown_panel, min = 60, days = True, hours = True, minutes = True )
            
            #
            
            min_unit_value = 1
            max_unit_value = 1000
            min_time_delta = 1
            
            self._file_maintenance_during_idle = QW.QCheckBox( self._file_maintenance_panel )
            
            self._file_maintenance_idle_throttle_velocity = ClientGUITime.VelocityCtrl( self._file_maintenance_panel, min_unit_value, max_unit_value, min_time_delta, minutes = True, seconds = True, per_phrase = 'every', unit = 'heavy work units' )
            
            self._file_maintenance_during_active = QW.QCheckBox( self._file_maintenance_panel )
            
            self._file_maintenance_active_throttle_velocity = ClientGUITime.VelocityCtrl( self._file_maintenance_panel, min_unit_value, max_unit_value, min_time_delta, minutes = True, seconds = True, per_phrase = 'every', unit = 'heavy work units' )
            
            tt = 'Different jobs will count for more or less weight. A file metadata reparse will count as one work unit, but quicker jobs like checking for file presence will count as fractions of one and will will work more frequently.'
            tt += os.linesep * 2
            tt += 'Please note that this throttle is not rigorous for long timescales, as file processing history is not currently saved on client exit. If you restart the client, the file manager thinks it has run 0 jobs and will be happy to run until the throttle kicks in again.'
            
            self._file_maintenance_idle_throttle_velocity.setToolTip( tt )
            self._file_maintenance_active_throttle_velocity.setToolTip( tt )
            
            #
            
            self._maintenance_vacuum_period_days = ClientGUICommon.NoneableSpinCtrl( self._vacuum_panel, '', min = 28, max = 1000, none_phrase = 'do not automatically vacuum' )
            
            tts = 'Vacuuming is a kind of full defrag of the database\'s internal page table. It can take a long time (1MB/s) on a slow drive and does not need to be done often, so feel free to set this at 180 days+.'
            
            self._maintenance_vacuum_period_days.setToolTip( tts )
            
            #
            
            self._idle_normal.setChecked( HC.options[ 'idle_normal' ] )
            self._idle_period.SetValue( HC.options['idle_period'] )
            self._idle_mouse_period.SetValue( HC.options['idle_mouse_period'] )
            self._idle_cpu_max.SetValue( HC.options['idle_cpu_max'] )
            
            self._idle_shutdown.SetValue( HC.options[ 'idle_shutdown' ] )
            self._idle_shutdown_max_minutes.setValue( HC.options['idle_shutdown_max_minutes'] )
            self._shutdown_work_period.SetValue( self._new_options.GetInteger( 'shutdown_work_period' ) )
            
            self._file_maintenance_during_idle.setChecked( self._new_options.GetBoolean( 'file_maintenance_during_idle' ) )
            
            file_maintenance_idle_throttle_files = self._new_options.GetInteger( 'file_maintenance_idle_throttle_files' )
            file_maintenance_idle_throttle_time_delta = self._new_options.GetInteger( 'file_maintenance_idle_throttle_time_delta' )
            
            file_maintenance_idle_throttle_velocity = ( file_maintenance_idle_throttle_files, file_maintenance_idle_throttle_time_delta )
            
            self._file_maintenance_idle_throttle_velocity.SetValue( file_maintenance_idle_throttle_velocity )
            
            self._file_maintenance_during_active.setChecked( self._new_options.GetBoolean( 'file_maintenance_during_active' ) )
            
            file_maintenance_active_throttle_files = self._new_options.GetInteger( 'file_maintenance_active_throttle_files' )
            file_maintenance_active_throttle_time_delta = self._new_options.GetInteger( 'file_maintenance_active_throttle_time_delta' )
            
            file_maintenance_active_throttle_velocity = ( file_maintenance_active_throttle_files, file_maintenance_active_throttle_time_delta )
            
            self._file_maintenance_active_throttle_velocity.SetValue( file_maintenance_active_throttle_velocity )
            
            self._maintenance_vacuum_period_days.SetValue( self._new_options.GetNoneableInteger( 'maintenance_vacuum_period_days' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Run maintenance jobs when the client is idle and the system is not otherwise busy: ', self._idle_normal ) )
            rows.append( ( 'Assume the client is idle if no general browsing activity has occurred in the past: ', self._idle_period ) )
            rows.append( ( 'Assume the client is idle if the mouse has not been moved in the past: ', self._idle_mouse_period ) )
            rows.append( ( 'Assume the system is busy if any CPU core has recent average usage above: ', self._idle_cpu_max ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._idle_panel, rows )
            
            self._idle_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Run jobs on shutdown: ', self._idle_shutdown ) )
            rows.append( ( 'Only run shutdown jobs once per: ', self._shutdown_work_period ) )
            rows.append( ( 'Max number of minutes to run shutdown jobs: ', self._idle_shutdown_max_minutes ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._shutdown_panel, rows )
            
            self._shutdown_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            text = '***'
            text += os.linesep
            text +='If you are a new user or do not completely understand these options, please do not touch them! Do not set the client to be idle all the time unless you know what you are doing or are testing something and are prepared for potential problems!'
            text += os.linesep
            text += '***'
            text += os.linesep * 2
            text += 'Sometimes, the client needs to do some heavy maintenance. This could be reformatting the database to keep it running fast or processing a large number of tags from a repository. Typically, these jobs will not allow you to use the gui while they run, and on slower computers--or those with not much memory--they can take a long time to complete.'
            text += os.linesep * 2
            text += 'You can set these jobs to run only when the client is idle, or only during shutdown, or neither, or both. If you leave the client on all the time in the background, focusing on \'idle time\' processing is often ideal. If you have a slow computer, relying on \'shutdown\' processing (which you can manually start when convenient), is often better.'
            text += os.linesep * 2
            text += 'If the client switches from idle to not idle during a job, it will try to abandon it and give you back control. This is not always possible, and even when it is, it will sometimes take several minutes, particularly on slower machines or those on HDDs rather than SSDs.'
            text += os.linesep * 2
            text += 'If the client believes the system is busy, it will generally not start jobs.'
            
            st = ClientGUICommon.BetterStaticText( self._jobs_panel, label = text )
            st.setWordWrap( True )
            
            self._jobs_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.Add( self._idle_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.Add( self._shutdown_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            message = 'Scheduled jobs such as reparsing file metadata and regenerating thumbnails are performed in the background.'
            
            self._file_maintenance_panel.Add( ClientGUICommon.BetterStaticText( self._file_maintenance_panel, label = message ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Run file maintenance during idle time: ', self._file_maintenance_during_idle ) )
            rows.append( ( 'Idle throttle: ', self._file_maintenance_idle_throttle_velocity ) )
            rows.append( ( 'Run file maintenance during normal time: ', self._file_maintenance_during_active ) )
            rows.append( ( 'Normal throttle: ', self._file_maintenance_active_throttle_velocity ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._file_maintenance_panel, rows )
            
            self._file_maintenance_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Number of days to wait between vacuums: ', self._maintenance_vacuum_period_days ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._vacuum_panel, rows )
            
            self._vacuum_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._file_maintenance_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, self._vacuum_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
            self._EnableDisableIdleNormal()
            self._EnableDisableIdleShutdown()
            
        
        def _EnableDisableIdleNormal( self ):
            
            if self._idle_normal.isChecked():
                
                self._idle_period.setEnabled( True )
                self._idle_mouse_period.setEnabled( True )
                self._idle_cpu_max.setEnabled( True )
                
            else:
                
                self._idle_period.setEnabled( False )
                self._idle_mouse_period.setEnabled( False )
                self._idle_cpu_max.setEnabled( False )
                
            
        
        def _EnableDisableIdleShutdown( self ):
            
            if self._idle_shutdown.GetValue() == CC.IDLE_NOT_ON_SHUTDOWN:
                
                self._shutdown_work_period.setEnabled( False )
                self._idle_shutdown_max_minutes.setEnabled( False )
                
            else:
                
                self._shutdown_work_period.setEnabled( True )
                self._idle_shutdown_max_minutes.setEnabled( True )
                
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'idle_normal' ] = self._idle_normal.isChecked()
            
            HC.options[ 'idle_period' ] = self._idle_period.GetValue()
            HC.options[ 'idle_mouse_period' ] = self._idle_mouse_period.GetValue()
            HC.options[ 'idle_cpu_max' ] = self._idle_cpu_max.GetValue()
            
            HC.options[ 'idle_shutdown' ] = self._idle_shutdown.GetValue()
            HC.options[ 'idle_shutdown_max_minutes' ] = self._idle_shutdown_max_minutes.value()
            
            self._new_options.SetInteger( 'shutdown_work_period', self._shutdown_work_period.GetValue() )
            
            self._new_options.SetBoolean( 'file_maintenance_during_idle', self._file_maintenance_during_idle.isChecked() )
            
            file_maintenance_idle_throttle_velocity = self._file_maintenance_idle_throttle_velocity.GetValue()
            
            ( file_maintenance_idle_throttle_files, file_maintenance_idle_throttle_time_delta ) = file_maintenance_idle_throttle_velocity
            
            self._new_options.SetInteger( 'file_maintenance_idle_throttle_files', file_maintenance_idle_throttle_files )
            self._new_options.SetInteger( 'file_maintenance_idle_throttle_time_delta', file_maintenance_idle_throttle_time_delta )
            
            self._new_options.SetBoolean( 'file_maintenance_during_active', self._file_maintenance_during_active.isChecked() )
            
            file_maintenance_active_throttle_velocity = self._file_maintenance_active_throttle_velocity.GetValue()
            
            ( file_maintenance_active_throttle_files, file_maintenance_active_throttle_time_delta ) = file_maintenance_active_throttle_velocity
            
            self._new_options.SetInteger( 'file_maintenance_active_throttle_files', file_maintenance_active_throttle_files )
            self._new_options.SetInteger( 'file_maintenance_active_throttle_time_delta', file_maintenance_active_throttle_time_delta )
            
            self._new_options.SetNoneableInteger( 'maintenance_vacuum_period_days', self._maintenance_vacuum_period_days.GetValue() )
            
        
    
    class _MediaPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._animation_start_position = QP.MakeQSpinBox( self, min=0, max=100 )
            
            self._disable_cv_for_gifs = QW.QCheckBox( self )
            self._disable_cv_for_gifs.setToolTip( 'OpenCV is good at rendering gifs, but if you have problems with it and your graphics card, check this and the less reliable and slower PIL will be used instead. EDIT: OpenCV is much better these days--this is mostly not needed.' )
            
            self._load_images_with_pil = QW.QCheckBox( self )
            self._load_images_with_pil.setToolTip( 'OpenCV is much faster than PIL, but it is sometimes less reliable. Switch this on if you experience crashes or other unusual problems while importing or viewing certain images. EDIT: OpenCV is much better these days--this is mostly not needed.' )
            
            self._use_system_ffmpeg = QW.QCheckBox( self )
            self._use_system_ffmpeg.setToolTip( 'Check this to always default to the system ffmpeg in your path, rather than using the static ffmpeg in hydrus\'s bin directory. (requires restart)' )
            
            self._always_loop_gifs = QW.QCheckBox( self )
            self._always_loop_gifs.setToolTip( 'Some GIFS have metadata specifying how many times they should be played, usually 1. Uncheck this to obey that number.' )
            
            self._media_viewer_cursor_autohide_time_ms = ClientGUICommon.NoneableSpinCtrl( self, none_phrase = 'do not autohide', min = 100, max = 100000, unit = 'ms' )
            
            self._anchor_and_hide_canvas_drags = QW.QCheckBox( self )
            self._touchscreen_canvas_drags_unanchor = QW.QCheckBox( self )
            
            from hydrus.client.gui import ClientGUICanvas
            
            self._media_viewer_zoom_center = ClientGUICommon.BetterChoice()
            
            for zoom_centerpoint_type in ClientGUICanvas.ZOOM_CENTERPOINT_TYPES:
                
                self._media_viewer_zoom_center.addItem( ClientGUICanvas.zoom_centerpoints_str_lookup[ zoom_centerpoint_type ], zoom_centerpoint_type )
                
            
            tt = 'When you zoom in or out, there is a centerpoint about which the image zooms. This point \'stays still\' while the image expands or shrinks around it. Different centerpoints give different feels, especially if you drag images around a bit.'
            
            self._media_viewer_zoom_center.setToolTip( tt )
            
            self._media_zooms = QW.QLineEdit( self )
            self._media_zooms.textChanged.connect( self.EventZoomsChanged )
            
            self._mpv_conf_path = QP.FilePickerCtrl( self, starting_directory = os.path.join( HC.STATIC_DIR, 'mpv-conf' ) )
            
            self._animated_scanbar_height = QP.MakeQSpinBox( self, min=1, max=255 )
            self._animated_scanbar_nub_width = QP.MakeQSpinBox( self, min=1, max=63 )
            
            self._media_viewer_panel = ClientGUICommon.StaticBox( self, 'media viewer mime handling' )
            
            media_viewer_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._media_viewer_panel )
            
            self._media_viewer_options = ClientGUIListCtrl.BetterListCtrl( media_viewer_list_panel, CGLC.COLUMN_LIST_MEDIA_VIEWER_OPTIONS.ID, 20, data_to_tuples_func = self._GetListCtrlData, activation_callback = self.EditMediaViewerOptions, use_simple_delete = True )
            
            media_viewer_list_panel.SetListCtrl( self._media_viewer_options )
            
            media_viewer_list_panel.AddButton( 'add', self.AddMediaViewerOptions, enabled_check_func = self._CanAddMediaViewOption )
            media_viewer_list_panel.AddButton( 'edit', self.EditMediaViewerOptions, enabled_only_on_selection = True )
            media_viewer_list_panel.AddDeleteButton( enabled_check_func = self._CanDeleteMediaViewOptions )
            
            #
            
            self._animation_start_position.setValue( int( HC.options['animation_start_position'] * 100.0 ) )
            self._disable_cv_for_gifs.setChecked( self._new_options.GetBoolean( 'disable_cv_for_gifs' ) )
            self._load_images_with_pil.setChecked( self._new_options.GetBoolean( 'load_images_with_pil' ) )
            self._use_system_ffmpeg.setChecked( self._new_options.GetBoolean( 'use_system_ffmpeg' ) )
            self._always_loop_gifs.setChecked( self._new_options.GetBoolean( 'always_loop_gifs' ) )
            self._media_viewer_cursor_autohide_time_ms.SetValue( self._new_options.GetNoneableInteger( 'media_viewer_cursor_autohide_time_ms' ) )
            self._anchor_and_hide_canvas_drags.setChecked( self._new_options.GetBoolean( 'anchor_and_hide_canvas_drags' ) )
            self._touchscreen_canvas_drags_unanchor.setChecked( self._new_options.GetBoolean( 'touchscreen_canvas_drags_unanchor' ) )
            self._animated_scanbar_height.setValue( self._new_options.GetInteger( 'animated_scanbar_height' ) )
            self._animated_scanbar_nub_width.setValue( self._new_options.GetInteger( 'animated_scanbar_nub_width' ) )
            
            self._media_viewer_zoom_center.SetValue( self._new_options.GetInteger( 'media_viewer_zoom_center' ) )
            
            media_zooms = self._new_options.GetMediaZooms()
            
            self._media_zooms.setText( ','.join( ( str( media_zoom ) for media_zoom in media_zooms ) ) )
            
            all_media_view_options = self._new_options.GetMediaViewOptions()
            
            for ( mime, view_options ) in all_media_view_options.items():
                
                data = QP.ListsToTuples( [ mime ] + list( view_options ) )
                
                self._media_viewer_options.AddDatas( ( data, ) )
                
            
            self._media_viewer_options.Sort()
            
            #
            
            vbox = QP.VBoxLayout()
            
            text = 'Please be warned that hydrus does not currently zoom in very efficiently at high zooms!'
            text += os.linesep
            text += 'Just be careful at >400%, particularly for already large files--it can lag out and eat a chunk of memory.'
            
            st = ClientGUICommon.BetterStaticText( self, text )
            st.setObjectName( 'HydrusWarning' )
            
            QP.AddToLayout( vbox, st )
            
            rows = []
            
            rows.append( ( 'Start animations this % in:', self._animation_start_position ) )
            rows.append( ( 'Prefer system FFMPEG:', self._use_system_ffmpeg ) )
            rows.append( ( 'Always Loop GIFs:', self._always_loop_gifs ) )
            rows.append( ( 'Centerpoint for media zooming:', self._media_viewer_zoom_center ) )
            rows.append( ( 'Media zooms:', self._media_zooms ) )
            rows.append( ( 'Set a new mpv.conf on dialog ok?:', self._mpv_conf_path ) )
            rows.append( ( 'Animation scanbar height:', self._animated_scanbar_height ) )
            rows.append( ( 'Animation scanbar nub width:', self._animated_scanbar_nub_width ) )
            rows.append( ( 'Time until mouse cursor autohides on media viewer:', self._media_viewer_cursor_autohide_time_ms ) )
            rows.append( ( 'RECOMMEND WINDOWS ONLY: Hide and anchor mouse cursor on media viewer drags:', self._anchor_and_hide_canvas_drags ) )
            rows.append( ( 'RECOMMEND WINDOWS ONLY: If set to hide and anchor, undo on apparent touchscreen drag:', self._touchscreen_canvas_drags_unanchor ) )
            rows.append( ( 'BUGFIX: Load images with PIL (slower):', self._load_images_with_pil ) )
            rows.append( ( 'BUGFIX: Load gifs with PIL instead of OpenCV (slower, bad transparency):', self._disable_cv_for_gifs ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self._media_viewer_panel.Add( media_viewer_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            QP.AddToLayout( vbox, self._media_viewer_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _CanAddMediaViewOption( self ):
            
            return len( self._GetUnsetMediaViewFiletypes() ) > 0
            
        
        def _CanDeleteMediaViewOptions( self ):
            
            deletable_mimes = set( HC.SEARCHABLE_MIMES )
            
            selected_mimes = set()
            
            for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._media_viewer_options.GetData( only_selected = True ):
                
                selected_mimes.add( mime )
                
            
            if len( selected_mimes ) == 0:
                
                return False
                
            
            all_selected_are_deletable = selected_mimes.issubset( deletable_mimes )
            
            return all_selected_are_deletable
            
        
        def _GetCopyOfGeneralMediaViewOptions( self, desired_mime ):
            
            general_mime_type = HC.mimes_to_general_mimetypes[ desired_mime ]
            
            for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._media_viewer_options.GetData():
                
                if mime == general_mime_type:
                    
                    view_options = ( desired_mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info )
                    
                    return view_options
                    
                
            
        
        def _GetUnsetMediaViewFiletypes( self ):
            
            editable_mimes = set( HC.SEARCHABLE_MIMES )
            
            set_mimes = set()
            
            for ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) in self._media_viewer_options.GetData():
                
                set_mimes.add( mime )
                
            
            unset_mimes = editable_mimes.difference( set_mimes )
            
            return unset_mimes
            
        
        def _GetListCtrlData( self, data ):
            
            ( mime, media_show_action, media_start_paused, media_start_with_embed, preview_show_action, preview_start_paused, preview_start_with_embed, zoom_info ) = data
            
            pretty_mime = self._GetPrettyMime( mime )
            
            pretty_media_show_action = CC.media_viewer_action_string_lookup[ media_show_action ]
            
            if media_start_paused:
                
                pretty_media_show_action += ', start paused'
                
            
            if media_start_with_embed:
                
                pretty_media_show_action += ', start with embed button'
                
            
            pretty_preview_show_action = CC.media_viewer_action_string_lookup[ preview_show_action ]
            
            if preview_start_paused:
                
                pretty_preview_show_action += ', start paused'
                
            
            if preview_start_with_embed:
                
                pretty_preview_show_action += ', start with embed button'
                
            
            no_show = len( set( ( media_show_action, preview_show_action ) ).intersection( { CC.MEDIA_VIEWER_ACTION_SHOW_WITH_NATIVE, CC.MEDIA_VIEWER_ACTION_SHOW_WITH_MPV } ) ) == 0
            
            if no_show:
                
                pretty_zoom_info = ''
                
            else:
                
                pretty_zoom_info = str( zoom_info )
                
            
            display_tuple = ( pretty_mime, pretty_media_show_action, pretty_preview_show_action, pretty_zoom_info )
            sort_tuple = ( pretty_mime, pretty_media_show_action, pretty_preview_show_action, pretty_zoom_info )
            
            return ( display_tuple, sort_tuple )
            
        
        def _GetPrettyMime( self, mime ):
            
            pretty_mime = HC.mime_string_lookup[ mime ]
            
            if mime not in HC.GENERAL_FILETYPES:
                
                pretty_mime = '{}: {}'.format( HC.mime_string_lookup[ HC.mimes_to_general_mimetypes[ mime ] ], pretty_mime )
                
            
            return pretty_mime
            
        
        def AddMediaViewerOptions( self ):
            
            unset_filetypes = self._GetUnsetMediaViewFiletypes()
            
            if len( unset_filetypes ) == 0:
                
                QW.QMessageBox.warning( self, 'Warning', 'You cannot add any more specific filetype options!' )
                
                return
                
            
            choice_tuples = [ ( self._GetPrettyMime( mime ), mime ) for mime in unset_filetypes ]
            
            try:
                
                mime = ClientGUIDialogsQuick.SelectFromList( self, 'select the filetype to add', choice_tuples, sort_tuples = True )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            data = self._GetCopyOfGeneralMediaViewOptions( mime )
            
            title = 'add media view options information'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIScrolledPanelsEdit.EditMediaViewOptionsPanel( dlg, data )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    new_data = panel.GetValue()
                    
                    self._media_viewer_options.AddDatas( ( new_data, ) )
                    
                
            
        
        def EditMediaViewerOptions( self ):
            
            for data in self._media_viewer_options.GetData( only_selected = True ):
                
                title = 'edit media view options information'
                
                with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsEdit.EditMediaViewOptionsPanel( dlg, data )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.exec() == QW.QDialog.Accepted:
                        
                        new_data = panel.GetValue()
                        
                        self._media_viewer_options.ReplaceData( data, new_data )
                        
                    
                
            
        
        def EventZoomsChanged( self, text ):
            
            try:
                
                media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.text().split( ',' ) ]
                
                self._media_zooms.setProperty( 'hydrus_text', 'default' )
                
            except ValueError:
                
                self._media_zooms.setObjectName( 'HydrusInvalid' )
                
            
            self._media_zooms.style().polish( self._media_zooms )
            
            self._media_zooms.update()
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'animation_start_position' ] = self._animation_start_position.value() / 100.0
            
            self._new_options.SetBoolean( 'disable_cv_for_gifs', self._disable_cv_for_gifs.isChecked() )
            self._new_options.SetBoolean( 'load_images_with_pil', self._load_images_with_pil.isChecked() )
            self._new_options.SetBoolean( 'use_system_ffmpeg', self._use_system_ffmpeg.isChecked() )
            self._new_options.SetBoolean( 'always_loop_gifs', self._always_loop_gifs.isChecked() )
            self._new_options.SetBoolean( 'anchor_and_hide_canvas_drags', self._anchor_and_hide_canvas_drags.isChecked() )
            self._new_options.SetBoolean( 'touchscreen_canvas_drags_unanchor', self._touchscreen_canvas_drags_unanchor.isChecked() )
            
            self._new_options.SetNoneableInteger( 'media_viewer_cursor_autohide_time_ms', self._media_viewer_cursor_autohide_time_ms.GetValue() )
            
            mpv_conf_path = self._mpv_conf_path.GetPath()
            
            if mpv_conf_path is not None and mpv_conf_path != '' and os.path.exists( mpv_conf_path ) and os.path.isfile( mpv_conf_path ):
                
                dest_mpv_conf_path = HG.client_controller.GetMPVConfPath()
                
                try:
                    
                    HydrusPaths.MirrorFile( mpv_conf_path, dest_mpv_conf_path )
                    
                except Exception as e:
                    
                    HydrusData.ShowText( 'Could not set the mpv conf path "{}" to "{}"! Error follows!'.format( mpv_conf_path, dest_mpv_conf_path ) )
                    HydrusData.ShowException( e )
                    
                
            
            self._new_options.SetInteger( 'animated_scanbar_height', self._animated_scanbar_height.value() )
            self._new_options.SetInteger( 'animated_scanbar_nub_width', self._animated_scanbar_nub_width.value() )
            
            self._new_options.SetInteger( 'media_viewer_zoom_center', self._media_viewer_zoom_center.GetValue() )
            
            try:
                
                media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.text().split( ',' ) ]
                
                media_zooms = [ media_zoom for media_zoom in media_zooms if media_zoom > 0.0 ]
                
                if len( media_zooms ) > 0:
                    
                    self._new_options.SetMediaZooms( media_zooms )
                    
                
            except ValueError:
                
                HydrusData.ShowText( 'Could not parse those zooms, so they were not saved!' )
                
            
            mimes_to_media_view_options = {}
            
            for data in self._media_viewer_options.GetData():
                
                data = list( data )
                
                mime = data[0]
                
                value = data[1:]
                
                mimes_to_media_view_options[ mime ] = value
                
            
            self._new_options.SetMediaViewOptions( mimes_to_media_view_options )
            
        
    
    class _RegexPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            regex_favourites = HC.options[ 'regex_favourites' ]
            
            self._regex_panel = ClientGUIScrolledPanelsEdit.EditRegexFavourites( self, regex_favourites )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, self._regex_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            regex_favourites = self._regex_panel.GetValue()
            
            HC.options[ 'regex_favourites' ] = regex_favourites
            
        
    
    class _SortCollectPanel( QW.QWidget ):
        
        def __init__( self, parent ):
            
            QW.QWidget.__init__( self, parent )
            
            self._default_media_sort = ClientGUISearch.MediaSortControl( self )
            
            self._fallback_media_sort = ClientGUISearch.MediaSortControl( self )
            
            self._save_page_sort_on_change = QW.QCheckBox( self )
            
            self._default_media_collect = ClientGUISearch.MediaCollectControl( self, silent = True )
            
            namespace_sorting_box = ClientGUICommon.StaticBox( self, 'namespace sorting' )
            
            self._namespace_sort_by = ClientGUIListBoxes.QueueListBox( namespace_sorting_box, 8, self._ConvertNamespaceTupleToSortString, self._AddNamespaceSort, self._EditNamespaceSort )
            
            #
            
            self._new_options = HG.client_controller.new_options
            
            try:
                
                self._default_media_sort.SetSort( self._new_options.GetDefaultSort() )
                
            except:
                
                media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
                
                self._default_media_sort.SetSort( media_sort )
                
            
            try:
                
                self._fallback_media_sort.SetSort( self._new_options.GetFallbackSort() )
                
            except:
                
                media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ), CC.SORT_ASC )
                
                self._fallback_media_sort.SetSort( media_sort )
                
            
            self._namespace_sort_by.AddDatas( [ tuple( sort_by ) for ( namespace_gumpf, sort_by ) in HC.options[ 'sort_by' ] ] )
            
            self._save_page_sort_on_change.setChecked( self._new_options.GetBoolean( 'save_page_sort_on_change' ) )
            
            #
            
            sort_by_text = 'You can manage your namespace sorting schemes here.'
            sort_by_text += os.linesep
            sort_by_text += 'The client will sort media by comparing their namespaces, moving from left to right until an inequality is found.'
            sort_by_text += os.linesep
            sort_by_text += 'Any namespaces here will also appear in your collect-by dropdowns.'
            
            namespace_sorting_box.Add( ClientGUICommon.BetterStaticText( namespace_sorting_box, sort_by_text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            namespace_sorting_box.Add( self._namespace_sort_by, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            rows = []
            
            rows.append( ( 'Default sort: ', self._default_media_sort ) )
            rows.append( ( 'Secondary sort (when primary gives two equal values): ', self._fallback_media_sort ) )
            rows.append( ( 'Update default sort every time a new sort is manually chosen: ', self._save_page_sort_on_change ) )
            rows.append( ( 'Default collect: ', self._default_media_collect ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            QP.AddToLayout( vbox, namespace_sorting_box, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def _AddNamespaceSort( self ):
            
            default = ( 'creator', 'series', 'page' )
            
            return self._EditNamespaceSort( default )
            
        
        def _ConvertNamespaceTupleToSortString( self, namespaces ):
            
            return '-'.join( namespaces )
            
        
        def _EditNamespaceSort( self, namespaces ):
            
            # users might want to add a namespace with a hyphen in it, so in lieu of a nice list to edit we'll just escape for now mate
            correct_char = '-'
            escaped_char = '\\-'
            
            escaped_namespaces = [ namespace.replace( correct_char, escaped_char ) for namespace in namespaces ]
            
            edit_string = '-'.join( escaped_namespaces )
            
            message = 'Write the namespaces you would like to sort by here, separated by hyphens. Any namespace in any of your sort definitions will be added to the collect-by menu.'
            message += os.linesep * 2
            message += 'If the namespace you want to add has a hyphen, like \'creator-id\', instead type it with a backslash escape, like \'creator\\-id-page\'.'
            
            with ClientGUIDialogs.DialogTextEntry( self, message, allow_blank = False, default = edit_string ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    edited_string = dlg.GetValue()
                    
                    edited_escaped_namespaces = re.split( r'(?<!\\)\-', edited_string )
                    
                    edited_namespaces = [ namespace.replace( escaped_char, correct_char ) for namespace in edited_escaped_namespaces ]
                    
                    edited_namespaces = [ HydrusTags.CleanTag( namespace ) for namespace in edited_namespaces if HydrusTags.TagOK( namespace ) ]
                    
                    if len( edited_namespaces ) > 0:
                        
                        return tuple( edited_namespaces )
                        
                    
                
                raise HydrusExceptions.VetoException()
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetDefaultSort( self._default_media_sort.GetSort() )
            self._new_options.SetFallbackSort( self._fallback_media_sort.GetSort() )
            self._new_options.SetBoolean( 'save_page_sort_on_change', self._save_page_sort_on_change.isChecked() )
            self._new_options.SetDefaultCollect( self._default_media_collect.GetValue() )
            
            sort_by_choices = [ ( 'namespaces', list( data ) ) for data in self._namespace_sort_by.GetData() ]
            
            HC.options[ 'sort_by' ] = sort_by_choices
            
        
    
    class _SpeedAndMemoryPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            disk_panel = ClientGUICommon.StaticBox( self, 'disk cache' )
            
            disk_cache_help_button = ClientGUICommon.BetterBitmapButton( disk_panel, CC.global_pixmaps().help, self._ShowDiskCacheHelp )
            disk_cache_help_button.setToolTip( 'Show help regarding the disk cache.' )
            
            help_hbox = ClientGUICommon.WrapInText( disk_cache_help_button, disk_panel, 'help for this panel -->', QG.QColor( 0, 0, 255 ) )
            
            self._disk_cache_init_period = ClientGUICommon.NoneableSpinCtrl( disk_panel, unit = 's', none_phrase = 'do not run', min = 1, max = 120 )
            self._disk_cache_init_period.setToolTip( 'When the client boots, it can speed up operation (particularly loading your session pages) by reading the front of its database into memory. This sets the max number of seconds it can spend doing that.' )
            
            self._disk_cache_maintenance = ClientGUIControls.NoneableBytesControl( disk_panel, initial_value = 256 * 1024 * 1024, none_label = 'do not keep db cached' )
            self._disk_cache_maintenance.setToolTip( 'The client can regularly ensure the front of its database is cached in your OS\'s disk cache. This represents how many megabytes it will ensure are cached in memory.' )
            
            #
            
            media_panel = ClientGUICommon.StaticBox( self, 'thumbnail size and media cache' )
            
            self._thumbnail_cache_size = QP.MakeQSpinBox( media_panel, min=5, max=3000 )
            self._thumbnail_cache_size.valueChanged.connect( self.EventThumbnailsUpdate )
            
            self._estimated_number_thumbnails = QW.QLabel( '', media_panel )
            
            self._fullscreen_cache_size = QP.MakeQSpinBox( media_panel, min=25, max=8192 )
            self._fullscreen_cache_size.valueChanged.connect( self.EventFullscreensUpdate )
            
            self._estimated_number_fullscreens = QW.QLabel( '', media_panel )
            
            self._thumbnail_cache_timeout = ClientGUITime.TimeDeltaButton( media_panel, min = 300, days = True, hours = True, minutes = True )
            self._thumbnail_cache_timeout.setToolTip( 'The amount of time after which a thumbnail in the cache will naturally be removed, if it is not shunted out due to a new member exceeding the size limit. Requires restart to kick in.' )
            
            self._image_cache_timeout = ClientGUITime.TimeDeltaButton( media_panel, min = 300, days = True, hours = True, minutes = True )
            self._image_cache_timeout.setToolTip( 'The amount of time after which a rendered image in the cache will naturally be removed, if it is not shunted out due to a new member exceeding the size limit. Requires restart to kick in.' )
            
            #
            
            buffer_panel = ClientGUICommon.StaticBox( self, 'video buffer' )
            
            self._video_buffer_size_mb = QP.MakeQSpinBox( buffer_panel, min=48, max=16*1024 )
            self._video_buffer_size_mb.valueChanged.connect( self.EventVideoBufferUpdate )
            
            self._estimated_number_video_frames = QW.QLabel( '', buffer_panel )
            
            #
            
            ac_panel = ClientGUICommon.StaticBox( self, 'tag autocomplete' )
            
            self._autocomplete_results_fetch_automatically = QW.QCheckBox( ac_panel )
            
            self._autocomplete_exact_match_threshold = ClientGUICommon.NoneableSpinCtrl( ac_panel, none_phrase = 'always do full search', min = 1, max = 1024 )
            self._autocomplete_exact_match_threshold.setToolTip( 'If the search input has this many characters or fewer, it will fetch exact results rather than full autocomplete results.' )
            
            #
            
            misc_panel = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._forced_search_limit = ClientGUICommon.NoneableSpinCtrl( misc_panel, '', min = 1, max = 100000 )
            
            #
            
            self._disk_cache_init_period.SetValue( self._new_options.GetNoneableInteger( 'disk_cache_init_period' ) )
            
            disk_cache_maintenance_mb = self._new_options.GetNoneableInteger( 'disk_cache_maintenance_mb' )
            
            if disk_cache_maintenance_mb is None:
                
                disk_cache_maintenance = disk_cache_maintenance_mb
                
            else:
                
                disk_cache_maintenance = disk_cache_maintenance_mb * 1024 * 1024
                
            
            self._disk_cache_maintenance.SetValue( disk_cache_maintenance )
            
            self._thumbnail_cache_size.setValue( int( HC.options['thumbnail_cache_size'] // 1048576 ) )
            
            self._fullscreen_cache_size.setValue( int( HC.options['fullscreen_cache_size'] // 1048576 ) )
            
            self._thumbnail_cache_timeout.SetValue( self._new_options.GetInteger( 'thumbnail_cache_timeout' ) )
            self._image_cache_timeout.SetValue( self._new_options.GetInteger( 'image_cache_timeout' ) )
            
            self._video_buffer_size_mb.setValue( self._new_options.GetInteger( 'video_buffer_size_mb' ) )
            
            self._autocomplete_results_fetch_automatically.setChecked( self._new_options.GetBoolean( 'autocomplete_results_fetch_automatically' ) )
            
            self._autocomplete_exact_match_threshold.SetValue( self._new_options.GetNoneableInteger( 'autocomplete_exact_match_threshold' ) )
            
            self._forced_search_limit.SetValue( self._new_options.GetNoneableInteger( 'forced_search_limit' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'run disk cache on boot for this long: ', self._disk_cache_init_period ) )
            rows.append( ( 'regularly ensure this much of the db is in OS\'s disk cache: ', self._disk_cache_maintenance ) )
            
            gridbox = ClientGUICommon.WrapInGrid( disk_panel, rows )
            
            vbox = QP.VBoxLayout()
            
            disk_panel.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
            disk_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, disk_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            thumbnails_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( thumbnails_sizer, self._thumbnail_cache_size, CC.FLAGS_VCENTER )
            QP.AddToLayout( thumbnails_sizer, self._estimated_number_thumbnails, CC.FLAGS_VCENTER )
            
            fullscreens_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( fullscreens_sizer, self._fullscreen_cache_size, CC.FLAGS_VCENTER )
            QP.AddToLayout( fullscreens_sizer, self._estimated_number_fullscreens, CC.FLAGS_VCENTER )
            
            video_buffer_sizer = QP.HBoxLayout()
            
            QP.AddToLayout( video_buffer_sizer, self._video_buffer_size_mb, CC.FLAGS_VCENTER )
            QP.AddToLayout( video_buffer_sizer, self._estimated_number_video_frames, CC.FLAGS_VCENTER )
            
            rows = []
            
            rows.append( ( 'MB memory reserved for thumbnail cache: ', thumbnails_sizer ) )
            rows.append( ( 'MB memory reserved for image cache: ', fullscreens_sizer ) )
            rows.append( ( 'Thumbnail cache timeout: ', self._thumbnail_cache_timeout ) )
            rows.append( ( 'Image cache timeout: ', self._image_cache_timeout ) )
            
            gridbox = ClientGUICommon.WrapInGrid( media_panel, rows )
            
            media_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, media_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'Hydrus video rendering is CPU intensive.'
            text += os.linesep
            text += 'If you have a lot of memory, you can set a generous potential video buffer to compensate.'
            text += os.linesep
            text += 'If the video buffer can hold an entire video, it only needs to be rendered once and will play and loop very smoothly.'
            text += os.linesep
            text += 'PROTIP: Do not go crazy here.'
            
            buffer_panel.Add( QW.QLabel( text, buffer_panel ), CC.FLAGS_VCENTER )
            
            rows = []
            
            rows.append( ( 'MB memory for video buffer: ', video_buffer_sizer ) )
            
            gridbox = ClientGUICommon.WrapInGrid( buffer_panel, rows )
            
            buffer_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, buffer_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'If you disable automatic autocomplete results fetching, use Ctrl+Space to fetch results manually.'
            
            ac_panel.Add( QW.QLabel( text, ac_panel ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Automatically fetch autocomplete results: ', self._autocomplete_results_fetch_automatically ) )
            rows.append( ( 'Fetch exact match results if input has <= this many characters: ', self._autocomplete_exact_match_threshold ) )
            
            gridbox = ClientGUICommon.WrapInGrid( ac_panel, rows )
            
            ac_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, ac_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Forced system:limit for all searches: ', self._forced_search_limit ) )
            
            gridbox = ClientGUICommon.WrapInGrid( misc_panel, rows )
            
            misc_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, misc_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
            #
            
            self.EventFullscreensUpdate( self._fullscreen_cache_size.value() )
            self.EventThumbnailsUpdate( self._thumbnail_cache_size.value() )
            self.EventVideoBufferUpdate( self._video_buffer_size_mb.value() )
            
        
        def _ShowDiskCacheHelp( self ):
            
            message = 'NO NEED TO USE THESE IF YOU RUN ON AN SSD.'
            message += os.linesep * 2
            message += 'The hydrus database runs best on a drive with fast random access latency. Certain important operations can function up to 100 times faster when started raw from an SSD rather than an HDD.'
            message += os.linesep * 2
            message += 'If you are on an HDD, the client can populate a pre-boot and ongoing disk cache. By contiguously frontloading the database into memory, the most important functions do not need to wait on your disk for most of their work.'
            message += os.linesep * 2
            message += 'Try 2 to 10 seconds boot cache, and 256-512MB ongoing disk cache.'
            message += os.linesep * 2
            message += 'Unless you are testing, do not go crazy with this stuff. You can set 8192MB if you like, but there are diminishing (and potentially negative) returns.'
            
            QW.QMessageBox.information( self, 'Information', message )
            
        
        def EventFullscreensUpdate( self, value ):
            
            display_size = ClientGUIFunctions.GetDisplaySize( self )
            
            estimated_bytes_per_fullscreen = 3 * display_size.width() * display_size.height()
            
            estimate = ( value * 1048576 ) // estimated_bytes_per_fullscreen
            
            self._estimated_number_fullscreens.setText( '(about {}-{} images)'.format( HydrusData.ToHumanInt( estimate ), HydrusData.ToHumanInt( estimate * 4 ) ) )
            
        
        def EventThumbnailsUpdate( self, value ):
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            res_string = HydrusData.ConvertResolutionToPrettyString( ( thumbnail_width, thumbnail_height ) )
            
            estimated_bytes_per_thumb = 3 * thumbnail_width * thumbnail_height
            
            estimated_thumbs = ( value * 1024 * 1024 ) // estimated_bytes_per_thumb
            
            self._estimated_number_thumbnails.setText( '(at '+res_string+', about '+HydrusData.ToHumanInt(estimated_thumbs)+' thumbnails)' )
            
        
        def EventVideoBufferUpdate( self, value ):
            
            estimated_720p_frames = int( ( value * 1024 * 1024 ) // ( 1280 * 720 * 3 ) )
            
            self._estimated_number_video_frames.setText( '(about '+HydrusData.ToHumanInt(estimated_720p_frames)+' frames of 720p video)' )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetNoneableInteger( 'disk_cache_init_period', self._disk_cache_init_period.GetValue() )
            
            disk_cache_maintenance = self._disk_cache_maintenance.GetValue()
            
            if disk_cache_maintenance is None:
                
                disk_cache_maintenance_mb = disk_cache_maintenance
                
            else:
                
                disk_cache_maintenance_mb = disk_cache_maintenance // ( 1024 * 1024 )
                
            
            self._new_options.SetNoneableInteger( 'disk_cache_maintenance_mb', disk_cache_maintenance_mb )
            
            HC.options[ 'thumbnail_cache_size' ] = self._thumbnail_cache_size.value() * 1048576
            HC.options[ 'fullscreen_cache_size' ] = self._fullscreen_cache_size.value() * 1048576
            
            self._new_options.SetInteger( 'thumbnail_cache_timeout', self._thumbnail_cache_timeout.GetValue() )
            self._new_options.SetInteger( 'image_cache_timeout', self._image_cache_timeout.GetValue() )
            
            self._new_options.SetInteger( 'video_buffer_size_mb', self._video_buffer_size_mb.value() )
            
            self._new_options.SetNoneableInteger( 'forced_search_limit', self._forced_search_limit.GetValue() )
            
            self._new_options.SetBoolean( 'autocomplete_results_fetch_automatically', self._autocomplete_results_fetch_automatically.isChecked() )
            self._new_options.SetNoneableInteger( 'autocomplete_exact_match_threshold', self._autocomplete_exact_match_threshold.GetValue() )
            
        
    
    class _StylePanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            self._qt_style_name = ClientGUICommon.BetterChoice( self )
            self._qt_stylesheet_name = ClientGUICommon.BetterChoice( self )
            
            self._qt_style_name.addItem( 'use default ("{}")'.format( ClientGUIStyle.ORIGINAL_STYLE_NAME ), None )
            
            try:
                
                for name in ClientGUIStyle.GetAvailableStyles():
                    
                    self._qt_style_name.addItem( name, name )
                    
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.ShowException( e )
                
            
            self._qt_stylesheet_name.addItem( 'use default', None )
            
            try:
                
                for name in ClientGUIStyle.GetAvailableStylesheets():
                    
                    self._qt_stylesheet_name.addItem( name, name )
                    
                
            except HydrusExceptions.DataMissing as e:
                
                HydrusData.ShowException( e )
                
            
            #
            
            self._qt_style_name.SetValue( self._new_options.GetNoneableString( 'qt_style_name' ) )
            self._qt_stylesheet_name.SetValue( self._new_options.GetNoneableString( 'qt_stylesheet_name' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            #
            
            text = 'The current styles are what your Qt has available, the stylesheets are what .css and .qss files are currently in install_dir/static/qss.'
            
            st = ClientGUICommon.BetterStaticText( self, label = text )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Qt style:', self._qt_style_name ) )
            rows.append( ( 'Qt stylesheet:', self._qt_stylesheet_name ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
            self._qt_style_name.currentIndexChanged.connect( self.StyleChanged )
            self._qt_stylesheet_name.currentIndexChanged.connect( self.StyleChanged )
            
        
        def StyleChanged( self ):
            
            qt_style_name = self._qt_style_name.GetValue()
            qt_stylesheet_name = self._qt_stylesheet_name.GetValue()
            
            try:
                
                if qt_style_name is None:
                    
                    ClientGUIStyle.SetStyleFromName( ClientGUIStyle.ORIGINAL_STYLE_NAME )
                    
                else:
                    
                    ClientGUIStyle.SetStyleFromName( qt_style_name )
                    
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Critical', 'Could not apply style: {}'.format( str( e ) ) )
                
            
            try:
                
                if qt_stylesheet_name is None:
                    
                    ClientGUIStyle.ClearStylesheet()
                    
                else:
                    
                    ClientGUIStyle.SetStylesheetFromPath( qt_stylesheet_name )
                    
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Critical', 'Could not apply stylesheet: {}'.format( str( e ) ) )
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetNoneableString( 'qt_style_name', self._qt_style_name.GetValue() )
            self._new_options.SetNoneableString( 'qt_stylesheet_name', self._qt_stylesheet_name.GetValue() )
            
        
    
    class _SystemTrayPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            self._always_show_system_tray_icon = QW.QCheckBox( self )
            self._minimise_client_to_system_tray = QW.QCheckBox( self )
            self._close_client_to_system_tray = QW.QCheckBox( self )
            self._start_client_in_system_tray = QW.QCheckBox( self )
            
            #
            
            self._always_show_system_tray_icon.setChecked( self._new_options.GetBoolean( 'always_show_system_tray_icon' ) )
            self._minimise_client_to_system_tray.setChecked( self._new_options.GetBoolean( 'minimise_client_to_system_tray' ) )
            self._close_client_to_system_tray.setChecked( self._new_options.GetBoolean( 'close_client_to_system_tray' ) )
            self._start_client_in_system_tray.setChecked( self._new_options.GetBoolean( 'start_client_in_system_tray' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Always show the hydrus system tray icon: ', self._always_show_system_tray_icon ) )
            rows.append( ( 'Minimise the main window to system tray: ', self._minimise_client_to_system_tray ) )
            rows.append( ( 'Close the main window to system tray: ', self._close_client_to_system_tray ) )
            rows.append( ( 'Start the client minimised to system tray: ', self._start_client_in_system_tray ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            from hydrus.client.gui import ClientGUISystemTray
            
            if not ClientGUISystemTray.SystemTrayAvailable():
                
                QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, 'Unfortunately, your system does not seem to have a supported system tray.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
                
                self._always_show_system_tray_icon.setEnabled( False )
                self._minimise_client_to_system_tray.setEnabled( False )
                self._close_client_to_system_tray.setEnabled( False )
                self._start_client_in_system_tray.setEnabled( False )
                
            elif not HC.PLATFORM_WINDOWS:
                
                if not HG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
                    
                    label = 'This is turned off for non-advanced non-Windows users for now.'
                    
                    self._always_show_system_tray_icon.setEnabled( False )
                    self._minimise_client_to_system_tray.setEnabled( False )
                    self._close_client_to_system_tray.setEnabled( False )
                    self._start_client_in_system_tray.setEnabled( False )
                    
                else:
                    
                    label = 'This can be buggy/crashy on non-Windows, hydev will keep working on this.'
                    
                
                QP.AddToLayout( vbox, ClientGUICommon.BetterStaticText( self, label ), CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( vbox, QW.QWidget( self ), CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'always_show_system_tray_icon', self._always_show_system_tray_icon.isChecked() )
            self._new_options.SetBoolean( 'minimise_client_to_system_tray', self._minimise_client_to_system_tray.isChecked() )
            self._new_options.SetBoolean( 'close_client_to_system_tray', self._close_client_to_system_tray.isChecked() )
            self._new_options.SetBoolean( 'start_client_in_system_tray', self._start_client_in_system_tray.isChecked() )
            
        
    
    class _TagsPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            general_panel = ClientGUICommon.StaticBox( self, 'general tag options' )
            
            self._default_tag_sort = ClientGUICommon.BetterChoice( general_panel )
            
            self._default_tag_sort.addItem( 'lexicographic (a-z)', CC.SORT_BY_LEXICOGRAPHIC_ASC )
            self._default_tag_sort.addItem( 'lexicographic (z-a)', CC.SORT_BY_LEXICOGRAPHIC_DESC )
            self._default_tag_sort.addItem( 'lexicographic (a-z) (group unnamespaced)', CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC )
            self._default_tag_sort.addItem( 'lexicographic (z-a) (group unnamespaced)', CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC )
            self._default_tag_sort.addItem( 'lexicographic (a-z) (ignore namespace)', CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_ASC )
            self._default_tag_sort.addItem( 'lexicographic (z-a) (ignore namespace)', CC.SORT_BY_LEXICOGRAPHIC_IGNORE_NAMESPACE_DESC )
            self._default_tag_sort.addItem( 'incidence (desc)', CC.SORT_BY_INCIDENCE_DESC )
            self._default_tag_sort.addItem( 'incidence (asc)', CC.SORT_BY_INCIDENCE_ASC )
            self._default_tag_sort.addItem( 'incidence (desc) (grouped by namespace)', CC.SORT_BY_INCIDENCE_NAMESPACE_DESC )
            self._default_tag_sort.addItem( 'incidence (asc) (grouped by namespace)', CC.SORT_BY_INCIDENCE_NAMESPACE_ASC )
            
            self._default_tag_repository = ClientGUICommon.BetterChoice( general_panel )
            
            self._default_tag_service_search_page = ClientGUICommon.BetterChoice( general_panel )
            
            self._ac_select_first_with_count = QW.QCheckBox( general_panel )
            
            self._apply_all_parents_to_all_services = QW.QCheckBox( general_panel )
            self._apply_all_siblings_to_all_services = QW.QCheckBox( general_panel )
            
            self._apply_all_parents_to_all_services.setToolTip( 'If checked, all services will apply their tag parents to each other. If unchecked, services will only apply tag parents to themselves.' )
            self._apply_all_siblings_to_all_services.setToolTip( 'If checked, all services will apply their tag siblings to each other. If unchecked, services will only apply tag siblings to themselves. In case of conflict, local tag services have precedence.' )
            
            #
            
            favourites_panel = ClientGUICommon.StaticBox( self, 'favourite tags' )
            
            desc = 'These tags will appear in your tag autocomplete results area, under the \'favourites\' tab.'
            
            favourites_st = ClientGUICommon.BetterStaticText( favourites_panel, desc )
            favourites_st.setWordWrap( True )
            
            expand_parents = False
            
            self._favourites = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( favourites_panel )
            self._favourites_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( favourites_panel, self._favourites.AddTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, CC.COMBINED_TAG_SERVICE_KEY, tag_service_key_changed_callable = self._favourites.SetTagServiceKey, show_paste_button = True )
            
            #
            
            self._default_tag_sort.SetValue( HC.options[ 'default_tag_sort' ] )
            
            self._default_tag_service_search_page.addItem( 'all known tags', CC.COMBINED_TAG_SERVICE_KEY )
            
            services = HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
            
            for service in services:
                
                self._default_tag_repository.addItem( service.GetName(), service.GetServiceKey() )
                
                self._default_tag_service_search_page.addItem( service.GetName(), service.GetServiceKey() )
                
            
            default_tag_repository_key = HC.options[ 'default_tag_repository' ]
            
            self._default_tag_repository.SetValue( default_tag_repository_key )
            
            self._default_tag_service_search_page.SetValue( new_options.GetKey( 'default_tag_service_search_page' ) )
            
            self._ac_select_first_with_count.setChecked( self._new_options.GetBoolean( 'ac_select_first_with_count' ) )
            
            self._apply_all_parents_to_all_services.setChecked( self._new_options.GetBoolean( 'apply_all_parents_to_all_services' ) )
            self._apply_all_siblings_to_all_services.setChecked( self._new_options.GetBoolean( 'apply_all_siblings_to_all_services' ) )
            
            #
            
            self._favourites.SetTags( new_options.GetStringList( 'favourite_tags' ) )
            
            #
            
            vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Default tag service in manage tag dialogs: ', self._default_tag_repository ) )
            rows.append( ( 'Default tag service in search pages: ', self._default_tag_service_search_page ) )
            rows.append( ( 'Default tag sort: ', self._default_tag_sort ) )
            rows.append( ( 'By default, select the first tag result with actual count in write-autocomplete: ', self._ac_select_first_with_count ) )
            rows.append( ( 'Apply all parents for all services: ', self._apply_all_parents_to_all_services ) )
            rows.append( ( 'Apply all siblings to all services (local siblings have precedence): ', self._apply_all_siblings_to_all_services ) )
            
            gridbox = ClientGUICommon.WrapInGrid( general_panel, rows )
            
            general_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, general_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            favourites_panel.Add( favourites_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            favourites_panel.Add( self._favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
            favourites_panel.Add( self._favourites_input )
            
            QP.AddToLayout( vbox, favourites_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'default_tag_repository' ] = self._default_tag_repository.GetValue()
            HC.options[ 'default_tag_sort' ] = QP.GetClientData( self._default_tag_sort, self._default_tag_sort.currentIndex() )
            
            self._new_options.SetBoolean( 'ac_select_first_with_count', self._ac_select_first_with_count.isChecked() )
            
            self._new_options.SetKey( 'default_tag_service_search_page', self._default_tag_service_search_page.GetValue() )
            
            self._new_options.SetBoolean( 'apply_all_parents_to_all_services', self._apply_all_parents_to_all_services.isChecked() )
            self._new_options.SetBoolean( 'apply_all_siblings_to_all_services', self._apply_all_siblings_to_all_services.isChecked() )
            
            #
            
            self._new_options.SetStringList( 'favourite_tags', list( self._favourites.GetTags() ) )
            
        
    
    class _TagPresentationPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_top' )
            
            self._thumbnail_top = ClientGUIScrolledPanelsEdit.TagSummaryGeneratorButton( self, tag_summary_generator )
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_bottom_right' )
            
            self._thumbnail_bottom_right = ClientGUIScrolledPanelsEdit.TagSummaryGeneratorButton( self, tag_summary_generator )
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'media_viewer_top' )
            
            self._media_viewer_top = ClientGUIScrolledPanelsEdit.TagSummaryGeneratorButton( self, tag_summary_generator )
            
            #
            
            render_panel = ClientGUICommon.StaticBox( self, 'namespace rendering' )
            
            render_st = ClientGUICommon.BetterStaticText( render_panel, label = 'Namespaced tags are stored and directly edited in hydrus as "namespace:subtag", but most presentation windows can display them differently.' )
            
            self._show_namespaces = QW.QCheckBox( render_panel )
            self._namespace_connector = QW.QLineEdit( render_panel )
            
            #
            
            namespace_colours_panel = ClientGUICommon.StaticBox( self, 'namespace colours' )
            
            self._namespace_colours = ClientGUIListBoxes.ListBoxTagsColourOptions( namespace_colours_panel, HC.options[ 'namespace_colours' ] )
            
            self._edit_namespace_colour = QW.QPushButton( 'edit selected', namespace_colours_panel )
            self._edit_namespace_colour.clicked.connect( self.EventEditNamespaceColour )
            
            self._new_namespace_colour = QW.QLineEdit( namespace_colours_panel )
            self._new_namespace_colour.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self._new_namespace_colour, self.AddNamespaceColour ) )
            
            #
            
            self._show_namespaces.setChecked( new_options.GetBoolean( 'show_namespaces' ) )
            self._namespace_connector.setText( new_options.GetString( 'namespace_connector' ) )
            
            #
            
            namespace_colours_panel.Add( self._namespace_colours, CC.FLAGS_EXPAND_BOTH_WAYS )
            namespace_colours_panel.Add( self._new_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            namespace_colours_panel.Add( self._edit_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            vbox = QP.VBoxLayout()
            
            #
            
            rows = []
            
            rows.append( ( 'On thumbnail top:', self._thumbnail_top ) )
            rows.append( ( 'On thumbnail bottom-right:', self._thumbnail_bottom_right ) )
            rows.append( ( 'On media viewer top:', self._media_viewer_top ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Show namespaces: ', self._show_namespaces ) )
            rows.append( ( 'If shown, namespace connecting string: ', self._namespace_connector ) )
            
            gridbox = ClientGUICommon.WrapInGrid( render_panel, rows )
            
            render_panel.Add( render_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            render_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            QP.AddToLayout( vbox, render_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            QP.AddToLayout( vbox, namespace_colours_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            self.setLayout( vbox )
            
        
        def EventEditNamespaceColour( self ):
            
            results = self._namespace_colours.GetSelectedNamespaceColours()
            
            for ( namespace, ( r, g, b ) ) in list( results.items() ):
                
                colour = QG.QColor( r, g, b )
                
                colour = QW.QColorDialog.getColor( colour, self, 'Namespace colour', QW.QColorDialog.ShowAlphaChannel )
                
                if colour.isValid():
                
                    self._namespace_colours.SetNamespaceColour( namespace, colour )
                    
                
            
        
        def AddNamespaceColour( self ):
            
            namespace = self._new_namespace_colour.text()
            
            if namespace != '':
                
                self._namespace_colours.SetNamespaceColour( namespace, QG.QColor( random.randint(0,255), random.randint(0,255), random.randint(0,255) ) )
                
                self._new_namespace_colour.setText( '' )
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetTagSummaryGenerator( 'thumbnail_top', self._thumbnail_top.GetValue() )
            self._new_options.SetTagSummaryGenerator( 'thumbnail_bottom_right', self._thumbnail_bottom_right.GetValue() )
            self._new_options.SetTagSummaryGenerator( 'media_viewer_top', self._media_viewer_top.GetValue() )
            
            self._new_options.SetBoolean( 'show_namespaces', self._show_namespaces.isChecked() )
            self._new_options.SetString( 'namespace_connector', self._namespace_connector.text() )
            
            HC.options[ 'namespace_colours' ] = self._namespace_colours.GetNamespaceColours()
            
        
    
    class _TagSuggestionsPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            suggested_tags_panel = ClientGUICommon.StaticBox( self, 'suggested tags' )
            
            self._suggested_tags_width = QP.MakeQSpinBox( suggested_tags_panel, min=20, max=65535 )
            
            self._suggested_tags_layout = ClientGUICommon.BetterChoice( suggested_tags_panel )
            
            self._suggested_tags_layout.addItem( 'notebook', 'notebook' )
            self._suggested_tags_layout.addItem( 'side-by-side', 'columns' )
            
            suggest_tags_panel_notebook = QW.QTabWidget( suggested_tags_panel )
            
            #
            
            suggested_tags_favourites_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            suggested_tags_favourites_panel.setMinimumWidth( 400 )
            
            self._suggested_favourites_services = ClientGUICommon.BetterChoice( suggested_tags_favourites_panel )
            
            tag_services = HG.client_controller.services_manager.GetServices( HC.REAL_TAG_SERVICES )
            
            for tag_service in tag_services:
                
                self._suggested_favourites_services.addItem( tag_service.GetName(), tag_service.GetServiceKey() )
                
            
            self._suggested_favourites = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( suggested_tags_favourites_panel )
            
            self._current_suggested_favourites_service = None
            
            self._suggested_favourites_dict = {}
            
            expand_parents = False
            
            self._suggested_favourites_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( suggested_tags_favourites_panel, self._suggested_favourites.AddTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, CC.COMBINED_TAG_SERVICE_KEY, tag_service_key_changed_callable = self._suggested_favourites.SetTagServiceKey, show_paste_button = True )
            
            #
            
            suggested_tags_related_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            self._show_related_tags = QW.QCheckBox( suggested_tags_related_panel )
            
            self._related_tags_search_1_duration_ms = QP.MakeQSpinBox( suggested_tags_related_panel, min=50, max=60000 )
            self._related_tags_search_2_duration_ms = QP.MakeQSpinBox( suggested_tags_related_panel, min=50, max=60000 )
            self._related_tags_search_3_duration_ms = QP.MakeQSpinBox( suggested_tags_related_panel, min=50, max=60000 )
            
            #
            
            suggested_tags_file_lookup_script_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            self._show_file_lookup_script_tags = QW.QCheckBox( suggested_tags_file_lookup_script_panel )
            
            self._favourite_file_lookup_script = ClientGUICommon.BetterChoice( suggested_tags_file_lookup_script_panel )
            
            script_names = sorted( HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP ) )
            
            for name in script_names:
                
                self._favourite_file_lookup_script.addItem( name, name )
                
            
            #
            
            suggested_tags_recent_panel = QW.QWidget( suggest_tags_panel_notebook )
            
            self._num_recent_tags = ClientGUICommon.NoneableSpinCtrl( suggested_tags_recent_panel, 'number of recent tags to show', min = 1, none_phrase = 'do not show' )
            
            #
            
            self._suggested_tags_width.setValue( self._new_options.GetInteger( 'suggested_tags_width' ) )
            
            self._suggested_tags_layout.SetValue( self._new_options.GetNoneableString( 'suggested_tags_layout' ) )
            
            self._show_related_tags.setChecked( self._new_options.GetBoolean( 'show_related_tags' ) )
            
            self._related_tags_search_1_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_1_duration_ms' ) )
            self._related_tags_search_2_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_2_duration_ms' ) )
            self._related_tags_search_3_duration_ms.setValue( self._new_options.GetInteger( 'related_tags_search_3_duration_ms' ) )
            
            self._show_file_lookup_script_tags.setChecked( self._new_options.GetBoolean( 'show_file_lookup_script_tags' ) )
            
            self._favourite_file_lookup_script.SetValue( self._new_options.GetNoneableString( 'favourite_file_lookup_script' ) )
            
            self._num_recent_tags.SetValue( self._new_options.GetNoneableInteger( 'num_recent_tags' ) )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            QP.AddToLayout( panel_vbox, self._suggested_favourites_services, CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( panel_vbox, self._suggested_favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( panel_vbox, self._suggested_favourites_input, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_favourites_panel.setLayout( panel_vbox )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Show related tags on single-file manage tags windows: ', self._show_related_tags ) )
            rows.append( ( 'Initial search duration (ms): ', self._related_tags_search_1_duration_ms ) )
            rows.append( ( 'Medium search duration (ms): ', self._related_tags_search_2_duration_ms ) )
            rows.append( ( 'Thorough search duration (ms): ', self._related_tags_search_3_duration_ms ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_related_panel, rows )
            
            desc = 'This will search the database for statistically related tags based on what your focused file already has.'
            
            QP.AddToLayout( panel_vbox, ClientGUICommon.BetterStaticText(suggested_tags_related_panel,desc), CC.FLAGS_EXPAND_PERPENDICULAR )
            QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            suggested_tags_related_panel.setLayout( panel_vbox )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            rows = []
            
            rows.append( ( 'Show file lookup scripts on single-file manage tags windows: ', self._show_file_lookup_script_tags ) )
            rows.append( ( 'Favourite file lookup script: ', self._favourite_file_lookup_script ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_file_lookup_script_panel, rows )
            
            QP.AddToLayout( panel_vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            suggested_tags_file_lookup_script_panel.setLayout( panel_vbox )
            
            #
            
            panel_vbox = QP.VBoxLayout()
            
            QP.AddToLayout( panel_vbox, self._num_recent_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            panel_vbox.addStretch( 1 )
            
            suggested_tags_recent_panel.setLayout( panel_vbox )
            
            #
            
            suggest_tags_panel_notebook.addTab( suggested_tags_favourites_panel, 'favourites' )
            suggest_tags_panel_notebook.addTab( suggested_tags_related_panel, 'related' )
            suggest_tags_panel_notebook.addTab( suggested_tags_file_lookup_script_panel, 'file lookup scripts' )
            suggest_tags_panel_notebook.addTab( suggested_tags_recent_panel, 'recent' )
            
            #
            
            rows = []
            
            rows.append( ( 'Width of suggested tags columns: ', self._suggested_tags_width ) )
            rows.append( ( 'Column layout: ', self._suggested_tags_layout ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_panel, rows )
            
            desc = 'The manage tags dialog can provide several kinds of tag suggestions. For simplicity, most are turned off by default.'
            
            suggested_tags_panel.Add( ClientGUICommon.BetterStaticText( suggested_tags_panel, desc ), CC.FLAGS_EXPAND_PERPENDICULAR )
            suggested_tags_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            suggested_tags_panel.Add( suggest_tags_panel_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, suggested_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.setLayout( vbox )
            
            #
            
            self._suggested_favourites_services.currentIndexChanged.connect( self.EventSuggestedFavouritesService )
            
            self.EventSuggestedFavouritesService( None )
            
        
        def _SaveCurrentSuggestedFavourites( self ):
            
            if self._current_suggested_favourites_service is not None:
                
                self._suggested_favourites_dict[ self._current_suggested_favourites_service ] = self._suggested_favourites.GetTags()
                
            
        
        def EventSuggestedFavouritesService( self, index ):
            
            self._SaveCurrentSuggestedFavourites()
            
            self._current_suggested_favourites_service = self._suggested_favourites_services.GetValue()
            
            if self._current_suggested_favourites_service in self._suggested_favourites_dict:
                
                favourites = self._suggested_favourites_dict[ self._current_suggested_favourites_service ]
                
            else:
                
                favourites = self._new_options.GetSuggestedTagsFavourites( self._current_suggested_favourites_service )
                
            
            self._suggested_favourites.SetTags( favourites )
            
            self._suggested_favourites_input.SetTagService( self._current_suggested_favourites_service )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetInteger( 'suggested_tags_width', self._suggested_tags_width.value() )
            self._new_options.SetNoneableString( 'suggested_tags_layout', self._suggested_tags_layout.GetValue() )
            
            self._SaveCurrentSuggestedFavourites()
            
            for ( service_key, favourites ) in list(self._suggested_favourites_dict.items()):
                
                self._new_options.SetSuggestedTagsFavourites( service_key, favourites )
                
            
            self._new_options.SetBoolean( 'show_related_tags', self._show_related_tags.isChecked() )
            
            self._new_options.SetInteger( 'related_tags_search_1_duration_ms', self._related_tags_search_1_duration_ms.value() )
            self._new_options.SetInteger( 'related_tags_search_2_duration_ms', self._related_tags_search_2_duration_ms.value() )
            self._new_options.SetInteger( 'related_tags_search_3_duration_ms', self._related_tags_search_3_duration_ms.value() )
            
            self._new_options.SetBoolean( 'show_file_lookup_script_tags', self._show_file_lookup_script_tags.isChecked() )
            self._new_options.SetNoneableString( 'favourite_file_lookup_script', self._favourite_file_lookup_script.GetValue() )
            
            self._new_options.SetNoneableInteger( 'num_recent_tags', self._num_recent_tags.GetValue() )
            
        
    
    class _ThumbnailsPanel( QW.QWidget ):
        
        def __init__( self, parent, new_options ):
            
            QW.QWidget.__init__( self, parent )
            
            self._new_options = new_options
            
            self._thumbnail_width = QP.MakeQSpinBox( self, min=20, max=2048 )
            self._thumbnail_height = QP.MakeQSpinBox( self, min=20, max=2048 )
            
            self._thumbnail_border = QP.MakeQSpinBox( self, min=0, max=20 )
            self._thumbnail_margin = QP.MakeQSpinBox( self, min=0, max=20 )
            
            self._video_thumbnail_percentage_in = QP.MakeQSpinBox( self, min=0, max=100 )
            
            self._thumbnail_scroll_rate = QW.QLineEdit( self )
            
            self._thumbnail_fill = QW.QCheckBox( self )
            
            self._thumbnail_visibility_scroll_percent = QP.MakeQSpinBox( self, min=1, max=99 )
            self._thumbnail_visibility_scroll_percent.setToolTip( 'Lower numbers will cause fewer scrolls, higher numbers more.' )
            
            self._media_background_bmp_path = QP.FilePickerCtrl( self )
            
            #
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            self._thumbnail_width.setValue( thumbnail_width )
            self._thumbnail_height.setValue( thumbnail_height )
            
            self._thumbnail_border.setValue( self._new_options.GetInteger( 'thumbnail_border' ) )
            self._thumbnail_margin.setValue( self._new_options.GetInteger( 'thumbnail_margin' ) )
            
            self._video_thumbnail_percentage_in.setValue( self._new_options.GetInteger( 'video_thumbnail_percentage_in' ) )
            
            self._thumbnail_scroll_rate.setText( self._new_options.GetString( 'thumbnail_scroll_rate' ) )
            
            self._thumbnail_fill.setChecked( self._new_options.GetBoolean( 'thumbnail_fill' ) )
            
            self._thumbnail_visibility_scroll_percent.setValue( self._new_options.GetInteger( 'thumbnail_visibility_scroll_percent' ) )
            
            media_background_bmp_path = self._new_options.GetNoneableString( 'media_background_bmp_path' )
            
            if media_background_bmp_path is not None:
                
                self._media_background_bmp_path.SetPath( media_background_bmp_path )
                
            
            #
            
            rows = []
            
            rows.append( ( 'Thumbnail width: ', self._thumbnail_width ) )
            rows.append( ( 'Thumbnail height: ', self._thumbnail_height ) )
            rows.append( ( 'Thumbnail border: ', self._thumbnail_border ) )
            rows.append( ( 'Thumbnail margin: ', self._thumbnail_margin ) )
            rows.append( ( 'Generate video thumbnails this % in: ', self._video_thumbnail_percentage_in ) )
            rows.append( ( 'Do not scroll down on key navigation if thumbnail at least this % visible: ', self._thumbnail_visibility_scroll_percent ) )
            rows.append( ( 'EXPERIMENTAL: Scroll thumbnails at this rate per scroll tick: ', self._thumbnail_scroll_rate ) )
            rows.append( ( 'EXPERIMENTAL: Zoom thumbnails so they \'fill\' their space: ', self._thumbnail_fill ) )
            rows.append( ( 'EXPERIMENTAL: Image path for thumbnail panel background image (set blank to clear): ', self._media_background_bmp_path ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = QP.VBoxLayout()
            
            QP.AddToLayout( vbox, gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.setLayout( vbox )
            
        
        def UpdateOptions( self ):
            
            new_thumbnail_dimensions = [self._thumbnail_width.value(), self._thumbnail_height.value()]
            
            HC.options[ 'thumbnail_dimensions' ] = new_thumbnail_dimensions
            
            self._new_options.SetInteger( 'thumbnail_border', self._thumbnail_border.value() )
            self._new_options.SetInteger( 'thumbnail_margin', self._thumbnail_margin.value() )
            
            self._new_options.SetInteger( 'video_thumbnail_percentage_in', self._video_thumbnail_percentage_in.value() )
            
            try:
                
                thumbnail_scroll_rate = self._thumbnail_scroll_rate.text()
                
                float( thumbnail_scroll_rate )
                
                self._new_options.SetString( 'thumbnail_scroll_rate', thumbnail_scroll_rate )
                
            except:
                
                pass
                
            
            self._new_options.SetBoolean( 'thumbnail_fill', self._thumbnail_fill.isChecked() )
            
            self._new_options.SetInteger( 'thumbnail_visibility_scroll_percent', self._thumbnail_visibility_scroll_percent.value() )
            
            media_background_bmp_path = self._media_background_bmp_path.GetPath()
            
            if media_background_bmp_path == '':
                
                media_background_bmp_path = None
                
            
            self._new_options.SetNoneableString( 'media_background_bmp_path', media_background_bmp_path )
            
        
    
    def CommitChanges( self ):
        
        for page in self._listbook.GetActivePages():
            
            page.UpdateOptions()
            
        
        try:
            
            HG.client_controller.WriteSynchronous( 'save_options', HC.options )
            
            HG.client_controller.WriteSynchronous( 'serialisable', self._new_options )
            
        except:
            
            QW.QMessageBox.critical( self, 'Error', traceback.format_exc() )
            
        
    
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
        
        QP.AddToLayout( hbox, self._add_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._edit_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._delete_button, CC.FLAGS_VCENTER )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._services_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_SMALL_INDENT )
        
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
            
            panel = ClientGUIScrolledPanelsEdit.EditServersideService( dlg_edit, service )
            
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
                
                panel = ClientGUIScrolledPanelsEdit.EditServersideService( dlg_edit, service )
                
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
            
        
    
class ManageURLsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, media ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        media = ClientMedia.FlattenMedia( media )
        
        self._current_media = [ m.Duplicate() for m in media ]
        
        self._multiple_files_warning = ClientGUICommon.BetterStaticText( self, label = 'Warning: you are editing urls for multiple files!\nBe very careful about adding URLs here, as they will apply to everything.\nAdding the same URL to multiple files is only appropriate for gallery-type URLs!' )
        self._multiple_files_warning.setObjectName( 'HydrusWarning' )
        
        if len( self._current_media ) == 1:
            
            self._multiple_files_warning.hide()
            
        
        self._urls_listbox = QW.QListWidget( self )
        self._urls_listbox.setSortingEnabled( True )
        self._urls_listbox.setSelectionMode( QW.QAbstractItemView.ExtendedSelection )
        self._urls_listbox.itemDoubleClicked.connect( self.EventListDoubleClick )
        self._listbox_event_filter = QP.WidgetEventFilter( self._urls_listbox )
        self._listbox_event_filter.EVT_KEY_DOWN( self.EventListKeyDown )
        
        ( width, height ) = ClientGUIFunctions.ConvertTextToPixels( self._urls_listbox, ( 120, 10 ) )
        
        self._urls_listbox.setMinimumWidth( width )
        self._urls_listbox.setMinimumHeight( height )
        
        self._url_input = QW.QLineEdit( self )
        self._url_input.installEventFilter( ClientGUICommon.TextCatchEnterEventFilter( self._url_input, self.AddURL ) )
        
        self._copy_button = ClientGUICommon.BetterButton( self, 'copy all', self._Copy )
        self._paste_button = ClientGUICommon.BetterButton( self, 'paste', self._Paste )
        
        self._urls_to_add = set()
        self._urls_to_remove = set()
        
        #
        
        self._pending_content_updates = []
        
        self._current_urls_count = collections.Counter()
        
        self._UpdateList()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._copy_button, CC.FLAGS_VCENTER )
        QP.AddToLayout( hbox, self._paste_button, CC.FLAGS_VCENTER )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._multiple_files_warning, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._urls_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.widget().setLayout( vbox )
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'global', 'media', 'main_gui' ] )
        
        HG.client_controller.CallAfterQtSafe( self, self._SetSearchFocus )
        
    
    def _Copy( self ):
        
        urls = sorted( self._current_urls_count.keys() )
        
        text = os.linesep.join( urls )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _EnterURL( self, url, only_add = False ):
        
        normalised_url = HG.client_controller.network_engine.domain_manager.NormaliseURL( url )
        
        addee_media = set()
        
        for m in self._current_media:
            
            locations_manager = m.GetLocationsManager()
            
            if normalised_url not in locations_manager.GetURLs():
                
                addee_media.add( m )
                
            
        
        if len( addee_media ) > 0:
            
            addee_hashes = { m.GetHash() for m in addee_media }
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( ( normalised_url, ), addee_hashes ) )
            
            for m in addee_media:
                
                m.GetMediaResult().ProcessContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                
            
            self._pending_content_updates.append( content_update )
            
        
        #
        
        self._UpdateList()
        
    
    def _Paste( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            QW.QMessageBox.warning( self, 'Warning', str(e) )
            
            return
            
        
        try:
            
            for url in HydrusText.DeserialiseNewlinedTexts( raw_text ):
                
                if url != '':
                    
                    self._EnterURL( url, only_add = True )
                    
                
            
        except Exception as e:
            
            QW.QMessageBox.warning( self, 'Warning', 'I could not understand what was in the clipboard: {}'.format( e ) )
            
        
    
    def _RemoveURL( self, url ):
        
        removee_media = set()
        
        for m in self._current_media:
            
            locations_manager = m.GetLocationsManager()
            
            if url in locations_manager.GetURLs():
                
                removee_media.add( m )
                
            
        
        if len( removee_media ) > 0:
            
            removee_hashes = { m.GetHash() for m in removee_media }
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( ( url, ), removee_hashes ) )
            
            for m in removee_media:
                
                m.GetMediaResult().ProcessContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                
            
            self._pending_content_updates.append( content_update )
            
        
        #
        
        self._UpdateList()
        
    
    def _SetSearchFocus( self ):
        
        self._url_input.setFocus( QC.Qt.OtherFocusReason )
        
    
    def _UpdateList( self ):
        
        self._urls_listbox.clear()
        
        self._current_urls_count = collections.Counter()
        
        for m in self._current_media:
            
            locations_manager = m.GetLocationsManager()
            
            for url in locations_manager.GetURLs():
                
                self._current_urls_count[ url ] += 1
                
            
        
        for ( url, count ) in self._current_urls_count.items():
            
            if len( self._current_media ) == 1:
                
                label = url
                
            else:
                
                label = '{} ({})'.format( url, count )
                
            item = QW.QListWidgetItem()
            item.setText( label )
            item.setData( QC.Qt.UserRole, url )
            self._urls_listbox.addItem( item )
            
        
    
    def EventListDoubleClick( self, item ):
    
        urls = [ QP.GetClientData( self._urls_listbox, selection.row() ) for selection in list( self._urls_listbox.selectedIndexes() ) ]
        
        for url in urls:
            
            self._RemoveURL( url )
            
        
        if len( urls ) == 1:
            
            url = urls[0]
            
            self._url_input.setText( url )
            
        
    
    def EventListKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ClientGUIShortcuts.DELETE_KEYS_QT:
            
            urls = [ QP.GetClientData( self._urls_listbox, selection.row() ) for selection in list( self._urls_listbox.selectedIndexes() ) ]
            
            for url in urls:
                
                self._RemoveURL( url )
                
            
        else:
            
            return True # was: event.ignore()
        
    
    def AddURL( self ):
        
        url = self._url_input.text()
        
        if url == '':
            
            self.parentWidget().DoOK()
            
        else:
            
            try:
                
                self._EnterURL( url )
                
                self._url_input.setText( '' )
                
            except Exception as e:
                
                QW.QMessageBox.warning( self, 'Warning', 'I could not add that URL: {}'.format( e ) )
                
            
        
    
    def CommitChanges( self ):
        
        if len( self._pending_content_updates ) > 0:
            
            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : self._pending_content_updates }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
    def ProcessApplicationCommand( self, command: CAC.ApplicationCommand ):
        
        command_processed = True
        
        data = command.GetData()
        
        if command.IsSimpleCommand():
            
            action = data
            
            if action == CAC.SIMPLE_MANAGE_FILE_URLS:
                
                self._OKParent()
                
            elif action == CAC.SIMPLE_SET_SEARCH_FOCUS:
                
                self._SetSearchFocus()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
class RepairFileSystemPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, missing_locations ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._only_thumbs = True
        
        self._incorrect_locations = {}
        self._correct_locations = {}
        
        for ( incorrect_location, prefix ) in missing_locations:
            
            self._incorrect_locations[ prefix ] = incorrect_location
            
            if prefix.startswith( 'f' ):
                
                self._only_thumbs = False
                
            
        
        text = 'This dialog has launched because some expected file storage directories were not found. This is a serious error. You have two options:'
        text += os.linesep * 2
        text += '1) If you know what these should be (e.g. you recently remapped their external drive to another location), update the paths here manually. For most users, this will be clicking _add a possibly correct location_ and then select the new folder where the subdirectories all went. You can repeat this if your folders are missing in multiple locations. Check everything reports _ok!_'
        text += os.linesep * 2
        text += 'Although it is best if you can find everything, you only _have_ to fix the subdirectories starting with \'f\', which store your original files. Those starting \'t\' and \'r\' are for your thumbnails, which can be regenerated with a bit of work.'
        text += os.linesep * 2
        text += 'Then hit \'apply\', and the client will launch. You should double-check all your locations under database->migrate database immediately.'
        text += os.linesep * 2
        text += '2) If the locations are not available, or you do not know what they should be, or you wish to fix this outside of the program, hit \'cancel\' to gracefully cancel client boot. Feel free to contact hydrus dev for help.'
        
        if self._only_thumbs:
            
            text += os.linesep * 2
            text += 'SPECIAL NOTE FOR YOUR SITUATION: The only paths missing are thumbnail paths. If you cannot recover these folders, you can hit apply to create empty paths at the original or corrected locations and then run a maintenance routine to regenerate the thumbnails from their originals.'
            
        
        st = ClientGUICommon.BetterStaticText( self, text )
        st.setWordWrap( True )
        
        self._locations = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_REPAIR_LOCATIONS.ID, 12, self._ConvertPrefixToListCtrlTuples, activation_callback = self._SetLocations )
        
        self._set_button = ClientGUICommon.BetterButton( self, 'set correct location', self._SetLocations )
        self._add_button = ClientGUICommon.BetterButton( self, 'add a possibly correct location (let the client figure out what it contains)', self._AddLocation )
        
        # add a button here for 'try to fill them in for me'. you give it a dir, and it tries to figure out and fill in the prefixes for you
        
        #
        
        self._locations.AddDatas( [ prefix for ( incorrect_location, prefix ) in missing_locations ] )
        
        self._locations.Sort()
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._locations, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._set_button, CC.FLAGS_LONE_BUTTON )
        QP.AddToLayout( vbox, self._add_button, CC.FLAGS_LONE_BUTTON )
        
        self.widget().setLayout( vbox )
        
    
    def _AddLocation( self ):
        
        with QP.DirDialog( self, 'Select the potential correct location.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                for prefix in self._locations.GetData():
                    
                    ok = os.path.exists( os.path.join( path, prefix ) )
                    
                    if ok:
                        
                        self._correct_locations[ prefix ] = ( path, ok )
                        
                    
                
                self._locations.UpdateDatas()
                
            
        
    
    def _ConvertPrefixToListCtrlTuples( self, prefix ):
        
        incorrect_location = self._incorrect_locations[ prefix ]
        
        if prefix in self._correct_locations:
            
            ( correct_location, ok ) = self._correct_locations[ prefix ]
            
            if ok:
                
                pretty_ok = 'ok!'
                
            else:
                
                pretty_ok = 'not found'
                
            
        else:
            
            correct_location = ''
            ok = None
            pretty_ok = ''
            
        
        pretty_incorrect_location = incorrect_location
        pretty_prefix = prefix
        pretty_correct_location = correct_location
        
        display_tuple = ( pretty_incorrect_location, pretty_prefix, pretty_correct_location, pretty_ok )
        sort_tuple = ( incorrect_location, prefix, correct_location, ok )
        
        return ( display_tuple, sort_tuple )
        
    
    def _GetValue( self ):
        
        correct_rows = []
        
        thumb_problems = False
        
        for prefix in self._locations.GetData():
            
            incorrect_location = self._incorrect_locations[ prefix ]
            
            if prefix not in self._correct_locations:
                
                if prefix.startswith( 'f' ):
                    
                    raise HydrusExceptions.VetoException( 'You did not correct all the file locations!' )
                    
                else:
                    
                    thumb_problems = True
                    
                    correct_location = incorrect_location
                    
                
            else:
                
                ( correct_location, ok ) = self._correct_locations[ prefix ]
                
                if not ok:
                    
                    if prefix.startswith( 'f' ):
                        
                        raise HydrusExceptions.VetoException( 'You did not find all the correct file locations!' )
                        
                    else:
                        
                        thumb_problems = True
                        
                    
                
            
            correct_rows.append( ( incorrect_location, prefix, correct_location ) )
            
        
        return ( correct_rows, thumb_problems )
        
    
    def _SetLocations( self ):
        
        prefixes = self._locations.GetData( only_selected = True )
        
        if len( prefixes ) > 0:
            
            with QP.DirDialog( self, 'Select correct location.' ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    path = dlg.GetPath()
                    
                    for prefix in prefixes:
                        
                        ok = os.path.exists( os.path.join( path, prefix ) )
                        
                        self._correct_locations[ prefix ] = ( path, ok )
                        
                    
                    self._locations.UpdateDatas()
                    
                
            
        
    
    def CheckValid( self ):
        
        # raises veto if invalid
        self._GetValue()
        
    
    def CommitChanges( self ):
        
        ( correct_rows, thumb_problems ) = self._GetValue()
        
        HG.client_controller.WriteSynchronous( 'repair_client_files', correct_rows )
        
    
    def UserIsOKToOK( self ):
        
        ( correct_rows, thumb_problems ) = self._GetValue()
        
        if thumb_problems:
            
            message = 'Some or all of your incorrect paths have not been corrected, but they are all thumbnail paths.'
            message += os.linesep * 2
            message += 'Would you like instead to create new empty subdirectories at the previous (or corrected, if you have entered them) locations?'
            message += os.linesep * 2
            message += 'You can run database->regenerate->thumbnails to fill them up again.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.Accepted:
                
                return False
                
            
        
        return True
        
