import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIFrames
import ClientGUIScrolledPanels
import ClientGUIPanels
import ClientTags
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import HydrusNATPunch
import os
import traceback
import wx

class AdvancedContentUpdatePanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    COPY = 0
    DELETE = 1
    DELETE_DELETED = 2
    
    ALL_MAPPINGS = 0
    SPECIFIC_MAPPINGS = 1
    SPECIFIC_NAMESPACE = 2
    NAMESPACED = 3
    UNNAMESPACED = 4
    
    def __init__( self, parent, service_key, hashes = None ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._service_key = service_key
        self._hashes = hashes
        
        service = HydrusGlobals.client_controller.GetServicesManager().GetService( self._service_key )
        
        self._service_name = service.GetName()
        
        self._command_panel = ClientGUICommon.StaticBox( self, 'database commands' )
        
        self._action_dropdown = ClientGUICommon.BetterChoice( self._command_panel )
        self._action_dropdown.Bind( wx.EVT_CHOICE, self.EventChoice )
        self._tag_type_dropdown = ClientGUICommon.BetterChoice( self._command_panel )
        self._action_text = wx.StaticText( self._command_panel, label = 'initialising' )
        self._service_key_dropdown = ClientGUICommon.BetterChoice( self._command_panel )
        
        self._go = ClientGUICommon.BetterButton( self._command_panel, 'Go!', self.Go )
        
        #
        
        self._hta_panel = ClientGUICommon.StaticBox( self, 'hydrus tag archives' )
        
        self._import_from_hta = ClientGUICommon.BetterButton( self._hta_panel, 'one-time mass import or delete using a hydrus tag archive', self.ImportFromHTA )
        self._export_to_hta = ClientGUICommon.BetterButton( self._hta_panel, 'export to hydrus tag archive', self.ExportToHTA )
        
        #
        
        services = [ service for service in HydrusGlobals.client_controller.GetServicesManager().GetServices( HC.TAG_SERVICES ) if service.GetServiceKey() != self._service_key ]
        
        if len( services ) > 0:
            
            self._action_dropdown.Append( 'copy', self.COPY )
            
        
        if self._service_key == CC.LOCAL_TAG_SERVICE_KEY:
            
            self._action_dropdown.Append( 'delete', self.DELETE )
            self._action_dropdown.Append( 'clear deleted record', self.DELETE_DELETED )
            
        
        self._action_dropdown.Select( 0 )
        
        #
        
        self._tag_type_dropdown.Append( 'all mappings', self.ALL_MAPPINGS )
        self._tag_type_dropdown.Append( 'all namespaced mappings', self.NAMESPACED )
        self._tag_type_dropdown.Append( 'all unnamespaced mappings', self.UNNAMESPACED )
        self._tag_type_dropdown.Append( 'specific tag\'s mappings', self.SPECIFIC_MAPPINGS )
        self._tag_type_dropdown.Append( 'specific namespace\'s mappings', self.SPECIFIC_NAMESPACE )
        
        self._tag_type_dropdown.Select( 0 )
        
        #
        
        for service in services:
            
            self._service_key_dropdown.Append( service.GetName(), service.GetServiceKey() )
            
        
        self._service_key_dropdown.Select( 0 )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._action_dropdown, CC.FLAGS_VCENTER )
        hbox.AddF( self._tag_type_dropdown, CC.FLAGS_VCENTER )
        hbox.AddF( self._action_text, CC.FLAGS_VCENTER )
        hbox.AddF( self._service_key_dropdown, CC.FLAGS_VCENTER )
        hbox.AddF( self._go, CC.FLAGS_VCENTER )
        
        self._command_panel.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        self._hta_panel.AddF( self._import_from_hta, CC.FLAGS_LONE_BUTTON )
        self._hta_panel.AddF( self._export_to_hta, CC.FLAGS_LONE_BUTTON )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        message = 'Regarding '
        
        if self._hashes is None:
            
            message += 'all'
            
        else:
            
            message += HydrusData.ConvertIntToPrettyString( len( self._hashes ) )
            
        
        message += ' files on ' + self._service_name
        
        title_st = wx.StaticText( self, label = message)
        
        title_st.Wrap( 540 )
        
        message = 'These advanced operations are powerful, so think before you click. They can lock up your client for a _long_ time, and are not undoable.'
        message += os.linesep * 2
        message += 'You may need to refresh your existing searches to see their effect.' 
        
        st = wx.StaticText( self, label = message )
        
        st.Wrap( 540 )
        
        vbox.AddF( title_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._command_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._hta_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self.EventChoice( None )
        
    
    def EventChoice( self, event ):
        
        data = self._action_dropdown.GetChoice()
        
        if data in ( self.DELETE, self.DELETE_DELETED ):
            
            self._action_text.SetLabelText( 'from ' + self._service_name )
            
            self._service_key_dropdown.Hide()
            
        else:
            
            self._action_text.SetLabelText( 'from ' + self._service_name + ' to')
            
            self._service_key_dropdown.Show()
            
        
        self.Layout()
        
    
    def ExportToHTA( self ):
        
        ClientTags.ExportToHTA( self, self._service_key, self._hashes )
        
    
    def Go( self ):
        
        # at some point, rewrite this to cope with multiple tags. setsometag is ready to go on that front
        # this should prob be with a listbox so people can enter their new multiple tags in several separate goes, rather than overwriting every time
        
        action = self._action_dropdown.GetChoice()
        
        tag_type = self._tag_type_dropdown.GetChoice()
        
        if tag_type == self.ALL_MAPPINGS:
            
            tag = None
            
        elif tag_type == self.SPECIFIC_MAPPINGS:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter tag' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    entry = dlg.GetValue()
                    
                    tag = ( 'tag', entry )
                    
                else:
                    
                    return
                    
                
            
        elif tag_type == self.SPECIFIC_NAMESPACE:
            
            with ClientGUIDialogs.DialogTextEntry( self, 'Enter namespace' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    entry = dlg.GetValue()
                    
                    if entry.endswith( ':' ): entry = entry[:-1]
                    
                    tag = ( 'namespace', entry )
                    
                else:
                    
                    return
                    
                
            
        elif tag_type == self.NAMESPACED:
            
            tag = ( 'namespaced', None )
            
        elif tag_type == self.UNNAMESPACED:
            
            tag = ( 'unnamespaced', None )
            
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure?' ) as dlg:
            
            if dlg.ShowModal() != wx.ID_YES: return
            
        
        if action == self.COPY:
            
            service_key_target = self._service_key_dropdown.GetChoice()
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'copy', ( tag, self._hashes, service_key_target ) ) )
            
        elif action == self.DELETE:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete', ( tag, self._hashes ) ) )
            
        elif action == self.DELETE_DELETED:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', ( tag, self._hashes ) ) )
            
        
        service_keys_to_content_updates = { self._service_key : [ content_update ] }
        
        HydrusGlobals.client_controller.Write( 'content_updates', service_keys_to_content_updates )
        
    
    def ImportFromHTA( self ):
        
        text = 'Select the Hydrus Tag Archive\'s location.'
        
        with wx.FileDialog( self, message = text, style = wx.FD_OPEN ) as dlg_file:
            
            if dlg_file.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg_file.GetPath() )
                
                ClientTags.ImportFromHTA( self, path, self._service_key, self._hashes )
                
            
        
    
class ReviewServicesPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._notebook = wx.Notebook( self )
        
        self._local_listbook = ClientGUICommon.ListBook( self._notebook )
        self._remote_listbook = ClientGUICommon.ListBook( self._notebook )
        
        self._notebook.AddPage( self._local_listbook, 'local' )
        self._notebook.AddPage( self._remote_listbook, 'remote' )
        
        self._InitialiseServices()
        
        self.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.EventPageChanged )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._controller.sub( self, 'RefreshServices', 'notify_new_services_gui' )
        
    
    def _InitialiseServices( self ):
        
        lb = self._notebook.GetCurrentPage()
        
        if lb.GetPageCount() == 0:
            
            previous_service_key = CC.LOCAL_FILE_SERVICE_KEY
            
        else:
            
            page = lb.GetCurrentPage().GetCurrentPage()
            
            previous_service_key = page.GetServiceKey()
            
        
        self._local_listbook.DeleteAllPages()
        self._remote_listbook.DeleteAllPages()
        
        listbook_dict = {}
        
        services = self._controller.GetServicesManager().GetServices( randomised = False )
        
        lb_to_select = None
        service_type_name_to_select = None
        service_type_lb = None
        service_name_to_select = None
        
        for service in services:
            
            service_type = service.GetServiceType()
            
            if service_type in HC.LOCAL_SERVICES: parent_listbook = self._local_listbook
            else: parent_listbook = self._remote_listbook
            
            if service_type == HC.TAG_REPOSITORY: service_type_name = 'tag repositories'
            elif service_type == HC.FILE_REPOSITORY: service_type_name = 'file repositories'
            elif service_type == HC.MESSAGE_DEPOT: service_type_name = 'message depots'
            elif service_type == HC.SERVER_ADMIN: service_type_name = 'administrative servers'
            elif service_type in HC.LOCAL_FILE_SERVICES: service_type_name = 'files'
            elif service_type == HC.LOCAL_TAG: service_type_name = 'tags'
            elif service_type == HC.LOCAL_RATING_LIKE: service_type_name = 'like/dislike ratings'
            elif service_type == HC.LOCAL_RATING_NUMERICAL: service_type_name = 'numerical ratings'
            elif service_type == HC.LOCAL_BOORU: service_type_name = 'booru'
            elif service_type == HC.IPFS: service_type_name = 'ipfs'
            else: continue
            
            if service_type_name not in listbook_dict:
                
                listbook = ClientGUICommon.ListBook( parent_listbook )
                
                listbook_dict[ service_type_name ] = listbook
                
                parent_listbook.AddPage( service_type_name, service_type_name, listbook )
                
            
            listbook = listbook_dict[ service_type_name ]
            
            name = service.GetName()
            
            panel_class = ClientGUIPanels.ReviewServicePanel
            
            listbook.AddPageArgs( name, name, panel_class, ( listbook, service ), {} )
            
            if service.GetServiceKey() == previous_service_key:
                
                lb_to_select = parent_listbook
                service_type_name_to_select = service_name_to_select
                service_type_lb = listbook
                name_to_select = name
                
            
        
        if lb_to_select is not None:
            
            if self._notebook.GetCurrentPage() != lb_to_select:
                
                selection = self._notebook.GetSelection()
                
                if selection == 0:
                    
                    self._notebook.SetSelection( 1 )
                    
                else:
                    
                    self._notebook.SetSelection( 0 )
                    
                
            
            lb_to_select.Select( service_name_to_select )
            
            service_type_lb.Select( name_to_select )
            
        
    
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
            
        
    
    def RefreshServices( self ):
        
        self._InitialiseServices()
        
    
