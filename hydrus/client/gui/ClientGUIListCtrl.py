from . import ClientConstants as CC
from . import ClientGUIDragDrop
from . import ClientGUICommon
from . import ClientGUICore as CGC
from . import ClientGUIFunctions
from . import ClientSerialisable
from . import ClientGUIShortcuts
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
import os
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from . import QtPorting as QP

def SafeNoneInt( value ):
    
    return -1 if value is None else value
    
def SafeNoneStr( value ):
    
    return '' if value is None else value
    
class BetterListCtrl( QW.QTreeWidget ):
    
    listCtrlChanged = QC.Signal()
    
    def __init__( self, parent, name, height_num_chars, sizing_column_initial_width_num_chars, columns, data_to_tuples_func, use_simple_delete = False, delete_key_callback = None, activation_callback = None, style = None ):           
        
        QW.QTreeWidget.__init__( self, parent )
        
        self.setAlternatingRowColors( True )
        self.setColumnCount( len(columns) )
        self.setSortingEnabled( False ) # Keeping the custom sort implementation. It would be better to use Qt's native sorting in the future so sort indicators are displayed on the headers as expected.
        self.setSelectionMode( QW.QAbstractItemView.ExtendedSelection )
        self.setRootIsDecorated( False )
        
        self._data_to_tuples_func = data_to_tuples_func
        
        self._use_simple_delete = use_simple_delete
        
        self._menu_callable = None
        
        self._sort_column = 0
        self._sort_asc = True
        
        # eventually have it look up 'name' in some options somewhere and see previous height, width, and column selection
        # this thing should deal with missing entries but also have some filtered defaults for subs listctrl, which will have a bunch of possible columns
        
        self._indices_to_data_info = {}
        self._data_to_indices = {}
        
        sizing_column_initial_width = self.fontMetrics().boundingRect( 'x' * sizing_column_initial_width_num_chars ).width()
        total_width = self.fontMetrics().boundingRect( 'x' * sizing_column_initial_width_num_chars ).width()
        
        resize_column = 1
        
        for ( i, ( name, width_num_chars ) ) in enumerate( columns ):
            
            if width_num_chars == -1:
                
                width = -1
                
                resize_column = i + 1
                
            else:
                
                width = self.fontMetrics().boundingRect( 'x' * width_num_chars ).width()
                
                total_width += width
                
            
            self.headerItem().setText( i, name )
            
            self.setColumnWidth( i, width )
            
        
        # Technically this is the previous behavior, but the two commented lines might work better in some cases (?)
        self.header().setStretchLastSection( False )
        self.header().setSectionResizeMode( resize_column - 1 , QW.QHeaderView.Stretch )
        #self.setColumnWidth( resize_column - 1, sizing_column_initial_width )
        #self.header().setStretchLastSection( True )
        
        self.setMinimumWidth( total_width )
        
        self.GrowShrinkColumnsHeight( height_num_chars )
        
        self._delete_key_callback = delete_key_callback
        self._activation_callback = activation_callback
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        self._widget_event_filter.EVT_KEY_DOWN( self.EventKeyDown )
        self.itemDoubleClicked.connect( self.EventItemActivated )
        
        self.header().setSectionsClickable( True )
        self.header().sectionClicked.connect( self.EventColumnClick )
        
    
    def _AddDataInfo( self, data_info ):
        
        ( data, display_tuple, sort_tuple ) = data_info
        
        if data in self._data_to_indices:
            
            return
            
        
        append_item = QW.QTreeWidgetItem()
        
        for i in range( len( display_tuple ) ):
            
            text = display_tuple[i]
            
            if len( text ) > 0:
                
                text = text.splitlines()[0]
                
            
            append_item.setText( i, text )
            append_item.setToolTip( i, text )
            
        
        self.addTopLevelItem( append_item )
        
        index = self.topLevelItemCount() - 1 
        
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
        
        for i in range( self.topLevelItemCount() ):
            
            if self.topLevelItem( i ).isSelected(): indices.append( i )
        
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
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _SortDataInfo( self ):
        
        data_infos = list( self._indices_to_data_info.values() )
        
        def sort_key( data_info ):
            
            ( data, display_tuple, sort_tuple ) = data_info
            
            return ( sort_tuple[ self._sort_column ], sort_tuple ) # add the sort tuple to get secondary sorting
            
        
        data_infos.sort( key = sort_key, reverse = not self._sort_asc )
        
        return data_infos
        
    
    def _SortAndRefreshRows( self ):
        
        selected_data_quick = set( self.GetData( only_selected = True ) )
        
        # The lack of clearSelection below caused erroneous behavior when using the move up/down buttons in the string transformations dialog, so added it.
        # The commented out code should be a no-op after the Qt port, leaving it just in case.
        """
        selected_indices = self._GetSelected()
        
        for selected_index in selected_indices:
            
            self.topLevelItem( selected_index ).setSelected( True )
        """
        self.clearSelection()
        
        sorted_data_info = self._SortDataInfo()
        
        self._indices_to_data_info = {}
        self._data_to_indices = {}
        
        for ( index, data_info ) in enumerate( sorted_data_info ):
            
            self._indices_to_data_info[ index ] = data_info
            
            ( data, display_tuple, sort_tuple ) = data_info
            
            self._data_to_indices[ data ] = index
            
            self._UpdateRow( index, display_tuple )
            
            if data in selected_data_quick:
                
                self.topLevelItem( index ).setSelected( True )
                
            
        
    
    def _UpdateRow( self, index, display_tuple ):
        
        for ( column_index, value ) in enumerate( display_tuple ):
            
            if len( value ) > 0:
                
                value = value.splitlines()[0]
                
            
            tree_widget_item = self.topLevelItem( index )
            
            existing_value = tree_widget_item.text( column_index )
            
            if existing_value != value:
                
                tree_widget_item.setText( column_index, value )
                tree_widget_item.setToolTip( column_index, value )
                
            
        
    
    def AddDatas( self, datas ):
        
        for data in datas:
            
            ( display_tuple, sort_tuple ) = self._GetDisplayAndSortTuples( data )
            
            self._AddDataInfo( ( data, display_tuple, sort_tuple ) )
            
        
        self.listCtrlChanged.emit()
        
    
    def AddMenuCallable( self, menu_callable ):
        
        self._menu_callable = menu_callable
        
        self.setContextMenuPolicy( QC.Qt.CustomContextMenu )
        self.customContextMenuRequested.connect( self.EventShowMenu )
        
    
    def DeleteDatas( self, datas ):
        
        deletees = [ ( self._data_to_indices[ data ], data ) for data in datas ]
        
        deletees.sort( reverse = True )
        
        # The below comment is most probably obsolote (from before the Qt port), but keeping it just in case it is not and also as an explanation.
        #
        # I am not sure, but I think if subsequent deleteitems occur in the same event, the event processing of the first is forced!!
        # this means that button checking and so on occurs for n-1 times on an invalid indices structure in this thing before correcting itself in the last one
        # if a button update then tests selected data against the invalid index and a selection is on the i+1 or whatever but just got bumped up into invalid area, we are exception city
        # this doesn't normally affect us because mostly we _are_ deleting selections when we do deletes, but 'try to link url stuff' auto thing hit this
        # I obviously don't want to recalc all indices for every delete
        # so I wrote a catch in getdata to skip the missing error, and now I'm moving the data deletion to a second loop, which seems to help
        
        for ( index, data ) in deletees:
            
            self.takeTopLevelItem( index )
            
        
        for ( index, data ) in deletees:
            
            del self._data_to_indices[ data ]
            
            del self._indices_to_data_info[ index ]
            
        
        self._RecalculateIndicesAfterDelete()
        
        self.listCtrlChanged.emit()
        
    
    def DeleteSelected( self ):
        
        indices = self._GetSelected()
        
        indices.sort( reverse = True )
        
        for index in indices:
            
            ( data, display_tuple, sort_tuple ) = self._indices_to_data_info[ index ]
            
            item = self.takeTopLevelItem( index )
            
            del item
            
            del self._data_to_indices[ data ]
            
            del self._indices_to_data_info[ index ]
            
        
        self._RecalculateIndicesAfterDelete()
        
        self.listCtrlChanged.emit()
        
    
    def EventColumnClick( self, col ):
        
        if col == self._sort_column:
            
            self._sort_asc = not self._sort_asc
            
        else:
            
            self._sort_column = col
            
            self._sort_asc = True
            
        
        self._SortAndRefreshRows()
        
    
    def EventItemActivated( self, item, column ):
        
        if self._activation_callback is not None:
            
            self._activation_callback()
            
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ClientGUIShortcuts.DELETE_KEYS:
            
            self.ProcessDeleteAction()
            
        elif key in ( ord( 'A' ), ord( 'a' ) ) and modifier == QC.Qt.ControlModifier:
            
            self.selectAll()
            
        else:
            
            return True # was: event.ignore()
            
        
    
    def EventShowMenu( self ):
        
        QP.CallAfter( self._ShowMenu )
        
    
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
        
        existing_min_width = self.minimumWidth()
        
        ( width_gumpf, ideal_client_height ) = ClientGUIFunctions.ConvertTextToPixels( self, ( 20, int( ( ideal_rows + 2 ) * 1.25 ) ) )
        
        QP.SetMinClientSize( self, ( existing_min_width, ideal_client_height ) )
        
    
    def HasData( self, data ):
        
        return data in self._data_to_indices
        
    
    def HasOneSelected( self ):
        
        return len( self.selectedItems() ) == 1
        
    
    def HasSelected( self ):
        
        return len( self.selectedItems() ) > 0 
        
    
    def ProcessDeleteAction( self ):
        
        if self._use_simple_delete:
            
            self.ShowDeleteSelectedDialog()
            
        elif self._delete_key_callback is not None:
            
            self._delete_key_callback()
            
        
    
    def SelectDatas( self, datas ):
        
        for data in datas:
            
            if data in self._data_to_indices:
                
                index = self._data_to_indices[ data ]
                
                self.topLevelItem( index ).setSelected( True )
                
            
        
    
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
        
        self.listCtrlChanged.emit()
        
    
    def ShowDeleteSelectedDialog( self ):
        
        from . import ClientGUIDialogsQuick
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            self.DeleteSelected()
            
        
    
    def Sort( self, col = None, asc = None ):
        
        if col is not None:
            
            self._sort_column = col
            
        
        if asc is not None:
            
            self._sort_asc = asc
            
        
        self._SortAndRefreshRows()
        
        self.listCtrlChanged.emit()
        
    
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
                
            
        
        self.listCtrlChanged.emit()
        
        return sort_data_has_changed
    

    def SetNonDupeName( self, obj ):

        current_names = { o.GetName() for o in self.GetData() if o is not obj }

        HydrusSerialisable.SetNonDupeName( obj, current_names )
        
    
    def ReplaceData( self, old_data, new_data ):
        
        new_data = QP.ListsToTuples( new_data )
        
        data_index = self._data_to_indices[ old_data ]

        ( display_tuple, sort_tuple ) = self._GetDisplayAndSortTuples( new_data )
        
        data_info = ( new_data, display_tuple, sort_tuple )
        
        self._indices_to_data_info[ data_index ] = data_info
        
        del self._data_to_indices[ old_data ]
        
        self._data_to_indices[ new_data ] = data_index
        
        self._UpdateRow( data_index, display_tuple )
        
    
