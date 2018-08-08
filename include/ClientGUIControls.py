import ClientCaches
import ClientConstants as CC
import ClientData
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIListCtrl
import ClientGUIMenus
import ClientGUIScrolledPanels
import ClientGUIShortcuts
import ClientGUITime
import ClientGUITopLevelWindows
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusNetworking
import HydrusText
import os
import wx

class BandwidthRulesCtrl( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, bandwidth_rules ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'bandwidth rules' )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'max allowed', 14 ), ( 'every', 16 ) ]
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'bandwidth_rules', 8, 10, columns, self._ConvertRuleToListctrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'delete', self._Delete, enabled_only_on_selection = True )
        
        #
        
        self._listctrl.AddDatas( bandwidth_rules.GetRules() )
        
        self._listctrl.Sort( 0 )
        
        #
        
        self.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _Add( self ):
        
        rule = ( HC.BANDWIDTH_TYPE_DATA, None, 1024 * 1024 * 100 )
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit rule' ) as dlg:
            
            panel = self._EditPanel( dlg, rule )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                new_rule = panel.GetValue()
                
                self._listctrl.AddDatas( ( new_rule, ) )
                
                self._listctrl.Sort()
                
            
        
    
    def _ConvertRuleToListctrlTuples( self, rule ):
        
        ( bandwidth_type, time_delta, max_allowed ) = rule
        
        pretty_time_delta = HydrusData.TimeDeltaToPrettyTimeDelta( time_delta )
        
        if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
            
            pretty_max_allowed = HydrusData.ConvertIntToBytes( max_allowed )
            
        elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
            
            pretty_max_allowed = HydrusData.ToHumanInt( max_allowed ) + ' requests'
            
        
        sort_tuple = ( max_allowed, time_delta )
        display_tuple = ( pretty_max_allowed, pretty_time_delta )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._listctrl.DeleteSelected()
                
            
        
    
    def _Edit( self ):
        
        selected_rules = self._listctrl.GetData( only_selected = True )
        
        for rule in selected_rules:
            
            with ClientGUITopLevelWindows.DialogEdit( self, 'edit rule' ) as dlg:
                
                panel = self._EditPanel( dlg, rule )
                
                dlg.SetPanel( panel )
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    edited_rule = panel.GetValue()
                    
                    self._listctrl.DeleteDatas( ( rule, ) )
                    
                    self._listctrl.AddDatas( ( edited_rule, ) )
                    
                else:
                    
                    break
                    
                
            
        
        self._listctrl.Sort()
        
    
    def GetValue( self ):
        
        bandwidth_rules = HydrusNetworking.BandwidthRules()
        
        for rule in self._listctrl.GetData():
            
            ( bandwidth_type, time_delta, max_allowed ) = rule
            
            bandwidth_rules.AddRule( bandwidth_type, time_delta, max_allowed )
            
        
        return bandwidth_rules
        
    
    class _EditPanel( ClientGUIScrolledPanels.EditPanel ):
        
        def __init__( self, parent, rule ):
            
            ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
            
            self._bandwidth_type = ClientGUICommon.BetterChoice( self )
            
            self._bandwidth_type.Append( 'data', HC.BANDWIDTH_TYPE_DATA )
            self._bandwidth_type.Append( 'requests', HC.BANDWIDTH_TYPE_REQUESTS )
            
            self._bandwidth_type.Bind( wx.EVT_CHOICE, self.EventBandwidth )
            
            self._max_allowed_bytes = BytesControl( self )
            self._max_allowed_requests = wx.SpinCtrl( self, min = 1, max = 1048576 )
            
            self._time_delta = ClientGUITime.TimeDeltaButton( self, min = 1, days = True, hours = True, minutes = True, seconds = True, monthly_allowed = True )
            
            #
            
            ( bandwidth_type, time_delta, max_allowed ) = rule
            
            self._bandwidth_type.SelectClientData( bandwidth_type )
            
            self._time_delta.SetValue( time_delta )
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                self._max_allowed_bytes.SetValue( max_allowed )
                
            else:
                
                self._max_allowed_requests.SetValue( max_allowed )
                
            
            self._UpdateEnabled()
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._max_allowed_bytes, CC.FLAGS_VCENTER )
            hbox.Add( self._max_allowed_requests, CC.FLAGS_VCENTER )
            hbox.Add( self._bandwidth_type, CC.FLAGS_VCENTER )
            hbox.Add( ClientGUICommon.BetterStaticText( self, ' every ' ), CC.FLAGS_VCENTER )
            hbox.Add( self._time_delta, CC.FLAGS_VCENTER )
            
            self.SetSizer( hbox )
            
        
        def _UpdateEnabled( self ):
            
            bandwidth_type = self._bandwidth_type.GetChoice()
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                self._max_allowed_bytes.Show()
                self._max_allowed_requests.Hide()
                
            elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                
                self._max_allowed_bytes.Hide()
                self._max_allowed_requests.Show()
                
            
            self.Layout()
            
        
        def EventBandwidth( self, event ):
            
            self._UpdateEnabled()
            
        
        def GetValue( self ):
            
            bandwidth_type = self._bandwidth_type.GetChoice()
            
            time_delta = self._time_delta.GetValue()
            
            if bandwidth_type == HC.BANDWIDTH_TYPE_DATA:
                
                max_allowed = self._max_allowed_bytes.GetValue()
                
            elif bandwidth_type == HC.BANDWIDTH_TYPE_REQUESTS:
                
                max_allowed = self._max_allowed_requests.GetValue()
                
            
            return ( bandwidth_type, time_delta, max_allowed )
            
        
    
