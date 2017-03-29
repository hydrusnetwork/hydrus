import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals
import HydrusNATPunch
import HydrusNetwork
import HydrusPaths
import os
import time
import wx

class ReviewServicePanel( wx.Panel ):
    
    def __init__( self, parent, service ):
        
        wx.Panel.__init__( self, parent )
        
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
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        for panel in subpanels:
            
            vbox.AddF( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.SetSizer( vbox )
        
    
    def _DisplayService( self ):
        
        service_type = self._service.GetServiceType()
        
        self._DisplayAccountInfo()
        
        if service_type in HC.REPOSITORIES + HC.LOCAL_SERVICES + [ HC.IPFS ]:
            
            service_info = self._controller.Read( 'service_info', self._service_key )
            
            if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                
                num_ratings = service_info[ HC.SERVICE_INFO_NUM_FILES ]
                
                self._ratings_text.SetLabelText( HydrusData.ConvertIntToPrettyString( num_ratings ) + ' files rated' )
                
            elif service_type == HC.LOCAL_BOORU:
                
                num_shares = service_info[ HC.SERVICE_INFO_NUM_SHARES ]
                
                self._num_shares.SetLabelText( HydrusData.ConvertIntToPrettyString( num_shares ) + ' shares currently active' )
                
            
        
        if service_type == HC.LOCAL_BOORU:
            
            booru_shares = self._controller.Read( 'local_booru_shares' )
            
            self._booru_shares.DeleteAllItems()
            
            for ( share_key, info ) in booru_shares.items():
                
                name = info[ 'name' ]
                text = info[ 'text' ]
                timeout = info[ 'timeout' ]
                hashes = info[ 'hashes' ]
                
                self._booru_shares.Append( ( name, text, HydrusData.ConvertTimestampToPrettyExpires( timeout ), len( hashes ) ), ( name, text, timeout, ( len( hashes ), hashes, share_key ) ) )
                
            
        
        if service_type == HC.IPFS:
            
            ipfs_shares = self._controller.Read( 'service_directories', self._service_key )
            
            self._ipfs_shares.DeleteAllItems()
            
            for ( multihash, num_files, total_size, note ) in ipfs_shares:
                
                self._ipfs_shares.Append( ( multihash, HydrusData.ConvertIntToPrettyString( num_files ), HydrusData.ConvertIntToBytes( total_size ), note ), ( multihash, num_files, total_size, note ) )
                
            
        
    
    def DeleteBoorus( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                for ( name, text, timeout, ( num_hashes, hashes, share_key ) ) in self._booru_shares.GetSelectedClientData():
                    
                    self._controller.Write( 'delete_local_booru_share', share_key )
                    
                
                self._booru_shares.RemoveAllSelected()
                
            
        
    
    def EditBoorus( self ):
    
        writes = []
        
        for ( name, text, timeout, ( num_hashes, hashes, share_key ) ) in self._booru_shares.GetSelectedClientData():
            
            with ClientGUIDialogs.DialogInputLocalBooruShare( self, share_key, name, text, timeout, hashes, new_share = False) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    ( share_key, name, text, timeout, hashes ) = dlg.GetInfo()
                    
                    info = {}
                    
                    info[ 'name' ] = name
                    info[ 'text' ] = text
                    info[ 'timeout' ] = timeout
                    info[ 'hashes' ] = hashes
                    
                    writes.append( ( share_key, info ) )
                    
                
            
        
        for ( share_key, info ) in writes:
            
            self._controller.Write( 'local_booru_share', share_key, info )
            
        
    
    def EditIPFSNotes( self ):
        
        for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetSelectedClientData():
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Set a note for ' + multihash + '.' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    hashes = self._controller.Read( 'service_directory', self._service_key, multihash )
                    
                    note = dlg.GetValue()
                    
                    content_update_row = ( hashes, multihash, note )
                    
                    content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
                    
                    HydrusGlobals.client_controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
                    
                
            
        
        self._DisplayService()
        
    
    def EventBooruDelete( self, event ):
        
        self.DeleteBoorus()
        
    
    def EventBooruEdit( self, event ):
        
        self.EditBoorus()
        
    
    def EventBooruOpenSearch( self, event ):
        
        for ( name, text, timeout, ( num_hashes, hashes, share_key ) ) in self._booru_shares.GetSelectedClientData():
            
            media_results = self._controller.Read( 'media_results', hashes )
            
            self._controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_media_results = media_results )
            
        
    
    def EventClearTrash( self, event ):
        
        def do_it():
            
            hashes = self._controller.Read( 'trash_hashes' )
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
            
            service_keys_to_content_updates = { CC.TRASH_SERVICE_KEY : [ content_update ] }
            
            self._controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
            
            wx.CallAfter( self._DisplayService )
            
        
        self._controller.CallToThread( do_it )
        
    
    def EventCopyExternalShareURL( self, event ):
        
        shares = self._booru_shares.GetSelectedClientData()
        
        if len( shares ) > 0:
            
            ( name, text, timeout, ( num_hashes, hashes, share_key ) ) = shares[0]
            
            info = self._service.GetInfo()
            
            external_ip = HydrusNATPunch.GetExternalIP() # eventually check for optional host replacement here
            
            external_port = info[ 'upnp' ]
            
            if external_port is None: external_port = info[ 'port' ]
            
            url = 'http://' + external_ip + ':' + HydrusData.ToUnicode( external_port ) + '/gallery?share_key=' + share_key.encode( 'hex' )
            
            self._controller.pub( 'clipboard', 'text', url )
            
        
    
    def EventCopyInternalShareURL( self, event ):
        
        shares = self._booru_shares.GetSelectedClientData()
        
        if len( shares ) > 0:
            
            ( name, text, timeout, ( num_hashes, hashes, share_key ) ) = shares[0]
            
            info = self._service.GetInfo()
            
            internal_ip = '127.0.0.1'
            
            internal_port = info[ 'port' ]
            
            url = 'http://' + internal_ip + ':' + str( internal_port ) + '/gallery?share_key=' + share_key.encode( 'hex' )
            
            self._controller.pub( 'clipboard', 'text', url )
            
        
    
    def EventDeleteLocalDeleted( self, event ):
        
        message = 'This will clear the client\'s memory of which files it has locally deleted, which affects \'exclude previously deleted files\' import tests.'
        message += os.linesep * 2
        message += 'It will freeze the gui while it works.'
        message += os.linesep * 2
        message += 'If you do not know what this does, click \'forget it\'.'
        
        with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg_add:
            
            result = dlg_add.ShowModal()
            
            if result == wx.ID_YES:
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', None ) )
                
                service_keys_to_content_updates = { self._service_key : [ content_update ] }
                
                HydrusGlobals.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                
                self._DisplayService()
                
            
        
    
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
                
                rows_s = weight / it_took
                
                update_speed_string = ' at ' + HydrusData.ConvertIntToPrettyString( rows_s ) + ' rows/s'
                
                c_u_p_total_weight_processed += weight
                
            
            job_key.DeleteVariable( 'popup_gauge_1' )
            
            self._service.SyncThumbnails( job_key )
            
            job_key.SetVariable( 'popup_text_1', 'done! ' + HydrusData.ConvertIntToPrettyString( c_u_p_num_rows ) + ' rows added.' )
            
            job_key.Finish()
            
        
        self._controller.CallToThread( do_it )
        
    
    def EventIPFSCopyMultihash( self, event ):
        
        shares = self._ipfs_shares.GetSelectedClientData()
        
        if len( shares ) > 0:
            
            ( multihash, num_files, total_size, note ) = shares[0]
            
            multihash_prefix = self._service.GetMultihashPrefix()
            
            text = multihash_prefix + multihash
            
            self._controller.pub( 'clipboard', 'text', text )
            
        
    
    def EventIPFSOpenSearch( self, event ):
        
        for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetSelectedClientData():
            
            hashes = self._controller.Read( 'service_directory', self._service_key, multihash )
            
            media_results = self._controller.Read( 'media_results', hashes )
            
            self._controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_media_results = media_results )
            
        
    
    def EventIPFSSetNote( self, event ):
        
        self.EditIPFSNotes()
        
    
    def EventIPFSUnpin( self, event ):
        
        self.UnpinIPFSDirectories()
        
    
    def EventServiceWideUpdate( self, event ):
        
        with ClientGUIDialogs.DialogAdvancedContentUpdate( self, self._service_key ) as dlg:
            
            dlg.ShowModal()
            
        
    
    def GetServiceKey( self ):
        
        return self._service.GetServiceKey()
        
    
    def RefreshLocalBooruShares( self ):
        
        self._DisplayService()
        
    
    def UnpinIPFSDirectories( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetSelectedClientData():
                    
                    self._service.UnpinDirectory( multihash )
                    
                
                self._ipfs_shares.RemoveAllSelected()
                
            
        
    
    class _ServicePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'name and type' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._name_and_type = wx.StaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.AddF( self._name_and_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HydrusGlobals.client_controller.sub( self, 'Update', 'service_updated' )
            
        
        def _Refresh( self ):
            
            name = self._service.GetName()
            service_type = self._service.GetServiceType()
            
            label = name + ' - ' + HC.service_string_lookup[ service_type ]
            
            self._name_and_type.SetLabelText( label )
            
        
        def Update( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceFilePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'files' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._file_info_st = wx.StaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.AddF( self._file_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HydrusGlobals.client_controller.sub( self, 'Update', 'service_updated' )
            
        
        def _Refresh( self ):
            
            HydrusGlobals.client_controller.CallToThread( self.THREADUpdateTagInfo )
            
        
        def _UpdateFromThread( self, text ):
            
            try:
                
                self._file_info_st.SetLabelText( text )
                
            except wx.PyDeadObjectError:
                
                pass
                
            
        
        def Update( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADUpdateTagInfo( self ):
            
            service_info = HydrusGlobals.client_controller.Read( 'service_info', self._service.GetServiceKey() )
            
            num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
            
            text = HydrusData.ConvertIntToPrettyString( num_files ) + ' files, totalling ' + HydrusData.ConvertIntToBytes( total_size )
            
            if self._service.GetServiceType() in ( HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ):
                
                num_deleted_files = service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ]
                
                text += ' - ' + HydrusData.ConvertIntToPrettyString( num_deleted_files ) + ' deleted files'
                
            
            wx.CallAfter( self._UpdateFromThread, text )
            
        
    
    class _ServiceRemotePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'clientside network' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._address = wx.StaticText( self )
            self._functional = wx.StaticText( self )
            self._bandwidth_summary = wx.StaticText( self )
            self._bandwidth_panel = wx.Panel( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.AddF( self._address, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._functional, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._bandwidth_summary, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._bandwidth_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            HydrusGlobals.client_controller.sub( self, 'Update', 'service_updated' )
            
        
        def _Refresh( self ):
            
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
                
                b_vbox.AddF( gauge, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
            self._bandwidth_panel.SetSizer( b_vbox )
            
            self.Layout()
            
            wx.PostEvent( self.GetParent(), CC.SizeChangedEvent( -1 ) )
            
        
        def Update( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceRestrictedPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'serverside hydrus account' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._title_and_expires_st = wx.StaticText( self )
            self._status_st = wx.StaticText( self )
            self._next_sync_st = wx.StaticText( self )
            self._bandwidth_summary = wx.StaticText( self )
            self._bandwidth_panel = wx.Panel( self )
            
            self._refresh_account_button = ClientGUICommon.BetterButton( self, 'refresh account', self._RefreshAccount )
            self._copy_account_key_button = ClientGUICommon.BetterButton( self, 'copy account key', self._CopyAccountKey )
            self._permissions_button = ClientGUICommon.MenuButton( self, 'see special permissions', [] )
            
            #
            
            self._Refresh()
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._refresh_account_button, CC.FLAGS_LONE_BUTTON )
            hbox.AddF( self._copy_account_key_button, CC.FLAGS_LONE_BUTTON )
            hbox.AddF( self._permissions_button, CC.FLAGS_LONE_BUTTON )
            
            self.AddF( self._title_and_expires_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._next_sync_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._bandwidth_summary, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._bandwidth_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
            
            HydrusGlobals.client_controller.sub( self, 'Update', 'service_updated' )
            
        
        def _CopyAccountKey( self ):
            
            account = self._service.GetAccount()
            
            account_key = account.GetAccountKey()
            
            account_key_hex = account_key.encode( 'hex' )
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', account_key_hex )
            
        
        def _Refresh( self ):
            
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
                
                b_vbox.AddF( gauge, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
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
            
            wx.PostEvent( self.GetParent(), CC.SizeChangedEvent( -1 ) )
            
        
        def _RefreshAccount( self ):
            
            def do_it():
                
                try:
                    
                    self._service.SyncAccount( force = True )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    wx.CallAfter( wx.MessageBox, HydrusData.ToUnicode( e ) )
                    
                
                wx.CallAfter( self._Refresh )
                
            
            self._refresh_account_button.Disable()
            self._refresh_account_button.SetLabelText( u'fetching\u2026' )
            
            HydrusGlobals.client_controller.CallToThread( do_it )
            
        
        def Update( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceRepositoryPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'repository sync' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._content_panel = wx.Panel( self )
            
            self._metadata_st = wx.StaticText( self )
            
            self._download_progress = ClientGUICommon.TextAndGauge( self )
            self._processing_progress = ClientGUICommon.TextAndGauge( self )
            
            self._sync_now_button = ClientGUICommon.BetterButton( self, 'process now', self._SyncNow )
            self._pause_play_button = ClientGUICommon.BetterButton( self, 'pause', self._PausePlay )
            self._export_updates_button = ClientGUICommon.BetterButton( self, 'export updates', self._ExportUpdates )
            self._reset_button = ClientGUICommon.BetterButton( self, 'reset processing cache', self._Reset )
            
            #
            
            self._Refresh()
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._sync_now_button, CC.FLAGS_LONE_BUTTON )
            hbox.AddF( self._pause_play_button, CC.FLAGS_LONE_BUTTON )
            hbox.AddF( self._export_updates_button, CC.FLAGS_LONE_BUTTON )
            hbox.AddF( self._reset_button, CC.FLAGS_LONE_BUTTON )
            
            self.AddF( self._metadata_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._download_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( self._processing_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
            
            HydrusGlobals.client_controller.sub( self, 'Update', 'service_updated' )
            
        
        def _ExportUpdates( self ):
            
            def do_it( dest_dir ):
                
                try:
                    
                    update_hashes = self._service.GetUpdateHashes()
                    
                    num_to_do = len( update_hashes )
                    
                    if num_to_do == 0:
                        
                        wx.CallAfter( wx.MessageBox, 'No updates to export!' )
                        
                    else:
                        
                        job_key = ClientThreading.JobKey( cancellable = True )
                        
                        try:
                            
                            job_key.SetVariable( 'popup_title', 'exporting updates for ' + self._service.GetName() )
                            HydrusGlobals.client_controller.pub( 'message', job_key )
                            
                            client_files_manager = HydrusGlobals.client_controller.GetClientFilesManager()
                            
                            for ( i, update_hash ) in enumerate( update_hashes ):
                                
                                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                                
                                if should_quit:
                                    
                                    job_key.SetVariable( 'popup_text_1', 'Cancelled!' )
                                    
                                    return
                                    
                                
                                try:
                                    
                                    update_path = client_files_manager.GetFilePath( update_hash, HC.APPLICATION_HYDRUS_UPDATE_CONTENT )
                                    
                                    dest_path = os.path.join( dest_dir, update_hash.encode( 'hex' ) )
                                    
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
                    
                    wx.CallAfter( self._export_updates_button.SetLabelText, 'export updates' )
                    wx.CallAfter( self._export_updates_button.Enable )
                    
                
            
            with wx.DirDialog( self, 'Select export location.' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    path = HydrusData.ToUnicode( dlg.GetPath() )
                    
                    self._export_updates_button.SetLabelText( u'exporting\u2026' )
                    self._export_updates_button.Disable()
                    
                    HydrusGlobals.client_controller.CallToThread( do_it, path )
                    
                
            
        
        def _PausePlay( self ):
            
            self._service.PausePlay()
            
        
        def _Refresh( self ):
            
            service_paused = self._service.IsPaused()
            
            options = HydrusGlobals.client_controller.GetOptions()
            
            all_repo_sync_paused = options[ 'pause_repo_sync' ]
            
            if service_paused or all_repo_sync_paused:
                
                self._sync_now_button.Disable()
                
            else:
                
                self._sync_now_button.Enable()
                
            
            if service_paused:
                
                self._pause_play_button.SetLabelText( 'unpause' )
                
            else:
                
                self._pause_play_button.SetLabelText( 'pause' )
                
            
            self._metadata_st.SetLabelText( self._service.GetNextUpdateDueString() )
            
            HydrusGlobals.client_controller.CallToThread( self.THREADFetchUpdateProgress )
            
        
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
            
            def do_it():
                
                self._service.Sync( False )
                
                self._my_updater.Update()
                
            
            self._sync_now_button.Disable()
            
            HydrusGlobals.client_controller.CallToThread( do_it )
            
        
        def _UpdateFromThread( self, download_text, download_value, processing_text, processing_value, range ):
            
            try:
                
                self._download_progress.SetValue( download_text, download_value, range )
                self._processing_progress.SetValue( processing_text, processing_value, range )
                
            except wx.PyDeadObjectError:
                
                pass
                
            
        
        def Update( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchUpdateProgress( self ):
            
            ( download_value, processing_value, range ) = HydrusGlobals.client_controller.Read( 'repository_progress', self._service.GetServiceKey() )
            
            download_text = 'downloaded ' + HydrusData.ConvertValueRangeToPrettyString( download_value, range )
            
            processing_text = 'processed ' + HydrusData.ConvertValueRangeToPrettyString( processing_value, range )
            
            wx.CallAfter( self._UpdateFromThread, download_text, download_value, processing_text, processing_value, range )
            
        
    
    class _ServiceIPFSPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'ipfs' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._name_and_type = wx.StaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.AddF( self._name_and_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HydrusGlobals.client_controller.sub( self, 'Update', 'service_updated' )
            
        
        def _Refresh( self ):
            
            self._name_and_type.SetLabelText( 'This is an IPFS service. This box will regain its old information and controls in a later version.' )
            
        
        def Update( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceLocalBooruPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'local booru' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._name_and_type = wx.StaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.AddF( self._name_and_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HydrusGlobals.client_controller.sub( self, 'Update', 'service_updated' )
            
        
        def _Refresh( self ):
            
            self._name_and_type.SetLabelText( 'This is a Local Booru service. This box will regain its old information and controls in a later version.' )
            
        
        def Update( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceRatingPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'ratings' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._name_and_type = wx.StaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.AddF( self._name_and_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HydrusGlobals.client_controller.sub( self, 'Update', 'service_updated' )
            
        
        def _Refresh( self ):
            
            # put this fetch on a thread, since it'll have to go to the db
            
            self._name_and_type.SetLabelText( 'This service has ratings. This box will regain its old information in a later version.' )
            
        
        def Update( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceTagPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'tags' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._tag_info_st = wx.StaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.AddF( self._tag_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HydrusGlobals.client_controller.sub( self, 'Update', 'service_updated' )
            
        
        def _Refresh( self ):
            
            HydrusGlobals.client_controller.CallToThread( self.THREADUpdateTagInfo )
            
        
        def _UpdateFromThread( self, text ):
            
            try:
                
                self._tag_info_st.SetLabelText( text )
                
            except wx.PyDeadObjectError:
                
                pass
                
            
        
        def Update( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADUpdateTagInfo( self ):
            
            service_info = HydrusGlobals.client_controller.Read( 'service_info', self._service.GetServiceKey() )
            
            num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
            num_mappings = service_info[ HC.SERVICE_INFO_NUM_MAPPINGS ]
            
            text = HydrusData.ConvertIntToPrettyString( num_mappings ) + ' total mappings involving ' + HydrusData.ConvertIntToPrettyString( num_tags ) + ' different tags on ' + HydrusData.ConvertIntToPrettyString( num_files ) + ' different files'
            
            if self._service.GetServiceType() == HC.TAG_REPOSITORY:
                
                num_deleted_mappings = service_info[ HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ]
                
                text += ' - ' + HydrusData.ConvertIntToPrettyString( num_deleted_mappings ) + ' deleted mappings'
                
            
            wx.CallAfter( self._UpdateFromThread, text )
            
        
    
