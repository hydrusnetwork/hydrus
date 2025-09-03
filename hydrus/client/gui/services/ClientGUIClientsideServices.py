import os
import time

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusPaths
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworkVariableHandling

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientPaths
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIAPI
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIPanels
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.media import ClientGUIMediaSimpleActions
from hydrus.client.gui.metadata import ClientGUIMigrateTags
from hydrus.client.gui.metadata import ClientGUITagFilter
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUIBandwidth
from hydrus.client.gui.widgets import ClientGUIColourPicker
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientRatings
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking import ClientNetworkingJobs

class ManageClientServicesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, auto_account_creation_service_key = None ):
        
        super().__init__( parent )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_MANAGE_SERVICES.ID, self._ConvertServiceToDisplayTuple, self._ConvertServiceToSortTuple )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrlTreeView( self, 25, model, delete_key_callback = self._Delete, activation_callback = self._Edit)
        
        menu_template_items = []
        
        for service_type in HC.ADDREMOVABLE_SERVICES:
            
            service_string = HC.service_string_lookup[ service_type ]
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( service_string, 'Add a new {}.'.format( service_string ), HydrusData.Call( self._Add, service_type ) ) )
            
        
        # TODO: wrap this list in a panel and improve these buttons' "enabled logic"
        
        self._add_button = ClientGUIMenuButton.MenuButton( self, 'add', menu_template_items )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        #
        
        self._original_services = CG.client_controller.services_manager.GetServices()
        
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
        
        if auto_account_creation_service_key is not None:
            
            CG.client_controller.CallLaterQtSafe( self, 1.2, 'auto-account creation spawn', self._Edit, auto_account_creation_service_key = auto_account_creation_service_key )
            
        
    
    def _Add( self, service_type ):
        
        service_key = HydrusData.GenerateKey()
        name = 'new service'
        
        service = ClientServices.GenerateService( service_key, service_type, name )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit service' ) as dlg:
            
            panel = EditClientServicePanel( dlg, service )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                new_service = panel.GetValue()
                
                HydrusSerialisable.SetNonDupeName( new_service, self._GetExistingNames(), do_casefold = True )
                
                self._listctrl.AddData( new_service, select_sort_and_scroll = True )
                
            
        
    
    def _ConvertServiceToDisplayTuple( self, service ):
        
        service_type = service.GetServiceType()
        name = service.GetName()
        
        deletable = service_type in HC.ADDREMOVABLE_SERVICES
        
        pretty_service_type = HC.service_string_lookup[ service_type ]
        
        if deletable:
            
            if service_type in HC.MUST_HAVE_AT_LEAST_ONE_SERVICES or service_type in HC.MUST_BE_EMPTY_OF_FILES_SERVICES:
                
                clauses = []
                
                if service_type in HC.MUST_BE_EMPTY_OF_FILES_SERVICES:
                    
                    clauses.append( 'must be empty of files' )
                    
                if service_type in HC.MUST_HAVE_AT_LEAST_ONE_SERVICES:
                    
                    clauses.append( 'must have at least one' )
                    
                
                pretty_deletable = ', '.join( clauses )
                
            else:
                
                pretty_deletable = 'yes'
                
            
        else:
            
            pretty_deletable = ''
            
        
        return ( name, pretty_service_type, pretty_deletable )
        
    
    def _ConvertServiceToSortTuple( self, service ):
        
        service_type = service.GetServiceType()
        name = service.GetName()
        
        deletable = service_type in HC.ADDREMOVABLE_SERVICES
        
        pretty_service_type = HC.service_string_lookup[ service_type ]
        
        if deletable:
            
            if service_type in HC.MUST_HAVE_AT_LEAST_ONE_SERVICES or service_type in HC.MUST_BE_EMPTY_OF_FILES_SERVICES:
                
                clauses = []
                
                if service_type in HC.MUST_BE_EMPTY_OF_FILES_SERVICES:
                    
                    clauses.append( 'must be empty of files' )
                    
                if service_type in HC.MUST_HAVE_AT_LEAST_ONE_SERVICES:
                    
                    clauses.append( 'must have at least one' )
                    
                
            
        
        return ( name, pretty_service_type, deletable )
        
    
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
                
                ClientGUIDialogsMessage.ShowInformation( self, message )
                
                return
                
            
        
        for service_type in HC.MUST_BE_EMPTY_OF_FILES_SERVICES:
            
            for service in deletable_services:
                
                if service.GetServiceType() == service_type and service in self._original_services:
                    
                    service_info = CG.client_controller.Read( 'service_info', service.GetServiceKey() )
                    
                    num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
                    
                    if num_files > 0:
                        
                        message = 'The service {} needs to be empty before it can be deleted, but it seems to have {} files in it! Please delete or migrate all the files from it and then try again.'.format( service.GetName(), HydrusNumbers.ToHumanInt( num_files ) )
                        
                        ClientGUIDialogsMessage.ShowInformation( self, message )
                        
                        return
                        
                    
            
        
        if len( deletable_services ) > 0:
            
            result = ClientGUIDialogsQuick.GetYesNo( self, 'Delete the selected services?' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._listctrl.DeleteDatas( deletable_services )
                
            
        
    
    def _Edit( self, auto_account_creation_service_key = None ):
        
        if auto_account_creation_service_key is None:
            
            selected_services = self._listctrl.GetData( only_selected = True )
            
        else:
            
            selected_services = [ service for service in self._listctrl.GetData() if service.GetServiceKey() == auto_account_creation_service_key ]
            
        
        if len( selected_services ) == 0:
            
            return
            
        
        service = selected_services[0]
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit service' ) as dlg:
            
            panel = EditClientServicePanel( dlg, service, auto_account_creation_service_key = auto_account_creation_service_key )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                edited_service = panel.GetValue()
                
                existing_names = self._GetExistingNames()
                
                existing_names.discard( service.GetName() )
                
                HydrusSerialisable.SetNonDupeName( edited_service, existing_names, do_casefold = True )
                
                self._listctrl.ReplaceData( service, edited_service, sort_and_scroll = True )
                
            
        
    
    def CommitChanges( self ):
        
        services = self._listctrl.GetData()
        
        CG.client_controller.SetServices( services )
        
        CG.client_controller.pub( 'clear_thumbnail_cache' )
        
    
    def UserIsOKToOK( self ):
        
        services = self._listctrl.GetData()
        
        new_service_keys = { service.GetServiceKey() for service in services }
        
        deletee_services = [ service for service in self._original_services if service.GetServiceKey() not in new_service_keys ]
        
        deletee_service_names = [ service.GetName() for service in deletee_services ]
        tag_service_in_deletes = True in ( service.GetServiceType() in HC.REAL_TAG_SERVICES for service in deletee_services )
        
        if len( deletee_service_names ) > 0:
            
            message = 'You are about to delete the following services:'
            message += '\n' * 2
            message += '\n'.join( deletee_service_names )
            message += '\n' * 2
            message += 'Are you absolutely sure this is correct?'
            
            if tag_service_in_deletes:
                
                message += '\n' * 2
                message += 'If the tag service you are deleting is very large, this operation may take a very very long time. You client will lock up until it is done.'
                
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return False
                
            
        
        return True
        
    
class EditClientServicePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, service, auto_account_creation_service_key = None ):
        
        super().__init__( parent )
        
        duplicate_service = service.Duplicate()
        
        ( self._service_key, self._service_type, name, self._dictionary ) = duplicate_service.ToTuple()
        
        self._service_panel = EditServiceSubPanel( self, name )
        
        self._panels = []
        
        if self._service_type in HC.REMOTE_SERVICES:
            
            remote_panel = EditServiceRemoteSubPanel( self, self._service_type, self._dictionary )
            
            self._panels.append( remote_panel )
            
        
        if self._service_type in HC.RESTRICTED_SERVICES:
            
            self._panels.append( EditServiceRestrictedSubPanel( self, self._service_key, remote_panel, self._service_type, self._dictionary, auto_account_creation_service_key = auto_account_creation_service_key ) )
            
        
        if self._service_type in HC.REAL_TAG_SERVICES:
            
            self._panels.append( EditServiceTagSubPanel( self, self._dictionary ) )
            
        
        if self._service_type == HC.CLIENT_API_SERVICE:
            
            self._panels.append( EditServiceClientServerSubPanel( self, self._service_type, self._dictionary ) )
            
        
        if self._service_type in HC.RATINGS_SERVICES:
            
            self._panels.append( EditServiceRatingsSubPanel( self, self._service_type, self._dictionary ) )
            
            if self._service_type in HC.STAR_RATINGS_SERVICES:
                
                self._panels.append( EditServiceStarRatingsSubPanel( self, self._dictionary ) )
                
                if self._service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    self._panels.append( EditServiceRatingsNumericalSubPanel( self, self._dictionary ) )
                    
                
            
        
        if self._service_type == HC.IPFS:
            
            self._panels.append( EditServiceIPFSSubPanel( self, self._dictionary ) )
            
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._service_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for panel in self._panels:
            
            QP.AddToLayout( vbox, panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        vbox.addStretch( 0 )
        
        self.widget().setLayout( vbox )
        
    
    def _GetArchiveNameToDisplay( self, portable_hta_path, namespaces ):
        
        hta_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_hta_path )
        
        if len( namespaces ) == 0:
            
            name_to_display = hta_path
            
        else:
            
            name_to_display = hta_path + ' (' + ', '.join( HydrusTags.ConvertUglyNamespacesToPrettyStrings( namespaces ) ) + ')'
            
        
        return name_to_display
        
    
    def GetValue( self ):
        
        name = self._service_panel.GetValue()
        
        dictionary = self._dictionary.Duplicate()
        
        for panel in self._panels:
            
            dictionary_part = panel.GetValue()
            
            dictionary.update( dictionary_part )
            
        
        return ClientServices.GenerateService( self._service_key, self._service_type, name, dictionary )
        
    

class EditServiceSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, name ):
        
        super().__init__( parent, 'name' )
        
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
        
        super().__init__( parent, 'network connection' )
        
        self._service_type = service_type
        
        credentials = dictionary[ 'credentials' ]
        
        self._host = QW.QLineEdit( self )
        self._port = ClientGUICommon.BetterSpinBox( self, min=1, max=65535, width = 80 )
        
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
                
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
            self._test_address_button.setEnabled( True )
            self._test_address_button.setText( 'test address' )
            
        
        def do_it():
            
            full_host = credentials.GetPortedAddress()
            
            url = scheme + full_host + '/' + request
            
            if self._service_type == HC.IPFS:
                
                network_job = ClientNetworkingJobs.NetworkJobIPFS( url )
                
            else:
                
                network_job = ClientNetworkingJobs.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
                
            
            network_job.OnlyTryConnectionOnce()
            network_job.OverrideBandwidth()
            
            network_job.SetForLogin( True )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
            try:
                
                network_job.WaitUntilDone()
                
                CG.client_controller.CallAfter( self, qt_done, 'Looks good!' )
                
            except HydrusExceptions.NetworkException as e:
                
                CG.client_controller.CallAfter( self, qt_done, 'Problem with that address: ' + str(e) )
                
            
        
        try:
            
            credentials = self.GetCredentials()
            
        except HydrusExceptions.VetoException as e:
            
            message = str( e )
            
            if len( message ) > 0:
                
                ClientGUIDialogsMessage.ShowWarning( self, message )
                
            
            return
            
        
        if self._service_type == HC.IPFS:
            
            scheme = 'http://'
            request = 'api/v0/version'
            
        else:
            
            scheme = 'https://'
            request = ''
            
        
        self._test_address_button.setEnabled( False )
        self._test_address_button.setText( 'testing' + HC.UNICODE_ELLIPSIS )
        
        CG.client_controller.CallToThread( do_it )
        
    
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
    
    def __init__( self, parent, service_key, remote_panel: EditServiceRemoteSubPanel, service_type, dictionary, auto_account_creation_service_key = None ):
        
        super().__init__( parent, 'hydrus network' )
        
        self._service_key = service_key
        self._remote_panel = remote_panel
        self._service_type = service_type
        
        self._original_credentials = dictionary[ 'credentials' ]
        
        self._access_key = QW.QLineEdit( self )
        
        self._auto_register = ClientGUICommon.BetterButton( self, 'check for automatic account creation', self._STARTFetchAutoAccountCreationAccountTypes )
        self._test_credentials_button = ClientGUICommon.BetterButton( self, 'test access key', self._STARTTestCredentials )
        self._register = ClientGUICommon.BetterButton( self, 'create an account with a registration token', self._EnterRegistrationKey )
        
        #
        
        if self._original_credentials.HasAccessKey():
            
            self._access_key.setText( self._original_credentials.GetAccessKey().hex() )
            
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._auto_register, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._register, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._test_credentials_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        st = ClientGUICommon.BetterStaticText( self, 'DO NOT SHARE YOUR ACCESS KEY WITH ANYONE, EVEN SERVER MODS' )
        
        st.setObjectName( 'HydrusWarning' )
        
        self.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        wrapped_access_key = ClientGUICommon.WrapInText( self._access_key, self, 'access key: ' )
        
        self.Add( wrapped_access_key, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        self._UpdateButtons()
        
        self._remote_panel.becameValidSignal.connect( self._UpdateButtons )
        self._remote_panel.becameInvalidSignal.connect( self._UpdateButtons )
        
        if auto_account_creation_service_key is not None:
            
            CG.client_controller.CallLaterQtSafe( self, 1.2, 'auto-account service spawn', self._STARTFetchAutoAccountCreationAccountTypes )
            
        
    
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
            
            full_host = credentials.GetPortedAddress()
            
            url = 'https://{}/auto_create_account_types'.format( full_host )
            
            network_job = ClientNetworkingJobs.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
            
            network_job.OnlyTryConnectionOnce()
            network_job.OverrideBandwidth()
            
            network_job.SetForLogin( True )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
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
        
        message = 'Enter the registration token.'
        
        try:
            
            registration_key_encoded = ClientGUIDialogsQuick.EnterText( self, message )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        if registration_key_encoded[0] == 'r':
            
            registration_key_encoded = registration_key_encoded[1:]
            
        
        if registration_key_encoded == 'init':
            
            registration_key = b'init'
            
        else:
            
            try:
                
                registration_key = bytes.fromhex( registration_key_encoded )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem parsing!', 'Could not parse that registration token!' )
                
                return
                
            
        
        self._STARTGetAccessKeyFromRegistrationKey( registration_key )
        
    
    def _STARTAutoCreateAccount( self, account_type: HydrusNetwork.AccountType ):
        
        credentials = self._remote_panel.GetCredentials()
        
        def work_callable():
            
            full_host = credentials.GetPortedAddress()
            
            # get a registration token
            
            url = 'https://{}/auto_create_registration_key?account_type_key={}'.format( full_host, account_type.GetAccountTypeKey().hex() )
            
            network_job = ClientNetworkingJobs.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
            
            network_job.OnlyTryConnectionOnce()
            network_job.OverrideBandwidth()
            
            network_job.SetForLogin( True )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
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
            
            full_host = credentials.GetPortedAddress()
            
            url = 'https://{}/access_key?registration_key={}'.format( full_host, registration_key.hex() )
            
            network_job = ClientNetworkingJobs.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
            
            network_job.OnlyTryConnectionOnce()
            network_job.OverrideBandwidth()
            
            network_job.SetForLogin( True )
            
            CG.client_controller.network_engine.AddJob( network_job )
            
            network_job.WaitUntilDone()
            
            network_bytes = network_job.GetContentBytes()
            
            parsed_response_args = HydrusNetworkVariableHandling.ParseNetworkBytesToParsedHydrusArgs( network_bytes )
            
            access_key = parsed_response_args[ 'access_key' ]
            
            return access_key
            
        
        def publish_callable( access_key ):
            
            access_key_encoded = access_key.hex()
            
            self._access_key.setText( access_key_encoded )
            
            self._EnableDisableButtons( True )
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Looks good!' )
            
        
        def errback_ui_cleanup_callable():
            
            self._EnableDisableButtons( True )
            
        
        self._EnableDisableButtons( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
        
        job.start()
        
    
    def _SelectAccountTypeForAutoAccountCreation( self, account_types: list[ HydrusNetwork.AccountType ] ):
        
        if len( account_types ) == 0:
            
            ClientGUIDialogsMessage.ShowInformation( self, 'Sorry, this server does not support automatic account creation!' )
            
        else:
            
            unavailable_account_types = [ account_type for account_type in account_types if not account_type.CanAutoCreateAccountNow() ]
            available_account_types = [ account_type for account_type in account_types if account_type.CanAutoCreateAccountNow() ]
            
            unavailable_text = ''
            
            if len( unavailable_account_types ) > 0:
                
                unavailable_texts = []
                
                for account_type in unavailable_account_types:
                    
                    ( num_accounts, time_delta ) = account_type.GetAutoCreateAccountVelocity()
                    
                    history = account_type.GetAutoCreateAccountHistory()
                    
                    text = '{} - {}'.format( account_type.GetTitle(), history.GetWaitingEstimate( HC.BANDWIDTH_TYPE_REQUESTS, time_delta, num_accounts ) )
                    
                    unavailable_texts.append( text )
                    
                
                unavailable_text = '\n' * 2
                unavailable_text += 'These other account types are currently in short supply and will be available after a delay:'
                unavailable_text += '\n' * 2
                unavailable_text += '\n'.join( unavailable_texts )
                
            
            if len( available_account_types ) == 1:
                
                account_type = available_account_types[ 0 ]
                
                message = 'This server offers auto-creation of a "{}" account type. Is this ok?'.format( account_type.GetTitle() )
                message += unavailable_text
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message, title = 'One account type available' )
                
                if result == QW.QDialog.DialogCode.Accepted:
                    
                    self._STARTAutoCreateAccount( account_type )
                    
                
            elif len( available_account_types ) > 0:
                
                message = 'Please select which account type you would like to create.'
                message += unavailable_text
                
                choice_tuples = [ ( account_type.GetTitle(), account_type, ', '.join( account_type.GetPermissionStrings() ) ) for account_type in available_account_types ]
                
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
                
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
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
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
        def errback_ui_cleanup_callable():
            
            self._EnableDisableButtons( True )
            
        
        self._EnableDisableButtons( False )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_ui_cleanup_callable = errback_ui_cleanup_callable )
        
        job.start()
        
    
    def GetCredentials( self ):
        
        credentials = self._remote_panel.GetCredentials()
        
        access_key_hex = self._access_key.text()
        
        if access_key_hex.startswith( 'r' ):
            
            raise HydrusExceptions.VetoException( 'The entered access key starts with an \'r\'! Is it actually a registration token?' )
            
        
        try:
            
            access_key = bytes.fromhex( access_key_hex )
            
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
            
            CG.client_controller.network_engine.session_manager.ClearSession( network_context )
            
        
        dictionary_part[ 'credentials' ] = credentials
        
        return dictionary_part
        
    

class EditServiceClientServerSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service_type, dictionary ):
        
        super().__init__( parent, 'client api' )
        
        self._client_server_options_panel = ClientGUICommon.StaticBox( self, 'options' )
        
        if service_type == HC.CLIENT_API_SERVICE:
            
            name = 'client api'
            default_port = 45869
            
        
        self._run_the_service = QW.QCheckBox( self._client_server_options_panel )
        
        self._port = ClientGUICommon.BetterSpinBox( self._client_server_options_panel, min = 1, max = 65535 )
        
        self._allow_non_local_connections = QW.QCheckBox( self._client_server_options_panel )
        self._allow_non_local_connections.setToolTip( ClientGUIFunctions.WrapToolTip( 'Allow other computers on the network to talk to use service. If unchecked, only localhost can talk to it. On Windows, the first time you start a local service that allows non-local connections, you will get the Windows firewall popup dialog when you ok the main services dialog.' ) )
        
        self._use_https = QW.QCheckBox( self._client_server_options_panel )
        self._use_https.setToolTip( ClientGUIFunctions.WrapToolTip( 'Host the server using https instead of http. This uses a self-signed certificate, stored in your db folder, which is imperfect but better than straight http. Your software (e.g. web browser testing the Client API welcome page) may need to go through a manual \'approve this ssl certificate\' process before it can work. If you host your client on a real DNS domain and acquire your own signed certificate, you can replace the cert+key file pair with that.' ) )
        
        self._support_cors = QW.QCheckBox( self._client_server_options_panel )
        self._support_cors.setToolTip( ClientGUIFunctions.WrapToolTip( 'Have this server support Cross-Origin Resource Sharing, which allows web browsers to access it off other domains. Turn this on if you want to access this service through a web-based wrapper (e.g. a booru wrapper) hosted on another domain.' ) )
        
        self._log_requests = QW.QCheckBox( self._client_server_options_panel )
        self._log_requests.setToolTip( ClientGUIFunctions.WrapToolTip( 'Hydrus server services will write a brief anonymous line to the log for every request made, but for the client services this tends to be a bit spammy. You probably want this off unless you are testing something.' ) )
        
        self._use_normie_eris = QW.QCheckBox( self._client_server_options_panel )
        self._use_normie_eris.setToolTip( ClientGUIFunctions.WrapToolTip( 'Use alternate ASCII art on the root page of the server.' ) )
        
        self._upnp = ClientGUICommon.NoneableSpinCtrl( self._client_server_options_panel, 55555, none_phrase = 'do not forward port', max = 65535 )
        
        self._external_scheme_override = ClientGUICommon.NoneableTextCtrl( self._client_server_options_panel, 'https' )
        self._external_host_override = ClientGUICommon.NoneableTextCtrl( self._client_server_options_panel, 'host.com' )
        self._external_port_override = ClientGUICommon.NoneableTextCtrl( self._client_server_options_panel, '12345' )
        
        self._external_port_override.setToolTip( ClientGUIFunctions.WrapToolTip( 'Setting this to a non-none empty string will forego the \':\' in the URL.' ) )
        
        self._bandwidth_rules = ClientGUIBandwidth.BandwidthRulesCtrl( self._client_server_options_panel, dictionary[ 'bandwidth_rules' ] )
        
        #
        
        self._port.setValue( default_port )
        self._upnp.SetValue( default_port )
        
        self._run_the_service.setChecked( dictionary[ 'port' ] is not None )
        
        if dictionary[ 'port' ] is not None:
            
            self._port.setValue( dictionary[ 'port' ] )
            
        
        self._upnp.SetValue( dictionary[ 'upnp_port' ] )
        
        self._allow_non_local_connections.setChecked( dictionary[ 'allow_non_local_connections' ] )
        self._use_https.setChecked( dictionary[ 'use_https' ] )
        self._support_cors.setChecked( dictionary[ 'support_cors' ] )
        self._log_requests.setChecked( dictionary[ 'log_requests' ] )
        self._use_normie_eris.setChecked( dictionary[ 'use_normie_eris' ] )
        
        self._external_scheme_override.SetValue( dictionary[ 'external_scheme_override' ] )
        self._external_host_override.SetValue( dictionary[ 'external_host_override' ] )
        self._external_port_override.SetValue( dictionary[ 'external_port_override' ] )
        
        #
        
        rows = []
        
        rows.append( ( 'run the {}?:'.format( name ), self._run_the_service ) )
        rows.append( ( 'local port:', self._port ) )
        rows.append( ( 'allow non-local connections:', self._allow_non_local_connections ) )
        rows.append( ( 'use https', self._use_https ) )
        rows.append( ( 'support CORS headers', self._support_cors ) )
        rows.append( ( 'log requests', self._log_requests ) )
        rows.append( ( 'normie-friendly welcome page', self._use_normie_eris ) )
        rows.append( ( 'upnp port', self._upnp ) )
        
        if False: # some old local booru gubbins--maybe delete?
            
            rows.append( ( 'scheme (http/https) override when copying external links', self._external_scheme_override ) )
            rows.append( ( 'host override when copying external links', self._external_host_override ) )
            rows.append( ( 'port override when copying external links', self._external_port_override ) )
            
        else:
            
            self._external_scheme_override.hide()
            self._external_host_override.hide()
            self._external_port_override.hide()
            
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self._client_server_options_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._client_server_options_panel.Add( self._bandwidth_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.Add( self._client_server_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self._allow_non_local_connections.clicked.connect( self._UpdateControls )
        self._run_the_service.clicked.connect( self._UpdateControls )
        
        self._UpdateControls()
        
    
    def _UpdateControls( self ):
        
        service_running = self._run_the_service.isChecked()
        
        self._port.setEnabled( service_running )
        self._allow_non_local_connections.setEnabled( service_running )
        self._use_https.setEnabled( service_running )
        self._support_cors.setEnabled( service_running )
        self._log_requests.setEnabled( service_running )
        self._use_normie_eris.setEnabled( service_running )
        self._upnp.setEnabled( service_running )
        self._external_scheme_override.setEnabled( service_running )
        self._external_host_override.setEnabled( service_running )
        self._external_port_override.setEnabled( service_running )
        
        if service_running:
            
            if self._allow_non_local_connections.isChecked():
                
                self._upnp.SetValue( None )
                
                self._upnp.setEnabled( False )
                
            else:
                
                self._upnp.setEnabled( True )
                
            
        
    
    def GetValue( self ):
        
        dictionary_part = {}
        
        if self._run_the_service.isChecked():
            
            port = self._port.value()
            
        else:
            
            port = None
            
        
        dictionary_part[ 'port' ] = port
        
        dictionary_part[ 'upnp_port' ] = self._upnp.GetValue()
        dictionary_part[ 'allow_non_local_connections' ] = self._allow_non_local_connections.isChecked()
        dictionary_part[ 'use_https' ] = self._use_https.isChecked()
        dictionary_part[ 'support_cors' ] = self._support_cors.isChecked()
        dictionary_part[ 'log_requests' ] = self._log_requests.isChecked()
        dictionary_part[ 'use_normie_eris' ] = self._use_normie_eris.isChecked()
        dictionary_part[ 'external_scheme_override' ] = self._external_scheme_override.GetValue()
        dictionary_part[ 'external_host_override' ] = self._external_host_override.GetValue()
        dictionary_part[ 'external_port_override' ] = self._external_port_override.GetValue()
        dictionary_part[ 'bandwidth_rules' ] = self._bandwidth_rules.GetValue()
        
        return dictionary_part
        
    

class EditServiceTagSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, dictionary ):
        
        super().__init__( parent, 'tags' )
        
        self._st = ClientGUICommon.BetterStaticText( self )
        
        self._st.setText( 'This is a tag service. There are no additional options for it at present.' )
        
        #
        
        self.Add( self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def GetValue( self ):
        
        dictionary_part = {}
        
        return dictionary_part
        
    

class EditServiceRatingsSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service_type, dictionary ):
        
        super().__init__( parent, 'rating display' )
        
        self._colour_ctrls = {}
        
        for colour_type in [ ClientRatings.LIKE, ClientRatings.DISLIKE, ClientRatings.NULL, ClientRatings.MIXED ]:
            
            border_ctrl = ClientGUIColourPicker.ColourPickerButton( self )
            fill_ctrl = ClientGUIColourPicker.ColourPickerButton( self )
            
            border_ctrl.setMaximumWidth( 20 )
            fill_ctrl.setMaximumWidth( 20 )
            
            self._colour_ctrls[ colour_type ] = ( border_ctrl, fill_ctrl )
            
        
        self._show_in_thumbnail = QW.QCheckBox( self )
        self._show_in_thumbnail_even_when_null = QW.QCheckBox( self )
        
        #
        
        for ( colour_type, ( border_rgb, fill_rgb ) ) in dictionary[ 'colours' ]:
            
            ( border_ctrl, fill_ctrl ) = self._colour_ctrls[ colour_type ]
            
            border_ctrl.SetColour( QG.QColor( *border_rgb ) )
            fill_ctrl.SetColour( QG.QColor( *fill_rgb ) )
            
        
        self._show_in_thumbnail.setChecked( dictionary[ 'show_in_thumbnail' ] )
        self._show_in_thumbnail_even_when_null.setChecked( dictionary[ 'show_in_thumbnail_even_when_null' ] )
        
        #
        
        rows = []
        
        for colour_type in [ ClientRatings.LIKE, ClientRatings.DISLIKE, ClientRatings.NULL, ClientRatings.MIXED ]:
            
            ( border_ctrl, fill_ctrl ) = self._colour_ctrls[ colour_type ]
            
            if service_type == HC.LOCAL_RATING_INCDEC and colour_type in ( ClientRatings.DISLIKE, ClientRatings.NULL ):
                
                border_ctrl.setVisible( False )
                fill_ctrl.setVisible( False )
                
                continue
                
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, border_ctrl, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, fill_ctrl, CC.FLAGS_CENTER_PERPENDICULAR )
            
            if colour_type == ClientRatings.LIKE:
                
                if service_type == HC.LOCAL_RATING_INCDEC:
                    
                    colour_text = 'normal rating'
                    
                else:
                    
                    colour_text = 'liked'
                    
                
            elif colour_type == ClientRatings.DISLIKE:
                
                colour_text = 'disliked'
                
            elif colour_type == ClientRatings.NULL:
                
                colour_text = 'not rated'
                
            else:
                
                colour_text = 'a mixture of ratings'
                
            
            rows.append( ( 'border/fill for ' + colour_text + ': ', hbox ) )
            
        
        rows.append( ( 'show in thumbnails', self._show_in_thumbnail ) )
        rows.append( ( '\u2514 even when file has no rating value', self._show_in_thumbnail_even_when_null ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._show_in_thumbnail.clicked.connect( self._UpdateControls )
        
        self._UpdateControls()
        
    
    def _UpdateControls( self ):
        
        self._show_in_thumbnail_even_when_null.setEnabled( self._show_in_thumbnail.isChecked() )
        
    
    def GetValue( self ):
        
        dictionary_part = {}
        
        dictionary_part[ 'colours' ] = {}
        
        for ( colour_type, ( border_ctrl, fill_ctrl ) ) in list(self._colour_ctrls.items()):
            
            border_colour = border_ctrl.GetColour()
            
            border_rgb = ( border_colour.red(), border_colour.green(), border_colour.blue() )
            
            fill_colour = fill_ctrl.GetColour()
            
            fill_rgb = ( fill_colour.red(), fill_colour.green(), fill_colour.blue() )
            
            dictionary_part[ 'colours' ][ colour_type ] = ( border_rgb, fill_rgb )
            
        
        dictionary_part[ 'show_in_thumbnail' ] = self._show_in_thumbnail.isChecked()
        dictionary_part[ 'show_in_thumbnail_even_when_null' ] = self._show_in_thumbnail_even_when_null.isChecked()
        
        return dictionary_part
        
    

class EditServiceStarRatingsSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, dictionary ):
        
        super().__init__( parent, 'rating shape' )
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_RATINGS )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the ratings help', 'Open the help page for ratings.', page_func ) )
        
        help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        help_hbox = ClientGUICommon.WrapInText( help_button, self, 'help -->', object_name = 'HydrusIndeterminate' )
        
        CC.global_icons().RefreshUserIcons()
        
        svg_ratings_are_ok = len( CC.global_icons().user_icons ) > 0
        
        choice_tuples = [
            ( 'shapes', 'shape' )
        ]
        
        if svg_ratings_are_ok:
            
            choice_tuples.append( ( 'svgs', 'rating_svg' ) )
            
        
        self._shape_or_svg = ClientGUICommon.BetterRadioBox( self, choice_tuples, vertical = True )
        
        self._shape = ClientGUICommon.BetterChoice( self )
        
        for ( shape, name ) in ClientRatings.shape_to_str_lookup_dict.items():
            
            self._shape.addItem( name, shape )
            
        
        self._rating_svg = ClientGUICommon.BetterChoice( self )
        
        if svg_ratings_are_ok:
            
            for name in sorted( CC.global_icons().user_icons.keys(), key = HydrusText.HumanTextSortKey ):
                
                self._rating_svg.addItem( name, name )
                
            
        else:
            
            self._rating_svg.addItem( 'no svgs found', None )
            
        #
        
        shape = dictionary[ 'shape' ]
        
        if shape is not None:
            
            self._shape_or_svg.SetValue( 'shape' )
            
            self._shape.SetValue( dictionary[ 'shape' ] )
            
        
        if svg_ratings_are_ok:
            
            rating_svg = dictionary[ 'rating_svg' ]
            
            if rating_svg is not None:
                
                self._shape_or_svg.SetValue( 'rating_svg' )
                
                self._rating_svg.SetValue( rating_svg )
                
            
        else:
            
            self._shape_or_svg.SetValue( 'shape' )
            
            self._shape_or_svg.setVisible( False )
            self._rating_svg.setVisible( False )
            
        
        #
        
        rows = []
        
        if svg_ratings_are_ok:
            
            rows.append( ( 'type: ', self._shape_or_svg ) )
            
        
        rows.append( ( 'shape: ', self._shape ) )
        
        if svg_ratings_are_ok:
            
            rows.append( ( 'svg: ', self._rating_svg ) )
            
        
        # preview here, ideally a manipulable fake control, or maybe we need to be more clever with num_stars in a numerical rating
        # fake bitmaps can also be fine
        # scaling size dynamically would also be nice, or at least showing what the current sizes are for media viewer, thumbs, and default 12px for anywhere else
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.Add( help_hbox, CC.FLAGS_ON_RIGHT )
        self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._UpdateControls()
        
        self._shape_or_svg.radioBoxChanged.connect( self._UpdateControls )
        
    
    def _UpdateControls( self ):
        
        selection = self._shape_or_svg.GetValue()
        
        self._shape.setEnabled( selection == 'shape' )
        self._rating_svg.setEnabled( selection == 'rating_svg' )
        
    
    def GetValue( self ):
        
        dictionary_part = {}
        
        selection = self._shape_or_svg.GetValue()
        
        if selection == 'shape':
            
            shape = self._shape.GetValue()
            
        else:
            
            shape = None
            
        
        dictionary_part[ 'shape' ] = shape
        
        if selection == 'rating_svg':
            
            rating_svg = self._rating_svg.GetValue()
            
        else:
            
            rating_svg = None
            
        
        dictionary_part[ 'rating_svg' ] = rating_svg
        
        return dictionary_part
        
    

class EditServiceRatingsNumericalSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, dictionary ):
        
        super().__init__( parent, 'numerical ratings' )
        
        self._num_stars = ClientGUICommon.BetterSpinBox( self, min=1, max=20 )
        self._allow_zero = QW.QCheckBox( self )
        self._custom_pad = ClientGUICommon.BetterSpinBox( self, min=-64, max=64 )
        self._draw_fraction = ClientGUICommon.BetterChoice( self )
        
        self._draw_fraction.addItem( 'do not', ClientRatings.DRAW_NO )
        self._draw_fraction.addItem( 'show on left', ClientRatings.DRAW_ON_LEFT )
        self._draw_fraction.addItem( 'show on right', ClientRatings.DRAW_ON_RIGHT )
        
        #
        
        self._num_stars.setValue( dictionary['num_stars'] )
        self._allow_zero.setChecked( dictionary[ 'allow_zero' ] )
        self._custom_pad.setValue( dictionary[ 'custom_pad' ] )
        self._draw_fraction.SetValue( dictionary[ 'show_fraction_beside_stars' ] )
        
        self._custom_pad.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set the distance, in pixels, between shapes in the row. Just set this to 0 if you want to go back to the old way these icons were rendered, with them displaying as a seamless loading bar.' ) )
        self._draw_fraction.setToolTip( ClientGUIFunctions.WrapToolTip( 'This will add the fractional display (e.g. \'4/5\') beside the rating stars. You can choose whether it appears on the right or left.' ) )
        
        #
        
        rows = []
        
        rows.append( ( 'number of \'stars\': ', self._num_stars ) )
        rows.append( ( 'allow a zero rating: ', self._allow_zero ) )
        rows.append( ( 'icon padding: ', self._custom_pad ) )
        rows.append( ( 'draw fraction beside the rating', self._draw_fraction ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
    
    def GetValue( self ):
        
        dictionary_part = {}
        
        num_stars = self._num_stars.value()
        allow_zero = self._allow_zero.isChecked()
        custom_pad = self._custom_pad.value()
        draw_fraction = self._draw_fraction.GetValue()
        
        if num_stars == 1 and not allow_zero:
            
            allow_zero = True
            
        
        dictionary_part[ 'num_stars' ] = num_stars
        dictionary_part[ 'allow_zero' ] = allow_zero
        dictionary_part[ 'custom_pad' ] = custom_pad
        dictionary_part[ 'show_fraction_beside_stars' ] = draw_fraction
        
        return dictionary_part
        
    

class EditServiceIPFSSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, dictionary ):
        
        super().__init__( parent, 'ipfs' )
        
        interaction_panel = ClientGUIPanels.IPFSDaemonStatusAndInteractionPanel( self, self.parentWidget().GetValue )
        
        #
        
        prefix_panel = ClientGUICommon.StaticBox( self, 'prefix' )
        
        self._multihash_prefix = QW.QLineEdit( prefix_panel )
        
        tt = 'When you tell the client to copy a ipfs multihash to your clipboard, it will prefix it with whatever is set here.'
        tt += '\n' * 2
        tt += 'Use this if you want to copy a full gateway url. For instance, you could put here:'
        tt += '\n' * 2
        tt += 'http://127.0.0.1:8080/ipfs/'
        tt += '\n'
        tt += '-or-'
        tt += '\n'
        tt += 'http://ipfs.io/ipfs/'
        
        self._multihash_prefix.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        #
        
        self._multihash_prefix.setText( dictionary[ 'multihash_prefix' ] )
        
        #
        
        self.Add( interaction_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        rows = []
        
        rows.append( ( 'clipboard multihash url prefix: ', self._multihash_prefix ) )
        
        gridbox = ClientGUICommon.WrapInGrid( prefix_panel, rows )
        
        prefix_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self.Add( prefix_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def GetValue( self ):
        
        dictionary_part = {}
        
        dictionary_part[ 'multihash_prefix' ] = self._multihash_prefix.text()
        
        return dictionary_part
        
    
class ReviewServicePanel( QW.QWidget ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent )
        
        self._service = service
        
        self._id_button = ClientGUICommon.BetterButton( self, 'id', self._GetAndShowID )
        self._id_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Click to fetch your service\'s database id.' ) )
        
        width = ClientGUIFunctions.ConvertTextToPixelWidth( self._id_button, 4 )
        
        self._id_button.setFixedWidth( width )
        
        self._service_key_button = ClientGUICommon.BetterButton( self, 'copy service key', CG.client_controller.pub, 'clipboard', 'text', service.GetServiceKey().hex() )
        
        self._refresh_button = ClientGUICommon.IconButton( self, CC.global_icons().refresh, self._RefreshButton )
        
        service_type = self._service.GetServiceType()
        
        subpanels = []
        
        subpanels.append( ( ReviewServiceSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
        
        if service_type in HC.REMOTE_SERVICES:
            
            subpanels.append( ( ReviewServiceRemoteSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            subpanels.append( ( ReviewServiceRestrictedSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR ) )
            
        
        if service_type in HC.REAL_FILE_SERVICES:
            
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
            
            subpanels.append( ( ReviewServiceIPFSSubPanel( self, service ), CC.FLAGS_EXPAND_PERPENDICULAR_BUT_BOTH_WAYS_LATER ) )
            
        
        if service_type == HC.CLIENT_API_SERVICE:
            
            subpanels.append( ( ReviewServiceClientAPISubPanel( self, service ), CC.FLAGS_EXPAND_BOTH_WAYS ) )
            
        
        #
        
        if not CG.client_controller.new_options.GetBoolean( 'advanced_mode' ):
            
            self._id_button.hide()
            self._service_key_button.hide()
            
        
        vbox = QP.VBoxLayout()
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._id_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._service_key_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._refresh_button, CC.FLAGS_CENTER )
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_ON_RIGHT )
        
        for ( panel, flags ) in subpanels:
            
            QP.AddToLayout( vbox, panel, flags )
            
        
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
    
    def _GetAndShowID( self ):
        
        service_key = self._service.GetServiceKey()
        
        def work_callable():
            
            service_id = CG.client_controller.Read( 'service_id', service_key )
            
            return service_id
            
        
        def publish_callable( service_id ):
            
            message = 'The service id is: {}'.format( service_id )
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def _RefreshButton( self ):
        
        CG.client_controller.pub( 'service_updated', self._service )
        
    
    def EventImmediateSync( self, event ):
        
        service = self._service
        
        def do_it():
            
            job_status = ClientThreading.JobStatus( pausable = True, cancellable = True )
            
            job_status.SetStatusTitle( service.GetName() + ': immediate sync' )
            job_status.SetStatusText( 'downloading' )
            
            CG.client_controller.pub( 'message', job_status )
            
            content_update_package = service.Request( HC.GET, 'immediate_content_update_package' )
            
            c_u_p_num_rows = content_update_package.GetNumRows()
            c_u_p_total_weight_processed = 0
            
            update_speed_string = ''
            
            for ( content_updates, weight ) in content_update_package.IterateContentUpdateChunks():
                
                ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                
                if should_quit:
                    
                    job_status.FinishAndDismiss()
                    
                    return
                    
                
                content_update_index_string = 'content ' + HydrusNumbers.ValueRangeToPrettyString( c_u_p_total_weight_processed, c_u_p_num_rows ) + ': '
                
                job_status.SetStatusText( content_update_index_string + 'committing' + update_speed_string )
                
                job_status.SetGauge( c_u_p_total_weight_processed, c_u_p_num_rows )
                
                precise_timestamp = HydrusTime.GetNowPrecise()
                
                CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( service.GetServiceKey(), content_updates ) )
                
                it_took = HydrusTime.GetNowPrecise() - precise_timestamp
                
                rows_s = int( weight / it_took )
                
                update_speed_string = ' at ' + HydrusNumbers.ToHumanInt( rows_s ) + ' rows/s'
                
                c_u_p_total_weight_processed += weight
                
            
            job_status.DeleteGauge()
            
            self._service.SyncThumbnails( job_status )
            
            job_status.SetStatusText( 'done! ' + HydrusNumbers.ToHumanInt( c_u_p_num_rows ) + ' rows added.' )
            
            job_status.Finish()
            
        
        CG.client_controller.CallToThread( do_it )
        
    
    def GetServiceKey( self ):
        
        return self._service.GetServiceKey()
        

class ReviewServiceSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent, 'name and type' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._name_and_type = ClientGUICommon.BetterStaticText( self )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._name_and_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
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
        
        super().__init__( parent, 'client api access keys' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._service_status = ClientGUICommon.BetterStaticText( self )
        
        permissions_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_CLIENT_API_PERMISSIONS.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._permissions_list = ClientGUIListCtrl.BetterListCtrlTreeView( permissions_list_panel, 10, model, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        permissions_list_panel.SetListCtrl( self._permissions_list )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'manually', 'Enter the details of the share manually.', self._AddManually ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from api request', 'Listen for an access permission request from an external program via the API.', self._AddFromAPI ) )
        
        permissions_list_panel.AddMenuButton( 'add', menu_template_items )
        permissions_list_panel.AddButton( 'edit', self._Edit, enabled_only_on_single_selection = True )
        permissions_list_panel.AddButton( 'duplicate', self._Duplicate, enabled_only_on_selection = True )
        permissions_list_panel.AddButton( 'delete', self._Delete, enabled_only_on_selection = True )
        permissions_list_panel.AddSeparator()
        permissions_list_panel.AddButton( 'open client api base url', self._OpenBaseURL )
        permissions_list_panel.AddButton( 'copy api access key', self._CopyAPIAccessKey, enabled_only_on_single_selection = True )
        
        self._permissions_list.Sort()
        
        #
        
        self._Refresh()
        
        #
        
        st = ClientGUICommon.BetterStaticText( self, label = 'Manage your Client API\'s different access key permissions here.' )
        
        self.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._service_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( permissions_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _ConvertDataToDisplayTuple( self, api_permissions ):
        
        name = api_permissions.GetName()
        
        pretty_name = name
        
        basic_permissions_string = api_permissions.GetBasicPermissionsString()
        advanced_permissions_string = api_permissions.GetAdvancedPermissionsString()
        
        display_tuple = ( pretty_name, basic_permissions_string, advanced_permissions_string )
        
        return display_tuple
        
    
    def _ConvertDataToSortTuple( self, api_permissions ):
        
        name = api_permissions.GetName()
        
        basic_permissions_string = api_permissions.GetBasicPermissionsString()
        advanced_permissions_string = api_permissions.GetAdvancedPermissionsString()
        
        sort_basic_permissions = basic_permissions_string
        sort_advanced_permissions = advanced_permissions_string
        
        sort_tuple = ( name, sort_basic_permissions, sort_advanced_permissions )
        
        return sort_tuple
        
    
    def _CopyAPIAccessKey( self ):
        
        selected = self._permissions_list.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return
            
        
        api_permissions = selected[0]
        
        access_key = api_permissions.GetAccessKey()
        
        text = access_key.hex()
        
        CG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _AddFromAPI( self ):
        
        port = self._service.GetPort()
        
        if port is None:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'The service is not running, so you cannot add new access via the API!' )
            
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
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                api_permissions = panel.GetValue()
                
                CG.client_controller.client_api_manager.AddAccess( api_permissions )
                
                self._Refresh()
                
            
        
    
    def _Delete( self ):
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            access_keys = [ api_permissions.GetAccessKey() for api_permissions in self._permissions_list.GetData( only_selected = True ) ]
            
            CG.client_controller.client_api_manager.DeleteAccess( access_keys )
            
            self._Refresh()
            
        
    
    def _Duplicate( self ):
        
        selected_api_permissions_objects = self._permissions_list.GetData( only_selected = True )
        
        dupes = [ api_permissions.Duplicate() for api_permissions in selected_api_permissions_objects ]
        
        # permissions objects do not need unique names, but let's dedupe the dupe objects' names here to make it easy to see which is which in this step
        
        existing_objects = list( self._permissions_list.GetData() )
        
        existing_names = { p_o.GetName() for p_o in existing_objects }
        
        for dupe in dupes:
            
            dupe.GenerateNewAccessKey()
            
            dupe.SetNonDupeName( existing_names, do_casefold = True )
            
            existing_names.add( dupe.GetName() )
            
        
        existing_objects.extend( dupes )
        
        CG.client_controller.client_api_manager.SetPermissions( existing_objects )
        
        self._Refresh()
        
    
    def _Edit( self ):
        
        selected_api_permissions_objects = self._permissions_list.GetData( only_selected = True )
        
        for api_permissions in selected_api_permissions_objects:
            
            title = 'edit api access permissions'
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIAPI.EditAPIPermissionsPanel( dlg, api_permissions )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    api_permissions = panel.GetValue()
                    
                    CG.client_controller.client_api_manager.OverwriteAccess( api_permissions )
                    
                else:
                    
                    break
                    
                
            
        
        self._Refresh()
        
    
    def _OpenBaseURL( self ):
        
        port = self._service.GetPort()
        
        if port is None:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'The service is not running, so you cannot view it in a web browser!' )
            
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
        
        api_permissions_objects = CG.client_controller.client_api_manager.GetAllPermissions()
        
        self._permissions_list.SetData( api_permissions_objects )
        
        self._permissions_list.Sort()
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    

class ReviewServiceCombinedLocalFilesSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent, 'combined local files' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._deferred_delete_status = ClientGUICommon.BetterStaticText( self, label = 'loading' + HC.UNICODE_ELLIPSIS )
        
        self._clear_deleted_files_record = ClientGUICommon.BetterButton( self, 'clear deleted files record', self._ClearDeletedFilesRecord )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._deferred_delete_status, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._clear_deleted_files_record, CC.FLAGS_ON_RIGHT )
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        CG.client_controller.sub( self, '_Refresh', 'notify_new_physical_file_delete_numbers' )
        
    
    def _ClearDeletedFilesRecord( self ):
        
        message = 'This will instruct your database to forget its _entire_ record of locally deleted files, meaning that if it ever encounters any of those files again, it will assume they are new and reimport them. This operation cannot be undone.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            message = 'Hey, I am just going to ask again--are you _absolutely_ sure? This is an advanced action that may mess up your downloads/imports in future.'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'yes, I am', no_label = 'no, I am not sure' )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                hashes = None
                
                content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, hashes )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                
                CG.client_controller.Write( 'content_updates', content_update_package )
                
                CG.client_controller.pub( 'service_updated', self._service )
                
            
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        CG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( text ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._deferred_delete_status.setText( text )
            
        
        ( num_files, num_thumbnails ) = CG.client_controller.Read( 'num_deferred_file_deletes' )
        
        if num_files == 0 and num_thumbnails == 0:
            
            text = 'No files are awaiting physical deletion from file storage.'
            
        else:
            
            text = '{} files and {} thumbnails are awaiting physical deletion from file storage.'.format( HydrusNumbers.ToHumanInt( num_files ), HydrusNumbers.ToHumanInt( num_thumbnails ) )
            
        
        CG.client_controller.CallAfter( self, qt_code, text )
        
    
class ReviewServiceFileSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent, 'files' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._file_info_st = ClientGUICommon.BetterStaticText( self )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._file_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        CG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( text ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._file_info_st.setText( text )
            
        
        service_info = CG.client_controller.Read( 'service_info', service.GetServiceKey() )
        
        num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
        
        text = HydrusNumbers.ToHumanInt( num_files ) + ' files, totalling ' + HydrusData.ToHumanBytes( total_size )
        
        if service.GetServiceType() in ( HC.LOCAL_FILE_DOMAIN, HC.COMBINED_LOCAL_MEDIA, HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ):
            
            num_deleted_files = service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ]
            
            text += ' - ' + HydrusNumbers.ToHumanInt( num_deleted_files ) + ' deleted files'
            
        
        CG.client_controller.CallAfter( self, qt_code, text )
        
    
class ReviewServiceRemoteSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent, 'this client\'s network use', can_expand = True, start_expanded = False )
        
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
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        credentials = self._service.GetCredentials()
        
        full_host = credentials.GetPortedAddress()
        
        self._address.setText( full_host )
        
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
        
        super().__init__( parent, 'hydrus service account - shared by all clients using the same access key', can_expand = True, start_expanded = False )
        
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
        
        self._network_sync_paused_button = ClientGUICommon.IconButton( self, CC.global_icons().pause, self._PausePlayNetworkSync )
        self._network_sync_paused_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play account sync' ) )
        
        self._refresh_account_button = ClientGUICommon.BetterButton( self, 'refresh account', self._RefreshAccount )
        self._copy_account_key_button = ClientGUICommon.BetterButton( self, 'copy account id', self._CopyAccountKey )
        self._permissions_button = ClientGUIMenuButton.MenuButton( self, 'see account permissions', [] )
        
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
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _CopyAccountKey( self ):
        
        account = self._service.GetAccount()
        
        account_key = account.GetAccountKey()
        
        account_key_hex = account_key.hex()
        
        CG.client_controller.pub( 'clipboard', 'text', account_key_hex )
        
    
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
            
            self._network_sync_paused_button.SetIconSmart( CC.global_icons().play )
            
        else:
            
            self._network_sync_paused_button.SetIconSmart( CC.global_icons().pause )
            
        
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
            
        
        menu_template_items = []
        
        p_s = account_type.GetPermissionStrings()
        
        if len( p_s ) == 0:
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemLabel( 'can only download', 'can only download' ) )
            
        else:
            
            for s in p_s:
                
                menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemLabel( s, s ) )
                
            
        
        self._permissions_button.SetMenuItems( menu_template_items )
        
    
    def _RefreshAccount( self ):
        
        service = self._service
        
        def work_callable():
            
            service.SyncAccount( force = True )
            
            return 1
            
        
        def publish_callable( result ):
            
            self._my_updater.Update()
            
        
        def errback_callable( etype, value, tb ):
            
            if not isinstance( etype, HydrusExceptions.ServerBusyException ):
                
                HydrusData.ShowExceptionTuple( etype, value, tb, do_wait = False )
                
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem!', str( value ) )
            
            self._my_updater.Update()
            
        
        if CG.client_controller.new_options.GetBoolean( 'pause_repo_sync' ):
            
            ClientGUIDialogsMessage.ShowWarning( self, 'All repositories are currently paused under the services->pause menu! Please unpause them and then try again!' )
            
            return
            
        
        if self._service.IsPausedNetworkSync():
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Account sync is paused for this service! Please unpause it to refresh its account.' )
            
            return
            
        
        self._refresh_account_button.setEnabled( False )
        self._refresh_account_button.setText( 'fetching' + HC.UNICODE_ELLIPSIS )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable )
        
        job.start()
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
class ReviewServiceRepositorySubPanel( QW.QWidget ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._network_panel = ClientGUICommon.StaticBox( self, 'network sync', can_expand = True, start_expanded = False )
        
        self._repo_options_st = ClientGUICommon.BetterStaticText( self._network_panel )
        
        tt = 'The update period is how often the repository bundles its recent uploads into a package for users to download. Anything you upload may take this long for other people to see.'
        tt += '\n' * 2
        tt += 'The anonymisation period is how long it takes for account information to be scrubbed from content. After this time, server admins/janitors cannot tell which account uploaded something.'
        
        self._repo_options_st.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._metadata_st = ClientGUICommon.BetterStaticText( self._network_panel )
        
        self._tag_filter_button = ClientGUICommon.BetterButton( self._network_panel, 'tag filter', self._ReviewTagFilter )
        self._tag_filter_button.setEnabled( False )
        
        self._download_progress = ClientGUICommon.TextAndGauge( self._network_panel )
        
        self._update_downloading_paused_button = ClientGUICommon.IconButton( self._network_panel, CC.global_icons().pause, self._PausePlayUpdateDownloading )
        self._update_downloading_paused_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play update downloading' ) )
        
        self._service_info_button = ClientGUICommon.BetterButton( self._network_panel, 'fetch service info', self._FetchServiceInfo )
        
        self._sync_remote_now_button = ClientGUICommon.BetterButton( self._network_panel, 'download now', self._SyncRemoteNow )
        
        reset_menu_template_items = []
        
        reset_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'do a full metadata resync', 'Resync all update information.', self._DoAFullMetadataResync ) )
        
        self._reset_downloading_button = ClientGUIMenuButton.MenuButton( self._network_panel, 'reset downloading', reset_menu_template_items )
        
        self._export_updates_button = ClientGUICommon.BetterButton( self._network_panel, 'export updates', self._ExportUpdates )
        
        #
        
        self._processing_panel = ClientGUICommon.StaticBox( self, 'processing sync', can_expand = True, start_expanded = False )
        
        self._update_processing_paused_button = ClientGUICommon.IconButton( self._processing_panel, CC.global_icons().pause, self._PausePlayUpdateProcessing )
        self._update_processing_paused_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play all update processing' ) )
        
        self._processing_definitions_progress = ClientGUICommon.TextAndGauge( self._processing_panel )
        
        #
        
        content_types = tuple( HC.SERVICE_TYPES_TO_CONTENT_TYPES[ self._service.GetServiceType() ] )
        
        self._content_types_to_gauges_and_buttons = {}
        
        for content_type in content_types:
            
            processing_progress = ClientGUICommon.TextAndGauge( self._processing_panel )
            
            processing_paused_button = ClientGUICommon.IconButton( self._processing_panel, CC.global_icons().pause, self._PausePlayUpdateProcessing, content_type )
            processing_paused_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'pause/play update processing for {}'.format( HC.content_type_string_lookup[ content_type ] ) ) )
            
            self._content_types_to_gauges_and_buttons[ content_type ] = ( processing_progress, processing_paused_button )
            
        
        #
        
        self._is_mostly_caught_up_st = ClientGUICommon.BetterStaticText( self._processing_panel )
        
        self._sync_processing_now_button = ClientGUICommon.BetterButton( self._processing_panel, 'process now', self._SyncProcessingNow )
        
        reset_menu_template_items = []
        
        reset_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'fill in definition gaps', 'Reprocess all definitions.', self._ReprocessDefinitions ) )
        reset_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'fill in content gaps', 'Reprocess all content.', self._ReprocessContent ) )
        reset_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        reset_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'delete and reprocess specific content', 'Reset some of the repository\'s content.', self._ResetProcessing ) )
        reset_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        reset_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'wipe all database data and reprocess', 'Reset entire repository.', self._Reset ) )
        
        self._reset_processing_button = ClientGUIMenuButton.MenuButton( self, 'reset processing', reset_menu_template_items )
        
        #
        
        self._Refresh()
        
        #
        
        new_options = CG.client_controller.new_options
        
        if not new_options.GetBoolean( 'advanced_mode' ):
            
            self._export_updates_button.hide()
            self._reset_processing_button.hide()
            
        
        if not self._service.GetServiceType() == HC.TAG_REPOSITORY:
            
            self._tag_filter_button.hide()
            
        
        self._network_panel.Add( self._repo_options_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._network_panel.Add( self._metadata_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._network_panel.Add( self._download_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._network_panel.Add( self._update_downloading_paused_button, CC.FLAGS_ON_RIGHT )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._service_info_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._tag_filter_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._sync_remote_now_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._reset_downloading_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._export_updates_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._network_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        self._processing_panel.Add( self._processing_definitions_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, ClientGUICommon.BetterStaticText( self._processing_panel, label = 'pause/play all processing: ' ), CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._update_processing_paused_button, CC.FLAGS_CENTER )
        
        self._processing_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        for content_type in content_types:
            
            ( gauge, button ) = self._content_types_to_gauges_and_buttons[ content_type ]
            
            self._processing_panel.Add( gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._processing_panel.Add( button, CC.FLAGS_ON_RIGHT )
            
        
        self._processing_panel.Add( self._is_mostly_caught_up_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._sync_processing_now_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._reset_processing_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._processing_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._network_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._processing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.setLayout( vbox )
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _DoAFullMetadataResync( self ):
        
        if self._service.IsDueAFullMetadataResync():
            
            message = 'This service is already due a full metadata resync.'
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
            return
            
        
        name = self._service.GetName()
        
        message = 'This will flag the client to resync the information about which update files it should download. It will occur on the next download sync.'
        message += '\n' * 2
        message += 'This is useful if the metadata archive has become unsynced, either due to a bug or a service switch. If it is not needed, it will not make any changes.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
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
                    
                    ClientGUIDialogsMessage.ShowInformation( self, 'No updates to export!' )
                    
                else:
                    
                    job_status = ClientThreading.JobStatus( cancellable = True )
                    
                    try:
                        
                        job_status.SetStatusTitle( 'exporting updates for ' + service.GetName() )
                        CG.client_controller.pub( 'message', job_status )
                        
                        client_files_manager = CG.client_controller.client_files_manager
                        
                        for ( i, update_hash ) in enumerate( update_hashes ):
                            
                            ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                            
                            if should_quit:
                                
                                job_status.SetStatusText( 'Cancelled!' )
                                
                                return
                                
                            
                            try:
                                
                                update_path = client_files_manager.GetFilePath( update_hash, HC.APPLICATION_HYDRUS_UPDATE_CONTENT )
                                
                                dest_path = os.path.join( dest_dir, update_hash.hex() )
                                
                                HydrusPaths.MirrorFile( update_path, dest_path )
                                
                            except HydrusExceptions.FileMissingException:
                                
                                continue
                                
                            finally:
                                
                                job_status.SetStatusText( HydrusNumbers.ValueRangeToPrettyString( i, num_to_do ) )
                                job_status.SetGauge( i, num_to_do )
                                
                            
                        
                        job_status.SetStatusText( 'Done!' )
                        
                    finally:
                        
                        job_status.DeleteGauge()
                        
                        job_status.Finish()
                        
                    
                
            finally:
                
                CG.client_controller.CallAfter( self, qt_done )
                
            
        
        with QP.DirDialog( self, 'Select export location.' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                path = dlg.GetPath()
                
                self._export_updates_button.setText( 'exporting' + HC.UNICODE_ELLIPSIS )
                self._export_updates_button.setEnabled( False )
                
                CG.client_controller.CallToThread( do_it, path, self._service )
                
            
        
    
    def _FetchServiceInfo( self ):
        
        service = self._service
        
        def work_callable():
            
            result = service.Request( HC.GET, 'service_info' )
            
            return dict( result[ 'service_info' ] )
            
        
        def publish_callable( service_info_dict ):
            
            if self._service.GetServiceType() == HC.TAG_REPOSITORY:
                
                service_info_types = HC.TAG_REPOSITORY_SERVICE_INFO_TYPES
                
            else:
                
                service_info_types = HC.FILE_REPOSITORY_SERVICE_INFO_TYPES
                
            
            message = 'Note that num file hashes and tags here include deleted content so will likely not line up with your review services value, which is only for current content.'
            message += '\n' * 2
            
            tuples = [ ( HC.service_info_enum_str_lookup[ info_type ], HydrusNumbers.ToHumanInt( service_info_dict[ info_type ] ) ) for info_type in service_info_types if info_type in service_info_dict ]
            string_rows = [ '{}: {}'.format( info_type, info ) for ( info_type, info ) in tuples ]
            
            message += '\n'.join( string_rows )
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
            self._my_updater.Update()
            
        
        def errback_callable( etype, value, tb ):
            
            if not isinstance( etype, HydrusExceptions.ServerBusyException ):
                
                HydrusData.ShowExceptionTuple( etype, value, tb, do_wait = False )
                
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem!', str( value ) )
            
            self._my_updater.Update()
            
        
        self._service_info_button.setEnabled( False )
        self._service_info_button.setText( 'fetching' + HC.UNICODE_ELLIPSIS )
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable, errback_callable = errback_callable )
        
        job.start()
        
    
    def _PausePlayUpdateDownloading( self ):
        
        self._service.PausePlayUpdateDownloading()
        
    
    def _PausePlayUpdateProcessing( self, content_type = None ):
        
        self._service.PausePlayUpdateProcessing( content_type = content_type )
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        self._sync_remote_now_button.setEnabled( False )
        self._sync_processing_now_button.setEnabled( False )
        
        #
        
        if self._service.IsPausedUpdateDownloading():
            
            self._update_downloading_paused_button.SetIconSmart( CC.global_icons().play )
            
        else:
            
            self._update_downloading_paused_button.SetIconSmart( CC.global_icons().pause )
            
        
        #
        
        
        self._service_info_button.setText( 'service info' )
        self._service_info_button.setEnabled( True )
        self._service_info_button.setVisible( CG.client_controller.new_options.GetBoolean( 'advanced_mode' ) )
        
        #
        
        all_processing_paused = self._service.IsPausedUpdateProcessing()
        
        if all_processing_paused:
            
            self._update_processing_paused_button.SetIconSmart( CC.global_icons().play )
            
        else:
            
            self._update_processing_paused_button.SetIconSmart( CC.global_icons().pause )
            
        
        for ( gauge, button ) in self._content_types_to_gauges_and_buttons.values():
            
            button.setEnabled( not all_processing_paused )
            
        
        #
        
        for ( content_type, ( gauge, button ) ) in self._content_types_to_gauges_and_buttons.items():
            
            if self._service.IsPausedUpdateProcessing( content_type ):
                
                button.SetIconSmart( CC.global_icons().play )
                
            else:
                
                button.SetIconSmart( CC.global_icons().pause )
                
            
        
        #
        
        repo_options_text_components = []
        
        try:
            
            update_period = self._service.GetUpdatePeriod()
            
            repo_options_text_components.append( 'update period: {}'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( update_period ) ) )
            
        except HydrusExceptions.DataMissing:
            
            repo_options_text_components.append( 'Unknown update period.' )
            
        
        try:
            
            nullification_period = self._service.GetNullificationPeriod()
            
            repo_options_text_components.append( 'anonymisation period: {}'.format( HydrusTime.TimeDeltaToPrettyTimeDelta( nullification_period ) ) )
            
        except HydrusExceptions.DataMissing:
            
            repo_options_text_components.append( 'Unknown anonymisation period.' )
            
        
        self._repo_options_st.setText( ', '.join( repo_options_text_components ) )
        
        if self._service.GetServiceType() == HC.TAG_REPOSITORY:
            
            try:
                
                tag_filter = self._service.GetTagFilter()
                
                self._tag_filter_button.setEnabled( True )
                
                tt = 'See which tags this repository accepts. Summary:{}{}'.format( '\n' * 2, tag_filter.ToPermittedString() )
                
                self._tag_filter_button.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
                
            except HydrusExceptions.DataMissing:
                
                self._tag_filter_button.setEnabled( False )
                self._tag_filter_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Do not have a tag filter for this repository. Try refreshing your account, or, if your client is old, update it.' ) )
                
            
        
        self._metadata_st.setText( self._service.GetNextUpdateDueString() )
        
        CG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def _ReprocessDefinitions( self ):
        
        def do_it( service, my_updater ):
            
            service_key = service.GetServiceKey()
            
            CG.client_controller.WriteSynchronous( 'reprocess_repository', service_key, ( HC.CONTENT_TYPE_DEFINITIONS, ) )
            
            my_updater.Update()
            
        
        name = self._service.GetName()
        
        message = 'This will command the client to reprocess all definition updates for {}. It will not delete anything.'.format( name )
        message += '\n' * 2
        message += 'This is a only useful as a debug tool for filling in \'gaps\'. If you do not understand what this does, turn back now.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.CallToThread( do_it, self._service, self._my_updater )
            
        
    
    def _ReprocessContent( self ):
        
        def do_it( service, my_updater, content_types_to_reset ):
            
            service_key = service.GetServiceKey()
            
            CG.client_controller.WriteSynchronous( 'reprocess_repository', service_key, content_types_to_reset )
            
            my_updater.Update()
            
        
        content_types = self._SelectContentTypes()
        
        if len( content_types ) == 0:
            
            return
            
        
        name = self._service.GetName()
        
        message = 'This will command the client to reprocess ({}) for {}. It will not delete anything.'.format( ', '.join( ( HC.content_type_string_lookup[ content_type ] for content_type in content_types ) ), name )
        message += '\n' * 2
        message += 'This is a only useful as a debug tool for filling in \'gaps\' caused by processing bugs or database damage. If you do not understand what this does, turn back now.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.CallToThread( do_it, self._service, self._my_updater, content_types )
            
        
    
    def _Reset( self ):
        
        name = self._service.GetName()
        
        message = 'This will delete all the processed information for ' + name + ' from the database, including definitions.' + '\n' * 2 + 'Once the service is reset, you will have to reprocess everything from your downloaded update files. The client will naturally do this in its idle time as before, just starting over from the beginning.' + '\n' * 2 + 'This is a severe maintenance task that is only appropriate after trying to recover from critical database error. If you do not understand what this does, click no!'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            message = 'Seriously, are you absolutely sure?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, message )
            
            if result == QW.QDialog.DialogCode.Accepted:
                
                self._service.Reset()
                
            
        
    
    def _ResetProcessing( self ):
        
        def do_it( service, my_updater, content_types_to_reset ):
            
            service_key = service.GetServiceKey()
            
            CG.client_controller.WriteSynchronous( 'reset_repository_processing', service_key, content_types_to_reset )
            
            my_updater.Update()
            
        
        content_types = self._SelectContentTypes()
        
        if len( content_types ) == 0:
            
            return
            
        
        name = self._service.GetName()
        
        message = 'You are about to delete and reprocess ({}) for {}.'.format( ', '.join( ( HC.content_type_string_lookup[ content_type ] for content_type in content_types ) ), name )
        message += '\n' * 2
        message += 'It may take some time to delete it all, and then future idle time to reprocess. It is only worth doing this if you believe there are logical problems in the initial process. If you just want to fill in gaps, use that simpler maintenance task, which runs much faster.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.CallToThread( do_it, self._service, self._my_updater, content_types )
            
        
    
    def _ReviewTagFilter( self ):
        
        try:
            
            tag_filter = self._service.GetTagFilter()
            
        except HydrusExceptions.DataMissing:
            
            return
            
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'review tag filter' )
        
        message = 'The Tag Repository applies this to all new pending tag mapping uploads. If you upload a mapping that this filter denies, it will be silently discarded serverside. Siblings and parents are not affected.'
        
        namespaces = CG.client_controller.network_engine.domain_manager.GetParserNamespaces()
        
        panel = ClientGUITagFilter.EditTagFilterPanel( frame, tag_filter, namespaces = namespaces, message = message, read_only = True )
        
        frame.SetPanel( panel )
        
    
    def _SelectContentTypes( self ):
        
        choice_tuples = [ ( HC.content_type_string_lookup[ content_type ], content_type, False ) for content_type in self._content_types_to_gauges_and_buttons.keys() ]
        
        try:
            
            result = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select the content to delete and reprocess', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return []
            
        
        content_types = result
        
        return content_types
        
    
    def _SyncRemoteNow( self ):
        
        def do_it( service, my_updater ):
            
            service.SyncRemote()
            
            my_updater.Update()
            
        
        self._sync_remote_now_button.setEnabled( False )
        
        CG.client_controller.CallToThread( do_it, self._service, self._my_updater )
        
    
    def _SyncProcessingNow( self ):
        
        message = 'This will tell the database to process any possible outstanding update files right now.'
        message += '\n' * 2
        message += 'You can still use the client while it runs, but it may make some things like autocomplete lookup a bit juddery.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            def do_it( service, my_updater ):
                
                service.SyncProcessUpdates( maintenance_mode = HC.MAINTENANCE_FORCED )
                
                my_updater.Update()
                
            
            self._sync_processing_now_button.setEnabled( False )
            
            CG.client_controller.CallToThread( do_it, self._service, self._my_updater )
            
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( num_local_updates, num_updates, content_types_to_num_processed_updates, content_types_to_num_updates, is_mostly_caught_up ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            download_text = 'downloaded {}'.format( HydrusNumbers.ValueRangeToPrettyString( num_local_updates, num_updates ) )
            
            self._download_progress.SetValue( download_text, num_local_updates, num_updates )
            
            processing_work_to_do = False
            
            d_value = content_types_to_num_processed_updates[ HC.CONTENT_TYPE_DEFINITIONS ]
            d_range = content_types_to_num_updates[ HC.CONTENT_TYPE_DEFINITIONS ]
            
            if d_value < d_range:
                
                processing_work_to_do = True
                
            
            definitions_text = 'definitions: {}'.format( HydrusNumbers.ValueRangeToPrettyString( d_value, d_range ) )
            
            self._processing_definitions_progress.SetValue( definitions_text, d_value, d_range )
            
            for ( content_type, ( gauge, button ) ) in self._content_types_to_gauges_and_buttons.items():
                
                c_value = content_types_to_num_processed_updates[ content_type ]
                c_range = content_types_to_num_updates[ content_type ]
                
                if not self._service.IsPausedUpdateProcessing( content_type ) and c_value < c_range:
                    
                    # there is work to do on downloads that we have on disk
                    processing_work_to_do = True
                    
                
                content_text = '{}: {}'.format( HC.content_type_string_lookup[ content_type ], HydrusNumbers.ValueRangeToPrettyString( c_value, c_range ) )
                
                gauge.SetValue( content_text, c_value, c_range )
                
            
            if is_mostly_caught_up:
                
                caught_up_text = 'Client is caught up to service and can upload content.'
                
            else:
                
                caught_up_text = 'Still some processing to do until the client is caught up.'
                
            
            self._is_mostly_caught_up_st.setText( caught_up_text )
            
            self._export_updates_button.setEnabled( d_value > 0 )
            
            metadata_due = self._service.GetMetadata().UpdateDue( from_client = True )
            updates_due = num_local_updates < num_updates
            
            download_work_to_do = metadata_due or updates_due
            
            can_sync_download = self._service.CanSyncDownload()
            
            if download_work_to_do and can_sync_download:
                
                self._sync_remote_now_button.setEnabled( True )
                
            else:
                
                self._sync_remote_now_button.setEnabled( False )
                
            
            can_sync_process = self._service.CanSyncProcess()
            
            if processing_work_to_do and can_sync_process:
                
                self._sync_processing_now_button.setEnabled( True )
                
            else:
                
                self._sync_processing_now_button.setEnabled( False )
                
            
        
        ( num_local_updates, num_updates, content_types_to_num_processed_updates, content_types_to_num_updates ) = CG.client_controller.Read( 'repository_progress', service.GetServiceKey() )
        
        is_mostly_caught_up = service.IsMostlyCaughtUp()
        
        CG.client_controller.CallAfter( self, qt_code, num_local_updates, num_updates, content_types_to_num_processed_updates, content_types_to_num_updates, is_mostly_caught_up )
        
    

class ReviewServiceIPFSSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent, 'ipfs', can_expand = True, start_expanded = False, expanded_size_vertical_policy = QW.QSizePolicy.Policy.Expanding )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        interaction_panel = ClientGUIPanels.IPFSDaemonStatusAndInteractionPanel( self, self.GetService )
        
        self._ipfs_shares_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        model = ClientGUIListCtrl.HydrusListItemModel( self, CGLC.COLUMN_LIST_IPFS_SHARES.ID, self._ConvertDataToDisplayTuple, self._ConvertDataToSortTuple )
        
        self._ipfs_shares = ClientGUIListCtrl.BetterListCtrlTreeView( self._ipfs_shares_panel, 6, model, delete_key_callback = self._Unpin, activation_callback = self._SetNotes )
        
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
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _ConvertDataToDisplayTuple( self, data ):
        
        ( multihash, num_files, total_size, note ) = data
        
        pretty_multihash = multihash
        pretty_num_files = HydrusNumbers.ToHumanInt( num_files )
        pretty_total_size = HydrusData.ToHumanBytes( total_size )
        pretty_note = note
        
        display_tuple = ( pretty_multihash, pretty_num_files, pretty_total_size, pretty_note )
        
        return display_tuple
        
    
    def _ConvertDataToSortTuple( self, data ):
        
        ( multihash, num_files, total_size, note ) = data
        
        sort_tuple = ( multihash, num_files, total_size, note )
        
        return sort_tuple
        
    
    def _CopyMultihashes( self ):
        
        multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetData( only_selected = True ) ]
        
        if len( multihashes ) == 0:
            
            multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetData() ]
            
        
        if len( multihashes ) > 0:
            
            multihash_prefix = self._service.GetMultihashPrefix()
            
            text = '\n'.join( ( multihash_prefix + multihash for multihash in multihashes ) )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _Refresh( self ):
        
        if not self or not QP.isValid( self ):
            
            return
            
        
        CG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def _SetNotes( self ):
        
        datas = self._ipfs_shares.GetData( only_selected = True )
        
        if len( datas ) > 0:
            
            message = 'Set a note for these shares.'
            
            try:
                
                note = ClientGUIDialogsQuick.EnterText( self, message )
                
            except HydrusExceptions.CancelledException:
                
                return
                
            
            content_updates = []
            
            for ( multihash, num_files, total_size, old_note ) in datas:
                
                hashes = CG.client_controller.Read( 'service_directory', self._service.GetServiceKey(), multihash )
                
                content_update_row = ( hashes, multihash, note )
                
                content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_ADD, content_update_row ) )
                
            
            CG.client_controller.Write( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( self._service.GetServiceKey(), content_updates ) )
            
            self._my_updater.Update()
            
        
    
    def _ShowSelectedInNewPages( self ):
        
        def qt_done():
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._ipfs_shares_panel.setEnabled( True )
            
        
        def do_it( service_key, pages_of_hashes_to_show ):
            
            try:
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
                
                for ( multihash, num_files, total_size, note ) in shares:
                    
                    hashes = CG.client_controller.Read( 'service_directory', service_key, multihash )
                    
                    CG.client_controller.pub( 'new_page_query', location_context, initial_hashes = hashes, page_name = 'ipfs directory' )
                    
                    time.sleep( 0.5 )
                    
                
            finally:
                
                CG.client_controller.CallAfter( self, qt_done )
                
            
        
        shares = self._ipfs_shares.GetData( only_selected = True )
        
        self._ipfs_shares_panel.setEnabled( False )
        
        CG.client_controller.CallToThread( do_it, self._service.GetServiceKey(), shares )
        
    
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
                
                CG.client_controller.CallAfter( self, qt_done )
                
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Unpin (remove) all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetData( only_selected = True ) ]
            
            self._ipfs_shares_panel.setEnabled( False )
            
            CG.client_controller.CallToThread( do_it, self._service, multihashes )
            
        
    
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
            
        
        ipfs_shares = CG.client_controller.Read( 'service_directories', service.GetServiceKey() )
        
        CG.client_controller.CallAfter( self, qt_code, ipfs_shares )
        
    

class ReviewServiceRatingSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent, 'ratings' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._rating_info_st = ClientGUICommon.BetterStaticText( self )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'for deleted files', 'delete all set ratings for files that have since been deleted', HydrusData.Call(  self._ClearRatings, 'delete_for_deleted_files', 'deleted files' ) ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'for all non-local files', 'delete all set ratings for files that are not in this client right now', HydrusData.Call( self._ClearRatings, 'delete_for_non_local_files', 'non-local files' ) ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'for all files', 'delete all set ratings for all files', HydrusData.Call( self._ClearRatings, 'delete_for_all_files', 'ALL FILES' ) ) )
        
        self._clear_deleted = ClientGUIMenuButton.MenuButton( self, 'clear ratings', menu_template_items )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._rating_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._clear_deleted, CC.FLAGS_ON_RIGHT )
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _ClearRatings( self, advanced_action, action_description ):
        
        message = 'Delete any ratings on this service for {}? THIS CANNOT BE UNDONE'.format( action_description )
        message += '\n' * 2
        message += 'Please note a client restart is needed to see the ratings disappear in media views.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADVANCED, advanced_action )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( self._service.GetServiceKey(), content_update )
            
            CG.client_controller.Write( 'content_updates', content_update_package, publish_content_updates = False )
            
            CG.client_controller.pub( 'service_updated', self._service )
            
        
    
    def _Refresh( self ):
        
        CG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( text ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._rating_info_st.setText( text )
            
        
        service_info = CG.client_controller.Read( 'service_info', service.GetServiceKey() )
        
        num_files = service_info[ HC.SERVICE_INFO_NUM_FILE_HASHES ]
        
        text = HydrusNumbers.ToHumanInt( num_files ) + ' files are rated'
        
        CG.client_controller.CallAfter( self, qt_code, text )
        
    

class ReviewServiceTagSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent, 'tags' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._tag_info_st = ClientGUICommon.BetterStaticText( self )
        
        self._tag_migration = ClientGUICommon.BetterButton( self, 'migrate tags', self._MigrateTags )
        
        #
        
        self._Refresh()
        
        #
        
        self.Add( self._tag_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._tag_migration, CC.FLAGS_ON_RIGHT )
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _MigrateTags( self ):
        
        tlw = CG.client_controller.GetMainTLW()
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( tlw, 'migrate tags' )
        
        panel = ClientGUIMigrateTags.MigrateTagsPanel( frame, self._service.GetServiceKey() )
        
        frame.SetPanel( panel )
        
    
    def _Refresh( self ):
        
        CG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( text ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._tag_info_st.setText( text )
            
        
        service_info = CG.client_controller.Read( 'service_info', service.GetServiceKey() )
        
        num_files = service_info[ HC.SERVICE_INFO_NUM_FILE_HASHES ]
        num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
        num_mappings = service_info[ HC.SERVICE_INFO_NUM_MAPPINGS ]
        
        text = HydrusNumbers.ToHumanInt( num_mappings ) + ' total mappings involving ' + HydrusNumbers.ToHumanInt( num_tags ) + ' different tags on ' + HydrusNumbers.ToHumanInt( num_files ) + ' different files'
        
        if service.GetServiceType() == HC.TAG_REPOSITORY:
            
            num_deleted_mappings = service_info[ HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ]
            
            text += ' - ' + HydrusNumbers.ToHumanInt( num_deleted_mappings ) + ' deleted mappings'
            
        
        CG.client_controller.CallAfter( self, qt_code, text )
        
    

class ReviewServiceTrashSubPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service ):
        
        super().__init__( parent, 'trash' )
        
        self._service = service
        
        self._my_updater = ClientGUIAsync.FastThreadToGUIUpdater( self, self._Refresh )
        
        self._undelete_all = ClientGUICommon.BetterButton( self, 'undelete all', self._UndeleteAll )
        self._undelete_all.setEnabled( False )
        
        self._clear_trash = ClientGUICommon.BetterButton( self, 'clear trash', self._ClearTrash )
        self._clear_trash.setEnabled( False )
        
        #
        
        self._Refresh()
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._undelete_all, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._clear_trash, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        CG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
        
    
    def _ClearTrash( self ):
        
        message = 'This will completely clear your trash of all its files, deleting them permanently from the client. This operation cannot be undone.'
        message += '\n' * 2
        message += 'If you have many files in your trash, it will take some time to complete and for all the files to eventually be deleted.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            def do_it( service ):
                
                hashes = CG.client_controller.Read( 'trash_hashes' )
                
                for group_of_hashes in HydrusLists.SplitIteratorIntoChunks( hashes, 16 ):
                    
                    content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, group_of_hashes )
                    
                    content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, content_update )
                    
                    CG.client_controller.WriteSynchronous( 'content_updates', content_update_package )
                    
                    time.sleep( 0.01 )
                    
                
                CG.client_controller.pub( 'service_updated', service )
                
            
            self._clear_trash.setEnabled( False )
            
            CG.client_controller.CallToThread( do_it, self._service )
            
        
    
    def _Refresh( self ):
        
        CG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
        
    
    def _UndeleteAll( self ):
        
        message = 'This will instruct your database to restore all files currently in the trash to all the local file services they have been in.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            def do_it( service ):
                
                hashes = CG.client_controller.Read( 'trash_hashes' )
                
                ClientGUIMediaSimpleActions.UndeleteFiles( hashes )
                
                CG.client_controller.pub( 'service_updated', service )
                
            
            self._undelete_all.setEnabled( False )
            
            CG.client_controller.CallToThread( do_it, self._service )
            
        
    
    def ServiceUpdated( self, service ):
        
        if service.GetServiceKey() == self._service.GetServiceKey():
            
            self._service = service
            
            self._my_updater.Update()
            
        
    
    def THREADFetchInfo( self, service ):
        
        def qt_code( num_files ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._clear_trash.setEnabled( num_files > 0 )
            self._undelete_all.setEnabled( num_files > 0 )
            
        
        service_info = CG.client_controller.Read( 'service_info', service.GetServiceKey() )
        
        num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
        
        CG.client_controller.CallAfter( self, qt_code, num_files )
        
    
class ReviewServicesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent: QW.QWidget, controller: "CG.ClientController.Controller" ):
        
        self._controller = controller
        
        super().__init__( parent )
        
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
        
        try:
            
            notebook: ClientGUICommon.BetterNotebook = self._notebook.currentWidget()
            
            if notebook.count() == 0:
                
                previous_service_key = None
                
            else:
                
                notebook_2: ClientGUICommon.BetterNotebook = notebook.currentWidget()
                
                page: ReviewServicePanel = notebook_2.currentWidget()
                
                previous_service_key = page.GetServiceKey()
                
            
        except:
            
            previous_service_key = None
            
        
        QP.DeleteAllNotebookPages( self._local_notebook )
        QP.DeleteAllNotebookPages( self._remote_notebook )
        
        notebook_dict = {}
        
        service_types = list( HC.ALL_SERVICES )
        
        # we want these in exactly this order, so a bit of shuffling
        for service_type in HC.LOCAL_FILE_SERVICES_IN_NICE_ORDER:
            
            if service_type in service_types:
                
                service_types.remove( service_type )
                
            
        
        service_types = list( HC.LOCAL_FILE_SERVICES_IN_NICE_ORDER ) + service_types
        
        services = self._controller.services_manager.GetServices( service_types )
        
        for service in services:
            
            service_type = service.GetServiceType()
            
            if service_type in HC.LOCAL_SERVICES: parent_notebook = self._local_notebook
            else: parent_notebook = self._remote_notebook
            
            if service_type == HC.TAG_REPOSITORY: service_type_name = 'tag repositories'
            elif service_type == HC.FILE_REPOSITORY: service_type_name = 'file repositories'
            elif service_type == HC.MESSAGE_DEPOT: service_type_name = 'message depots'
            elif service_type == HC.SERVER_ADMIN: service_type_name = 'administrative servers'
            elif service_type in HC.LOCAL_FILE_SERVICES: service_type_name = 'locations'
            elif service_type == HC.LOCAL_TAG: service_type_name = 'tags'
            elif service_type == HC.LOCAL_RATING_LIKE: service_type_name = 'like/dislike ratings'
            elif service_type == HC.LOCAL_RATING_NUMERICAL: service_type_name = 'numerical ratings'
            elif service_type == HC.LOCAL_RATING_INCDEC: service_type_name = 'inc/dec ratings'
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
        
    
