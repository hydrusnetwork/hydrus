from . import ClientConstants as CC
from . import ClientData
from . import ClientDragDrop
from . import ClientGUICommon
from . import ClientGUIFunctions
from . import ClientSerialisable
from . import ClientGUIShortcuts
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
import os
import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

( ListCtrlEvent, EVT_LIST_CTRL ) = wx.lib.newevent.NewCommandEvent()

def SafeNoneInt( value ):
    
    return -1 if value is None else value
    
def SafeNoneStr( value ):
    
    return '' if value is None else value
    
# This used to be ColumnSorterMixin, but it was crashing on sort-click on clients with many pages open
# I've disabled it for now because it was still catching people. The transition to BetterListCtrl will nuke the whole thing eventually.
class SaneListCtrl( wx.ListCtrl, ListCtrlAutoWidthMixin ):
    
    def __init__( self, parent, height, columns, delete_key_callback = None, activation_callback = None ):
        
        num_columns = len( columns )
        
        wx.ListCtrl.__init__( self, parent, style = wx.LC_REPORT )
        ListCtrlAutoWidthMixin.__init__( self )
        
        self.itemDataMap = {}
        self._data_indices_to_sort_indices = {}
        self._data_indices_to_sort_indices_dirty = False
        self._next_data_index = 0
        
        resize_column = 1
        
        for ( i, ( name, width ) ) in enumerate( columns ):
            
            self.InsertColumn( i, name, width = width )
            
            if width == -1:
                
                resize_column = i + 1
                
            
        
        self.setResizeColumn( resize_column )
        
        self.SetMinSize( ( -1, height ) )
        
        self._delete_key_callback = delete_key_callback
        self._activation_callback = activation_callback
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        self.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventItemActivated )
        
        self.Bind( wx.EVT_LIST_COL_BEGIN_DRAG, self.EventBeginColDrag )
        
    
    def _GetIndexFromDataIndex( self, data_index ):
        
        if self._data_indices_to_sort_indices_dirty:
            
            self._data_indices_to_sort_indices = { self.GetItemData( index ) : index for index in range( self.GetItemCount() ) }
            
            self._data_indices_to_sort_indices_dirty = False
            
        
        try:
            
            return self._data_indices_to_sort_indices[ data_index ]
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'Data not found!' )
            
        
    
    def Append( self, display_tuple, sort_tuple ):
        
        index = wx.ListCtrl.Append( self, display_tuple )
        
        data_index = self._next_data_index
        
        self.SetItemData( index, data_index )
        
        self.itemDataMap[ data_index ] = list( sort_tuple )
        self._data_indices_to_sort_indices[ data_index ] = index
        
        self._next_data_index += 1
        
    
    def DeleteItem( self, *args, **kwargs ):
        
        wx.ListCtrl.DeleteItem( self, *args, **kwargs )
        
        self._data_indices_to_sort_indices_dirty = True
        
    
    def EventBeginColDrag( self, event ):
        
        # resizeCol is not zero-indexed
        
        if event.GetColumn() == self._resizeCol - 1:
            
            last_column = self.GetColumnCount()
            
            if self._resizeCol != last_column:
                
                self.setResizeColumn( last_column )
                
            else:
                
                event.Veto()
                
                return
                
            
        
        event.Skip()
        
    
    def EventItemActivated( self, event ):
        
        if self._activation_callback is not None:
            
            self._activation_callback()
            
        else:
            
            event.Skip()
            
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in CC.DELETE_KEYS:
            
            if self._delete_key_callback is not None:
                
                self._delete_key_callback()
                
            
        elif key in ( ord( 'A' ), ord( 'a' ) ) and modifier == wx.ACCEL_CTRL:
            
            self.SelectAll()
            
        else:
            
            event.Skip()
            
        
    
    def GetAllSelected( self ):
        
        indices = []
        
        i = self.GetFirstSelected()
        
        while i != -1:
            
            indices.append( i )
            
            i = self.GetNextSelected( i )
            
        
        return indices
        
    
    def GetClientData( self, index = None ):
        
        if index is None:
            
            data_indicies = [ self.GetItemData( index ) for index in range( self.GetItemCount() ) ]
            
            datas = [ tuple( self.itemDataMap[ data_index ] ) for data_index in data_indicies ]
            
            return datas
            
        else:
            
            data_index = self.GetItemData( index )
            
            return tuple( self.itemDataMap[ data_index ] )
            
        
    
    def GetIndexFromClientData( self, data, column_index = None ):
        
        for index in range( self.GetItemCount() ):
            
            client_data = self.GetClientData( index )
            
            if column_index is None:
                
                comparison_data = client_data
                
            else:
                
                comparison_data = client_data[ column_index ]
                
            
            if comparison_data == data:
                
                return index
                
            
        
        raise HydrusExceptions.DataMissing( 'Data not found!' )
        
    
    def GetSecondarySortValues( self, col, key1, key2 ):
        
        # This overrides the ColumnSortedMixin. Just spam the whole tuple back.
        
        return ( self.itemDataMap[ key1 ], self.itemDataMap[ key2 ] )
        
    
    def GetListCtrl( self ):
        
        return self
        
    
    def GetSelectedClientData( self ):
        
        indices = self.GetAllSelected()
        
        results = []
        
        for index in indices:
            
            results.append( self.GetClientData( index ) )
            
        
        return results
        
    
    def HasClientData( self, data, column_index = None ):
        
        try:
            
            index = self.GetIndexFromClientData( data, column_index )
            
            return True
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
    
    def OnSortOrderChanged( self ):
        
        self._data_indices_to_sort_indices_dirty = True
        
    
    def RemoveAllSelected( self ):
        
        indices = self.GetAllSelected()
        
        self.RemoveIndices( indices )
        
    
    def RemoveIndices( self, indices ):
        
        indices.sort()
        
        indices.reverse() # so we don't screw with the indices of deletees below
        
        for index in indices:
            
            self.DeleteItem( index )
            
        
    
    def SelectAll( self ):
        
        currently_selected = set( self.GetAllSelected() )
        
        currently_not_selected = [ index for index in range( self.GetItemCount() ) if index not in currently_selected ]
        
        for index in currently_not_selected:
            
            self.Select( index )
            
        
    
    def UpdateRow( self, index, display_tuple, sort_tuple ):
        
        column = 0
        
        for value in display_tuple:
            
            self.SetItem( index, column, value )
            
            column += 1
            
        
        data_index = self.GetItemData( index )
        
        self.itemDataMap[ data_index ] = list( sort_tuple )
        
    
