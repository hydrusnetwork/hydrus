from . import ClientAPI
from . import ClientConstants as CC
from . import ClientGUIAPI
from . import ClientGUICommon
from . import ClientGUIDialogs
from . import ClientGUIListCtrl
from . import ClientGUIScrolledPanelsReview
from . import ClientGUITopLevelWindows
from . import ClientPaths
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusNATPunch
from . import HydrusNetwork
from . import HydrusPaths
import os
import time
import wx

class IPFSDaemonStatusAndInteractionPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, service_callable ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'ipfs daemon' )
        
        self._is_running = False
        self._nocopy_enabled = False
        
        self._service_callable = service_callable
        
        self._running_status = ClientGUICommon.BetterStaticText( self )
        self._check_running_button = ClientGUICommon.BetterButton( self, 'check daemon', self._CheckRunning )
        self._nocopy_status = ClientGUICommon.BetterStaticText( self )
        self._check_nocopy = ClientGUICommon.BetterButton( self, 'check nocopy', self._CheckNoCopy )
        self._enable_nocopy = ClientGUICommon.BetterButton( self, 'enable nocopy', self._EnableNoCopy )
        
        self._check_running_button.Disable()
        self._check_nocopy.Disable()
        
        #
        
        gridbox = wx.FlexGridSizer( 2 )
        
        gridbox.AddGrowableCol( 1, 1 )
        
        gridbox.Add( self._check_running_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._running_status, CC.FLAGS_VCENTER )
        gridbox.Add( self._check_nocopy, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( self._nocopy_status, CC.FLAGS_VCENTER )
        gridbox.Add( self._enable_nocopy, CC.FLAGS_EXPAND_BOTH_WAYS )
        gridbox.Add( ( 20, 20 ), CC.FLAGS_VCENTER )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._CheckRunning()
        
    
    def _CheckNoCopy( self ):
        
        def wx_clean_up( result, nocopy_enabled ):
            
            if not self:
                
                return
                
            
            self._nocopy_status.SetLabelText( result )
            
            self._check_nocopy.Enable()
            
            self._nocopy_enabled = nocopy_enabled
            
            if self._nocopy_enabled:
                
                self._enable_nocopy.Disable()
                
            else:
                
                self._enable_nocopy.Enable()
                
            
        
        def do_it( service ):
            
            try:
                
                nocopy_enabled = service.GetNoCopyEnabled()
                
                if nocopy_enabled:
                    
                    result = 'Nocopy is enabled.'
                    
                else:
                    
                    result = 'Nocopy is not enabled.'
                    
                
            except Exception as e:
                
                result = 'Problem: {}'.format( str( e ) )
                
                nocopy_enabled = False
                
            finally:
                
                wx.CallAfter( wx_clean_up, result, nocopy_enabled )
                
            
        
        self._check_nocopy.Disable()
        
        self._nocopy_status.SetLabelText( 'checking\u2026' )
        
        service = self._service_callable()
        
        HG.client_controller.CallToThread( do_it, service )
        
    
    def _CheckRunning( self ):
        
        def wx_clean_up( result, is_running ):
            
            if not self:
                
                return
                
            
            self._running_status.SetLabelText( result )
            
            self._is_running = is_running
            
            self._check_running_button.Enable()
            
            if self._is_running:
                
                self._check_nocopy.Enable()
                
                self._CheckNoCopy()
                
            
        
        def do_it( service ):
            
            try:
                
                version = service.GetDaemonVersion()
                
                result = 'Running version {}.'.format( version )
                
                is_running = True
                
            except Exception as e:
                
                result = 'Problem: {}'.format( str( e ) )
                
                is_running = False
                
            finally:
                
                wx.CallAfter( wx_clean_up, result, is_running )
                
            
        
        self._check_running_button.Disable()
        self._check_nocopy.Disable()
        self._enable_nocopy.Disable()
        
        self._running_status.SetLabelText( 'checking\u2026' )
        
        service = self._service_callable()
        
        HG.client_controller.CallToThread( do_it, service )
        
    
    def _EnableNoCopy( self ):
        
        def wx_clean_up( success ):
            
            if not self:
                
                return
                
            
            if success:
                
                self._CheckNoCopy()
                
            else:
                
                wx.MessageBox( 'Unfortunately, was unable to set nocopy configuration.' )
                
                self._enable_nocopy.Enable()
                
            
        
        def do_it( service ):
            
            try:
                
                success = service.EnableNoCopy( True )
                
            except Exception as e:
                
                message = 'Problem: {}'.format( str( e ) )
                
                wx.CallAfter( wx.MessageBox, message )
                
                success = False
                
            finally:
                
                wx.CallAfter( wx_clean_up, success )
                
            
        
        self._enable_nocopy.Disable()
        
        service = self._service_callable()
        
        HG.client_controller.CallToThread( do_it, service )
        
    
class ReviewServicePanel( wx.Panel ):
    
    def __init__( self, parent, service ):
        
        wx.Panel.__init__( self, parent )
        
        self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_FRAMEBK ) )
        
        self._service = service
        
        service_type = self._service.GetServiceType()
        
        subpanels = []
        
        subpanels.append( self._ServicePanel( self, service ) )
        
        if service_type in HC.REMOTE_SERVICES:
            
            subpanels.append( self._ServiceRemotePanel( self, service ) )
            
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            subpanels.append( self._ServiceRestrictedPanel( self, service ) )
            
        
        if service_type in HC.FILE_SERVICES:
            
            subpanels.append( self._ServiceFilePanel( self, service ) )
            
        
        if self._service.GetServiceKey() == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
            
            subpanels.append( self._ServiceCombinedLocalFilesPanel( self, service ) )
            
        
        if self._service.GetServiceKey() == CC.TRASH_SERVICE_KEY:
            
            subpanels.append( self._ServiceTrashPanel( self, service ) )
            
        
        if service_type in HC.TAG_SERVICES:
            
            subpanels.append( self._ServiceTagPanel( self, service ) )
            
        
        if service_type in HC.RATINGS_SERVICES:
            
            subpanels.append( self._ServiceRatingPanel( self, service ) )
            
        
        if service_type in HC.REPOSITORIES:
            
            subpanels.append( self._ServiceRepositoryPanel( self, service ) )
            
        
        if service_type == HC.IPFS:
            
            subpanels.append( self._ServiceIPFSPanel( self, service ) )
            
        
        if service_type == HC.LOCAL_BOORU:
            
            subpanels.append( self._ServiceLocalBooruPanel( self, service ) )
            
        
        if service_type == HC.CLIENT_API_SERVICE:
            
            subpanels.append( self._ServiceClientAPIPanel( self, service ) )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        for panel in subpanels:
            
            vbox.Add( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.SetSizer( vbox )
        
    
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
        
    
    class _ServicePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'name and type' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._name_and_type = ClientGUICommon.BetterStaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.Add( self._name_and_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            name = self._service.GetName()
            service_type = self._service.GetServiceType()
            
            label = name + ' - ' + HC.service_string_lookup[ service_type ]
            
            self._name_and_type.SetLabelText( label )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceClientAPIPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'client api' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._service_status = ClientGUICommon.BetterStaticText( self )
            
            permissions_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            columns = [ ( 'name', -1 ), ( 'basic permissions', 36 ), ( 'advanced permissions', 36 ) ]
            
            self._permissions_list = ClientGUIListCtrl.BetterListCtrl( permissions_list_panel, 'client_api_permissions', 10, 36, columns, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
            
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
                
                wx.MessageBox( 'The service is not running, so you cannot add new access via the API!' )
                
                return
                
            
            title = 'waiting for API access permissions request'
            
            with ClientGUITopLevelWindows.DialogNullipotent( self, title ) as dlg:
                
                panel = ClientGUIAPI.CaptureAPIAccessPermissionsRequestPanel( dlg )
                
                dlg.SetPanel( panel )
                
                ClientAPI.last_api_permissions_request = None
                ClientAPI.api_request_dialog_open = True
                
                dlg.ShowModal()
                
                ClientAPI.api_request_dialog_open = False
                
                api_permissions = panel.GetAPIAccessPermissions()
                
                if api_permissions is not None:
                    
                    self._AddManually( api_permissions = api_permissions )
                    
                
            
        
        def _AddManually( self, api_permissions = None ):
            
            if api_permissions is None:
                
                api_permissions = ClientAPI.APIPermissions()
                
            
            title = 'edit api access permissions'
            
            with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
                
                panel = ClientGUIAPI.EditAPIPermissionsPanel( dlg, api_permissions )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    api_permissions = panel.GetValue()
                    
                    HG.client_controller.client_api_manager.AddAccess( api_permissions )
                    
                    self._Refresh()
                    
                
            
        
        def _Delete( self ):
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
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
                
                with ClientGUITopLevelWindows.DialogEdit( self, title ) as dlg:
                    
                    panel = ClientGUIAPI.EditAPIPermissionsPanel( dlg, api_permissions )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        api_permissions = panel.GetValue()
                        
                        HG.client_controller.client_api_manager.OverwriteAccess( api_permissions )
                        
                    else:
                        
                        break
                        
                    
                
            
            self._Refresh()
            
        
        def _OpenBaseURL( self ):
            
            port = self._service.GetPort()
            
            if port is None:
                
                wx.MessageBox( 'The service is not running, so you cannot view it in a web browser!' )
                
            else:
                
                url = 'http://127.0.0.1:{}/'.format( self._service.GetPort() )
                
                ClientPaths.LaunchURLInWebBrowser( url )
                
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            port = self._service.GetPort()
            
            if port is None:
                
                status = 'The client api is not running.'
                
            else:
                
                status = 'The client api should be running on port {}.'.format( port )
                
                upnp_port = self._service.GetUPnPPort()
                
                if upnp_port is not None:
                    
                    status += ' It should be open via UPnP on external port {}.'.format( upnp_port )
                    
                
            
            self._service_status.SetLabelText( status )
            
            api_permissions_objects = HG.client_controller.client_api_manager.GetAllPermissions()
            
            self._permissions_list.SetData( api_permissions_objects )
            
            self._permissions_list.Sort()
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceCombinedLocalFilesPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'combined local files' )
            
            self._service = service
            
            self._clear_deleted_files_record = ClientGUICommon.BetterButton( self, 'clear deleted files record', self._ClearDeletedFilesRecord )
            
            #
            
            self.Add( self._clear_deleted_files_record, CC.FLAGS_LONE_BUTTON )
            
        
        def _ClearDeletedFilesRecord( self ):
            
            message = 'This will instruct your database to forget its entire record of locally deleted files, meaning that if it ever encounters any of those files again, it will assume they are new and reimport them. This operation cannot be undone.'
            
            with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg_add:
                
                result = dlg_add.ShowModal()
                
                if result == wx.ID_YES:
                    
                    hashes = None
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', hashes ) )
                    
                    service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
                    
                    HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                    
                    HG.client_controller.pub( 'service_updated', self._service )
                    
                
            
        
    
    class _ServiceFilePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'files' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._file_info_st = ClientGUICommon.BetterStaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.Add( self._file_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( text ):
                
                if not self:
                    
                    return
                    
                
                self._file_info_st.SetLabelText( text )
                
            
            service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
            
            num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
            
            text = HydrusData.ToHumanInt( num_files ) + ' files, totalling ' + HydrusData.ToHumanBytes( total_size )
            
            if service.GetServiceType() in ( HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ):
                
                num_deleted_files = service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ]
                
                text += ' - ' + HydrusData.ToHumanInt( num_deleted_files ) + ' deleted files'
                
            
            wx.CallAfter( wx_code, text )
            
        
    
    class _ServiceRemotePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'this client\'s network use' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._address = ClientGUICommon.BetterStaticText( self )
            self._functional = ClientGUICommon.BetterStaticText( self )
            self._bandwidth_summary = ClientGUICommon.BetterStaticText( self )
            self._bandwidth_panel = wx.Panel( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.Add( self._address, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._functional, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._bandwidth_summary, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._bandwidth_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            credentials = self._service.GetCredentials()
            
            ( host, port ) = credentials.GetAddress()
            
            self._address.SetLabelText( host + ':' + str( port ) )
            
            status = self._service.GetStatusString()
            
            self._functional.SetLabelText( status )
            
            bandwidth_summary = self._service.GetBandwidthCurrentMonthSummary()
            
            self._bandwidth_summary.SetLabelText( bandwidth_summary )
            
            self._bandwidth_panel.DestroyChildren()
            
            b_gauges = []
            
            bandwidth_rows = self._service.GetBandwidthStringsAndGaugeTuples()
            
            b_vbox = wx.BoxSizer( wx.VERTICAL )
            
            for ( status, ( value, range ) ) in bandwidth_rows:
                
                gauge = ClientGUICommon.TextAndGauge( self._bandwidth_panel )
                
                gauge.SetValue( status, value, range )
                
                b_vbox.Add( gauge, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
            self._bandwidth_panel.SetSizer( b_vbox )
            
            self.Layout()
            
            ClientGUITopLevelWindows.PostSizeChangedEvent( self )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceRestrictedPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'hydrus service account - shared by all clients using the same access key' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._title_and_expires_st = ClientGUICommon.BetterStaticText( self )
            self._status_st = ClientGUICommon.BetterStaticText( self )
            self._next_sync_st = ClientGUICommon.BetterStaticText( self )
            self._bandwidth_summary = ClientGUICommon.BetterStaticText( self )
            self._bandwidth_panel = wx.Panel( self )
            
            self._refresh_account_button = ClientGUICommon.BetterButton( self, 'refresh account', self._RefreshAccount )
            self._copy_account_key_button = ClientGUICommon.BetterButton( self, 'copy account key', self._CopyAccountKey )
            self._permissions_button = ClientGUICommon.MenuButton( self, 'see special permissions', [] )
            
            #
            
            self._Refresh()
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._refresh_account_button, CC.FLAGS_VCENTER )
            hbox.Add( self._copy_account_key_button, CC.FLAGS_VCENTER )
            hbox.Add( self._permissions_button, CC.FLAGS_VCENTER )
            
            self.Add( self._title_and_expires_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._next_sync_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._bandwidth_summary, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._bandwidth_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self.Add( hbox, CC.FLAGS_BUTTON_SIZER )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _CopyAccountKey( self ):
            
            account = self._service.GetAccount()
            
            account_key = account.GetAccountKey()
            
            account_key_hex = account_key.hex()
            
            HG.client_controller.pub( 'clipboard', 'text', account_key_hex )
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            account = self._service.GetAccount()
            
            account_type = account.GetAccountType()
            
            title = account_type.GetTitle()
            
            expires_status = account.GetExpiresString()
            
            self._title_and_expires_st.SetLabelText( title + ' that ' + expires_status )
            
            account_status = account.GetStatusString()
            
            self._status_st.SetLabelText( account_status )
            
            next_sync_status = self._service.GetNextAccountSyncStatus()
            
            self._next_sync_st.SetLabelText( next_sync_status )
            
            #
            
            bandwidth_summary = account.GetBandwidthCurrentMonthSummary()
            
            self._bandwidth_summary.SetLabelText( bandwidth_summary )
            
            self._bandwidth_panel.DestroyChildren()
            
            b_gauges = []
            
            bandwidth_rows = account.GetBandwidthStringsAndGaugeTuples()
            
            b_vbox = wx.BoxSizer( wx.VERTICAL )
            
            for ( status, ( value, range ) ) in bandwidth_rows:
                
                gauge = ClientGUICommon.TextAndGauge( self._bandwidth_panel )
                
                gauge.SetValue( status, value, range )
                
                b_vbox.Add( gauge, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
            self._bandwidth_panel.SetSizer( b_vbox )
            
            #
            
            self._refresh_account_button.SetLabelText( 'refresh account' )
            self._refresh_account_button.Enable()
            
            account_key = account.GetAccountKey()
            
            if account_key is None or account_key == '':
                
                self._copy_account_key_button.Disable()
                
            else:
                
                self._copy_account_key_button.Enable()
                
            
            menu_items = []
            
            p_s = account_type.GetPermissionStrings()
            
            if len( p_s ) == 0:
                
                menu_items.append( ( 'label', 'no special permissions', 'no special permissions', None ) )
                
            else:
                
                for s in p_s:
                    
                    menu_items.append( ( 'label', s, s, None ) )
                    
                
            
            self._permissions_button.SetMenuItems( menu_items )
            
            self.Layout()
            
            ClientGUITopLevelWindows.PostSizeChangedEvent( self )
            
        
        def _RefreshAccount( self ):
            
            def do_it():
                
                try:
                    
                    self._service.SyncAccount( force = True )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    wx.CallAfter( wx.MessageBox, str( e ) )
                    
                
                wx.CallAfter( self._Refresh )
                
            
            if HG.client_controller.options[ 'pause_repo_sync' ]:
                
                wx.MessageBox( 'All repositories are currently paused under the services->pause menu! Please unpause them and then try again!' )
                
                return
                
            
            if self._service.GetServiceType() in HC.REPOSITORIES and self._service.IsPaused():
                
                wx.MessageBox( 'The service is paused! Please unpause it to refresh its account.' )
                
                return
                
            
            self._refresh_account_button.Disable()
            self._refresh_account_button.SetLabelText( 'fetching\u2026' )
            
            HG.client_controller.CallToThread( do_it )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceRepositoryPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'repository sync' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._content_panel = wx.Panel( self )
            
            self._metadata_st = ClientGUICommon.BetterStaticText( self )
            
            self._download_progress = ClientGUICommon.TextAndGauge( self )
            self._processing_progress = ClientGUICommon.TextAndGauge( self )
            
            self._sync_now_button = ClientGUICommon.BetterButton( self, 'process now', self._SyncNow )
            self._pause_play_button = ClientGUICommon.BetterButton( self, 'pause', self._PausePlay )
            self._export_updates_button = ClientGUICommon.BetterButton( self, 'export updates', self._ExportUpdates )
            self._reset_button = ClientGUICommon.BetterButton( self, 'reset processing cache', self._Reset )
            
            #
            
            self._Refresh()
            
            #
            
            new_options = HG.client_controller.new_options
            
            if not new_options.GetBoolean( 'advanced_mode' ):
                
                self._sync_now_button.Hide()
                self._export_updates_button.Hide()
                self._reset_button.Hide()
                
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._sync_now_button, CC.FLAGS_VCENTER )
            hbox.Add( self._pause_play_button, CC.FLAGS_VCENTER )
            hbox.Add( self._export_updates_button, CC.FLAGS_VCENTER )
            hbox.Add( self._reset_button, CC.FLAGS_VCENTER )
            
            self.Add( self._metadata_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._download_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._processing_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( hbox, CC.FLAGS_BUTTON_SIZER )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _ExportUpdates( self ):
            
            def wx_done():
                
                if not self:
                    
                    return
                    
                
                self._export_updates_button.SetLabelText( 'export updates' )
                self._export_updates_button.Enable()
                
            
            def do_it( dest_dir, service ):
                
                try:
                    
                    update_hashes = service.GetUpdateHashes()
                    
                    num_to_do = len( update_hashes )
                    
                    if num_to_do == 0:
                        
                        wx.CallAfter( wx.MessageBox, 'No updates to export!' )
                        
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
                    
                    wx.CallAfter( wx_done )
                    
                
            
            with wx.DirDialog( self, 'Select export location.' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    path = dlg.GetPath()
                    
                    self._export_updates_button.SetLabelText( 'exporting\u2026' )
                    self._export_updates_button.Disable()
                    
                    HG.client_controller.CallToThread( do_it, path, self._service )
                    
                
            
        
        def _PausePlay( self ):
            
            self._service.PausePlay()
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            service_paused = self._service.IsPaused()
            
            self._sync_now_button.Disable()
            
            if service_paused:
                
                self._pause_play_button.SetLabelText( 'paused' )
                self._pause_play_button.SetForegroundColour( ( 128, 0, 0 ) )
                
            else:
                
                self._pause_play_button.SetLabelText( 'working' )
                self._pause_play_button.SetForegroundColour( ( 0, 128, 0 ) )
                
            
            self._metadata_st.SetLabelText( self._service.GetNextUpdateDueString() )
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def _Reset( self ):
            
            name = self._service.GetName()
            
            message = 'This will remove all the processed information for ' + name + ' from the database, setting the \'processed\' gauge back to 0.' + os.linesep * 2 + 'Once the service is reset, you will have to reprocess everything that has been downloaded over again. The client will naturally do this in its idle time as before, just starting over from the beginning.' + os.linesep * 2 + 'If you do not understand what this does, click no!'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    message = 'Seriously, are you absolutely sure?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg2:
                        
                        if dlg2.ShowModal() == wx.ID_YES:
                            
                            self._service.Reset()
                            
                        
                    
                
            
        
        def _SyncNow( self ):
            
            message = 'This will tell the database to process any outstanding update files.'
            message += os.linesep * 2
            message += 'This is a big task that usually runs during idle time. It locks the entire database and takes over the ui, stopping you from interacting with it. It is cancellable but may still take some time to return ui control to you.'
            message += os.linesep * 2
            message += 'If you are a new user, click \'no\'!'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    def do_it():
                        
                        self._service.SyncProcessUpdates( maintenance_mode = HC.MAINTENANCE_FORCED )
                        
                        self._my_updater.Update()
                        
                    
                    self._sync_now_button.Disable()
                    
                    HG.client_controller.CallToThread( do_it )
                    
                
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( download_text, download_value, processing_text, processing_value, range ):
                
                if not self:
                    
                    return
                    
                
                self._download_progress.SetValue( download_text, download_value, range )
                self._processing_progress.SetValue( processing_text, processing_value, range )
                
                if processing_value == download_value:
                    
                    self._sync_now_button.Disable()
                    
                
                if download_value == 0:
                    
                    self._export_updates_button.Disable()
                    
                else:
                    
                    self._export_updates_button.Enable()
                    
                
                if processing_value == 0:
                    
                    self._reset_button.Disable()
                    
                else:
                    
                    self._reset_button.Enable()
                    
                
                processing_work_to_do = processing_value < download_value
                
                service_paused = self._service.IsPaused()
                
                all_repo_sync_paused = HG.client_controller.options[ 'pause_repo_sync' ]
                
                if service_paused or all_repo_sync_paused or not processing_work_to_do:
                    
                    self._sync_now_button.Disable()
                    
                else:
                    
                    self._sync_now_button.Enable()
                    
                
            
            ( download_value, processing_value, range ) = HG.client_controller.Read( 'repository_progress', service.GetServiceKey() )
            
            download_text = 'downloaded ' + HydrusData.ConvertValueRangeToPrettyString( download_value, range )
            
            processing_text = 'processed ' + HydrusData.ConvertValueRangeToPrettyString( processing_value, range )
            
            wx.CallAfter( wx_code, download_text, download_value, processing_text, processing_value, range )
            
        
    
    class _ServiceIPFSPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'ipfs' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            interaction_panel = IPFSDaemonStatusAndInteractionPanel( self, self.GetService )
            
            self._ipfs_shares_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            columns = [ ( 'multihash', 34 ), ( 'num files', 11 ), ( 'total size', 12 ), ( 'note', -1 ) ]
            
            self._ipfs_shares = ClientGUIListCtrl.BetterListCtrl( self._ipfs_shares_panel, 'ipfs_shares', 12, 32, columns, self._ConvertDataToListCtrlTuple, delete_key_callback = self._Unpin, activation_callback = self._SetNotes )
            
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
            
            if not self:
                
                return
                
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def _SetNotes( self ):
            
            datas = self._ipfs_shares.GetData( only_selected = True )
            
            if len( datas ) > 0:
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Set a note for these shares.' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        note = dlg.GetValue()
                        
                        content_updates = []
                        
                        for ( multihash, num_files, total_size, old_note ) in datas:
                            
                            hashes = HG.client_controller.Read( 'service_directory', self._service.GetServiceKey(), multihash )
                            
                            content_update_row = ( hashes, multihash, note )
                            
                            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_ADD, content_update_row ) )
                            
                        
                        HG.client_controller.Write( 'content_updates', { self._service.GetServiceKey() : content_updates } )
                        
                        self._my_updater.Update()
                        
                    
                
            
        
        def _ShowSelectedInNewPages( self ):
            
            def wx_done():
                
                if not self:
                    
                    return
                    
                
                self._ipfs_shares_panel.Enable()
                
            
            def do_it( service_key, pages_of_hashes_to_show ):
                
                try:
                    
                    for ( multihash, num_files, total_size, note ) in shares:
                        
                        hashes = HG.client_controller.Read( 'service_directory', service_key, multihash )
                        
                        HG.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes, page_name = 'ipfs directory' )
                        
                        time.sleep( 0.5 )
                        
                    
                finally:
                    
                    wx.CallAfter( wx_done )
                    
                
            
            shares = self._ipfs_shares.GetData( only_selected = True )
            
            self._ipfs_shares_panel.Disable()
            
            HG.client_controller.CallToThread( do_it, self._service.GetServiceKey(), shares )
            
        
        def _Unpin( self ):
            
            def wx_done():
                
                if not self:
                    
                    return
                    
                
                self._ipfs_shares_panel.Enable()
                
                self._my_updater.Update()
                
            
            def do_it( service, multihashes ):
                
                try:
                    
                    for multihash in multihashes:
                        
                        service.UnpinDirectory( multihash )
                        
                    
                finally:
                    
                    wx.CallAfter( wx_done )
                    
                
            
            with ClientGUIDialogs.DialogYesNo( self, 'Unpin (remove) all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetData( only_selected = True ) ]
                    
                    self._ipfs_shares_panel.Disable()
                    
                    HG.client_controller.CallToThread( do_it, self._service, multihashes )
                    
                
            
        
        def GetService( self ):
            
            return self._service
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( ipfs_shares ):
                
                if not self:
                    
                    return
                    
                
                # list of ( multihash, num_files, total_size, note )
                
                self._ipfs_shares.SetData( ipfs_shares )
                
            
            ipfs_shares = HG.client_controller.Read( 'service_directories', service.GetServiceKey() )
            
            wx.CallAfter( wx_code, ipfs_shares )
            
        
    
    class _ServiceLocalBooruPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'local booru' )
            
            self._service = service
            
            self._share_key_info = {}
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._service_status = ClientGUICommon.BetterStaticText( self )
            
            booru_share_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            columns = [ ( 'name', -1 ), ( 'info', 36 ), ( 'expires', 12 ), ( 'files', 12 ) ]
            
            self._booru_shares = ClientGUIListCtrl.BetterListCtrl( booru_share_panel, 'local_booru_shares', 10, 36, columns, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
            
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
                
                wx.MessageBox( 'The local booru is not currently running!' )
                
            
            urls = []
            
            for share_key in self._booru_shares.GetData( only_selected = True ):
                
                try:
                    
                    url = self._service.GetExternalShareURL( share_key )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    wx.MessageBox( 'Unfortunately, could not generate an external URL: {}'.format( e ) )
                    
                    return
                    
                
                urls.append( url )
                
            
            text = os.linesep.join( urls )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
        def _CopyInternalShareURL( self ):
            
            internal_ip = '127.0.0.1'
            
            internal_port = self._service.GetPort()
            
            if internal_port is None:
                
                wx.MessageBox( 'The local booru is not currently running!' )
                
            
            urls = []
            
            for share_key in self._booru_shares.GetData( only_selected = True ):
                
                url = 'http://' + internal_ip + ':' + str( internal_port ) + '/gallery?share_key=' + share_key.hex()
                
                urls.append( url )
                
            
            text = os.linesep.join( urls )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
        def _Delete( self ):
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
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
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
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
            
            if not self:
                
                return
                
            
            port = self._service.GetPort()
            
            if port is None:
                
                status = 'The local booru is not running.'
                
            else:
                
                status = 'The local booru should be running on port {}.'.format( port )
                
                upnp_port = self._service.GetUPnPPort()
                
                if upnp_port is not None:
                    
                    status += ' It should be open via UPnP on external port {}.'.format( upnp_port )
                    
                
            
            self._service_status.SetLabelText( status )
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( booru_shares ):
                
                if not self:
                    
                    return
                    
                
                self._share_key_info.update( booru_shares )
                
                self._booru_shares.SetData( list(booru_shares.keys()) )
                
                self._booru_shares.Sort()
                
            
            booru_shares = HG.client_controller.Read( 'local_booru_shares' )
            
            wx.CallAfter( wx_code, booru_shares )
            
        
    
    class _ServiceRatingPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'ratings' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._rating_info_st = ClientGUICommon.BetterStaticText( self )
            
            menu_items = []
            
            menu_items.append( ( 'normal', 'for deleted files', 'delete all set ratings for files that have since been deleted', HydrusData.Call( self._ClearRatings, 'delete_for_deleted_files', 'deleted files' ) ) )
            menu_items.append( ( 'normal', 'for all non-local files', 'delete all set ratings for files that are not in this client right now', HydrusData.Call( self._ClearRatings, 'delete_for_non_local_files', 'non-local files' ) ) )
            menu_items.append( ( 'separator', None, None, None ) )
            menu_items.append( ( 'normal', 'for all files', 'delete all set ratings for all files', HydrusData.Call( self._ClearRatings, 'delete_for_all_files', 'ALL FILES' ) ) )
            
            self._clear_deleted = ClientGUICommon.MenuButton( self, 'clear ratings', menu_items )
            
            #
            
            self._Refresh()
            
            #
            
            self.Add( self._rating_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._clear_deleted, CC.FLAGS_LONE_BUTTON )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _ClearRatings( self, advanced_action, action_description ):
            
            message = 'Delete any ratings on this service for {}? THIS CANNOT BE UNDONE'.format( action_description )
            message += os.linesep * 2
            message += 'Please note a client restart is needed to see the ratings disappear in media views.'
            
            with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg_add:
                
                result = dlg_add.ShowModal()
                
                if result == wx.ID_YES:
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADVANCED, advanced_action )
                    
                    service_keys_to_content_updates = { self._service.GetServiceKey() : [ content_update ] }
                    
                    HG.client_controller.Write( 'content_updates', service_keys_to_content_updates, do_pubsubs = False )
                    
                    HG.client_controller.pub( 'service_updated', self._service )
                    
                
            
        
        def _Refresh( self ):
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( text ):
                
                if not self:
                    
                    return
                    
                
                self._rating_info_st.SetLabelText( text )
                
            
            service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
            
            num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            
            text = HydrusData.ToHumanInt( num_files ) + ' files are rated'
            
            wx.CallAfter( wx_code, text )
            
        
    
    class _ServiceTagPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'tags' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._tag_info_st = ClientGUICommon.BetterStaticText( self )
            
            self._advanced_content_update = ClientGUICommon.BetterButton( self, 'advanced service-wide update', self._AdvancedContentUpdate )
            
            #
            
            new_options = HG.client_controller.new_options
            
            advanced_mode = new_options.GetBoolean( 'advanced_mode' )
            
            if not advanced_mode:
                
                self._advanced_content_update.Hide()
                
            
            self._Refresh()
            
            #
            
            self.Add( self._tag_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._advanced_content_update, CC.FLAGS_LONE_BUTTON )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _AdvancedContentUpdate( self ):
            
            with ClientGUITopLevelWindows.DialogNullipotent( self, 'advanced content update' ) as dlg:
                
                panel = ClientGUIScrolledPanelsReview.AdvancedContentUpdatePanel( dlg, self._service.GetServiceKey() )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
        
        def _Refresh( self ):
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( text ):
                
                if not self:
                    
                    return
                    
                
                self._tag_info_st.SetLabelText( text )
                
            
            service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
            
            num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
            num_mappings = service_info[ HC.SERVICE_INFO_NUM_MAPPINGS ]
            
            text = HydrusData.ToHumanInt( num_mappings ) + ' total mappings involving ' + HydrusData.ToHumanInt( num_tags ) + ' different tags on ' + HydrusData.ToHumanInt( num_files ) + ' different files'
            
            if service.GetServiceType() == HC.TAG_REPOSITORY:
                
                num_deleted_mappings = service_info[ HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ]
                
                text += ' - ' + HydrusData.ToHumanInt( num_deleted_mappings ) + ' deleted mappings'
                
            
            wx.CallAfter( wx_code, text )
            
        
    
    class _ServiceTrashPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'trash' )
            
            self._service = service
            
            self._clear_trash = ClientGUICommon.BetterButton( self, 'clear trash', self._ClearTrash )
            
            #
            
            self.Add( self._clear_trash, CC.FLAGS_LONE_BUTTON )
            
        
        def _ClearTrash( self ):
            
            message = 'This will completely clear your trash of all its files, deleting them permanently from the client. This operation cannot be undone.'
            message += os.linesep * 2
            message += 'If you have many files in your trash, it will take some time to complete and for all the files to eventually be deleted.'
            
            with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg_add:
                
                result = dlg_add.ShowModal()
                
                if result == wx.ID_YES:
                    
                    def do_it():
                        
                        hashes = HG.client_controller.Read( 'trash_hashes' )
                        
                        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
                        
                        service_keys_to_content_updates = { CC.TRASH_SERVICE_KEY : [ content_update ] }
                        
                        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                        HG.client_controller.pub( 'service_updated', self._service )
                        
                    
                    HG.client_controller.CallToThread( do_it )
                    
                
            
        
    
