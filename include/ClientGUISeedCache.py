import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIListCtrl
import ClientGUIMenus
import ClientGUIScrolledPanels
import ClientGUITopLevelWindows
import HydrusConstants as HC
import HydrusData
import HydrusGlobals as HG
import HydrusPaths
import os
import webbrowser
import wx

class EditSeedCachePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, controller, seed_cache ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        self._controller = controller
        self._seed_cache = seed_cache
        
        self._text = ClientGUICommon.BetterStaticText( self, 'initialising' )
        
        # add index control row here, hide it if needed and hook into showing/hiding and postsizechangedevent on seed add/remove
        
        columns = [ ( '#', 3 ), ( 'source', -1 ), ( 'status', 12 ), ( 'added', 23 ), ( 'last modified', 23 ), ( 'source time', 23 ), ( 'note', 20 ) ]
        
        self._list_ctrl = ClientGUIListCtrl.BetterListCtrl( self, 'seed_cache', 30, 30, columns, self._ConvertSeedToListCtrlTuples )
        
        #
        
        self._AddSeeds( self._seed_cache.GetSeeds() )
        
        self._list_ctrl.Sort( 0 )
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        vbox.AddF( self._text, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.AddF( self._list_ctrl, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.SetSizer( vbox )
        
        self._list_ctrl.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
        self._controller.sub( self, 'NotifySeedsUpdated', 'seed_cache_seeds_updated' )
        
        wx.CallAfter( self._UpdateText )
        
    
    def _AddSeeds( self, seeds ):
        
        self._list_ctrl.AddDatas( seeds )
        
    
    def _ConvertSeedToListCtrlTuples( self, seed ):
        
        seed_index = self._seed_cache.GetSeedIndex( seed )
        
        seed_data = seed.seed_data
        status = seed.status
        added = seed.created
        modified = seed.modified
        source_time = seed.source_time
        note = seed.note
        
        pretty_seed_index = HydrusData.ConvertIntToPrettyString( seed_index )
        pretty_seed_data = HydrusData.ToUnicode( seed_data )
        pretty_status = CC.status_string_lookup[ status ]
        pretty_added = HydrusData.ConvertTimestampToPrettyAgo( added ) + ' ago'
        pretty_modified = HydrusData.ConvertTimestampToPrettyAgo( modified ) + ' ago'
        
        if source_time is None:
            
            pretty_source_time = 'unknown'
            
        else:
            
            pretty_source_time = HydrusData.ConvertTimestampToHumanPrettyTime( source_time )
            
        
        pretty_note = note.split( os.linesep )[0]
        
        display_tuple = ( pretty_seed_index, pretty_seed_data, pretty_status, pretty_added, pretty_modified, pretty_source_time, pretty_note )
        sort_tuple = ( seed_index, seed_data, status, added, modified, source_time, note )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedNotes( self ):
        
        notes = []
        
        for seed in self._list_ctrl.GetData( only_selected = True ):
            
            note = seed.note
            
            if note != '':
                
                notes.append( note )
                
            
        
        if len( notes ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( notes )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopySelectedSeedData( self ):
        
        seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( seeds ) > 0:
            
            separator = os.linesep * 2
            
            text = separator.join( ( seed.seed_data for seed in seeds ) )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _DeleteSelected( self ):
        
        seeds_to_delete = self._list_ctrl.GetData( only_selected = True )
        
        if len( seeds_to_delete ) > 0:
            
            message = 'Are you sure you want to delete all the selected entries?'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    self._seed_cache.RemoveSeeds( seeds_to_delete )
                    
                
            
        
    
    def _OpenSelectedSeedData( self ):
        
        seeds = self._list_ctrl.GetData( only_selected = True )
        
        if len( seeds ) > 0:
            
            if len( seeds ) > 10:
                
                message = 'You have many objects selected--are you sure you want to open them all?'
                
                with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                    
                    if dlg.ShowModal() != wx.ID_YES:
                        
                        return
                        
                    
                
            
            if seeds[0].seed_data.startswith( 'http' ):
                
                for seed in seeds:
                    
                    webbrowser.open( seed.seed_data )
                    
                
            else:
                
                try:
                    
                    for seed in seeds:
                        
                        HydrusPaths.OpenFileLocation( seed.seed_data )
                        
                    
                except Exception as e:
                    
                    wx.MessageBox( unicode( e ) )
                    
                
            
        
    
    def _SetSelected( self, status_to_set ):
        
        seeds = self._list_ctrl.GetData( only_selected = True )
        
        for seed in seeds:
            
            seed.SetStatus( status_to_set )
            
        
        self._seed_cache.NotifySeedsUpdated( seeds )
        
    
    def _ShowMenuIfNeeded( self ):
        
        if self._list_ctrl.HasSelected() > 0:
            
            menu = wx.Menu()
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'copy sources', 'Copy all the selected sources to clipboard.', self._CopySelectedSeedData )
            ClientGUIMenus.AppendMenuItem( self, menu, 'copy notes', 'Copy all the selected notes to clipboard.', self._CopySelectedNotes )
            
            ClientGUIMenus.AppendSeparator( menu )
            
            ClientGUIMenus.AppendMenuItem( self, menu, 'open sources', 'Open all the selected sources in your file explorer or web browser.', self._OpenSelectedSeedData )
            
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
                
                if self._list_ctrl.HasData( seed ):
                    
                    seeds_to_update.append( seed )
                    
                else:
                    
                    seeds_to_add.append( seed )
                    
                
            else:
                
                if self._list_ctrl.HasData( seed ):
                    
                    seeds_to_delete.append( seed )
                    
                
            
        
        self._list_ctrl.DeleteDatas( seeds_to_delete )
        
        self._list_ctrl.UpdateDatas( seeds_to_update )
        
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
            
        
    
class SeedCacheButton( ClientGUICommon.BetterBitmapButton ):
    
    def __init__( self, parent, controller, seed_cache_get_callable, seed_cache_set_callable = None ):
        
        ClientGUICommon.BetterBitmapButton.__init__( self, parent, CC.GlobalBMPs.seed_cache, self._ShowSeedCacheFrame )
        
        self._controller = controller
        self._seed_cache_get_callable = seed_cache_get_callable
        self._seed_cache_set_callable = seed_cache_set_callable
        
        self.SetToolTipString( 'open detailed file import status--right-click for quick actions, if applicable' )
        
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
    
    def _ClearProcessed( self ):
        
        message = 'Are you sure you want to delete all the processed (i.e. anything with a non-blank status in the larger window) files? This is useful for cleaning up and de-laggifying a very large list, but not much else.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                seed_cache = self._seed_cache_get_callable()
                
                seed_cache.RemoveProcessedSeeds()
                
            
        
    
    def _RetryFailures( self ):
        
        message = 'Are you sure you want to retry all the failed files?'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                seed_cache = self._seed_cache_get_callable()
                
                seed_cache.RetryFailures()
                
            
        
    
    def _ShowSeedCacheFrame( self ):
        
        seed_cache = self._seed_cache_get_callable()
        
        tlp = ClientGUICommon.GetTLP( self )
        
        if isinstance( tlp, wx.Dialog ):
            
            if self._seed_cache_set_callable is None: # throw up a dialog that edits the seed cache in place
                
                with ClientGUITopLevelWindows.DialogNullipotent( self, 'file import status' ) as dlg:
                    
                    panel = EditSeedCachePanel( dlg, self._controller, seed_cache )
                    
                    dlg.SetPanel( panel )
                    
                    dlg.ShowModal()
                    
                
            else: # throw up a dialog that edits the seed cache but can be cancelled
                
                dupe_seed_cache = seed_cache.Duplicate()
                
                with ClientGUITopLevelWindows.DialogEdit( self, 'file import status' ) as dlg:
                    
                    panel = EditSeedCachePanel( dlg, self._controller, dupe_seed_cache )
                    
                    dlg.SetPanel( panel )
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        self._seed_cache_set_callable( dupe_seed_cache )
                        
                    
                
            
        else: # throw up a frame that edits the seed cache in place
            
            title = 'file import status'
            frame_key = 'file_import_status'
            
            frame = ClientGUITopLevelWindows.FrameThatTakesScrollablePanel( self, title, frame_key )
            
            panel = EditSeedCachePanel( frame, self._controller, seed_cache )
            
            frame.SetPanel( panel )
            
        
    
    def EventShowMenu( self, event ):
        
        seed_cache = self._seed_cache_get_callable()
        
        menu_items = []
        
        num_failures = seed_cache.GetSeedCount( CC.STATUS_FAILED )
        
        if num_failures > 0:
            
            menu_items.append( ( 'normal', 'retry ' + HydrusData.ConvertIntToPrettyString( num_failures ) + ' failures', 'Tell this cache to reattempt all its failures.', self._RetryFailures ) )
            
        
        num_unknown = seed_cache.GetSeedCount( CC.STATUS_UNKNOWN )
        
        num_processed = len( seed_cache ) - num_unknown
        
        if num_processed > 0:
            
            menu_items.append( ( 'normal', 'delete ' + HydrusData.ConvertIntToPrettyString( num_processed ) + ' \'processed\' files from the queue', 'Tell this cache to clear out processed files, reducing the size of the queue.', self._ClearProcessed ) )
            
        
        if len( menu_items ) > 0:
            
            menu = wx.Menu()
            
            for ( item_type, title, description, data ) in menu_items:
                
                if item_type == 'normal':
                    
                    func = data
                    
                    ClientGUIMenus.AppendMenuItem( self, menu, title, description, func )
                    
                elif item_type == 'check':
                    
                    check_manager = data
                    
                    current_value = check_manager.GetCurrentValue()
                    func = check_manager.Invert
                    
                    if current_value is not None:
                        
                        ClientGUIMenus.AppendMenuCheckItem( self, menu, title, description, current_value, func )
                        
                    
                elif item_type == 'separator':
                    
                    ClientGUIMenus.AppendSeparator( menu )
                    
                
            
            HG.client_controller.PopupMenu( self, menu )
            
        else:
            
            event.Skip()
            
        
    
class SeedCacheStatusControl( wx.Panel ):
    
    def __init__( self, parent, controller ):
        
        wx.Panel.__init__( self, parent, style = wx.BORDER_DOUBLE )
        
        self._controller = controller
        
        self._seed_cache = None
        
        self._import_summary_st = ClientGUICommon.BetterStaticText( self )
        self._progress_st = ClientGUICommon.BetterStaticText( self )
        
        self._seed_cache_button = SeedCacheButton( self, self._controller, self._GetSeedCache )
        
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
        
    
    def _GetSeedCache( self ):
        
        return self._seed_cache
        
    
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
        
        if self._controller.gui.IShouldRegularlyUpdate( self ):
            
            self._Update()
            
        
    
