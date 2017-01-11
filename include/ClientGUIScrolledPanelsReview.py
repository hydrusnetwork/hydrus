import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIFrames
import ClientGUIScrolledPanels
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import HydrusNATPunch
import os
import traceback
import wx

class ReviewServicesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._notebook = wx.Notebook( self )
        
        self._local_listbook = ClientGUICommon.ListBook( self._notebook )
        self._remote_listbook = ClientGUICommon.ListBook( self._notebook )
        
        self._edit = wx.Button( self, label = 'manage services' )
        self._edit.Bind( wx.EVT_BUTTON, self.EventEdit )
        
        self._InitialiseServices()
        
        self._notebook.AddPage( self._local_listbook, 'local' )
        self._notebook.AddPage( self._remote_listbook, 'remote' )
        
        self.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventPageChanged )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( self._edit, CC.FLAGS_SMALL_INDENT )
        
        self.SetSizer( vbox )
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_gui' )
        
    
    def _InitialiseServices( self ):
        
        self._local_listbook.DeleteAllPages()
        self._remote_listbook.DeleteAllPages()
        
        listbook_dict = {}
        
        services = self._controller.GetServicesManager().GetServices()
        
        for service in services:
            
            service_type = service.GetServiceType()
            
            if service_type in HC.LOCAL_SERVICES: parent_listbook = self._local_listbook
            else: parent_listbook = self._remote_listbook
            
            if service_type == HC.TAG_REPOSITORY: name = 'tag repositories'
            elif service_type == HC.FILE_REPOSITORY: name = 'file repositories'
            elif service_type == HC.MESSAGE_DEPOT: name = 'message depots'
            elif service_type == HC.SERVER_ADMIN: name = 'administrative servers'
            elif service_type in HC.LOCAL_FILE_SERVICES: name = 'files'
            elif service_type == HC.LOCAL_TAG: name = 'tags'
            elif service_type == HC.LOCAL_RATING_LIKE: name = 'like/dislike ratings'
            elif service_type == HC.LOCAL_RATING_NUMERICAL: name = 'numerical ratings'
            elif service_type == HC.LOCAL_BOORU: name = 'booru'
            elif service_type == HC.IPFS: name = 'ipfs'
            else: continue
            
            if name not in listbook_dict:
                
                listbook = ClientGUICommon.ListBook( parent_listbook )
                
                listbook_dict[ name ] = listbook
                
                parent_listbook.AddPage( name, name, listbook )
                
            
            listbook = listbook_dict[ name ]
            
            name = service.GetName()
            
            listbook.AddPageArgs( name, name, self._Panel, ( listbook, self._controller, service.GetServiceKey() ), {} )
            
        
    
    def EventPageChanged( self, event ):
        
        wx.PostEvent( self.GetParent(), CC.SizeChangedEvent( -1 ) )
        
    
    def DoGetBestSize( self ):
        
        # this overrides the py stub in ScrolledPanel, which allows for unusual scroll behaviour driven by whatever this returns
        
        # wx.Notebook isn't expanding on page change and hence increasing min/virtual size and so on to the scrollable panel above, nullifying the neat expand-on-change-page event
        # so, until I write my own or figure out a clever solution, let's just force it
        
        if hasattr( self, '_notebook' ):
            
            current_page = self._notebook.GetCurrentPage()
            
            ( notebook_width, notebook_height ) = self._notebook.GetSize()
            ( page_width, page_height ) = current_page.GetSize()
            
            extra_width = notebook_width - page_width
            extra_height = notebook_height - page_height
            
            ( page_best_width, page_best_height ) = current_page.GetBestSize()
            
            best_size = ( page_best_width + extra_width, page_best_height + extra_height )
            
            return best_size
            
        else:
            
            return ( -1, -1 )
            
        
    
    def EventEdit( self, event ):
        
        original_pause_status = HC.options[ 'pause_repo_sync' ]
        
        HC.options[ 'pause_repo_sync' ] = True
        
        try:
            
            import ClientGUIDialogsManage
            
            with ClientGUIDialogsManage.DialogManageServices( self ) as dlg:
                
                dlg.ShowModal()
                
            
        except: wx.MessageBox( traceback.format_exc() )
        
        HC.options[ 'pause_repo_sync' ] = original_pause_status
        
    
    def RefreshServices( self ):
        
        self._InitialiseServices()
        
    
    class _Panel( wx.Panel ):
        
        def __init__( self, parent, controller, service_key ):
            
            wx.Panel.__init__( self, parent )
            
            self._controller = controller
            self._service_key = service_key
            
            self._service = self._controller.GetServicesManager().GetService( service_key )
            
            service_type = self._service.GetServiceType()
            
            if service_type in HC.REPOSITORIES + HC.LOCAL_SERVICES + [ HC.IPFS ]:
                
                self._info_panel = ClientGUICommon.StaticBox( self, 'service information' )
                
                if service_type in HC.FILE_SERVICES: 
                    
                    self._files_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                    if service_type in ( HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ):
                        
                        self._deleted_files_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                        
                    
                elif service_type in HC.TAG_SERVICES:
                    
                    self._tags_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                    if service_type == HC.TAG_REPOSITORY:
                        
                        self._deleted_tags_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                        
                    
                elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    self._ratings_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                elif service_type == HC.LOCAL_BOORU:
                    
                    self._num_shares = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                    self._bytes = ClientGUICommon.Gauge( self._info_panel )
                    
                    self._bytes_text = wx.StaticText( self._info_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                    
                
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                self._permissions_panel = ClientGUICommon.StaticBox( self, 'service permissions' )
                
                self._account_type = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER )
                
                self._age = ClientGUICommon.Gauge( self._permissions_panel )
                
                self._age_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                
                self._bytes = ClientGUICommon.Gauge( self._permissions_panel )
                
                self._bytes_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                
                self._requests = ClientGUICommon.Gauge( self._permissions_panel )
                
                self._requests_text = wx.StaticText( self._permissions_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                
            
            if service_type in HC.REPOSITORIES:
                
                self._synchro_panel = ClientGUICommon.StaticBox( self, 'repository synchronisation' )
                
                self._updates = ClientGUICommon.Gauge( self._synchro_panel )
                
                self._updates_text = wx.StaticText( self._synchro_panel, style = wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE )
                
                self._immediate_sync = wx.Button( self._synchro_panel, label = 'sync now' )
                self._immediate_sync.Bind( wx.EVT_BUTTON, self.EventImmediateSync)
                
            
            if service_type == HC.LOCAL_BOORU:
                
                self._booru_shares_panel = ClientGUICommon.StaticBox( self, 'shares' )
                
                self._booru_shares = ClientGUICommon.SaneListCtrl( self._booru_shares_panel, -1, [ ( 'title', 110 ), ( 'text', -1 ), ( 'expires', 170 ), ( 'num files', 70 ) ], delete_key_callback = self.DeleteBoorus, activation_callback = self.EditBoorus )
                
                self._booru_open_search = wx.Button( self._booru_shares_panel, label = 'open share in new page' )
                self._booru_open_search.Bind( wx.EVT_BUTTON, self.EventBooruOpenSearch )
                
                self._copy_internal_share_link = wx.Button( self._booru_shares_panel, label = 'copy internal share link' )
                self._copy_internal_share_link.Bind( wx.EVT_BUTTON, self.EventCopyInternalShareURL )
                
                self._copy_external_share_link = wx.Button( self._booru_shares_panel, label = 'copy external share link' )
                self._copy_external_share_link.Bind( wx.EVT_BUTTON, self.EventCopyExternalShareURL )
                
                self._booru_edit = wx.Button( self._booru_shares_panel, label = 'edit' )
                self._booru_edit.Bind( wx.EVT_BUTTON, self.EventBooruEdit )
                
                self._booru_delete = wx.Button( self._booru_shares_panel, label = 'delete' )
                self._booru_delete.Bind( wx.EVT_BUTTON, self.EventBooruDelete )
                
            
            if service_type == HC.IPFS:
                
                self._ipfs_shares_panel = ClientGUICommon.StaticBox( self, 'pinned directories' )
                
                self._ipfs_shares = ClientGUICommon.SaneListCtrl( self._ipfs_shares_panel, -1, [ ( 'multihash', 110 ), ( 'num files', 70 ), ( 'total size', 70 ), ( 'note', 200 ) ], delete_key_callback = self.UnpinIPFSDirectories, activation_callback = self.EditIPFSNotes )
                
                self._ipfs_open_search = wx.Button( self._ipfs_shares_panel, label = 'open share in new page' )
                self._ipfs_open_search.Bind( wx.EVT_BUTTON, self.EventIPFSOpenSearch )
                
                self._ipfs_set_note = wx.Button( self._ipfs_shares_panel, label = 'set note' )
                self._ipfs_set_note.Bind( wx.EVT_BUTTON, self.EventIPFSSetNote )
                
                self._copy_multihash = wx.Button( self._ipfs_shares_panel, label = 'copy multihash' )
                self._copy_multihash.Bind( wx.EVT_BUTTON, self.EventIPFSCopyMultihash )
                
                self._ipfs_delete = wx.Button( self._ipfs_shares_panel, label = 'unpin' )
                self._ipfs_delete.Bind( wx.EVT_BUTTON, self.EventIPFSUnpin )
                
            
            if service_type in HC.TAG_SERVICES:
                
                self._service_wide_update = wx.Button( self, label = 'advanced service-wide operation' )
                self._service_wide_update.Bind( wx.EVT_BUTTON, self.EventServiceWideUpdate )
                
            
            if self._service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
                
                self._delete_local_deleted = wx.Button( self, label = 'clear deleted file record' )
                self._delete_local_deleted.SetToolTipString( 'Command the client to forget which files it has deleted, resetting all the \'exclude previously deleted files\' checks.' )
                self._delete_local_deleted.Bind( wx.EVT_BUTTON, self.EventDeleteLocalDeleted )
                
            
            if self._service_key == CC.TRASH_SERVICE_KEY:
                
                self._clear_trash = wx.Button( self, label = 'clear trash' )
                self._clear_trash.Bind( wx.EVT_BUTTON, self.EventClearTrash )
                
            
            if service_type == HC.SERVER_ADMIN:
                
                self._init = wx.Button( self, label = 'initialise server' )
                self._init.Bind( wx.EVT_BUTTON, self.EventServerInitialise )
                
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                self._refresh = wx.Button( self, label = 'refresh account' )
                self._refresh.Bind( wx.EVT_BUTTON, self.EventServiceRefreshAccount )
                
                self._copy_account_key = wx.Button( self, label = 'copy account key' )
                self._copy_account_key.Bind( wx.EVT_BUTTON, self.EventCopyAccountKey )
                
            
            #
            
            self._DisplayService()
            
            #
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            if service_type in HC.REPOSITORIES + HC.LOCAL_SERVICES + [ HC.IPFS ]:
                
                if service_type in HC.FILE_SERVICES:
                    
                    self._info_panel.AddF( self._files_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                    if service_type in ( HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ):
                        
                        self._info_panel.AddF( self._deleted_files_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                        
                    
                elif service_type in HC.TAG_SERVICES:
                    
                    self._info_panel.AddF( self._tags_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                    if service_type == HC.TAG_REPOSITORY:
                        
                        self._info_panel.AddF( self._deleted_tags_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                        
                    
                elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
                    self._info_panel.AddF( self._ratings_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                elif service_type == HC.LOCAL_BOORU:
                    
                    self._info_panel.AddF( self._num_shares, CC.FLAGS_EXPAND_PERPENDICULAR )
                    self._info_panel.AddF( self._bytes, CC.FLAGS_EXPAND_PERPENDICULAR )
                    self._info_panel.AddF( self._bytes_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
                vbox.AddF( self._info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                self._permissions_panel.AddF( self._account_type, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._permissions_panel.AddF( self._age, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._permissions_panel.AddF( self._age_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._permissions_panel.AddF( self._bytes, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._permissions_panel.AddF( self._bytes_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._permissions_panel.AddF( self._requests, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._permissions_panel.AddF( self._requests_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                vbox.AddF( self._permissions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            if service_type in HC.REPOSITORIES:
                
                self._synchro_panel.AddF( self._updates, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._synchro_panel.AddF( self._updates_text, CC.FLAGS_EXPAND_PERPENDICULAR )
                self._synchro_panel.AddF( self._immediate_sync, CC.FLAGS_LONE_BUTTON )
                
                vbox.AddF( self._synchro_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            if service_type == HC.LOCAL_BOORU:
                
                self._booru_shares_panel.AddF( self._booru_shares, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                b_box = wx.BoxSizer( wx.HORIZONTAL )
                b_box.AddF( self._booru_open_search, CC.FLAGS_VCENTER )
                b_box.AddF( self._copy_internal_share_link, CC.FLAGS_VCENTER )
                b_box.AddF( self._copy_external_share_link, CC.FLAGS_VCENTER )
                b_box.AddF( self._booru_edit, CC.FLAGS_VCENTER )
                b_box.AddF( self._booru_delete, CC.FLAGS_VCENTER )
                
                self._booru_shares_panel.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
                
                vbox.AddF( self._booru_shares_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
            
            if service_type == HC.IPFS:
                
                self._ipfs_shares_panel.AddF( self._ipfs_shares, CC.FLAGS_EXPAND_BOTH_WAYS )
                
                b_box = wx.BoxSizer( wx.HORIZONTAL )
                b_box.AddF( self._ipfs_open_search, CC.FLAGS_VCENTER )
                b_box.AddF( self._ipfs_set_note, CC.FLAGS_VCENTER )
                b_box.AddF( self._copy_multihash, CC.FLAGS_VCENTER )
                b_box.AddF( self._ipfs_delete, CC.FLAGS_VCENTER )
                
                self._ipfs_shares_panel.AddF( b_box, CC.FLAGS_BUTTON_SIZER )
                
                vbox.AddF( self._ipfs_shares_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
            
            if service_type in HC.RESTRICTED_SERVICES + [ HC.LOCAL_TAG ] or self._service_key in ( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, CC.TRASH_SERVICE_KEY ):
                
                repo_buttons_hbox = wx.BoxSizer( wx.HORIZONTAL )
                
                if self._service_key == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
                    
                    repo_buttons_hbox.AddF( self._delete_local_deleted, CC.FLAGS_VCENTER )
                    
                
                if self._service_key == CC.TRASH_SERVICE_KEY:
                    
                    repo_buttons_hbox.AddF( self._clear_trash, CC.FLAGS_VCENTER )
                    
                
                if service_type in HC.TAG_SERVICES:
                    
                    repo_buttons_hbox.AddF( self._service_wide_update, CC.FLAGS_VCENTER )
                    
                
                if service_type == HC.SERVER_ADMIN:
                    
                    repo_buttons_hbox.AddF( self._init, CC.FLAGS_VCENTER )
                    
                
                if service_type in HC.RESTRICTED_SERVICES:
                    
                    repo_buttons_hbox.AddF( self._refresh, CC.FLAGS_VCENTER )
                    repo_buttons_hbox.AddF( self._copy_account_key, CC.FLAGS_VCENTER )
                    
                
                vbox.AddF( repo_buttons_hbox, CC.FLAGS_BUTTON_SIZER )
                
            
            self.SetSizer( vbox )
            
            self._timer_updates = wx.Timer( self, id = CC.ID_TIMER_UPDATES )
            
            if service_type in HC.REPOSITORIES:
                
                self.Bind( wx.EVT_TIMER, self.TIMEREventUpdates, id = CC.ID_TIMER_UPDATES )
                
                self._timer_updates.Start( 1000, wx.TIMER_CONTINUOUS )
                
            
            self._controller.sub( self, 'ProcessServiceUpdates', 'service_updates_gui' )
            if service_type == HC.LOCAL_BOORU: self._controller.sub( self, 'RefreshLocalBooruShares', 'refresh_local_booru_shares' )
            
        
        def _DisplayAccountInfo( self ):
            
            service_type = self._service.GetServiceType()
            
            now = HydrusData.GetNow()
            
            if service_type == HC.LOCAL_BOORU:
                
                info = self._service.GetInfo()
                
                max_monthly_data = info[ 'max_monthly_data' ]
                used_monthly_data = info[ 'used_monthly_data' ]
                used_monthly_requests = info[ 'used_monthly_requests' ]
                
                if used_monthly_requests == 0: monthly_requests_text = ''
                else: monthly_requests_text = ' in ' + HydrusData.ConvertIntToPrettyString( used_monthly_requests ) + ' requests'
                
                if max_monthly_data is None:
                    
                    self._bytes.Hide()
                    
                    self._bytes_text.SetLabelText( 'used ' + HydrusData.ConvertIntToBytes( used_monthly_data ) + monthly_requests_text + ' this month' )
                    
                else:
                    
                    self._bytes.Show()
                    
                    self._bytes.SetRange( max_monthly_data )
                    self._bytes.SetValue( used_monthly_data )
                    
                    self._bytes_text.SetLabelText( 'used ' + HydrusData.ConvertValueRangeToPrettyString( used_monthly_data, max_monthly_data ) + monthly_requests_text + ' this month' )
                    
                
            
            if service_type in HC.RESTRICTED_SERVICES:
                
                account = self._service.GetInfo( 'account' )
                
                account_type = account.GetAccountType()
                
                account_type_string = account_type.ConvertToString()
                
                if self._account_type.GetLabelText() != account_type_string:
                    
                    self._account_type.SetLabelText( account_type_string )
                    
                    self._account_type.Wrap( 400 )
                    
                
                created = account.GetCreated()
                expires = account.GetExpires()
                
                if expires is None: self._age.Hide()
                else:
                    
                    self._age.Show()
                    
                    self._age.SetRange( expires - created )
                    self._age.SetValue( min( now - created, expires - created ) )
                    
                
                self._age_text.SetLabelText( account.GetExpiresString() )
                
                max_num_bytes = account_type.GetMaxBytes()
                max_num_requests = account_type.GetMaxRequests()
                
                used_bytes = account.GetUsedBytes()
                used_requests = account.GetUsedRequests()
                
                if max_num_bytes is None: self._bytes.Hide()
                else:
                    
                    self._bytes.Show()
                    
                    self._bytes.SetRange( max_num_bytes )
                    self._bytes.SetValue( used_bytes )
                    
                
                self._bytes_text.SetLabelText( account.GetUsedBytesString() )
                
                if max_num_requests is None: self._requests.Hide()
                else:
                    
                    self._requests.Show()
                    
                    self._requests.SetRange( max_num_requests )
                    self._requests.SetValue( min( used_requests, max_num_requests ) )
                    
                
                self._requests_text.SetLabelText( account.GetUsedRequestsString() )
                
                if service_type in HC.REPOSITORIES:
                    
                    ( first_timestamp, next_download_timestamp, next_processing_timestamp ) = self._service.GetTimestamps()
                    
                    if first_timestamp is None:
                        
                        num_updates = 0
                        num_updates_downloaded = 0
                        
                        self._updates.SetValue( 0 )
                        
                    else:
                        
                        num_updates = ( now - first_timestamp ) / HC.UPDATE_DURATION
                        num_updates_downloaded = ( next_download_timestamp - first_timestamp ) / HC.UPDATE_DURATION
                        
                        self._updates.SetRange( num_updates )
                        self._updates.SetValue( num_updates_downloaded )
                        
                    
                    self._updates_text.SetLabelText( self._service.GetUpdateStatus() )
                    
                    if account.HasPermission( HC.RESOLVE_PETITIONS ):
                        
                        self._immediate_sync.Show()
                        
                    else:
                        
                        self._immediate_sync.Hide()
                        
                    
                
                self._refresh.Enable()
                
                if account.HasAccountKey(): self._copy_account_key.Enable()
                else: self._copy_account_key.Disable()
                
            
        
        def _DisplayService( self ):
            
            service_type = self._service.GetServiceType()
            
            self._DisplayAccountInfo()
            
            if service_type in HC.REPOSITORIES + HC.LOCAL_SERVICES + [ HC.IPFS ]:
                
                service_info = self._controller.Read( 'service_info', self._service_key )
                
                if service_type in HC.FILE_SERVICES:
                    
                    num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
                    total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
                    
                    self._files_text.SetLabelText( HydrusData.ConvertIntToPrettyString( num_files ) + ' files, totalling ' + HydrusData.ConvertIntToBytes( total_size ) )
                    
                    if service_type in ( HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ):
                        
                        num_deleted_files = service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ]
                        
                        self._deleted_files_text.SetLabelText( HydrusData.ConvertIntToPrettyString( num_deleted_files ) + ' deleted files' )
                        
                    
                elif service_type in HC.TAG_SERVICES:
                    
                    num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
                    num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
                    num_mappings = service_info[ HC.SERVICE_INFO_NUM_MAPPINGS ]
                    
                    self._tags_text.SetLabelText( HydrusData.ConvertIntToPrettyString( num_files ) + ' hashes, ' + HydrusData.ConvertIntToPrettyString( num_tags ) + ' tags, totalling ' + HydrusData.ConvertIntToPrettyString( num_mappings ) + ' mappings' )
                    
                    if service_type == HC.TAG_REPOSITORY:
                        
                        num_deleted_mappings = service_info[ HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ]
                        
                        self._deleted_tags_text.SetLabelText( HydrusData.ConvertIntToPrettyString( num_deleted_mappings ) + ' deleted mappings' )
                        
                    
                elif service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                    
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
                    
                
            
            if service_type == HC.SERVER_ADMIN:
                
                if self._service.IsInitialised():
                    
                    self._init.Hide()
                    self._refresh.Show()
                    
                else:
                    
                    self._init.Show()
                    self._refresh.Hide()
                    
                
            
        
        def DeleteBoorus( self ):
            
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
            
        
        def EventCopyAccountKey( self, event ):
            
            account_key = self._service.GetInfo( 'account' ).GetAccountKey()
            
            account_key_hex = account_key.encode( 'hex' )
            
            self._controller.pub( 'clipboard', 'text', account_key_hex )
            
        
        def EventCopyExternalShareURL( self, event ):
            
            shares = self._booru_shares.GetSelectedClientData()
            
            if len( shares ) > 0:
                
                ( name, text, timeout, ( num_hashes, hashes, share_key ) ) = shares[0]
                
                info = self._service.GetInfo()
                
                external_ip = HydrusNATPunch.GetExternalIP() # eventually check for optional host replacement here
                
                external_port = info[ 'upnp' ]
                
                if external_port is None: external_port = info[ 'port' ]
                
                url = 'http://' + external_ip + ':' + str( external_port ) + '/gallery?share_key=' + share_key.encode( 'hex' )
                
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
                
                multihash_prefix = self._service.GetInfo( 'multihash_prefix' )
                
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
                
            
        
        def EventServerInitialise( self, event ):
            
            service_key = self._service.GetServiceKey()
            service_type = self._service.GetServiceType()
            name = self._service.GetName()
            
            response = self._service.Request( HC.GET, 'init' )
            
            access_key = response[ 'access_key' ]
            
            info_update = { 'access_key' : access_key }
            
            edit_log = [ HydrusData.EditLogActionEdit( service_key, ( service_key, service_type, name, info_update ) ) ]
            
            self._controller.Write( 'update_services', edit_log )
            
            ClientGUIFrames.ShowKeys( 'access', ( access_key, ) )
            
        
        def EventServiceRefreshAccount( self, event ):
            
            self._refresh.Disable()
            
            def do_it():
                
                try:
                    
                    response = self._service.Request( HC.GET, 'account' )
                    
                    account = response[ 'account' ]
                    
                    account.MakeFresh()
                    
                    self._controller.Write( 'service_updates', { self._service_key : [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_ACCOUNT, account ) ] } )
                    
                except:
                    
                    wx.CallAfter( self._refresh.Enable )
                    
                    raise
                    
                
            
            self._controller.CallToThread( do_it )
            
        
        def ProcessServiceUpdates( self, service_keys_to_service_updates ):
            
            for ( service_key, service_updates ) in service_keys_to_service_updates.items():
                
                for service_update in service_updates:
                    
                    if service_key == self._service_key:
                        
                        ( action, row ) = service_update.ToTuple()
                        
                        if action in ( HC.SERVICE_UPDATE_ACCOUNT, HC.SERVICE_UPDATE_REQUEST_MADE ):
                            
                            self._DisplayAccountInfo()
                            
                        else:
                            
                            self._DisplayService()
                            
                        
                        self.Layout()
                        
                    
                
            
        
        def RefreshLocalBooruShares( self ):
            
            self._DisplayService()
            
        
        def UnpinIPFSDirectories( self ):
            
            for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetSelectedClientData():
                
                self._service.UnpinDirectory( multihash )
                
            
            self._ipfs_shares.RemoveAllSelected()
            
        
        def TIMEREventUpdates( self, event ):
            
            try:
                
                self._updates_text.SetLabelText( self._service.GetUpdateStatus() )
                
            except wx.PyDeadObjectError:
                
                self._timer_updates.Stop()
                
            except:
                
                self._timer_updates.Stop()
                
                raise
                
            
        
    
