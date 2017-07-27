import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIMenus
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import os
import wx

class EditSeedCachePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, controller, seed_cache ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._controller = controller
        self._seed_cache = seed_cache
        
        self._text = ClientGUICommon.BetterStaticText( self, 'initialising' )
        
        # add index control row here, hide it if needed and hook into showing/hiding and postsizechangedevent on seed add/remove
        
        height = 300
        columns = [ ( 'source', -1 ), ( 'status', 90 ), ( 'added', 150 ), ( 'last modified', 150 ), ( 'note', 200 ) ]
        
        self._list_ctrl = ClientGUICommon.SaneListCtrlForSingleObject( self, height, columns )
        
        #
        
        self._AddSeeds( self._seed_cache.GetSeeds() )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._text, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._list_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._list_ctrl.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        self._controller.sub( self, 'NotifySeedsUpdated', 'seed_cache_seeds_updated' )
        
        wx.CallAfter( self._UpdateText )
        
    
    def _AddSeeds( self, seeds ):
        
        for seed in seeds:
            
            sort_tuple = self._seed_cache.GetSeedInfo( seed )
            
            ( display_tuple, sort_tuple ) = self._GetListCtrlTuples( seed )
            
            self._list_ctrl.Append( display_tuple, sort_tuple, seed )
            
        
    
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
        
        for seed in self._list_ctrl.GetObjects( only_selected = True ):
            
            ( seed, status, added_timestamp, last_modified_timestamp, note ) = self._seed_cache.GetSeedInfo( seed )
            
            if note != '':
                
                notes.append( note )
                
            
        
        if len( notes ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( notes )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopySelectedSeeds( self ):
        
        seeds = self._list_ctrl.GetObjects( only_selected = True )
        
        if len( seeds ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( seeds )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _DeleteSelected( self ):
        
        seeds_to_delete = self._list_ctrl.GetObjects( only_selected = True )
        
        if len( seeds_to_delete ) > 0:
            
            message = 'Are you sure you want to delete all the selected entries?'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._seed_cache.RemoveSeeds( seeds_to_delete )
                    
                
            
        
    
    def _SetSelected( self, status_to_set ):
        
        seeds_to_set = self._list_ctrl.GetObjects( only_selected = True )
        
        self._seed_cache.UpdateSeedsStatus( seeds_to_set, status_to_set )
        
    
    def _ShowMenuIfNeeded( self ):
        
        if self._list_ctrl.GetSelectedItemCount() > 0:
            
            menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'copy sources', 'Copy all the selected sources to clipboard.', self._CopySelectedSeeds )
            ClientGUIMenus.AppendMenuItem( self, menu, 'copy notes', 'Copy all the selected notes to clipboard.', self._CopySelectedNotes )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'try again', 'Reset the progress of all the selected imports.', HydrusData.Call( self._SetSelected, CC.STATUS_UNKNOWN ) )
            ClientGUIMenus.AppendMenuItem( self, menu, 'skip', 'Skip all the selected imports.', HydrusData.Call( self._SetSelected, CC.STATUS_SKIPPED ) )
            ClientGUIMenus.AppendMenuItem( self, menu, 'delete', 'Remove all the selected imports.', self._DeleteSelected )
            
            HG.client_controller.PopupMenu( self, menu )
            
        
    
    def _UpdateListCtrl( self, seeds ):
        
        seeds_to_add = []
        seeds_to_update = []
        seeds_to_delete = []
        
        for seed in seeds:
            
            if self._seed_cache.HasSeed( seed ):
                
                if self._list_ctrl.HasObject( seed ):
                    
                    seeds_to_update.append( seed )
                    
                else:
                    
                    seeds_to_add.append( seed )
                    
                
            else:
                
                if self._list_ctrl.HasObject( seed ):
                    
                    seeds_to_delete.append( seed )
                    
                
            
        
        for seed in seeds_to_delete:
            
            index = self._list_ctrl.GetIndexFromObject( seed )
            
            self._list_ctrl.DeleteItem( index )
            
        
        for seed in seeds_to_update:
            
            index = self._list_ctrl.GetIndexFromObject( seed )
            
            ( display_tuple, sort_tuple ) = self._GetListCtrlTuples( seed )
            
            self._list_ctrl.UpdateRow( index, display_tuple, sort_tuple, seed )
            
        
        self._AddSeeds( seeds_to_add )
        
    
    def _UpdateText( self ):
        
        ( status, ( total_processed, total ) ) = self._seed_cache.GetStatus()
        
        self._text.SetLabelText( status )
        
        self.Layout()
        
    
    def EventShowMenu( self, event ):
        
        wx.CallAfter( self._ShowMenuIfNeeded )
        
        event.Skip() # let the right click event go through before doing menu, in case selection should happen
        
    
    def GetValue( self ):
        
        return self._seed_cache
        
    
    def NotifySeedsUpdated( self, seed_cache_key, seeds ):
        
        if seed_cache_key == self._seed_cache.GetSeedCacheKey():
            
            self._UpdateText()
            self._UpdateListCtrl( seeds )
            
        
    