class SaneListCtrlForSingleObject( SaneListCtrl ):
    
    def __init__( self, *args, **kwargs ):
        
        # this could one day just take column parameters that the user can pick
        # it could just take obj in append or whatever and generate column tuples off that
        
        self._data_indices_to_objects = {}
        self._objects_to_data_indices = {}
        
        SaneListCtrl.__init__( self, *args, **kwargs )
        
    
    def Append( self, display_tuple, sort_tuple, obj ):
        
        self._data_indices_to_objects[ self._next_data_index ] = obj
        self._objects_to_data_indices[ obj ] = self._next_data_index
        
        SaneListCtrl.Append( self, display_tuple, sort_tuple )
        
    
    def GetIndexFromObject( self, obj ):
        
        try:
            
            data_index = self._objects_to_data_indices[ obj ]
            
            index = self._GetIndexFromDataIndex( data_index )
            
            return index
            
        except KeyError:
            
            raise HydrusExceptions.DataMissing( 'Data not found!' )
            
        
    
    def GetObject( self, index ):
        
        data_index = self.GetItemData( index )
        
        return self._data_indices_to_objects[ data_index ]
        
    
    def GetObjects( self, only_selected = False ):
        
        if only_selected:
            
            indicies = self.GetAllSelected()
            
        else:
            
            indicies = list( range( self.GetItemCount() ) )
            
        
        data_indicies = [ self.GetItemData( index ) for index in indicies ]
        
        datas = [ self._data_indices_to_objects[ data_index ] for data_index in data_indicies ]
        
        return datas
        
    
    def HasObject( self, obj ):
        
        try:
            
            index = self.GetIndexFromObject( obj )
            
            return True
            
        except HydrusExceptions.DataMissing:
            
            return False
            
        
    
    def SetNonDupeName( self, obj ):
        
        # when column population is handled here, we can tuck this into normal append/update calls internally
        
        current_names = { o.GetName() for o in self.GetObjects() if o is not obj }
        
        HydrusSerialisable.SetNonDupeName( obj, current_names )
        
    
    def UpdateRow( self, index, display_tuple, sort_tuple, obj ):
        
        SaneListCtrl.UpdateRow( self, index, display_tuple, sort_tuple )
        
        data_index = self.GetItemData( index )
        
        self._data_indices_to_objects[ data_index ] = obj
        self._objects_to_data_indices[ obj ] = data_index
        
    
