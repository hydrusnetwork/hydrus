import ClientCaches
import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMenus
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import HydrusNetworking
import os
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
            
        
    
class EditStringToStringDictControl( wx.Panel ):
    
    def __init__( self, parent, initial_dict ):
        
        wx.Panel.__init__( self, parent )
        
        self._listctrl = ClientGUICommon.SaneListCtrl( self, 120, [ ( 'key', 200 ), ( 'value', -1 ) ], delete_key_callback = self.Delete, activation_callback = self.Edit )
        
        self._add = ClientGUICommon.BetterButton( self, 'add', self.Add )
        self._edit = ClientGUICommon.BetterButton( self, 'edit', self.Edit )
        self._delete = ClientGUICommon.BetterButton( self, 'delete', self.Delete )
        
        #
        
        for display_tuple in initial_dict.items():
            
            self._listctrl.Append( display_tuple, display_tuple )
            
        
        #
        
        button_hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        button_hbox.AddF( self._add, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._edit, CC.FLAGS_VCENTER )
        button_hbox.AddF( self._delete, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._listctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        vbox.AddF( button_hbox, CC.FLAGS_BUTTON_SIZER )
        
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
        
    
class SeedCacheControl( ClientGUICommon.SaneListCtrlForSingleObject ):
    
    def __init__( self, parent, seed_cache ):
        
        height = 300
        columns = [ ( 'source', -1 ), ( 'status', 90 ), ( 'added', 150 ), ( 'last modified', 150 ), ( 'note', 200 ) ]
        
        ClientGUICommon.SaneListCtrlForSingleObject.__init__( self, parent, height, columns )
        
        self._seed_cache = seed_cache
        
        for seed in self._seed_cache.GetSeeds():
            
            self._AddSeed( seed )
            
        
        self.Bind( wx.EVT_MENU, self.EventMenu )
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        HydrusGlobals.client_controller.sub( self, 'NotifySeedUpdated', 'seed_cache_seed_updated' )
        
    
    def _AddSeed( self, seed ):
        
        sort_tuple = self._seed_cache.GetSeedInfo( seed )
        
        ( display_tuple, sort_tuple ) = self._GetListCtrlTuples( seed )
        
        self.Append( display_tuple, sort_tuple, seed )
        
    
    def _GetListCtrlTuples( self, seed ):
        
        sort_tuple = self._seed_cache.GetSeedInfo( seed )
        
        ( seed, status, added_timestamp, last_modified_timestamp, note ) = sort_tuple
        
        pretty_seed = HydrusData.ToUnicode( seed )
        pretty_status = CC.status_string_lookup[ status ]
        pretty_added = HydrusData.ConvertTimestampToPrettyAgo( added_timestamp )
        pretty_modified = HydrusData.ConvertTimestampToPrettyAgo( last_modified_timestamp )
        pretty_note = note.split( os.linesep )[0]
        
        display_tuple = ( pretty_seed, pretty_status, pretty_added, pretty_modified, pretty_note )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedNotes( self ):
        
        notes = []
        
        for seed in self.GetObjects( only_selected = True ):
            
            ( seed, status, added_timestamp, last_modified_timestamp, note ) = self._seed_cache.GetSeedInfo( seed )
            
            if note != '':
                
                notes.append( note )
                
            
        
        if len( notes ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( notes )
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopySelectedSeeds( self ):
        
        seeds = self.GetObjects( only_selected = True )
        
        if len( seeds ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( seeds )
            
            HydrusGlobals.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _DeleteSelected( self ):
        
        seeds_to_delete = self.GetObjects( only_selected = True )
        
        for seed in seeds_to_delete:
            
            self._seed_cache.RemoveSeed( seed )
            
        
    
    def _SetSelected( self, status_to_set ):
        
        seeds_to_reset = self.GetObjects( only_selected = True )
        
        for seed in seeds_to_reset:
            
            self._seed_cache.UpdateSeedStatus( seed, status_to_set )
            
        
    
    def EventMenu( self, event ):
        
        action = ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetAction( event.GetId() )
        
        if action is not None:
            
            ( command, data ) = action
            
            if command == 'copy_seed_notes': self._CopySelectedNotes()
            elif command == 'copy_seeds': self._CopySelectedSeeds()
            elif command == 'delete_seeds':
                
                message = 'Are you sure you want to delete all the selected entries?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_YES:
                        
                        self._DeleteSelected()
                        
                    
                
            elif command == 'set_seed_unknown': self._SetSelected( CC.STATUS_UNKNOWN )
            elif command == 'set_seed_skipped': self._SetSelected( CC.STATUS_SKIPPED )
            else: event.Skip()
            
        
    
    def _ShowMenuIfNeeded( self ):
        
        if self.GetSelectedItemCount() > 0:
            
            menu = wx.Menu()
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_seeds' ), 'copy sources' )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'copy_seed_notes' ), 'copy notes' )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'set_seed_unknown' ), 'try again' )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'set_seed_skipped' ), 'skip' )
            menu.Append( ClientCaches.MENU_EVENT_ID_TO_ACTION_CACHE.GetTemporaryId( 'delete_seeds' ), 'delete' )
            
            HydrusGlobals.client_controller.PopupMenu( self, menu )
            
        
    
    def EventShowMenu( self, event ):
        
        wx.CallAfter( self._ShowMenuIfNeeded )
        
        event.Skip() # let the right click event go through before doing menu, in case selection should happen
        
    
    def NotifySeedUpdated( self, seed ):
        
        if self._seed_cache.HasSeed( seed ):
            
            if self.HasObject( seed ):
                
                index = self.GetIndexFromObject( seed )
                
                ( display_tuple, sort_tuple ) = self._GetListCtrlTuples( seed )
                
                self.UpdateRow( index, display_tuple, sort_tuple, seed )
                
            else:
                
                self._AddSeed( seed )
                
            
        else:
            
            if self.HasObject( seed ):
                
                index = self.GetIndexFromObject( seed )
                
                self.DeleteItem( index )
                
            
        
    
