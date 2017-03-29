import ClientCaches
import ClientConstants as CC
import ClientData
import ClientDownloading
import ClientGUIACDropdown
import ClientGUICommon
import ClientGUIControls
import ClientGUIDialogs
import ClientGUIListBoxes
import ClientGUIPredicates
import ClientGUIScrolledPanels
import ClientGUIScrolledPanelsEdit
import ClientGUISerialisable
import ClientGUITagSuggestions
import ClientGUITopLevelWindows
import ClientImporting
import ClientMedia
import ClientRatings
import ClientSerialisable
import ClientServices
import collections
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusNetwork
import HydrusNetworking
import HydrusPaths
import HydrusSerialisable
import HydrusTagArchive
import HydrusTags
import itertools
import os
import random
import traceback
import wx

class ManageAccountTypesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, service_key ):
        
        self._admin_service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._deletee_account_type_keys_to_new_account_type_keys = {}
        
        self._account_types_listctrl = ClientGUICommon.SaneListCtrlForSingleObject( self, 200, [ ( 'title', -1 ) ], delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._Add )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        response = self._admin_service.Request( HC.GET, 'account_types' )
        
        account_types = response[ 'account_types' ]
        
        for account_type in account_types:
            
            ( display_tuple, sort_tuple ) = self._ConvertAccountTypeToTuples( account_type )
            
            self._account_types_listctrl.Append( display_tuple, sort_tuple, account_type )
            
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._add_button, CC.FLAGS_VCENTER )
        hbox.AddF( self._edit_button, CC.FLAGS_VCENTER )
        hbox.AddF( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._account_types_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
        
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
        
        self._listctrl = ClientGUICommon.SaneListCtrlForSingleObject( self, 400, [ ( 'type', 220 ), ( 'name', -1 ), ( 'deletable', 120 ) ], delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        menu_items = []
        
        for service_type in HC.ADDREMOVABLE_SERVICES:
            
            service_string = HC.service_string_lookup[ service_type ]
            
            menu_items.append( ( 'normal', service_string, 'Add a new ' + service_string + '.', HydrusData.Call( self._Add, service_type ) ) )
            
        
        self._add_button = ClientGUICommon.MenuButton( self, 'add', menu_items = menu_items )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        #
        
        all_services = HydrusGlobals.client_controller.GetServicesManager().GetServices()
        
        for service in all_services:
            
            ( display_tuple, sort_tuple ) = self._ConvertServiceToTuples( service )
            
            self._listctrl.Append( display_tuple, sort_tuple, service )
            
        
        self._listctrl.SortListItems( 0 )
        
        #
        
        add_remove_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        add_remove_hbox.AddF( self._add_button, CC.FLAGS_LONE_BUTTON )
        add_remove_hbox.AddF( self._edit_button, CC.FLAGS_LONE_BUTTON )
        add_remove_hbox.AddF( self._delete_button, CC.FLAGS_LONE_BUTTON )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( add_remove_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _ConvertServiceToTuples( self, service ):
        
        service_type = service.GetServiceType()
        name = service.GetName()
        deletable = service_type in HC.ADDREMOVABLE_SERVICES
        
        pretty_service_type = HC.service_string_lookup[ service_type ]
        
        if deletable:
            
            pretty_deletable = 'yes'
            
        else:
            
            pretty_deletable = ''
            
        
        return ( ( pretty_service_type, name, pretty_deletable ), ( pretty_service_type, name, deletable ) )
        
    
    def _Add( self, service_type ):
        
        service_key = HydrusData.GenerateKey()
        name = 'new service'
        
        service = ClientServices.GenerateService( service_key, service_type, name )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit service' ) as dlg:
            
            panel = self._EditPanel( dlg, service )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_service = panel.GetValue()
                
                self._listctrl.SetNonDupeName( new_service )
                
                ( display_tuple, sort_tuple ) = self._ConvertServiceToTuples( new_service )
                
                self._listctrl.Append( display_tuple, sort_tuple, new_service )
                
            
        
    
    def _Delete( self ):
        
        deletable_indices = []
        
        selected = self._listctrl.GetAllSelected()
        
        for index in selected:
            
            service = self._listctrl.GetObject( index )
            
            if service.GetServiceType() in HC.ADDREMOVABLE_SERVICES:
                
                deletable_indices.append( index )
                
            
        
        self._listctrl.RemoveIndices( deletable_indices )
        
    
    def _Edit( self ):
        
        indices = self._listctrl.GetAllSelected()
        
        for index in indices:
            
            service = self._listctrl.GetObject( index )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit service' ) as dlg:
                
                panel = self._EditPanel( dlg, service )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_service = panel.GetValue()
                    
                    ( display_tuple, sort_tuple ) = self._ConvertServiceToTuples( edited_service )
                    
                    self._listctrl.UpdateRow( index, display_tuple, sort_tuple, edited_service )
                    
                else:
                    
                    return
                    
                
            
        
    
    def CommitChanges( self ):
        
        services = self._listctrl.GetObjects()
        
        HydrusGlobals.client_controller.SetServices( services )
        
    
    class _EditPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, service ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            duplicate_service = service.Duplicate()
            
            ( self._service_key, self._service_type, name, self._dictionary ) = duplicate_service.ToTuple()
            
            self._service_panel = self._ServicePanel( self, name )
            
            self._panels = []
            
            if self._service_type in HC.REMOTE_SERVICES:
                
                remote_panel = self._ServiceRemotePanel( self, self._dictionary )
                
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
            
            vbox.AddF( self._service_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            for panel in self._panels:
                
                vbox.AddF( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
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
                    
                    archive_namespaces = hta.GetNamespaces()
                
                    with ClientGUIDialogs.DialogCheckFromListOfStrings( self, 'Select namespaces', HydrusData.ConvertUglyNamespacesToPrettyStrings( archive_namespaces ) ) as dlg:
                        
                        if dlg.ShowModal() == wx.ID_OK:
                            
                            namespaces = HydrusData.ConvertPrettyStringsToUglyNamespaces( dlg.GetChecked() )
                            
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
                
                archive_namespaces = hta.GetNamespaces()
                
                with ClientGUIDialogs.DialogCheckFromListOfStrings( self, 'Select namespaces', HydrusData.ConvertUglyNamespacesToPrettyStrings( archive_namespaces ), HydrusData.ConvertUglyNamespacesToPrettyStrings( existing_namespaces ) ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        namespaces = HydrusData.ConvertPrettyStringsToUglyNamespaces( dlg.GetChecked() )
                        
                    else:
                        
                        return
                        
                    
                
                name_to_display = self._GetArchiveNameToDisplay( portable_hta_path, namespaces )
                
                self._archive_sync.SetString( selection, name_to_display )
                self._archive_sync.SetClientData( selection, ( portable_hta_path, namespaces ) )
                
            
        
        def EventArchiveRemove( self, event ):
            
            selection = self._archive_sync.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                self._archive_sync.Delete( selection )
                
            
        
        def EventCheckIPFS( self, event ):
            
            service = self.GetValue()
            
            try:
                
                version = service.GetDaemonVersion()
                
                wx.MessageBox( 'Everything looks ok! Connected to IPFS Daemon with version: ' + version )
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
                wx.MessageBox( 'Could not connect!' )
                
            
        
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
                
                self.AddF( self._name, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                name = self._name.GetValue()
                
                if name == '':
                    
                    wx.MessageBox( 'Please enter a name!' )
                    
                    raise HydrusExceptions.VetoException()
                    
                
                return name
                
            
        
        class _ServiceRemotePanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'clientside network' )
                
                credentials = dictionary[ 'credentials' ]
                bandwidth_rules = dictionary[ 'bandwidth_rules' ]
                
                self._host = wx.TextCtrl( self )
                self._port = wx.SpinCtrl( self, min = 1, max = 65535, size = ( 80, -1 ) )
                
                self._test_address_button = ClientGUICommon.BetterButton( self, 'test address', self._TestAddress )
                
                self._bandwidth_rules = ClientGUIControls.BandwidthRulesCtrl( self, bandwidth_rules )
                
                #
                
                ( host, port ) = credentials.GetAddress()
                
                self._host.SetValue( host )
                self._port.SetValue( port )
                
                #
                
                hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                hbox.AddF( self._host, CC.FLAGS_EXPAND_BOTH_WAYS )
                hbox.AddF( wx.StaticText( self, label = ':' ), CC.FLAGS_VCENTER )
                hbox.AddF( self._port, CC.FLAGS_VCENTER )
                
                wrapped_hbox = ClientGUICommon.WrapInText( hbox, self, 'address: ' )
                
                self.AddF( wrapped_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                self.AddF( self._test_address_button, CC.FLAGS_LONE_BUTTON )
                self.AddF( self._bandwidth_rules, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def _TestAddress( self ):
                
                try:
                    
                    credentials = self.GetCredentials()
                    
                except HydrusExceptions.VetoException:
                    
                    return
                    
                
                ( host, port ) = credentials.GetAddress()
                
                url = 'https://' + host + ':' + str( port ) + '/'
                
                try:
                    
                    result = HydrusGlobals.client_controller.DoHTTP( HC.GET, url, hydrus_network = True )
                    
                    wx.MessageBox( 'Got an ok response!' )
                    
                except HydrusExceptions.NetworkException as e:
                    
                    wx.MessageBox( 'Problem with that address: ' + HydrusData.ToUnicode( e ) )
                    
                
            
            def GetCredentials( self ):
                
                host = self._host.GetValue()
                
                if host == '':
                    
                    wx.MessageBox( 'Please enter a host!' )
                    
                    raise HydrusExceptions.VetoException()
                    
                
                port = self._port.GetValue()
                
                return HydrusNetwork.Credentials( host, port )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                credentials = self.GetCredentials()
                
                dictionary_part[ 'credentials' ] = credentials
                
                bandwidth_rules = self._bandwidth_rules.GetValue()
                
                dictionary_part[ 'bandwidth_rules' ] = bandwidth_rules
                
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
                
                hbox.AddF( self._register, CC.FLAGS_LONE_BUTTON )
                hbox.AddF( self._test_credentials_button, CC.FLAGS_LONE_BUTTON )
                
                wrapped_access_key = ClientGUICommon.WrapInText( self._access_key, self, 'access key: ' )
                
                self.AddF( wrapped_access_key, CC.FLAGS_EXPAND_PERPENDICULAR )
                self.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
                
            
            def _GetAccessKeyFromRegistrationKey( self ):
                
                def do_it( service, registration_key ):
                    
                    try:
                        
                        response = service.Request( HC.GET, 'access_key', { 'registration_key' : registration_key } )
                        
                        access_key_encoded = response[ 'access_key' ].encode( 'hex' )
                        
                        wx.CallAfter( self._access_key.SetValue, access_key_encoded )
                        
                    finally:
                        
                        wx.CallAfter( self._register.Enable )
                        wx.CallAfter( self._register.SetLabel, 'fetch an access key with a registration key' )
                        
                    
                
                try:
                    
                    credentials = self._remote_panel.GetCredentials()
                    
                except HydrusExceptions.VetoException:
                    
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
                        
                    
                
                service_key = HydrusData.GenerateKey()
                
                service = ClientServices.GenerateService( service_key, self._service_type, 'test service' )
                
                service.SetCredentials( credentials )
                
                self._register.Disable()
                self._register.SetLabel( u'fetching\u2026' )
                
                HydrusGlobals.client_controller.CallToThread( do_it, service, registration_key )
                
            
            def _TestCredentials( self ):
                
                try:
                    
                    credentials = self.GetCredentials()
                    
                except HydrusExceptions.VetoException:
                    
                    return
                    
                
                service_key = HydrusData.GenerateKey()
                
                service = ClientServices.GenerateService( service_key, self._service_type, 'test service' )
                
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
                    
                
            
            def GetCredentials( self ):
                
                credentials = self._remote_panel.GetCredentials()
                
                try:
                    
                    access_key = self._access_key.GetValue().decode( 'hex' )
                    
                except:
                    
                    wx.MessageBox( 'Could not understand that access key!' )
                    
                    raise HydrusExceptions.VetoException()
                    
                
                if access_key != '':
                    
                    credentials.SetAccessKey( access_key )
                    
                
                return credentials
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                credentials = self.GetCredentials()
                
                if credentials != self._original_credentials:
                    
                    account = HydrusNetwork.Account.GenerateUnknownAccount()
                    
                    dictionary_part[ 'account' ] = HydrusNetwork.Account.GenerateSerialisableTupleFromAccount( account )
                    
                    session_manager = HydrusGlobals.client_controller.GetClientSessionManager()
                    
                    session_manager.DeleteSessionKey( self._service_key )
                    
                
                dictionary_part[ 'credentials' ] = credentials
                
                return dictionary_part
                
            
        
        class _ServiceTagPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'tags' )
                
                self._st = wx.StaticText( self )
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
                
                self.AddF( self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                return dictionary_part
                
            
        
        class _ServiceLocalBooruPanel( ClientGUICommon.StaticBox ):
            
            def __init__( self, parent, dictionary ):
                
                ClientGUICommon.StaticBox.__init__( self, parent, 'local booru' )
                
                #dictionary[ 'port' ] = None
                #dictionary[ 'upnp_port' ] = None
                #dictionary[ 'bandwidth_rules' ] = HydrusNetworking.BandwidthRules()
                
                self._st = wx.StaticText( self )
                '''
            if service_type == HC.LOCAL_BOORU:
                
                self._booru_options_panel = ClientGUICommon.StaticBox( self, 'options' )
                
                self._port = ClientGUICommon.NoneableSpinCtrl( self._booru_options_panel, 'booru local port', none_phrase = 'do not run local booru service', min = 1, max = 65535 )
                
                self._upnp = ClientGUICommon.NoneableSpinCtrl( self._booru_options_panel, 'upnp port', none_phrase = 'do not forward port', max = 65535 )
                
                self._max_monthly_data = ClientGUICommon.NoneableSpinCtrl( self._booru_options_panel, 'max monthly MB', multiplier = 1024 * 1024 )
                
            '''
                #
                
                self._st.SetLabelText( 'This is a Local Booru service. This box will get regain its port options in a future update.' )
                
                #
                
                self.AddF( self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
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
                    
                    hbox.AddF( border_ctrl, CC.FLAGS_VCENTER )
                    hbox.AddF( fill_ctrl, CC.FLAGS_VCENTER )
                    
                    if colour_type == ClientRatings.LIKE: colour_text = 'liked'
                    elif colour_type == ClientRatings.DISLIKE: colour_text = 'disliked'
                    elif colour_type == ClientRatings.NULL: colour_text = 'not rated'
                    elif colour_type == ClientRatings.MIXED: colour_text = 'a mixture of ratings'
                    
                    rows.append( ( 'border/fill for ' + colour_text + ': ', hbox ) )
                    
                
                gridbox = ClientGUICommon.WrapInGrid( self, rows )
                
                self.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
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
                
                self.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
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
                
                # test creds and fetch version
                # multihash_prefix
                '''
            if service_type == HC.IPFS:
                
                self._ipfs_panel = ClientGUICommon.StaticBox( self, 'ipfs settings' )
                
                self._multihash_prefix = wx.TextCtrl( self._ipfs_panel, value = info[ 'multihash_prefix' ] )
                
                tts = 'When you tell the client to copy the ipfs multihash to your clipboard, it will prefix it with this.'
                tts += os.linesep * 2
                tts += 'Use this if you would rather copy a full gateway url with that action. For instance, you could put here:'
                tts += os.linesep * 2
                tts += 'http://127.0.0.1:8080/ipfs/'
                tts += os.linesep
                tts += 'http://ipfs.io/ipfs/'
                
                self._multihash_prefix.SetToolTipString( tts )
                
            '''
                self._st = wx.StaticText( self )
                
                #
                
                self._st.SetLabelText( 'This is an IPFS service. This box will get regain IPFS options in a future update.' )
                
                #
                
                self.AddF( self._st, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            def GetValue( self ):
                
                dictionary_part = {}
                
                return dictionary_part
                
            
        
    
class ManageOptionsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._new_options = HydrusGlobals.client_controller.GetNewOptions()
        
        self._listbook = ClientGUICommon.ListBook( self )
        
        self._listbook.AddPage( 'connection', 'connection', self._ConnectionPanel( self._listbook ) )
        self._listbook.AddPage( 'files and trash', 'files and trash', self._FilesAndTrashPanel( self._listbook ) )
        self._listbook.AddPage( 'speed and memory', 'speed and memory', self._SpeedAndMemoryPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'maintenance and processing', 'maintenance and processing', self._MaintenanceAndProcessingPanel( self._listbook ) )
        self._listbook.AddPage( 'media', 'media', self._MediaPanel( self._listbook ) )
        self._listbook.AddPage( 'gui', 'gui', self._GUIPanel( self._listbook ) )
        #self._listbook.AddPage( 'sound', 'sound', self._SoundPanel( self._listbook ) )
        self._listbook.AddPage( 'default file system predicates', 'default file system predicates', self._DefaultFileSystemPredicatesPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'default tag import options', 'default tag import options', self._DefaultTagImportOptionsPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'colours', 'colours', self._ColoursPanel( self._listbook ) )
        self._listbook.AddPage( 'sort/collect', 'sort/collect', self._SortCollectPanel( self._listbook ) )
        self._listbook.AddPage( 'shortcuts', 'shortcuts', self._ShortcutsPanel( self._listbook ) )
        self._listbook.AddPage( 'file storage locations', 'file storage locations', self._ClientFilesPanel( self._listbook ) )
        self._listbook.AddPage( 'downloading', 'downloading', self._DownloadingPanel( self._listbook, self._new_options ) )
        self._listbook.AddPage( 'tags', 'tags', self._TagsPanel( self._listbook, self._new_options ) )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._listbook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    class _ClientFilesPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._client_files = ClientGUICommon.SaneListCtrl( self, 200, [ ( 'path', -1 ), ( 'weight', 80 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._edit = wx.Button( self, label = 'edit weight' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEditWeight )
            
            self._delete = wx.Button( self, label = 'delete' )
            self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
            
            self._resized_thumbnails_override = wx.DirPickerCtrl( self, style = wx.DIRP_USE_TEXTCTRL )
            
            self._full_size_thumbnails_override = wx.DirPickerCtrl( self, style = wx.DIRP_USE_TEXTCTRL )
            
            #
            
            self._new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._new_options.GetClientFilesLocationsToIdealWeights()
            
            for ( location, weight ) in locations_to_ideal_weights.items():
                
                self._client_files.Append( ( location, HydrusData.ConvertIntToPrettyString( int( weight ) ) ), ( location, weight ) )
                
            
            if resized_thumbnail_override is not None:
                
                self._resized_thumbnails_override.SetPath( resized_thumbnail_override )
                
            
            if full_size_thumbnail_override is not None:
                
                self._full_size_thumbnails_override.SetPath( full_size_thumbnail_override )
                
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            text = 'Here you can change the folders where the client stores your files. Setting a higher weight increases the proportion of your collection that that folder stores.'
            text += os.linesep * 2
            text += 'If you add or remove folders here, it will take time for the client to incrementally rebalance your files across the new selection, but if you are in a hurry, you can force a full rebalance from the database->maintenance menu on the main gui.'
            
            st = wx.StaticText( self, label = text )
            
            st.Wrap( 400 )
            
            vbox.AddF( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.AddF( self._client_files, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._add, CC.FLAGS_VCENTER )
            hbox.AddF( self._edit, CC.FLAGS_VCENTER )
            hbox.AddF( self._delete, CC.FLAGS_VCENTER )
            
            vbox.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
            
            text = 'If you like, you can force your thumbnails to be stored elsewhere, for instance on a low-latency SSD.'
            text += os.linesep * 2
            text += 'Normally, your full size thumbnails are rarely accessed--only to initially generate resized thumbnails--so you can store them somewhere slow, but if you set the thumbnail size to be the maximum of 200x200, these originals will be used instead of resized thumbs and are good in a fast location.'
            text += os.linesep * 2
            text += 'Leave either of these blank to store the thumbnails alongside the original files.'
            
            st = wx.StaticText( self, label = text )
            
            st.Wrap( 400 )
            
            vbox.AddF( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self, label = 'full size thumbnail override location: ' ), CC.FLAGS_VCENTER )
            hbox.AddF( self._full_size_thumbnails_override, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox.AddF( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( wx.StaticText( self, label = 'resized thumbnail override location: ' ), CC.FLAGS_VCENTER )
            hbox.AddF( self._resized_thumbnails_override, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox.AddF( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def Delete( self ):
            
            if len( self._client_files.GetAllSelected() ) < self._client_files.GetItemCount():
                
                with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        self._client_files.RemoveAllSelected()
                        
                    
                
            
        
        def Edit( self ):
            
            for i in self._client_files.GetAllSelected():
                
                ( location, weight ) = self._client_files.GetClientData( i )
                
                with wx.NumberEntryDialog( self, 'Enter the weight of ' + location + '.', '', 'Enter Weight', value = int( weight ), min = 1, max = 256 ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        weight = dlg.GetValue()
                        
                        weight = float( weight )
                        
                        self._client_files.UpdateRow( i, ( location, HydrusData.ConvertIntToPrettyString( int( weight ) ) ), ( location, weight ) )
                        
                    
                
            
        
        def EventAdd( self, event ):
            
            with wx.DirDialog( self, 'Select the file location' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    path = HydrusData.ToUnicode( dlg.GetPath() )
                    
                    for ( location, weight ) in self._client_files.GetClientData():
                        
                        if path == location:
                            
                            wx.MessageBox( 'You already have that location entered!' )
                            
                            return
                            
                        
                    
                    with wx.NumberEntryDialog( self, 'Enter the weight of ' + path + '.', '', 'Enter Weight', value = 1, min = 1, max = 256 ) as dlg_num:
                        
                        if dlg_num.ShowModal() == wx.ID_OK:
                            
                            weight = dlg_num.GetValue()
                            
                            weight = float( weight )
                            
                            self._client_files.Append( ( path, HydrusData.ConvertIntToPrettyString( int( weight ) ) ), ( path, weight ) )
                            
                        
                    
                
            
        
        def EventDelete( self, event ):
            
            self.Delete()
            
        
        def EventEditWeight( self, event ):
            
            self.Edit()
            
        
        def UpdateOptions( self ):
            
            locations_to_weights = {}
            
            for ( location, weight ) in self._client_files.GetClientData():
                
                locations_to_weights[ location ] = weight
                
            
            resized_thumbnails_override = self._resized_thumbnails_override.GetPath()
            
            if resized_thumbnails_override == '':
                
                resized_thumbnails_override = None
                
            
            full_size_thumbnails_override = self._full_size_thumbnails_override.GetPath()
            
            if full_size_thumbnails_override == '':
                
                full_size_thumbnails_override = None
                
            
            self._new_options.SetClientFilesLocationsToIdealWeights( locations_to_weights, resized_thumbnails_override, full_size_thumbnails_override )
            
        

    class _ColoursPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._gui_colours = {}
            
            for ( name, rgb ) in HC.options[ 'gui_colours' ].items():
                
                ctrl = wx.ColourPickerCtrl( self )
                
                ctrl.SetMaxSize( ( 20, -1 ) )
                
                self._gui_colours[ name ] = ctrl
                
            
            self._namespace_colours = ClientGUIListBoxes.ListBoxTagsColourOptions( self, HC.options[ 'namespace_colours' ] )
            
            self._edit_namespace_colour = wx.Button( self, label = 'edit selected' )
            self._edit_namespace_colour.Bind( wx.EVT_BUTTON, self.EventEditNamespaceColour )
            
            self._new_namespace_colour = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
            self._new_namespace_colour.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownNamespace )
            
            #
            
            for ( name, rgb ) in HC.options[ 'gui_colours' ].items(): self._gui_colours[ name ].SetColour( wx.Colour( *rgb ) )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._gui_colours[ 'thumb_background' ], CC.FLAGS_VCENTER )
            hbox.AddF( self._gui_colours[ 'thumb_background_selected' ], CC.FLAGS_VCENTER )
            hbox.AddF( self._gui_colours[ 'thumb_background_remote' ], CC.FLAGS_VCENTER )
            hbox.AddF( self._gui_colours[ 'thumb_background_remote_selected' ], CC.FLAGS_VCENTER )
            
            rows.append( ( 'thumbnail background (local: normal/selected, remote: normal/selected): ', hbox ) )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._gui_colours[ 'thumb_border' ], CC.FLAGS_VCENTER )
            hbox.AddF( self._gui_colours[ 'thumb_border_selected' ], CC.FLAGS_VCENTER )
            hbox.AddF( self._gui_colours[ 'thumb_border_remote' ], CC.FLAGS_VCENTER )
            hbox.AddF( self._gui_colours[ 'thumb_border_remote_selected' ], CC.FLAGS_VCENTER )
            
            rows.append( ( 'thumbnail border (local: normal/selected, remote: normal/selected): ', hbox ) )
            
            rows.append( ( 'thumbnail grid background: ', self._gui_colours[ 'thumbgrid_background' ] ) )
            rows.append( ( 'autocomplete background: ', self._gui_colours[ 'autocomplete_background' ] ) )
            rows.append( ( 'media viewer background: ', self._gui_colours[ 'media_background' ] ) )
            rows.append( ( 'media viewer text: ', self._gui_colours[ 'media_text' ] ) )
            rows.append( ( 'tags box background: ', self._gui_colours[ 'tags_box' ] ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._namespace_colours, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._new_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._edit_namespace_colour, CC.FLAGS_EXPAND_PERPENDICULAR )
            
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
            
            if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                namespace = self._new_namespace_colour.GetValue()
                
                if namespace != '':
                    
                    self._namespace_colours.SetNamespaceColour( namespace, wx.Colour( random.randint( 0, 255 ), random.randint( 0, 255 ), random.randint( 0, 255 ) ) )
                    
                    self._new_namespace_colour.SetValue( '' )
                    
                
            else: event.Skip()
            
        
        def UpdateOptions( self ):
            
            for ( name, ctrl ) in self._gui_colours.items():
                
                colour = ctrl.GetColour()
                
                rgb = ( colour.Red(), colour.Green(), colour.Blue() )
                
                HC.options[ 'gui_colours' ][ name ] = rgb
                
            
            HC.options[ 'namespace_colours' ] = self._namespace_colours.GetNamespaceColours()
            
        
    
    class _ConnectionPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._external_host = wx.TextCtrl( self )
            self._external_host.SetToolTipString( 'If you have trouble parsing your external ip using UPnP, you can force it to be this.' )
            
            proxy_panel = ClientGUICommon.StaticBox( self, 'proxy settings' )
            
            self._proxy_type = ClientGUICommon.BetterChoice( proxy_panel )
            
            self._proxy_address = wx.TextCtrl( proxy_panel )
            self._proxy_port = wx.SpinCtrl( proxy_panel, min = 0, max = 65535 )
            
            self._proxy_username = wx.TextCtrl( proxy_panel )
            self._proxy_password = wx.TextCtrl( proxy_panel )
            
            #
            
            if HC.options[ 'external_host' ] is not None:
                
                self._external_host.SetValue( HC.options[ 'external_host' ] )
                
            
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
            
            text = 'You have to restart the client for proxy settings to take effect.'
            text += os.linesep
            text += 'This is in a buggy prototype stage right now, pending a rewrite of the networking engine.'
            text += os.linesep
            text += 'Please send me your feedback.'
            
            proxy_panel.AddF( wx.StaticText( proxy_panel, label = text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'proxy type: ', self._proxy_type ) )
            rows.append( ( 'address: ', self._proxy_address ) )
            rows.append( ( 'port: ', self._proxy_port ) )
            rows.append( ( 'username (optional): ', self._proxy_username ) )
            rows.append( ( 'password (optional): ', self._proxy_password ) )
            
            gridbox = ClientGUICommon.WrapInGrid( proxy_panel, rows )
            
            proxy_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            rows = []
            
            rows.append( ( 'external ip/host override: ', self._external_host ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( proxy_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
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
            
        
    
    class _DownloadingPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            general = ClientGUICommon.StaticBox( self, 'general' )
            
            self._website_download_polite_wait = wx.SpinCtrl( general, min = 1, max = 30 )
            
            self._waiting_politely_text = wx.CheckBox( general )
            
            self._verify_regular_https = wx.CheckBox( general )
            
            #
            
            gallery_downloader = ClientGUICommon.StaticBox( self, 'gallery downloader' )
            
            self._gallery_file_limit = ClientGUICommon.NoneableSpinCtrl( gallery_downloader, 'by default, stop searching once this many files are found', none_phrase = 'no limit', min = 1, max = 1000000 )
            
            #
            
            thread_checker = ClientGUICommon.StaticBox( self, 'thread checker' )
            
            self._thread_times_to_check = wx.SpinCtrl( thread_checker, min = 0, max = 65536 )
            self._thread_times_to_check.SetToolTipString( 'how many times the thread checker will check' )
            
            self._thread_check_period = ClientGUICommon.TimeDeltaButton( thread_checker, min = 30, hours = True, minutes = True, seconds = True )
            self._thread_check_period.SetToolTipString( 'how long the checker will wait between checks' )
            
            #
            
            self._website_download_polite_wait.SetValue( HC.options[ 'website_download_polite_wait' ] )
            self._waiting_politely_text.SetValue( self._new_options.GetBoolean( 'waiting_politely_text' ) )
            
            self._verify_regular_https.SetValue( self._new_options.GetBoolean( 'verify_regular_https' ) )
            
            self._gallery_file_limit.SetValue( HC.options[ 'gallery_file_limit' ] )
            
            ( times_to_check, check_period ) = HC.options[ 'thread_checker_timings' ]
            
            self._thread_times_to_check.SetValue( times_to_check )
            
            self._thread_check_period.SetValue( check_period )
            
            #
            
            rows = []
            
            rows.append( ( 'seconds to politely wait between gallery/thread url requests: ', self._website_download_polite_wait ) )
            rows.append( ( 'instead of the traffic light waiting politely indicator, use text: ', self._waiting_politely_text ) )
            rows.append( ( 'BUGFIX: verify regular https traffic:', self._verify_regular_https ) )
            
            gridbox = ClientGUICommon.WrapInGrid( general, rows )
            
            general.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            gallery_downloader.AddF( self._gallery_file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'default number of times to check: ', self._thread_times_to_check ) )
            rows.append( ( 'default wait between checks: ', self._thread_check_period ) )
            
            gridbox = ClientGUICommon.WrapInGrid( thread_checker, rows )
            
            thread_checker.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( general, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( gallery_downloader, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( thread_checker, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'website_download_polite_wait' ] = self._website_download_polite_wait.GetValue()
            self._new_options.SetBoolean( 'waiting_politely_text', self._waiting_politely_text.GetValue() )
            self._new_options.SetBoolean( 'verify_regular_https', self._verify_regular_https.GetValue() )
            HC.options[ 'gallery_file_limit' ] = self._gallery_file_limit.GetValue()
            HC.options[ 'thread_checker_timings' ] = ( self._thread_times_to_check.GetValue(), self._thread_check_period.GetValue() )
            
        
    
    class _MaintenanceAndProcessingPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            self._jobs_panel = ClientGUICommon.StaticBox( self, 'when to run high cpu jobs' )
            self._maintenance_panel = ClientGUICommon.StaticBox( self, 'maintenance period' )
            self._processing_panel = ClientGUICommon.StaticBox( self, 'processing' )
            
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
            
            self._processing_phase = wx.SpinCtrl( self._processing_panel, min = 0, max = 100000 )
            self._processing_phase.SetToolTipString( 'how long this client will delay processing updates after they are due. useful if you have multiple clients and do not want them to process at the same time' )
            
            #
            
            self._idle_normal.SetValue( HC.options[ 'idle_normal' ] )
            self._idle_period.SetValue( HC.options[ 'idle_period' ] )
            self._idle_mouse_period.SetValue( HC.options[ 'idle_mouse_period' ] )
            self._idle_cpu_max.SetValue( HC.options[ 'idle_cpu_max' ] )
            
            self._idle_shutdown.SelectClientData( HC.options[ 'idle_shutdown' ] )
            self._idle_shutdown_max_minutes.SetValue( HC.options[ 'idle_shutdown_max_minutes' ] )
            
            self._maintenance_vacuum_period_days.SetValue( self._new_options.GetNoneableInteger( 'maintenance_vacuum_period_days' ) )
            
            self._processing_phase.SetValue( HC.options[ 'processing_phase' ] )
            
            #
            
            rows = []
            
            rows.append( ( 'Run maintenance jobs when the client is idle and the system is not otherwise busy: ', self._idle_normal ) )
            rows.append( ( 'Assume the client is idle if no general browsing activity has occured in the past: ', self._idle_period ) )
            rows.append( ( 'Assume the client is idle if the mouse has not been moved in the past: ', self._idle_mouse_period ) )
            rows.append( ( 'Assume the system is busy if any CPU core has recent average usage above: ', self._idle_cpu_max ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._idle_panel, rows )
            
            self._idle_panel.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Run jobs on shutdown: ', self._idle_shutdown ) )
            rows.append( ( 'Max number of minutes to run shutdown jobs: ', self._idle_shutdown_max_minutes ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._shutdown_panel, rows )
            
            self._shutdown_panel.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'CPU-heavy jobs like maintenance routines and repository synchronisation processing will stutter or lock up your gui, so they do not normally run when you are searching for and looking at files.'
            text += os.linesep * 2
            text += 'You can set them to run only when the client is idle, or only during shutdown, or neither, or both.'
            text += os.linesep * 2
            text += 'If the client switches from idle to not idle, it will try to abandon any jobs it is half way through.'
            text += os.linesep * 2
            text += 'If the client believes the system is busy, it will not start jobs.'
            
            st = wx.StaticText( self._jobs_panel, label = text )
            
            st.Wrap( 550 )
            
            self._jobs_panel.AddF( st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.AddF( self._idle_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            self._jobs_panel.AddF( self._shutdown_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Number of days to wait between vacuums: ', self._maintenance_vacuum_period_days ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._maintenance_panel, rows )
            
            self._maintenance_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Delay repository update processing by (s): ', self._processing_phase ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self._processing_panel, rows )
            
            self._processing_panel.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._maintenance_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._processing_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
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
            
            HC.options[ 'processing_phase' ] = self._processing_phase.GetValue()
            
            self._new_options.SetNoneableInteger( 'maintenance_vacuum_period_days', self._maintenance_vacuum_period_days.GetValue() )
            
        
    
    class _DefaultFileSystemPredicatesPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            self._filter_inbox_and_archive_predicates = wx.CheckBox( self, label = 'hide inbox and archive predicates if either has no files' )
            
            self._filter_inbox_and_archive_predicates.SetValue( self._new_options.GetBoolean( 'filter_inbox_and_archive_predicates' ) )
            
            self._file_system_predicate_age = ClientGUIPredicates.PanelPredicateSystemAge( self )
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
            
            vbox.AddF( self._filter_inbox_and_archive_predicates, CC.FLAGS_VCENTER )
            vbox.AddF( ( 20, 20 ), CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_age, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_duration, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_height, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_mime, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_num_pixels, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_num_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_num_words, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_ratio, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_similar_to, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_size, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( self._file_system_predicate_width, CC.FLAGS_EXPAND_PERPENDICULAR )
            
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
            
        
    
    class _DefaultTagImportOptionsPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            self._import_tag_options = wx.ListBox( self )
            self._import_tag_options.Bind( wx.EVT_LEFT_DCLICK, self.EventDelete )
            
            self._add = wx.Button( self, label = 'add' )
            self._add.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._edit = wx.Button( self, label = 'edit' )
            self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._delete = wx.Button( self, label = 'delete' )
            self._delete.Bind( wx.EVT_BUTTON, self.EventDelete )
            
            #
            
            for ( gallery_identifier, import_tag_options ) in self._new_options.GetDefaultImportTagOptions().items():
                
                name = gallery_identifier.ToString()
                
                self._import_tag_options.Append( name, ( gallery_identifier, import_tag_options ) )
                
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._import_tag_options, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._add, CC.FLAGS_BUTTON_SIZER )
            hbox.AddF( self._edit, CC.FLAGS_BUTTON_SIZER )
            hbox.AddF( self._delete, CC.FLAGS_BUTTON_SIZER )
            
            vbox.AddF( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def EventAdd( self, event ):
            
            gallery_identifiers = []
            
            for site_type in [ HC.SITE_TYPE_DEFAULT, HC.SITE_TYPE_DEVIANT_ART, HC.SITE_TYPE_HENTAI_FOUNDRY, HC.SITE_TYPE_NEWGROUNDS, HC.SITE_TYPE_PIXIV, HC.SITE_TYPE_TUMBLR ]:
                
                gallery_identifiers.append( ClientDownloading.GalleryIdentifier( site_type ) )
                
            
            gallery_identifiers.append( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_BOORU ) )
            
            boorus = HydrusGlobals.client_controller.Read( 'remote_boorus' )
            
            for booru_name in boorus.keys():
                
                gallery_identifiers.append( ClientDownloading.GalleryIdentifier( HC.SITE_TYPE_BOORU, additional_info = booru_name ) )
                
            
            list_of_tuples = [ ( gallery_identifier.ToString(), gallery_identifier ) for gallery_identifier in gallery_identifiers ]
            
            with ClientGUIDialogs.DialogSelectFromList( self, 'select tag domain', list_of_tuples ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    gallery_identifier = dlg.GetChoice()
                    
                    name = gallery_identifier.ToString()
                    
                    for i in range( self._import_tag_options.GetCount() ):
                        
                        if name == self._import_tag_options.GetString( i ):
                            
                            wx.MessageBox( 'You already have default tag import options set up for that domain!' )
                            
                            return
                            
                        
                    
                    with ClientGUIDialogs.DialogInputImportTagOptions( self, name, gallery_identifier ) as ito_dlg:
                        
                        if ito_dlg.ShowModal() == wx.ID_OK:
                            
                            import_tag_options = ito_dlg.GetImportTagOptions()
                            
                            self._import_tag_options.Append( name, ( gallery_identifier, import_tag_options ) )
                            
                        
                    
                
            
        
        def EventDelete( self, event ):
            
            selection = self._import_tag_options.GetSelection()
            
            if selection != wx.NOT_FOUND: self._import_tag_options.Delete( selection )
            
        
        def EventEdit( self, event ):
            
            selection = self._import_tag_options.GetSelection()
            
            if selection != wx.NOT_FOUND:
                
                name = self._import_tag_options.GetString( selection )
                
                ( gallery_identifier, import_tag_options ) = self._import_tag_options.GetClientData( selection )
                
                with ClientGUIDialogs.DialogInputImportTagOptions( self, name, gallery_identifier, import_tag_options ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        import_tag_options = dlg.GetImportTagOptions()
                        
                        self._import_tag_options.SetClientData( selection, ( gallery_identifier, import_tag_options ) )
                        
                    
                
            
        
        def UpdateOptions( self ):
            
            self._new_options.ClearDefaultImportTagOptions()
            
            for ( gallery_identifier, import_tag_options ) in [ self._import_tag_options.GetClientData( i ) for i in range( self._import_tag_options.GetCount() ) ]:
                
                self._new_options.SetDefaultImportTagOptions( gallery_identifier, import_tag_options )
                
            
        
    
    class _FilesAndTrashPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._export_location = wx.DirPickerCtrl( self, style = wx.DIRP_USE_TEXTCTRL )
            
            self._delete_to_recycle_bin = wx.CheckBox( self, label = '' )
            self._exclude_deleted_files = wx.CheckBox( self, label = '' )
            
            self._remove_filtered_files = wx.CheckBox( self, label = '' )
            self._remove_trashed_files = wx.CheckBox( self, label = '' )
            
            self._trash_max_age = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no age limit', min = 0, max = 8640 )
            self._trash_max_size = ClientGUICommon.NoneableSpinCtrl( self, '', none_phrase = 'no size limit', min = 0, max = 20480 )
            
            #
            
            if HC.options[ 'export_path' ] is not None:
                
                abs_path = HydrusPaths.ConvertPortablePathToAbsPath( HC.options[ 'export_path' ] )
                
                if abs_path is not None:
                    
                    self._export_location.SetPath( abs_path )
                    
                
            
            self._delete_to_recycle_bin.SetValue( HC.options[ 'delete_to_recycle_bin' ] )
            self._exclude_deleted_files.SetValue( HC.options[ 'exclude_deleted_files' ] )
            self._remove_filtered_files.SetValue( HC.options[ 'remove_filtered_files' ] )
            self._remove_trashed_files.SetValue( HC.options[ 'remove_trashed_files' ] )
            self._trash_max_age.SetValue( HC.options[ 'trash_max_age' ] )
            self._trash_max_size.SetValue( HC.options[ 'trash_max_size' ] )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            rows.append( ( 'Default export directory: ', self._export_location ) )
            rows.append( ( 'When deleting files or folders, send them to the OS\'s recycle bin: ', self._delete_to_recycle_bin ) )
            rows.append( ( 'By default, do not reimport files that have been previously deleted: ', self._exclude_deleted_files ) )
            rows.append( ( 'Remove files from view when they are filtered: ', self._remove_filtered_files ) )
            rows.append( ( 'Remove files from view when they are sent to the trash: ', self._remove_trashed_files ) )
            rows.append( ( 'Number of hours a file can be in the trash before being deleted: ', self._trash_max_age ) )
            rows.append( ( 'Maximum size of trash (MB): ', self._trash_max_size ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            text = 'If you set the default export directory blank, the client will use \'hydrus_export\' under the current user\'s home directory.'
            
            vbox.AddF( wx.StaticText( self, label = text ), CC.FLAGS_CENTER )
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'export_path' ] = HydrusPaths.ConvertAbsPathToPortablePath( HydrusData.ToUnicode( self._export_location.GetPath() ) )
            
            HC.options[ 'delete_to_recycle_bin' ] = self._delete_to_recycle_bin.GetValue()
            HC.options[ 'exclude_deleted_files' ] = self._exclude_deleted_files.GetValue()
            HC.options[ 'remove_filtered_files' ] = self._remove_filtered_files.GetValue()
            HC.options[ 'remove_trashed_files' ] = self._remove_trashed_files.GetValue()
            HC.options[ 'trash_max_age' ] = self._trash_max_age.GetValue()
            HC.options[ 'trash_max_size' ] = self._trash_max_size.GetValue()
            
        
    
    class _GUIPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._main_gui_title = wx.TextCtrl( self )
            
            self._default_gui_session = wx.Choice( self )
            
            self._confirm_client_exit = wx.CheckBox( self )
            self._confirm_trash = wx.CheckBox( self )
            self._confirm_archive = wx.CheckBox( self )
            
            self._always_embed_autocompletes = wx.CheckBox( self )
            
            self._gui_capitalisation = wx.CheckBox( self )
            
            self._hide_preview = wx.CheckBox( self )
            
            self._show_thumbnail_title_banner = wx.CheckBox( self )
            self._show_thumbnail_page = wx.CheckBox( self )
            
            self._hide_message_manager_on_gui_iconise = wx.CheckBox( self )
            self._hide_message_manager_on_gui_iconise.SetToolTipString( 'If your message manager does not automatically minimise with your main gui, try this. It can lead to unusual show and positioning behaviour on window managers that do not support it, however.' )
            
            self._hide_message_manager_on_gui_deactive = wx.CheckBox( self )
            self._hide_message_manager_on_gui_deactive.SetToolTipString( 'If your message manager stays up after you minimise the program to the system tray using a custom window manager, try this out! It hides the popup messages as soon as the main gui loses focus.' )
            
            frame_locations_panel = ClientGUICommon.StaticBox( self, 'frame locations' )
            
            self._frame_locations = ClientGUICommon.SaneListCtrl( frame_locations_panel, 200, [ ( 'name', -1 ), ( 'remember size', 90 ), ( 'remember position', 90 ), ( 'last size', 90 ), ( 'last position', 90 ), ( 'default gravity', 90 ), ( 'default position', 90 ), ( 'maximised', 90 ), ( 'fullscreen', 90 ) ], activation_callback = self.EditFrameLocations )
            
            self._frame_locations_edit_button = wx.Button( frame_locations_panel, label = 'edit' )
            self._frame_locations_edit_button.Bind( wx.EVT_BUTTON, self.EventEditFrameLocation )
            
            #
            
            self._new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            self._main_gui_title.SetValue( self._new_options.GetString( 'main_gui_title' ) )
            
            gui_session_names = HydrusGlobals.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION )
            
            if 'last session' not in gui_session_names: gui_session_names.insert( 0, 'last session' )
            
            self._default_gui_session.Append( 'just a blank page', None )
            
            for name in gui_session_names: self._default_gui_session.Append( name, name )
            
            try: self._default_gui_session.SetStringSelection( HC.options[ 'default_gui_session' ] )
            except: self._default_gui_session.SetSelection( 0 )
            
            self._confirm_client_exit.SetValue( HC.options[ 'confirm_client_exit' ] )
            
            self._confirm_trash.SetValue( HC.options[ 'confirm_trash' ] )
            
            self._confirm_archive.SetValue( HC.options[ 'confirm_archive' ] )
            
            self._always_embed_autocompletes.SetValue( HC.options[ 'always_embed_autocompletes' ] )
            
            self._gui_capitalisation.SetValue( HC.options[ 'gui_capitalisation' ] )
            
            self._hide_preview.SetValue( HC.options[ 'hide_preview' ] )
            
            self._show_thumbnail_title_banner.SetValue( self._new_options.GetBoolean( 'show_thumbnail_title_banner' ) )
            
            self._show_thumbnail_page.SetValue( self._new_options.GetBoolean( 'show_thumbnail_page' ) )
            
            self._hide_message_manager_on_gui_iconise.SetValue( self._new_options.GetBoolean( 'hide_message_manager_on_gui_iconise' ) )
            self._hide_message_manager_on_gui_deactive.SetValue( self._new_options.GetBoolean( 'hide_message_manager_on_gui_deactive' ) )
            
            for ( name, info ) in self._new_options.GetFrameLocations():
                
                listctrl_list = [ name ] + list( info )
                
                pretty_listctrl_list = self._GetPrettyFrameLocationInfo( listctrl_list )
                
                self._frame_locations.Append( pretty_listctrl_list, listctrl_list )
                
            
            self._frame_locations.SortListItems( col = 0 )
            
            #
            
            rows = []
            
            rows.append( ( 'Main gui title: ', self._main_gui_title ) )
            rows.append( ( 'Default session on startup: ', self._default_gui_session ) )
            rows.append( ( 'Confirm client exit: ', self._confirm_client_exit ) )
            rows.append( ( 'Confirm sending files to trash: ', self._confirm_trash ) )
            rows.append( ( 'Confirm sending more than one file to archive or inbox: ', self._confirm_archive ) )
            rows.append( ( 'Always embed autocomplete dropdown results window: ', self._always_embed_autocompletes ) )
            rows.append( ( 'Capitalise gui: ', self._gui_capitalisation ) )
            rows.append( ( 'Hide the preview window: ', self._hide_preview ) )
            rows.append( ( 'Show \'title\' banner on thumbnails: ', self._show_thumbnail_title_banner ) )
            rows.append( ( 'Show volume/chapter/page number on thumbnails: ', self._show_thumbnail_page ) )
            rows.append( ( 'BUGFIX: Hide the popup message manager when the main gui is minimised: ', self._hide_message_manager_on_gui_iconise ) )
            rows.append( ( 'BUGFIX: Hide the popup message manager when the main gui loses focus: ', self._hide_message_manager_on_gui_deactive ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            text = 'Here you can override the current and default values for many frame and dialog sizing and positioning variables.'
            text += os.linesep
            text += 'This is an advanced control. If you aren\'t confident of what you are doing here, come back later!'
            
            frame_locations_panel.AddF( wx.StaticText( frame_locations_panel, label = text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            frame_locations_panel.AddF( self._frame_locations, CC.FLAGS_EXPAND_BOTH_WAYS )
            frame_locations_panel.AddF( self._frame_locations_edit_button, CC.FLAGS_LONE_BUTTON )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( frame_locations_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
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
            HC.options[ 'gui_capitalisation' ] = self._gui_capitalisation.GetValue()
            
            HC.options[ 'hide_preview' ] = self._hide_preview.GetValue()
            
            title = self._main_gui_title.GetValue()
            
            self._new_options.SetString( 'main_gui_title', title )
            
            HydrusGlobals.client_controller.pub( 'main_gui_title', title )
            
            self._new_options.SetBoolean( 'show_thumbnail_title_banner', self._show_thumbnail_title_banner.GetValue() )
            self._new_options.SetBoolean( 'show_thumbnail_page', self._show_thumbnail_page.GetValue() )
            
            self._new_options.SetBoolean( 'hide_message_manager_on_gui_iconise', self._hide_message_manager_on_gui_iconise.GetValue() )
            self._new_options.SetBoolean( 'hide_message_manager_on_gui_deactive', self._hide_message_manager_on_gui_deactive.GetValue() )
            
            for listctrl_list in self._frame_locations.GetClientData():
                
                ( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen ) = listctrl_list
                
                self._new_options.SetFrameLocation( name, remember_size, remember_position, last_size, last_position, default_gravity, default_position, maximised, fullscreen )
                
            
        
    
    class _MediaPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            self._animation_start_position = wx.SpinCtrl( self, min = 0, max = 100 )
            
            self._disable_cv_for_gifs = wx.CheckBox( self )
            self._disable_cv_for_gifs.SetToolTipString( 'OpenCV is good at rendering gifs, but if you have problems with it and your graphics card, check this and the less reliable and slower PIL will be used instead.' )
            
            self._load_images_with_pil = wx.CheckBox( self )
            self._load_images_with_pil.SetToolTipString( 'OpenCV is much faster than PIL, but the current release crashes on certain images. You can try turning this off, but switch it back on if you have any problems.' )
            
            self._use_system_ffmpeg = wx.CheckBox( self )
            self._use_system_ffmpeg.SetToolTipString( 'Check this to always default to the system ffmpeg in your path, rather than using the static ffmpeg in hydrus\'s bin directory. (requires restart)' )
            
            self._media_zooms = wx.TextCtrl( self )
            self._media_zooms.Bind( wx.EVT_TEXT, self.EventZoomsChanged )
            
            self._media_viewer_panel = ClientGUICommon.StaticBox( self, 'media viewer mime handling' )
            
            self._media_viewer_options = ClientGUICommon.SaneListCtrlForSingleObject( self._media_viewer_panel, 300, [ ( 'mime', 150 ), ( 'media show action', 140 ), ( 'preview show action', 140 ), ( 'zoom info', -1 ) ], activation_callback = self.EditMediaViewerOptions )
            
            self._media_viewer_edit_button = wx.Button( self._media_viewer_panel, label = 'edit' )
            self._media_viewer_edit_button.Bind( wx.EVT_BUTTON, self.EventEditMediaViewerOptions )
            
            #
            
            self._animation_start_position.SetValue( int( HC.options[ 'animation_start_position' ] * 100.0 ) )
            self._disable_cv_for_gifs.SetValue( self._new_options.GetBoolean( 'disable_cv_for_gifs' ) )
            self._load_images_with_pil.SetValue( self._new_options.GetBoolean( 'load_images_with_pil' ) )
            self._use_system_ffmpeg.SetValue( self._new_options.GetBoolean( 'use_system_ffmpeg' ) )
            
            media_zooms = self._new_options.GetMediaZooms()
            
            self._media_zooms.SetValue( ','.join( ( str( media_zoom ) for media_zoom in media_zooms ) ) )
            
            mimes_in_correct_order = ( HC.IMAGE_JPEG, HC.IMAGE_PNG, HC.IMAGE_GIF, HC.APPLICATION_FLASH, HC.APPLICATION_PDF, HC.APPLICATION_HYDRUS_UPDATE_CONTENT, HC.APPLICATION_HYDRUS_UPDATE_DEFINITIONS, HC.VIDEO_AVI, HC.VIDEO_FLV, HC.VIDEO_MOV, HC.VIDEO_MP4, HC.VIDEO_MKV, HC.VIDEO_MPEG, HC.VIDEO_WEBM, HC.VIDEO_WMV, HC.AUDIO_MP3, HC.AUDIO_OGG, HC.AUDIO_FLAC, HC.AUDIO_WMA )
            
            for mime in mimes_in_correct_order:
                
                items = self._new_options.GetMediaViewOptions( mime )
                
                data = [ mime ] + list( items )
                
                ( display_tuple, sort_tuple, data ) = self._GetListCtrlData( data )
                
                self._media_viewer_options.Append( display_tuple, sort_tuple, data )
                
            
            self._media_viewer_options.SortListItems( col = 0 )
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            rows.append( ( 'Start animations this % in: ', self._animation_start_position ) )
            rows.append( ( 'Disable OpenCV for gifs: ', self._disable_cv_for_gifs ) )
            rows.append( ( 'Load images with PIL: ', self._load_images_with_pil ) )
            rows.append( ( 'Prefer system FFMPEG: ', self._use_system_ffmpeg ) )
            rows.append( ( 'Media zooms: ', self._media_zooms ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self._media_viewer_panel.AddF( self._media_viewer_options, CC.FLAGS_EXPAND_BOTH_WAYS )
            self._media_viewer_panel.AddF( self._media_viewer_edit_button, CC.FLAGS_LONE_BUTTON )
            
            vbox.AddF( self._media_viewer_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
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
            
            try:
                
                media_zooms = [ float( media_zoom ) for media_zoom in self._media_zooms.GetValue().split( ',' ) ]
                
                if len( media_zooms ) > 0:
                    
                    self._new_options.SetMediaZooms( media_zooms )
                    
                
            except ValueError:
                
                HydrusData.ShowText( 'Could not parse those zooms, so they were not saved!' )
                
            
            for data in self._media_viewer_options.GetObjects():
                
                data = list( data )
                
                mime = data[0]
                
                value = data[1:]
                
                self._new_options.SetMediaViewOptions( mime, value )
                
            
        
    
    class _ShortcutsPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._shortcuts = ClientGUICommon.SaneListCtrl( self, 480, [ ( 'modifier', 120 ), ( 'key', 120 ), ( 'action', -1 ) ], delete_key_callback = self.DeleteShortcuts, activation_callback = self.EditShortcuts )
            
            self._shortcuts_add = wx.Button( self, label = 'add' )
            self._shortcuts_add.Bind( wx.EVT_BUTTON, self.EventAdd )
            
            self._shortcuts_edit = wx.Button( self, label = 'edit' )
            self._shortcuts_edit.Bind( wx.EVT_BUTTON, self.EventEdit )
            
            self._shortcuts_delete = wx.Button( self, label = 'delete' )
            self._shortcuts_delete.Bind( wx.EVT_BUTTON, self.EventDelete )
            
            #
            
            for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items():
                
                for ( key, action ) in key_dict.items():
                    
                    ( pretty_modifier, pretty_key ) = ClientData.ConvertShortcutToPrettyShortcut( modifier, key )
                    
                    pretty_action = action
                    
                    self._shortcuts.Append( ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                    
                
            
            self._SortListCtrl()
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( wx.StaticText( self, label = 'These shortcuts are global to the main gui! You probably want to stick to function keys or ctrl + something!' ), CC.FLAGS_VCENTER )
            vbox.AddF( self._shortcuts, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._shortcuts_add, CC.FLAGS_BUTTON_SIZER )
            hbox.AddF( self._shortcuts_edit, CC.FLAGS_BUTTON_SIZER )
            hbox.AddF( self._shortcuts_delete, CC.FLAGS_BUTTON_SIZER )
            
            vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def _SortListCtrl( self ): self._shortcuts.SortListItems( 2 )
        
        def DeleteShortcuts( self ):
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._shortcuts.RemoveAllSelected()
                    
                
            
        
        def EditShortcuts( self ):
        
            indices = self._shortcuts.GetAllSelected()
            
            for index in indices:
                
                ( modifier, key, action ) = self._shortcuts.GetClientData( index )
                
                with ClientGUIDialogs.DialogInputShortcut( self, modifier, key, action ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( modifier, key, action ) = dlg.GetInfo()
                        
                        ( pretty_modifier, pretty_key ) = ClientData.ConvertShortcutToPrettyShortcut( modifier, key )
                        
                        pretty_action = action
                        
                        self._shortcuts.UpdateRow( index, ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                        
                        self._SortListCtrl()
                        
                    
                
            
        
        def EventAdd( self, event ):
            
            with ClientGUIDialogs.DialogInputShortcut( self ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( modifier, key, action ) = dlg.GetInfo()
                    
                    ( pretty_modifier, pretty_key ) = ClientData.ConvertShortcutToPrettyShortcut( modifier, key )
                    
                    pretty_action = action
                    
                    self._shortcuts.Append( ( pretty_modifier, pretty_key, pretty_action ), ( modifier, key, action ) )
                    
                    self._SortListCtrl()
                    
                
            
        
        def EventDelete( self, event ):
            
            self.DeleteShortcuts()
            
        
        def EventEdit( self, event ):
            
            self.EditShortcuts()
            
        
        def UpdateOptions( self ):
            
            shortcuts = {}
            
            shortcuts[ wx.ACCEL_NORMAL ] = {}
            shortcuts[ wx.ACCEL_CTRL ] = {}
            shortcuts[ wx.ACCEL_ALT ] = {}
            shortcuts[ wx.ACCEL_SHIFT ] = {}
            
            for ( modifier, key, action ) in self._shortcuts.GetClientData(): shortcuts[ modifier ][ key ] = action
            
            HC.options[ 'shortcuts' ] = shortcuts
            
        
    
    class _SortCollectPanel( wx.Panel ):
        
        def __init__( self, parent ):
            
            wx.Panel.__init__( self, parent )
            
            self._default_sort = ClientGUICommon.ChoiceSort( self )
            
            self._sort_fallback = ClientGUICommon.ChoiceSort( self )
            
            self._default_collect = ClientGUICommon.CheckboxCollect( self )
            
            self._sort_by = wx.ListBox( self )
            self._sort_by.Bind( wx.EVT_LEFT_DCLICK, self.EventRemoveSortBy )
            
            self._new_sort_by = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
            self._new_sort_by.Bind( wx.EVT_KEY_DOWN, self.EventKeyDownSortBy )
            
            #
            
            try:
                
                self._default_sort.SetSelection( HC.options[ 'default_sort' ] )
                
            except:
                
                self._default_sort.SetSelection( 0 )
                
            
            try:
                
                self._sort_fallback.SetSelection( HC.options[ 'sort_fallback' ] )
                
            except:
                
                self._sort_fallback.SetSelection( 0 )
                
            
            for ( sort_by_type, sort_by ) in HC.options[ 'sort_by' ]:
                
                self._sort_by.Append( '-'.join( sort_by ), sort_by )
                
            
            #
            
            rows = []
            
            rows.append( ( 'Default sort: ', self._default_sort ) )
            rows.append( ( 'Secondary sort (when primary gives two equal values): ', self._sort_fallback ) )
            rows.append( ( 'Default collect: ', self._default_collect ) )
            
            gridbox = ClientGUICommon.WrapInGrid( self, rows )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            sort_by_text = 'You can manage new namespace sorting schemes here.'
            sort_by_text += os.linesep
            sort_by_text += 'The client will sort media by comparing their namespaces, moving from left to right until an inequality is found.'
            sort_by_text += os.linesep
            sort_by_text += 'Any changes will be shown in the sort-by dropdowns of any new pages you open.'
            
            vbox.AddF( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            vbox.AddF( wx.StaticText( self, label = sort_by_text ), CC.FLAGS_VCENTER )
            vbox.AddF( self._sort_by, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._new_sort_by, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def EventKeyDownSortBy( self, event ):
            
            if event.KeyCode in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
                
                sort_by_string = self._new_sort_by.GetValue()
                
                if sort_by_string != '':
                    
                    try: sort_by = sort_by_string.split( '-' )
                    except:
                        
                        wx.MessageBox( 'Could not parse that sort by string!' )
                        
                        return
                        
                    
                    self._sort_by.Append( sort_by_string, sort_by )
                    
                    self._new_sort_by.SetValue( '' )
                    
                
            else: event.Skip()
            
        
        def EventRemoveSortBy( self, event ):
            
            selection = self._sort_by.GetSelection()
            
            if selection != wx.NOT_FOUND: self._sort_by.Delete( selection )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'default_sort' ] = self._default_sort.GetSelection() 
            HC.options[ 'sort_fallback' ] = self._sort_fallback.GetSelection()
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
            
            vbox.AddF( self._play_dumper_noises, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            self.SetSizer( vbox )
            
        
        def UpdateOptions( self ):
            
            HC.options[ 'play_dumper_noises' ] = self._play_dumper_noises.GetValue()
            
        
    
    class _SpeedAndMemoryPanel( wx.Panel ):
        
        def __init__( self, parent, new_options ):
            
            wx.Panel.__init__( self, parent )
            
            self._new_options = new_options
            
            disk_panel = ClientGUICommon.StaticBox( self, 'disk cache' )
            
            self._disk_cache_init_period = ClientGUICommon.NoneableSpinCtrl( disk_panel, 'max disk cache init period', none_phrase = 'do not run', min = 1, max = 120 )
            self._disk_cache_init_period.SetToolTipString( 'When the client boots, it can speed up operation by reading the front of the database into memory. This sets the max number of seconds it can spend doing that.' )
            
            self._disk_cache_maintenance_mb = ClientGUICommon.NoneableSpinCtrl( disk_panel, 'disk cache maintenance (MB)', none_phrase = 'do not keep db cached', min = 32, max = 65536 )
            self._disk_cache_maintenance_mb.SetToolTipString( 'The client can regularly check the front of its database is cached in memory. This represents how many megabytes it will ensure are cached.' )
            
            #
            
            media_panel = ClientGUICommon.StaticBox( self, 'thumbnail size and media cache' )
            
            self._thumbnail_width = wx.SpinCtrl( media_panel, min = 20, max = 200 )
            self._thumbnail_width.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._thumbnail_height = wx.SpinCtrl( media_panel, min = 20, max = 200 )
            self._thumbnail_height.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._thumbnail_cache_size = wx.SpinCtrl( media_panel, min = 5, max = 3000 )
            self._thumbnail_cache_size.Bind( wx.EVT_SPINCTRL, self.EventThumbnailsUpdate )
            
            self._estimated_number_thumbnails = wx.StaticText( media_panel, label = '' )
            
            self._fullscreen_cache_size = wx.SpinCtrl( media_panel, min = 25, max = 3000 )
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
            self._num_autocomplete_chars.SetToolTipString( 'how many characters you enter before the gui fetches autocomplete results from the db. (otherwise, it will only fetch exact matches)' + os.linesep + 'increase this if you find autocomplete results are slow' )
            
            self._fetch_ac_results_automatically = wx.CheckBox( ac_panel )
            self._fetch_ac_results_automatically.Bind( wx.EVT_CHECKBOX, self.EventFetchAuto )
            
            self._autocomplete_long_wait = wx.SpinCtrl( ac_panel, min = 0, max = 10000 )
            self._autocomplete_long_wait.SetToolTipString( 'how long the gui will typically wait, after you enter a character, before it queries the db with what you have entered so far' )
            
            self._autocomplete_short_wait_chars = wx.SpinCtrl( ac_panel, min = 1, max = 100 )
            self._autocomplete_short_wait_chars.SetToolTipString( 'how many characters you enter before the gui starts waiting the short time before querying the db' )
            
            self._autocomplete_short_wait = wx.SpinCtrl( ac_panel, min = 0, max = 10000 )
            self._autocomplete_short_wait.SetToolTipString( 'how long the gui will typically wait, after you enter a lot of characters, before it queries the db with what you have entered so far' )
            
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
            
            disk_panel.AddF( self._disk_cache_init_period, CC.FLAGS_EXPAND_PERPENDICULAR )
            disk_panel.AddF( self._disk_cache_maintenance_mb, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.AddF( disk_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            thumbnails_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            thumbnails_sizer.AddF( self._thumbnail_cache_size, CC.FLAGS_VCENTER )
            thumbnails_sizer.AddF( self._estimated_number_thumbnails, CC.FLAGS_VCENTER )
            
            fullscreens_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            fullscreens_sizer.AddF( self._fullscreen_cache_size, CC.FLAGS_VCENTER )
            fullscreens_sizer.AddF( self._estimated_number_fullscreens, CC.FLAGS_VCENTER )
            
            video_buffer_sizer = wx.BoxSizer( wx.HORIZONTAL )
            
            video_buffer_sizer.AddF( self._video_buffer_size_mb, CC.FLAGS_VCENTER )
            video_buffer_sizer.AddF( self._estimated_number_video_frames, CC.FLAGS_VCENTER )
            
            rows = []
            
            rows.append( ( 'Thumbnail width: ', self._thumbnail_width ) )
            rows.append( ( 'Thumbnail height: ', self._thumbnail_height ) )
            rows.append( ( 'MB memory reserved for thumbnail cache: ', thumbnails_sizer ) )
            rows.append( ( 'MB memory reserved for media viewer cache: ', fullscreens_sizer ) )
            
            gridbox = ClientGUICommon.WrapInGrid( media_panel, rows )
            
            media_panel.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.AddF( media_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'Hydrus video rendering is CPU intensive.'
            text += os.linesep
            text += 'If you have a lot of memory, you can set a generous potential video buffer to compensate.'
            text += os.linesep
            text += 'If the video buffer can hold an entire video, it only needs to be rendered once and will loop smoothly.'
            
            buffer_panel.AddF( wx.StaticText( buffer_panel, label = text ), CC.FLAGS_VCENTER )
            
            rows = []
            
            rows.append( ( 'MB memory for video buffer: ', video_buffer_sizer ) )
            
            gridbox = ClientGUICommon.WrapInGrid( buffer_panel, rows )
            
            buffer_panel.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.AddF( buffer_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            text = 'If you disable automatic autocomplete results fetching, use Ctrl+Space to fetch results manually.'
            
            ac_panel.AddF( wx.StaticText( ac_panel, label = text ), CC.FLAGS_EXPAND_PERPENDICULAR )
            
            rows = []
            
            rows.append( ( 'Automatically fetch autocomplete results after a short delay: ', self._fetch_ac_results_automatically ) )
            rows.append( ( 'Autocomplete long wait character threshold: ', self._num_autocomplete_chars ) )
            rows.append( ( 'Autocomplete long wait (ms): ', self._autocomplete_long_wait ) )
            rows.append( ( 'Autocomplete short wait character threshold: ', self._autocomplete_short_wait_chars ) )
            rows.append( ( 'Autocomplete short wait (ms): ', self._autocomplete_short_wait ) )
            
            gridbox = ClientGUICommon.WrapInGrid( ac_panel, rows )
            
            ac_panel.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.AddF( ac_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Forced system:limit for all searches: ', self._forced_search_limit ) )
            
            gridbox = ClientGUICommon.WrapInGrid( misc_panel, rows )
            
            misc_panel.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.AddF( misc_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            self.SetSizer( vbox )
            
            #
            
            self.EventFetchAuto( None )
            self.EventFullscreensUpdate( None )
            self.EventThumbnailsUpdate( None )
            self.EventVideoBufferUpdate( None )
            
            wx.CallAfter( self.Layout ) # draws the static texts correctly
            
        
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
            
            self._apply_all_parents_to_all_services = wx.CheckBox( general_panel )
            
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
            
            tag_services = HydrusGlobals.client_controller.GetServicesManager().GetServices( ( HC.TAG_REPOSITORY, ) )
            
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
            
            script_names = HydrusGlobals.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_PARSE_ROOT_FILE_LOOKUP )
            
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
            
            services = HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.TAG_SERVICES )
            
            for service in services:
                
                self._default_tag_repository.Append( service.GetName(), service.GetServiceKey() )
                
                self._default_tag_service_search_page.Append( service.GetName(), service.GetServiceKey() )
                
            
            default_tag_repository_key = HC.options[ 'default_tag_repository' ]
            
            self._default_tag_repository.SelectClientData( default_tag_repository_key )
            
            self._default_tag_service_search_page.SelectClientData( new_options.GetKey( 'default_tag_service_search_page' ) )
            
            self._show_all_tags_in_autocomplete.SetValue( HC.options[ 'show_all_tags_in_autocomplete' ] )
            
            self._apply_all_parents_to_all_services.SetValue( self._new_options.GetBoolean( 'apply_all_parents_to_all_services' ) )
            
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
            rows.append( ( 'Suggest all parents for all services: ', self._apply_all_parents_to_all_services ) )
            
            gridbox = ClientGUICommon.WrapInGrid( general_panel, rows )
            
            general_panel.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.AddF( general_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            rows = []
            
            rows.append( ( 'Show namespaces: ', self._show_namespaces ) )
            rows.append( ( 'If shown, namespace connecting string: ', self._namespace_connector ) )
            
            gridbox = ClientGUICommon.WrapInGrid( render_panel, rows )
            
            render_panel.AddF( render_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            render_panel.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            vbox.AddF( render_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            #
            
            panel_vbox = wx.BoxSizer( wx.VERTICAL )
            
            panel_vbox.AddF( self._suggested_favourites_services, CC.FLAGS_EXPAND_PERPENDICULAR )
            panel_vbox.AddF( self._suggested_favourites, CC.FLAGS_EXPAND_BOTH_WAYS )
            panel_vbox.AddF( self._suggested_favourites_input, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_favourites_panel.SetSizer( panel_vbox )
            
            #
            
            panel_vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            rows.append( ( 'Show related tags on single-file manage tags windows: ', self._show_related_tags ) )
            rows.append( ( 'Initial search duration (ms): ', self._related_tags_search_1_duration_ms ) )
            rows.append( ( 'Medium search duration (ms): ', self._related_tags_search_2_duration_ms ) )
            rows.append( ( 'Thorough search duration (ms): ', self._related_tags_search_3_duration_ms ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_related_panel, rows )
            
            panel_vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_related_panel.SetSizer( panel_vbox )
            
            #
            
            panel_vbox = wx.BoxSizer( wx.VERTICAL )
            
            rows = []
            
            rows.append( ( 'Show file lookup scripts on single-file manage tags windows: ', self._show_file_lookup_script_tags ) )
            rows.append( ( 'Favourite file lookup script: ', self._favourite_file_lookup_script ) )
            
            gridbox = ClientGUICommon.WrapInGrid( suggested_tags_file_lookup_script_panel, rows )
            
            panel_vbox.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            suggested_tags_file_lookup_script_panel.SetSizer( panel_vbox )
            
            #
            
            panel_vbox = wx.BoxSizer( wx.VERTICAL )
            
            panel_vbox.AddF( self._num_recent_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            
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
            
            suggested_tags_panel.AddF( gridbox, CC.FLAGS_EXPAND_PERPENDICULAR )
            suggested_tags_panel.AddF( suggest_tags_panel_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            vbox.AddF( suggested_tags_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
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
            
            self._new_options.SetKey( 'default_tag_service_search_page', self._default_tag_service_search_page.GetChoice() )
            
            self._new_options.SetInteger( 'suggested_tags_width', self._suggested_tags_width.GetValue() )
            self._new_options.SetNoneableString( 'suggested_tags_layout', self._suggested_tags_layout.GetChoice() )
            
            self._new_options.SetBoolean( 'apply_all_parents_to_all_services', self._apply_all_parents_to_all_services.GetValue() )
            
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
            
            HydrusGlobals.client_controller.WriteSynchronous( 'save_options', HC.options )
            
            HydrusGlobals.client_controller.WriteSynchronous( 'serialisable', self._new_options )
            
        except:
            
            wx.MessageBox( traceback.format_exc() )
            
        

class ManageServerServicesPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent, service_key ):
        
        self._clientside_admin_service = HydrusGlobals.client_controller.GetServicesManager().GetService( service_key )
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        self._deletee_service_keys = []
        
        columns = [ ( 'port', 80 ), ( 'name', -1 ), ( 'type', 220 ) ]
        
        self._services_listctrl = ClientGUICommon.SaneListCtrlForSingleObject( self, 120, columns, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
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
            
        
        self._services_listctrl.SortListItems( 0 )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._add_button, CC.FLAGS_VCENTER )
        hbox.AddF( self._edit_button, CC.FLAGS_VCENTER )
        hbox.AddF( self._delete_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._services_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( hbox, CC.FLAGS_SMALL_INDENT )
        
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
        
        with HydrusGlobals.dirty_object_lock:
            
            HydrusGlobals.client_controller.WriteSynchronous( 'update_server_services', admin_service_key, services, service_keys_to_access_keys, self._deletee_service_keys )
            
            HydrusGlobals.client_controller.RefreshServices()
            
        
    
class ManageSubscriptionsPanel( ClientGUIScrolledPanels.ManagePanel ):
    
    def __init__( self, parent ):
        
        ClientGUIScrolledPanels.ManagePanel.__init__( self, parent )
        
        subscriptions = HydrusGlobals.client_controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION )
        
        #
        
        columns = [ ( 'name', -1 ), ( 'site', 80 ), ( 'period', 80 ), ( 'last checked', 100 ), ( 'recent error?', 100 ), ( 'urls', 60 ), ( 'failures', 60 ), ( 'paused', 80 ), ( 'check now?', 100 ) ]
        
        self._subscriptions = ClientGUICommon.SaneListCtrlForSingleObject( self, 300, columns, delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        self._add = ClientGUICommon.BetterButton( self, 'add', self.Add )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'to clipboard', 'Serialise the script and put it on your clipboard.', self.ExportToClipboard ) )
        menu_items.append( ( 'normal', 'to png', 'Serialise the script and encode it to an image file you can easily share with other hydrus users.', self.ExportToPng ) )
        
        self._export = ClientGUICommon.MenuButton( self, 'export', menu_items )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'from clipboard', 'Load a script from text in your clipboard.', self.ImportFromClipboard ) )
        menu_items.append( ( 'normal', 'from png', 'Load a script from an encoded png.', self.ImportFromPng ) )
        
        self._import = ClientGUICommon.MenuButton( self, 'import', menu_items )
        
        self._duplicate = ClientGUICommon.BetterButton( self, 'duplicate', self.Duplicate )
        self._edit = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        self._delete = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        self._retry_failures = ClientGUICommon.BetterButton( self, 'retry failures', self.RetryFailures )
        self._pause_resume = ClientGUICommon.BetterButton( self, 'pause/resume', self.PauseResume )
        self._check_now = ClientGUICommon.BetterButton( self, 'check now', self.CheckNow )
        self._reset = ClientGUICommon.BetterButton( self, 'reset', self.Reset )
        
        #
        
        for subscription in subscriptions:
            
            ( display_tuple, sort_tuple ) = self._ConvertSubscriptionToTuples( subscription )
            
            self._subscriptions.Append( display_tuple, sort_tuple, subscription )
            
        
        #
        
        text_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        text_hbox.AddF( wx.StaticText( self, label = 'For more information about subscriptions, please check' ), CC.FLAGS_VCENTER )
        text_hbox.AddF( wx.HyperlinkCtrl( self, id = -1, label = 'here', url = 'file://' + HC.HELP_DIR + '/getting_started_subscriptions.html' ), CC.FLAGS_VCENTER )
        
        action_box = wx.BoxSizer( wx.HORIZONTAL )
        
        action_box.AddF( self._retry_failures, CC.FLAGS_VCENTER )
        action_box.AddF( self._pause_resume, CC.FLAGS_VCENTER )
        action_box.AddF( self._check_now, CC.FLAGS_VCENTER )
        action_box.AddF( self._reset, CC.FLAGS_VCENTER )
        
        button_box = wx.BoxSizer( wx.HORIZONTAL )
        
        button_box.AddF( self._add, CC.FLAGS_VCENTER )
        button_box.AddF( self._export, CC.FLAGS_VCENTER )
        button_box.AddF( self._import, CC.FLAGS_VCENTER )
        button_box.AddF( self._duplicate, CC.FLAGS_VCENTER )
        button_box.AddF( self._edit, CC.FLAGS_VCENTER )
        button_box.AddF( self._delete, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( text_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._subscriptions, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( action_box, CC.FLAGS_BUTTON_SIZER )
        vbox.AddF( button_box, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _ConvertSubscriptionToTuples( self, subscription ):
        
        ( name, gallery_identifier, gallery_stream_identifiers, query, period, get_tags_if_url_known_and_file_redundant, initial_file_limit, periodic_file_limit, paused, import_file_options, import_tag_options, last_checked, last_error, check_now, seed_cache ) = subscription.ToTuple()
        
        pretty_site = gallery_identifier.ToString()
        
        pretty_last_checked = HydrusData.ConvertTimestampToPrettySync( last_checked )
        
        pretty_period = HydrusData.ConvertTimeDeltaToPrettyString( period )
        
        error_next_check_time = last_error + HC.UPDATE_DURATION
        
        if HydrusData.TimeHasPassed( error_next_check_time ):
            
            pretty_error = ''
            
        else:
            
            pretty_error = 'yes'
            
        
        num_urls = seed_cache.GetSeedCount()
        pretty_urls = HydrusData.ConvertIntToPrettyString( num_urls )
        
        num_failures = seed_cache.GetSeedCount( CC.STATUS_FAILED )
        pretty_failures = HydrusData.ConvertIntToPrettyString( num_failures )
        
        if paused:
            
            pretty_paused = 'yes'
            
        else:
            
            pretty_paused = ''
            
        
        if check_now:
            
            pretty_check_now = 'yes'
            
        else:
            
            pretty_check_now = ''
            
        
        display_tuple = ( name, pretty_site, pretty_period, pretty_last_checked, pretty_error, pretty_urls, pretty_failures, pretty_paused, pretty_check_now )
        sort_tuple = ( name, pretty_site, period, last_checked, pretty_error, num_urls, num_failures, paused, check_now )
        
        return ( display_tuple, sort_tuple )
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for subscription in self._subscriptions.GetObjects( only_selected = True ):
            
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
            
            if isinstance( obj, ClientImporting.Subscription ):
                
                subscription = obj
                
                self._subscriptions.SetNonDupeName( subscription )
                
                ( display_tuple, sort_tuple ) = self._ConvertSubscriptionToTuples( subscription )
                
                self._subscriptions.Append( display_tuple, sort_tuple, subscription )
                
            else:
                
                wx.MessageBox( 'That was not a script--it was a: ' + type( obj ).__name__ )
                
            
        
    
    def Add( self ):
        
        empty_subscription = ClientImporting.Subscription( 'new subscription' )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit subscription' ) as dlg_edit:
            
            panel = ClientGUIScrolledPanelsEdit.EditSubscriptionPanel( dlg_edit, empty_subscription )
            
            dlg_edit.SetPanel( panel )
            
            if dlg_edit.ShowModal() == wx.ID_OK:
                
                new_subscription = panel.GetValue()
                
                self._subscriptions.SetNonDupeName( new_subscription )
                
                ( display_tuple, sort_tuple ) = self._ConvertSubscriptionToTuples( new_subscription )
                
                self._subscriptions.Append( display_tuple, sort_tuple, new_subscription )
                
            
        
    
    def CheckNow( self ):
        
        for i in self._subscriptions.GetAllSelected():
            
            subscription = self._subscriptions.GetObject( i )
            
            subscription.CheckNow()
            
            ( display_tuple, sort_tuple ) = self._ConvertSubscriptionToTuples( subscription )
            
            self._subscriptions.UpdateRow( i, display_tuple, sort_tuple, subscription )
            
        
    
    def CommitChanges( self ):
        
        subscriptions = self._subscriptions.GetObjects()
        
        HydrusGlobals.client_controller.Write( 'serialisables_overwrite', [ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ], subscriptions )
        
        HydrusGlobals.client_controller.pub( 'notify_new_subscriptions' )
        
    
    def Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._subscriptions.RemoveAllSelected()
                
            
        
    
    def Duplicate( self ):
        
        subs_to_dupe = []
        
        for subscription in self._subscriptions.GetObjects( only_selected = True ):
            
            subs_to_dupe.append( subscription )
            
        
        for subscription in subs_to_dupe:
            
            dupe_subscription = subscription.Duplicate()
            
            self._subscriptions.SetNonDupeName( dupe_subscription )
            
            ( display_tuple, sort_tuple ) = self._ConvertSubscriptionToTuples( dupe_subscription )
            
            self._subscriptions.Append( display_tuple, sort_tuple, dupe_subscription )
            
        
    
    def Edit( self ):
        
        for index in self._subscriptions.GetAllSelected():
            
            subscription = self._subscriptions.GetObject( index )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit subscription' ) as dlg:
                
                original_name = subscription.GetName()
                
                panel = ClientGUIScrolledPanelsEdit.EditSubscriptionPanel( dlg, subscription )
                
                dlg.SetPanel( panel )
                
                result = dlg.ShowModal()
                
                if result == wx.ID_OK:
                    
                    edited_subscription = panel.GetValue()
                    
                    if edited_subscription.GetName() != original_name:
                        
                        self._subscriptions.SetNonDupeName( edited_subscription )
                        
                    
                    ( display_tuple, sort_tuple ) = self._ConvertSubscriptionToTuples( edited_subscription )
                    
                    self._subscriptions.UpdateRow( index, display_tuple, sort_tuple, edited_subscription )
                    
                elif result == wx.ID_CANCEL:
                    
                    break
                    
                
                
            
        
    
    def ExportToClipboard( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def ExportToPng( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            with ClientGUITopLevelWindows.DialogNullipotent( self, 'export to png' ) as dlg:
                
                panel = ClientGUISerialisable.PngExportPanel( dlg, export_object )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
        
    
    def ImportFromClipboard( self ):
        
        if wx.TheClipboard.Open():
            
            data = wx.TextDataObject()
            
            wx.TheClipboard.GetData( data )
            
            wx.TheClipboard.Close()
            
            raw_text = data.GetText()
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( raw_text )
                
                self._ImportObject( obj )
                
            except Exception as e:
                
                wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            
        else:
            
            wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
    
    def ImportFromPng( self ):
        
        with wx.FileDialog( self, 'select the png with the encoded script', wildcard = 'PNG (*.png)|*.png' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg.GetPath() )
                
                try:
                    
                    payload = ClientSerialisable.LoadFromPng( path )
                    
                except Exception as e:
                    
                    wx.MessageBox( HydrusData.ToUnicode( e ) )
                    
                    return
                    
                
                try:
                    
                    obj = HydrusSerialisable.CreateFromNetworkString( payload )
                    
                    self._ImportObject( obj )
                    
                except:
                    
                    wx.MessageBox( 'I could not understand what was encoded in the png!' )
                    
                
            
        
    
    def PauseResume( self ):
        
        for i in self._subscriptions.GetAllSelected():
            
            subscription = self._subscriptions.GetObject( i )
            
            subscription.PauseResume()
            
            ( display_tuple, sort_tuple ) = self._ConvertSubscriptionToTuples( subscription )
            
            self._subscriptions.UpdateRow( i, display_tuple, sort_tuple, subscription )
            
        
    
    def Reset( self ):
        
        message = '''Resetting these subscriptions will delete all their remembered urls, meaning when they next run, they will try to download them all over again. This may be expensive in time and data. Only do it if you are willing to wait. Do you want to do it?'''
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                for i in self._subscriptions.GetAllSelected():
                    
                    subscription = self._subscriptions.GetObject( i )
                    
                    subscription.Reset()
                    
                    ( display_tuple, sort_tuple ) = self._ConvertSubscriptionToTuples( subscription )
                    
                    self._subscriptions.UpdateRow( i, display_tuple, sort_tuple, subscription )
                    
                
            
        
    
    def RetryFailures( self ):
        
        for i in self._subscriptions.GetAllSelected():
            
            subscription = self._subscriptions.GetObject( i )
            
            seed_cache = subscription.GetSeedCache()
            
            failed_seeds = seed_cache.GetSeeds( CC.STATUS_FAILED )
            
            for seed in failed_seeds:
                
                seed_cache.UpdateSeedStatus( seed, CC.STATUS_UNKNOWN )
                
                ( display_tuple, sort_tuple ) = self._ConvertSubscriptionToTuples( subscription )
                
                self._subscriptions.UpdateRow( i, display_tuple, sort_tuple, subscription )
                
            
        
    
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
        
        services = HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.TAG_SERVICES )
        
        for service in services:
            
            service_key = service.GetServiceKey()
            name = service.GetName()
            
            page = self._Panel( self._tag_repositories, self._file_service_key, service.GetServiceKey(), self._current_media, self._immediate_commit, canvas_key = self._canvas_key )
            
            self._tag_repositories.AddPage( name, service_key, page )
            
        
        default_tag_repository_key = HC.options[ 'default_tag_repository' ]
        
        self._tag_repositories.Select( default_tag_repository_key )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._tag_repositories, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_CHAR_HOOK, self.EventCharHook )
        
        self.RefreshAcceleratorTable()
        
        if self._canvas_key is not None:
            
            HydrusGlobals.client_controller.sub( self, 'CanvasHasNewMedia', 'canvas_new_display_media' )
            
        
    
    def _SetSearchFocus( self ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        if page is not None:
            
            page.SetTagBoxFocus()
            
        
    
    def CanvasHasNewMedia( self, canvas_key, new_media_singleton ):
        
        if canvas_key == self._canvas_key:
            
            self._current_media = ( new_media_singleton.Duplicate(), )
            
            for page in self._tag_repositories.GetActivePages():
                
                page.SetMedia( self._current_media )
                
            
        
    
    def CommitChanges( self ):
        
        service_keys_to_content_updates = {}
        
        for page in self._tag_repositories.GetActivePages():
            
            ( service_key, content_updates ) = page.GetContentUpdates()
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
        
    
    def EventCharHook( self, event ):
        
        # the char hook event goes up. if it isn't skipped all the way, the subsequent text event will never occur
        # however we don't want the char hook going all the way up sometimes!
        
        if not HC.PLATFORM_LINUX:
            
            # If I let this go uncaught, it propagates to the media viewer above, so an Enter or a '+' closes the window or zooms in!
            # The DoAllowNextEvent tells wx to gen regular key_down/char events so our text box gets them like normal, despite catching the event here
            
            if event.KeyCode == wx.WXK_ESCAPE:
                
                event.Skip()
                
            else:
                
                event.DoAllowNextEvent()
                
            
        else:
            
            # Top jej, the events weren't being generated after all in Linux, so here's a possibly borked patch for that:
            
            if event.KeyCode != wx.WXK_ESCAPE:
                
                HydrusGlobals.do_not_catch_char_hook = True
                
            
            event.Skip()
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'manage_tags':
                
                wx.PostEvent( self.GetParent(), wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'ok' ) ) )
                
            elif command == 'set_search_focus':
                
                self._SetSearchFocus()
                
            elif command == 'canvas_show_next':
                
                if self._canvas_key is not None:
                    
                    HydrusGlobals.client_controller.pub( 'canvas_show_next', self._canvas_key )
                    
                
            elif command == 'canvas_show_previous':
                
                if self._canvas_key is not None:
                    
                    HydrusGlobals.client_controller.pub( 'canvas_show_previous', self._canvas_key )
                    
                
            else:
                
                event.Skip()
                
            
        
    
    def EventServiceChanged( self, event ):
        
        page = self._tag_repositories.GetCurrentPage()
        
        if page is not None:
            
            wx.CallAfter( page.SetTagBoxFocus )
            
        
    
    def RefreshAcceleratorTable( self ):
        
        interested_actions = [ 'manage_tags', 'set_search_focus' ]
        
        entries = []
        
        for ( modifier, key_dict ) in HC.options[ 'shortcuts' ].items():
            
            entries.extend( [ ( modifier, key, ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetPermanentId( action ) ) for ( key, action ) in key_dict.items() if action in interested_actions ] )
            
        
        self.SetAcceleratorTable( wx.AcceleratorTable( entries ) )
        
    
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
                
                self._service = HydrusGlobals.client_controller.GetServicesManager().GetService( tag_service_key )
                
            
            self._tags_box_sorter = ClientGUICommon.StaticBoxSorterForListBoxTags( self, 'tags' )
            
            self._tags_box = ClientGUIListBoxes.ListBoxTagsSelectionTagsDialog( self._tags_box_sorter, self.AddTags, self.RemoveTags )
            
            self._tags_box_sorter.SetTagsBox( self._tags_box )
            
            self._new_options = HydrusGlobals.client_controller.GetNewOptions()
            
            self._add_parents_checkbox = wx.CheckBox( self._tags_box_sorter, label = 'auto-add entered tags\' parents' )
            self._add_parents_checkbox.SetValue( self._new_options.GetBoolean( 'add_parents_on_manage_tags' ) )
            self._add_parents_checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckAddParents )
            
            self._collapse_siblings_checkbox = wx.CheckBox( self._tags_box_sorter, label = 'auto-replace entered siblings' )
            self._collapse_siblings_checkbox.SetValue( self._new_options.GetBoolean( 'replace_siblings_on_manage_tags' ) )
            self._collapse_siblings_checkbox.Bind( wx.EVT_CHECKBOX, self.EventCheckCollapseSiblings )
            
            self._show_deleted_checkbox = wx.CheckBox( self._tags_box_sorter, label = 'show deleted' )
            self._show_deleted_checkbox.Bind( wx.EVT_CHECKBOX, self.EventShowDeleted )
            
            self._tags_box_sorter.AddF( self._add_parents_checkbox, CC.FLAGS_LONE_BUTTON )
            self._tags_box_sorter.AddF( self._collapse_siblings_checkbox, CC.FLAGS_LONE_BUTTON )
            self._tags_box_sorter.AddF( self._show_deleted_checkbox, CC.FLAGS_LONE_BUTTON )
            
            expand_parents = True
            
            self._add_tag_box = ClientGUIACDropdown.AutoCompleteDropdownTagsWrite( self, self.EnterTags, expand_parents, self._file_service_key, self._tag_service_key, null_entry_callable = self.Ok )
            
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
                    
                
            
            copy_paste_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            copy_paste_hbox.AddF( self._copy_tags, CC.FLAGS_VCENTER )
            copy_paste_hbox.AddF( self._paste_tags, CC.FLAGS_VCENTER )
            
            advanced_hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            advanced_hbox.AddF( self._remove_tags, CC.FLAGS_VCENTER )
            advanced_hbox.AddF( self._advanced_content_update_button, CC.FLAGS_VCENTER )
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            vbox.AddF( self._tags_box_sorter, CC.FLAGS_EXPAND_BOTH_WAYS )
            vbox.AddF( self._add_tag_box, CC.FLAGS_EXPAND_PERPENDICULAR )
            vbox.AddF( copy_paste_hbox, CC.FLAGS_BUTTON_SIZER )
            vbox.AddF( advanced_hbox, CC.FLAGS_BUTTON_SIZER )
            vbox.AddF( self._modify_mappers, CC.FLAGS_LONE_BUTTON )
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._suggested_tags, CC.FLAGS_EXPAND_PERPENDICULAR )
            hbox.AddF( vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            
            #
            
            self.SetSizer( hbox )
            
        
        def _AddTags( self, tags, only_add = False, only_remove = False, forced_reason = None ):
            
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
                            
                            tag_parents_manager = HydrusGlobals.client_controller.GetManager( 'tag_parents' )
                            
                            parents = tag_parents_manager.GetParents( self._tag_service_key, tag )
                            
                            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, choice_action, ( parent, hashes ) ) for parent in parents ) )
                            
                        
                    
                
            
            if len( recent_tags ) > 0 and HydrusGlobals.client_controller.GetNewOptions().GetNoneableInteger( 'num_recent_tags' ) is not None:
                
                HydrusGlobals.client_controller.Write( 'push_recent_tags', self._tag_service_key, recent_tags )
                
            
            
            for m in self._media:
                
                for content_update in content_updates:
                    
                    m.GetMediaResult().ProcessContentUpdate( self._tag_service_key, content_update )
                    
                
            
            if self._immediate_commit:
                
                service_keys_to_content_updates = { self._tag_service_key : content_updates }
                
                HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                
            else:
                
                self._content_updates.extend( content_updates )
                
            
            self._tags_box.SetTagsByMedia( self._media, force_reload = True )
            
        
        def AddTags( self, tags, only_add = False ):
            
            if len( tags ) > 0:
                
                self._AddTags( tags, only_add = only_add )
                
            
        
        def EnterTags( self, tags, only_add = False ):
            
            if self._collapse_siblings_checkbox.GetValue():
                
                siblings_manager = HydrusGlobals.client_controller.GetManager( 'tag_siblings' )
                
                tags = siblings_manager.CollapseTags( self._tag_service_key, tags )
                
            
            if len( tags ) > 0:
                
                self._AddTags( tags, only_add = only_add )
                
            
        
        def EventAdvancedContentUpdate( self, event ):
            
            hashes = set()
            
            for m in self._media:
                
                hashes.update( m.GetHashes() )
                
            
            self.Ok()
        
            parent = self.GetTopLevelParent().GetParent()
            
            def do_it():
                
                with ClientGUIDialogs.DialogAdvancedContentUpdate( parent, self._tag_service_key, hashes ) as dlg:
                    
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
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
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
            
            if wx.TheClipboard.Open():
                
                data = wx.TextDataObject()
                
                wx.TheClipboard.GetData( data )
                
                wx.TheClipboard.Close()
                
                text = data.GetText()
                
                try:
                    
                    tags = HydrusData.DeserialisePrettyTags( text )
                    
                    tags = HydrusTags.CleanTags( tags )
                    
                    self.EnterTags( tags, only_add = True )
                    
                except: wx.MessageBox( 'I could not understand what was in the clipboard' )
                
            else: wx.MessageBox( 'I could not get permission to access the clipboard.' )
            
        
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
            
        
        def Ok( self ):
            
            wx.PostEvent( self, wx.CommandEvent( commandType = wx.wxEVT_COMMAND_MENU_SELECTED, winid = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'ok' ) ) )
            
        
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
            
        
    
