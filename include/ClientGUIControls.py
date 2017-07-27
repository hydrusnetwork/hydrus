import ClientCaches
import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMenus
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusNetworking
import os
import wx

class BandwidthRulesCtrl( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, bandwidth_rules ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'bandwidth rules' )
        
        columns = [ ( 'type', -1 ), ( 'time delta', 120 ), ( 'max allowed', 80 ) ]
        
        listctrl_panel = ClientGUICommon.SaneListCtrlPanel( self )
        
        self._listctrl = ClientGUICommon.SaneListCtrl( listctrl_panel, 100, columns, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'delete', self._Delete, enabled_only_on_selection = True )
        
        #
        
        for rule in bandwidth_rules.GetRules():
            
            sort_tuple = rule
            
            display_tuple = self._GetDisplayTuple( sort_tuple )
            
            self._listctrl.Append( display_tuple, sort_tuple )
            
        
        #
        
        self.AddF( listctrl_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def _Add( self ):
        
        rule = ( HC.BANDWIDTH_TYPE_DATA, None, 1024 * 1024 * 100 )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit rule' ) as dlg:
            
            panel = self._EditPanel( dlg, rule )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_rule = panel.GetValue()
                
                sort_tuple = new_rule
                
                display_tuple = self._GetDisplayTuple( sort_tuple )
                
                self._listctrl.Append( display_tuple, sort_tuple )
                
            
        
    
    def _GetDisplayTuple( self, rule ):
        
        ( bandwidth_type, time_delta, max_allowed ) = rule
        
        pretty_bandwidth_type = HC.bandwidth_type_string_lookup[ bandwidth_type ]
        
        pretty_time_delta = HydrusData.ConvertTimeDeltaToPrettyString( time_delta )
        
        if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
            
            pretty_max_allowed = HydrusData.ConvertIntToBytes( max_allowed )
            
        elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
            
            pretty_max_allowed = HydrusData.ConvertIntToPrettyString( max_allowed )
            
        
        return ( pretty_bandwidth_type, pretty_time_delta, pretty_max_allowed )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._listctrl.RemoveAllSelected()
                
            
        
    
    def _Edit( self ):
        
        all_selected = self._listctrl.GetAllSelected()
        
        for index in all_selected:
            
            rule = self._listctrl.GetClientData( index )
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit rule' ) as dlg:
                
                panel = self._EditPanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_rule = panel.GetValue()
                    
                    sort_tuple = edited_rule
                    
                    display_tuple = self._GetDisplayTuple( sort_tuple )
                    
                    self._listctrl.UpdateRow( index, display_tuple, sort_tuple )
                    
                else:
                    
                    break
                    
                
            
        
    
    def GetValue( self ):
        
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        
        for ( bandwidth_type, time_delta, max_allowed ) in self._listctrl.GetClientData():
            
            bandwidth_rules.AddRule( bandwidth_type, time_delta, max_allowed )
            
        
        return bandwidth_rules
        
    
    class _EditPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, rule ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            self._bandwidth_type = ClientGUICommon.BetterChoice( self )
            
            self._bandwidth_type.Append( 'data', HC.BANDWIDTH_TYPE_DATA )
            self._bandwidth_type.Append( 'requests', HC.BANDWIDTH_TYPE_REQUESTS )
            
            self._bandwidth_type.Bind( wx.EVT_CHOICE, self.EventBandwidth )
            
            self._time_delta = ClientGUICommon.TimeDeltaButton( self, min = 1, days = True, hours = True, minutes = True, seconds = True, monthly_allowed = True )
            
            self._max_allowed = wx.SpinCtrl( self, min = 1, max = 1024 * 1024 * 1024 )
            
            self._max_allowed_st = ClientGUICommon.BetterStaticText( self )
            
            #
            
            ( bandwidth_type, time_delta, max_allowed ) = rule
            
            self._bandwidth_type.SelectClientData( bandwidth_type )
            
            self._time_delta.SetValue( time_delta )
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                max_allowed /= 1048576
                
            
            self._max_allowed.SetValue( max_allowed )
            
            self._UpdateMaxAllowedSt()
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.AddF( self._bandwidth_type, CC.FLAGS_VCENTER )
            hbox.AddF( self._time_delta, CC.FLAGS_VCENTER )
            hbox.AddF( self._max_allowed, CC.FLAGS_VCENTER )
            hbox.AddF( self._max_allowed_st, CC.FLAGS_VCENTER )
            
            self.SetSizer( hbox )
            
        
        def _UpdateMaxAllowedSt( self ):
            
            bandwidth_type = self._bandwidth_type.GetChoice()
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                self._max_allowed_st.SetLabelText( 'MB' )
                
            elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                
                self._max_allowed_st.SetLabelText( 'requests' )
                
            
        
        def EventBandwidth( self, event ):
            
            self._UpdateMaxAllowedSt()
            
        
        def GetValue( self ):
            
            bandwidth_type = self._bandwidth_type.GetChoice()
            
            time_delta = self._time_delta.GetValue()
            
            max_allowed = self._max_allowed.GetValue()
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                max_allowed *= 1048576
                
            
            return ( bandwidth_type, time_delta, max_allowed )
            
        
    
class EditStringToStringDictControl( wx.Panel ):
    
    def __init__( self, parent, initial_dict ):
        
        wx.Panel.__init__( self, parent )
        
        listctrl_panel = ClientGUICommon.SaneListCtrlPanel( self )
        
        self._listctrl = ClientGUICommon.SaneListCtrl( listctrl_panel, 120, [ ( 'key', 200 ), ( 'value', -1 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self.Add )
        listctrl_panel.AddButton( 'edit', self.Edit, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'delete', self.Delete, enabled_only_on_selection = True )
        
        #
        
        for display_tuple in initial_dict.items():
            
            self._listctrl.Append( display_tuple, display_tuple )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def Add( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the key', allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                key = dlg.GetValue()
                
                with ClientGUIDialogs.DialogTextEntry( self, 'enter the value', allow_blank = True ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        value = dlg.GetValue()
                        
                        display_tuple = ( key, value )
                        
                        self._listctrl.Append( display_tuple, display_tuple )
                        
                    
                
            
        
    
    def Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._listctrl.RemoveAllSelected()
                
            
        
    
    def Edit( self ):
        
        for i in self._listctrl.GetAllSelected():
            
            ( key, value ) = self._listctrl.GetClientData( i )
            
            import ClientGUIDialogs
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the key', default = key, allow_blank = False ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    key = dlg.GetValue()
                    
                else:
                    
                    return
                    
                
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the value', default = value, allow_blank = True ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    value = dlg.GetValue()
                    
                else:
                    
                    return
                    
                
            
            display_tuple = ( key, value )
            
            self._listctrl.UpdateRow( i, display_tuple, display_tuple )
            
        
    
    def GetValue( self ):
        
        value_dict = { key : value for ( key, value ) in self._listctrl.GetClientData() }
        
        return value_dict
        
    
class NetworkJobControl( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self._network_job = None
        self._download_started = False
        
        self._left_text = ClientGUICommon.BetterStaticText( self )
        self._right_text = ClientGUICommon.BetterStaticText( self, style = wx.ALIGN_RIGHT )
        
        # 512/768KB - 200KB/s
        right_width = ClientData.ConvertTextToPixelWidth( self._right_text, 20 )
        
        self._right_text.SetMinSize( ( right_width, -1 ) )
        
        self._gauge = ClientGUICommon.Gauge( self )
        
        self._cancel_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.stop, self.Cancel )
        
        #
        
        self._Update()
        
        #
        
        st_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        st_hbox.AddF( self._left_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        st_hbox.AddF( self._right_text, CC.FLAGS_VCENTER )
        
        left_vbox = wx.BoxSizer( wx.VERTICAL )
        
        left_vbox.AddF( st_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        left_vbox.AddF( self._gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( left_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        hbox.AddF( self._cancel_button, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        #
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventUpdate )
        
        self._update_timer = wx.Timer( self )
        
    
    def _Update( self ):
        
        if self._network_job is None or self._network_job.NoEngineYet():
            
            self._left_text.SetLabelText( '' )
            self._right_text.SetLabelText( '' )
            self._gauge.SetRange( 1 )
            self._gauge.SetValue( 0 )
            
            can_cancel = False
            
        else:
            
            if self._network_job.IsDone():
                
                can_cancel = False
                
            else:
                
                can_cancel = True
                
            
            ( status_text, current_speed, bytes_read, bytes_to_read ) = self._network_job.GetStatus()
            
            self._left_text.SetLabelText( status_text )
            
            if not self._download_started and current_speed > 0:
                
                self._download_started = True
                
            
            if self._download_started and not self._network_job.HasError():
                
                speed_text = ''
                
                if bytes_read is not None:
                    
                    if bytes_to_read is not None and bytes_read != bytes_to_read:
                        
                        speed_text += HydrusData.ConvertValueRangeToBytes( bytes_read, bytes_to_read )
                        
                    else:
                        
                        speed_text += HydrusData.ConvertIntToBytes( bytes_read )
                        
                    
                
                if current_speed != bytes_to_read: # if it is a real quick download, just say its size
                    
                    speed_text += ' ' + HydrusData.ConvertIntToBytes( current_speed ) + '/s'
                    
                
                self._right_text.SetLabelText( speed_text )
                
            else:
                
                self._right_text.SetLabelText( '' )
                
            
            self._gauge.SetRange( bytes_to_read )
            self._gauge.SetValue( bytes_read )
            
        
        if can_cancel:
            
            if not self._cancel_button.IsEnabled():
                
                self._cancel_button.Enable()
                
            
        else:
            
            if self._cancel_button.IsEnabled():
                
                self._cancel_button.Disable()
                
            
        
    
    def Cancel( self ):
        
        if self._network_job is not None:
            
            self._network_job.Cancel()
            
        
    
    def ClearNetworkJob( self ):
        
        if self:
            
            self._network_job = None
            
            self._Update()
            
            self._update_timer.Stop()
            
        
    
    def SetNetworkJob( self, network_job ):
        
        if self:
            
            self._network_job = network_job
            self._download_started = False
            
            self._update_timer.Start( 250, wx.TIMER_CONTINUOUS )
            
        
    
    def TIMEREventUpdate( self, event ):
        
        if HG.client_controller.gui.IAmInCurrentPage( self ):
            
            self._Update()
            
        