class SaneListCtrlPanel( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._listctrl = None
        
        self._button_infos = []
        
    
    def _SomeSelected( self ):
        
        return self._listctrl.GetSelectedItemCount() > 0
        
    
    def _UpdateButtons( self ):
        
        for ( button, enabled_check_func ) in self._button_infos:
            
            if enabled_check_func():
                
                button.Enable()
                
            else:
                
                button.Disable()
                
            
        
    
    def AddButton( self, label, clicked_func, enabled_only_on_selection = False, enabled_check_func = None ):
        
        button = ClientGUICommon.BetterButton( self, label, clicked_func )
        
        self._buttonbox.Add( button, CC.FLAGS_VCENTER )
        
        if enabled_only_on_selection:
            
            enabled_check_func = self._SomeSelected
            
        
        if enabled_check_func is not None:
            
            self._button_infos.append( ( button, enabled_check_func ) )
            
        
    
    def AddWindow( self, window ):
        
        self._buttonbox.Add( window, CC.FLAGS_VCENTER )
        
    
    def EventContentChanged( self, event ):
        
        if not self._listctrl:
            
            return
            
        
        self._UpdateButtons()
        
        event.Skip()
        
    
    def EventSelectionChanged( self, event ):
        
        if not self._listctrl:
            
            return
            
        
        self._UpdateButtons()
        
        event.Skip()
        
    
    def SetListCtrl( self, listctrl ):
        
        self._listctrl = listctrl
        
        self._vbox.Add( self._listctrl, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._vbox.Add( self._buttonbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( self._vbox )
        
        self._listctrl.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventSelectionChanged )
        self._listctrl.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventSelectionChanged )
        
        self._listctrl.Bind( wx.EVT_LIST_INSERT_ITEM, self.EventContentChanged )
        self._listctrl.Bind( wx.EVT_LIST_DELETE_ITEM, self.EventContentChanged )
        self._listctrl.Bind( wx.EVT_LIST_DELETE_ALL_ITEMS, self.EventContentChanged )
        
    
class BetterListCtrl( wx.ListCtrl, ListCtrlAutoWidthMixin ):
    
    def __init__( self, parent, name, height_num_chars, sizing_column_initial_width_num_chars, columns, data_to_tuples_func, use_simple_delete = False, delete_key_callback = None, activation_callback = None, style = None ):
        
        if style is None:
            
            style = wx.LC_REPORT
            
        else:
            
            style = wx.LC_REPORT | style
            
        
        wx.ListCtrl.__init__( self, parent, style = style )
        ListCtrlAutoWidthMixin.__init__( self )
        
        self._data_to_tuples_func = data_to_tuples_func
        
        self._use_simple_delete = use_simple_delete
        
        self._menu_callable = None
        
        self._sort_column = 0
        self._sort_asc = True
        
        # eventually have it look up 'name' in some options somewhere and see previous height, width, and column selection
        # this thing should deal with missing entries but also have some filtered defaults for subs listctrl, which will have a bunch of possible columns
        
        self._indices_to_data_info = {}
        self._data_to_indices = {}
        
        total_width = ClientGUIFunctions.ConvertTextToPixelWidth( self, sizing_column_initial_width_num_chars )
        
        resize_column = 1
        
        for ( i, ( name, width_num_chars ) ) in enumerate( columns ):
            
            if width_num_chars == -1:
                
                width = -1
                
                resize_column = i + 1
                
            else:
                
                width = ClientGUIFunctions.ConvertTextToPixelWidth( self, width_num_chars )
                
                total_width += width
                
            
            self.InsertColumn( i, name, width = width )
            
        
        self.setResizeColumn( resize_column )
        
        self.SetInitialSize( ( total_width, -1 ) )
        
        self.GrowShrinkColumnsHeight( height_num_chars )
        
        self._delete_key_callback = delete_key_callback
        self._activation_callback = activation_callback
        
        self.Bind( wx.EVT_KEY_DOWN, self.EventKeyDown )
        self.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.EventItemActivated )
        
        self.Bind( wx.EVT_LIST_COL_BEGIN_DRAG, self.EventBeginColDrag )
        self.Bind( wx.EVT_LIST_COL_CLICK, self.EventColumnClick )
        
    
    def _AddDataInfo( self, data_info ):
        
        ( data, display_tuple, sort_tuple ) = data_info
        
        if data in self._data_to_indices:
            
            return
            
        
        index = self.Append( display_tuple )
        
        self._indices_to_data_info[ index ] = data_info
        self._data_to_indices[ data ] = index
        
    
    def _GetDisplayAndSortTuples( self, data ):
        
        ( display_tuple, sort_tuple ) = self._data_to_tuples_func( data )
        
        better_sort = []
        
        for item in sort_tuple:
            
            if isinstance( item, str ):
                
                item = HydrusData.HumanTextSortKey( item )
                
            
            better_sort.append( item )
            
        
        sort_tuple = tuple( better_sort )
        
        return ( display_tuple, sort_tuple )
        
    
    def _GetSelected( self ):
        
        indices = []
        
        i = self.GetFirstSelected()
        
        while i != -1:
            
            indices.append( i )
            
            i = self.GetNextSelected( i )
            
        
        return indices
        
    
    def _RecalculateIndicesAfterDelete( self ):
        
        indices_and_data_info = list( self._indices_to_data_info.items() )
        
        indices_and_data_info.sort()
        
        self._indices_to_data_info = {}
        self._data_to_indices = {}
        
        for ( index, ( old_index, data_info ) ) in enumerate( indices_and_data_info ):
            
            ( data, display_tuple, sort_tuple ) = data_info
            
            self._data_to_indices[ data ] = index
            self._indices_to_data_info[ index ] = data_info
            
        
    
    def _ShowMenu( self ):
        
        try:
            
            menu = self._menu_callable()
            
        except HydrusExceptions.DataMissing:
            
            return
            
        
        HG.client_controller.PopupMenu( self, menu )
        
    
    def _SortDataInfo( self ):
        
        data_infos = list( self._indices_to_data_info.values() )
        
        def sort_key( data_info ):
            
            ( data, display_tuple, sort_tuple ) = data_info
            
            return ( sort_tuple[ self._sort_column ], sort_tuple ) # add the sort tuple to get secondary sorting
            
        
        data_infos.sort( key = sort_key, reverse = not self._sort_asc )
        
        return data_infos
        
    
    def _SortAndRefreshRows( self ):
        
        selected_data_quick = set( self.GetData( only_selected = True ) )
        
        selected_indices = self._GetSelected()
        
        for selected_index in selected_indices:
            
            self.Select( selected_index, False )
            
        
        sorted_data_info = self._SortDataInfo()
        
        self._indices_to_data_info = {}
        self._data_to_indices = {}
        
        for ( index, data_info ) in enumerate( sorted_data_info ):
            
            self._indices_to_data_info[ index ] = data_info
            
            ( data, display_tuple, sort_tuple ) = data_info
            
            self._data_to_indices[ data ] = index
            
            self._UpdateRow( index, display_tuple )
            
            if data in selected_data_quick:
                
                self.Select( index )
                
            
        
    
    def _UpdateRow( self, index, display_tuple ):
        
        for ( column_index, value ) in enumerate( display_tuple ):
            
            existing_value = self.GetItem( index, column_index )
            
            if existing_value != value:
                
                self.SetItem( index, column_index, value )
                
            
        
    
    def AddDatas( self, datas ):
        
        for data in datas:
            
            ( display_tuple, sort_tuple ) = self._GetDisplayAndSortTuples( data )
            
            self._AddDataInfo( ( data, display_tuple, sort_tuple ) )
            
        
        wx.QueueEvent( self.GetEventHandler(), ListCtrlEvent( -1 ) )
        
    
    def AddMenuCallable( self, menu_callable ):
        
        self._menu_callable = menu_callable
        
        self.Bind( wx.EVT_RIGHT_DOWN, self.EventShowMenu )
        
    
    def DeleteDatas( self, datas ):
        
        deletees = [ ( self._data_to_indices[ data ], data ) for data in datas ]
        
        deletees.sort( reverse = True )
        
        # I am not sure, but I think if subsequent deleteitems occur in the same event, the event processing of the first is forced!!
        # this means that button checking and so on occurs for n-1 times on an invalid indices structure in this thing before correcting itself in the last one
        # if a button update then tests selected data against the invalid index and a selection is on the i+1 or whatever but just got bumped up into invalid area, we are exception city
        # this doesn't normally affect us because mostly we _are_ deleting selections when we do deletes, but 'try to link url stuff' auto thing hit this
        # I obviously don't want to recalc all indices for every delete
        # so I wrote a catch in getdata to skip the missing error, and now I'm moving the data deletion to a second loop, which seems to help
        
        for ( index, data ) in deletees:
            
            self.DeleteItem( index )
            
        
        for ( index, data ) in deletees:
            
            del self._data_to_indices[ data ]
            
            del self._indices_to_data_info[ index ]
            
        
        self._RecalculateIndicesAfterDelete()
        
        wx.QueueEvent( self.GetEventHandler(), ListCtrlEvent( -1 ) )
        
    
    def DeleteSelected( self ):
        
        indices = self._GetSelected()
        
        indices.sort( reverse = True )
        
        for index in indices:
            
            ( data, display_tuple, sort_tuple ) = self._indices_to_data_info[ index ]
            
            self.DeleteItem( index )
            
            del self._data_to_indices[ data ]
            
            del self._indices_to_data_info[ index ]
            
        
        self._RecalculateIndicesAfterDelete()
        
        wx.QueueEvent( self.GetEventHandler(), ListCtrlEvent( -1 ) )
        
    
    def EventBeginColDrag( self, event ):
        
        # resizeCol is not zero-indexed
        
        if event.GetColumn() == self._resizeCol - 1:
            
            last_column = self.GetColumnCount()
            
            if self._resizeCol != last_column:
                
                self.setResizeColumn( last_column )
                
            else:
                
                event.Veto()
                
                return
                
            
        
        event.Skip()
        
    
    def EventColumnClick( self, event ):
        
        col = event.GetColumn()
        
        if col == self._sort_column:
            
            self._sort_asc = not self._sort_asc
            
        else:
            
            self._sort_column = col
            
            self._sort_asc = True
            
        
        self._SortAndRefreshRows()
        
    
    def EventItemActivated( self, event ):
        
        if self._activation_callback is not None:
            
            self._activation_callback()
            
        else:
            
            event.Skip()
            
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in CC.DELETE_KEYS:
            
            self.ProcessDeleteAction()
            
        elif key in ( ord( 'A' ), ord( 'a' ) ) and modifier == wx.ACCEL_CTRL:
            
            self.SelectAll()
            
        else:
            
            event.Skip()
            
        
    
    def EventShowMenu( self, event ):
        
        wx.CallAfter( self._ShowMenu )
        
        event.Skip() # let the right click event go through before doing menu, in case selection should happen
        
    
    def GetData( self, only_selected = False ):
        
        if only_selected:
            
            indices = self._GetSelected()
            
        else:
            
            indices = list(self._indices_to_data_info.keys())
            
        
        result = []
        
        for index in indices:
            
            # this can get fired while indices are invalid, wew
            if index not in self._indices_to_data_info:
                
                continue
                
            
            ( data, display_tuple, sort_tuple ) = self._indices_to_data_info[ index ]
            
            result.append( data )
            
        
        return result
        
    
    def GrowShrinkColumnsHeight( self, ideal_rows ):
        
        # +2 for the header row and * 1.25 for magic rough text-to-rowheight conversion
        
        existing_min_width = self.GetMinClientSize()[0]
        
        ( width_gumpf, ideal_client_height ) = ClientGUIFunctions.ConvertTextToPixels( self, ( 20, int( ( ideal_rows + 2 ) * 1.25 ) ) )
        
        self.SetMinClientSize( ( existing_min_width, ideal_client_height ) )
        
    
    def HasData( self, data ):
        
        return data in self._data_to_indices
        
    
    def HasOneSelected( self ):
        
        return self.GetSelectedItemCount() == 1
        
    
    def HasSelected( self ):
        
        return self.GetSelectedItemCount() > 0
        
    
    def ProcessDeleteAction( self ):
        
        if self._use_simple_delete:
            
            self.ShowDeleteSelectedDialog()
            
        elif self._delete_key_callback is not None:
            
            self._delete_key_callback()
            
        
    
    def SelectAll( self ):
        
        currently_selected = set( self._GetSelected() )
        
        currently_not_selected = [ index for index in range( self.GetItemCount() ) if index not in currently_selected ]
        
        for index in currently_not_selected:
            
            self.Select( index )
            
        
    
    def SelectDatas( self, datas ):
        
        for data in datas:
            
            if data in self._data_to_indices:
                
                index = self._data_to_indices[ data ]
                
                self.Select( index )
                
            
        
    
    def SelectNone( self ):
        
        currently_selected = set( self._GetSelected() )
        
        for index in currently_selected:
            
            self.Select( index, False )
            
        
    
    def SetData( self, datas ):
        
        existing_datas = set( self._data_to_indices.keys() )
        
        # useful to preserve order here sometimes (e.g. export file path generation order)
        datas_to_add = [ data for data in datas if data not in existing_datas ]
        datas_to_update = [ data for data in datas if data in existing_datas ]
        datas_to_delete = existing_datas.difference( datas )
        
        if len( datas_to_delete ) > 0:
            
            self.DeleteDatas( datas_to_delete )
            
        
        if len( datas_to_update ) > 0:
            
            self.UpdateDatas( datas_to_update )
            
        
        if len( datas_to_add ) > 0:
            
            self.AddDatas( datas_to_add )
            
        
        self._SortAndRefreshRows()
        
        wx.QueueEvent( self.GetEventHandler(), ListCtrlEvent( -1 ) )
        
    
    def ShowDeleteSelectedDialog( self ):
        
        from . import ClientGUIDialogs
        
        with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self.DeleteSelected()
                
            
        
    
    def Sort( self, col = None, asc = None ):
        
        if col is not None:
            
            self._sort_column = col
            
        
        if asc is not None:
            
            self._sort_asc = asc
            
        
        self._SortAndRefreshRows()
        
        wx.QueueEvent( self.GetEventHandler(), ListCtrlEvent( -1 ) )
        
    
    def UpdateDatas( self, datas = None ):
        
        if datas is None:
            
            # keep it sorted here, which is sometimes useful
            
            indices_and_datas = [ ( index, data ) for ( data, index ) in self._data_to_indices.items() ]
            
            indices_and_datas.sort()
            
            datas = [ data for ( index, data ) in indices_and_datas ]
            
        
        sort_data_has_changed = False
        
        for data in datas:
            
            ( display_tuple, sort_tuple ) = self._GetDisplayAndSortTuples( data )
            
            data_info = ( data, display_tuple, sort_tuple )
            
            index = self._data_to_indices[ data ]
            
            existing_data_info = self._indices_to_data_info[ index ]
            
            if data_info != existing_data_info:
                
                if not sort_data_has_changed:
                    
                    ( existing_data, existing_display_tuple, existing_sort_tuple ) = existing_data_info
                    
                    if sort_tuple[ self._sort_column ] != existing_sort_tuple[ self._sort_column ]: # this does not govern secondary sorts, but let's not spam sorts m8
                        
                        sort_data_has_changed = True
                        
                    
                
                self._indices_to_data_info[ index ] = data_info
                
                self._UpdateRow( index, display_tuple )
                
            
        
        wx.QueueEvent( self.GetEventHandler(), ListCtrlEvent( -1 ) )
        
        return sort_data_has_changed
        

