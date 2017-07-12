import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIFrames
import ClientGUIScrolledPanels
import ClientGUIPanels
import ClientGUITopLevelWindows
import ClientTags
import ClientThreading
import collections
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusNATPunch
import HydrusPaths
import os
import traceback
import webbrowser
import wx

class AdvancedContentUpdatePanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    COPY = 0
    DELETE = 1
    DELETE_DELETED = 2
    DELETE_FOR_DELETED_FILES = 3
    
    ALL_MAPPINGS = 0
    SPECIFIC_MAPPINGS = 1
    SPECIFIC_NAMESPACE = 2
    NAMESPACED = 3
    UNNAMESPACED = 4
    
    def __init__( self, parent, service_key, hashes = None ):
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._service_key = service_key
        self._hashes = hashes
        
        service = HG.client_controller.services_manager.GetService( self._service_key )
        
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
        
        services = [ service for service in HG.client_controller.services_manager.GetServices( HC.TAG_SERVICES ) if service.GetServiceKey() != self._service_key ]
        
        if len( services ) > 0:
            
            self._action_dropdown.Append( 'copy', self.COPY )
            
        
        if self._service_key == CC.LOCAL_TAG_SERVICE_KEY:
            
            self._action_dropdown.Append( 'delete', self.DELETE )
            self._action_dropdown.Append( 'clear deleted record', self.DELETE_DELETED )
            self._action_dropdown.Append( 'delete from deleted files', self.DELETE_FOR_DELETED_FILES )
            
        
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
        
        title_st = ClientGUICommon.BetterStaticText( self, message )
        
        title_st.Wrap( 540 )
        
        message = 'These advanced operations are powerful, so think before you click. They can lock up your client for a _long_ time, and are not undoable.'
        message += os.linesep * 2
        message += 'You may need to refresh your existing searches to see their effect.' 
        
        st = ClientGUICommon.BetterStaticText( self, message )
        
        st.Wrap( 540 )
        
        vbox.AddF( title_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._command_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._hta_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        self.EventChoice( None )
        
    
    def EventChoice( self, event ):
        
        data = self._action_dropdown.GetChoice()
        
        if data in ( self.DELETE, self.DELETE_DELETED, self.DELETE_FOR_DELETED_FILES ):
            
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
            
        elif action == self.DELETE_FOR_DELETED_FILES:
            
            content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_for_deleted_files', ( tag, self._hashes ) ) )
            
        
        service_keys_to_content_updates = { self._service_key : [ content_update ] }
        
        HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
        
    
    def ImportFromHTA( self ):
        
        text = 'Select the Hydrus Tag Archive\'s location.'
        
        with wx.FileDialog( self, message = text, style = wx.FD_OPEN ) as dlg_file:
            
            if dlg_file.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg_file.GetPath() )
                
                ClientTags.ImportFromHTA( self, path, self._service_key, self._hashes )
                
            
        
    
class ReviewAllBandwidthPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._bandwidths = ClientGUICommon.SaneListCtrlForSingleObject( self, 360, [ ( 'context', -1 ), ( 'context type', 100 ), ( 'current usage', 100 ), ( 'past 24 hours', 100 ), ( 'this month', 100 ) ], activation_callback = self.ShowNetworkContext )
        
        self._bandwidths.SetMinSize( ( 640, 360 ) )
        
        # a button/checkbox to say 'show only those with data in the past 30 days'
        # a button to say 'delete all record of this context'
        
        #
        
        for ( network_context, bandwidth_tracker ) in self._controller.network_engine.bandwidth_manager.GetNetworkContextsAndBandwidthTrackersForUser():
            
            ( display_tuple, sort_tuple ) = self._GetTuples( network_context, bandwidth_tracker )
            
            self._bandwidths.Append( display_tuple, sort_tuple, network_context )
            
        
        self._bandwidths.SortListItems( 0 )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._bandwidths, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _GetTuples( self, network_context, bandwidth_tracker ):
        
        sortable_network_context = ( network_context.context_type, network_context.context_data )
        sortable_context_type = CC.network_context_type_string_lookup[ network_context.context_type ]
        current_usage = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 )
        day_usage = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 86400 )
        month_usage = bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None )
        
        pretty_network_context = network_context.ToUnicode()
        pretty_context_type = CC.network_context_type_string_lookup[ network_context.context_type ]
        
        if current_usage == 0:
            
            pretty_current_usage = ''
            
        else:
            
            pretty_current_usage = HydrusData.ConvertIntToBytes( current_usage ) + '/s'
            
        
        pretty_day_usage = HydrusData.ConvertIntToBytes( day_usage )
        pretty_month_usage = HydrusData.ConvertIntToBytes( month_usage )
        
        return ( ( pretty_network_context, pretty_context_type, pretty_current_usage, pretty_day_usage, pretty_month_usage ), ( sortable_network_context, sortable_context_type, current_usage, day_usage, month_usage ) )
        
    
    def ShowNetworkContext( self ):
        
        for network_context in self._bandwidths.GetObjects( only_selected = True ):
            
            frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self._controller.GetGUI(), 'review bandwidth for ' + network_context.ToUnicode() )
            
            panel = ReviewNetworkContextBandwidthPanel( frame, self._controller, network_context )
            
            frame.SetPanel( panel )
            
        
    
class ReviewNetworkContextBandwidthPanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller, network_context ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        self._network_context = network_context
        
        self._bandwidth_tracker = self._controller.network_engine.bandwidth_manager.GetTracker( self._network_context )
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'description' )
        
        self._name = ClientGUICommon.BetterStaticText( info_panel, label = self._network_context.ToUnicode() )
        self._description = ClientGUICommon.BetterStaticText( info_panel, label = CC.network_context_type_description_lookup[ self._network_context.context_type ] )
        
        #
        
        usage_panel = ClientGUICommon.StaticBox( self, 'usage' )
        
        self._current_usage_st = ClientGUICommon.BetterStaticText( usage_panel )
        
        self._time_delta_usage_bandwidth_type = ClientGUICommon.BetterChoice( usage_panel )
        self._time_delta_usage_time_delta = ClientGUICommon.TimeDeltaButton( usage_panel, days = True, hours = True, minutes = True, seconds = True )
        self._time_delta_usage_st = ClientGUICommon.BetterStaticText( usage_panel )
        
        #
        
        self._time_delta_usage_time_delta.SetValue( 86400 )
        
        for bandwidth_type in ( HC.BANDWIDTH_TYPE_DATA, HC.BANDWIDTH_TYPE_REQUESTS ):
            
            self._time_delta_usage_bandwidth_type.Append( HC.bandwidth_type_string_lookup[ bandwidth_type ], bandwidth_type )
            
        
        self._time_delta_usage_bandwidth_type.SelectClientData( HC.BANDWIDTH_TYPE_DATA )
        
        # usage this month (with dropdown to select previous months for all months on record)
        
        # rules panel
        # a way to show how much the current rules are used up--see review services for how this is already done
        # button to edit rules for this domain
        
        #
        
        info_panel.AddF( self._name, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.AddF( self._description, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._time_delta_usage_bandwidth_type, CC.FLAGS_VCENTER )
        hbox.AddF( ClientGUICommon.BetterStaticText( usage_panel, ' in the past ' ), CC.FLAGS_VCENTER )
        hbox.AddF( self._time_delta_usage_time_delta, CC.FLAGS_VCENTER )
        hbox.AddF( self._time_delta_usage_st, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        usage_panel.AddF( self._current_usage_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        usage_panel.AddF( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( usage_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        min_width = ClientData.ConvertTextToPixelWidth( self, 60 )
        
        self.SetMinSize( ( min_width, -1 ) )
        
        #
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventUpdate )
        
        self._move_hide_timer = wx.Timer( self )
        
        self._move_hide_timer.Start( 250, wx.TIMER_CONTINUOUS )
        
    
    def _Update( self ):
        
        current_usage = self._bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 )
        
        pretty_current_usage = 'current usage: ' + HydrusData.ConvertIntToBytes( current_usage ) + '/s'
        
        self._current_usage_st.SetLabelText( pretty_current_usage )
        
        #
        
        bandwidth_type = self._time_delta_usage_bandwidth_type.GetChoice()
        time_delta = self._time_delta_usage_time_delta.GetValue()
        
        time_delta_usage = self._bandwidth_tracker.GetUsage( bandwidth_type, time_delta )
        
        if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
            
            converter = HydrusData.ConvertIntToBytes
            
        elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
            
            converter = HydrusData.ConvertIntToPrettyString
            
        
        pretty_time_delta_usage = ': ' + converter( time_delta_usage )
        
        self._time_delta_usage_st.SetLabelText( pretty_time_delta_usage )
        
    
    def TIMEREventUpdate( self, event ):
        
        self._Update()
        
    
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
        
        services = self._controller.services_manager.GetServices( randomised = False )
        
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
        
        ClientGUITopLevelWindows.PostSizeChangedEvent( self )
        
    
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
        
    
class MigrateDatabasePanel( ClientGUIScrolledPanels.ReviewPanel ):
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        menu_items = []
        
        page_func = HydrusData.Call( webbrowser.open, 'file://' + HC.HELP_DIR + '/database_migration.html' )
        
        menu_items.append( ( 'normal', 'open the html migration help', 'Open the help page for database migration in your web browesr.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'current paths' )
        
        self._refresh_button = ClientGUICommon.BetterBitmapButton( info_panel, CC.GlobalBMPs.refresh, self._Update )
        
        self._current_install_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_db_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_media_paths_st = ClientGUICommon.BetterStaticText( info_panel )
        
        self._current_media_locations_listctrl = ClientGUICommon.SaneListCtrl( info_panel, 120, [ ( 'location', -1 ), ( 'portable?', 70 ), ( 'weight', 60 ), ( 'ideal usage', 160 ), ( 'current usage', 160 ) ] )
        
        # ways to:
        # increase/decrease ideal weight
        # force rebalance now
        # add new path
        # remove existing path
        # set/clear thumb locations
        # move whole db and portable paths (requires shutdown and user shortcut command line yes/no warning)
        
        # move the db and all portable client_files locations (provides warning about the shortcut and lets you copy the new location)
            # this will require a shutdown
        
        # rebalance files, listctrl
        # location | portable yes/no | weight | ideal percent
        # every change here, if valid, is saved immediately
        
        # store all resized thumbs in sep location
        # store all full_size thumbs in sep location
        
        # do rebalance now button, only enabled if there is work to do
            # should report to a stoppable job_key panel or something. text, gauge, stop button
        
        #
        
        help_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        st = ClientGUICommon.BetterStaticText( self, 'help for this panel -->' )
        
        st.SetForegroundColour( wx.Colour( 0, 0, 255 ) )
        
        help_hbox.AddF( st, CC.FLAGS_VCENTER )
        help_hbox.AddF( help_button, CC.FLAGS_VCENTER )
        
        #
        
        info_panel.AddF( self._refresh_button, CC.FLAGS_LONE_BUTTON )
        info_panel.AddF( self._current_install_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.AddF( self._current_db_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.AddF( self._current_media_paths_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.AddF( self._current_media_locations_listctrl, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.AddF( info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        min_width = ClientData.ConvertTextToPixelWidth( self, 90 )
        
        self.SetMinSize( ( min_width, -1 ) )
        
        self._Update()
        
    
    def _GenerateCurrentMediaTuples( self ):
        
        # ideal
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._controller.GetNewOptions().GetClientFilesLocationsToIdealWeights()
        
        # current
        
        prefixes_to_locations = HG.client_controller.Read( 'client_files_locations' )
        
        locations_to_file_weights = collections.Counter()
        locations_to_fs_thumb_weights = collections.Counter()
        locations_to_r_thumb_weights = collections.Counter()
        
        for ( prefix, location ) in prefixes_to_locations.items():
            
            if prefix.startswith( 'f' ):
                
                locations_to_file_weights[ location ] += 1
                
            
            if prefix.startswith( 't' ):
                
                locations_to_fs_thumb_weights[ location ] += 1
                
            
            if prefix.startswith( 'r' ):
                
                locations_to_r_thumb_weights[ location ] += 1
                
            
        
        #
        
        all_locations = set()
        
        all_locations.update( locations_to_ideal_weights.keys() )
        
        if resized_thumbnail_override is not None:
            
            all_locations.add( resized_thumbnail_override )
            
        
        if full_size_thumbnail_override is not None:
            
            all_locations.add( full_size_thumbnail_override )
            
        
        all_locations.update( locations_to_file_weights.keys() )
        all_locations.update( locations_to_fs_thumb_weights.keys() )
        all_locations.update( locations_to_r_thumb_weights.keys() )
        
        all_locations = list( all_locations )
        
        all_locations.sort()
        
        tuples = []
        
        total_ideal_weight = sum( locations_to_ideal_weights.values() )
        
        for location in all_locations:
            
            pretty_location = location
            
            portable_location = HydrusPaths.ConvertAbsPathToPortablePath( location )
            portable = not os.path.isabs( portable_location )
            
            if portable:
                
                pretty_portable = 'yes'
                
            else:
                
                pretty_portable = 'no'
                
            
            if location in locations_to_ideal_weights:
                
                ideal_weight = locations_to_ideal_weights[ location ]
                
                pretty_ideal_weight = str( ideal_weight )
                
            else:
                
                ideal_weight = 0
                
                pretty_ideal_weight = 'n/a'
                
            
            fp = locations_to_file_weights[ location ] / 256.0
            tp = locations_to_fs_thumb_weights[ location ] / 256.0
            rp = locations_to_r_thumb_weights[ location ] / 256.0
            
            p = HydrusData.ConvertFloatToPercentage
            
            current_usage = ( fp, tp, rp )
            
            usages = []
            
            if fp > 0:
                
                usages.append( p( fp ) + ' files' )
                
            
            if tp > 0 and tp != fp:
                
                usages.append( p( tp ) + ' full-size thumbnails' )
                
            
            if rp > 0 and rp != fp:
                
                usages.append( p( rp ) + ' resized thumbnails' )
                
            
            pretty_current_usage = ','.join( usages )
            
            if location in locations_to_ideal_weights:
                
                ideal_fp = locations_to_ideal_weights[ location ] / float( total_ideal_weight )
                
            else:
                
                ideal_fp = 0.0
                
            
            if full_size_thumbnail_override is not None and location == full_size_thumbnail_override:
                
                ideal_tp = 1.0
                
            else:
                
                ideal_tp = 0.0
                
            
            if resized_thumbnail_override is not None and location == resized_thumbnail_override:
                
                ideal_rp = 1.0
                
            else:
                
                ideal_rp = 0.0
                
            
            ideal_usage = ( ideal_fp, ideal_tp, ideal_rp )
            
            usages = []
            
            if ideal_fp > 0:
                
                usages.append( p( ideal_fp ) + ' files' )
                
            
            if ideal_tp > 0 and ideal_tp != ideal_fp:
                
                usages.append( p( ideal_tp ) + ' full-size thumbnails' )
                
            
            if ideal_rp > 0 and ideal_rp != ideal_fp:
                
                usages.append( p( ideal_rp ) + ' resized thumbnails' )
                
            
            pretty_ideal_usage = ','.join( usages )
            
            display_tuple = ( pretty_location, pretty_portable, pretty_ideal_weight, pretty_ideal_usage, pretty_current_usage )
            sort_tuple = ( location, portable, ideal_weight, ideal_usage, current_usage )
            
            tuples.append( ( display_tuple, sort_tuple ) )
            
        
        return tuples
        
    
    def _Update( self ):
        
        approx_total_db_size = self._controller.db.GetApproxTotalFileSize()
        
        self._current_db_path_st.SetLabelText( 'database (totalling about ' + HydrusData.ConvertIntToBytes( approx_total_db_size ) + '): ' + self._controller.GetDBDir() )
        self._current_install_path_st.SetLabelText( 'install: ' + HC.BASE_DIR )
        
        service_info = HG.client_controller.Read( 'service_info', CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
        
        all_local_files_total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
        
        approx_total_client_files = all_local_files_total_size * 1.1
        
        self._current_media_paths_st.SetLabelText( 'media (totalling about ' + HydrusData.ConvertIntToBytes( approx_total_client_files ) + '):' )
        
        self._current_media_locations_listctrl.DeleteAllItems()
        
        for ( display_tuple, sort_tuple ) in self._GenerateCurrentMediaTuples():
            
            self._current_media_locations_listctrl.Append( display_tuple, sort_tuple )
            
        
    
