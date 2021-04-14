import os
import time
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTagArchive
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworkVariableHandling

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientPaths
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAPI
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIPanels
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIScrolledPanelsReview
from hydrus.client.gui import ClientGUIStringControls
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIControls
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.metadata import ClientRatings
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingJobs

class ManageClientServicesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( self, CGLC.COLUMN_LIST_MANAGE_SERVICES.ID, 25, self._ConvertServiceToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit)
        
        menu_items = []
        
        for service_type in HC.ADDREMOVABLE_SERVICES:
            
            service_string = HC.service_string_lookup[ service_type ]
            
            menu_items.append( ( 'normal', service_string, 'Add a new ' + service_string + '.', HydrusData.Call( self._Add, service_type ) ) )
            
        
        self._add_button = ClientGUIMenuButton.MenuButton( self, 'add', menu_items = menu_items )
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
            
            panel = EditClientServicePanel( dlg, service )
            
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
                    
                    panel = EditClientServicePanel( dlg, service )
                    
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
        
    
class EditClientServicePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, service ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        duplicate_service = service.Duplicate()
        
        ( self._service_key, self._service_type, name, self._dictionary ) = duplicate_service.ToTuple()
        
        self._service_panel = EditServiceSubPanel( self, name )
        
        self._panels = []
        
        if self._service_type in HC.REMOTE_SERVICES:
            
            remote_panel = EditServiceRemoteSubPanel( self, self._service_type, self._dictionary )
            
            self._panels.append( remote_panel )
            
        
        if self._service_type in HC.RESTRICTED_SERVICES:
            
            self._panels.append( EditServiceRestrictedSubPanel( self, self._service_key, remote_panel, self._service_type, self._dictionary ) )
            
        
        if self._service_type in HC.REAL_TAG_SERVICES:
            
            self._panels.append( EditServiceTagSubPanel( self, self._dictionary ) )
            
        
        if self._service_type in ( HC.CLIENT_API_SERVICE, HC.LOCAL_BOORU ):
            
            self._panels.append( EditServiceClientServerSubPanel( self, self._service_type, self._dictionary ) )
            
        
        if self._service_type in HC.RATINGS_SERVICES:
            
            self._panels.append( EditServiceRatingsSubPanel( self, self._dictionary ) )
            
            if self._service_type == HC.LOCAL_RATING_NUMERICAL:
                
                self._panels.append( EditServiceRatingsNumericalSubPanel( self, self._dictionary ) )
                
            
        
        if self._service_type == HC.IPFS:
            
            self._panels.append( EditServiceIPFSSubPanel( self, self._dictionary ) )
            
        
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
        
    
class EditServiceSubPanel( ClientGUICommon.StaticBox ):
    
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
        
    

class EditServiceRemoteSubPanel( ClientGUICommon.StaticBox ):
    
    becameInvalidSignal = QC.Signal()
    becameValidSignal = QC.Signal()
    
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
        
        #
        
        self._currently_valid = self.ValueIsValid()
        
        self._host.textChanged.connect( self._DoValidityCheck )
        
    
    def _DoValidityCheck( self ):
        
        currently_valid = self.ValueIsValid()
        
        if currently_valid != self._currently_valid:
            
            self._currently_valid = currently_valid
            
            if self._currently_valid:
                
                self.becameValidSignal.emit()
                
            else:
                
                self.becameInvalidSignal.emit()
                
            
        
    
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
        
    
    def ValueIsValid( self ):
        
        try:
            
            self.GetCredentials()
            
            return True
            
        except HydrusExceptions.VetoException:
            
            return False
            
        
    

class EditServiceRestrictedSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service_key, remote_panel: EditServiceRemoteSubPanel, service_type, dictionary ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'hydrus network' )
        
        self._service_key = service_key
        self._remote_panel = remote_panel
        self._service_type = service_type
        
        self._original_credentials = dictionary[ 'credentials' ]
        
        self._access_key = QW.QLineEdit( self )
        
        self._auto_register = ClientGUICommon.BetterButton( self, 'check for automatic account creation', self._STARTFetchAutoAccountCreationAccountTypes )
        self._test_credentials_button = ClientGUICommon.BetterButton( self, 'test access key', self._STARTTestCredentials )
        self._register = ClientGUICommon.BetterButton( self, 'fetch an access key with a registration key', self._EnterRegistrationKey )
        
        #
        
        if self._original_credentials.HasAccessKey():
            
            self._access_key.setText( self._original_credentials.GetAccessKey().hex() )
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._auto_register, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._register, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._test_credentials_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        wrapped_access_key = ClientGUICommon.WrapInText( self._access_key, self, 'access key: ' )
        
        self.Add( wrapped_access_key, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        self._UpdateButtons()
        
        self._remote_panel.becameValidSignal.connect( self._UpdateButtons )
        self._remote_panel.becameInvalidSignal.connect( self._UpdateButtons )
        
    
    def _EnableDisableButtons( self, value ):
        
        address_valid = self._remote_panel.ValueIsValid()
        
        if not address_valid:
            
            value = False
            
        
        self._auto_register.setEnabled( value )
        self._register.setEnabled( value )
        self._test_credentials_button.setEnabled( value )
        
    
    def _UpdateButtons( self ):
        
        address_valid = self._remote_panel.ValueIsValid()
        
        self._EnableDisableButtons( address_valid )
        
    
    def _STARTFetchAutoAccountCreationAccountTypes( self ):
        
        credentials = self._remote_panel.GetCredentials()
        
        def work_callable():
            
            ( host, port ) = credentials.GetAddress()
            
            url = 'https://{}:{}/auto_create_account_types'.format( host, port )
            
            network_job = ClientNetworkingJobs.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
            
            network_job.OnlyTryConnectionOnce()
            network_job.OverrideBandwidth()
            
            network_job.SetForLogin( True )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            network_bytes = network_job.GetContentBytes()
            
            parsed_response_args = HydrusNetworkVariableHandling.ParseNetworkBytesToParsedHydrusArgs( network_bytes )
            
            account_types = list( parsed_response_args[ 'account_types' ] )
            
            return account_types
            
        
        def publish_callable( account_types ):
            
            self._EnableDisableButtons( True )
            
            self._SelectAccountTypeForAutoAccountCreation( account_types )
            
        
        def errback_ui_cleanup_callable():
            
            self._EnableDisableButtons( True )
            
        
        self._EnableDisableButtons( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
        
        job.start()
        
    
    def _EnterRegistrationKey( self ):
        
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
                
            
        
        self._STARTGetAccessKeyFromRegistrationKey( registration_key )
        
    
    def _STARTAutoCreateAccount( self, account_type: HydrusNetwork.AccountType ):
        
        credentials = self._remote_panel.GetCredentials()
        
        def work_callable():
            
            ( host, port ) = credentials.GetAddress()
            
            # get a registration key
            
            url = 'https://{}:{}/auto_create_registration_key?account_type_key={}'.format( host, port, account_type.GetAccountTypeKey().hex() )
            
            network_job = ClientNetworkingJobs.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
            
            network_job.OnlyTryConnectionOnce()
            network_job.OverrideBandwidth()
            
            network_job.SetForLogin( True )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            network_bytes = network_job.GetContentBytes()
            
            parsed_response_args = HydrusNetworkVariableHandling.ParseNetworkBytesToParsedHydrusArgs( network_bytes )
            
            registration_key = parsed_response_args[ 'registration_key' ]
            
            return registration_key
            
        
        def publish_callable( registration_key ):
            
            self._EnableDisableButtons( True )
            
            # break this up into the 'yep, now I have the key' and call that
            self._STARTGetAccessKeyFromRegistrationKey( registration_key )
            
        
        def errback_ui_cleanup_callable():
            
            self._EnableDisableButtons( True )
            
        
        self._EnableDisableButtons( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
        
        job.start()
        
    
    def _STARTGetAccessKeyFromRegistrationKey( self, registration_key ):
        
        credentials = self._remote_panel.GetCredentials()
        
        def work_callable():
            
            ( host, port ) = credentials.GetAddress()
            
            url = 'https://{}:{}/access_key?registration_key={}'.format( host, port, registration_key.hex() )
            
            network_job = ClientNetworkingJobs.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
            
            network_job.OnlyTryConnectionOnce()
            network_job.OverrideBandwidth()
            
            network_job.SetForLogin( True )
            
            HG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            network_bytes = network_job.GetContentBytes()
            
            parsed_response_args = HydrusNetworkVariableHandling.ParseNetworkBytesToParsedHydrusArgs( network_bytes )
            
            access_key = parsed_response_args[ 'access_key' ]
            
            return access_key
            
        
        def publish_callable( access_key ):
            
            access_key_encoded = access_key.hex()
            
            self._access_key.setText( access_key_encoded )
            
            self._EnableDisableButtons( True )
            
            QW.QMessageBox.information( self, 'Information', 'Looks good!' )
            
        
        def errback_ui_cleanup_callable():
            
            self._EnableDisableButtons( True )
            
        
        self._EnableDisableButtons( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
        
        job.start()
        
    
    def _SelectAccountTypeForAutoAccountCreation( self, account_types: typing.List[ HydrusNetwork.AccountType ] ):
        
        if len( account_types ) == 0:
            
            QW.QMessageBox.information( self, 'No auto account creation', 'Sorry, this server does not support automatic account creation!' )
            
        else:
            
            unavailable_account_types = [ account_type for account_type in account_types if not account_type.CanAutoCreateAccountNow() ]
            available_account_types = [ account_type for account_type in account_types if account_type.CanAutoCreateAccountNow() ]
            
            unavailable_text = ''
            
            if len( unavailable_account_types ) > 0:
                
                unavailable_texts = []
                
                for account_type in unavailable_account_types:
                    
                    ( num_accounts, time_delta ) = account_type.GetAutoCreationVelocity()
                    
                    history = account_type.GetAutoCreationHistory()
                    
                    text = '{} - {}'.format( account_type.GetTitle(), history.GetWaitingEstimate( HC.BANDWIDTH_TYPE_REQUESTS, time_delta, num_accounts ) )
                    
                    unavailable_texts.append( text )
                    
                
                unavailable_text = os.linesep * 2
                unavailable_text += 'These other account types are currently in short supply and will be available after a delay:'
                unavailable_text += os.linesep * 2
                unavailable_text += os.linesep.join( unavailable_texts )
                
            
            if len( available_account_types ) == 1:
                
                account_type = available_account_types[ 0 ]
                
                message = 'This server offers auto-creation of a "{}" account type. Is this ok?'.format( account_type.GetTitle() )
                message += unavailable_text
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'One account type available' )
                
                if result == QW.QDialog.Accepted:
                    
                    self._STARTAutoCreateAccount( account_type )
                    
                
            elif len( available_account_types ) > 0:
                
                message = 'Please select which account type you would like to create.'
                message += unavailable_text
                
                choice_tuples = [ ( account_type.GetTitle(), account_type, account_type.GetPermissionsString() ) for account_type in available_account_types ]
                
                try:
                    
                    account_type = ClientGUIDialogsQuick.SelectFromListButtons( self, 'Select account type to create', choice_tuples, message = message )
                    
                    self._STARTAutoCreateAccount( account_type )
                    
                except HydrusExceptions.CancelledException:
                    
                    return
                    
                
            
        
    
    def _STARTTestCredentials( self ):
        
        credentials = self.GetCredentials()
        service_type = self._service_type
        
        def qt_done( message ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            QW.QMessageBox.information( self, 'Information', message )
            
            self._test_credentials_button.setEnabled( True )
            self._test_credentials_button.setText( 'test access key' )
            
        
        def work_callable():
            
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
                
            
            return message
            
        
        def publish_callable( message ):
            
            self._EnableDisableButtons( True )
            
            QW.QMessageBox.information( self, 'Information', message )
            
        
        def errback_ui_cleanup_callable():
            
            self._EnableDisableButtons( True )
            
        
        self._EnableDisableButtons( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
        
        job.start()
        
    
    def GetCredentials( self ):
        
        credentials = self._remote_panel.GetCredentials()
        
        try:
            
            access_key = bytes.fromhex( self._access_key.text() )
            
        except Exception as e:
            
            raise HydrusExceptions.VetoException( 'Could not understand that access key!') from e
            
        
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
        
    

class EditServiceClientServerSubPanel( ClientGUICommon.StaticBox ):
    
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
        
    

class EditServiceTagSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, dictionary ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'tags' )
        
        self._st = ClientGUICommon.BetterStaticText( self )
        
        self._st.setText( 'This is a tag service. There are no additional options for it at present.' )
        
        #
        
        self.Add( self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def GetValue( self ):
        
        dictionary_part = {}
        
        return dictionary_part
        
    

class EditServiceRatingsSubPanel( ClientGUICommon.StaticBox ):
    
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
        
    
class EditServiceRatingsNumericalSubPanel( ClientGUICommon.StaticBox ):
    
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
        
    

class EditServiceIPFSSubPanel( ClientGUICommon.StaticBox ):
    
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
        
    
class ReviewServicePanel( QW.QWidget ):
    
    def __init__( self, parent, service ):
        
        QW.QWidget.__init__( self, parent )
        
        self._service = service
        
        self._refresh_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().refresh, self._RefreshButton )
        
        service_type = self._service.GetServiceType()
        
        subpanels = []
        
        subpanels.append( ( ReviewServiceSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
        
        if service_type in HC.REMOTE_SERVICES:
            
            subpanels.append( ( ReviewServiceRemoteSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            subpanels.append( ( ReviewServiceRestrictedSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if service_type in HC.FILE_SERVICES:
            
            subpanels.append( ( ReviewServiceFileSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if self._service.GetServiceKey() == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
            
            subpanels.append( ( ReviewServiceCombinedLocalFilesSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if self._service.GetServiceKey() == CC.TRASH_SERVICE_KEY:
            
            subpanels.append( ( ReviewServiceTrashSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if service_type in HC.REAL_TAG_SERVICES:
            
            subpanels.append( ( ReviewServiceTagSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if service_type in HC.RATINGS_SERVICES:
            
            subpanels.append( ( ReviewServiceRatingSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if service_type in HC.REPOSITORIES:
            
            subpanels.append( ( ReviewServiceRepositorySubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if service_type == HC.IPFS:
            
            subpanels.append( ( ReviewServiceIPFSSubPanel( self, service ), CC.FLAGS_EXPAND_BOTH_WAYS ) )
            
        
        if service_type == HC.LOCAL_BOORU:
            
            subpanels.append( ( ReviewServiceLocalBooruSubPanel( self, service ), CC.FLAGS_EXPAND_BOTH_WAYS ) )
            
        
        if service_type == HC.CLIENT_API_SERVICE:
            
            subpanels.append( ( ReviewServiceClientAPISubPanel( self, service ), CC.FLAGS_EXPAND_BOTH_WAYS ) )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._refresh_button, CC.FLAGS_ON_RIGHT )
        
        saw_both_ways = False
        
        for ( panel, flags ) in subpanels:
            
            if flags == CC.FLAGS_EXPAND_BOTH_WAYS:
                
                saw_both_ways = True
                
            
            QP.AddToLayout( vbox, panel, flags )
            
        
        if not saw_both_ways:
            
            vbox.addStretch( 1 )
            
        
        self.setLayout( vbox )
        
    
    def _RefreshButton( self ):
        
        HG.client_controller.pub( 'service_updated', self._service )
        
    
    def EventImmediateSync( self, event ):
        
        def do_it():
            
            job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
            
            job_key.SetVariable( 'popup_title', self._service.GetName() + ': immediate sync' )
            job_key.SetVariable( 'popup_text_1', 'downloading' )
            
            self._controller.pub( 'message', job_key )
            
            content_update_package = self._service.Request( HC.GET, 'immediate_content_update_package' )
            
            c_u_p_num_rows = content_update_package.GetNumRows()
            c_u_p_total_weight_processed = 0
            
            update_speed_string = ''
            
            content_update_index_string = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( c_u_p_total_weight_processed, c_u_p_num_rows ) + ': '
            
            job_key.SetVariable( 'popup_text_1', content_update_index_string + 'committing' + update_speed_string )
            
            job_key.SetVariable( 'popup_gauge_1', ( c_u_p_total_weight_processed, c_u_p_num_rows ) )
            
            for ( content_updates, weight ) in content_update_package.IterateContentUpdateChunks():
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    job_key.Delete()
                    
                    return
                    
                
                content_update_index_string = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( c_u_p_total_weight_processed, c_u_p_num_rows ) + ': '
                
                job_key.SetVariable( 'popup_text_1', content_update_index_string + 'committing' + update_speed_string )
                
                job_key.SetVariable( 'popup_gauge_1', ( c_u_p_total_weight_processed, c_u_p_num_rows ) )
                
                precise_timestamp = HydrusData.GetNowPrecise()
                
                self._controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
                
                it_took = HydrusData.GetNowPrecise() - precise_timestamp
                
                rows_s = int( weight / it_took )
                
                update_speed_string = ' at ' + HydrusData.ToHumanInt( rows_s ) + ' rows/s'
                
                c_u_p_total_weight_processed += weight
                
            
            job_key.DeleteVariable( 'popup_gauge_1' )
            
            self._service.SyncThumbnails( job_key )
            
            job_key.SetVariable( 'popup_text_1', 'done! ' + HydrusData.ToHumanInt( c_u_p_num_rows ) + ' rows added.' )
            
            job_key.Finish()
            
        
        self._controller.CallToThread( do_it )
        
    
    def GetServiceKey( self ):
        
        return self._service.GetServiceKey()
        

class ReviewServiceSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'name and type' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._name_and_type = ClientGUICommon.BetterStaticText( self )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._name_and_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        name = self._service.GetName()
        service_type = self._service.GetServiceType()
        
        label = name + ' - ' + HC.service_string_lookup[ service_type ]
        
        self._name_and_type.setText( label )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    

class ReviewServiceClientAPISubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'client api' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._service_status = ClientGUICommon.BetterStaticText( self )
        
        permissions_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._permissions_list = ClientGUIListCtrl.BetterListCtrl( permissions_list_panel, CGLC.COLUMN_LIST_CLIENT_API_PERMISSIONS.ID, 10, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        permissions_list_panel.SetListCtrl( self._permissions_list )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'manually', 'Enter the details of the share manually.', self._AddManually ) )
        menu_items.append( ( 'normal', 'from api request', 'Listen for an access permission request from an external program via the API.', self._AddFromAPI ) )
        
        permissions_list_panel.AddMenuButton( 'add', menu_items )
        permissions_list_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        permissions_list_panel.AddButton( 'duplicate', self._Duplicate, enabled_only_on_selection = True )
        permissions_list_panel.AddButton( 'delete', self._Delete, enabled_only_on_selection = True )
        permissions_list_panel.AddSeparator()
        permissions_list_panel.AddButton( 'open client api base url', self._OpenBaseURL )
        permissions_list_panel.AddButton( 'copy api access key', self._CopyAPIAccessKey, enabled_only_on_single_selection = True )
        
        self._permissions_list.Sort()
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._service_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( permissions_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _ConvertDataToListCtrlTuples( self, api_permissions ):
        
        name = api_permissions.GetName()
        
        pretty_name = name
        
        basic_permissions_string = api_permissions.GetBasicPermissionsString()
        advanced_permissions_string = api_permissions.GetAdvancedPermissionsString()
        
        sort_basic_permissions = basic_permissions_string
        sort_advanced_permissions = advanced_permissions_string
        
        display_tuple = ( pretty_name, basic_permissions_string, advanced_permissions_string )
        sort_tuple = ( name, sort_basic_permissions, sort_advanced_permissions )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopyAPIAccessKey( self ):
        
        selected = self._permissions_list.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return
            
        
        api_permissions = selected[0]
        
        access_key = api_permissions.GetAccessKey()
        
        text = access_key.hex()
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _AddFromAPI( self ):
        
        port = self._service.GetPort()
        
        if port is None:
            
            QW.QMessageBox.warning( self, 'Warning', 'The service is not running, so you cannot add new access via the API!' )
            
            return
            
        
        title = 'waiting for API access permissions request'
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, title ) as dlg:
            
            panel = ClientGUIAPI.CaptureAPIAccessPermissionsRequestPanel( dlg )
            
            dlg.SetPanel( panel )
            
            ClientAPI.last_api_permissions_request = None
            ClientAPI.api_request_dialog_open = True
            
            dlg.exec()
            
            ClientAPI.api_request_dialog_open = False
            
            api_permissions = panel.GetAPIAccessPermissions()
            
            if api_permissions is not None:
                
                self._AddManually( api_permissions = api_permissions )
                
            
        
    
    def _AddManually( self, api_permissions = None ):
        
        if api_permissions is None:
            
            api_permissions = ClientAPI.APIPermissions()
            
        
        title = 'edit api access permissions'
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
            
            panel = ClientGUIAPI.EditAPIPermissionsPanel( dlg, api_permissions )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                api_permissions = panel.GetValue()
                
                HG.client_controller.client_api_manager.AddAccess( api_permissions )
                
                self._Refresh()
                
            
        
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            access_keys = [ api_permissions.GetAccessKey() for api_permissions in self._permissions_list.GetData( only_selected = True ) ]
            
            HG.client_controller.client_api_manager.DeleteAccess( access_keys )
            
            self._Refresh()
            
        
    
    def _Duplicate( self ):
        
        selected_api_permissions_objects = self._permissions_list.GetData( only_selected = True )
        
        dupes = [ api_permissions.Duplicate() for api_permissions in selected_api_permissions_objects ]
        
        # permissions objects do not need unique names, but let's dedupe the dupe objects' names here to make it easy to see which is which in this step
        
        existing_objects = list( self._permissions_list.GetData() )
        
        existing_names = { p_o.GetName() for p_o in existing_objects }
        
        for dupe in dupes:
            
            dupe.GenerateNewAccessKey()
            
            dupe.SetNonDupeName( existing_names )
            
            existing_names.add( dupe.GetName() )
            
        
        existing_objects.extend( dupes )
        
        HG.client_controller.client_api_manager.SetPermissions( existing_objects )
        
        self._Refresh()
        
    
    def _Edit( self ):
        
        selected_api_permissions_objects = self._permissions_list.GetData( only_selected = True )
        
        for api_permissions in selected_api_permissions_objects:
            
            title = 'edit api access permissions'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIAPI.EditAPIPermissionsPanel( dlg, api_permissions )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    api_permissions = panel.GetValue()
                    
                    HG.client_controller.client_api_manager.OverwriteAccess( api_permissions )
                    
                else:
                    
                    break
                    
                
            
        
        self._Refresh()
        
    
    def _OpenBaseURL( self ):
        
        port = self._service.GetPort()
        
        if port is None:
            
            QW.QMessageBox.warning( self, 'Warning', 'The service is not running, so you cannot view it in a web browser!' )
            
        else:
            
            if self._service.UseHTTPS():
                
                scheme = 'https'
                
            else:
                
                scheme = 'http'
                
            
            url = '{}://127.0.0.1:{}/'.format( scheme, self._service.GetPort() )
            
            ClientPaths.LaunchURLInWebBrowser( url )
            
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        port = self._service.GetPort()
        
        if port is None:
            
            status = 'The client api is not running.'
            
        else:
            
            status = 'The client api should be running on port {}.'.format( port )
            
            upnp_port = self._service.GetUPnPPort()
            
            if upnp_port is not None:
                
                status += ' It should be open via UPnP on external port {}.'.format( upnp_port )
                
            
        
        self._service_status.setText( status )
        
        api_permissions_objects = HG.client_controller.client_api_manager.GetAllPermissions()
        
        self._permissions_list.SetData( api_permissions_objects )
        
        self._permissions_list.Sort()
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    

class ReviewServiceCombinedLocalFilesSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'combined local files' )
        
        self._service = service
        
        self._clear_deleted_files_record = ClientGUICommon.BetterButton( self, 'clear deleted files record', self._ClearDeletedFilesRecord )
        
        #
        
        self.Add( self._clear_deleted_files_record, CC.FLAGS_ON_RIGHT )
        
    
    def _ClearDeletedFilesRecord( self ):
        
        message = 'This will instruct your database to forget its entire record of locally deleted files, meaning that if it ever encounters any of those files again, it will assume they are new and reimport them. This operation cannot be undone.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            hashes = None
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', hashes ) )
            
            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
            
            HG.client_controller.pub( 'service_updated', self._service )
            
        
    

class ReviewServiceFileSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'files' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._file_info_st = ClientGUICommon.BetterStaticText( self )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._file_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( text ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._file_info_st.setText( text )
            
        
        service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
        
        num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
        
        text = HydrusData.ToHumanInt( num_files ) + ' files, totalling ' + HydrusData.ToHumanBytes( total_size )
        
        if service.GetServiceType() in ( HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ):
            
            num_deleted_files = service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ]
            
            text += ' - ' + HydrusData.ToHumanInt( num_deleted_files ) + ' deleted files'
            
        
        QP.CallAfter( qt_code, text )
        
    

class ReviewServiceRemoteSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'this client\'s network use' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._address = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        self._functional = ClientGUICommon.BetterStaticText( self )
        self._bandwidth_summary = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        
        self._functional.setWordWrap( True )
        
        self._bandwidth_panel = QW.QWidget( self )
        
        vbox = QP.VBoxLayout()
        
        self._bandwidth_panel.setLayout( vbox )
        
        self._rule_widgets = []
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._address, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._functional, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._bandwidth_summary, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._bandwidth_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        credentials = self._service.GetCredentials()
        
        ( host, port ) = credentials.GetAddress()
        
        self._address.setText( host+':'+str(port) )
        
        ( is_ok, status_string ) = self._service.GetStatusInfo()
        
        self._functional.setText( status_string )
        
        if is_ok:
            
            self._functional.setObjectName( '' )
            
        else:
            
            self._functional.setObjectName( 'HydrusWarning' )
            
        
        self._functional.style().polish( self._functional )
        
        bandwidth_summary = self._service.GetBandwidthCurrentMonthSummary()
        
        self._bandwidth_summary.setText( bandwidth_summary )
        
        vbox = self._bandwidth_panel.layout()
        
        for rule_widget in self._rule_widgets:
            
            vbox.removeWidget( rule_widget )
            
            rule_widget.deleteLater()
            
        
        self._rule_widgets = []
        
        bandwidth_rows = self._service.GetBandwidthStringsAndGaugeTuples()
        
        for ( status, ( value, range ) ) in bandwidth_rows:
            
            gauge = ClientGUICommon.TextAndGauge( self._bandwidth_panel )
            
            gauge.SetValue( status, value, range )
            
            self._rule_widgets.append( gauge )
            
            QP.AddToLayout( vbox, gauge, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    

class ReviewServiceRestrictedSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'hydrus service account - shared by all clients using the same access key' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._title_and_expires_st = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        self._status_st = ClientGUICommon.BetterStaticText( self )
        self._message_st = ClientGUICommon.BetterStaticText( self )
        self._next_sync_st = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        self._bandwidth_summary = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        
        self._status_st.setWordWrap( True )
        self._message_st.setWordWrap( True )
        
        self._bandwidth_panel = QW.QWidget( self )
        
        vbox = QP.VBoxLayout()
        
        self._bandwidth_panel.setLayout( vbox )
        
        self._rule_widgets = []
        
        self._network_sync_paused_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().pause, self._PausePlayNetworkSync )
        self._network_sync_paused_button.setToolTip( 'pause/play account sync' )
        
        self._refresh_account_button = ClientGUICommon.BetterButton( self, 'refresh account', self._RefreshAccount )
        self._copy_account_key_button = ClientGUICommon.BetterButton( self, 'copy account key', self._CopyAccountKey )
        self._permissions_button = ClientGUIMenuButton.MenuButton( self, 'see special permissions', [] )
        
        #
        
        self._Refresh()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._network_sync_paused_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._refresh_account_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._copy_account_key_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._permissions_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.Add( self._title_and_expires_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._next_sync_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._message_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._bandwidth_summary, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._bandwidth_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _CopyAccountKey( self ):
        
        account = self._service.GetAccount()
        
        account_key = account.GetAccountKey()
        
        account_key_hex = account_key.hex()
        
        HG.client_controller.pub( 'clipboard', 'text', account_key_hex )
        
    
    def _PausePlayNetworkSync( self ):
        
        self._service.PausePlayNetworkSync()
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        account = self._service.GetAccount()
        
        account_type = account.GetAccountType()
        
        title = account_type.GetTitle()
        
        expires_status = account.GetExpiresString()
        
        self._title_and_expires_st.setText( title+' that '+expires_status )
        
        ( is_ok, status_string ) = account.GetStatusInfo()
        
        self._status_st.setText( status_string )
        
        if is_ok:
            
            self._status_st.setObjectName( '' )
            
        else:
            
            self._status_st.setObjectName( 'HydrusWarning' )
            
        
        self._status_st.style().polish( self._status_st )
        
        ( message, message_created ) = account.GetMessageAndTimestamp()
        
        if message != '':
            
            message = 'Message from server: {}'.format( message )
            
        
        self._message_st.setText( message )
        
        next_sync_status = self._service.GetNextAccountSyncStatus()
        
        self._next_sync_st.setText( next_sync_status )
        
        #
        
        if self._service.IsPausedNetworkSync():
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._network_sync_paused_button, CC.global_pixmaps().play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._network_sync_paused_button, CC.global_pixmaps().pause )
            
        
        #
        
        bandwidth_summary = account.GetBandwidthCurrentMonthSummary()
        
        self._bandwidth_summary.setText( bandwidth_summary )
        
        vbox = self._bandwidth_panel.layout()
        
        for rule_widget in self._rule_widgets:
            
            vbox.removeWidget( rule_widget )
            
            rule_widget.deleteLater()
            
        
        self._rule_widgets = []
        
        bandwidth_rows = account.GetBandwidthStringsAndGaugeTuples()
        
        for ( status, ( value, range ) ) in bandwidth_rows:
            
            gauge = ClientGUICommon.TextAndGauge( self._bandwidth_panel )
            
            gauge.SetValue( status, value, range )
            
            self._rule_widgets.append( gauge )
            
            QP.AddToLayout( vbox, gauge, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        #
        
        self._refresh_account_button.setText( 'refresh account' )
        
        if self._service.CanSyncAccount( including_external_communication = False ):
            
            self._refresh_account_button.setEnabled( True )
            
        else:
            
            self._refresh_account_button.setEnabled( False )
            
        
        account_key = account.GetAccountKey()
        
        if account_key is None or account_key == '':
            
            self._copy_account_key_button.setEnabled( False )
            
        else:
            
            self._copy_account_key_button.setEnabled( True )
            
        
        menu_items = []
        
        p_s = account_type.GetPermissionStrings()
        
        if len( p_s ) == 0:
            
            menu_items.append( ( 'label', 'no special permissions', 'no special permissions', None ) )
            
        else:
            
            for s in p_s:
                
                menu_items.append( ( 'label', s, s, None ) )
                
            
        
        self._permissions_button.SetMenuItems( menu_items )
        
    
    def _RefreshAccount( self ):
        
        def do_it( service, my_updater ):
            
            try:
                
                service.SyncAccount( force = True )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                QP.CallAfter( QW.QMessageBox.critical, None, 'Error', str(e) )
                
            
            my_updater.Update()
            
        
        if HG.client_controller.options[ 'pause_repo_sync' ]:
            
            QW.QMessageBox.warning( self, 'Warning', 'All repositories are currently paused under the services->pause menu! Please unpause them and then try again!' )
            
            return
            
        
        if self._service.GetServiceType() in HC.REPOSITORIES and self._service.IsPausedNetworkSync():
            
            QW.QMessageBox.warning( self, 'Warning', 'Account sync is paused for this service! Please unpause it to refresh its account.' )
            
            return
            
        
        self._refresh_account_button.setEnabled( False )
        self._refresh_account_button.setText( 'fetching\u2026' )
        
        HG.client_controller.CallToThread( do_it, self._service, self._my_updater )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
class ReviewServiceRepositorySubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'repository sync' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._content_panel = QW.QWidget( self )
        
        self._metadata_st = ClientGUICommon.BetterStaticText( self )
        
        self._download_progress = ClientGUICommon.TextAndGauge( self )
        
        self._update_downloading_paused_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().pause, self._PausePlayUpdateDownloading )
        self._update_downloading_paused_button.setToolTip( 'pause/play update downloading' )
        
        self._update_processing_paused_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().pause, self._PausePlayUpdateProcessing )
        self._update_processing_paused_button.setToolTip( 'pause/play update processing' )
        
        self._processing_progress = ClientGUICommon.TextAndGauge( self )
        self._is_mostly_caught_up_st = ClientGUICommon.BetterStaticText( self )
        
        self._sync_remote_now_button = ClientGUICommon.BetterButton( self, 'download now', self._SyncRemoteNow )
        self._sync_processing_now_button = ClientGUICommon.BetterButton( self, 'process now', self._SyncProcessingNow )
        self._export_updates_button = ClientGUICommon.BetterButton( self, 'export updates', self._ExportUpdates )
        
        reset_menu_items = []
        
        reset_menu_items.append( ( 'normal', 'do a full metadata resync', 'Resync all update information.', self._DoAFullMetadataResync ) )
        
        self._reset_downloading_button = ClientGUIMenuButton.MenuButton( self, 'reset downloading', reset_menu_items )
        
        reset_menu_items = []
        
        reset_menu_items.append( ( 'normal', 'fill in definition gaps', 'Reprocess all definitions.', self._ReprocessDefinitions ) )
        reset_menu_items.append( ( 'normal', 'fill in content gaps', 'Reprocess all content.', self._ReprocessContent ) )
        reset_menu_items.append( ( 'separator', None, None, None ) )
        reset_menu_items.append( ( 'normal', 'wipe database data and reprocess from update files', 'Reset entire repository.', self._Reset ) )
        
        self._reset_processing_button = ClientGUIMenuButton.MenuButton( self, 'reset processing', reset_menu_items )
        
        #
        
        self._Refresh()
        
        #
        
        new_options = HG.client_controller.new_options
        
        if not new_options.GetBoolean( 'advanced_mode' ):
            
            self._export_updates_button.hide()
            self._reset_processing_button.hide()
            
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._sync_remote_now_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sync_processing_now_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._export_updates_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._reset_downloading_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._reset_processing_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.Add( self._metadata_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._download_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._update_downloading_paused_button, CC.FLAGS_ON_RIGHT )
        self.Add( self._processing_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._update_processing_paused_button, CC.FLAGS_ON_RIGHT )
        self.Add( self._is_mostly_caught_up_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _DoAFullMetadataResync( self ):
        
        if self._service.IsDueAFullMetadataResync():
            
            message = 'This service is already due a full metadata resync.'
            
            QW.QMessageBox.information( self, "Information", message )
            
            return
            
        
        name = self._service.GetName()
        
        message = 'This will flag the client to resync the information about which update files it should download. It will occur on the next download sync.'
        message += os.linesep * 2
        message += 'This is useful if the metadata archive has become unsynced, either due to a bug or a service switch. If it is not needed, it will not make any changes.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            self._service.DoAFullMetadataResync()
            
            self._my_updater.Update()
            
        
    
    def _ExportUpdates( self ):
        
        def qt_done():
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._export_updates_button.setText( 'export updates' )
            self._export_updates_button.setEnabled( True )
            
        
        def do_it( dest_dir, service ):
            
            try:
                
                update_hashes = service.GetUpdateHashes()
                
                num_to_do = len( update_hashes )
                
                if num_to_do == 0:
                    
                    QP.CallAfter( QW.QMessageBox.information, None, 'Information', 'No updates to export!' )
                    
                else:
                    
                    job_key = ClientThreading.JobKey( cancellable = True )
                    
                    try:
                        
                        job_key.SetVariable( 'popup_title', 'exporting updates for ' + service.GetName() )
                        HG.client_controller.pub( 'message', job_key )
                        
                        client_files_manager = HG.client_controller.client_files_manager
                        
                        for ( i, update_hash ) in enumerate( update_hashes ):
                            
                            ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                            
                            if should_quit:
                                
                                job_key.SetVariable( 'popup_text_1', 'Cancelled!' )
                                
                                return
                                
                            
                            try:
                                
                                update_path = client_files_manager.GetFilePath( update_hash, HC.APPLICATION_HYDRUS_UPDATE_CONTENT, check_file_exists = False )
                                
                                dest_path = os.path.join( dest_dir, update_hash.hex() )
                                
                                HydrusPaths.MirrorFile( update_path, dest_path )
                                
                            except HydrusExceptions.FileMissingException:
                                
                                continue
                                
                            finally:
                                
                                job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do ) )
                                job_key.SetVariable( 'popup_gauge_1', ( i, num_to_do ) )
                                
                            
                        
                        job_key.SetVariable( 'popup_text_1', 'Done!' )
                        
                    finally:
                        
                        job_key.DeleteVariable( 'popup_gauge_1' )
                        
                        job_key.Finish()
                        
                    
                
            finally:
                
                QP.CallAfter( qt_done )
                
            
        
        with QP.DirDialog( self, 'Select export location.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                path = dlg.GetPath()
                
                self._export_updates_button.setText( 'exporting\u2026' )
                self._export_updates_button.setEnabled( False )
                
                HG.client_controller.CallToThread( do_it, path, self._service )
                
            
        
    
    def _PausePlayUpdateDownloading( self ):
        
        self._service.PausePlayUpdateDownloading()
        
    
    def _PausePlayUpdateProcessing( self ):
        
        self._service.PausePlayUpdateProcessing()
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        self._sync_remote_now_button.setEnabled( False )
        self._sync_processing_now_button.setEnabled( False )
        
        #
        
        if self._service.IsPausedUpdateDownloading():
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._update_downloading_paused_button, CC.global_pixmaps().play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._update_downloading_paused_button, CC.global_pixmaps().pause )
            
        
        #
        
        if self._service.IsPausedUpdateProcessing():
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._update_processing_paused_button, CC.global_pixmaps().play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._update_processing_paused_button, CC.global_pixmaps().pause )
            
        
        #
        
        self._metadata_st.setText( self._service.GetNextUpdateDueString() )
        
        HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def _ReprocessDefinitions( self ):
        
        def do_it( service, my_updater ):
            
            service_key = service.GetServiceKey()
            
            HG.client_controller.WriteSynchronous( 'reprocess_repository', service_key, ( HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS, ) )
            
            my_updater.Update()
            
        
        name = self._service.GetName()
        
        message = 'This will command the client to reprocess all definition updates for {}. It will not delete anything.'.format( name )
        message += os.linesep * 2
        message += 'This is a only useful as a debug tool for filling in \'gaps\'. If you do not understand what this does, turn back now.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            HG.client_controller.CallToThread( do_it, self._service, self._my_updater )
            
        
    
    def _ReprocessContent( self ):
        
        def do_it( service, my_updater ):
            
            service_key = service.GetServiceKey()
            
            HG.client_controller.WriteSynchronous( 'reprocess_repository', service_key, ( HC.APPLICATION_HYDRUS_UPDATE_CONTENT, ) )
            
            my_updater.Update()
            
        
        name = self._service.GetName()
        
        message = 'This will command the client to reprocess all content updates for {}. It will not delete anything.'.format( name )
        message += os.linesep * 2
        message += 'This is a only useful as a debug tool for filling in \'gaps\'. If you do not understand what this does, turn back now.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            HG.client_controller.CallToThread( do_it, self._service, self._my_updater )
            
        
    
    def _Reset( self ):
        
        name = self._service.GetName()
        
        message = 'This will delete all the processed information for ' + name + ' from the database.' + os.linesep * 2 + 'Once the service is reset, you will have to reprocess everything from your downloaded update files. The client will naturally do this in its idle time as before, just starting over from the beginning.' + os.linesep * 2 + 'If you do not understand what this does, click no!'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            message = 'Seriously, are you absolutely sure?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.Accepted:
                
                self._service.Reset()
                
            
        
    
    def _SyncRemoteNow( self ):
        
        def do_it( service, my_updater ):
            
            service.SyncRemote()
            
            my_updater.Update()
            
        
        self._sync_remote_now_button.setEnabled( False )
        
        HG.client_controller.CallToThread( do_it, self._service, self._my_updater )
        
    
    def _SyncProcessingNow( self ):
        
        message = 'This will tell the database to process any possible outstanding update files right now.'
        message += os.linesep * 2
        message += 'You can still use the client while it runs, but it may make some things like autocomplete lookup a bit juddery.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            def do_it( service, my_updater ):
                
                service.SyncProcessUpdates( maintenance_mode = HC.MAINTENANCE_FORCED )
                
                my_updater.Update()
                
            
            self._sync_processing_now_button.setEnabled( False )
            
            HG.client_controller.CallToThread( do_it, self._service, self._my_updater )
            
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( download_text, download_value, processing_text, processing_value, range, is_mostly_caught_up ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._download_progress.SetValue( download_text, download_value, range )
            self._processing_progress.SetValue( processing_text, processing_value, range )
            
            if is_mostly_caught_up:
                
                caught_up_text = 'Client is caught up to service and can upload content.'
                
            else:
                
                caught_up_text = 'Still some processing to do until the client is caught up.'
                
            
            self._is_mostly_caught_up_st.setText( caught_up_text )
            
            if download_value == 0:
                
                self._export_updates_button.setEnabled( False )
                
            else:
                
                self._export_updates_button.setEnabled( True )
                
            
            if processing_value == 0:
                
                self._reset_processing_button.setEnabled( False )
                
            else:
                
                self._reset_processing_button.setEnabled( True )
                
            
            metadata_due = self._service.GetMetadata().UpdateDue( from_client = True )
            updates_due = download_value < range
            
            download_work_to_do = metadata_due or updates_due
            
            can_sync_download = self._service.CanSyncDownload()
            
            if download_work_to_do and can_sync_download:
                
                self._sync_remote_now_button.setEnabled( True )
                
            else:
                
                self._sync_remote_now_button.setEnabled( False )
                
            
            processing_work_to_do = processing_value < download_value
            
            can_sync_process = self._service.CanSyncProcess()
            
            if processing_work_to_do and can_sync_process:
                
                self._sync_processing_now_button.setEnabled( True )
                
            else:
                
                self._sync_processing_now_button.setEnabled( False )
                
            
        
        ( download_value, processing_value, range ) = HG.client_controller.Read( 'repository_progress', service.GetServiceKey() )
        
        is_mostly_caught_up = service.IsMostlyCaughtUp()
        
        download_text = 'downloaded ' + HydrusData.ConvertValueRangeToPrettyString( download_value, range )
        
        processing_text = 'processed ' + HydrusData.ConvertValueRangeToPrettyString( processing_value, range )
        
        QP.CallAfter( qt_code, download_text, download_value, processing_text, processing_value, range, is_mostly_caught_up )
        
    

class ReviewServiceIPFSSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'ipfs' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        interaction_panel = ClientGUIPanels.IPFSDaemonStatusAndInteractionPanel( self, self.GetService )
        
        self._ipfs_shares_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._ipfs_shares = ClientGUIListCtrl.BetterListCtrl( self._ipfs_shares_panel, CGLC.COLUMN_LIST_IPFS_SHARES.ID, 6, self._ConvertDataToListCtrlTuple, delete_key_callback = self._Unpin, activation_callback = self._SetNotes )
        
        self._ipfs_shares_panel.SetListCtrl( self._ipfs_shares )
        
        self._ipfs_shares_panel.AddButton( 'copy multihashes', self._CopyMultihashes, enabled_only_on_selection = True )
        self._ipfs_shares_panel.AddButton( 'show selected in main gui', self._ShowSelectedInNewPages, enabled_only_on_selection = True )
        self._ipfs_shares_panel.AddButton( 'set notes', self._SetNotes, enabled_only_on_selection = True )
        self._ipfs_shares_panel.AddButton( 'unpin selected', self._Unpin, enabled_only_on_selection = True )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( interaction_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._ipfs_shares_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _ConvertDataToListCtrlTuple( self, data ):
        
        ( multihash, num_files, total_size, note ) = data
        
        pretty_multihash = multihash
        pretty_num_files = HydrusData.ToHumanInt( num_files )
        pretty_total_size = HydrusData.ToHumanBytes( total_size )
        pretty_note = note
        
        display_tuple = ( pretty_multihash, pretty_num_files, pretty_total_size, pretty_note )
        sort_tuple = ( multihash, num_files, total_size, note )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopyMultihashes( self ):
        
        multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetData( only_selected = True ) ]
        
        if len( multihashes ) == 0:
            
            multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetData() ]
            
        
        if len( multihashes ) > 0:
            
            multihash_prefix = self._service.GetMultihashPrefix()
            
            text = os.linesep.join( ( multihash_prefix + multihash for multihash in multihashes ) )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def _SetNotes( self ):
        
        datas = self._ipfs_shares.GetData( only_selected = True )
        
        if len( datas ) > 0:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Set a note for these shares.' ) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    note = dlg.GetValue()
                    
                    content_updates = []
                    
                    for ( multihash, num_files, total_size, old_note ) in datas:
                        
                        hashes = HG.client_controller.Read( 'service_directory', self._service.GetServiceKey(), multihash )
                        
                        content_update_row = ( hashes, multihash, note )
                        
                        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_ADD, content_update_row ) )
                        
                    
                    HG.client_controller.Write( 'content_updates', { self._service.GetServiceKey() : content_updates } )
                    
                    self._my_updater.Update()
                    
                
            
        
    
    def _ShowSelectedInNewPages( self ):
        
        def qt_done():
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._ipfs_shares_panel.setEnabled( True )
            
        
        def do_it( service_key, pages_of_hashes_to_show ):
            
            try:
                
                for ( multihash, num_files, total_size, note ) in shares:
                    
                    hashes = HG.client_controller.Read( 'service_directory', service_key, multihash )
                    
                    HG.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes, page_name = 'ipfs directory' )
                    
                    time.sleep( 0.5 )
                    
                
            finally:
                
                QP.CallAfter( qt_done )
                
            
        
        shares = self._ipfs_shares.GetData( only_selected = True )
        
        self._ipfs_shares_panel.setEnabled( False )
        
        HG.client_controller.CallToThread( do_it, self._service.GetServiceKey(), shares )
        
    
    def _Unpin( self ):
        
        def qt_done():
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._ipfs_shares_panel.setEnabled( True )
            
            self._my_updater.Update()
            
        
        def do_it( service, multihashes ):
            
            try:
                
                for multihash in multihashes:
                    
                    service.UnpinDirectory( multihash )
                    
                
            finally:
                
                QP.CallAfter( qt_done )
                
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Unpin (remove) all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetData( only_selected = True ) ]
            
            self._ipfs_shares_panel.setEnabled( False )
            
            HG.client_controller.CallToThread( do_it, self._service, multihashes )
            
        
    
    def GetService( self ):
        
        return self._service
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( ipfs_shares ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            # list of ( multihash, num_files, total_size, note )
            
            self._ipfs_shares.SetData( ipfs_shares )
            
        
        ipfs_shares = HG.client_controller.Read( 'service_directories', service.GetServiceKey() )
        
        QP.CallAfter( qt_code, ipfs_shares )
        
    

class ReviewServiceLocalBooruSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'local booru' )
        
        self._service = service
        
        self._share_key_info = {}
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._service_status = ClientGUICommon.BetterStaticText( self )
        
        booru_share_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        self._booru_shares = ClientGUIListCtrl.BetterListCtrl( booru_share_panel, CGLC.COLUMN_LIST_LOCAL_BOORU_SHARES.ID, 10, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        booru_share_panel.SetListCtrl( self._booru_shares )
        
        booru_share_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        booru_share_panel.AddButton( 'delete', self._Delete, enabled_only_on_selection = True )
        booru_share_panel.AddSeparator()
        booru_share_panel.AddButton( 'open in new page', self._OpenSearch, enabled_only_on_selection = True )
        booru_share_panel.AddButton( 'copy internal share url', self._CopyInternalShareURL, enabled_check_func = self._CanCopyURL )
        booru_share_panel.AddButton( 'copy external share url', self._CopyExternalShareURL, enabled_check_func = self._CanCopyURL )
        
        self._booru_shares.Sort()
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._service_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( booru_share_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _CanCopyURL( self ):
        
        has_selected = self._booru_shares.HasSelected()
        service_is_running = self._service.GetPort() is not None
        
        return has_selected and service_is_running
        
    
    def _ConvertDataToListCtrlTuples( self, share_key ):
        
        info = self._share_key_info[ share_key ]
        
        name = info[ 'name' ]
        text = info[ 'text' ]
        timeout = info[ 'timeout' ]
        hashes = info[ 'hashes' ]
        
        num_hashes = len( hashes )
        
        pretty_name = name
        pretty_text = text
        pretty_timeout = HydrusData.ConvertTimestampToPrettyExpires( timeout )
        pretty_hashes = HydrusData.ToHumanInt( num_hashes )
        
        sort_timeout = ClientGUIListCtrl.SafeNoneInt( timeout )
        
        display_tuple = ( pretty_name, pretty_text, pretty_timeout, pretty_hashes )
        sort_tuple = ( name, text, sort_timeout, num_hashes )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopyExternalShareURL( self ):
        
        internal_port = self._service.GetPort()
        
        if internal_port is None:
            
            QW.QMessageBox.warning( self, 'Warning', 'The local booru is not currently running!' )
            
        
        urls = []
        
        for share_key in self._booru_shares.GetData( only_selected = True ):
            
            try:
                
                url = self._service.GetExternalShareURL( share_key )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                QW.QMessageBox.critical( self, 'Error', 'Unfortunately, could not generate an external URL: {}'.format(e) )
                
                return
                
            
            urls.append( url )
            
        
        text = os.linesep.join( urls )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _CopyInternalShareURL( self ):
        
        internal_port = self._service.GetPort()
        
        if internal_port is None:
            
            QW.QMessageBox.warning( self, 'Warning', 'The local booru is not currently running!' )
            
        
        urls = []
        
        for share_key in self._booru_shares.GetData( only_selected = True ):
            
            url = self._service.GetInternalShareURL( share_key )
            
            urls.append( url )
            
        
        text = os.linesep.join( urls )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            for share_key in self._booru_shares.GetData( only_selected = True ):
                
                HG.client_controller.Write( 'delete_local_booru_share', share_key )
                
            
            self._booru_shares.DeleteSelected()
            
        
    
    def _Edit( self ):
        
        for share_key in self._booru_shares.GetData( only_selected = True ):
            
            info = self._share_key_info[ share_key ]
            
            name = info[ 'name' ]
            text = info[ 'text' ]
            timeout = info[ 'timeout' ]
            hashes = info[ 'hashes' ]
            
            with ClientGUIDialogs.DialogInputLocalBooruShare( self, share_key, name, text, timeout, hashes, new_share = False) as dlg:
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    ( share_key, name, text, timeout, hashes ) = dlg.GetInfo()
                    
                    info = {}
                    
                    info[ 'name' ] = name
                    info[ 'text' ] = text
                    info[ 'timeout' ] = timeout
                    info[ 'hashes' ] = hashes
                    
                    HG.client_controller.Write( 'local_booru_share', share_key, info )
                    
                else:
                    
                    break
                    
                
            
        
        self._Refresh()
        
    
    def _OpenSearch( self ):
        
        for share_key in self._booru_shares.GetData( only_selected = True ):
            
            info = self._share_key_info[ share_key ]
            
            name = info[ 'name' ]
            hashes = info[ 'hashes' ]
            
            HG.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes, page_name = 'booru share: ' + name )
            
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        port = self._service.GetPort()
        
        if port is None:
            
            status = 'The local booru is not running.'
            
        else:
            
            status = 'The local booru should be running on port {}.'.format( port )
            
            upnp_port = self._service.GetUPnPPort()
            
            if upnp_port is not None:
                
                status += ' It should be open via UPnP on external port {}.'.format( upnp_port )
                
            
        
        self._service_status.setText( status )
        
        HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( booru_shares ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._share_key_info.update( booru_shares )
            
            self._booru_shares.SetData( list(booru_shares.keys()) )
            
            self._booru_shares.Sort()
            
        
        booru_shares = HG.client_controller.Read( 'local_booru_shares' )
        
        QP.CallAfter( qt_code, booru_shares )
        
    

class ReviewServiceRatingSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'ratings' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._rating_info_st = ClientGUICommon.BetterStaticText( self )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'for deleted files', 'delete all set ratings for files that have since been deleted', HydrusData.Call( self._ClearRatings, 'delete_for_deleted_files', 'deleted files' ) ) )
        menu_items.append( ( 'normal', 'for all non-local files', 'delete all set ratings for files that are not in this client right now', HydrusData.Call( self._ClearRatings, 'delete_for_non_local_files', 'non-local files' ) ) )
        menu_items.append( ( 'separator', None, None, None ) )
        menu_items.append( ( 'normal', 'for all files', 'delete all set ratings for all files', HydrusData.Call( self._ClearRatings, 'delete_for_all_files', 'ALL FILES' ) ) )
        
        self._clear_deleted = ClientGUIMenuButton.MenuButton( self, 'clear ratings', menu_items )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._rating_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._clear_deleted, CC.FLAGS_ON_RIGHT )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _ClearRatings( self, advanced_action, action_description ):
        
        message = 'Delete any ratings on this service for {}? THIS CANNOT BE UNDONE'.format( action_description )
        message += os.linesep * 2
        message += 'Please note a client restart is needed to see the ratings disappear in media views.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADVANCED, advanced_action )
            
            service_keys_to_content_updates = { self._service.GetServiceKey() : [ content_update ] }
            
            HG.client_controller.Write( 'content_updates', service_keys_to_content_updates, publish_content_updates = False )
            
            HG.client_controller.pub( 'service_updated', self._service )
            
        
    
    def _Refresh( self ):
        
        HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( text ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._rating_info_st.setText( text )
            
        
        service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
        
        num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        
        text = HydrusData.ToHumanInt( num_files ) + ' files are rated'
        
        QP.CallAfter( qt_code, text )
        
    

class ReviewServiceTagSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'tags' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._tag_info_st = ClientGUICommon.BetterStaticText( self )
        
        self._tag_migration = ClientGUICommon.BetterButton( self, 'migrate tags', self._MigrateTags )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._tag_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._tag_migration, CC.FLAGS_ON_RIGHT )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _MigrateTags( self ):
        
        tlw = HG.client_controller.GetMainTLW()
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( tlw, 'migrate tags' )
        
        panel = ClientGUIScrolledPanelsReview.MigrateTagsPanel( frame, self._service.GetServiceKey() )
        
        frame.SetPanel( panel )
        
    
    def _Refresh( self ):
        
        HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( text ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._tag_info_st.setText( text )
            
        
        service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
        
        num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
        num_mappings = service_info[ HC.SERVICE_INFO_NUM_MAPPINGS ]
        
        text = HydrusData.ToHumanInt( num_mappings ) + ' total mappings involving ' + HydrusData.ToHumanInt( num_tags ) + ' different tags on ' + HydrusData.ToHumanInt( num_files ) + ' different files'
        
        if service.GetServiceType() == HC.TAG_REPOSITORY:
            
            num_deleted_mappings = service_info[ HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ]
            
            text += ' - ' + HydrusData.ToHumanInt( num_deleted_mappings ) + ' deleted mappings'
            
        
        QP.CallAfter( qt_code, text )
        
    

class ReviewServiceTrashSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'trash' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._clear_trash = ClientGUICommon.BetterButton( self, 'clear trash', self._ClearTrash )
        self._clear_trash.setEnabled( False )
        
        #
        
        self._Refresh()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._clear_trash, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _ClearTrash( self ):
        
        message = 'This will completely clear your trash of all its files, deleting them permanently from the client. This operation cannot be undone.'
        message += os.linesep * 2
        message += 'If you have many files in your trash, it will take some time to complete and for all the files to eventually be deleted.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.Accepted:
            
            def do_it( service ):
                
                hashes = HG.client_controller.Read( 'trash_hashes' )
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
                
                service_keys_to_content_updates = { CC.TRASH_SERVICE_KEY : [ content_update ] }
                
                HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
                HG.client_controller.pub( 'service_updated', service )
                
            
            self._clear_trash.setEnabled( False )
            
            HG.client_controller.CallToThread( do_it, self._service )
            
        
    
    def _Refresh( self ):
        
        HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( num_files ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._clear_trash.setEnabled( num_files > 0 )
            
        
        service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
        
        num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        
        QP.CallAfter( qt_code, num_files )
        
    
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
            
            page = ReviewServicePanel( services_notebook, service )
            
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
        
    