class BytesControl( wx.Panel ):
    
    def __init__( self, parent, initial_value = 65536 ):
        
        wx.Panel.__init__( self, parent )
        
        self._spin = wx.SpinCtrl( self, min = 0, max = 1048576 )
        
        width = ClientGUICommon.ConvertTextToPixelWidth( self._spin, 12 )
        
        self._spin.SetSize( ( width, -1 ) )
        
        self._unit = ClientGUICommon.BetterChoice( self )
        
        self._unit.Append( 'B', 1 )
        self._unit.Append( 'KB', 1024 )
        self._unit.Append( 'MB', 1024 * 1024 )
        self._unit.Append( 'GB', 1024 * 1024 * 1024 )
        
        #
        
        self.SetValue( initial_value )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._spin, CC.FLAGS_VCENTER )
        hbox.Add( self._unit, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def Bind( self, event_type, callback ):
        
        self._spin.Bind( wx.EVT_SPINCTRL, callback )
        
        self._unit.Bind( wx.EVT_CHOICE, callback )
        
    
    def Disable( self ):
        
        self._spin.Disable()
        self._unit.Disable()
        
    
    def Enable( self ):
        
        self._spin.Enable()
        self._unit.Enable()
        
    
    def GetSeparatedValue( self ):
        
        return ( self._spin.GetValue(), self._unit.GetChoice() )
        
    
    def GetValue( self ):
        
        return self._spin.GetValue() * self._unit.GetChoice()
        
    
    def SetSeparatedValue( self, value, unit ):
        
        return ( self._spin.SetValue( value ), self._unit.SelectClientData( unit ) )
        
    
    def SetValue( self, value ):
        
        max_unit = 1024 * 1024 * 1024
        
        unit = 1
        
        while value % 1024 == 0 and unit < max_unit:
            
            value /= 1024
            
            unit *= 1024
            
        
        self._spin.SetValue( value )
        self._unit.SelectClientData( unit )
        
    
class NoneableBytesControl( wx.Panel ):
    
    def __init__( self, parent, initial_value = 65536, none_label = 'no limit' ):
        
        wx.Panel.__init__( self, parent )
        
        self._bytes = BytesControl( self )
        
        self._none_checkbox = wx.CheckBox( self, label = none_label )
        
        #
        
        self.SetValue( initial_value )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._bytes, CC.FLAGS_SIZER_VCENTER )
        hbox.Add( self._none_checkbox, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
        #
        
        self._none_checkbox.Bind( wx.EVT_CHECKBOX, self.EventNoneChecked )
        
    
    def _UpdateEnabled( self ):
        
        if self._none_checkbox.GetValue():
            
            self._bytes.Disable()
            
        else:
            
            self._bytes.Enable()
            
        
    
    def EventNoneChecked( self, event ):
        
        self._UpdateEnabled()
        
    
    def Bind( self, event_type, callback ):
        
        self._bytes.Bind( wx.EVT_SPINCTRL, callback )
        
        self._none_checkbox.Bind( wx.EVT_CHECKBOX, callback )
        
    
    def GetValue( self ):
        
        if self._none_checkbox.GetValue():
            
            return None
            
        else:
            
            return self._bytes.GetValue()
            
        
    
    def SetToolTip( self, text ):
        
        wx.Panel.SetToolTip( self, text )
        
        for c in self.GetChildren():
            
            c.SetToolTip( text )
            
        
    
    def SetValue( self, value ):
        
        if value is None:
            
            self._none_checkbox.SetValue( True )
            
        else:
            
            self._none_checkbox.SetValue( False )
            
            self._bytes.SetValue( value )
            
        
        self._UpdateEnabled()
        
    
class EditStringToStringDictControl( wx.Panel ):
    
    def __init__( self, parent, initial_dict ):
        
        wx.Panel.__init__( self, parent )
        
        listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
        
        columns = [ ( 'key', 20 ), ( 'value', -1 ) ]
        
        self._listctrl = ClientGUIListCtrl.BetterListCtrl( listctrl_panel, 'key_to_value', 10, 36, columns, self._ConvertDataToListCtrlTuples, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        listctrl_panel.SetListCtrl( self._listctrl )
        
        listctrl_panel.AddButton( 'add', self._Add )
        listctrl_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
        listctrl_panel.AddButton( 'delete', self._Delete, enabled_only_on_selection = True )
        
        #
        
        self._listctrl.AddDatas( initial_dict.items() )
        
        self._listctrl.Sort()
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.Add( listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
    
    def _ConvertDataToListCtrlTuples( self, data ):
        
        ( key, value ) = data
        
        display_tuple = ( key, value )
        sort_tuple = ( key, value )
        
        return ( display_tuple, sort_tuple )
        
    
    def _Add( self ):
        
        with ClientGUIDialogs.DialogTextEntry( self, 'enter the key', allow_blank = False ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                key = dlg.GetValue()
                
                with ClientGUIDialogs.DialogTextEntry( self, 'enter the value', allow_blank = True ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        value = dlg.GetValue()
                        
                        data = ( key, value )
                        
                        self._listctrl.AddDatas( ( data, ) )
                        
                    
                
            
        
    
    def _Delete( self ):
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._listctrl.DeleteSelected()
                
            
        
    
    def _Edit( self ):
        
        for data in self._listctrl.GetData( only_selected = True ):
            
            ( key, value ) = data
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the key', default = key, allow_blank = False ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    key = dlg.GetValue()
                    
                else:
                    
                    break
                    
                
            
            with ClientGUIDialogs.DialogTextEntry( self, 'edit the value', default = value, allow_blank = True ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    value = dlg.GetValue()
                    
                else:
                    
                    break
                    
                
            
            self._listctrl.DeleteDatas( ( data, ) )
            
            new_data = ( key, value )
            
            self._listctrl.AddDatas( ( new_data, ) )
            
        
        self._listctrl.Sort()
        
    
    def GetValue( self ):
        
        value_dict = dict( self._listctrl.GetData() )
        
        return value_dict
        
    
class NetworkJobControl( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self._network_job = None
        self._download_started = False
        
        self._auto_override_bandwidth_rules = False
        
        self._left_text = ClientGUICommon.BetterStaticText( self, style = wx.ST_ELLIPSIZE_END )
        self._right_text = ClientGUICommon.BetterStaticText( self, style = wx.ALIGN_RIGHT )
        
        self._last_right_min_width = ( -1, -1 )
        
        self._gauge = ClientGUICommon.Gauge( self )
        
        menu_items = []
        
        invert_call = self.FlipOverrideBandwidthForCurrentJob
        value_call = self.CurrentJobOverridesBandwidth
        
        check_manager = ClientGUICommon.CheckboxManagerCalls( invert_call, value_call )
        
        menu_items.append( ( 'check', 'override bandwidth rules for this job', 'Tell the current job to ignore existing bandwidth rules and go ahead anyway.', check_manager ) )
        
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        invert_call = self.FlipAutoOverrideBandwidth
        value_call = self.AutoOverrideBandwidth
        
        check_manager = ClientGUICommon.CheckboxManagerCalls( invert_call, value_call )
        
        menu_items.append( ( 'check', 'auto-override bandwidth rules for all jobs here after five seconds', 'Ignore existing bandwidth rules for all jobs under this control, instead waiting a flat five seconds.', check_manager ) )
        
        self._cog_button = ClientGUICommon.MenuBitmapButton( self, CC.GlobalBMPs.cog, menu_items )
        self._cancel_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.stop, self.Cancel )
        
        #
        
        self._Update()
        
        #
        
        st_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        st_hbox.Add( self._left_text, CC.FLAGS_EXPAND_BOTH_WAYS )
        st_hbox.Add( self._right_text, CC.FLAGS_VCENTER )
        
        left_vbox = wx.BoxSizer( wx.VERTICAL )
        
        left_vbox.Add( st_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        left_vbox.Add( self._gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( left_vbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        hbox.Add( self._cog_button, CC.FLAGS_VCENTER )
        hbox.Add( self._cancel_button, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def _OverrideBandwidthIfAppropriate( self ):
        
        if self._network_job is None or self._network_job.NoEngineYet():
            
            return
            
        else:
            
            if self._auto_override_bandwidth_rules and HydrusData.TimeHasPassed( self._network_job.GetCreationTime() + 5 ):
                
                self._network_job.OverrideBandwidth()
                
            
        
    
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
                
            
            speed_text = ''
            
            if self._download_started and not self._network_job.HasError():
                
                if bytes_read is not None:
                    
                    if bytes_to_read is not None and bytes_read != bytes_to_read:
                        
                        speed_text += HydrusData.ConvertValueRangeToBytes( bytes_read, bytes_to_read )
                        
                    else:
                        
                        speed_text += HydrusData.ConvertIntToBytes( bytes_read )
                        
                    
                
                if current_speed != bytes_to_read: # if it is a real quick download, just say its size
                    
                    speed_text += ' ' + HydrusData.ConvertIntToBytes( current_speed ) + '/s'
                    
                
            
            self._right_text.SetLabelText( speed_text )
            
            right_width = ClientGUICommon.ConvertTextToPixelWidth( self._right_text, len( speed_text ) )
            
            right_min_size = ( right_width, -1 )
            
            if right_min_size != self._last_right_min_width:
                
                self._last_right_min_width = right_min_size
                
                self._right_text.SetMinSize( right_min_size )
                
                self.Layout()
                
            
            self._gauge.SetRange( bytes_to_read )
            self._gauge.SetValue( bytes_read )
            
        
        if can_cancel:
            
            if not self._cancel_button.IsEnabled():
                
                self._cancel_button.Enable()
                
            
        else:
            
            if self._cancel_button.IsEnabled():
                
                self._cancel_button.Disable()
                
            
        
    
    def AutoOverrideBandwidth( self ):
        
        return self._auto_override_bandwidth_rules
        
    
    def Cancel( self ):
        
        if self._network_job is not None:
            
            self._network_job.Cancel()
            
        
    
    def ClearNetworkJob( self ):
        
        self.SetNetworkJob( None )
        
    
    def CurrentJobOverridesBandwidth( self ):
        
        if self._network_job is None:
            
            return None
            
        else:
            
            return not self._network_job.ObeysBandwidth()
            
        
    
    def FlipAutoOverrideBandwidth( self ):
        
        self._auto_override_bandwidth_rules = not self._auto_override_bandwidth_rules
        
    
    def FlipOverrideBandwidthForCurrentJob( self ):
        
        if self._network_job is not None:
            
            self._network_job.OverrideBandwidth()
            
        
    
    def SetNetworkJob( self, network_job ):
        
        if network_job is None:
            
            if self._network_job is not None:
                
                self._network_job = None
                
                self._Update()
                
                HG.client_controller.gui.UnregisterUIUpdateWindow( self )
                
            
        else:
            
            if self._network_job != network_job:
                
                self._network_job = network_job
                self._download_started = False
                
                HG.client_controller.gui.RegisterUIUpdateWindow( self )
                
            
        
    
    def TIMERUIUpdate( self ):
        
        self._OverrideBandwidthIfAppropriate()
        
        if HG.client_controller.gui.IShouldRegularlyUpdate( self ):
            
            self._Update()
            
        
    
class StringToStringDictButton( ClientGUICommon.BetterButton ):
    
    def __init__( self, parent, label ):
        
        ClientGUICommon.BetterButton.__init__( self, parent, label, self._Edit )
        
        self._value = {}
        
    
    def _Edit( self ):
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'edit string dictionary' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            control = EditStringToStringDictControl( panel, self._value )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                self._value = control.GetValue()
                
            
        
    
    def GetValue( self ):
        
        return self._value
        
    
    def SetValue( self, value ):
        
        self._value = value
        
    
class TextAndPasteCtrl( wx.Panel ):
    
    def __init__( self, parent, add_callable, allow_empty_input = False ):
        
        self._add_callable = add_callable
        self._allow_empty_input = allow_empty_input
        
        wx.Panel.__init__( self, parent )
        
        self._text_input = wx.TextCtrl( self, style = wx.TE_PROCESS_ENTER )
        self._text_input.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        
        self._paste_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.paste, self._Paste )
        self._paste_button.SetToolTip( 'Paste multiple inputs from the clipboard. Assumes the texts are newline-separated.' )
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.Add( self._text_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        hbox.Add( self._paste_button, CC.FLAGS_VCENTER )
        
        self.SetSizer( hbox )
        
    
    def _Paste( self ):
        
        raw_text = HG.client_controller.GetClipboardText()
        
        try:
            
            texts = [ text for text in HydrusText.DeserialiseNewlinedTexts( raw_text ) ]
            
            if not self._allow_empty_input:
                
                texts = [ text for text in texts if text != '' ]
                
            
            if len( texts ) > 0:
                
                self._add_callable( texts )
                
            
        except:
            
            wx.MessageBox( 'I could not understand what was in the clipboard' )
            
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ( wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER ):
            
            text = self._text_input.GetValue()
            
            if not self._allow_empty_input and text == '':
                
                return
                
            
            self._add_callable( ( text, ) )
            
            self._text_input.SetValue( '' )
            
        else:
            
            event.Skip()
            
        
    
    def GetValue( self ):
        
        return self._text_input.GetValue()
        
    
    def SetValue( self, text ):
        
        self._text_input.SetValue( text )
        
    
