import ClientConstants as CC
import ClientGUICommon
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import HydrusConstants as HC
import HydrusData
import HydrusNetworking
import wx

class BandwidthRulesCtrl( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent, bandwidth_rules ):
        
        ClientGUICommon.StaticBox.__init__( self, parent, 'bandwidth rules' )
        
        columns = [ ( 'type', -1 ), ( 'time delta', 120 ), ( 'max allowed', 80 ) ]
        
        self._listctrl = ClientGUICommon.SaneListCtrl( self, 100, columns, delete_key_callback = self._Delete, activation_callback = self._Edit )
        
        self._add_button = ClientGUICommon.BetterButton( self, 'add', self._Add )
        self._edit_button = ClientGUICommon.BetterButton( self, 'edit', self._Edit )
        self._delete_button = ClientGUICommon.BetterButton( self, 'delete', self._Delete )
        
        #
        
        for rule in bandwidth_rules.GetRules():
            
            sort_tuple = rule
            
            display_tuple = self._GetDisplayTuple( sort_tuple )
            
            self._listctrl.Append( display_tuple, sort_tuple )
            
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._add_button, CC.FLAGS_LONE_BUTTON )
        hbox.AddF( self._edit_button, CC.FLAGS_LONE_BUTTON )
        hbox.AddF( self._delete_button, CC.FLAGS_LONE_BUTTON )
        
        self.AddF( self._listctrl, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.AddF( hbox, CC.FLAGS_BUTTON_SIZER )
        
    
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
            
            self._time_delta = ClientGUICommon.TimeDeltaButton( self, min = 3600, days = True, hours = True, monthly_allowed = True )
            
            self._max_allowed = wx.SpinCtrl( self, min = 1, max = 1024 * 1024 * 1024 )
            
            self._max_allowed_st = wx.StaticText( self )
            
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
            
        