class BetterListCtrlPanel( wx.Panel ):
    
    def __init__( self, parent ):
        
        wx.Panel.__init__( self, parent )
        
        self._vbox = wx.BoxSizer( wx.VERTICAL )
        
        self._buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._listctrl = None
        
        self._permitted_object_types = []
        self._import_add_callable = lambda x: None
        
        self._button_infos = []
        
    
    def _AddAllDefaults( self, defaults_callable, add_callable ):
        
        defaults = defaults_callable()
        
        for default in defaults:
            
            add_callable( default )
            
        
        self._listctrl.Sort()
        
    
    def _AddButton( self, button, enabled_only_on_selection = False, enabled_only_on_single_selection = False, enabled_check_func = None ):
        
        self._buttonbox.Add( button, CC.FLAGS_VCENTER )
        
        if enabled_only_on_selection:
            
            enabled_check_func = self._HasSelected
            
        
        if enabled_only_on_single_selection:
            
            enabled_check_func = self._HasOneSelected
            
        
        if enabled_check_func is not None:
            
            self._button_infos.append( ( button, enabled_check_func ) )
            
        
    
    def _AddSomeDefaults( self, defaults_callable, add_callable ):
        
        defaults = defaults_callable()
        
        selected = False
        
        choice_tuples = [ ( default.GetName(), default, selected ) for default in defaults ]
        
        from . import ClientGUITopLevelWindows
        from . import ClientGUIScrolledPanelsEdit
        
        with ClientGUITopLevelWindows.DialogEdit( self, 'select the defaults to add' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditChooseMultiple( dlg, choice_tuples )
            
            dlg.SetPanel( panel )
            
            if dlg.ShowModal() == wx.ID_OK:
                
                defaults_to_add = panel.GetValue()
                
                for default in defaults_to_add:
                    
                    add_callable( default )
                    
                
            
        
        self._listctrl.Sort()
        
    
    def _Duplicate( self ):
        
        dupe_data = self._GetExportObject()
        
        if dupe_data is not None:
            
            dupe_data = dupe_data.Duplicate()
            
            self._ImportObject( dupe_data )
            
        
        self._listctrl.Sort()
        
    
    def _ExportToClipboard( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            HG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def _ExportToPng( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            from . import ClientGUITopLevelWindows
            from . import ClientGUISerialisable
            
            with ClientGUITopLevelWindows.DialogNullipotent( self, 'export to png' ) as dlg:
                
                panel = ClientGUISerialisable.PngExportPanel( dlg, export_object )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
        
    
    def _ExportToPngs( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is None:
            
            return
            
        
        if not isinstance( export_object, HydrusSerialisable.SerialisableList ):
            
            self._ExportToPng()
            
            return
            
        
        from . import ClientGUITopLevelWindows
        from . import ClientGUISerialisable
        
        with ClientGUITopLevelWindows.DialogNullipotent( self, 'export to pngs' ) as dlg:
            
            panel = ClientGUISerialisable.PngsExportPanel( dlg, export_object )
            
            dlg.SetPanel( panel )
            
            dlg.ShowModal()
            
        
    
    def _GetExportObject( self ):
        
        to_export = HydrusSerialisable.SerialisableList()
        
        for obj in self._listctrl.GetData( only_selected = True ):
            
            to_export.append( obj )
            
        
        if len( to_export ) == 0:
            
            return None
            
        elif len( to_export ) == 1:
            
            return to_export[0]
            
        else:
            
            return to_export
            
        
    
    def _HasSelected( self ):
        
        return self._listctrl.HasSelected()
        
    
    def _HasOneSelected( self ):
        
        return self._listctrl.HasOneSelected()
        
    
    def _ImportFromClipboard( self ):
        
        try:
            
            raw_text = HG.client_controller.GetClipboardText()
            
        except HydrusExceptions.DataMissing as e:
            
            wx.MessageBox( str( e ) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            wx.MessageBox( 'I could not understand what was in the clipboard' )
            
        
        self._listctrl.Sort()
        
    
    def _ImportFromPng( self ):
        
        with wx.FileDialog( self, 'select the png or pngs with the encoded data', style = wx.FD_OPEN | wx.FD_MULTIPLE, wildcard = 'PNG (*.png)|*.png' ) as dlg:
            
            if dlg.ShowModal() == wx.ID_OK:
                
                paths = dlg.GetPaths()
                
                self._ImportPngs( paths )
                
            
        
        self._listctrl.Sort()
        
    
    def _ImportObject( self, obj ):
        
        bad_object_type_names = set()
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                self._ImportObject( sub_obj )
                
            
        else:
            
            if isinstance( obj, self._permitted_object_types ):
                
                self._import_add_callable( obj )
                
            else:
                
                bad_object_type_names.add( HydrusData.GetTypeName( type( obj ) ) )
                
            
        
        if len( bad_object_type_names ) > 0:
            
            message = 'The imported objects included these types:'
            message += os.linesep * 2
            message += os.linesep.join( bad_object_type_names )
            message += os.linesep * 2
            message += 'Whereas this control only allows:'
            message += os.linesep * 2
            message += os.linesep.join( ( HydrusData.GetTypeName( o ) for o in self._permitted_object_types ) )
            
            wx.MessageBox( message )
            
        
    
    def _ImportPngs( self, paths ):
        
        for path in paths:
            
            try:
                
                payload = ClientSerialisable.LoadFromPng( path )
                
            except Exception as e:
                
                wx.MessageBox( str( e ) )
                
                return
                
            
            try:
                
                obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
                
                self._ImportObject( obj )
                
            except:
                
                wx.MessageBox( 'I could not understand what was encoded in the file!' )
                
                return
                
            
        
    
    def _UpdateButtons( self ):
        
        for ( button, enabled_check_func ) in self._button_infos:
            
            if enabled_check_func():
                
                button.Enable()
                
            else:
                
                button.Disable()
                
            
        
    
    def AddButton( self, label, clicked_func, enabled_only_on_selection = False, enabled_only_on_single_selection = False, enabled_check_func = None ):
        
        button = ClientGUICommon.BetterButton( self, label, clicked_func )
        
        self._AddButton( button, enabled_only_on_selection = enabled_only_on_selection, enabled_only_on_single_selection = enabled_only_on_single_selection, enabled_check_func = enabled_check_func )
        
        self._UpdateButtons()
        
    
    def AddDefaultsButton( self, defaults_callable, add_callable ):
        
        import_menu_items = []
        
        all_call = HydrusData.Call( self._AddAllDefaults, defaults_callable, add_callable )
        some_call = HydrusData.Call( self._AddSomeDefaults, defaults_callable, add_callable )
        
        import_menu_items.append( ( 'normal', 'add them all', 'Load all the defaults.', all_call ) )
        import_menu_items.append( ( 'normal', 'select from a list', 'Load some of the defaults.', some_call ) )
        
        self.AddMenuButton( 'add defaults', import_menu_items )
        
    
    def AddDeleteButton( self ):
        
        self.AddButton( 'delete', self._listctrl.ProcessDeleteAction, enabled_only_on_selection = True )
        
    
    def AddImportExportButtons( self, permitted_object_types, import_add_callable ):
        
        self._permitted_object_types = permitted_object_types
        self._import_add_callable = import_add_callable
        
        export_menu_items = []
        
        export_menu_items.append( ( 'normal', 'to clipboard', 'Serialise the selected data and put it on your clipboard.', self._ExportToClipboard ) )
        export_menu_items.append( ( 'normal', 'to png', 'Serialise the selected data and encode it to an image file you can easily share with other hydrus users.', self._ExportToPng ) )
        
        all_objs_are_named = False not in ( issubclass( o, HydrusSerialisable.SerialisableBaseNamed ) for o in self._permitted_object_types )
        
        if all_objs_are_named:
            
            export_menu_items.append( ( 'normal', 'to pngs', 'Serialise the selected data and encode it to multiple image files you can easily share with other hydrus users.', self._ExportToPngs ) )
            
        
        import_menu_items = []
        
        import_menu_items.append( ( 'normal', 'from clipboard', 'Load a data from text in your clipboard.', self._ImportFromClipboard ) )
        import_menu_items.append( ( 'normal', 'from pngs (note you can also drag and drop pngs onto this list)', 'Load a data from an encoded png.', self._ImportFromPng ) )
        
        self.AddMenuButton( 'export', export_menu_items, enabled_only_on_selection = True )
        self.AddMenuButton( 'import', import_menu_items )
        self.AddButton( 'duplicate', self._Duplicate, enabled_only_on_selection = True )
        
        self.SetDropTarget( ClientDragDrop.FileDropTarget( self, filenames_callable = self.ImportFromDragDrop ) )
        
    
    def AddMenuButton( self, label, menu_items, enabled_only_on_selection = False, enabled_check_func = None ):
        
        button = ClientGUICommon.MenuButton( self, label, menu_items )
        
        self._AddButton( button, enabled_only_on_selection = enabled_only_on_selection, enabled_check_func = enabled_check_func )
        
        self._UpdateButtons()
        
    
    def AddSeparator( self ):
        
        self._buttonbox.Add( ( 20, 20 ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
    
    def AddWindow( self, window ):
        
        self._buttonbox.Add( window, CC.FLAGS_VCENTER )
        
    
    def EventContentChanged( self, event ):
        
        if not self._listctrl:
            
            return
            
        
        self._UpdateButtons()
        
        event.Skip()
        
    
    def EventSelectionChanged( self, event ):
        
        if not self._listctrl:
            
            return
            
        
        self._UpdateButtons()
        
        event.Skip()
        
    
    def ImportFromDragDrop( self, paths ):
        
        from . import ClientGUIDialogs
        
        message = 'Try to import the ' + HydrusData.ToHumanInt( len( paths ) ) + ' dropped files to this list? I am expecting png files.'
        
        with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
            
            if dlg.ShowModal() == wx.ID_YES:
                
                self._ImportPngs( paths )
                
                self._listctrl.Sort()
                
            
        
    
    def NewButtonRow( self ):
        
        self._buttonbox = wx.BoxSizer( wx.HORIZONTAL )
        
        self._vbox.Add( self._buttonbox, CC.FLAGS_BUTTON_SIZER )
        
    
    def SetListCtrl( self, listctrl ):
        
        self._listctrl = listctrl
        
        self._vbox.Add( self._listctrl, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._vbox.Add( self._buttonbox, CC.FLAGS_BUTTON_SIZER )
        
        self.SetSizer( self._vbox )
        
        self._listctrl.Bind( wx.EVT_LIST_ITEM_SELECTED, self.EventSelectionChanged )
        self._listctrl.Bind( wx.EVT_LIST_ITEM_DESELECTED, self.EventSelectionChanged )
        
        self._listctrl.Bind( wx.EVT_LIST_INSERT_ITEM, self.EventContentChanged )
        self._listctrl.Bind( wx.EVT_LIST_DELETE_ITEM, self.EventContentChanged )
        self._listctrl.Bind( wx.EVT_LIST_DELETE_ALL_ITEMS, self.EventContentChanged )
        
    
    def UpdateButtons( self ):
        
        self._UpdateButtons()
        