class SeedCacheStatusControl( wx.Panel ):
    
    def __init__( self, parent, controller ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self._controller = controller
        
        self._seed_cache = None
        
        self._import_summary_st = ClientGUICommon.BetterStaticText( self )
        self._progress_st = ClientGUICommon.BetterStaticText( self )
        
        self._seed_cache_button = ClientGUICommon.BetterBitmapButton( self, CC.GlobalBMPs.seed_cache, self._ShowSeedCacheFrame )
        self._seed_cache_button.SetToolTipString( 'open detailed file import status' )
        
        self._progress_gauge = ClientGUICommon.Gauge( self )
        
        #
        
        self._Update()
        
        #
        
        hbox = wx.BoxSizer( wx.HORIZONTAL )
        
        hbox.AddF( self._progress_st, CC.FLAGS_VCENTER_EXPAND_DEPTH_ONLY )
        hbox.AddF( self._seed_cache_button, CC.FLAGS_VCENTER )
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._import_summary_st, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        vbox.AddF( self._progress_gauge, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.SetSizer( vbox )
        
        #
        
        self.Bind( wx.EVT_TIMER, self.TIMEREventUpdate )
        
        self._update_timer = wx.Timer( self )
        
    
    def _ShowSeedCacheFrame( self ):
        
        title = 'file import status'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = EditSeedCachePanel( frame, self._controller, self._seed_cache )
        
        frame.SetPanel( panel )
        
    
    def _Update( self ):
        
        if self._seed_cache is None:
            
            self._import_summary_st.SetLabelText( '' )
            self._progress_st.SetLabelText( '' )
            self._progress_gauge.SetRange( 1 )
            self._progress_gauge.SetValue( 0 )
            
            if self._seed_cache_button.IsEnabled():
                
                self._seed_cache_button.Disable()
                
            
        else:
            
            ( import_summary, ( num_done, num_to_do ) ) = self._seed_cache.GetStatus()
            
            self._import_summary_st.SetLabelText( import_summary )
            
            if num_to_do == 0:
                
                self._progress_st.SetLabelText( '' )
                
            else:
                
                self._progress_st.SetLabelText( HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ) )
                
            
            self._progress_gauge.SetRange( num_to_do )
            self._progress_gauge.SetValue( num_done )
            
            if not self._seed_cache_button.IsEnabled():
                
                self._seed_cache_button.Enable()
                
            
        
    
    def ClearSeedCache( self ):
        
        if self:
            
            self._Update()
            
            self._seed_cache = None
            
            self._update_timer.Stop()
            
        
    
    def SetSeedCache( self, seed_cache ):
        
        if self:
            
            self._seed_cache = seed_cache
            
            self._update_timer.Start( 250, wx.TIMER_CONTINUOUS )
            
        
    
    def TIMEREventUpdate( self, event ):
        
        if self._controller.gui.IAmInCurrentPage( self ):
            
            self._Update()
            
        
    
