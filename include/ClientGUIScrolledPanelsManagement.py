import ClientCaches
import ClientConstants as CC
import ClientData
import ClientDefaults
import ClientDownloading
import ClientGUIACDropdown
import ClientGUICommon
import ClientGUIControls
import ClientGUIDialogs
import ClientGUIListBoxes
import ClientGUIListCtrl
import ClientGUIPredicates
import ClientGUIScrolledPanels
import ClientGUIScrolledPanelsEdit
import ClientGUIScrolledPanelsReview
import ClientGUISerialisable
import ClientGUIShortcuts
import ClientGUITagSuggestions
import ClientGUITopLevelWindows
import ClientNetworking
import ClientImporting
import ClientMedia
import ClientRatings
import ClientSerialisable
import ClientServices
import ClientGUITime
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusNetwork
import HydrusNetworking
import HydrusPaths
import HydrusSerialisable
import HydrusTagArchive
import HydrusTags
import HydrusText
import itertools
import os
import random
import traceback
import urlparse
import webbrowser
import wx

class ManageAccountTypesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, service_key ):
        
        self._admin_service = HG.client_controller.services_manager.GetService( service_key )
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._deletee_account_type_keys_to_new_account_type_keys = {}
        
        self._account_types_listctrl = ClientGUIListCtrl.SaneListCtrlForSingleObject( self, 200, [ ( 'title', -1 ) ], delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._Add )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        response = self._admin_service.Request( HC.GET, 'account_types' )
        
        account_types = response[ 'account_types' ]
        
        for account_type in account_types:
            
            ( display_tuple, sort_tuple ) = self._ConvertAccountTypeToTuples( account_type )
            
            self._account_types_listctrl.Append( display_tuple, sort_tuple, account_type )
            
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._add_button, CC.FLAGS_VCENTER )
        hbox.Add( self._edit_button, CC.FLAGS_VCENTER )
        hbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._account_types_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _Add( self ):
        
        title = 'new account type'
        permissions = {}
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        
        account_type = HydrusNetwork.AccountType.GenerateNewAccountTypeFromParameters( title, permissions, bandwidth_rules )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit account type' ) as dlg_edit:
            
            panel = ClientGUIScrolledPanelsEdit.EditAccountTypePanel( dlg_edit, self._admin_service.GetServiceType(), account_type )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_account_type = panel.GetValue()
                
                ( display_tuple, sort_tuple ) = self._ConvertAccountTypeToTuples( new_account_type )
                
                self._account_types_listctrl.Append( display_tuple, sort_tuple, new_account_type )
                
            
        
    
    
    def _ConvertAccountTypeToTuples( self, account_type ):
        
        title = account_type.GetTitle()
        
        display_tuple = ( title, )
        sort_tuple = ( title, )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                indices = self._account_types_listctrl.GetAllSelected()
                
                account_types_about_to_delete = { self._account_types_listctrl.GetObject( index ) for index in indices }
                
                all_account_types = set( self._account_types_listctrl.GetObjects() )
                
                account_types_can_move_to = list( all_account_types - account_types_about_to_delete )
                
                if len( account_types_can_move_to ) == 0:
                    
                    wx.MessageBox( 'You cannot delete every account type!' )
                    
                    return
                    
                
                for deletee_account_type in account_types_about_to_delete:
                    
                    if len( account_types_can_move_to ) > 1:
                        
                        deletee_title = deletee_account_type.GetTitle()
                        
                        list_of_tuples = [ ( account_type.GetTitle(), account_type ) for account_type in account_types_can_move_to ]
                        
                        with ClientGUIDialogs.DialogSelectFromList( self, 'what should deleted ' + deletee_title + ' accounts become?', list_of_tuples ) as dlg:
                            
                            if dlg.ShowModal() == wx.ID_OK:
                                
                                new_account_type = dlg.GetChoice()
                                
                            else:
                                
                                return
                                
                            
                        
                    else:
                        
                        ( new_account_type, ) = account_types_can_move_to
                        
                    
                    deletee_account_type_key = deletee_account_type.GetAccountTypeKey()
                    new_account_type_key = new_account_type.GetAccountTypeKey()
                    
                    self._deletee_account_type_keys_to_new_account_type_keys[ deletee_account_type_key ] = new_account_type_key
                    
                
                self._account_types_listctrl.RemoveAllSelected()
                
            
        
    
    def _Edit( self ):
        
        indices = self._account_types_listctrl.GetAllSelected()
        
        for index in indices:
            
            account_type = self._account_types_listctrl.GetObject( index )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit account type' ) as dlg_edit:
                
                panel = ClientGUIScrolledPanelsEdit.EditAccountTypePanel( dlg_edit, self._admin_service.GetServiceType(), account_type )
                
                dlg_edit.SetPanel( panel )
                
                if dlg_edit.ShowModal() == wx.ID_OK:
                    
                    edited_account_type = panel.GetValue()
                    
                    ( display_tuple, sort_tuple ) = self._ConvertAccountTypeToTuples( edited_account_type )
                    
                    self._account_types_listctrl.UpdateRow( index, display_tuple, sort_tuple, edited_account_type )
                    
                else:
                    
                    return
                    
                
            
        
    
    def CommitChanges( self ):
        
        account_types = self._account_types_listctrl.GetObjects()
        
        def key_transfer_not_collapsed():
            
            keys = set( self._deletee_account_type_keys_to_new_account_type_keys.keys() )
            values = set( self._deletee_account_type_keys_to_new_account_type_keys.values() )
            
            return len( keys.intersection( values ) ) > 0
            
        
        while key_transfer_not_collapsed():
            
            # some deletees are going to other deletees, so lets collapse
            
            deletee_account_type_keys = set( self._deletee_account_type_keys_to_new_account_type_keys.keys() )
            
            account_type_keys_tuples = self._deletee_account_type_keys_to_new_account_type_keys.items()
            
            for ( deletee_account_type_key, new_account_type_key ) in account_type_keys_tuples:
                
                if new_account_type_key in deletee_account_type_keys:
                    
                    better_new_account_type_key = self._deletee_account_type_keys_to_new_account_type_keys[ new_account_type_key ]
                    
                    self._deletee_account_type_keys_to_new_account_type_keys[ deletee_account_type_key ] = better_new_account_type_key
                    
                
            
        
        serialisable_deletee_account_type_keys_to_new_account_type_keys = HydrusSerialisable.SerialisableBytesDictionary( self._deletee_account_type_keys_to_new_account_type_keys )
        
        self._admin_service.Request( HC.POST, 'account_types', { 'account_types' : account_types, 'deletee_account_type_keys_to_new_account_type_keys' : serialisable_deletee_account_type_keys_to_new_account_type_keys } )
        
    
class ManageClientServicesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( self, 'manage_services', 25, 20, [ ( 'type', 20 ), ( 'name', -1 ), ( 'deletable', 12 ) ], self._ConvertServiceToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit)
        
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
        
        self._listctrl.Sort( 0 )
        
        #
        
        add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        add_remove_hbox.Add( self._add_button, CC.FLAGS_LONE_BUTTON )
        add_remove_hbox.Add( self._edit_button, CC.FLAGS_LONE_BUTTON )
        add_remove_hbox.Add( self._delete_button, CC.FLAGS_LONE_BUTTON )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( add_remove_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _Add( self, service_type ):
        
        service_key = HydrusData.GenerateKey()
        name = 'new service'
        
        service = ClientServices.GenerateService( service_key, service_type, name )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit service' ) as dlg:
            
            panel = self._EditPanel( dlg, service )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_service = panel.GetValue()
                
                ClientGUIListCtrl.SetNonDupeName( new_service, self._GetExistingNames() )
                
                self._listctrl.AddDatas( ( new_service, ) )
                
                self._listctrl.Sort()
                
            
        
    
    def _ConvertServiceToListCtrlTuples( self, service ):
        
        service_type = service.GetServiceType()
        name = service.GetName()
        deletable = service_type in HC.ADDREMOVABLE_SERVICES
        
        pretty_service_type = HC.service_string_lookup[ service_type ]
        
        if deletable:
            
            pretty_deletable = 'yes'
            
        else:
            
            pretty_deletable = ''
            
        
        return ( ( pretty_service_type, name, pretty_deletable ), ( pretty_service_type, name, deletable ) )
        
    
    def _GetExistingNames( self ):
        
        services = self._listctrl.GetData()
        
        names = { service.GetName() for service in services }
        
        return names
        
    
    def _Delete( self ):
        
        selected_services = self._listctrl.GetData( only_selected = True )
        
        deletable_services = [ service for service in selected_services if service.GetServiceType() in HC.ADDREMOVABLE_SERVICES ]
        
        if len( deletable_services ) > 0:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Delete the selected services?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._listctrl.DeleteDatas( deletable_services )
                    
                
            
        
    
    def _Edit( self ):
        
        selected_services = self._listctrl.GetData( only_selected = True )
        
        try:
            
            for service in selected_services:
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'edit service' ) as dlg:
                    
                    panel = self._EditPanel( dlg, service )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        self._listctrl.DeleteDatas( ( service, ) )
                        
                        edited_service = panel.GetValue()
                        
                        ClientGUIListCtrl.SetNonDupeName( edited_service, self._GetExistingNames() )
                        
                        self._listctrl.AddDatas( ( edited_service, ) )
                        
                    else:
                        
                        return
                        
                    
                
            
        finally:
            
            self._listctrl.Sort()
            
        
    
    def CommitChanges( self ):
        
        services = self._listctrl.GetData()
        
        new_service_keys = { service.GetServiceKey() for service in services }
        
        deletee_service_names = [ service.GetName() for service in self._original_services if service.GetServiceKey() not in new_service_keys ]
        
        if len( deletee_service_names ) > 0:
            
            message = 'You are about to delete the following services:'
            message += os.linesep * 2
            message += os.linesep.join( deletee_service_names )
            message += os.linesep * 2
            message += 'Are you absolutely sure this is correct?'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    raise HydrusExceptions.VetoException( 'Commit cancelled by user! If you do not believe you meant to delete any services (i.e the code accidentally intended to delete them all by itself), please inform hydrus dev immediately.' )
                    
                
            
            
        
        HG.client_controller.SetServices( services )
        
    
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
                
            
            if self._service_type in HC.TAG_SERVICES:
                
                self._panels.append( self._ServiceTagPanel( self, self._dictionary ) )
                
            
            if self._service_type == HC.LOCAL_BOORU:
                
                self._panels.append( self._ServiceLocalBooruPanel( self, self._dictionary ) )
                
            
            if self._service_type in HC.RATINGS_SERVICES:
                
                self._panels.append( self._ServiceRatingsPanel( self, self._dictionary ) )
                
                if self._service_type == HC.LOCAL_RATING_NUMERICAL:
                    
                    self._panels.append( self._ServiceRatingsNumericalPanel( self, self._dictionary ) )
                    
                
            
            if self._service_type == HC.IPFS:
                
                self._panels.append( self._ServiceIPFSPanel( self, self._dictionary ) )
                
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._service_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            for panel in self._panels:
                
                vbox.Add( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            self.SetSizer( vbox )
            
        
        def _GetArchiveNameToDisplay( self, portable_hta_path, namespaces ):
            
            hta_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_hta_path )
            
            if len( namespaces ) == 0: name_to_display = hta_path
            else: name_to_display = hta_path + ' (' + ', '.join( HydrusData.ConvertUglyNamespacesToPrettyStrings( namespaces ) ) + ')'
            
            return name_to_display
            
        
        def EventArchiveAdd( self, event ):
            
            if self._archive_sync.GetCount() == 0:
                
                wx.MessageBox( 'Be careful with this tool! Syncing a lot of files to a large archive can take a very long time to initialise.' )
                
            
            text = 'Select the Hydrus Tag Archive\'s location.'
            
            with wx.FileDialog( self, message = text, style = wx.FD_OPEN ) as dlg_file:
                
                if dlg_file.ShowModal() == wx.ID_OK:
                    
                    hta_path = HydrusData.ToUnicode( dlg_file.GetPath() )
                    
                    portable_hta_path = HydrusPaths.ConvertAbsPathToPortablePath( hta_path )
                    
                    hta = HydrusTagArchive.HydrusTagArchive( hta_path )
                    
                    archive_namespaces = list( hta.GetNamespaces() )
                    
                    archive_namespaces.sort()
                    
                    list_of_tuples = [ ( HydrusData.ConvertUglyNamespaceToPrettyString( namespace ), namespace, False ) for namespace in archive_namespaces ]
                    
                    with ClientGUIDialogs.DialogCheckFromList( self, 'Select namespaces', list_of_tuples ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            namespaces = dlg.GetChecked()
                            
                        else:
                            
                            return
                            
                        
                    
                    name_to_display = self._GetArchiveNameToDisplay( portable_hta_path, namespaces )
                    
                    self._archive_sync.Append( name_to_display, ( portable_hta_path, namespaces ) )
                    
                
            
        
        def EventArchiveEdit( self, event ):
            
            selection = self._archive_sync.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                ( portable_hta_path, existing_namespaces ) = self._archive_sync.GetClientData( selection )
                
                hta_path = HydrusPaths.ConvertPortablePathToAbsPath( portable_hta_path )
                
                if not os.path.exists( hta_path ):
                    
                    wx.MessageBox( 'This archive does not seem to exist any longer!' )
                    
                    return
                    
                
                hta = HydrusTagArchive.HydrusTagArchive( hta_path )
                
                archive_namespaces = list( hta.GetNamespaces() )
                
                archive_namespaces.sort()
                
                list_of_tuples = [ ( HydrusData.ConvertUglyNamespaceToPrettyString( namespace ), namespace, namespace in existing_namespaces ) for namespace in archive_namespaces ]
                
                with ClientGUIDialogs.DialogCheckFromList( self, 'Select namespaces', list_of_tuples ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        namespaces = dlg.GetChecked()
                        
                    else:
                        
                        return
                        
                    
                
                name_to_display = self._GetArchiveNameToDisplay( portable_hta_path, namespaces )
                
                self._archive_sync.SetString( selection, name_to_display )
                self._archive_sync.SetClientData( selection, ( portable_hta_path, namespaces ) )
                
            
        
        def EventArchiveRemove( self, event ):
            
            selection = self._archive_sync.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
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
                
                self._name = wx.TextCtrl( self )
                
                #
                
                self._name.SetValue( name )
                
                #
                
                self.Add( self._name, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                name = self._name.GetValue()
                
                if name == '':
                    
                    raise HydrusExceptions.VetoException( 'Please enter a name!' )
                    
                
                return name
                
            
        
        class _ServiceRemotePanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, service_type, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'network connection' )
                
                self._service_type = service_type
                
                credentials = dictionary[ 'credentials' ]
                
                self._host = wx.TextCtrl( self )
                self._port = wx.SpinCtrl( self, min = 1, max = 65535, size = ( 80, -1 ) )
                
                self._test_address_button = ClientGUICommon.BetterButton( self, 'test address', self._TestAddress )
                
                #
                
                ( host, port ) = credentials.GetAddress()
                
                self._host.SetValue( host )
                self._port.SetValue( port )
                
                #
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.Add( self._host, CC.FLAGS_EXPAND_BOTH_WAYS )
                hbox.Add( ClientGUICommon.BetterStaticText( self, ':' ), CC.FLAGS_VCENTER )
                hbox.Add( self._port, CC.FLAGS_VCENTER )
                
                wrapped_hbox = ClientGUICommon.WrapInText( hbox, self, 'address: ' )
                
                self.Add( wrapped_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                self.Add( self._test_address_button, CC.FLAGS_LONE_BUTTON )
                
            
            def _TestAddress( self ):
                
                try:
                    
                    credentials = self.GetCredentials()
                    
                except HydrusExceptions.VetoException as e:
                    
                    message = HydrusData.ToUnicode( e )
                    
                    if len( message ) > 0:
                        
                        wx.MessageBox( message )
                        
                    
                    return
                    
                
                ( host, port ) = credentials.GetAddress()
                
                if self._service_type == HC.IPFS:
                    
                    scheme = 'http://'
                    request = 'api/v0/version'
                    
                else:
                    
                    scheme = 'https://'
                    request = ''
                    
                
                url = scheme + host + ':' + str( port ) + '/' + request
                
                network_job = ClientNetworking.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
                
                network_job.OverrideBandwidth()
                
                network_job.SetForLogin( True )
                
                HG.client_controller.network_engine.AddJob( network_job )
                
                try:
                    
                    network_job.WaitUntilDone()
                    
                    wx.MessageBox( 'Got an ok response!' )
                    
                except HydrusExceptions.NetworkException as e:
                    
                    wx.MessageBox( 'Problem with that address: ' + HydrusData.ToUnicode( e ) )
                    
                
            
            def GetCredentials( self ):
                
                host = self._host.GetValue()
                
                if host == '':
                    
                    raise HydrusExceptions.VetoException( 'Please enter a host!' )
                    
                
                port = self._port.GetValue()
                
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
                
                self._access_key = wx.TextCtrl( self, size = ( 400, -1 ) )
                
                self._test_credentials_button = ClientGUICommon.BetterButton( self, 'test access key', self._TestCredentials )
                self._register = ClientGUICommon.BetterButton( self, 'fetch an access key with a registration key', self._GetAccessKeyFromRegistrationKey )
                
                #
                
                if self._original_credentials.HasAccessKey():
                    
                    self._access_key.SetValue( self._original_credentials.GetAccessKey().encode( 'hex' ) )
                    
                
                #
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.Add( self._register, CC.FLAGS_LONE_BUTTON )
                hbox.Add( self._test_credentials_button, CC.FLAGS_LONE_BUTTON )
                
                wrapped_access_key = ClientGUICommon.WrapInText( self._access_key, self, 'access key: ' )
                
                self.Add( wrapped_access_key, CC.FLAGS_EXPAND_PERPENDICULAR )
                self.Add( hbox, CC.FLAGS_BUTTON_SIZER )
                
            
            def _GetAccessKeyFromRegistrationKey( self ):
                
                def wx_done():
                    
                    if not self:
                        
                        return
                        
                    
                    self._register.Enable()
                    self._register.SetLabel( 'fetch an access key with a registration key' )
                    
                
                def wx_setkey( access_key_encoded ):
                    
                    if not self:
                        
                        return
                        
                    
                    self._access_key.SetValue( access_key_encoded )
                    
                
                def do_it( credentials, registration_key ):
                    
                    try:
                        
                        ( host, port ) = credentials.GetAddress()
                        
                        url = 'https://' + host + ':' + str( port ) + '/access_key?registration_key=' + registration_key.encode( 'hex' )
                        
                        network_job = ClientNetworking.NetworkJobHydrus( CC.TEST_SERVICE_KEY, 'GET', url )
                        
                        network_job.OverrideBandwidth()
                        
                        network_job.SetForLogin( True )
                        
                        HG.client_controller.network_engine.AddJob( network_job )
                        
                        try:
                            
                            network_job.WaitUntilDone()
                            
                            content = network_job.GetContent()
                            
                            response = HydrusNetwork.ParseBodyString( content )
                            
                            access_key_encoded = response[ 'access_key' ].encode( 'hex' )
                            
                            wx.CallAfter( wx_setkey, access_key_encoded )
                            
                            wx.MessageBox( 'Looks good!' )
                            
                        except Exception as e:
                            
                            HydrusData.PrintException( e )
                            
                            wx.MessageBox( 'Had a problem: ' + HydrusData.ToUnicode( e ) )
                            
                        
                    finally:
                        
                        wx.CallAfter( wx_done )
                        
                    
                
                try:
                    
                    credentials = self._remote_panel.GetCredentials()
                    
                except HydrusExceptions.VetoException as e:
                    
                    message = HydrusData.ToUnicode( e )
                    
                    if len( message ) > 0:
                        
                        wx.MessageBox( message )
                        
                    
                    return
                    
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Enter the registration key.' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        registration_key_encoded = dlg.GetValue()
                        
                    else:
                        
                        return
                        
                    
                
                if registration_key_encoded[0] == 'r':
                    
                    registration_key_encoded = registration_key_encoded[1:]
                    
                
                if registration_key_encoded == 'init':
                    
                    registration_key = registration_key_encoded
                    
                else:
                    
                    try:
                        
                        registration_key = registration_key_encoded.decode( 'hex' )
                        
                    except:
                        
                        wx.MessageBox( 'Could not parse that registration key!' )
                        
                        return
                        
                    
                
                self._register.Disable()
                self._register.SetLabel( u'fetching\u2026' )
                
                HG.client_controller.CallToThread( do_it, credentials, registration_key )
                
            
            def _TestCredentials( self ):
                
                def do_it( credentials ):
                    
                    service = ClientServices.GenerateService( CC.TEST_SERVICE_KEY, self._service_type, CC.TEST_SERVICE_KEY )
                    
                    service.SetCredentials( credentials )
                    
                    try:
                        
                        if self._service_type in HC.RESTRICTED_SERVICES:
                            
                            response = service.Request( HC.GET, 'access_key_verification' )
                            
                            if not response[ 'verified' ]:
                                
                                wx.MessageBox( 'That access key was not recognised!' )
                                
                            else:
                                
                                wx.MessageBox( 'Everything looks ok!' )
                                
                            
                        
                    except HydrusExceptions.WrongServiceTypeException:
                        
                        wx.MessageBox( 'Connection was made, but the service was not a ' + HC.service_string_lookup[ self._service_type ] + '.' )
                        
                        return
                        
                    except HydrusExceptions.NetworkException as e:
                        
                        wx.MessageBox( 'Network problem: ' + HydrusData.ToUnicode( e ) )
                        
                        return
                        
                    finally:
                        
                        self._test_credentials_button.Enable()
                        self._test_credentials_button.SetLabel( 'test access key' )
                        
                    
                
                try:
                    
                    credentials = self.GetCredentials()
                    
                except HydrusExceptions.VetoException as e:
                    
                    message = HydrusData.ToUnicode( e )
                    
                    if len( message ) > 0:
                        
                        wx.MessageBox( message )
                        
                    
                    return
                    
                
                self._test_credentials_button.Disable()
                self._test_credentials_button.SetLabel( u'fetching\u2026' )
                
                HG.client_controller.CallToThread( do_it, credentials )
                
            
            def GetCredentials( self ):
                
                credentials = self._remote_panel.GetCredentials()
                
                try:
                    
                    access_key = self._access_key.GetValue().decode( 'hex' )
                    
                except:
                    
                    raise HydrusExceptions.VetoException( 'Could not understand that access key!')
                    
                
                if access_key != '':
                    
                    credentials.SetAccessKey( access_key )
                    
                
                return credentials
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                credentials = self.GetCredentials()
                
                if credentials != self._original_credentials:
                    
                    account = HydrusNetwork.Account.GenerateUnknownAccount()
                    
                    dictionary_part[ 'account' ] = HydrusNetwork.Account.GenerateSerialisableTupleFromAccount( account )
                    
                    network_context = ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, self._service_key )
                    
                    HG.client_controller.network_engine.session_manager.ClearSession( network_context )
                    
                
                dictionary_part[ 'credentials' ] = credentials
                
                return dictionary_part
                
            
        
        class _ServiceTagPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'tags' )
                
                self._st = ClientGUICommon.BetterStaticText( self )
                '''
            if service_type in HC.TAG_SERVICES:
                
                self._archive_panel = ClientGUICommon.StaticBox( self, 'archive synchronisation' )
                
                self._archive_sync = wx.ListBox( self._archive_panel, size = ( -1, 100 ) )
                
                self._archive_sync_add = wx.Button( self._archive_panel, label = 'add' )
                self._archive_sync_add.Bind( wx.EVT_BUTTON, self.EventArchiveAdd )
                
                self._archive_sync_edit = wx.Button( self._archive_panel, label = 'edit' )
                self._archive_sync_edit.Bind( wx.EVT_BUTTON, self.EventArchiveEdit )
                
                self._archive_sync_remove = wx.Button( self._archive_panel, label = 'remove' )
                self._archive_sync_remove.Bind( wx.EVT_BUTTON, self.EventArchiveRemove )
                
                
            if service_type in HC.TAG_SERVICES:
                
                for ( portable_hta_path, namespaces ) in info[ 'tag_archive_sync' ].items():
                    
                    name_to_display = self._GetArchiveNameToDisplay( portable_hta_path, namespaces )
                    
                    self._archive_sync.Append( name_to_display, ( portable_hta_path, namespaces ) )
                    
                
            
            
            
            if service_type in HC.TAG_SERVICES:
                
                tag_archives = {}
                
                for i in range( self._archive_sync.GetCount() ):
                    
                    ( portable_hta_path, namespaces ) = self._archive_sync.GetClientData( i )
                    
                    tag_archives[ portable_hta_path ] = namespaces
                    
                
                info[ 'tag_archive_sync' ] = tag_archives
                
            
                
            '''
                #
                
                self._st.SetLabelText( 'This is a tag service. This box will get regain tag archive options in a future update.' )
                
                #
                
                self.Add( self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                return dictionary_part
                
            
        
        class _ServiceLocalBooruPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'local booru' )
                
                self._booru_options_panel = ClientGUICommon.StaticBox( self, 'options' )
                
                self._port = ClientGUICommon.NoneableSpinCtrl( self._booru_options_panel, 'booru local port', none_phrase = 'do not run local booru service', min = 1, max = 65535 )
                
                self._upnp = ClientGUICommon.NoneableSpinCtrl( self._booru_options_panel, 'upnp port', none_phrase = 'do not forward port', max = 65535 )
                
                self._bandwidth_rules = ClientGUIControls.BandwidthRulesCtrl( self._booru_options_panel, dictionary[ 'bandwidth_rules' ] )
                
                #
                
                self._port.SetValue( dictionary[ 'port' ] )
                self._upnp.SetValue( dictionary[ 'upnp_port' ] )
                
                #
                
                self._booru_options_panel.Add( self._port, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._booru_options_panel.Add( self._upnp, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._booru_options_panel.Add( self._bandwidth_rules, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                self.Add( self._booru_options_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                dictionary_part[ 'port' ] = self._port.GetValue()
                dictionary_part[ 'upnp_port' ] = self._upnp.GetValue()
                dictionary_part[ 'bandwidth_rules' ] = self._bandwidth_rules.GetValue()
                
                return dictionary_part
                
            
        
        class _ServiceRatingsPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'ratings' )
                
                self._shape = ClientGUICommon.BetterChoice( self )
                
                self._shape.Append( 'circle', ClientRatings.CIRCLE )
                self._shape.Append( 'square', ClientRatings.SQUARE )
                self._shape.Append( 'star', ClientRatings.STAR )
                
                self._colour_ctrls = {}
                
                for colour_type in [ ClientRatings.LIKE, ClientRatings.DISLIKE, ClientRatings.NULL, ClientRatings.MIXED ]:
                    
                    border_ctrl = wx.ColourPickerCtrl( self )
                    fill_ctrl = wx.ColourPickerCtrl( self )
                    
                    border_ctrl.SetMaxSize( ( 20, -1 ) )
                    fill_ctrl.SetMaxSize( ( 20, -1 ) )
                    
                    self._colour_ctrls[ colour_type ] = ( border_ctrl, fill_ctrl )
                    
                
                #
                
                self._shape.SelectClientData( dictionary[ 'shape' ] )
                
                for ( colour_type, ( border_rgb, fill_rgb ) ) in dictionary[ 'colours' ]:
                    
                    ( border_ctrl, fill_ctrl ) = self._colour_ctrls[ colour_type ]
                    
                    border_ctrl.SetColour( wx.Colour( *border_rgb ) )
                    fill_ctrl.SetColour( wx.Colour( *fill_rgb ) )
                    
                
                #
                
                rows = []
                
                rows.append( ( 'shape: ', self._shape ) )
                
                for colour_type in [ ClientRatings.LIKE, ClientRatings.DISLIKE, ClientRatings.NULL, ClientRatings.MIXED ]:
                    
                    ( border_ctrl, fill_ctrl ) = self._colour_ctrls[ colour_type ]
                    
                    hbox = wx.BoxSizer( wx.HORIZONTAL )
                    
                    hbox.Add( border_ctrl, CC.FLAGS_VCENTER )
                    hbox.Add( fill_ctrl, CC.FLAGS_VCENTER )
                    
                    if colour_type == ClientRatings.LIKE: colour_text = 'liked'
                    elif colour_type == ClientRatings.DISLIKE: colour_text = 'disliked'
                    elif colour_type == ClientRatings.NULL: colour_text = 'not rated'
                    elif colour_type == ClientRatings.MIXED: colour_text = 'a mixture of ratings'
                    
                    rows.append( ( 'border/fill for ' + colour_text + ': ', hbox ) )
                    
                
                gridbox = ClientGUICommon.WrapInGrid( self, rows )
                
                self.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                dictionary_part[ 'shape' ] = self._shape.GetChoice()
                
                dictionary_part[ 'colours' ] = {}
                
                for ( colour_type, ( border_ctrl, fill_ctrl ) ) in self._colour_ctrls.items():
                    
                    border_colour = border_ctrl.GetColour()
                    
                    border_rgb = ( border_colour.Red(), border_colour.Green(), border_colour.Blue() )
                    
                    fill_colour = fill_ctrl.GetColour()
                    
                    fill_rgb = ( fill_colour.Red(), fill_colour.Green(), fill_colour.Blue() )
                    
                    dictionary_part[ 'colours' ][ colour_type ] = ( border_rgb, fill_rgb )
                    
                
                return dictionary_part
                
            
        
        class _ServiceRatingsNumericalPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'numerical ratings' )
                
                self._num_stars = wx.SpinCtrl( self, min = 1, max = 20 )
                self._allow_zero = wx.CheckBox( self )
                
                #
                
                self._num_stars.SetValue( dictionary[ 'num_stars' ] )
                self._allow_zero.SetValue( dictionary[ 'allow_zero' ] )
                
                #
                
                rows = []
                
                rows.append( ( 'number of \'stars\': ', self._num_stars ) )
                rows.append( ( 'allow a zero rating: ', self._allow_zero ) )
                
                gridbox = ClientGUICommon.WrapInGrid( self, rows )
                
                self.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                num_stars = self._num_stars.GetValue()
                allow_zero = self._allow_zero.GetValue()
                
                if num_stars == 1 and not allow_zero:
                    
                    allow_zero = True
                    
                
                dictionary_part[ 'num_stars' ] = num_stars
                dictionary_part[ 'allow_zero' ] = allow_zero
                
                return dictionary_part
                
            
        
        class _ServiceIPFSPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'ipfs' )
                
                self._multihash_prefix = wx.TextCtrl( self )
                
                tts = 'When you tell the client to copy the ipfs multihash to your clipboard, it will prefix it with this.'
                tts += os.linesep * 2
                tts += 'Use this if you would rather copy a full gateway url with that action. For instance, you could put here:'
                tts += os.linesep * 2
                tts += 'http://127.0.0.1:8080/ipfs/'
                tts += os.linesep
                tts += 'http://ipfs.io/ipfs/'
                
                self._multihash_prefix.SetToolTip( tts )
                
                #
                
                self._multihash_prefix.SetValue( dictionary[ 'multihash_prefix' ] )
                
                #
                
                self.Add( ClientGUICommon.WrapInText( self._multihash_prefix, self, 'multihash prefix: ' ), CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                dictionary_part[ 'multihash_prefix' ] = self._multihash_prefix.GetValue()
                
                return dictionary_part
                
            
        
    
class ManageOptionsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._new_options = HG.client_controller.new_options
        
        self._listbook = ClientGUICommon.ListBook( self )
        
        self._listbook.AddPage( 'gui', 'gui', self._GUIPanel( self._listbook ) ) # leave this at the top, to make it default page
        self._listbook.AddPage( 'connection', 'connection', self._ConnectionPanel( self._listbook ) )
        self._listbook.AddPage( 'files and trash', 'files and trash', self._FilesAndTrashPanel( self._listbook ) )
        self._listbook.AddPage( 'speed and memory', 'speed and memory', self._SpeedAndMemoryPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'maintenance and processing', 'maintenance and processing', self._MaintenanceAndProcessingPanel( self._listbook ) )
        self._listbook.AddPage( 'media', 'media', self._MediaPanel( self._listbook ) )
        #self._listbook.AddPage( 'sound', 'sound', self._SoundPanel( self._listbook ) )
        self._listbook.AddPage( 'default file system predicates', 'default file system predicates', self._DefaultFileSystemPredicatesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'colours', 'colours', self._ColoursPanel( self._listbook ) )
        self._listbook.AddPage( 'regex favourites', 'regex favourites', self._RegexPanel( self._listbook ) )
        self._listbook.AddPage( 'sort/collect', 'sort/collect', self._SortCollectPanel( self._listbook ) )
        self._listbook.AddPage( 'downloading', 'downloading', self._DownloadingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'importing', 'importing', self._ImportingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tag summaries', 'tag summaries', self._TagSummariesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tags', 'tags', self._TagsPanel( self._listbook, self._new_options ) )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    class _ColoursPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            coloursets_panel = ClientGUICommon.StaticBox( self, 'coloursets' )
            
            self._current_colourset = ClientGUICommon.BetterChoice( coloursets_panel )
            
            self._current_colourset.Append( 'default', 'default' )
            self._current_colourset.Append( 'darkmode', 'darkmode' )
            
            self._current_colourset.SelectClientData( self._new_options.GetString( 'current_colourset' ) )
            
            self._notebook = wx.Notebook( coloursets_panel )
            
            self._gui_colours = {}
            
            for colourset in ( 'default', 'darkmode' ):
                
                self._gui_colours[ colourset ] = {}
                
                colour_panel = wx.Panel( self._notebook )
                
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
                    
                    ctrl = wx.ColourPickerCtrl( colour_panel )
                    
                    ctrl.SetMaxSize( ( 20, -1 ) )
                    
                    ctrl.SetColour( self._new_options.GetColour( colour_type, colourset ) )
                    
                    self._gui_colours[ colourset ][ colour_type ] = ctrl
                    
                
                #
                
                rows = []
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.Add( self._gui_colours[ colourset ][ CC.COLOUR_THUMB_BACKGROUND ], CC.FLAGS_VCENTER )
                hbox.Add( self._gui_colours[ colourset ][ CC.COLOUR_THUMB_BACKGROUND_SELECTED ], CC.FLAGS_VCENTER )
                hbox.Add( self._gui_colours[ colourset ][ CC.COLOUR_THUMB_BACKGROUND_REMOTE ], CC.FLAGS_VCENTER )
                hbox.Add( self._gui_colours[ colourset ][ CC.COLOUR_THUMB_BACKGROUND_REMOTE_SELECTED ], CC.FLAGS_VCENTER )
                
                rows.append( ( 'thumbnail background (local: normal/selected, remote: normal/selected): ', hbox ) )
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.Add( self._gui_colours[ colourset ][ CC.COLOUR_THUMB_BORDER ], CC.FLAGS_VCENTER )
                hbox.Add( self._gui_colours[ colourset ][ CC.COLOUR_THUMB_BORDER_SELECTED ], CC.FLAGS_VCENTER )
                hbox.Add( self._gui_colours[ colourset ][ CC.COLOUR_THUMB_BORDER_REMOTE ], CC.FLAGS_VCENTER )
                hbox.Add( self._gui_colours[ colourset ][ CC.COLOUR_THUMB_BORDER_REMOTE_SELECTED ], CC.FLAGS_VCENTER )
                
                rows.append( ( 'thumbnail border (local: normal/selected, remote: normal/selected): ', hbox ) )
                
                rows.append( ( 'thumbnail grid background: ', self._gui_colours[ colourset ][ CC.COLOUR_THUMBGRID_BACKGROUND ] ) )
                rows.append( ( 'autocomplete background: ', self._gui_colours[ colourset ][ CC.COLOUR_AUTOCOMPLETE_BACKGROUND ] ) )
                rows.append( ( 'media viewer background: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_BACKGROUND ] ) )
                rows.append( ( 'media viewer text: ', self._gui_colours[ colourset ][ CC.COLOUR_MEDIA_TEXT ] ) )
                rows.append( ( 'tags box background: ', self._gui_colours[ colourset ][ CC.COLOUR_TAGS_BOX ] ) )
                
                gridbox = ClientGUICommon.WrapInGrid( colour_panel, rows )
                
                colour_panel.SetSizer( gridbox )
                
                select = colourset == 'default'
                
                self._notebook.AddPage( colour_panel, colourset, select = select )
                
            
            #
            
            namespace_colours_panel = ClientGUICommon.StaticBox( self, 'namespace colours' )
            
            self._namespace_colours = ClientGUIListBoxes.ListBoxTagsColourOptions( namespace_colours_panel, HC.options[ 'namespace_colours' ] )
            
            self._edit_namespace_colour = wx.Button( namespace_colours_panel, label = 'edit selected' )
            self._edit_namespace_colour.Bind( wx.EVT_BUTTON, self.EventEditNamespaceColour )
            
            self._new_namespace_colour = wx.TextCtrl( namespace_colours_panel, style = wx.TE_PROCESS_ENTER )
            self._new_namespace_colour.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownNamespace )
            
            #
            
            coloursets_panel.Add( ClientGUICommon.WrapInText( self._current_colourset, coloursets_panel, 'current colourset: ' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            coloursets_panel.Add( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            namespace_colours_panel.Add( self._namespace_colours, CC.FLAGS_EXPAND_BOTH_WAYS )
            namespace_colours_panel.Add( self._new_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            namespace_colours_panel.Add( self._edit_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( coloursets_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.Add( namespace_colours_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
        
        def EventEditNamespaceColour( self, event ):
            
            results = self._namespace_colours.GetSelectedNamespaceColours()
            
            for ( namespace, colour ) in results.items():
                
                colour_data = wx.ColourData()
                
                colour_data.SetColour( colour )
                colour_data.SetChooseFull( True )
                
                with wx.ColourDialog( self, data = colour_data ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        colour_data = dlg.GetColourData()
                        
                        colour = colour_data.GetColour()
                        
                        self._namespace_colours.SetNamespaceColour( namespace, colour )
                        
                    
                
            
        
        def EventKeyDownNamespace( self, event ):
            
            ( modifier, key ) = ClientData.ConvertKeyEventToSimpleTuple( event )
            
            if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                namespace = self._new_namespace_colour.GetValue()
                
                if namespace != '':
                    
                    self._namespace_colours.SetNamespaceColour( namespace, wx.Colour( random.randint( 0, 255 ), random.randint( 0, 255 ), random.randint( 0, 255 ) ) )
                    
                    self._new_namespace_colour.SetValue( '' )
                    
                
            else:
                
                event.Skip()
                
            
        
        def UpdateOptions( self ):
            
            for colourset in self._gui_colours:
                
                for ( colour_type, ctrl ) in self._gui_colours[ colourset ].items():
                    
                    colour = ctrl.GetColour()
                    
                    self._new_options.SetColour( colour_type, colourset, colour )
                    
                
            
            self._new_options.SetString( 'current_colourset', self._current_colourset.GetChoice() )
            
            HC.options[ 'namespace_colours' ] = self._namespace_colours.GetNamespaceColours()
            
        
    
    class _ConnectionPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            general = ClientGUICommon.StaticBox( self, 'general' )
            
            self._verify_regular_https = wx.CheckBox( general )
            
            self._external_host = wx.TextCtrl( self )
            self._external_host.SetToolTip( 'If you have trouble parsing your external ip using UPnP, you can force it to be this.' )
            
            self._network_timeout = wx.SpinCtrl( self, min = 3, max = 300 )
            self._network_timeout.SetToolTip( 'If a network connection experiences any uninterrupted inactivity for this duration, it will throw an error.' )
            
            proxy_panel = ClientGUICommon.StaticBox( self, 'proxy settings' )
            
            self._proxy_type = ClientGUICommon.BetterChoice( proxy_panel )
            
            self._proxy_address = wx.TextCtrl( proxy_panel )
            self._proxy_port = wx.SpinCtrl( proxy_panel, min = 0, max = 65535 )
            
            self._proxy_username = wx.TextCtrl( proxy_panel )
            self._proxy_password = wx.TextCtrl( proxy_panel )
            
            #
            
            self._new_options = HG.client_controller.new_options
            
            self._verify_regular_https.SetValue( self._new_options.GetBoolean( 'verify_regular_https' ) )
            
            if HC.options[ 'external_host' ] is not None:
                
                self._external_host.SetValue( HC.options[ 'external_host' ] )
                
            
            self._network_timeout.SetValue( self._new_options.GetInteger( 'network_timeout' ) )
            
            self._proxy_type.Append( 'http', 'http' )
            self._proxy_type.Append( 'socks4', 'socks4' )
            self._proxy_type.Append( 'socks5', 'socks5' )
            
            if HC.options[ 'proxy' ] is not None:
                
                ( proxytype, host, port, username, password ) = HC.options[ 'proxy' ]
                
                self._proxy_type.SelectClientData( proxytype )
                
                self._proxy_address.SetValue( host )
                self._proxy_port.SetValue( port )
                
                if username is not None:
                    
                    self._proxy_username.SetValue( username )
                    
                
                if password is not None:
                    
                    self._proxy_password.SetValue( password )
                    
                
            else:
                
                self._proxy_type.Select( 0 )
                
            
            #
            
            rows = []
            
            rows.append( ( 'BUGFIX: verify regular https traffic:', self._verify_regular_https ) )
            
            gridbox = ClientGUICommon.WrapInGrid( general, rows )
            
            general.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            text = 'You have to restart the client for proxy settings to take effect.'
            text += os.linesep
            text += 'This is in a buggy prototype stage right now, pending a rewrite of the networking engine.'
            text += os.linesep
            text += 'Please send me your feedback.'
            
            proxy_panel.Add( wx.StaticText( proxy_panel, label = text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'proxy type: ', self._proxy_type ) )
            rows.append( ( 'address: ', self._proxy_address ) )
            rows.append( ( 'port: ', self._proxy_port ) )
            rows.append( ( 'username (optional): ', self._proxy_username ) )
            rows.append( ( 'password (optional): ', self._proxy_password ) )
            
            gridbox = ClientGUICommon.WrapInGrid( proxy_panel, rows )
            
            proxy_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            proxy_panel.Hide() # proxy settings no longer in use for new engine
            
            #
            
            rows = []
            
            rows.append( ( 'external ip/host override: ', self._external_host ) )
            rows.append( ( 'network timeout (seconds): ', self._network_timeout ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( general, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.Add( proxy_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'verify_regular_https', self._verify_regular_https.GetValue() )
            
            if self._proxy_address.GetValue() == '':
                
                HC.options[ 'proxy' ] = None
                
            else:
                
                proxytype = self._proxy_type.GetChoice()
                address = self._proxy_address.GetValue()
                port = self._proxy_port.GetValue()
                username = self._proxy_username.GetValue()
                password = self._proxy_password.GetValue()
                
                if username == '': username = None
                if password == '': password = None
                
                HC.options[ 'proxy' ] = ( proxytype, address, port, username, password )
                
            
            external_host = self._external_host.GetValue()
            
            if external_host == '':
                
                external_host = None
                
            
            HC.options[ 'external_host' ] = external_host
            
            self._new_options.SetInteger( 'network_timeout', self._network_timeout.GetValue() )
            
        
    
    class _DownloadingPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            gallery_downloader = ClientGUICommon.StaticBox( self, 'gallery downloader' )
            
            self._gallery_file_limit = ClientGUICommon.NoneableSpinCtrl( gallery_downloader, 'by default, stop searching once this many files are found', none_phrase = 'no limit', min = 1, max = 1000000 )
            
            #
            
            subscriptions = ClientGUICommon.StaticBox( self, 'subscriptions' )
            
            self._process_subs_in_random_order = wx.CheckBox( subscriptions )
            self._process_subs_in_random_order.SetToolTip( 'Processing in random order is useful whenever bandwidth is tight, as it stops an \'aardvark\' subscription from always getting first whack at what is available. Otherwise, they will be processed in alphabetical order.' )
            
            #
            
            thread_checker = ClientGUICommon.StaticBox( self, 'thread checker' )
            
            self._permit_watchers_to_name_their_pages = wx.CheckBox( thread_checker )
            
            self._thread_watcher_not_found_page_string = ClientGUICommon.NoneableTextCtrl( thread_checker, none_phrase = 'do not show' )
            self._thread_watcher_dead_page_string = ClientGUICommon.NoneableTextCtrl( thread_checker, none_phrase = 'do not show' )
            self._thread_watcher_paused_page_string = ClientGUICommon.NoneableTextCtrl( thread_checker, none_phrase = 'do not show' )
            
            checker_options = self._new_options.GetDefaultThreadCheckerOptions()
            
            self._thread_checker_options = ClientGUITime.EditCheckerOptions( thread_checker, checker_options )
            
            #
            
            self._process_subs_in_random_order.SetValue( self._new_options.GetBoolean( 'process_subs_in_random_order' ) )
            
            self._gallery_file_limit.SetValue( HC.options[ 'gallery_file_limit' ] )
            
            self._permit_watchers_to_name_their_pages.SetValue( self._new_options.GetBoolean( 'permit_watchers_to_name_their_pages' ) )
            
            self._thread_watcher_not_found_page_string.SetValue( self._new_options.GetNoneableString( 'thread_watcher_not_found_page_string' ) )
            self._thread_watcher_dead_page_string.SetValue( self._new_options.GetNoneableString( 'thread_watcher_dead_page_string' ) )
            self._thread_watcher_paused_page_string.SetValue( self._new_options.GetNoneableString( 'thread_watcher_paused_page_string' ) )
            
            #
            
            gallery_downloader.Add( self._gallery_file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Sync subscriptions in random order:', self._process_subs_in_random_order ) )
            
            gridbox = ClientGUICommon.WrapInGrid( subscriptions, rows )
            
            subscriptions.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            
            rows = []
            
            rows.append( ( 'Permit thread checkers to name their own pages:', self._permit_watchers_to_name_their_pages ) )
            rows.append( ( 'Prepend 404 thread checker page names with this:', self._thread_watcher_not_found_page_string ) )
            rows.append( ( 'Prepend dead thread checker page names with this:', self._thread_watcher_dead_page_string ) )
            rows.append( ( 'Prepend paused thread checker page names with this:', self._thread_watcher_paused_page_string ) )
            
            gridbox = ClientGUICommon.WrapInGrid( thread_checker, rows )
            
            thread_checker.Add( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            thread_checker.Add( self._thread_checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( gallery_downloader, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( subscriptions, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( thread_checker, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'gallery_file_limit' ] = self._gallery_file_limit.GetValue()
            
            self._new_options.SetBoolean( 'process_subs_in_random_order', self._process_subs_in_random_order.GetValue() )
            
            self._new_options.SetBoolean( 'permit_watchers_to_name_their_pages', self._permit_watchers_to_name_their_pages.GetValue() )
            
            self._new_options.SetDefaultThreadCheckerOptions( self._thread_checker_options.GetValue() )
            
            self._new_options.SetNoneableString( 'thread_watcher_not_found_page_string', self._thread_watcher_not_found_page_string.GetValue() )
            self._new_options.SetNoneableString( 'thread_watcher_dead_page_string', self._thread_watcher_dead_page_string.GetValue() )
            self._new_options.SetNoneableString( 'thread_watcher_paused_page_string', self._thread_watcher_paused_page_string.GetValue() )
            
        
    
    class _ImportingPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            default_fios = ClientGUICommon.StaticBox( self, 'default file import options' )
            
            import ClientGUIImport
            
            quiet_file_import_options = self._new_options.GetDefaultFileImportOptions( 'quiet' )
            
            self._quiet_fios = ClientGUIImport.FileImportOptionsButton( default_fios, quiet_file_import_options )
            
            loud_file_import_options = self._new_options.GetDefaultFileImportOptions( 'loud' )
            
            self._loud_fios = ClientGUIImport.FileImportOptionsButton( default_fios, loud_file_import_options )
            
            #
            
            default_tios = ClientGUICommon.StaticBox( self, 'default tag import options' )
            
            self._tag_import_options = wx.ListBox( default_tios )
            self._tag_import_options.Bind( wx.EVT_LEFT_DCLICK, self.EventEdit )
            
            self._add = wx.Button( default_tios, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._edit = wx.Button( default_tios, label = 'edit' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._delete = wx.Button( default_tios, label = 'delete' )
            self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
            
            #
            
            for ( gallery_identifier, tag_import_options ) in self._new_options.GetDefaultTagImportOptions().items():
                
                name = gallery_identifier.ToString()
                
                self._tag_import_options.Append( name, ( gallery_identifier, tag_import_options ) )
                
            
            #
            
            rows = []
            
            rows.append( ( 'For \'quiet\' import contexts like import folders and subscriptions:', self._quiet_fios ) )
            rows.append( ( 'For import contexts that work on pages:', self._loud_fios ) )
            
            gridbox = ClientGUICommon.WrapInGrid( default_fios, rows )
            
            default_fios.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            default_tios.Add( self._tag_import_options, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._add, CC.FLAGS_VCENTER )
            hbox.Add( self._edit, CC.FLAGS_VCENTER )
            hbox.Add( self._delete, CC.FLAGS_VCENTER )
            
            default_tios.Add( hbox, CC.FLAGS_BUTTON_SIZER )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( default_fios, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( default_tios, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
        
        def EventAdd( self, event ):
            
            gallery_identifiers = []
            
            for site_type in [ HC.SITE_TYPE_DEFAULT, HC.SITE_TYPE_DEVIANT_ART, HC.SITE_TYPE_HENTAI_FOUNDRY, HC.SITE_TYPE_NEWGROUNDS, HC.SITE_TYPE_PIXIV, HC.SITE_TYPE_TUMBLR, HC.SITE_TYPE_THREAD_WATCHER ]:
                
                gallery_identifiers.append( ClientDownloading.GalleryIdentifier( site_type ) )
                
            
            gallery_identifiers.append( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_BOORU ) )
            
            boorus = HG.client_controller.Read( 'remote_boorus' )
            
            for booru_name in boorus.keys():
                
                gallery_identifiers.append( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_BOORU, additional_info = booru_name ) )
                
            
            list_of_tuples = [ ( gallery_identifier.ToString(), gallery_identifier ) for gallery_identifier in gallery_identifiers ]
            
            with ClientGUIDialogs.DialogSelectFromList( self, 'select tag domain', list_of_tuples ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    gallery_identifier = dlg.GetChoice()
                    
                    name = gallery_identifier.ToString()
                    
                    for i in range( self._tag_import_options.GetCount() ):
                        
                        if name == self._tag_import_options.GetString( i ):
                            
                            wx.MessageBox( 'You already have default tag import options set up for that domain!' )
                            
                            return
                            
                        
                    
                    new_options = HG.client_controller.new_options
                    
                    tag_import_options = new_options.GetDefaultTagImportOptions( gallery_identifier )
                    
                    ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( gallery_identifier )
                    
                    with ClientGUITopLevelWindows.DialogEdit( self, 'edit tag import options' ) as dlg:
                        
                        panel = ClientGUIScrolledPanelsEdit.EditTagImportOptionsPanel( dlg, namespaces, tag_import_options )
                        
                        dlg.SetPanel( panel )
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            tag_import_options = panel.GetValue()
                            
                            self._tag_import_options.Append( name, ( gallery_identifier, tag_import_options ) )
                            
                        
                    
                
            
        
        def EventDelete( self, event ):
            
            selection = self._tag_import_options.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                name = self._tag_import_options.GetString( selection )
                
                with ClientGUIDialogs.DialogYesNo( self, 'Delete \'' + name + '\' entry?' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        self._tag_import_options.Delete( selection )
                        
                    
                
            
        
        def EventEdit( self, event ):
            
            selection = self._tag_import_options.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                name = self._tag_import_options.GetString( selection )
                
                ( gallery_identifier, tag_import_options ) = self._tag_import_options.GetClientData( selection )
                
                ( namespaces, search_value ) = ClientDefaults.GetDefaultNamespacesAndSearchValue( gallery_identifier )
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'edit tag import options' ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsEdit.EditTagImportOptionsPanel( dlg, namespaces, tag_import_options )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        tag_import_options = panel.GetValue()
                        
                        self._tag_import_options.SetClientData( selection, ( gallery_identifier, tag_import_options ) )
                        
                    
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetDefaultFileImportOptions( 'quiet', self._quiet_fios.GetValue() )
            self._new_options.SetDefaultFileImportOptions( 'loud', self._loud_fios.GetValue() )
            
            self._new_options.ClearDefaultTagImportOptions()
            
            for ( gallery_identifier, tag_import_options ) in [ self._tag_import_options.GetClientData( i ) for i in range( self._tag_import_options.GetCount() ) ]:
                
                self._new_options.SetDefaultTagImportOptions( gallery_identifier, tag_import_options )
                
            
        
    
    class _MaintenanceAndProcessingPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._jobs_panel = ClientGUICommon.StaticBox( self, 'when to run high cpu jobs' )
            self._maintenance_panel = ClientGUICommon.StaticBox( self, 'maintenance period' )
            
            self._idle_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'idle' )
            self._shutdown_panel = ClientGUICommon.StaticBox( self._jobs_panel, 'shutdown' )
            
            #
            
            self._idle_normal = wx.CheckBox( self._idle_panel )
            self._idle_normal.Bind( wx.EVT_CHECKBOX, self.EventIdleNormal )
            
            self._idle_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, '', min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore normal browsing' )
            self._idle_mouse_period = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, '', min = 1, max = 1000, multiplier = 60, unit = 'minutes', none_phrase = 'ignore mouse movements' )
            self._idle_cpu_max = ClientGUICommon.NoneableSpinCtrl( self._idle_panel, '', min = 5, max = 99, unit = '%', none_phrase = 'ignore cpu usage' )
            
            #
            
            self._idle_shutdown = ClientGUICommon.BetterChoice( self._shutdown_panel )
            
            for idle_id in ( CC.IDLE_NOT_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN, CC.IDLE_ON_SHUTDOWN_ASK_FIRST ):
                
                self._idle_shutdown.Append( CC.idle_string_lookup[ idle_id ], idle_id )
                
            
            self._idle_shutdown.Bind( wx.EVT_CHOICE, self.EventIdleShutdown )
            
            self._idle_shutdown_max_minutes = wx.SpinCtrl( self._shutdown_panel, min = 1, max = 1440 )
            
            #
            
            self._maintenance_vacuum_period_days = ClientGUICommon.NoneableSpinCtrl( self._maintenance_panel, '', min = 1, max = 365, none_phrase = 'do not automatically vacuum' )
            
            #
            
            self._idle_normal.SetValue( HC.options[ 'idle_normal' ] )
            self._idle_period.SetValue( HC.options[ 'idle_period' ] )
            self._idle_mouse_period.SetValue( HC.options[ 'idle_mouse_period' ] )
            self._idle_cpu_max.SetValue( HC.options[ 'idle_cpu_max' ] )
            
            self._idle_shutdown.SelectClientData( HC.options[ 'idle_shutdown' ] )
            self._idle_shutdown_max_minutes.SetValue( HC.options[ 'idle_shutdown_max_minutes' ] )
            
            self._maintenance_vacuum_period_days.SetValue( self._new_options.GetNoneableInteger( 'maintenance_vacuum_period_days' ) )
            
            #
            
            rows = []
            
            rows.append( ( 'Run maintenance jobs when the client is idle and the system is not otherwise busy: ', self._idle_normal ) )
            rows.append( ( 'Assume the client is idle if no general browsing activity has occured in the past: ', self._idle_period ) )
            rows.append( ( 'Assume the client is idle if the mouse has not been moved in the past: ', self._idle_mouse_period ) )
            rows.append( ( 'Assume the system is busy if any CPU core has recent average usage above: ', self._idle_cpu_max ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._idle_panel, rows )
            
            self._idle_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Run jobs on shutdown: ', self._idle_shutdown ) )
            rows.append( ( 'Max number of minutes to run shutdown jobs: ', self._idle_shutdown_max_minutes ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._shutdown_panel, rows )
            
            self._shutdown_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
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
            
            st = wx.StaticText( self._jobs_panel, label = text )
            
            st.Wrap( 550 )
            
            self._jobs_panel.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.Add( self._idle_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.Add( self._shutdown_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Number of days to wait between vacuums: ', self._maintenance_vacuum_period_days ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._maintenance_panel, rows )
            
            self._maintenance_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._maintenance_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
            self._EnableDisableIdleNormal()
            self._EnableDisableIdleShutdown()
            
        
        def _EnableDisableIdleNormal( self ):
            
            if self._idle_normal.GetValue() == True:
                
                self._idle_period.Enable()
                self._idle_mouse_period.Enable()
                self._idle_cpu_max.Enable()
                
            else:
                
                self._idle_period.Disable()
                self._idle_mouse_period.Disable()
                self._idle_cpu_max.Disable()
                
            
        
        def _EnableDisableIdleShutdown( self ):
            
            if self._idle_shutdown.GetChoice() == CC.IDLE_NOT_ON_SHUTDOWN:
                
                self._idle_shutdown_max_minutes.Disable()
                
            else:
                
                self._idle_shutdown_max_minutes.Enable()
                
            
        
        def EventIdleNormal( self, event ):
            
            self._EnableDisableIdleNormal()
            
        
        def EventIdleShutdown( self, event ):
            
            self._EnableDisableIdleShutdown()
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'idle_normal' ] = self._idle_normal.GetValue()
            
            HC.options[ 'idle_period' ] = self._idle_period.GetValue()
            HC.options[ 'idle_mouse_period' ] = self._idle_mouse_period.GetValue()
            HC.options[ 'idle_cpu_max' ] = self._idle_cpu_max.GetValue()
            
            HC.options[ 'idle_shutdown' ] = self._idle_shutdown.GetChoice()
            HC.options[ 'idle_shutdown_max_minutes' ] = self._idle_shutdown_max_minutes.GetValue()
            
            self._new_options.SetNoneableInteger( 'maintenance_vacuum_period_days', self._maintenance_vacuum_period_days.GetValue() )
            
        
    
    class _DefaultFileSystemPredicatesPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            self._filter_inbox_and_archive_predicates = wx.CheckBox( self, label = 'hide inbox and archive predicates if either has no files' )
            
            self._filter_inbox_and_archive_predicates.SetValue( self._new_options.GetBoolean( 'filter_inbox_and_archive_predicates' ) )
            
            self._file_system_predicate_age = ClientGUIPredicates.PanelPredicateSystemAgeDelta( self )
            self._file_system_predicate_duration = ClientGUIPredicates.PanelPredicateSystemDuration( self )
            self._file_system_predicate_height = ClientGUIPredicates.PanelPredicateSystemHeight( self )
            self._file_system_predicate_limit = ClientGUIPredicates.PanelPredicateSystemLimit( self )
            self._file_system_predicate_mime = ClientGUIPredicates.PanelPredicateSystemMime( self )
            self._file_system_predicate_num_pixels = ClientGUIPredicates.PanelPredicateSystemNumPixels( self )
            self._file_system_predicate_num_tags = ClientGUIPredicates.PanelPredicateSystemNumTags( self )
            self._file_system_predicate_num_words = ClientGUIPredicates.PanelPredicateSystemNumWords( self )
            self._file_system_predicate_ratio = ClientGUIPredicates.PanelPredicateSystemRatio( self )
            self._file_system_predicate_similar_to = ClientGUIPredicates.PanelPredicateSystemSimilarTo( self )
            self._file_system_predicate_size = ClientGUIPredicates.PanelPredicateSystemSize( self )
            self._file_system_predicate_width = ClientGUIPredicates.PanelPredicateSystemWidth( self )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._filter_inbox_and_archive_predicates, CC.FLAGS_VCENTER )
            vbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_age, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_duration, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_height, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_mime, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_num_pixels, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_num_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_num_words, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_ratio, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_similar_to, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_size, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( self._file_system_predicate_width, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetBoolean( 'filter_inbox_and_archive_predicates', self._filter_inbox_and_archive_predicates.GetValue() )
            
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
            
        
    
    class _TagSummariesPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            #
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_top' )
            
            self._thumbnail_top = ClientGUIScrolledPanelsEdit.TagSummaryGeneratorButton( self, tag_summary_generator )
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'thumbnail_bottom_right' )
            
            self._thumbnail_bottom_right = ClientGUIScrolledPanelsEdit.TagSummaryGeneratorButton( self, tag_summary_generator )
            
            tag_summary_generator = self._new_options.GetTagSummaryGenerator( 'media_viewer_top' )
            
            self._media_viewer_top = ClientGUIScrolledPanelsEdit.TagSummaryGeneratorButton( self, tag_summary_generator )
            
            # file export favourites
            # file dnd
            
            #
            
            rows = []
            
            rows.append( ( 'On thumbnail top:', self._thumbnail_top ) )
            rows.append( ( 'On thumbnail bottom-right:', self._thumbnail_bottom_right ) )
            rows.append( ( 'On media viewer top:', self._media_viewer_top ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetTagSummaryGenerator( 'thumbnail_top', self._thumbnail_top.GetValue() )
            self._new_options.SetTagSummaryGenerator( 'thumbnail_bottom_right', self._thumbnail_bottom_right.GetValue() )
            self._new_options.SetTagSummaryGenerator( 'media_viewer_top', self._media_viewer_top.GetValue() )
            
        
    
    class _FilesAndTrashPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._export_location = wx.DirPickerCtrl( self, style = wx.DIRP_USE_TEXTCTRL )
            
            self._delete_to_recycle_bin = wx.CheckBox( self, label = '' )
            
            self._remove_filtered_files = wx.CheckBox( self, label = '' )
            self._remove_trashed_files = wx.CheckBox( self, label = '' )
            
            self._trash_max_age = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no age limit', min = 0, max = 8640 )
            self._trash_max_size = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no size limit', min = 0, max = 20480 )
            
            mime_panel = ClientGUICommon.StaticBox( self, '\'open externally\' launch paths' )
            
            self._mime_launch_listctrl = ClientGUIListCtrl.BetterListCtrl( mime_panel, 'mime_launch', 15, 30, [ ( 'mime', 20 ), ( 'launch path', -1 ) ], self._ConvertMimeToListCtrlTuples, activation_callback = self._EditMimeLaunch )
            
            #
            
            if HC.options[ 'export_path' ] is not None:
                
                abs_path = HydrusPaths.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
                
                if abs_path is not None:
                    
                    self._export_location.SetPath( abs_path )
                    
                
            
            self._delete_to_recycle_bin.SetValue( HC.options[ 'delete_to_recycle_bin' ] )
            self._remove_filtered_files.SetValue( HC.options[ 'remove_filtered_files' ] )
            self._remove_trashed_files.SetValue( HC.options[ 'remove_trashed_files' ] )
            self._trash_max_age.SetValue( HC.options[ 'trash_max_age' ] )
            self._trash_max_size.SetValue( HC.options[ 'trash_max_size' ] )
            
            self._new_options = HG.client_controller.new_options
            
            for mime in HC.SEARCHABLE_MIMES:
                
                launch_path = self._new_options.GetMimeLaunch( mime )
                
                self._mime_launch_listctrl.AddDatas( [ ( mime, launch_path ) ] )
                
            
            self._mime_launch_listctrl.Sort( 0 )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            rows.append( ( 'Default export directory: ', self._export_location ) )
            rows.append( ( 'When deleting files or folders, send them to the OS\'s recycle bin: ', self._delete_to_recycle_bin ) )
            rows.append( ( 'Remove files from view when they are filtered: ', self._remove_filtered_files ) )
            rows.append( ( 'Remove files from view when they are sent to the trash: ', self._remove_trashed_files ) )
            rows.append( ( 'Number of hours a file can be in the trash before being deleted: ', self._trash_max_age ) )
            rows.append( ( 'Maximum size of trash (MB): ', self._trash_max_size ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            mime_panel.Add( self._mime_launch_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            text = 'If you set the default export directory blank, the client will use \'hydrus_export\' under the current user\'s home directory.'
            
            vbox.Add( ClientGUICommon.BetterStaticText( self, text ), CC.FLAGS_CENTER )
            vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.Add( mime_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
        
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
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
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
            
            HC.options[ 'export_path' ] = HydrusPaths.ConvertAbsPathToPortablePath( HydrusData.ToUnicode( self._export_location.GetPath() ) )
            
            HC.options[ 'delete_to_recycle_bin' ] = self._delete_to_recycle_bin.GetValue()
            HC.options[ 'remove_filtered_files' ] = self._remove_filtered_files.GetValue()
            HC.options[ 'remove_trashed_files' ] = self._remove_trashed_files.GetValue()
            HC.options[ 'trash_max_age' ] = self._trash_max_age.GetValue()
            HC.options[ 'trash_max_size' ] = self._trash_max_size.GetValue()
            
            for ( mime, launch_path ) in self._mime_launch_listctrl.GetData():
                
                self._new_options.SetMimeLaunch( mime, launch_path )
                
            
        
    
    class _GUIPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._main_gui_title = wx.TextCtrl( self )
            
            self._default_gui_session = wx.Choice( self )
            
            self._last_session_save_period_minutes = wx.SpinCtrl( self, min = 1, max = 1440 )
            
            self._default_new_page_goes = ClientGUICommon.BetterChoice( self )
            
            for value in [ CC.NEW_PAGE_GOES_FAR_LEFT, CC.NEW_PAGE_GOES_LEFT_OF_CURRENT, CC.NEW_PAGE_GOES_RIGHT_OF_CURRENT, CC.NEW_PAGE_GOES_FAR_RIGHT ]:
                
                self._default_new_page_goes.Append( CC.new_page_goes_string_lookup[ value ], value )
                
            
            self._confirm_client_exit = wx.CheckBox( self )
            self._confirm_trash = wx.CheckBox( self )
            self._confirm_archive = wx.CheckBox( self )
            
            self._max_page_name_chars = wx.SpinCtrl( self, min = 1, max = 256 )
            
            self._page_file_count_display = ClientGUICommon.BetterChoice( self )
            
            for display_type in ( CC.PAGE_FILE_COUNT_DISPLAY_ALL, CC.PAGE_FILE_COUNT_DISPLAY_ONLY_IMPORTERS, CC.PAGE_FILE_COUNT_DISPLAY_NONE ):
                
                self._page_file_count_display.Append( CC.page_file_count_display_string_lookup[ display_type ], display_type )
                
            
            self._total_pages_warning = wx.SpinCtrl( self, min = 5, max = 200 )
            
            self._reverse_page_shift_drag_behaviour = wx.CheckBox( self )
            self._reverse_page_shift_drag_behaviour.SetToolTip( 'By default, holding down shift when you drop off a page tab means the client will not \'chase\' the page tab. This makes this behaviour default, with shift-drop meaning to chase.' )
            
            self._always_embed_autocompletes = wx.CheckBox( self )
            
            self._hide_preview = wx.CheckBox( self )
            
            self._thumbnail_fill = wx.CheckBox( self )
            
            self._thumbnail_visibility_scroll_percent = wx.SpinCtrl( self, min = 1, max = 99 )
            self._thumbnail_visibility_scroll_percent.SetToolTip( 'Lower numbers will cause fewer scrolls, higher numbers more.' )
            
            self._discord_dnd_fix = wx.CheckBox( self )
            self._discord_dnd_fix.SetToolTip( 'This makes small file drag-and-drops a little laggier in exchange for discord support.' )
            
            self._always_show_hover_windows = wx.CheckBox( self )
            self._always_show_hover_windows.SetToolTip( 'If your window manager doesn\'t like showing the hover windows on mouse-over (typically on some Linux flavours), please try this out and give the dev feedback on this forced size and position accuracy!' )
            
            self._hide_message_manager_on_gui_iconise = wx.CheckBox( self )
            self._hide_message_manager_on_gui_iconise.SetToolTip( 'If your message manager does not automatically minimise with your main gui, try this. It can lead to unusual show and positioning behaviour on window managers that do not support it, however.' )
            
            self._hide_message_manager_on_gui_deactive = wx.CheckBox( self )
            self._hide_message_manager_on_gui_deactive.SetToolTip( 'If your message manager stays up after you minimise the program to the system tray using a custom window manager, try this out! It hides the popup messages as soon as the main gui loses focus.' )
            
            frame_locations_panel = ClientGUICommon.StaticBox( self, 'frame locations' )
            
            self._frame_locations = ClientGUIListCtrl.SaneListCtrl( frame_locations_panel, 200, [ ( 'name', -1 ), ( 'remember size', 90 ), ( 'remember position', 90 ), ( 'last size', 90 ), ( 'last position', 90 ), ( 'default gravity', 90 ), ( 'default position', 90 ), ( 'maximised', 90 ), ( 'fullscreen', 90 ) ], activation_callback = self.EditFrameLocations )
            
            self._frame_locations_edit_button = wx.Button( frame_locations_panel, label = 'edit' )
            self._frame_locations_edit_button.Bind( wx.EVT_BUTTON, self.EventEditFrameLocation )
            
            #
            
            self._new_options = HG.client_controller.new_options
            
            self._main_gui_title.SetValue( self._new_options.GetString( 'main_gui_title' ) )
            
            gui_session_names = HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
            
            if 'last session' not in gui_session_names:
                
                gui_session_names.insert( 0, 'last session' )
                
            
            self._default_gui_session.Append( 'just a blank page', None )
            
            for name in gui_session_names:
                
                self._default_gui_session.Append( name, name )
                
            
            try:
                
                self._default_gui_session.SetStringSelection( HC.options[ 'default_gui_session' ] )
                
            except:
                
                self._default_gui_session.SetSelection( 0 )
                
            
            self._last_session_save_period_minutes.SetValue( self._new_options.GetInteger( 'last_session_save_period_minutes' ) )
            
            self._default_new_page_goes.SelectClientData( self._new_options.GetInteger( 'default_new_page_goes' ) )
            
            self._confirm_client_exit.SetValue( HC.options[ 'confirm_client_exit' ] )
            
            self._confirm_trash.SetValue( HC.options[ 'confirm_trash' ] )
            
            self._confirm_archive.SetValue( HC.options[ 'confirm_archive' ] )
            
            self._max_page_name_chars.SetValue( self._new_options.GetInteger( 'max_page_name_chars' ) )
            
            self._page_file_count_display.SelectClientData( self._new_options.GetInteger( 'page_file_count_display' ) )
            
            self._total_pages_warning.SetValue( self._new_options.GetInteger( 'total_pages_warning' ) )
            
            self._reverse_page_shift_drag_behaviour.SetValue( self._new_options.GetBoolean( 'reverse_page_shift_drag_behaviour' ) )
            
            self._always_embed_autocompletes.SetValue( HC.options[ 'always_embed_autocompletes' ] )
            
            self._hide_preview.SetValue( HC.options[ 'hide_preview' ] )
            
            self._thumbnail_fill.SetValue( self._new_options.GetBoolean( 'thumbnail_fill' ) )
            
            self._thumbnail_visibility_scroll_percent.SetValue( self._new_options.GetInteger( 'thumbnail_visibility_scroll_percent' ) )
            
            self._discord_dnd_fix.SetValue( self._new_options.GetBoolean( 'discord_dnd_fix' ) )
            
            self._always_show_hover_windows.SetValue( self._new_options.GetBoolean( 'always_show_hover_windows' ) )
            
            self._hide_message_manager_on_gui_iconise.SetValue( self._new_options.GetBoolean( 'hide_message_manager_on_gui_iconise' ) )
            self._hide_message_manager_on_gui_deactive.SetValue( self._new_options.GetBoolean( 'hide_message_manager_on_gui_deactive' ) )
            
            for ( name, info ) in self._new_options.GetFrameLocations():
                
                listctrl_list = [ name ] + list( info )
                
                pretty_listctrl_list = self._GetPrettyFrameLocationInfo( listctrl_list )
                
                self._frame_locations.Append( pretty_listctrl_list, listctrl_list )
                
            
            #self._frame_locations.SortListItems( col = 0 )
            
            #
            
            rows = []
            
            rows.append( ( 'Main gui title: ', self._main_gui_title ) )
            rows.append( ( 'Default session on startup: ', self._default_gui_session ) )
            rows.append( ( 'If \'last session\' above, autosave it how often (minutes)?', self._last_session_save_period_minutes ) )
            rows.append( ( 'By default, new page tabs: ', self._default_new_page_goes ) )
            rows.append( ( 'Confirm client exit: ', self._confirm_client_exit ) )
            rows.append( ( 'Confirm sending files to trash: ', self._confirm_trash ) )
            rows.append( ( 'Confirm sending more than one file to archive or inbox: ', self._confirm_archive ) )
            rows.append( ( 'Max characters to display in a page name: ', self._max_page_name_chars ) )
            rows.append( ( 'Show page file count after its name: ', self._page_file_count_display ) )
            rows.append( ( 'Warn at this many total pages: ', self._total_pages_warning ) )
            rows.append( ( 'Reverse page tab shift-drag behaviour: ', self._reverse_page_shift_drag_behaviour ) )
            rows.append( ( 'Always embed autocomplete dropdown results window: ', self._always_embed_autocompletes ) )
            rows.append( ( 'Hide the preview window: ', self._hide_preview ) )
            rows.append( ( 'Zoom thumbnails so they \'fill\' their space (experimental): ', self._thumbnail_fill ) )
            rows.append( ( 'Do not scroll down on key navigation if thumbnail at least this % visible: ', self._thumbnail_visibility_scroll_percent ) )
            rows.append( ( 'BUGFIX: Discord file drag-and-drop fix (works for <=10, <50MB file DnDs): ', self._discord_dnd_fix ) )
            rows.append( ( 'BUGFIX: Always show media viewer hover windows: ', self._always_show_hover_windows ) )
            rows.append( ( 'BUGFIX: Hide the popup message manager when the main gui is minimised: ', self._hide_message_manager_on_gui_iconise ) )
            rows.append( ( 'BUGFIX: Hide the popup message manager when the main gui loses focus: ', self._hide_message_manager_on_gui_deactive ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            text = 'Here you can override the current and default values for many frame and dialog sizing and positioning variables.'
            text += os.linesep
            text += 'This is an advanced control. If you aren\'t confident of what you are doing here, come back later!'
            
            frame_locations_panel.Add( wx.StaticText( frame_locations_panel, label = text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            frame_locations_panel.Add( self._frame_locations, CC.FLAGS_EXPAND_BOTH_WAYS )
            frame_locations_panel.Add( self._frame_locations_edit_button, CC.FLAGS_LONE_BUTTON )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( frame_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
        
        def _GetPrettyFrameLocationInfo( self, listctrl_list ):
            
            pretty_listctrl_list = []
            
            for item in listctrl_list:
                
                pretty_listctrl_list.append( str( item ) )
                
            
            return pretty_listctrl_list
            
        
        def EditFrameLocations( self ):
            
            for i in self._frame_locations.GetAllSelected():
                
                listctrl_list = self._frame_locations.GetClientData( i )
                
                title = 'set frame location information'
                
                with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsEdit.EditFrameLocationPanel( dlg, listctrl_list )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        new_listctrl_list = panel.GetValue()
                        pretty_new_listctrl_list = self._GetPrettyFrameLocationInfo( new_listctrl_list )
                        
                        self._frame_locations.UpdateRow( i, pretty_new_listctrl_list, new_listctrl_list )
                        
                    
                
            
        
        def EventEditFrameLocation( self, event ):
            
            self.EditFrameLocations()
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'default_gui_session' ] = self._default_gui_session.GetStringSelection()
            HC.options[ 'confirm_client_exit' ] = self._confirm_client_exit.GetValue()
            HC.options[ 'confirm_trash' ] = self._confirm_trash.GetValue()
            HC.options[ 'confirm_archive' ] = self._confirm_archive.GetValue()
            HC.options[ 'always_embed_autocompletes' ] = self._always_embed_autocompletes.GetValue()
            
            HC.options[ 'hide_preview' ] = self._hide_preview.GetValue()
            
            title = self._main_gui_title.GetValue()
            
            self._new_options.SetString( 'main_gui_title', title )
            
            self._new_options.SetInteger( 'last_session_save_period_minutes', self._last_session_save_period_minutes.GetValue() )
            
            self._new_options.SetInteger( 'default_new_page_goes', self._default_new_page_goes.GetChoice() )
            
            self._new_options.SetInteger( 'max_page_name_chars', self._max_page_name_chars.GetValue() )
            
            self._new_options.SetInteger( 'page_file_count_display', self._page_file_count_display.GetChoice() )
            
            self._new_options.SetInteger( 'total_pages_warning', self._total_pages_warning.GetValue() )
            
            self._new_options.SetBoolean( 'reverse_page_shift_drag_behaviour', self._reverse_page_shift_drag_behaviour.GetValue() )
            
            HG.client_controller.pub( 'main_gui_title', title )
            
            self._new_options.SetBoolean( 'thumbnail_fill', self._thumbnail_fill.GetValue() )
            
            self._new_options.SetInteger( 'thumbnail_visibility_scroll_percent', self._thumbnail_visibility_scroll_percent.GetValue() )
            
            self._new_options.SetBoolean( 'discord_dnd_fix', self._discord_dnd_fix.GetValue() )
            self._new_options.SetBoolean( 'always_show_hover_windows', self._always_show_hover_windows.GetValue() )
            self._new_options.SetBoolean( 'hide_message_manager_on_gui_iconise', self._hide_message_manager_on_gui_iconise.GetValue() )
            self._new_options.SetBoolean( 'hide_message_manager_on_gui_deactive', self._hide_message_manager_on_gui_deactive.GetValue() )
            
            for listctrl_list in self._frame_locations.GetClientData():
                
                ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
                
                self._new_options.SetFrameLocation( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
                
            
        
    
    class _MediaPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = HG.client_controller.new_options
            
            self._animation_start_position = wx.SpinCtrl( self, min = 0, max = 100 )
            
            self._disable_cv_for_gifs = wx.CheckBox( self )
            self._disable_cv_for_gifs.SetToolTip( 'OpenCV is good at rendering gifs, but if you have problems with it and your graphics card, check this and the less reliable and slower PIL will be used instead. EDIT: OpenCV is much better these days--this is mostly not needed.' )
            
            self._load_images_with_pil = wx.CheckBox( self )
            self._load_images_with_pil.SetToolTip( 'OpenCV is much faster than PIL, but it is sometimes less reliable. Switch this on if you experience crashes or other unusual problems while importing or viewing certain images. EDIT: OpenCV is much better these days--this is mostly not needed.' )
            
            self._use_system_ffmpeg = wx.CheckBox( self )
            self._use_system_ffmpeg.SetToolTip( 'Check this to always default to the system ffmpeg in your path, rather than using the static ffmpeg in hydrus\'s bin directory. (requires restart)' )
            
            self._anchor_and_hide_canvas_drags = wx.CheckBox( self )
            
            self._media_zooms = wx.TextCtrl( self )
            self._media_zooms.Bind( wx.EVT_TEXT, self.EventZoomsChanged )
            
            self._media_viewer_panel = ClientGUICommon.StaticBox( self, 'media viewer mime handling' )
            
            self._media_viewer_options = ClientGUIListCtrl.SaneListCtrlForSingleObject( self._media_viewer_panel, 300, [ ( 'mime', 150 ), ( 'media show action', 140 ), ( 'preview show action', 140 ), ( 'zoom info', -1 ) ], activation_callback = self.EditMediaViewerOptions )
            
            self._media_viewer_edit_button = wx.Button( self._media_viewer_panel, label = 'edit' )
            self._media_viewer_edit_button.Bind( wx.EVT_BUTTON, self.EventEditMediaViewerOptions )
            
            #
            
            self._animation_start_position.SetValue( int( HC.options[ 'animation_start_position' ] * 100.0 ) )
            self._disable_cv_for_gifs.SetValue( self._new_options.GetBoolean( 'disable_cv_for_gifs' ) )
            self._load_images_with_pil.SetValue( self._new_options.GetBoolean( 'load_images_with_pil' ) )
            self._use_system_ffmpeg.SetValue( self._new_options.GetBoolean( 'use_system_ffmpeg' ) )
            self._anchor_and_hide_canvas_drags.SetValue( self._new_options.GetBoolean( 'anchor_and_hide_canvas_drags' ) )
            
            media_zooms = self._new_options.GetMediaZooms()
            
            self._media_zooms.SetValue( ','.join( ( str( media_zoom ) for media_zoom in media_zooms ) ) )
            
            mimes_in_correct_order = ( HC.IMAGE_JPEG, HC.IMAGE_PNG, HC.IMAGE_APNG, HC.IMAGE_GIF, HC.APPLICATION_FLASH, HC.APPLICATION_PDF, HC.APPLICATION_ZIP, HC.APPLICATION_RAR, HC.APPLICATION_7Z, HC.APPLICATION_HYDRUS_UPDATE_CONTENT, HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS, HC.VIDEO_AVI, HC.VIDEO_FLV, HC.VIDEO_MOV, HC.VIDEO_MP4, HC.VIDEO_MKV, HC.VIDEO_MPEG, HC.VIDEO_WEBM, HC.VIDEO_WMV, HC.AUDIO_MP3, HC.AUDIO_OGG, HC.AUDIO_FLAC, HC.AUDIO_WMA )
            
            for mime in mimes_in_correct_order:
                
                items = self._new_options.GetMediaViewOptions( mime )
                
                data = [ mime ] + list( items )
                
                ( display_tuple, sort_tuple, data ) = self._GetListCtrlData( data )
                
                self._media_viewer_options.Append( display_tuple, sort_tuple, data )
                
            
            #self._media_viewer_options.SortListItems( col = 0 )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            rows.append( ( 'Start animations this % in: ', self._animation_start_position ) )
            rows.append( ( 'Prefer system FFMPEG: ', self._use_system_ffmpeg ) )
            rows.append( ( 'Media zooms: ', self._media_zooms ) )
            rows.append( ( 'WINDOWS ONLY: Hide and anchor mouse cursor on slow canvas drags: ', self._anchor_and_hide_canvas_drags ) )
            rows.append( ( 'BUGFIX: Load images with PIL: ', self._load_images_with_pil ) )
            rows.append( ( 'BUGFIX: Disable OpenCV for gifs: ', self._disable_cv_for_gifs ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._media_viewer_panel.Add( self._media_viewer_options, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._media_viewer_panel.Add( self._media_viewer_edit_button, CC.FLAGS_LONE_BUTTON )
            
            vbox.Add( self._media_viewer_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
        
        def _GetListCtrlData( self, data ):
            
            ( mime, media_show_action, preview_show_action, zoom_info ) = data
            
            # can't store a list in the listctrl obj space, as it is unhashable
            data = ( mime, media_show_action, preview_show_action, tuple( zoom_info ) )
            
            pretty_mime = HC.mime_string_lookup[ mime ]
            pretty_media_show_action = CC.media_viewer_action_string_lookup[ media_show_action ]
            pretty_preview_show_action = CC.media_viewer_action_string_lookup[ preview_show_action ]
            
            no_show = media_show_action in CC.no_support and preview_show_action in CC.no_support
            
            if no_show:
                
                pretty_zoom_info = ''
                
            else:
                
                pretty_zoom_info = str( zoom_info )
                
            
            display_tuple = ( pretty_mime, pretty_media_show_action, pretty_preview_show_action, pretty_zoom_info )
            sort_tuple = ( pretty_mime, pretty_media_show_action, pretty_preview_show_action, pretty_zoom_info )
            
            return ( display_tuple, sort_tuple, data )
            
        
        def EditMediaViewerOptions( self ):
            
            for i in self._media_viewer_options.GetAllSelected():
                
                data = self._media_viewer_options.GetObject( i )
                
                title = 'set media view options information'
                
                with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsEdit.EditMediaViewOptionsPanel( dlg, data )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        new_data = panel.GetValue()
                        
                        ( display_tuple, sort_tuple, new_data ) = self._GetListCtrlData( new_data )
                        
                        self._media_viewer_options.UpdateRow( i, display_tuple, sort_tuple, new_data )
                        
                    
                
            
        
        def EventEditMediaViewerOptions( self, event ):
            
            self.EditMediaViewerOptions()
            
        
        def EventZoomsChanged( self, event ):
            
            try:
                
                media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.GetValue().split( ',' ) ]
                
                self._media_zooms.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
                
            except ValueError:
                
                self._media_zooms.SetBackgroundColour( wx.Colour( 255, 127, 127 ) )
                
            
            self._media_zooms.Refresh()
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'animation_start_position' ] = float( self._animation_start_position.GetValue() ) / 100.0
            
            self._new_options.SetBoolean( 'disable_cv_for_gifs', self._disable_cv_for_gifs.GetValue() )
            self._new_options.SetBoolean( 'load_images_with_pil', self._load_images_with_pil.GetValue() )
            self._new_options.SetBoolean( 'use_system_ffmpeg', self._use_system_ffmpeg.GetValue() )
            self._new_options.SetBoolean( 'anchor_and_hide_canvas_drags', self._anchor_and_hide_canvas_drags.GetValue() )
            
            try:
                
                media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.GetValue().split( ',' ) ]
                
                media_zooms = [ media_zoom for media_zoom in media_zooms if media_zoom > 0.0 ]
                
                if len( media_zooms ) > 0:
                    
                    self._new_options.SetMediaZooms( media_zooms )
                    
                
            except ValueError:
                
                HydrusData.ShowText( 'Could not parse those zooms, so they were not saved!' )
                
            
            for data in self._media_viewer_options.GetObjects():
                
                data = list( data )
                
                mime = data[0]
                
                value = data[1:]
                
                self._new_options.SetMediaViewOptions( mime, value )
                
            
        
    
    class _RegexPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            regex_favourites = HC.options[ 'regex_favourites' ]
            
            self._regex_panel = ClientGUIScrolledPanelsEdit.EditRegexFavourites( self, regex_favourites )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._regex_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            regex_favourites = self._regex_panel.GetValue()
            
            HC.options[ 'regex_favourites' ] = regex_favourites
            
        
    
    class _SortCollectPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._default_sort = ClientGUICommon.ChoiceSort( self )
            
            self._fallback_sort = ClientGUICommon.ChoiceSort( self )
            
            self._default_collect = ClientGUICommon.CheckboxCollect( self )
            
            self._sort_by = wx.ListBox( self )
            self._sort_by.Bind( wx.EVT_LEFT_DCLICK, self.EventRemoveSortBy )
            
            self._new_sort_by = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
            self._new_sort_by.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownSortBy )
            
            #
            
            self._new_options = HG.client_controller.new_options
            
            try:
                
                self._default_sort.SetSort( self._new_options.GetDefaultSort() )
                
            except:
                
                media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_FILESIZE ), CC.SORT_ASC )
                
                self._default_sort.SetSort( media_sort )
                
            
            try:
                
                self._fallback_sort.SetSort( self._new_options.GetFallbackSort() )
                
            except:
                
                media_sort = ClientMedia.MediaSort( ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ), CC.SORT_ASC )
                
                self._fallback_sort.SetSort( media_sort )
                
            
            for ( sort_by_type, sort_by ) in HC.options[ 'sort_by' ]:
                
                self._sort_by.Append( '-'.join( sort_by ), sort_by )
                
            
            #
            
            rows = []
            
            rows.append( ( 'Default sort: ', self._default_sort ) )
            rows.append( ( 'Secondary sort (when primary gives two equal values): ', self._fallback_sort ) )
            rows.append( ( 'Default collect: ', self._default_collect ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            sort_by_text = 'You can manage new namespace sorting schemes here.'
            sort_by_text += os.linesep
            sort_by_text += 'The client will sort media by comparing their namespaces, moving from left to right until an inequality is found.'
            sort_by_text += os.linesep
            sort_by_text += 'Any changes will be shown in the sort-by dropdowns of any new pages you open.'
            
            vbox.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.Add( ClientGUICommon.BetterStaticText( self, sort_by_text ), CC.FLAGS_VCENTER )
            vbox.Add( self._sort_by, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.Add( self._new_sort_by, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def EventKeyDownSortBy( self, event ):
            
            ( modifier, key ) = ClientData.ConvertKeyEventToSimpleTuple( event )
            
            if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                sort_by_string = self._new_sort_by.GetValue()
                
                if sort_by_string != '':
                    
                    try: sort_by = sort_by_string.split( '-' )
                    except:
                        
                        wx.MessageBox( 'Could not parse that sort by string!' )
                        
                        return
                        
                    
                    self._sort_by.Append( sort_by_string, sort_by )
                    
                    self._new_sort_by.SetValue( '' )
                    
                
            else:
                
                event.Skip()
                
            
        
        def EventRemoveSortBy( self, event ):
            
            selection = self._sort_by.GetSelection()
            
            if selection != wx.NOT_FOUND: self._sort_by.Delete( selection )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetDefaultSort( self._default_sort.GetSort() )
            self._new_options.SetFallbackSort( self._fallback_sort.GetSort() )
            HC.options[ 'default_collect' ] = self._default_collect.GetChoice()
            
            sort_by_choices = []
            
            for sort_by in [ self._sort_by.GetClientData( i ) for i in range( self._sort_by.GetCount() ) ]: sort_by_choices.append( ( 'namespaces', sort_by ) )
            
            HC.options[ 'sort_by' ] = sort_by_choices
            
        
    
    class _SoundPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._play_dumper_noises = wx.CheckBox( self, label = 'play success/fail noises when dumping' )
            
            #
            
            self._play_dumper_noises.SetValue( HC.options[ 'play_dumper_noises' ] )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._play_dumper_noises, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'play_dumper_noises' ] = self._play_dumper_noises.GetValue()
            
        
    
    class _SpeedAndMemoryPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            disk_panel = ClientGUICommon.StaticBox( self, 'disk cache' )
            
            disk_cache_help_button = ClientGUICommon.BetterBitmapButton( disk_panel, CC.GlobalBMPs.help, self._ShowDiskCacheHelp )
            disk_cache_help_button.SetToolTip( 'Show help regarding the disk cache.' )
            
            help_hbox = ClientGUICommon.WrapInText( disk_cache_help_button, disk_panel, 'help for this panel -->', wx.Colour( 0, 0, 255 ) )
            
            self._disk_cache_init_period = ClientGUICommon.NoneableSpinCtrl( disk_panel, 'run disk cache on boot for this long', unit = 's', none_phrase = 'do not run', min = 1, max = 120 )
            self._disk_cache_init_period.SetToolTip( 'When the client boots, it can speed up operation by reading the front of the database into memory. This sets the max number of seconds it can spend doing that.' )
            
            self._disk_cache_maintenance_mb = ClientGUICommon.NoneableSpinCtrl( disk_panel, 'disk cache maintenance', unit = 'MB', none_phrase = 'do not keep db cached', min = 32, max = 65536 )
            self._disk_cache_maintenance_mb.SetToolTip( 'The client can regularly check the front of its database is cached in memory. This represents how many megabytes it will ensure are cached.' )
            
            #
            
            media_panel = ClientGUICommon.StaticBox( self, 'thumbnail size and media cache' )
            
            self._thumbnail_width = wx.SpinCtrl( media_panel, min = 20, max = 200 )
            self._thumbnail_width.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._thumbnail_height = wx.SpinCtrl( media_panel, min = 20, max = 200 )
            self._thumbnail_height.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._thumbnail_cache_size = wx.SpinCtrl( media_panel, min = 5, max = 3000 )
            self._thumbnail_cache_size.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._estimated_number_thumbnails = wx.StaticText( media_panel, label = '' )
            
            self._fullscreen_cache_size = wx.SpinCtrl( media_panel, min = 25, max = 8192 )
            self._fullscreen_cache_size.Bind( wx.EVT_SPINCTRL, self.EventFullscreensUpdate )
            
            self._estimated_number_fullscreens = wx.StaticText( media_panel, label = '' )
            
            #
            
            buffer_panel = ClientGUICommon.StaticBox( self, 'video buffer' )
            
            self._video_buffer_size_mb = wx.SpinCtrl( buffer_panel, min = 48, max = 16 * 1024 )
            self._video_buffer_size_mb.Bind( wx.EVT_SPINCTRL, self.EventVideoBufferUpdate )
            
            self._estimated_number_video_frames = wx.StaticText( buffer_panel, label = '' )
            
            #
            
            ac_panel = ClientGUICommon.StaticBox( self, 'tag autocomplete' )
            
            self._num_autocomplete_chars = wx.SpinCtrl( ac_panel, min = 1, max = 100 )
            self._num_autocomplete_chars.SetToolTip( 'how many characters you enter before the gui fetches autocomplete results from the db. (otherwise, it will only fetch exact matches)' + os.linesep + 'increase this if you find autocomplete results are slow' )
            
            self._fetch_ac_results_automatically = wx.CheckBox( ac_panel )
            self._fetch_ac_results_automatically.Bind( wx.EVT_CHECKBOX, self.EventFetchAuto )
            
            self._autocomplete_long_wait = wx.SpinCtrl( ac_panel, min = 0, max = 10000 )
            self._autocomplete_long_wait.SetToolTip( 'how long the gui will typically wait, after you enter a character, before it queries the db with what you have entered so far' )
            
            self._autocomplete_short_wait_chars = wx.SpinCtrl( ac_panel, min = 1, max = 100 )
            self._autocomplete_short_wait_chars.SetToolTip( 'how many characters you enter before the gui starts waiting the short time before querying the db' )
            
            self._autocomplete_short_wait = wx.SpinCtrl( ac_panel, min = 0, max = 10000 )
            self._autocomplete_short_wait.SetToolTip( 'how long the gui will typically wait, after you enter a lot of characters, before it queries the db with what you have entered so far' )
            
            #
            
            misc_panel = ClientGUICommon.StaticBox( self, 'misc' )
            
            self._forced_search_limit = ClientGUICommon.NoneableSpinCtrl( misc_panel, '', min = 1, max = 100000 )
            
            #
            
            self._disk_cache_init_period.SetValue( self._new_options.GetNoneableInteger( 'disk_cache_init_period' ) )
            self._disk_cache_maintenance_mb.SetValue( self._new_options.GetNoneableInteger( 'disk_cache_maintenance_mb' ) )
            
            ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
            
            self._thumbnail_width.SetValue( thumbnail_width )
            
            self._thumbnail_height.SetValue( thumbnail_height )
            
            self._thumbnail_cache_size.SetValue( int( HC.options[ 'thumbnail_cache_size' ] / 1048576 ) )
            
            self._fullscreen_cache_size.SetValue( int( HC.options[ 'fullscreen_cache_size' ] / 1048576 ) )
            
            self._video_buffer_size_mb.SetValue( self._new_options.GetInteger( 'video_buffer_size_mb' ) )
            
            self._num_autocomplete_chars.SetValue( HC.options[ 'num_autocomplete_chars' ] )
            
            self._fetch_ac_results_automatically.SetValue( HC.options[ 'fetch_ac_results_automatically' ] )
            
            ( char_limit, long_wait, short_wait ) = HC.options[ 'ac_timings' ]
            
            self._autocomplete_long_wait.SetValue( long_wait )
            
            self._autocomplete_short_wait_chars.SetValue( char_limit )
            
            self._autocomplete_short_wait.SetValue( short_wait )
            
            self._forced_search_limit.SetValue( self._new_options.GetNoneableInteger( 'forced_search_limit' ) )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            disk_panel.Add( help_hbox, CC.FLAGS_BUTTON_SIZER )
            disk_panel.Add( self._disk_cache_init_period, CC.FLAGS_EXPAND_PERPENDICULAR )
            disk_panel.Add( self._disk_cache_maintenance_mb, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.Add( disk_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            thumbnails_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            thumbnails_sizer.Add( self._thumbnail_cache_size, CC.FLAGS_VCENTER )
            thumbnails_sizer.Add( self._estimated_number_thumbnails, CC.FLAGS_VCENTER )
            
            fullscreens_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            fullscreens_sizer.Add( self._fullscreen_cache_size, CC.FLAGS_VCENTER )
            fullscreens_sizer.Add( self._estimated_number_fullscreens, CC.FLAGS_VCENTER )
            
            video_buffer_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            video_buffer_sizer.Add( self._video_buffer_size_mb, CC.FLAGS_VCENTER )
            video_buffer_sizer.Add( self._estimated_number_video_frames, CC.FLAGS_VCENTER )
            
            rows = []
            
            rows.append( ( 'Thumbnail width: ', self._thumbnail_width ) )
            rows.append( ( 'Thumbnail height: ', self._thumbnail_height ) )
            rows.append( ( 'MB memory reserved for thumbnail cache: ', thumbnails_sizer ) )
            rows.append( ( 'MB memory reserved for media viewer cache: ', fullscreens_sizer ) )
            
            gridbox = ClientGUICommon.WrapInGrid( media_panel, rows )
            
            media_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.Add( media_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'Hydrus video rendering is CPU intensive.'
            text += os.linesep
            text += 'If you have a lot of memory, you can set a generous potential video buffer to compensate.'
            text += os.linesep
            text += 'If the video buffer can hold an entire video, it only needs to be rendered once and will loop smoothly.'
            
            buffer_panel.Add( wx.StaticText( buffer_panel, label = text ), CC.FLAGS_VCENTER )
            
            rows = []
            
            rows.append( ( 'MB memory for video buffer: ', video_buffer_sizer ) )
            
            gridbox = ClientGUICommon.WrapInGrid( buffer_panel, rows )
            
            buffer_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.Add( buffer_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'If you disable automatic autocomplete results fetching, use Ctrl+Space to fetch results manually.'
            
            ac_panel.Add( wx.StaticText( ac_panel, label = text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Automatically fetch autocomplete results after a short delay: ', self._fetch_ac_results_automatically ) )
            rows.append( ( 'Autocomplete long wait character threshold: ', self._num_autocomplete_chars ) )
            rows.append( ( 'Autocomplete long wait (ms): ', self._autocomplete_long_wait ) )
            rows.append( ( 'Autocomplete short wait character threshold: ', self._autocomplete_short_wait_chars ) )
            rows.append( ( 'Autocomplete short wait (ms): ', self._autocomplete_short_wait ) )
            
            gridbox = ClientGUICommon.WrapInGrid( ac_panel, rows )
            
            ac_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.Add( ac_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Forced system:limit for all searches: ', self._forced_search_limit ) )
            
            gridbox = ClientGUICommon.WrapInGrid( misc_panel, rows )
            
            misc_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.Add( misc_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            self.SetSizer( vbox )
            
            #
            
            self.EventFetchAuto( None )
            self.EventFullscreensUpdate( None )
            self.EventThumbnailsUpdate( None )
            self.EventVideoBufferUpdate( None )
            
            wx.CallAfter( self.Layout ) # draws the static texts correctly
            
        
        def _ShowDiskCacheHelp( self ):
            
            message = 'The hydrus database runs best on a drive with fast random access latency. Important and heavy read and write operations can function up to 100 times faster when started raw from an SSD rather than an HDD.'
            message += os.linesep * 2
            message += 'To get around this, the client populates a pre-boot and ongoing disk cache. By contiguously frontloading the database into memory, the most important functions do not need to wait on your disk for most of their work.'
            message += os.linesep * 2
            message += 'If you tend to leave your client on in the background and have a slow drive but a lot of ram, you might like to pump these numbers up. 15s boot cache and 2048MB ongoing can really make a difference on, for instance, a slow laptop drive.'
            message += os.linesep * 2
            message += 'If you run the database from an SSD, you can reduce or entirely eliminate these values, as the benefit is not so stark. 2s and 256MB is fine.'
            message += os.linesep * 2
            message += 'Unless you are testing, do not go crazy with this stuff. You can set 8192MB if you like, but there are diminishing returns.'
            
            wx.MessageBox( message )
            
        
        def EventFetchAuto( self, event ):
            
            if self._fetch_ac_results_automatically.GetValue() == True:
                
                self._autocomplete_long_wait.Enable()
                self._autocomplete_short_wait_chars.Enable()
                self._autocomplete_short_wait.Enable()
                
            else:
                
                self._autocomplete_long_wait.Disable()
                self._autocomplete_short_wait_chars.Disable()
                self._autocomplete_short_wait.Disable()
                
            
        
        def EventFullscreensUpdate( self, event ):
            
            ( width, height ) = ClientGUITopLevelWindows.GetDisplaySize( self )
            
            estimated_bytes_per_fullscreen = 3 * width * height
            
            self._estimated_number_fullscreens.SetLabelText( '(about ' + HydrusData.ConvertIntToPrettyString( ( self._fullscreen_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_fullscreen ) + '-' + HydrusData.ConvertIntToPrettyString( ( self._fullscreen_cache_size.GetValue() * 1048576 ) / ( estimated_bytes_per_fullscreen / 4 ) ) + ' images)' )
            
        
        def EventThumbnailsUpdate( self, event ):
            
            estimated_bytes_per_thumb = 3 * self._thumbnail_height.GetValue() * self._thumbnail_width.GetValue()
            
            self._estimated_number_thumbnails.SetLabelText( '(about ' + HydrusData.ConvertIntToPrettyString( ( self._thumbnail_cache_size.GetValue() * 1048576 ) / estimated_bytes_per_thumb ) + ' thumbnails)' )
            
        
        def EventVideoBufferUpdate( self, event ):
            
            estimated_720p_frames = int( ( self._video_buffer_size_mb.GetValue() * 1024 * 1024 ) / ( 1280 * 720 * 3 ) )
            
            self._estimated_number_video_frames.SetLabelText( '(about ' + HydrusData.ConvertIntToPrettyString( estimated_720p_frames ) + ' frames of 720p video)' )
            
        
        def UpdateOptions( self ):
            
            self._new_options.SetNoneableInteger( 'disk_cache_init_period', self._disk_cache_init_period.GetValue() )
            self._new_options.SetNoneableInteger( 'disk_cache_maintenance_mb', self._disk_cache_maintenance_mb.GetValue() )
            
            new_thumbnail_dimensions = [ self._thumbnail_width.GetValue(), self._thumbnail_height.GetValue() ]
            
            HC.options[ 'thumbnail_dimensions' ] = new_thumbnail_dimensions
            
            HC.options[ 'thumbnail_cache_size' ] = self._thumbnail_cache_size.GetValue() * 1048576
            HC.options[ 'fullscreen_cache_size' ] = self._fullscreen_cache_size.GetValue() * 1048576
            
            self._new_options.SetInteger( 'video_buffer_size_mb', self._video_buffer_size_mb.GetValue() )
            
            self._new_options.SetNoneableInteger( 'forced_search_limit', self._forced_search_limit.GetValue() )
            
            HC.options[ 'num_autocomplete_chars' ] = self._num_autocomplete_chars.GetValue()
            
            HC.options[ 'fetch_ac_results_automatically' ] = self._fetch_ac_results_automatically.GetValue()
            
            long_wait = self._autocomplete_long_wait.GetValue()
            
            char_limit = self._autocomplete_short_wait_chars.GetValue()
            
            short_wait = self._autocomplete_short_wait.GetValue()
            
            HC.options[ 'ac_timings' ] = ( char_limit, long_wait, short_wait )
            
        
    
    class _TagsPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            general_panel = ClientGUICommon.StaticBox( self, 'general tag options' )
            
            self._default_tag_sort = wx.Choice( general_panel )
            
            self._default_tag_sort.Append( 'lexicographic (a-z)', CC.SORT_BY_LEXICOGRAPHIC_ASC )
            self._default_tag_sort.Append( 'lexicographic (z-a)', CC.SORT_BY_LEXICOGRAPHIC_DESC )
            self._default_tag_sort.Append( 'lexicographic (a-z) (grouped by namespace)', CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC )
            self._default_tag_sort.Append( 'lexicographic (z-a) (grouped by namespace)', CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC )
            self._default_tag_sort.Append( 'incidence (desc)', CC.SORT_BY_INCIDENCE_DESC )
            self._default_tag_sort.Append( 'incidence (asc)', CC.SORT_BY_INCIDENCE_ASC )
            self._default_tag_sort.Append( 'incidence (desc) (grouped by namespace)', CC.SORT_BY_INCIDENCE_NAMESPACE_DESC )
            self._default_tag_sort.Append( 'incidence (asc) (grouped by namespace)', CC.SORT_BY_INCIDENCE_NAMESPACE_ASC )
            
            self._default_tag_repository = ClientGUICommon.BetterChoice( general_panel )
            
            self._default_tag_service_search_page = ClientGUICommon.BetterChoice( general_panel )
            
            self._show_all_tags_in_autocomplete = wx.CheckBox( general_panel )
            
            self._ac_select_first_with_count = wx.CheckBox( general_panel )
            
            self._apply_all_parents_to_all_services = wx.CheckBox( general_panel )
            self._apply_all_siblings_to_all_services = wx.CheckBox( general_panel )
            
            #
            
            render_panel = ClientGUICommon.StaticBox( self, 'tag rendering' )
            
            render_st = wx.StaticText( render_panel, label = 'Namespaced tags are stored and directly edited in hydrus as "namespace:subtag", but most presentation windows can display them differently.' )
            render_st.Wrap( 400 )
            
            self._show_namespaces = wx.CheckBox( render_panel )
            self._namespace_connector = wx.TextCtrl( render_panel )
            
            #
            
            suggested_tags_panel = ClientGUICommon.StaticBox( self, 'suggested tags' )
            
            self._suggested_tags_width = wx.SpinCtrl( suggested_tags_panel, min = 20, max = 65535 )
            
            self._suggested_tags_layout = ClientGUICommon.BetterChoice( suggested_tags_panel )
            
            self._suggested_tags_layout.Append( 'notebook', 'notebook' )
            self._suggested_tags_layout.Append( 'side-by-side', 'columns' )
            
            suggest_tags_panel_notebook = wx.Notebook( suggested_tags_panel )
            
            #
            
            suggested_tags_favourites_panel = wx.Panel( suggest_tags_panel_notebook )
            
            suggested_tags_favourites_panel.SetMinSize( ( 400, -1 ) )
            
            self._suggested_favourites_services = ClientGUICommon.BetterChoice( suggested_tags_favourites_panel )
            
            self._suggested_favourites_services.Append( CC.LOCAL_TAG_SERVICE_KEY, CC.LOCAL_TAG_SERVICE_KEY )
            
            tag_services = HG.client_controller.services_manager.GetServices( ( HC.TAG_REPOSITORY, ) )
            
            for tag_service in tag_services:
                
                self._suggested_favourites_services.Append( tag_service.GetName(), tag_service.GetServiceKey() )
                
            
            self._suggested_favourites = ClientGUIListBoxes.ListBoxTagsStringsAddRemove( suggested_tags_favourites_panel )
            
            self._current_suggested_favourites_service = None
            
            self._suggested_favourites_dict = {}
            
            expand_parents = False
            
            self._suggested_favourites_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( suggested_tags_favourites_panel, self._suggested_favourites.AddTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, CC.LOCAL_TAG_SERVICE_KEY )
            
            #
            
            suggested_tags_related_panel = wx.Panel( suggest_tags_panel_notebook )
            
            self._show_related_tags = wx.CheckBox( suggested_tags_related_panel )
            
            self._related_tags_search_1_duration_ms = wx.SpinCtrl( suggested_tags_related_panel, min = 50, max = 60000 )
            self._related_tags_search_2_duration_ms = wx.SpinCtrl( suggested_tags_related_panel, min = 50, max = 60000 )
            self._related_tags_search_3_duration_ms = wx.SpinCtrl( suggested_tags_related_panel, min = 50, max = 60000 )
            
            #
            
            suggested_tags_file_lookup_script_panel = wx.Panel( suggest_tags_panel_notebook )
            
            self._show_file_lookup_script_tags = wx.CheckBox( suggested_tags_file_lookup_script_panel )
            
            self._favourite_file_lookup_script = ClientGUICommon.BetterChoice( suggested_tags_file_lookup_script_panel )
            
            script_names = list( HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP ) )
            
            script_names.sort()
            
            for name in script_names:
                
                self._favourite_file_lookup_script.Append( name, name )
                
            
            #
            
            suggested_tags_recent_panel = wx.Panel( suggest_tags_panel_notebook )
            
            self._num_recent_tags = ClientGUICommon.NoneableSpinCtrl( suggested_tags_recent_panel, 'number of recent tags to show', min = 1, none_phrase = 'do not show' )
            
            #
            
            if HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_ASC: self._default_tag_sort.Select( 0 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_DESC: self._default_tag_sort.Select( 1 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC: self._default_tag_sort.Select( 2 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC: self._default_tag_sort.Select( 3 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_DESC: self._default_tag_sort.Select( 4 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_ASC: self._default_tag_sort.Select( 5 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_NAMESPACE_DESC: self._default_tag_sort.Select( 6 )
            elif HC.options[ 'default_tag_sort' ] == CC.SORT_BY_INCIDENCE_NAMESPACE_ASC: self._default_tag_sort.Select( 7 )
            
            self._default_tag_service_search_page.Append( 'all known tags', CC.COMBINED_TAG_SERVICE_KEY )
            
            services = HG.client_controller.services_manager.GetServices( HC.TAG_SERVICES )
            
            for service in services:
                
                self._default_tag_repository.Append( service.GetName(), service.GetServiceKey() )
                
                self._default_tag_service_search_page.Append( service.GetName(), service.GetServiceKey() )
                
            
            default_tag_repository_key = HC.options[ 'default_tag_repository' ]
            
            self._default_tag_repository.SelectClientData( default_tag_repository_key )
            
            self._default_tag_service_search_page.SelectClientData( new_options.GetKey( 'default_tag_service_search_page' ) )
            
            self._show_all_tags_in_autocomplete.SetValue( HC.options[ 'show_all_tags_in_autocomplete' ] )
            self._ac_select_first_with_count.SetValue( self._new_options.GetBoolean( 'ac_select_first_with_count' ) )
            
            self._apply_all_parents_to_all_services.SetValue( self._new_options.GetBoolean( 'apply_all_parents_to_all_services' ) )
            self._apply_all_siblings_to_all_services.SetValue( self._new_options.GetBoolean( 'apply_all_siblings_to_all_services' ) )
            
            #
            
            self._show_namespaces.SetValue( new_options.GetBoolean( 'show_namespaces' ) )
            self._namespace_connector.SetValue( new_options.GetString( 'namespace_connector' ) )
            
            #
            
            self._suggested_tags_width.SetValue( self._new_options.GetInteger( 'suggested_tags_width' ) )
            
            self._suggested_tags_layout.SelectClientData( self._new_options.GetNoneableString( 'suggested_tags_layout' ) )
            
            self._suggested_favourites_services.SelectClientData( CC.LOCAL_TAG_SERVICE_KEY )
            
            self._show_related_tags.SetValue( self._new_options.GetBoolean( 'show_related_tags' ) )
            
            self._related_tags_search_1_duration_ms.SetValue( self._new_options.GetInteger( 'related_tags_search_1_duration_ms' ) )
            self._related_tags_search_2_duration_ms.SetValue( self._new_options.GetInteger( 'related_tags_search_2_duration_ms' ) )
            self._related_tags_search_3_duration_ms.SetValue( self._new_options.GetInteger( 'related_tags_search_3_duration_ms' ) )
            
            self._show_file_lookup_script_tags.SetValue( self._new_options.GetBoolean( 'show_file_lookup_script_tags' ) )
            
            self._favourite_file_lookup_script.SelectClientData( self._new_options.GetNoneableString( 'favourite_file_lookup_script' ) )
            
            self._num_recent_tags.SetValue( self._new_options.GetNoneableInteger( 'num_recent_tags' ) )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            rows.append( ( 'Default tag service in manage tag dialogs: ', self._default_tag_repository ) )
            rows.append( ( 'Default tag service in search pages: ', self._default_tag_service_search_page ) )
            rows.append( ( 'Default tag sort: ', self._default_tag_sort ) )
            rows.append( ( 'By default, search non-local tags in write-autocomplete: ', self._show_all_tags_in_autocomplete ) )
            rows.append( ( 'By default, select the first tag result with actual count in write-autocomplete: ', self._ac_select_first_with_count ) )
            rows.append( ( 'Suggest all parents for all services: ', self._apply_all_parents_to_all_services ) )
            rows.append( ( 'Apply all siblings to all services (local siblings have precedence): ', self._apply_all_siblings_to_all_services ) )
            
            gridbox = ClientGUICommon.WrapInGrid( general_panel, rows )
            
            general_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.Add( general_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Show namespaces: ', self._show_namespaces ) )
            rows.append( ( 'If shown, namespace connecting string: ', self._namespace_connector ) )
            
            gridbox = ClientGUICommon.WrapInGrid( render_panel, rows )
            
            render_panel.Add( render_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            render_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.Add( render_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            panel_vbox = wx.BoxSizer( wx.VERTICAL )
            
            panel_vbox.Add( self._suggested_favourites_services, CC.FLAGS_EXPAND_PERPENDICULAR )
            panel_vbox.Add( self._suggested_favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
            panel_vbox.Add( self._suggested_favourites_input, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_favourites_panel.SetSizer( panel_vbox )
            
            #
            
            panel_vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            rows.append( ( 'Show related tags on single-file manage tags windows: ', self._show_related_tags ) )
            rows.append( ( 'Initial search duration (ms): ', self._related_tags_search_1_duration_ms ) )
            rows.append( ( 'Medium search duration (ms): ', self._related_tags_search_2_duration_ms ) )
            rows.append( ( 'Thorough search duration (ms): ', self._related_tags_search_3_duration_ms ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_related_panel, rows )
            
            panel_vbox.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_related_panel.SetSizer( panel_vbox )
            
            #
            
            panel_vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            rows.append( ( 'Show file lookup scripts on single-file manage tags windows: ', self._show_file_lookup_script_tags ) )
            rows.append( ( 'Favourite file lookup script: ', self._favourite_file_lookup_script ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_file_lookup_script_panel, rows )
            
            panel_vbox.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_file_lookup_script_panel.SetSizer( panel_vbox )
            
            #
            
            panel_vbox = wx.BoxSizer( wx.VERTICAL )
            
            panel_vbox.Add( self._num_recent_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_recent_panel.SetSizer( panel_vbox )
            
            #
            
            suggest_tags_panel_notebook.AddPage( suggested_tags_favourites_panel, 'favourites' )
            suggest_tags_panel_notebook.AddPage( suggested_tags_related_panel, 'related' )
            suggest_tags_panel_notebook.AddPage( suggested_tags_file_lookup_script_panel, 'file lookup scripts' )
            suggest_tags_panel_notebook.AddPage( suggested_tags_recent_panel, 'recent' )
            
            #
            
            rows = []
            
            rows.append( ( 'Width of suggested tags columns: ', self._suggested_tags_width ) )
            rows.append( ( 'Column layout: ', self._suggested_tags_layout ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_panel, rows )
            
            suggested_tags_panel.Add( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            suggested_tags_panel.Add( suggest_tags_panel_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox.Add( suggested_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            #
            
            self.SetSizer( vbox )
            
            #
            
            self._suggested_favourites_services.Bind( wx.EVT_CHOICE, self.EventSuggestedFavouritesService )
            
            self.EventSuggestedFavouritesService( None )
            
        
        def _SaveCurrentSuggestedFavourites( self ):
            
            if self._current_suggested_favourites_service is not None:
                
                self._suggested_favourites_dict[ self._current_suggested_favourites_service ] = self._suggested_favourites.GetTags()
                
            
        
        def EventSuggestedFavouritesService( self, event ):
            
            self._SaveCurrentSuggestedFavourites()
            
            self._current_suggested_favourites_service = self._suggested_favourites_services.GetChoice()
            
            if self._current_suggested_favourites_service in self._suggested_favourites_dict:
                
                favourites = self._suggested_favourites_dict[ self._current_suggested_favourites_service ]
                
            else:
                
                favourites = self._new_options.GetSuggestedTagsFavourites( self._current_suggested_favourites_service )
                
            
            self._suggested_favourites.SetTags( favourites )
            
            self._suggested_favourites_input.SetTagService( self._current_suggested_favourites_service )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'default_tag_repository' ] = self._default_tag_repository.GetChoice()
            HC.options[ 'default_tag_sort' ] = self._default_tag_sort.GetClientData( self._default_tag_sort.GetSelection() )
            HC.options[ 'show_all_tags_in_autocomplete' ] = self._show_all_tags_in_autocomplete.GetValue()
            
            self._new_options.SetBoolean( 'ac_select_first_with_count', self._ac_select_first_with_count.GetValue() )
            
            self._new_options.SetKey( 'default_tag_service_search_page', self._default_tag_service_search_page.GetChoice() )
            
            self._new_options.SetInteger( 'suggested_tags_width', self._suggested_tags_width.GetValue() )
            self._new_options.SetNoneableString( 'suggested_tags_layout', self._suggested_tags_layout.GetChoice() )
            
            self._new_options.SetBoolean( 'apply_all_parents_to_all_services', self._apply_all_parents_to_all_services.GetValue() )
            self._new_options.SetBoolean( 'apply_all_siblings_to_all_services', self._apply_all_siblings_to_all_services.GetValue() )
            
            self._new_options.SetBoolean( 'show_namespaces', self._show_namespaces.GetValue() )
            self._new_options.SetString( 'namespace_connector', self._namespace_connector.GetValue() )
            
            self._SaveCurrentSuggestedFavourites()
            
            for ( service_key, favourites ) in self._suggested_favourites_dict.items():
                
                self._new_options.SetSuggestedTagsFavourites( service_key, favourites )
                
            
            self._new_options.SetBoolean( 'show_related_tags', self._show_related_tags.GetValue() )
            
            self._new_options.SetInteger( 'related_tags_search_1_duration_ms', self._related_tags_search_1_duration_ms.GetValue() )
            self._new_options.SetInteger( 'related_tags_search_2_duration_ms', self._related_tags_search_2_duration_ms.GetValue() )
            self._new_options.SetInteger( 'related_tags_search_3_duration_ms', self._related_tags_search_3_duration_ms.GetValue() )
            
            self._new_options.SetBoolean( 'show_file_lookup_script_tags', self._show_file_lookup_script_tags.GetValue() )
            self._new_options.SetNoneableString( 'favourite_file_lookup_script', self._favourite_file_lookup_script.GetChoice() )
            
            self._new_options.SetNoneableInteger( 'num_recent_tags', self._num_recent_tags.GetValue() )
            
        
    
    def CommitChanges( self ):
        
        for page in self._listbook.GetActivePages():
            
            page.UpdateOptions()
            
        
        try:
            
            HG.client_controller.WriteSynchronous( 'save_options', HC.options )
            
            HG.client_controller.WriteSynchronous( 'serialisable', self._new_options )
            
        except:
            
            wx.MessageBox( traceback.format_exc() )
            
        

class ManageServerServicesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, service_key ):
        
        self._clientside_admin_service = HG.client_controller.services_manager.GetService( service_key )
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._deletee_service_keys = []
        
        columns = [ ( 'port', 80 ), ( 'name', -1 ), ( 'type', 220 ) ]
        
        self._services_listctrl = ClientGUIListCtrl.SaneListCtrlForSingleObject( self, 120, columns, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'tag repository', 'Create a new tag repository.', self._AddTagRepository ) )
        menu_items.append( ( 'normal', 'file repository', 'Create a new file repository.', self._AddFileRepository ) )
        
        self._add_button = ClientGUICommon.MenuButton( self, 'add', menu_items )
        
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        #
        
        response = self._clientside_admin_service.Request( HC.GET, 'services' )
        
        serverside_services = response[ 'services' ]
        
        for serverside_service in serverside_services:
            
            ( display_tuple, sort_tuple ) = self._ConvertServiceToTuples( serverside_service )
            
            self._services_listctrl.Append( display_tuple, sort_tuple, serverside_service )
            
        
        #self._services_listctrl.SortListItems( 0 )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._add_button, CC.FLAGS_VCENTER )
        hbox.Add( self._edit_button, CC.FLAGS_VCENTER )
        hbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._services_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( hbox, CC.FLAGS_SMALL_INDENT )
        
        self.SetSizer( vbox )
        
    
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
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit serverside service' ) as dlg_edit:
            
            panel = ClientGUIScrolledPanelsEdit.EditServersideService( dlg_edit, service )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_service = panel.GetValue()
                
                self._services_listctrl.SetNonDupeName( new_service )
                
                self._SetNonDupePort( new_service )
                
                ( display_tuple, sort_tuple ) = self._ConvertServiceToTuples( new_service )
                
                self._services_listctrl.Append( display_tuple, sort_tuple, new_service )
                
            
        
    
    def _AddFileRepository( self ):
        
        self._Add( HC.FILE_REPOSITORY )
        
    
    def _AddTagRepository( self ):
        
        self._Add( HC.TAG_REPOSITORY )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                for service in self._services_listctrl.GetObjects( only_selected = True ):
                    
                    self._deletee_service_keys.append( service.GetServiceKey() )
                    
                
                self._services_listctrl.RemoveAllSelected()
                
            
        
    
    def _Edit( self ):
        
        for index in self._services_listctrl.GetAllSelected():
            
            service = self._services_listctrl.GetObject( index )
            
            original_name = service.GetName()
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit serverside service' ) as dlg_edit:
                
                panel = ClientGUIScrolledPanelsEdit.EditServersideService( dlg_edit, service )
                
                dlg_edit.SetPanel( panel )
                
                result = dlg_edit.ShowModal()
                
                if result == wx.ID_OK:
                    
                    edited_service = panel.GetValue()
                    
                    if edited_service.GetName() != original_name:
                        
                        self._services_listctrl.SetNonDupeName( edited_service )
                        
                    
                    self._SetNonDupePort( edited_service )
                    
                    ( display_tuple, sort_tuple ) = self._ConvertServiceToTuples( edited_service )
                    
                    self._services_listctrl.UpdateRow( index, display_tuple, sort_tuple, edited_service )
                    
                elif result == wx.ID_CANCEL:
                    
                    break
                    
                
            
        
    
    def _GetNextPort( self ):
        
        existing_ports = [ service.GetPort() for service in self._services_listctrl.GetObjects() ]
        
        largest_port = max( existing_ports )
        
        next_port = largest_port
        
        while next_port in existing_ports:
            
            next_port = max( 1, ( next_port + 1 ) % 65536 )
            
        
        return next_port
        
    
    def _SetNonDupePort( self, new_service ):
        
        existing_ports = [ service.GetPort() for service in self._services_listctrl.GetObjects() if service.GetServiceKey() != new_service.GetServiceKey() ]
        
        new_port = new_service.GetPort()
        
        if new_port in existing_ports:
            
            next_port = self._GetNextPort()
            
            service.SetPort( next_port )
            
        
    
    def CommitChanges( self ):
        
        services = self._services_listctrl.GetObjects()
        
        response = self._clientside_admin_service.Request( HC.POST, 'services', { 'services' : services } )
        
        service_keys_to_access_keys = dict( response[ 'service_keys_to_access_keys' ] )
        
        admin_service_key = self._clientside_admin_service.GetServiceKey()
        
        with HG.dirty_object_lock:
            
            HG.client_controller.WriteSynchronous( 'update_server_services', admin_service_key, services, service_keys_to_access_keys, self._deletee_service_keys )
            
            HG.client_controller.RefreshServices()
            
        
    
class ManageShortcutsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        help_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.help, self._ShowHelp )
        help_button.SetToolTip( 'Show help regarding editing shortcuts.' )
        
        reserved_panel = ClientGUICommon.StaticBox( self, 'reserved' )
        
        self._reserved_shortcuts = ClientGUIListCtrl.SaneListCtrlForSingleObject( reserved_panel, 180, [ ( 'name', -1 ), ( 'size', 100 ) ], activation_callback = self._EditReserved )
        
        self._reserved_shortcuts.SetMinSize( ( 320, 200 ) )
        
        self._edit_reserved_button = ClientGUICommon.BetterButton( reserved_panel, 'edit', self._EditReserved )
        
        #
        
        custom_panel = ClientGUICommon.StaticBox( self, 'custom' )
        
        self._custom_shortcuts = ClientGUIListCtrl.SaneListCtrlForSingleObject( custom_panel, 120, [ ( 'name', -1 ), ( 'size', 100 ) ], delete_key_callback = self._Delete, activation_callback = self._EditCustom )
        
        self._add_button = ClientGUICommon.BetterButton( custom_panel, 'add', self._Add )
        self._edit_custom_button = ClientGUICommon.BetterButton( custom_panel, 'edit', self._EditCustom )
        self._delete_button = ClientGUICommon.BetterButton( custom_panel, 'delete', self._Delete )
        
        #
        
        all_shortcuts = HG.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS )
        
        reserved_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() in CC.SHORTCUTS_RESERVED_NAMES ]
        custom_shortcuts = [ shortcuts for shortcuts in all_shortcuts if shortcuts.GetName() not in CC.SHORTCUTS_RESERVED_NAMES ]
        
        for shortcuts in reserved_shortcuts:
            
            ( display_tuple, sort_tuple ) = self._GetTuples( shortcuts )
            
            self._reserved_shortcuts.Append( display_tuple, sort_tuple, shortcuts )
            
        
        self._original_custom_names = set()
        
        for shortcuts in custom_shortcuts:
            
            ( display_tuple, sort_tuple ) = self._GetTuples( shortcuts )
            
            self._custom_shortcuts.Append( display_tuple, sort_tuple, shortcuts )
            
            self._original_custom_names.add( shortcuts.GetName() )
            
        
        #
        
        reserved_panel.Add( self._reserved_shortcuts, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        reserved_panel.Add( self._edit_reserved_button, CC.FLAGS_LONE_BUTTON )
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.Add( self._add_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._edit_custom_button, CC.FLAGS_VCENTER )
        button_hbox.Add( self._delete_button, CC.FLAGS_VCENTER )
        
        custom_panel.Add( self._custom_shortcuts, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        custom_panel.Add( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( help_button, CC.FLAGS_LONE_BUTTON )
        vbox.Add( reserved_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( custom_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _Add( self ):
        
        shortcuts = ClientData.Shortcuts( 'new shortcuts' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit shortcuts' ) as dlg:
            
            panel = self._EditPanel( dlg, shortcuts )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_shortcuts = panel.GetValue()
                
                ( display_tuple, sort_tuple ) = self._GetTuples( new_shortcuts )
                
                self._custom_shortcuts.Append( display_tuple, sort_tuple, new_shortcuts )
                
            
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._custom_shortcuts.RemoveAllSelected()
                
            
        
    
    def _EditCustom( self ):
        
        all_selected = self._custom_shortcuts.GetAllSelected()
        
        for index in all_selected:
            
            shortcuts = self._custom_shortcuts.GetObject( index )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit shortcuts' ) as dlg:
                
                panel = self._EditPanel( dlg, shortcuts )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_shortcuts = panel.GetValue()
                    
                    ( display_tuple, sort_tuple ) = self._GetTuples( edited_shortcuts )
                    
                    self._custom_shortcuts.UpdateRow( index, display_tuple, sort_tuple, edited_shortcuts )
                    
                else:
                    
                    break
                    
                
            
        
    
    def _EditReserved( self ):
        
        all_selected = self._reserved_shortcuts.GetAllSelected()
        
        for index in all_selected:
            
            shortcuts = self._reserved_shortcuts.GetObject( index )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit shortcuts' ) as dlg:
                
                panel = self._EditPanel( dlg, shortcuts )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_shortcuts = panel.GetValue()
                    
                    ( display_tuple, sort_tuple ) = self._GetTuples( edited_shortcuts )
                    
                    self._reserved_shortcuts.UpdateRow( index, display_tuple, sort_tuple, edited_shortcuts )
                    
                else:
                    
                    break
                    
                
            
        
    
    def _GetTuples( self, shortcuts ):
        
        name = shortcuts.GetName()
        size = len( shortcuts )
        
        display_tuple = ( name, HydrusData.ConvertIntToPrettyString( size ) )
        sort_tuple = ( name, size )
        
        return ( display_tuple, sort_tuple )
        
    
    def _ShowHelp( self ):
        
        message = 'I am in the process of converting the multiple old messy shortcut systems to this single unified engine. Many actions are not yet available here, and mouse support is very limited. I expect to overwrite the reserved shortcut sets back to (new and expanded) defaults at least once more, so don\'t remap everything yet unless you are ok with doing it again.'
        message += os.linesep * 2
        message += '---'
        message += os.linesep * 2
        message += 'In hydrus, shortcuts are split into different sets that are active in different contexts. Depending on where the program focus is, multiple sets can be active at the same time. On a keyboard or mouse event, the active sets will be consulted one after another (typically from the smallest and most precise focus to the largest and broadest parent) until an action match is found.'
        message += os.linesep * 2
        message += 'There are two kinds--\'reserved\' and \'custom\':'
        message += os.linesep * 2
        message += 'Reserved shortcuts are always active in their contexts--the \'main_gui\' one is always consulted when you hit a key on the main gui window, for instance. They have limited actions to choose from, appropriate to their context. If you would prefer to, say, open the manage tags dialog with Ctrl+F3, edit or add that entry in the \'media\' set and that new shortcut will apply anywhere you are focused on some particular media.'
        message += os.linesep * 2
        message += 'Custom shortcuts sets are those you can create and rename at will. They are only ever active in the media viewer window, and only when you set them so from the top hover-window\'s keyboard icon. They are primarily meant for setting tags and ratings with shortcuts, and are intended to be turned on and off as you perform different \'filtering\' jobs--for instance, you might like to set the 1-5 keys to the different values of a five-star rating system, or assign a few simple keystrokes to a number of common tags.'
        message += os.linesep * 2
        message += 'The reserved \'media\' set also supports tag and rating actions, if you would like some of those to always be active.'
        
        wx.MessageBox( message )
        
    
    def CommitChanges( self ):
        
        for shortcuts in self._reserved_shortcuts.GetObjects():
            
            HG.client_controller.Write( 'serialisable', shortcuts )
            
        
        good_names = set()
        
        for shortcuts in self._custom_shortcuts.GetObjects():
            
            good_names.add( shortcuts.GetName() )
            
            HG.client_controller.Write( 'serialisable', shortcuts )
            
        
        deletees = self._original_custom_names.difference( good_names )
        
        for name in deletees:
            
            HG.client_controller.Write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUTS, name )
            
        
        HG.client_controller.pub( 'new_shortcuts' )
        
    
    class _EditPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, shortcuts ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            self._name = wx.TextCtrl( self )
            self._shortcuts = ClientGUIListCtrl.SaneListCtrl( self, 480, [ ( 'shortcut', 150 ), ( 'command', -1 ) ], delete_key_callback = self.RemoveShortcuts, activation_callback = self.EditShortcuts )
            
            self._shortcuts.SetMinSize( ( 360, 480 ) )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._edit = wx.Button( self, label = 'edit' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._remove = wx.Button( self, label = 'remove' )
            self._remove.Bind( wx.EVT_BUTTON, self.EventRemove )
            
            #
            
            name = shortcuts.GetName()
            
            self._name.SetValue( name )
            
            self._this_is_custom = True
            
            if name in CC.SHORTCUTS_RESERVED_NAMES:
                
                self._this_is_custom = False
                
                self._name.Disable()
                
            
            for ( shortcut, command ) in shortcuts:
                
                sort_tuple = ( shortcut, command )
                
                pretty_tuple = self._ConvertSortTupleToPrettyTuple( sort_tuple )
                
                self._shortcuts.Append( pretty_tuple, sort_tuple )
                
            
            #self._shortcuts.SortListItems( 1 )
            
            #
            
            action_buttons = wx.BoxSizer( wx.HORIZONTAL )
            
            action_buttons.Add( self._add, CC.FLAGS_VCENTER )
            action_buttons.Add( self._edit, CC.FLAGS_VCENTER )
            action_buttons.Add( self._remove, CC.FLAGS_VCENTER )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( ClientGUICommon.WrapInText( self._name, self, 'name: ' ), CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.Add( self._shortcuts, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.Add( action_buttons, CC.FLAGS_BUTTON_SIZER )
            
            self.SetSizer( vbox )
            
        
        def _ConvertSortTupleToPrettyTuple( self, ( shortcut, command ) ):
            
            return ( shortcut.ToString(), command.ToString() )
            
        
        def EditShortcuts( self ):
            
            name = self._name.GetValue()
            
            selected_indices = self._shortcuts.GetAllSelected()
            
            for index in selected_indices:
                
                ( shortcut, command ) = self._shortcuts.GetClientData( index )
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'edit shortcut command' ) as dlg:
                    
                    panel = self._EditPanel( dlg, shortcut, command, name )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( shortcut, command ) = panel.GetValue()
                        
                        sort_tuple = ( shortcut, command )
                        
                        pretty_tuple = self._ConvertSortTupleToPrettyTuple( sort_tuple )
                        
                        self._shortcuts.UpdateRow( index, pretty_tuple, sort_tuple )
                        
                    else:
                        
                        break
                        
                    
                
            
        
        def EventAdd( self, event ):
            
            shortcut = ClientData.Shortcut()
            command = ClientData.ApplicationCommand()
            name = self._name.GetValue()
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit shortcut command' ) as dlg:
                
                panel = self._EditPanel( dlg, shortcut, command, name )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( shortcut, command ) = panel.GetValue()
                    
                    sort_tuple = ( shortcut, command )
                    
                    pretty_tuple = self._ConvertSortTupleToPrettyTuple( sort_tuple )
                    
                    self._shortcuts.Append( pretty_tuple, sort_tuple )
                    
                
            
        
        def EventEdit( self, event ):
            
            self.EditShortcuts()
            
        
        def EventRemove( self, event ):
            
            self.RemoveShortcuts()
            
        
        def GetValue( self ):
            
            name = self._name.GetValue()
            
            if self._this_is_custom and name in CC.SHORTCUTS_RESERVED_NAMES:
                
                raise HydrusExceptions.VetoException( 'That name is reserved--please pick another!' )
                
            
            shortcuts = ClientData.Shortcuts( name )
            
            for ( shortcut, command ) in self._shortcuts.GetClientData():
                
                shortcuts.SetCommand( shortcut, command )
                
            
            return shortcuts
            
        
        def RemoveShortcuts( self ):
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._shortcuts.RemoveAllSelected()
                    
                
            
        
        class _EditPanel( ClientGUIScrolledPanels.EditPanel ):
            
            def __init__( self, parent, shortcut, command, shortcuts_name ):
                
                ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
                
                self._final_command = 'simple'
                
                self._current_ratings_like_service = None
                self._current_ratings_numerical_service = None
                
                #
                
                self._shortcut_panel = ClientGUICommon.StaticBox( self, 'shortcut' )
                
                self._shortcut = ClientGUICommon.Shortcut( self._shortcut_panel )
                
                #
                
                self._none_panel = ClientGUICommon.StaticBox( self, 'simple actions' )
                
                if shortcuts_name in CC.SHORTCUTS_RESERVED_NAMES:
                    
                    choices = CC.simple_shortcut_name_to_action_lookup[ shortcuts_name ]
                    
                else:
                    
                    choices = CC.simple_shortcut_name_to_action_lookup[ 'custom' ]
                    
                
                choices = list( choices )
                
                choices.sort()
                
                self._simple_actions = wx.Choice( self._none_panel, choices = choices )
                
                self._set_simple = ClientGUICommon.BetterButton( self._none_panel, 'set command', self._SetSimple )
                
                #
                
                self._content_panel = ClientGUICommon.StaticBox( self, 'content actions' )
                
                self._flip_or_set_action = ClientGUICommon.BetterChoice( self._content_panel )
                
                self._flip_or_set_action.Append( 'set', HC.CONTENT_UPDATE_SET )
                self._flip_or_set_action.Append( 'flip on and off', HC.CONTENT_UPDATE_FLIP )
                
                self._flip_or_set_action.SelectClientData( HC.CONTENT_UPDATE_SET )
                
                self._tag_panel = ClientGUICommon.StaticBox( self._content_panel, 'tag service actions' )
                
                self._tag_service_keys = wx.Choice( self._tag_panel )
                self._tag_value = wx.TextCtrl( self._tag_panel, style = wx.TE_READONLY )
                
                expand_parents = False
                
                self._tag_input = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self._tag_panel, self.SetTags, expand_parents, CC.LOCAL_FILE_SERVICE_KEY, CC.COMBINED_TAG_SERVICE_KEY )
                
                self._set_tag = ClientGUICommon.BetterButton( self._tag_panel, 'set command', self._SetTag )
                
                #
                
                self._ratings_like_panel = ClientGUICommon.StaticBox( self._content_panel, 'like/dislike ratings service actions' )
                
                self._ratings_like_service_keys = wx.Choice( self._ratings_like_panel )
                self._ratings_like_service_keys.Bind( wx.EVT_CHOICE, self.EventRecalcActions )
                self._ratings_like_like = wx.RadioButton( self._ratings_like_panel, style = wx.RB_GROUP, label = 'like' )
                self._ratings_like_dislike = wx.RadioButton( self._ratings_like_panel, label = 'dislike' )
                self._ratings_like_remove = wx.RadioButton( self._ratings_like_panel, label = 'remove rating' )
                
                self._set_ratings_like = ClientGUICommon.BetterButton( self._ratings_like_panel, 'set command', self._SetRatingsLike )
                
                #
                
                self._ratings_numerical_panel = ClientGUICommon.StaticBox( self._content_panel, 'numerical ratings service actions' )
                
                self._ratings_numerical_service_keys = wx.Choice( self._ratings_numerical_panel )
                self._ratings_numerical_service_keys.Bind( wx.EVT_CHOICE, self.EventRecalcActions )
                self._ratings_numerical_slider = wx.Slider( self._ratings_numerical_panel, style = wx.SL_AUTOTICKS | wx.SL_LABELS )
                self._ratings_numerical_remove = wx.CheckBox( self._ratings_numerical_panel, label = 'remove rating' )
                
                self._set_ratings_numerical = ClientGUICommon.BetterButton( self._ratings_numerical_panel, 'set command', self._SetRatingsNumerical )
                
                #
                
                services = HG.client_controller.services_manager.GetServices( ( HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) )
                
                for service in services:
                    
                    service_type = service.GetServiceType()
                    
                    if service_type in HC.TAG_SERVICES: choice = self._tag_service_keys
                    elif service_type == HC.LOCAL_RATING_LIKE: choice = self._ratings_like_service_keys
                    elif service_type == HC.LOCAL_RATING_NUMERICAL: choice = self._ratings_numerical_service_keys
                    
                    choice.Append( service.GetName(), service.GetServiceKey() )
                    
                
                self._SetActions()
                
                #
                
                self._shortcut.SetValue( shortcut )
                
                command_type = command.GetCommandType()
                data = command.GetData()
                
                if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
                    
                    action = data
                    
                    self._simple_actions.SetStringSelection( action )
                    
                    self._SetSimple()
                    
                else:
                    
                    ( service_key, content_type, action, value ) = data
                    
                    self._service = HG.client_controller.services_manager.GetService( service_key )
                    
                    service_name = self._service.GetName()
                    service_type = self._service.GetServiceType()
                    
                    self._flip_or_set_action.SelectClientData( action )
                    
                    if service_type in HC.TAG_SERVICES:
                        
                        self._tag_service_keys.SetStringSelection( service_name )
                        
                        self._tag_value.SetValue( value )
                        
                        self._SetTag()
                        
                    elif service_type == HC.LOCAL_RATING_LIKE:
                        
                        self._ratings_like_service_keys.SetStringSelection( service_name )
                        
                        self._SetActions()
                        
                        if value is None:
                            
                            self._ratings_like_remove.SetValue( True )
                            
                        elif value == True:
                            
                            self._ratings_like_like.SetValue( True )
                            
                        elif value == False:
                            
                            self._ratings_like_dislike.SetValue( True )
                            
                        
                        self._SetRatingsLike()
                        
                    elif service_type == HC.LOCAL_RATING_NUMERICAL:
                        
                        self._ratings_numerical_service_keys.SetStringSelection( service_name )
                        
                        self._SetActions()
                        
                        if value is None:
                            
                            self._ratings_numerical_remove.SetValue( True )
                            
                        else:
                            
                            num_stars = self._current_ratings_numerical_service.GetNumStars()
                            
                            slider_value = int( round( value * num_stars ) )
                            
                            self._ratings_numerical_slider.SetValue( slider_value )
                            
                        
                        self._SetRatingsNumerical()
                        
                    
                    if self._final_command is None:
                        
                        self._SetSimple()
                        
                    
                
                #
                
                self._shortcut_panel.Add( self._shortcut, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                none_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                none_hbox.Add( self._simple_actions, CC.FLAGS_EXPAND_DEPTH_ONLY )
                none_hbox.Add( self._set_simple, CC.FLAGS_VCENTER )
                
                self._none_panel.Add( none_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                tag_sub_vbox = wx.BoxSizer( wx.VERTICAL )
                
                tag_sub_vbox.Add( self._tag_value, CC.FLAGS_EXPAND_PERPENDICULAR )
                tag_sub_vbox.Add( self._tag_input, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                tag_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                tag_hbox.Add( self._tag_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
                tag_hbox.Add( tag_sub_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                tag_hbox.Add( self._set_tag, CC.FLAGS_VCENTER )
                
                self._tag_panel.Add( tag_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                ratings_like_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                ratings_like_hbox.Add( self._ratings_like_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
                ratings_like_hbox.Add( self._ratings_like_like, CC.FLAGS_VCENTER )
                ratings_like_hbox.Add( self._ratings_like_dislike, CC.FLAGS_VCENTER )
                ratings_like_hbox.Add( self._ratings_like_remove, CC.FLAGS_VCENTER )
                ratings_like_hbox.Add( self._set_ratings_like, CC.FLAGS_VCENTER )
                
                self._ratings_like_panel.Add( ratings_like_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                ratings_numerical_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                ratings_numerical_hbox.Add( self._ratings_numerical_service_keys, CC.FLAGS_EXPAND_DEPTH_ONLY )
                ratings_numerical_hbox.Add( self._ratings_numerical_slider, CC.FLAGS_VCENTER )
                ratings_numerical_hbox.Add( self._ratings_numerical_remove, CC.FLAGS_VCENTER )
                ratings_numerical_hbox.Add( self._set_ratings_numerical, CC.FLAGS_VCENTER )
                
                self._ratings_numerical_panel.Add( ratings_numerical_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
                self._content_panel.Add( self._flip_or_set_action, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._content_panel.Add( self._tag_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._content_panel.Add( self._ratings_like_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._content_panel.Add( self._ratings_numerical_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                vbox = wx.BoxSizer( wx.VERTICAL )
                
                vbox.Add( self._none_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                vbox.Add( self._content_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                is_custom_or_media = shortcuts_name not in CC.SHORTCUTS_RESERVED_NAMES or shortcuts_name == 'media'
                
                if not is_custom_or_media:
                    
                    self._set_simple.Hide()
                    
                    self._content_panel.Hide()
                    
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.Add( self._shortcut_panel, CC.FLAGS_VCENTER )
                hbox.Add( ClientGUICommon.BetterStaticText( self, u'\u2192' ), CC.FLAGS_VCENTER )
                hbox.Add( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
                
                self.SetSizer( hbox )
                
            
            def _EnableButtons( self ):
                
                for button in [ self._set_simple, self._set_ratings_like, self._set_ratings_numerical, self._set_tag ]:
                    
                    button.Enable()
                    
                
            
            def _GetCommand( self ):
                
                if self._final_command == 'simple':
                    
                    return self._GetSimple()
                    
                elif self._final_command == 'ratings_like':
                    
                    return self._GetRatingsLike()
                    
                if self._final_command == 'ratings_numerical':
                    
                    return self._GetRatingsNumerical()
                    
                if self._final_command == 'tag':
                    
                    return self._GetTag()
                    
                
            
            def _GetSimple( self ):
                
                action = self._simple_actions.GetStringSelection()
                
                if action == '':
                    
                    raise HydrusExceptions.VetoException( 'Please select an action!' )
                    
                else:
                    
                    return ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_SIMPLE, action )
                    
                
            
            def _GetRatingsLike( self ):
                
                selection = self._ratings_like_service_keys.GetSelection()
                
                if selection != wx.NOT_FOUND:
                    
                    service_key = self._ratings_like_service_keys.GetClientData( selection )
                    
                    action = self._flip_or_set_action.GetChoice()
                    
                    if self._ratings_like_like.GetValue():
                        
                        value = 1.0
                        
                    elif self._ratings_like_dislike.GetValue():
                        
                        value = 0.0
                        
                    else:
                        
                        value = None
                        
                    
                    return ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, value ) )
                    
                else:
                    
                    raise HydrusExceptions.VetoException( 'Please select a rating service!' )
                    
                
            
            def _GetRatingsNumerical( self ):
                
                selection = self._ratings_numerical_service_keys.GetSelection()
                
                if selection != wx.NOT_FOUND:
                    
                    service_key = self._ratings_numerical_service_keys.GetClientData( selection )
                    
                    action = self._flip_or_set_action.GetChoice()
                    
                    if self._ratings_numerical_remove.GetValue():
                        
                        value = None
                        
                    else:
                        
                        value = self._ratings_numerical_slider.GetValue()
                        
                        num_stars = self._current_ratings_numerical_service.GetNumStars()
                        allow_zero = self._current_ratings_numerical_service.AllowZero()
                        
                        if allow_zero:
                            
                            value = float( value ) / num_stars
                            
                        else:
                            
                            value = float( value - 1 ) / ( num_stars - 1 )
                            
                        
                    
                    return ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_RATINGS, action, value ) )
                    
                else:
                    
                    raise HydrusExceptions.VetoException( 'Please select a rating service!' )
                    
                
            
            def _GetTag( self ):
                
                selection = self._tag_service_keys.GetSelection()
                
                if selection != wx.NOT_FOUND:
                    
                    service_key = self._tag_service_keys.GetClientData( selection )
                    
                    action = self._flip_or_set_action.GetChoice()
                    
                    value = self._tag_value.GetValue()
                    
                    if value == '':
                        
                        raise HydrusExceptions.VetoException( 'Please enter a tag!' )
                        
                    
                    return ClientData.ApplicationCommand( CC.APPLICATION_COMMAND_TYPE_CONTENT, ( service_key, HC.CONTENT_TYPE_MAPPINGS, action, value ) )
                    
                else:
                    
                    raise HydrusExceptions.VetoException( 'Please select a tag service!' )
                    
                
            
            def _SetActions( self ):
                
                if self._ratings_like_service_keys.GetCount() > 0:
                    
                    selection = self._ratings_like_service_keys.GetSelection()
                    
                    if selection != wx.NOT_FOUND:
                        
                        service_key = self._ratings_like_service_keys.GetClientData( selection )
                        
                        service = HG.client_controller.services_manager.GetService( service_key )
                        
                        self._current_ratings_like_service = service
                        
                    
                
                if self._ratings_numerical_service_keys.GetCount() > 0:
                    
                    selection = self._ratings_numerical_service_keys.GetSelection()
                    
                    if selection != wx.NOT_FOUND:
                        
                        service_key = self._ratings_numerical_service_keys.GetClientData( selection )
                        
                        service = HG.client_controller.services_manager.GetService( service_key )
                        
                        self._current_ratings_numerical_service = service
                        
                        num_stars = service.GetNumStars()
                        
                        allow_zero = service.AllowZero()
                        
                        if allow_zero:
                            
                            min = 0
                            
                        else:
                            
                            min = 1
                            
                        
                        self._ratings_numerical_slider.SetRange( min, num_stars )
                        
                    
                
            
            def _SetSimple( self ):
                
                self._EnableButtons()
                
                self._set_simple.Disable()
                
                self._final_command = 'simple'
                
            
            def _SetRatingsLike( self ):
                
                self._EnableButtons()
                
                self._set_ratings_like.Disable()
                
                self._final_command = 'ratings_like'
                
            
            def _SetRatingsNumerical( self ):
                
                self._EnableButtons()
                
                self._set_ratings_numerical.Disable()
                
                self._final_command = 'ratings_numerical'
                
            
            def _SetTag( self ):
                
                self._EnableButtons()
                
                self._set_tag.Disable()
                
                self._final_command = 'tag'
                
            
            def EventRecalcActions( self, event ):
                
                self._SetActions()
                
                event.Skip()
                
            
            def GetValue( self ):
                
                shortcut = self._shortcut.GetValue()
                
                command = self._GetCommand()
                
                return ( shortcut, command )
                
            
            def SetTags( self, tags ):
                
                if len( tags ) > 0:
                    
                    tag = list( tags )[0]
                    
                    self._tag_value.SetValue( tag )
                    
                
            
        
    
class ManageTagsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, file_service_key, media, immediate_commit = False, canvas_key = None ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._file_service_key = file_service_key
        
        self._immediate_commit = immediate_commit
        self._canvas_key = canvas_key
        
        media = ClientMedia.FlattenMedia( media )
        
        self._current_media = [ m.Duplicate() for m in media ]
        
        self._hashes = set()
        
        for m in self._current_media:
            
            self._hashes.update( m.GetHashes() )
            
        
        self._tag_repositories = ClientGUICommon.ListBook( self )
        self._tag_repositories.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventServiceChanged )
        
        #
        
        services = HG.client_controller.services_manager.GetServices( HC.TAG_SERVICES )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_repositories, self._file_service_key, service.GetServiceKey(), self._current_media, self._immediate_commit, canvas_key = self._canvas_key )
            
            self._tag_repositories.AddPage( name, service_key, page )
            
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        self._tag_repositories.Select( default_tag_repository_key )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Bind( ClientGUIACDropdown.EVT_SELECT_UP, self.EventSelectUp )
        self.Bind( ClientGUIACDropdown.EVT_SELECT_DOWN, self.EventSelectDown )
        
        self.Bind( ClientGUIACDropdown.EVT_SHOW_PREVIOUS, self.EventShowPrevious )
        self.Bind( ClientGUIACDropdown.EVT_SHOW_NEXT, self.EventShowNext )
        
        if self._canvas_key is not None:
            
            HG.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
        self._my_shortcut_handler = ClientGUIShortcuts.ShortcutsHandler( self, [ 'media', 'main_gui' ] )
        
    
    def _GetServiceKeysToContentUpdates( self ):
        
        service_keys_to_content_updates = {}
        
        for page in self._tag_repositories.GetActivePages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        return service_keys_to_content_updates
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        if page is not None:
            
            page.SetTagBoxFocus()
            
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = ( new_media_singleton.Duplicate(), )
            
            for page in self._tag_repositories.GetActivePages():
                
                page.SetMedia( self._current_media )
                
            
        
    
    def CanCancel( self ):
        
        service_keys_to_content_updates = self._GetServiceKeysToContentUpdates()
        
        if len( service_keys_to_content_updates ) > 0:
            
            message = 'Are you sure you want to cancel? You have uncommitted changes that will be lost.'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() != wx.ID_YES:
                    
                    return False
                    
                
            
        
        return True
        
    
    def CommitChanges( self ):
        
        service_keys_to_content_updates = self._GetServiceKeysToContentUpdates()
        
        if len( service_keys_to_content_updates ) > 0:
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
    def EventSelectDown( self, event ):
        
        self._tag_repositories.SelectDown()
        
    
    def EventSelectUp( self, event ):
        
        self._tag_repositories.SelectUp()
        
    
    def EventShowNext( self, event ):
        
        if self._canvas_key is not None:
            
            HG.client_controller.pub( 'canvas_show_next', self._canvas_key )
            
        
    
    def EventShowPrevious( self, event ):
        
        if self._canvas_key is not None:
            
            HG.client_controller.pub( 'canvas_show_previous', self._canvas_key )
            
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        if page is not None:
            
            wx.CallAfter( page.SetTagBoxFocus )
            
        
    
    def ProcessApplicationCommand( self, command ):
        
        command_processed = True
        
        command_type = command.GetCommandType()
        data = command.GetData()
        
        if command_type == CC.APPLICATION_COMMAND_TYPE_SIMPLE:
            
            action = data
            
            if action == 'manage_file_tags':
                
                self._OKParent()
                
            elif action == 'set_search_focus':
                
                self._SetSearchFocus()
                
            else:
                
                command_processed = False
                
            
        else:
            
            command_processed = False
            
        
        return command_processed
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, file_service_key, tag_service_key, media, immediate_commit, canvas_key = None ):
            
            wx.Panel.__init__( self, parent )
            
            self._file_service_key = file_service_key
            self._tag_service_key = tag_service_key
            self._immediate_commit = immediate_commit
            self._canvas_key = canvas_key
            
            self._content_updates = []
            
            self._i_am_local_tag_service = self._tag_service_key == CC.LOCAL_TAG_SERVICE_KEY
            
            if not self._i_am_local_tag_service:
                
                self._service = HG.client_controller.services_manager.GetService( tag_service_key )
                
            
            self._tags_box_sorter = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'tags' )
            
            self._tags_box = ClientGUIListBoxes.ListBoxTagsSelectionTagsDialog( self._tags_box_sorter, self.AddTags, self.RemoveTags )
            
            self._tags_box_sorter.SetTagsBox( self._tags_box )
            
            self._new_options = HG.client_controller.new_options
            
            self._add_parents_checkbox = wx.CheckBox( self._tags_box_sorter, label = 'auto-add entered tags\' parents' )
            self._add_parents_checkbox.SetValue( self._new_options.GetBoolean( 'add_parents_on_manage_tags' ) )
            self._add_parents_checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckAddParents )
            
            self._collapse_siblings_checkbox = wx.CheckBox( self._tags_box_sorter, label = 'auto-replace entered siblings' )
            self._collapse_siblings_checkbox.SetValue( self._new_options.GetBoolean( 'replace_siblings_on_manage_tags' ) )
            self._collapse_siblings_checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckCollapseSiblings )
            
            self._show_deleted_checkbox = wx.CheckBox( self._tags_box_sorter, label = 'show deleted' )
            self._show_deleted_checkbox.Bind( wx.EVT_CHECKBOX, self.EventShowDeleted )
            
            self._tags_box_sorter.Add( self._add_parents_checkbox, CC.FLAGS_LONE_BUTTON )
            self._tags_box_sorter.Add( self._collapse_siblings_checkbox, CC.FLAGS_LONE_BUTTON )
            self._tags_box_sorter.Add( self._show_deleted_checkbox, CC.FLAGS_LONE_BUTTON )
            
            expand_parents = True
            
            self._add_tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterTags, expand_parents, self._file_service_key, self._tag_service_key, null_entry_callable = self.OK )
            
            self._advanced_content_update_button = wx.Button( self, label = 'advanced operation' )
            self._advanced_content_update_button.Bind( wx.EVT_BUTTON, self.EventAdvancedContentUpdate )
            
            self._modify_mappers = wx.Button( self, label = 'modify mappers' )
            self._modify_mappers.Bind( wx.EVT_BUTTON, self.EventModify )
            
            self._copy_tags = wx.Button( self, id = wx.ID_COPY, label = 'copy tags' )
            self._copy_tags.Bind( wx.EVT_BUTTON, self.EventCopyTags )
            
            self._paste_tags = wx.Button( self, id = wx.ID_PASTE, label = 'paste tags' )
            self._paste_tags.Bind( wx.EVT_BUTTON, self.EventPasteTags )
            
            if self._i_am_local_tag_service:
                
                text = 'remove all tags'
                
            else:
                
                text = 'petition all tags'
                
            
            self._remove_tags = wx.Button( self, label = text )
            self._remove_tags.Bind( wx.EVT_BUTTON, self.EventRemoveTags )
            
            self._tags_box.ChangeTagService( self._tag_service_key )
            
            self.SetMedia( media )
            
            self._suggested_tags = ClientGUITagSuggestions.SuggestedTagsPanel( self, self._tag_service_key, self._media, self.AddTags, canvas_key = self._canvas_key )
            
            if self._i_am_local_tag_service:
                
                self._modify_mappers.Hide()
                
            else:
                
                if not self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_OVERRULE ):
                    
                    self._modify_mappers.Hide()
                    
                
            
            if not self._new_options.GetBoolean( 'advanced_mode' ):
                
                self._advanced_content_update_button.Hide()
                
            
            copy_paste_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            copy_paste_hbox.Add( self._copy_tags, CC.FLAGS_VCENTER )
            copy_paste_hbox.Add( self._paste_tags, CC.FLAGS_VCENTER )
            
            advanced_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            advanced_hbox.Add( self._remove_tags, CC.FLAGS_VCENTER )
            advanced_hbox.Add( self._advanced_content_update_button, CC.FLAGS_VCENTER )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.Add( self._tags_box_sorter, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.Add( self._add_tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.Add( copy_paste_hbox, CC.FLAGS_BUTTON_SIZER )
            vbox.Add( advanced_hbox, CC.FLAGS_BUTTON_SIZER )
            vbox.Add( self._modify_mappers, CC.FLAGS_LONE_BUTTON )
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._suggested_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            hbox.Add( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            self.SetSizer( hbox )
            
            if self._immediate_commit:
                
                HG.client_controller.sub( self, 'ProcessContentUpdates', 'content_updates_gui' )
                
            
        
        def _AddTags( self, tags, only_add = False, only_remove = False, forced_reason = None ):
            
            tags = HydrusTags.CleanTags( tags )
            
            if not self._i_am_local_tag_service and self._service.HasPermission( HC.CONTENT_TYPE_MAPPINGS, HC.PERMISSION_ACTION_OVERRULE ):
                
                forced_reason = 'admin'
                
            
            tag_managers = [ m.GetTagsManager() for m in self._media ]
            
            num_files = len( self._media )
            
            # let's figure out what these tags can mean for the media--add, remove, or what?
            
            choices = collections.defaultdict( list )
            
            for tag in tags:
                
                num_current = len( [ 1 for tag_manager in tag_managers if tag in tag_manager.GetCurrent( self._tag_service_key ) ] )
                
                if self._i_am_local_tag_service:
                    
                    if not only_remove:
                        
                        if num_current < num_files:
                            
                            num_non_current = num_files - num_current
                            
                            choices[ HC.CONTENT_UPDATE_ADD ].append( ( tag, num_non_current ) )
                            
                        
                    
                    if not only_add:
                        
                        if num_current > 0:
                            
                            choices[ HC.CONTENT_UPDATE_DELETE ].append( ( tag, num_current ) )
                            
                        
                    
                else:
                    
                    num_pending = len( [ 1 for tag_manager in tag_managers if tag in tag_manager.GetPending( self._tag_service_key ) ] )
                    num_petitioned = len( [ 1 for tag_manager in tag_managers if tag in tag_manager.GetPetitioned( self._tag_service_key ) ] )
                    
                    if not only_remove:
                        
                        if num_current + num_pending < num_files:
                            
                            num_pendable = num_files - ( num_current + num_pending )
                            
                            choices[ HC.CONTENT_UPDATE_PEND ].append( ( tag, num_pendable ) )
                            
                        
                    
                    if not only_add:
                        
                        if num_current > num_petitioned and not only_add:
                            
                            num_petitionable = num_current - num_petitioned
                            
                            choices[ HC.CONTENT_UPDATE_PETITION ].append( ( tag, num_petitionable ) )
                            
                        
                        if num_pending > 0 and not only_add:
                            
                            choices[ HC.CONTENT_UPDATE_RESCIND_PEND ].append( ( tag, num_pending ) )
                            
                        
                    
                    if not only_remove:
                        
                        if num_petitioned > 0:
                            
                            choices[ HC.CONTENT_UPDATE_RESCIND_PETITION ].append( ( tag, num_petitioned ) )
                            
                        
                    
                
            
            if len( choices ) == 0:
                
                return
                
            
            # now we have options, let's ask the user what they want to do
            
            if len( choices ) == 1:
                
                [ ( choice_action, tag_counts ) ] = choices.items()
                
                tags = { tag for ( tag, count ) in tag_counts }
                
            else:
                
                bdc_choices = []
                
                preferred_order = [ HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_DELETE, HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_RESCIND_PEND, HC.CONTENT_UPDATE_PETITION, HC.CONTENT_UPDATE_RESCIND_PETITION ]
                
                choice_text_lookup = {}
                
                choice_text_lookup[ HC.CONTENT_UPDATE_ADD ] = 'add'
                choice_text_lookup[ HC.CONTENT_UPDATE_DELETE ] = 'delete'
                choice_text_lookup[ HC.CONTENT_UPDATE_PEND ] = 'pend'
                choice_text_lookup[ HC.CONTENT_UPDATE_PETITION ] = 'petition'
                choice_text_lookup[ HC.CONTENT_UPDATE_RESCIND_PEND ] = 'rescind pend'
                choice_text_lookup[ HC.CONTENT_UPDATE_RESCIND_PETITION ] = 'rescind petition'
                
                for choice_action in preferred_order:
                    
                    if choice_action not in choices:
                        
                        continue
                        
                    
                    choice_text_prefix = choice_text_lookup[ choice_action ]
                    
                    tag_counts = choices[ choice_action ]
                    
                    tags = { tag for ( tag, count ) in tag_counts }
                    
                    if len( tags ) == 1:
                        
                        [ ( tag, count ) ] = tag_counts
                        
                        text = choice_text_prefix + ' "' + tag + '" for ' + HydrusData.ConvertIntToPrettyString( count ) + ' files'
                        
                    else:
                        
                        text = choice_text_prefix + ' ' + HydrusData.ConvertIntToPrettyString( len( tags ) ) + ' tags'
                        
                    
                    data = ( choice_action, tags )
                    
                    tooltip = os.linesep.join( ( tag + ' - ' + HydrusData.ConvertIntToPrettyString( count ) + ' files' for ( tag, count ) in tag_counts ) )
                    
                    bdc_choices.append( ( text, data, tooltip ) )
                    
                
                intro = 'What would you like to do?'
                
                with ClientGUIDialogs.DialogButtonChoice( self, intro, bdc_choices ) as dlg:
                    
                    result = dlg.ShowModal()
                    
                    if result == wx.ID_OK:
                        
                        ( always_do, ( choice_action, tags ) ) = dlg.GetData()
                        
                    else:
                        
                        return
                        
                    
                
                
            
            if choice_action == HC.CONTENT_UPDATE_PETITION:
                
                if forced_reason is None:
                    
                    # add the easy reason buttons here
                    
                    if len( tags ) == 1:
                        
                        ( tag, ) = tags
                        
                        tag_text = '"' + tag + '"'
                        
                    else:
                        
                        tag_text = 'the ' + HydrusData.ConvertIntToPrettyString( len( tags ) ) + ' tags'
                        
                    
                    message = 'Enter a reason for ' + tag_text + ' to be removed. A janitor will review your petition.'
                    
                    suggestions = []
                    
                    suggestions.append( 'mangled parse/typo' )
                    suggestions.append( 'not applicable' )
                    suggestions.append( 'should be namespaced' )
                    
                    with ClientGUIDialogs.DialogTextEntry( self, message, suggestions = suggestions ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            reason = dlg.GetValue()
                            
                        else:
                            
                            return
                            
                        
                    
                    # if this above sub-dialog occurs, the 'default focus' reverts to the main gui when the manage tags frame closes, wew lad
                    
                    ClientGUICommon.GetTLP( self ).GetParent().SetFocus()
                    self.SetFocus()
                    
                else:
                    
                    reason = forced_reason
                    
                
            
            # we have an action and tags, so let's effect the content updates
            
            content_updates = []
            
            recent_tags = set()
            
            for tag in tags:
                
                if choice_action == HC.CONTENT_UPDATE_ADD: media_to_affect = ( m for m in self._media if tag not in m.GetTagsManager().GetCurrent( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_DELETE: media_to_affect = ( m for m in self._media if tag in m.GetTagsManager().GetCurrent( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_PEND: media_to_affect = ( m for m in self._media if tag not in m.GetTagsManager().GetCurrent( self._tag_service_key ) and tag not in m.GetTagsManager().GetPending( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_PETITION: media_to_affect = ( m for m in self._media if tag in m.GetTagsManager().GetCurrent( self._tag_service_key ) and tag not in m.GetTagsManager().GetPetitioned( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PEND: media_to_affect = ( m for m in self._media if tag in m.GetTagsManager().GetPending( self._tag_service_key ) )
                elif choice_action == HC.CONTENT_UPDATE_RESCIND_PETITION: media_to_affect = ( m for m in self._media if tag in m.GetTagsManager().GetPetitioned( self._tag_service_key ) )
                
                hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in media_to_affect ) ) )
                
                if len( hashes ) > 0:
                    
                    if choice_action == HC.CONTENT_UPDATE_PETITION:
                        
                        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( tag, hashes, reason ) ) )
                        
                    else:
                        
                        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( tag, hashes ) ) )
                        
                    
                    if choice_action in ( HC.CONTENT_UPDATE_ADD, HC.CONTENT_UPDATE_PEND ):
                        
                        recent_tags.add( tag )
                        
                        if self._add_parents_checkbox.GetValue():
                            
                            tag_parents_manager = HG.client_controller.GetManager( 'tag_parents' )
                            
                            parents = tag_parents_manager.GetParents( self._tag_service_key, tag )
                            
                            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( parent, hashes ) ) for parent in parents ) )
                            
                        
                    
                
            
            if len( recent_tags ) > 0 and HG.client_controller.new_options.GetNoneableInteger( 'num_recent_tags' ) is not None:
                
                HG.client_controller.Write( 'push_recent_tags', self._tag_service_key, recent_tags )
                
            
            if self._immediate_commit:
                
                service_keys_to_content_updates = { self._tag_service_key : content_updates }
                
                HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
            else:
                
                for m in self._media:
                    
                    for content_update in content_updates:
                        
                        m.GetMediaResult().ProcessContentUpdate( self._tag_service_key, content_update )
                        
                    
                
                self._content_updates.extend( content_updates )
                
            
            self._tags_box.SetTagsByMedia( self._media, force_reload = True )
            
        
        def AddTags( self, tags, only_add = False ):
            
            if len( tags ) > 0:
                
                self._AddTags( tags, only_add = only_add )
                
            
        
        def EnterTags( self, tags, only_add = False ):
            
            if self._collapse_siblings_checkbox.GetValue():
                
                siblings_manager = HG.client_controller.GetManager( 'tag_siblings' )
                
                tags = siblings_manager.CollapseTags( self._tag_service_key, tags )
                
            
            if len( tags ) > 0:
                
                self._AddTags( tags, only_add = only_add )
                
            
        
        def EventAdvancedContentUpdate( self, event ):
            
            hashes = set()
            
            for m in self._media:
                
                hashes.update( m.GetHashes() )
                
            
            parent = self.GetTopLevelParent().GetParent()
            
            self.OK()
            
            # do this because of the OK() call, which doesn't want to happen in the dialog event loop
            def do_it():
                
                with ClientGUITopLevelWindows.DialogNullipotent( parent, 'advanced content update' ) as dlg:
                    
                    panel = ClientGUIScrolledPanelsReview.AdvancedContentUpdatePanel( dlg, self._tag_service_key, hashes )
                    
                    dlg.SetPanel( panel )
                    
                    dlg.ShowModal()
                    
                
            
            wx.CallAfter( do_it )
            
        
        def EventCheckAddParents( self, event ):
            
            self._new_options.SetBoolean( 'add_parents_on_manage_tags', self._add_parents_checkbox.GetValue() )
            
        
        def EventCheckCollapseSiblings( self, event ):
            
            self._new_options.SetBoolean( 'replace_siblings_on_manage_tags', self._collapse_siblings_checkbox.GetValue() )
            
        
        def EventCopyTags( self, event ):
        
            ( current_tags_to_count, deleted_tags_to_count, pending_tags_to_count, petitioned_tags_to_count ) = ClientData.GetMediasTagCount( self._media, tag_service_key = self._tag_service_key, collapse_siblings = False )
            
            tags = set( current_tags_to_count.keys() ).union( pending_tags_to_count.keys() )
            
            text = os.linesep.join( tags )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
        def EventModify( self, event ):
            
            wx.MessageBox( 'this does not work yet!' )
            
            return
            
            contents = []
            
            tags = self._tags_box.GetSelectedTags()
            
            hashes = set( itertools.chain.from_iterable( ( m.GetHashes() for m in self._media ) ) )
            
            for tag in tags:
                
                contents.extend( [ HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) ) for hash in hashes ] )
                
            
            if len( contents ) > 0:
                
                subject_accounts = 'blah' # fetch subjects from the server using the contents
                
                with ClientGUIDialogs.DialogModifyAccounts( self, self._tag_service_key, subject_accounts ) as dlg: dlg.ShowModal()
                
            
        
        def EventPasteTags( self, event ):
            
            text = HG.client_controller.GetClipboardText()
            
            try:
                
                tags = HydrusText.DeserialiseNewlinedTexts( text )
                
                tags = HydrusTags.CleanTags( tags )
                
                self.EnterTags( tags, only_add = True )
                
            except:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        
        def EventRemoveTags( self, event ):
            
            tag_managers = [ m.GetTagsManager() for m in self._media ]
            
            removable_tags = set()
            
            for tag_manager in tag_managers:
                
                removable_tags.update( tag_manager.GetCurrent( self._tag_service_key ) )
                removable_tags.update( tag_manager.GetPending( self._tag_service_key ) )
                
            
            self._AddTags( removable_tags, only_remove = True )
            
        
        def EventShowDeleted( self, event ):
            
            self._tags_box.SetShow( 'deleted', self._show_deleted_checkbox.GetValue() )
            
        
        def GetContentUpdates( self ): return ( self._tag_service_key, self._content_updates )
        
        def HasChanges( self ):
            
            return len( self._content_updates ) > 0
            
        
        def OK( self ):
            
            wx.QueueEvent( self.GetEventHandler(), ClientGUITopLevelWindows.OKEvent( -1 ) )
            
        
        def ProcessContentUpdates( self, service_keys_to_content_updates ):
            
            for ( service_key, content_updates ) in service_keys_to_content_updates.items():
                
                for content_update in content_updates:
                    
                    for m in self._media:
                        
                        if len( m.GetHashes().intersection( content_update.GetHashes() ) ) > 0:
                            
                            m.GetMediaResult().ProcessContentUpdate( service_key, content_update )
                            
                        
                    
                
            
            self._tags_box.SetTagsByMedia( self._media, force_reload = True )
            
        
        def RemoveTags( self, tags ):
            
            if len( tags ) > 0:
                
                self._AddTags( tags, only_remove = True )
                
            
        
        def SetMedia( self, media ):
            
            if media is None:
                
                media = []
                
            
            self._media = media
            
            self._tags_box.SetTagsByMedia( self._media )
            
        
        def SetTagBoxFocus( self ):
            
            self._add_tag_box.SetFocus()
            
        

class ManageURLsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, media ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._media = media
        
        self._urls_listbox = wx.ListBox( self, style = wx.LB_SORT | wx.LB_SINGLE )
        self._urls_listbox.Bind( wx.EVT_LISTBOX_DCLICK, self.EventListDoubleClick )
        
        ( width, height ) = ClientData.ConvertTextToPixels( self._urls_listbox, ( 120, 10 ) )
        
        self._urls_listbox.SetInitialSize( ( width, height ) )
        
        self._url_input = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
        self._url_input.Bind( wx.EVT_CHAR_HOOK, self.EventInputCharHook )
        
        self._copy_button = ClientGUICommon.BetterButton( self, 'copy all', self._Copy )
        self._paste_button = ClientGUICommon.BetterButton( self, 'paste', self._Paste )
        
        self._urls_to_add = set()
        self._urls_to_remove = set()
        
        #
        
        locations_manager = self._media.GetLocationsManager()
        
        self._original_urls = set( locations_manager.GetURLs() )
        
        for url in self._original_urls:
            
            self._urls_listbox.Append( url, url )
            
        
        self._current_urls = set( self._original_urls )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._copy_button, CC.FLAGS_VCENTER )
        hbox.Add( self._paste_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( self._urls_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.Add( self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
        wx.CallAfter( self._url_input.SetFocus )
        
    
    def _Copy( self ):
        
        urls = list( self._current_urls )
        
        urls.sort()
        
        text = os.linesep.join( urls )
        
        HG.client_controller.pub( 'clipboard', 'text', text )
        
    
    def _EnterURL( self, url, only_add = False ):
        
        if url in self._current_urls:
            
            if only_add:
                
                return
                
            
            for index in range( self._urls_listbox.GetCount() ):
                
                existing_url = self._urls_listbox.GetClientData( index )
                
                if existing_url == url:
                    
                    self._RemoveURL( index )
                    
                    return
                    
                
            
        else:
            
            self._urls_listbox.Append( url, url )
            
            self._current_urls.add( url )
            
            if url not in self._original_urls:
                
                self._urls_to_add.add( url )
                
            
        
    
    def _Paste( self ):
        
        raw_text = HG.client_controller.GetClipboardText()
        
        try:
            
            for url in HydrusText.DeserialiseNewlinedTexts( raw_text ):
                
                if url != '':
                    
                    self._EnterURL( url, only_add = True )
                    
                
            
        except:
            
            wx.MessageBox( 'I could not understand what was in the clipboard' )
            
        
    
    def _RemoveURL( self, index ):
        
        url = self._urls_listbox.GetClientData( index )
        
        self._urls_listbox.Delete( index )
        
        self._current_urls.discard( url )
        
        self._urls_to_add.discard( url )
        
        if url in self._original_urls:
            
            self._urls_to_remove.add( url )
            
        
    
    def EventListDoubleClick( self, event ):
        
        selection = self._urls_listbox.GetSelection()
        
        if selection != wx.NOT_FOUND:
            
            url = self._urls_listbox.GetClientData( selection )
            
            self._RemoveURL( selection )
            
            self._url_input.SetValue( url )
            
        
    
    def EventInputCharHook( self, event ):
        
        ( modifier, key ) = ClientData.ConvertKeyEventToSimpleTuple( event )
        
        if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            url = self._url_input.GetValue()
            
            if url == '':
                
                self.GetParent().DoOK()
                
            else:
                
                parse_result = urlparse.urlparse( url )
                
                if parse_result.scheme == '':
                    
                    wx.MessageBox( 'Could not parse that URL! Please make sure you include http:// or https://.' )
                    
                    return
                    
                
                self._EnterURL( url )
                
                self._url_input.SetValue( '' )
                
            
        else:
            
            event.Skip()
            
        
    
    def CommitChanges( self ):
        
        hash = self._media.GetHash()
        
        content_updates = []
        
        if len( self._urls_to_add ) > 0:
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( hash, self._urls_to_add ) ) )
            
        
        if len( self._urls_to_remove ) > 0:
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( hash, self._urls_to_remove ) ) )
            
        
        if len( content_updates ) > 0:
            
            service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : content_updates }
            
            HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
class RepairFileSystemPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, missing_locations ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._only_thumbs = True
        
        for ( incorrect_location, prefix ) in missing_locations:
            
            if prefix.startswith( 'f' ):
                
                self._only_thumbs = False
                
            
        
        text = 'This dialog has launched because some expected file storage directories were not found. This is a serious error. You have two options:'
        text += os.linesep * 2
        text += '1) If you know what these should be (e.g. you recently remapped their external drive to another location), update the paths here manually. For most users, this will likely be a simple ctrl+a->correct, but if you have a more complicated system or store your thumbnails different to your files, make sure you skim the whole list. Check everything reports _ok!_'
        text += os.linesep * 2
        text += 'Then hit \'apply\', and the client will launch. You should double-check your \'preferred\' file storage locations under database->migrate database immediately.'
        text += os.linesep * 2
        text += '2) If the locations are not available, or you do not know what they should be, or you wish to fix this outside of the program, hit \'cancel\' to gracefully cancel client boot. Feel free to contact hydrus dev for help.'
        
        if self._only_thumbs:
            
            text += os.linesep * 2
            text += 'SPECIAL NOTE FOR YOUR SITUATION: The only paths missing are thumbnail paths. If you cannot recover these folders, you can hit apply to create empty paths at the original or corrected locations and then run a maintenance routine to regenerate the thumbnails from their originals.'
            
        
        st = ClientGUICommon.BetterStaticText( self, text )
        
        st.Wrap( 640 )
        
        self._locations = ClientGUIListCtrl.SaneListCtrl( self, 400, [ ( 'missing location', -1 ), ( 'expected subdirectory', 120 ), ( 'correct location', 240 ), ( 'now ok?', 120 ) ], activation_callback = self._SetLocations )
        
        self._set_button = ClientGUICommon.BetterButton( self, 'set correct location', self._SetLocations )
        
        # add a button here for 'try to fill them in for me'. you give it a dir, and it tries to figure out and fill in the prefixes for you
        
        #
        
        for ( incorrect_location, prefix ) in missing_locations:
            
            t = ( incorrect_location, prefix, '', '' )
            
            self._locations.Append( t, t )
            
        
        # sort by prefix
        
        #self._locations.SortListItems( 1 ) # subdirs secondary
        #self._locations.SortListItems( 0 ) # missing location primary
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._locations, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.Add( self._set_button, CC.FLAGS_LONE_BUTTON )
        
        self.SetSizer( vbox )
        
    
    def _SetLocations( self ):
        
        selected_indices = self._locations.GetAllSelected()
        
        if len( selected_indices ) > 0:
            
            with wx.DirDialog( self, 'Select correct location.' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    correct_location = HydrusData.ToUnicode( dlg.GetPath() )
                    
                    for index in selected_indices:
                        
                        ( incorrect_location, prefix, gumpf, gumpf_ok ) = self._locations.GetClientData( index )
                        
                        if os.path.exists( os.path.join( correct_location, prefix ) ):
                            
                            ok = 'ok!'
                            
                        else:
                            
                            ok = 'not found'
                            
                        
                        t = ( incorrect_location, prefix, correct_location, ok )
                        
                        self._locations.UpdateRow( index, t, t )
                        
                    
                
            
        
    
    def CommitChanges( self ):
        
        correct_rows = []
        
        if self._only_thumbs:
            
            problems = False
            
            for ( incorrect_location, prefix, correct_location, ok ) in self._locations.GetClientData():
                
                if correct_location == '':
                    
                    problems = True
                    
                    correct_location = incorrect_location
                    
                elif ok != 'ok!':
                    
                    problems = True
                    
                
                correct_rows.append( ( incorrect_location, prefix, correct_location ) )
                
            
            if problems:
                
                message = 'Some or all of your incorrect paths have not been corrected, but they are all thumbnail paths.'
                message += os.linesep * 2
                message += 'Would you like instead to create new empty folders at the previous (or corrected, if you have entered them) locations?'
                message += os.linesep * 2
                message += 'You can run database->regenerate->all thumbnails to fill them up again.'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES:
                        
                        raise HydrusExceptions.VetoException()
                        
                    
                
            
        else:
            
            for ( incorrect_location, prefix, correct_location, ok ) in self._locations.GetClientData():
                
                if correct_location == '':
                    
                    raise HydrusExceptions.VetoException( 'You did not correct all the locations!' )
                    
                elif ok != 'ok!':
                    
                    raise HydrusExceptions.VetoException( 'You did not find all the correct locations!' )
                    
                else:
                    
                    correct_rows.append( ( incorrect_location, prefix, correct_location ) )
                    
                
            
        
        HG.client_controller.WriteSynchronous( 'repair_client_files', correct_rows )
        
    