class BetterListCtrlPanel( QW.QWidget ):
    
    def __init__( self, parent ):
        
        QW.QWidget.__init__( self, parent )
        
        self._vbox = QP.VBoxLayout()
        
        self._buttonbox = QP.HBoxLayout()
        
        self._listctrl = None
        
        self._permitted_object_types = []
        self._import_add_callable = lambda x: None
        self._custom_get_callable = None
        
        self._button_infos = []
        
    
    def _AddAllDefaults( self, defaults_callable, add_callable ):
        
        defaults = defaults_callable()
        
        for default in defaults:
            
            add_callable( default )
            
        
        self._listctrl.Sort()
        
    
    def _AddButton( self, button, enabled_only_on_selection = False, enabled_only_on_single_selection = False, enabled_check_func = None ):
        
        QP.AddToLayout( self._buttonbox, button, CC.FLAGS_VCENTER )
        
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
            
            if dlg.exec() == QW.QDialog.Accepted:
                
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
                
                dlg.exec()
                
            
        
    
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
            
            dlg.exec()
            
        
    
    def _GetExportObject( self ):
        
        if self._custom_get_callable is None:
            
            to_export = HydrusSerialisable.SerialisableList()
            
            for obj in self._listctrl.GetData( only_selected = True ):
                
                to_export.append( obj )
                
            
        else:
            
            to_export = [ self._custom_get_callable() ]
            
        
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
            
            QW.QMessageBox.critical( self, 'Error', str(e) )
            
            return
            
        
        try:
            
            obj = HydrusSerialisable.CreateFromString( raw_text )
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard' )
            
        
        self._listctrl.Sort()
        
    
    def _ImportFromPng( self ):
        
        with QP.FileDialog( self, 'select the png or pngs with the encoded data', acceptMode = QW.QFileDialog.AcceptOpen, fileMode = QW.QFileDialog.ExistingFiles, wildcard = 'PNG (*.png)|*.png' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
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
            
            QW.QMessageBox.critical( self, 'Error', message )
            
        
    
    def _ImportPngs( self, paths ):
        
        for path in paths:
            
            try:
                
                payload = ClientSerialisable.LoadFromPng( path )
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            try:
                
                obj = HydrusSerialisable.CreateFromNetworkBytes( payload )
                
                self._ImportObject( obj )
                
            except:
                
                QW.QMessageBox.critical( self, 'Error', 'I could not understand what was encoded in the file!' )
                
                return
                
            
        
    
    def _UpdateButtons( self ):
        
        for ( button, enabled_check_func ) in self._button_infos:
            
            if enabled_check_func():
                
                button.setEnabled( True )
                
            else:
                
                button.setEnabled( False )
                
            
        
    
    def AddBitmapButton( self, bitmap, clicked_func, tooltip = None, enabled_only_on_selection = False, enabled_only_on_single_selection = False, enabled_check_func = None ):
        
        button = ClientGUICommon.BetterBitmapButton( self, bitmap, clicked_func )
        
        if tooltip is not None:
            
            button.setToolTip( tooltip )
            
        
        self._AddButton( button, enabled_only_on_selection = enabled_only_on_selection, enabled_only_on_single_selection = enabled_only_on_single_selection, enabled_check_func = enabled_check_func )
        
        self._UpdateButtons()
        
    
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
        
    
    def AddDeleteButton( self, enabled_check_func = None ):
        
        if enabled_check_func is None:
            
            enabled_only_on_selection = True
            
        else:
            
            enabled_only_on_selection = False
            
        
        self.AddButton( 'delete', self._listctrl.ProcessDeleteAction, enabled_check_func = enabled_check_func, enabled_only_on_selection = enabled_only_on_selection )
        
    
    def AddImportExportButtons( self, permitted_object_types, import_add_callable, custom_get_callable = None ):
        
        self._permitted_object_types = permitted_object_types
        self._import_add_callable = import_add_callable
        self._custom_get_callable = custom_get_callable
        
        export_menu_items = []
        
        export_menu_items.append( ( 'normal', 'to clipboard', 'Serialise the selected data and put it on your clipboard.', self._ExportToClipboard ) )
        export_menu_items.append( ( 'normal', 'to png', 'Serialise the selected data and encode it to an image file you can easily share with other hydrus users.', self._ExportToPng ) )
        
        if self._custom_get_callable is None:
            
            all_objs_are_named = False not in ( issubclass( o, HydrusSerialisable.SerialisableBaseNamed ) for o in self._permitted_object_types )
            
            if all_objs_are_named:
                
                export_menu_items.append( ( 'normal', 'to pngs', 'Serialise the selected data and encode it to multiple image files you can easily share with other hydrus users.', self._ExportToPngs ) )
                
            
        
        import_menu_items = []
        
        import_menu_items.append( ( 'normal', 'from clipboard', 'Load a data from text in your clipboard.', self._ImportFromClipboard ) )
        import_menu_items.append( ( 'normal', 'from pngs (note you can also drag and drop pngs onto this list)', 'Load a data from an encoded png.', self._ImportFromPng ) )
        
        self.AddMenuButton( 'export', export_menu_items, enabled_only_on_selection = True )
        self.AddMenuButton( 'import', import_menu_items )
        self.AddButton( 'duplicate', self._Duplicate, enabled_only_on_selection = True )
        
        self.setAcceptDrops( True )
        self.installEventFilter( ClientGUIDragDrop.FileDropTarget( self, filenames_callable = self.ImportFromDragDrop ) )
        
    
    def AddMenuButton( self, label, menu_items, enabled_only_on_selection = False, enabled_check_func = None ):
        
        button = ClientGUICommon.MenuButton( self, label, menu_items )
        
        self._AddButton( button, enabled_only_on_selection = enabled_only_on_selection, enabled_check_func = enabled_check_func )
        
        self._UpdateButtons()
        
    
    def AddSeparator( self ):
        
        self._buttonbox.insertStretch( -1, 1 )
        
    
    def AddWindow( self, window ):
        
        QP.AddToLayout( self._buttonbox, window, CC.FLAGS_VCENTER )
        
    
    def EventContentChanged( self, parent, first, last ):
        
        if not self._listctrl:
            
            return
            
        
        self._UpdateButtons()
        
    
    def EventSelectionChanged( self ):
        
        if not self._listctrl:
            
            return
            
        
        self._UpdateButtons()
        
    
    def ImportFromDragDrop( self, paths ):
        
        from . import ClientGUIDialogsQuick
        
        message = 'Try to import the ' + HydrusData.ToHumanInt( len( paths ) ) + ' dropped files to this list? I am expecting png files.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            self._ImportPngs( paths )
            
            self._listctrl.Sort()
            
        
    
    def NewButtonRow( self ):
        
        self._buttonbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._vbox, self._buttonbox, CC.FLAGS_BUTTON_SIZER )
        
    
    def SetListCtrl( self, listctrl ):
        
        self._listctrl = listctrl
        
        QP.AddToLayout( self._vbox, self._listctrl, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( self._vbox, self._buttonbox, CC.FLAGS_BUTTON_SIZER )
        
        self.setLayout( self._vbox )
        
        self._listctrl.itemSelectionChanged.connect( self.EventSelectionChanged )
        
        self._listctrl.model().rowsInserted.connect( self.EventContentChanged )
        self._listctrl.model().rowsRemoved.connect( self.EventContentChanged )
        
    
    def UpdateButtons( self ):
        
        self._UpdateButtons()
        
