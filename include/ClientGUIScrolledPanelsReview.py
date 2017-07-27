import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIFrames
import ClientGUIScrolledPanels
import ClientGUIScrolledPanelsEdit
import ClientGUIPanels
import ClientGUIPopupMessages
import ClientGUITopLevelWindows
import ClientNetworking
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

try:
    
    import ClientGUIMatPlotLib
    
    MATPLOTLIB_OK = True
    
except ImportError:
    
    MATPLOTLIB_OK = False
    

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
            
            if dlg.ShowModal() != wx.ID_YES:
                
                return
                
            
        
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
        
        self._history_time_delta_threshold = ClientGUICommon.TimeDeltaButton( self, days = True, hours = True, minutes = True, seconds = True )
        self._history_time_delta_threshold.Bind( ClientGUICommon.EVT_TIME_DELTA, self.EventTimeDeltaChanged )
        
        self._history_time_delta_none = wx.CheckBox( self, label = 'show all' )
        self._history_time_delta_none.Bind( wx.EVT_CHECKBOX, self.EventTimeDeltaChanged )
        
        self._bandwidths = ClientGUICommon.SaneListCtrlForSingleObject( self, 360, [ ( 'name', -1 ), ( 'type', 100 ), ( 'current usage', 100 ), ( 'past 24 hours', 100 ), ( 'this month', 100 ), ( 'has specific rules', 120 ) ], activation_callback = self.ShowNetworkContext )
        
        self._bandwidths.SetMinSize( ( 740, 360 ) )
        
        self._edit_default_bandwidth_rules_button = ClientGUICommon.BetterButton( self, 'edit default bandwidth rules', self._EditDefaultBandwidthRules )
        
        default_rules_help_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.help, self._ShowDefaultRulesHelp )
        default_rules_help_button.SetToolTipString( 'Show help regarding default bandwidth rules.' )
        
        self._delete_record_button = ClientGUICommon.BetterButton( self, 'delete selected history', self._DeleteNetworkContexts )
        
        #
        
        self._history_time_delta_threshold.SetValue( 86400 * 30 )
        
        self._bandwidths.SortListItems( 0 )
        
        self._update_timer = wx.Timer( self )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventUpdate )
        
        self._Update()
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( ClientGUICommon.BetterStaticText( self, 'Show network contexts with usage in the past: ' ), CC.FLAGS_VCENTER )
        hbox.AddF( self._history_time_delta_threshold, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.AddF( self._history_time_delta_none, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( self._edit_default_bandwidth_rules_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( default_rules_help_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._delete_record_button, CC.FLAGS_VCENTER )
        
        vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._bandwidths, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( vbox )
        
    
    def _DeleteNetworkContexts( self ):
        
        selected_network_contexts = self._bandwidths.GetObjects( only_selected = True )
        
        if len( selected_network_contexts ) > 0:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Are you sure? This will delete all bandwidth record for the selected network contexts.' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._controller.network_engine.bandwidth_manager.DeleteHistory( selected_network_contexts )
                    
                    self._Update()
                    
                
        
    
    def _EditDefaultBandwidthRules( self ):
        
        network_contexts_and_bandwidth_rules = self._controller.network_engine.bandwidth_manager.GetDefaultRules()
        
        choice_tuples = [ ( network_context.ToUnicode() + ' (' + str( len( bandwidth_rules.GetRules() ) ) + ' rules)', ( network_context, bandwidth_rules ) ) for ( network_context, bandwidth_rules ) in network_contexts_and_bandwidth_rules ]
        
        with ClientGUIDialogs.DialogSelectFromList( self, 'select network context', choice_tuples ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                ( network_context, bandwidth_rules ) = dlg.GetChoice()
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'edit bandwidth rules for ' + network_context.ToUnicode() ) as dlg_2:
                    
                    panel = ClientGUIScrolledPanelsEdit.EditBandwidthRulesPanel( dlg_2, bandwidth_rules )
                    
                    dlg_2.SetPanel( panel )
                    
                    if dlg_2.ShowModal() == wx.ID_OK:
                        
                        bandwidth_rules = panel.GetValue()
                        
                        self._controller.network_engine.bandwidth_manager.SetRules( network_context, bandwidth_rules )
                        
                    
                
            
        
    
    def _GetTuples( self, network_context, bandwidth_tracker ):
        
        has_rules = not self._controller.network_engine.bandwidth_manager.UsesDefaultRules( network_context )
        
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
        
        if has_rules:
            
            pretty_has_rules = 'yes'
            
        else:
            
            pretty_has_rules = ''
            
        
        return ( ( pretty_network_context, pretty_context_type, pretty_current_usage, pretty_day_usage, pretty_month_usage, pretty_has_rules ), ( sortable_network_context, sortable_context_type, current_usage, day_usage, month_usage, has_rules ) )
        
    
    def _ShowDefaultRulesHelp( self ):
        
        help = 'Network requests act in multiple contexts. Most use the \'global\' and \'web domain\' network contexts, but a hydrus server request, for instance, will add its own service-specific context, and a subscription will add both itself and its downloader.'
        help += os.linesep * 2
        help += 'If a network context does not have some specific rules set up, it will use its respective default, which may or may not have rules of its own. If you want to set general policy, like "Never download more than 1GB/day from any individual website," or "Limit the entire client to 2MB/s," do it through \'global\' and these defaults.'
        help += os.linesep * 2
        help += 'All contexts\' rules are consulted and have to pass before a request can do work. If you set a 200KB/s limit on a website domain and a 50KB/s limit on global, your download will only ever run at 50KB/s. To make sense, network contexts with broader scope should have more lenient rules.'
        help += os.linesep * 2
        help += 'There are two special \'instance\' contexts, for downloaders and threads. These represent individual queries, either a single gallery search or a single watched thread. It is useful to set rules for these so your searches will gather a fast initial sample of results in the first few minutes--so you can make sure you are happy with them--but otherwise trickle the rest in over time. This keeps your CPU and other bandwidth limits less hammered and helps to avoid accidental downloads of many thousands of small bad files or a few hundred gigantic files all in one go.'
        help += os.linesep * 2
        help += 'If you do not understand what is going on here, you can safely leave it alone. The default settings make for a _reasonable_ and polite profile that will not accidentally cause you to download way too much in one go or piss off servers by being too aggressive. The simplest way of throttling your client is by editing the rules for the global context.'
        
        wx.MessageBox( help )
        
    
    def _Update( self ):
        
        ( sort_col, sort_asc ) = self._bandwidths.GetSortState()
        
        selected_network_contexts = self._bandwidths.GetObjects( only_selected = True )
        
        self._bandwidths.DeleteAllItems()
        
        if self._history_time_delta_none.GetValue() == True:
            
            history_time_delta_threshold = None
            
        else:
            
            history_time_delta_threshold = self._history_time_delta_threshold.GetValue()
            
        
        network_contexts_and_bandwidth_trackers = self._controller.network_engine.bandwidth_manager.GetNetworkContextsAndBandwidthTrackersForUser( history_time_delta_threshold )
        
        for ( index, ( network_context, bandwidth_tracker ) ) in enumerate( network_contexts_and_bandwidth_trackers ):
            
            ( display_tuple, sort_tuple ) = self._GetTuples( network_context, bandwidth_tracker )
            
            self._bandwidths.Append( display_tuple, sort_tuple, network_context )
            
            if network_context in selected_network_contexts:
                
                self._bandwidths.Select( index )
                
            
        
        self._bandwidths.SortListItems( sort_col, sort_asc )
        
        timer_duration_s = max( len( network_contexts_and_bandwidth_trackers ), 20 )
        
        self._update_timer.Start( 1000 * timer_duration_s, wx.TIMER_ONE_SHOT )
        
    
    def EventTimeDeltaChanged( self, event ):
        
        if self._history_time_delta_none.GetValue() == True:
            
            self._history_time_delta_threshold.Disable()
            
        else:
            
            self._history_time_delta_threshold.Enable()
            
        
        self._Update()
        
    
    def TIMEREventUpdate( self, event ):
        
        self._Update()
        
    
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
        
        self._bandwidth_rules = self._controller.network_engine.bandwidth_manager.GetRules( self._network_context )
        self._bandwidth_tracker = self._controller.network_engine.bandwidth_manager.GetTracker( self._network_context )
        
        self._last_fetched_rule_rows = set()
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'description' )
        
        description = CC.network_context_type_description_lookup[ self._network_context.context_type ]
        
        self._name = ClientGUICommon.BetterStaticText( info_panel, label = self._network_context.ToUnicode() )
        self._description = ClientGUICommon.BetterStaticText( info_panel, label = description )
        
        #
        
        usage_panel = ClientGUICommon.StaticBox( self, 'usage' )
        
        self._current_usage_st = ClientGUICommon.BetterStaticText( usage_panel )
        
        self._time_delta_usage_bandwidth_type = ClientGUICommon.BetterChoice( usage_panel )
        self._time_delta_usage_time_delta = ClientGUICommon.TimeDeltaButton( usage_panel, days = True, hours = True, minutes = True, seconds = True )
        self._time_delta_usage_st = ClientGUICommon.BetterStaticText( usage_panel )
        
        #
        
        rules_panel = ClientGUICommon.StaticBox( self, 'rules' )
        
        self._uses_default_rules_st = ClientGUICommon.BetterStaticText( rules_panel, style = wx.ALIGN_CENTER )
        
        self._rules_rows_panel = wx.Panel( rules_panel )
        
        self._use_default_rules_button = ClientGUICommon.BetterButton( rules_panel, 'use default rules', self._UseDefaultRules )
        self._edit_rules_button = ClientGUICommon.BetterButton( rules_panel, 'edit rules', self._EditRules )
        
        #
        
        self._time_delta_usage_time_delta.SetValue( 86400 )
        
        for bandwidth_type in ( HC.BANDWIDTH_TYPE_DATA, HC.BANDWIDTH_TYPE_REQUESTS ):
            
            self._time_delta_usage_bandwidth_type.Append( HC.bandwidth_type_string_lookup[ bandwidth_type ], bandwidth_type )
            
        
        self._time_delta_usage_bandwidth_type.SelectClientData( HC.BANDWIDTH_TYPE_DATA )
        
        monthly_usage = self._bandwidth_tracker.GetMonthlyDataUsage()
        
        if len( monthly_usage ) > 0:
            
            if MATPLOTLIB_OK:
                
                self._barchart_canvas = ClientGUIMatPlotLib.BarChartBandwidthHistory( usage_panel, monthly_usage )
                
            else:
                
                self._barchart_canvas = ClientGUICommon.BetterStaticText( usage_panel, 'Could not find matplotlib, so cannot display bar chart here.' )
                
            
        else:
            
            self._barchart_canvas = ClientGUICommon.BetterStaticText( usage_panel, 'No usage yet, so no usage history to show.' )
            
        
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
        usage_panel.AddF( self._barchart_canvas, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._edit_rules_button, CC.FLAGS_SIZER_VCENTER )
        hbox.AddF( self._use_default_rules_button, CC.FLAGS_SIZER_VCENTER )
        
        rules_panel.AddF( self._uses_default_rules_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        rules_panel.AddF( self._rules_rows_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        rules_panel.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( usage_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( rules_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self._rules_rows_panel.Bind( wx.EVT_TIMER, self.TIMEREventUpdateRules )
        
        self._rules_timer = wx.Timer( self._rules_rows_panel )
        
        self._rules_timer.Start( 5000, wx.TIMER_CONTINUOUS )
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventUpdate )
        
        self._timer = wx.Timer( self )
        
        self._timer.Start( 1000, wx.TIMER_CONTINUOUS )
        
        self._UpdateRules()
        self._Update()
        
    
    def _EditRules( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit bandwidth rules for ' + self._network_context.ToUnicode() ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditBandwidthRulesPanel( dlg, self._bandwidth_rules )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._bandwidth_rules = panel.GetValue()
                
                self._controller.network_engine.bandwidth_manager.SetRules( self._network_context, self._bandwidth_rules )
                
                self._UpdateRules()
                
            
        
    
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
        
    
    def _UpdateRules( self ):
        
        changes_made = False
        
        if self._network_context.IsDefault() or self._network_context == ClientNetworking.GLOBAL_NETWORK_CONTEXT:
            
            if self._use_default_rules_button.IsShown():
                
                self._uses_default_rules_st.Hide()
                self._use_default_rules_button.Hide()
                
                changes_made = True
                
            
        else:
            
            if self._controller.network_engine.bandwidth_manager.UsesDefaultRules( self._network_context ):
                
                self._uses_default_rules_st.SetLabelText( 'uses default rules' )
                
                self._edit_rules_button.SetLabel( 'set specific rules' )
                
                if self._use_default_rules_button.IsShown():
                    
                    self._use_default_rules_button.Hide()
                    
                    changes_made = True
                    
                
            else:
                
                self._uses_default_rules_st.SetLabelText( 'has its own rules' )
                
                self._edit_rules_button.SetLabel( 'edit rules' )
                
                if not self._use_default_rules_button.IsShown():
                    
                    self._use_default_rules_button.Show()
                    
                    changes_made = True
                    
                
            
        
        rule_rows = self._bandwidth_rules.GetUsageStringsAndGaugeTuples( self._bandwidth_tracker, threshold = 0 )
        
        if rule_rows != self._last_fetched_rule_rows:
            
            self._last_fetched_rule_rows = rule_rows
            
            self._rules_rows_panel.DestroyChildren()
            
            vbox = wx.BoxSizer( wx.VERTICAL )
            
            for ( status, ( v, r ) ) in rule_rows:
                
                tg = ClientGUICommon.TextAndGauge( self._rules_rows_panel )
                
                tg.SetValue( status, v, r )
                
                vbox.AddF( tg, CC.FLAGS_EXPAND_PERPENDICULAR )
                
            
            self._rules_rows_panel.SetSizer( vbox )
            
            changes_made = True
            
        
        if changes_made:
            
            self.Layout()
            
            ClientGUITopLevelWindows.PostSizeChangedEvent( self )
            
        
    
    def _UseDefaultRules( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Are you sure you want to revert to using the default rules for this context?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._controller.network_engine.bandwidth_manager.DeleteRules( self._network_context )
                
                self._UpdateRules()
                
            
        
    
    def TIMEREventUpdate( self, event ):
        
        self._Update()
        
    
    def TIMEREventUpdateRules( self, event ):
        
        self._UpdateRules()
        
    
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
    
    RESIZED_RATIO = 0.012
    FULLSIZE_RATIO = 0.016
    
    def __init__( self, parent, controller ):
        
        self._controller = controller
        
        self._new_options = self._controller.GetNewOptions()
        
        ClientGUIScrolledPanels.ReviewPanel.__init__( self, parent )
        
        menu_items = []
        
        page_func = HydrusData.Call( webbrowser.open, 'file://' + HC.HELP_DIR + '/database_migration.html' )
        
        menu_items.append( ( 'normal', 'open the html migration help', 'Open the help page for database migration in your web browesr.', page_func ) )
        
        help_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.help, menu_items )
        
        #
        
        info_panel = ClientGUICommon.StaticBox( self, 'locations' )
        
        self._current_install_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_db_path_st = ClientGUICommon.BetterStaticText( info_panel )
        self._current_media_paths_st = ClientGUICommon.BetterStaticText( info_panel )
        
        self._current_media_locations_listctrl = ClientGUICommon.SaneListCtrl( info_panel, 120, [ ( 'location', -1 ), ( 'portable?', 70 ), ( 'free space', 70 ), ( 'weight', 50 ), ( 'ideal usage', 200 ), ( 'current usage', 200 ) ] )
        
        self._add_path_button = ClientGUICommon.BetterButton( info_panel, 'add location', self._AddPath )
        self._remove_path_button = ClientGUICommon.BetterButton( info_panel, 'empty/remove location', self._RemovePaths )
        self._increase_weight_button = ClientGUICommon.BetterButton( info_panel, 'increase weight', self._IncreaseWeight )
        self._decrease_weight_button = ClientGUICommon.BetterButton( info_panel, 'decrease weight', self._DecreaseWeight )
        self._rebalance_button = ClientGUICommon.BetterButton( info_panel, 'move files now', self._Rebalance )
        
        self._resized_thumbs_location = wx.TextCtrl( info_panel )
        self._resized_thumbs_location.Disable()
        
        self._fullsize_thumbs_location = wx.TextCtrl( info_panel )
        self._fullsize_thumbs_location.Disable()
        
        self._resized_thumbs_location_set = ClientGUICommon.BetterButton( info_panel, 'set', self._SetResizedThumbnailLocation )
        self._fullsize_thumbs_location_set = ClientGUICommon.BetterButton( info_panel, 'set', self._SetFullsizeThumbnailLocation )
        
        self._resized_thumbs_location_clear = ClientGUICommon.BetterButton( info_panel, 'clear', self._ClearResizedThumbnailLocation )
        self._fullsize_thumbs_location_clear = ClientGUICommon.BetterButton( info_panel, 'clear', self._ClearFullsizeThumbnailLocation )
        
        self._rebalance_status_st = ClientGUICommon.BetterStaticText( info_panel )
        
        # move whole db and portable paths (requires shutdown and user shortcut command line yes/no warning)
        
        #
        
        help_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        st = ClientGUICommon.BetterStaticText( self, 'help for this panel -->' )
        
        st.SetForegroundColour( wx.Colour( 0, 0, 255 ) )
        
        help_hbox.AddF( st, CC.FLAGS_VCENTER )
        help_hbox.AddF( help_button, CC.FLAGS_VCENTER )
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( self._add_path_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._remove_path_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._increase_weight_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._decrease_weight_button, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._rebalance_button, CC.FLAGS_VCENTER )
        
        r_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        r_hbox.AddF( ClientGUICommon.BetterStaticText( info_panel, 'resized thumbnail location' ), CC.FLAGS_VCENTER )
        r_hbox.AddF( self._resized_thumbs_location, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        r_hbox.AddF( self._resized_thumbs_location_set, CC.FLAGS_VCENTER )
        r_hbox.AddF( self._resized_thumbs_location_clear, CC.FLAGS_VCENTER )
        
        t_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        t_hbox.AddF( ClientGUICommon.BetterStaticText( info_panel, 'full-size thumbnail location' ), CC.FLAGS_VCENTER )
        t_hbox.AddF( self._fullsize_thumbs_location, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        t_hbox.AddF( self._fullsize_thumbs_location_set, CC.FLAGS_VCENTER )
        t_hbox.AddF( self._fullsize_thumbs_location_clear, CC.FLAGS_VCENTER )
        
        info_panel.AddF( self._current_install_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.AddF( self._current_db_path_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.AddF( self._current_media_paths_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.AddF( self._current_media_locations_listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        info_panel.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        info_panel.AddF( r_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.AddF( t_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        info_panel.AddF( self._rebalance_status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( help_hbox, CC.FLAGS_BUTTON_SIZER )
        vbox.AddF( info_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        min_width = ClientData.ConvertTextToPixelWidth( self, 100 )
        
        self.SetMinSize( ( min_width, -1 ) )
        
        self._Update()
        
    
    def _AddPath( self ):
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._new_options.GetClientFilesLocationsToIdealWeights()
        
        with wx.DirDialog( self, 'Select the location' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = HydrusData.ToUnicode( dlg.GetPath() )
                
                if path in locations_to_ideal_weights:
                    
                    wx.MessageBox( 'You already have that location entered!' )
                    
                    return
                    
                
                if path == resized_thumbnail_override or path == full_size_thumbnail_override:
                    
                    wx.MessageBox( 'That path is already used as a special thumbnail location--please choose another.' )
                    
                    return
                    
                
                self._new_options.SetClientFilesLocation( path, 1 )
                
                self._Update()
                
            
        
    
    def _AdjustWeight( self, amount ):
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._new_options.GetClientFilesLocationsToIdealWeights()
        
        adjustees = set()
        
        for ( location, portable, free_space, weight, gumpf, gumpf ) in self._current_media_locations_listctrl.GetSelectedClientData():
            
            if location in locations_to_ideal_weights:
                
                adjustees.add( location )
                
            
        
        if len( adjustees ) > 0:
            
            for location in adjustees:
                
                current_weight = locations_to_ideal_weights[ location ]
                
                new_amount = current_weight + amount
                
                if new_amount > 0:
                    
                    self._new_options.SetClientFilesLocation( location, new_amount )
                    
                
            
            self._Update()
            
        
    
    def _ClearFullsizeThumbnailLocation( self ):
        
        self._new_options.SetFullsizeThumbnailOverride( None )
        
        self._Update()
        
    
    def _ClearResizedThumbnailLocation( self ):
        
        self._new_options.SetResizedThumbnailOverride( None )
        
        self._Update()
        
    
    def _DecreaseWeight( self ):
        
        self._AdjustWeight( -1 )
        
    
    def _GenerateCurrentMediaTuples( self, approx_total_client_files ):
        
        f_space = approx_total_client_files
        r_space = approx_total_client_files * self.RESIZED_RATIO
        t_space = approx_total_client_files * self.FULLSIZE_RATIO
        
        # ideal
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._new_options.GetClientFilesLocationsToIdealWeights()
        
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
                
            
            free_space = HydrusPaths.GetFreeSpace( location )
            pretty_free_space = HydrusData.ConvertIntToBytes( free_space )
            
            fp = locations_to_file_weights[ location ] / 256.0
            tp = locations_to_fs_thumb_weights[ location ] / 256.0
            rp = locations_to_r_thumb_weights[ location ] / 256.0
            
            p = HydrusData.ConvertFloatToPercentage
            
            current_bytes = fp * f_space + tp * t_space + rp * r_space
            
            current_usage = ( fp, tp, rp )
            
            usages = []
            
            if fp > 0:
                
                usages.append( p( fp ) + ' files' )
                
            
            if tp > 0:
                
                usages.append( p( tp ) + ' full-size thumbnails' )
                
            
            if rp > 0:
                
                usages.append( p( rp ) + ' resized thumbnails' )
                
            
            if len( usages ) > 0:
                
                if fp == tp and tp == rp:
                    
                    usages = [ p( fp ) + ' everything' ]
                    
                
                pretty_current_usage = HydrusData.ConvertIntToBytes( current_bytes ) + ' - ' + ','.join( usages )
                
            else:
                
                pretty_current_usage = 'nothing'
                
            
            #
            
            if location in locations_to_ideal_weights:
                
                ideal_weight = locations_to_ideal_weights[ location ]
                
                pretty_ideal_weight = str( int( ideal_weight ) )
                
            else:
                
                ideal_weight = 0
                
                pretty_ideal_weight = 'n/a'
                
            
            if location in locations_to_ideal_weights:
                
                ideal_fp = locations_to_ideal_weights[ location ] / float( total_ideal_weight )
                
            else:
                
                ideal_fp = 0.0
                
            
            if full_size_thumbnail_override is None:
                
                ideal_tp = ideal_fp
                
            else:
                
                if location == full_size_thumbnail_override:
                    
                    ideal_tp = 1.0
                    
                else:
                    
                    ideal_tp = 0.0
                    
                
            
            if resized_thumbnail_override is None:
                
                ideal_rp = ideal_fp
                
            else:
                
                if location == resized_thumbnail_override:
                    
                    ideal_rp = 1.0
                    
                else:
                    
                    ideal_rp = 0.0
                    
                
            
            ideal_bytes = ideal_fp * f_space + ideal_tp * t_space + ideal_rp * r_space
            
            ideal_usage = ( ideal_fp, ideal_tp, ideal_rp )
            
            usages = []
            
            if ideal_fp > 0:
                
                usages.append( p( ideal_fp ) + ' files' )
                
            
            if ideal_tp > 0:
                
                usages.append( p( ideal_tp ) + ' full-size thumbnails' )
                
            
            if ideal_rp > 0:
                
                usages.append( p( ideal_rp ) + ' resized thumbnails' )
                
            
            if len( usages ) > 0:
                
                if ideal_fp == ideal_tp and ideal_tp == ideal_rp:
                    
                    usages = [ p( ideal_fp ) + ' everything' ]
                    
                
                pretty_ideal_usage = HydrusData.ConvertIntToBytes( ideal_bytes ) + ' - ' + ','.join( usages )
                
            else:
                
                pretty_ideal_usage = 'nothing'
                
            
            display_tuple = ( pretty_location, pretty_portable, pretty_free_space, pretty_ideal_weight, pretty_ideal_usage, pretty_current_usage )
            sort_tuple = ( location, portable, free_space, ideal_weight, ideal_usage, current_usage )
            
            tuples.append( ( location, display_tuple, sort_tuple ) )
            
        
        return tuples
        
    
    def _IncreaseWeight( self ):
        
        self._AdjustWeight( 1 )
        
    
    def _Rebalance( self ):
        
        job_key = ClientThreading.JobKey( cancellable = True )
        
        job_key.SetVariable( 'popup_title', 'rebalancing files' )
        
        self._controller.CallToThread( self._controller.client_files_manager.Rebalance, job_key )
        
        with ClientGUITopLevelWindows.DialogNullipotentVetoable( self, 'migrating files' ) as dlg:
            
            panel = ClientGUIPopupMessages.PopupMessageDialogPanel( dlg, job_key )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
        self._Update()
        
    
    def _RemovePaths( self ):
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._new_options.GetClientFilesLocationsToIdealWeights()
        
        removees = set()
        
        for ( location, portable, free_space, weight, gumpf, gumpf ) in self._current_media_locations_listctrl.GetSelectedClientData():
            
            if location in locations_to_ideal_weights:
                
                removees.add( location )
                
            
        
        # eventually have a check and veto if not enough size on the destination partition
        
        if len( removees ) == 0:
            
            wx.MessageBox( 'Please select some locations with weight.' )
            
        elif len( removees ) == len( locations_to_ideal_weights ):
            
            wx.MessageBox( 'You cannot empty every single location--please add a new place for the files to be moved to and then try again.' )
            
        else:
            
            with ClientGUIDialogs.DialogYesNo( self, 'Are you sure? This will schedule all the selected locations to have all their current files removed.' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    for location in removees:
                        
                        self._new_options.RemoveClientFilesLocation( location )
                        
                    
                    self._Update()
                    
                
            
        
    
    def _SetFullsizeThumbnailLocation( self ):
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._new_options.GetClientFilesLocationsToIdealWeights()
        
        with wx.DirDialog( self ) as dlg:
            
            if full_size_thumbnail_override is not None:
                
                dlg.SetPath( full_size_thumbnail_override )
                
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                if path in locations_to_ideal_weights:
                    
                    wx.MessageBox( 'That path already exists as a regular file location! Please choose another.' )
                    
                else:
                    
                    self._new_options.SetFullsizeThumbnailOverride( path )
                    
                    self._Update()
                    
                
            
        
    
    def _SetResizedThumbnailLocation( self ):
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._new_options.GetClientFilesLocationsToIdealWeights()
        
        with wx.DirDialog( self ) as dlg:
            
            if resized_thumbnail_override is not None:
                
                dlg.SetPath( resized_thumbnail_override )
                
            
            if dlg.ShowModal() == wx.ID_OK:
                
                path = dlg.GetPath()
                
                if path in locations_to_ideal_weights:
                    
                    wx.MessageBox( 'That path already exists as a regular file location! Please choose another.' )
                    
                else:
                    
                    self._new_options.SetResizedThumbnailOverride( path )
                    
                    self._Update()
                    
                
            
        
    
    def _Update( self ):
        
        approx_total_db_size = self._controller.db.GetApproxTotalFileSize()
        
        self._current_db_path_st.SetLabelText( 'database (totalling about ' + HydrusData.ConvertIntToBytes( approx_total_db_size ) + '): ' + self._controller.GetDBDir() )
        self._current_install_path_st.SetLabelText( 'install: ' + HC.BASE_DIR )
        
        service_info = HG.client_controller.Read( 'service_info', CC.COMBINED_LOCAL_FILE_SERVICE_KEY )
        
        all_local_files_total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
        
        approx_total_client_files = all_local_files_total_size * ( 1.0 + self.RESIZED_RATIO + self.FULLSIZE_RATIO )
        
        self._current_media_paths_st.SetLabelText( 'media (totalling about ' + HydrusData.ConvertIntToBytes( approx_total_client_files ) + '):' )
        
        selected_locations = { l[0] for l in self._current_media_locations_listctrl.GetSelectedClientData() }
        
        self._current_media_locations_listctrl.DeleteAllItems()
        
        for ( i, ( location, display_tuple, sort_tuple ) ) in enumerate( self._GenerateCurrentMediaTuples( all_local_files_total_size ) ):
            
            self._current_media_locations_listctrl.Append( display_tuple, sort_tuple )
            
            if location in selected_locations:
                
                self._current_media_locations_listctrl.Select( i )
                
            
        
        #
        
        ( locations_to_ideal_weights, resized_thumbnail_override, full_size_thumbnail_override ) = self._new_options.GetClientFilesLocationsToIdealWeights()
        
        if resized_thumbnail_override is None:
            
            self._resized_thumbs_location.SetValue( 'none set' )
            
            self._resized_thumbs_location_set.Enable()
            self._resized_thumbs_location_clear.Disable()
            
        else:
            
            self._resized_thumbs_location.SetValue( resized_thumbnail_override )
            
            self._resized_thumbs_location_set.Disable()
            self._resized_thumbs_location_clear.Enable()
            
        
        if full_size_thumbnail_override is None:
            
            self._fullsize_thumbs_location.SetValue( 'none set' )
            
            self._fullsize_thumbs_location_set.Enable()
            self._fullsize_thumbs_location_clear.Disable()
            
        else:
            
            self._fullsize_thumbs_location.SetValue( full_size_thumbnail_override )
            
            self._fullsize_thumbs_location_set.Disable()
            self._fullsize_thumbs_location_clear.Enable()
            
        
        #
        
        if self._controller.client_files_manager.RebalanceWorkToDo():
            
            self._rebalance_button.Enable()
            
            self._rebalance_status_st.SetForegroundColour( ( 128, 0, 0 ) )
            
            self._rebalance_status_st.SetLabelText( 'files need to be moved' )
            
        else:
            
            self._rebalance_button.Disable()
            
            self._rebalance_status_st.SetForegroundColour( ( 0, 128, 0 ) )
            
            self._rebalance_status_st.SetLabelText( 'all files are in their ideal locations' )
            
        
    
