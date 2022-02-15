import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientSerialisable
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListStatus
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton

def SafeNoneInt( value ):
    
    return -1 if value is None else value
    
def SafeNoneStr( value ):
    
    return '' if value is None else value
    
class BetterListCtrl( QW.QTreeWidget ):
    
    columnListContentsChanged = QC.Signal()
    columnListStatusChanged = QC.Signal()
    
    def __init__( self, parent, column_list_type, height_num_chars, data_to_tuples_func, use_simple_delete = False, delete_key_callback = None, activation_callback = None, style = None, column_types_to_name_overrides = None ):           
        
        QW.QTreeWidget.__init__( self, parent )
        
        self._have_shown_a_column_data_error = False
        
        self._creation_time = HydrusData.GetNow()
        
        self._column_list_type = column_list_type
        
        self._column_list_status: ClientGUIListStatus.ColumnListStatus = HG.client_controller.column_list_manager.GetStatus( self._column_list_type )
        self._original_column_list_status = self._column_list_status
        
        self.setAlternatingRowColors( True )
        self.setColumnCount( self._column_list_status.GetColumnCount() )
        self.setSortingEnabled( False ) # Keeping the custom sort implementation. It would be better to use Qt's native sorting in the future so sort indicators are displayed on the headers as expected.
        self.setSelectionMode( QW.QAbstractItemView.ExtendedSelection )
        self.setRootIsDecorated( False )
        
        self._initial_height_num_chars = height_num_chars
        self._forced_height_num_chars = None
        
        self._data_to_tuples_func = data_to_tuples_func
        
        self._use_simple_delete = use_simple_delete
        
        self._menu_callable = None
        
        ( self._sort_column_type, self._sort_asc ) = self._column_list_status.GetSort()
        
        self._indices_to_data_info = {}
        self._data_to_indices = {}
        
        # old way
        '''
        #sizing_column_initial_width = self.fontMetrics().boundingRect( 'x' * sizing_column_initial_width_num_chars ).width()
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
        '''
        main_tlw = HG.client_controller.GetMainTLW()
        
        # if last section is set too low, for instance 3, the column seems unable to ever shrink from initial (expanded to fill space) size
        #  _    _  ___  _    _    __     __   ___  
        # ( \/\/ )(  _)( \/\/ )  (  )   (  ) (   \ 
        #  \    /  ) _) \    /    )(__  /__\  ) ) )
        #   \/\/  (___)  \/\/    (____)(_)(_)(___/ 
        #
        # I think this is because of mismatch between set size and min size! So ensuring we never set smaller than that initially should fix this???!?
        
        MIN_SECTION_SIZE_CHARS = 3
        MIN_LAST_SECTION_SIZE_CHARS = 10
        
        self._min_section_width = ClientGUIFunctions.ConvertTextToPixelWidth( main_tlw, MIN_SECTION_SIZE_CHARS )
        
        self.header().setMinimumSectionSize( self._min_section_width )
        
        last_column_index = self._column_list_status.GetColumnCount() - 1
        
        for ( i, column_type ) in enumerate( self._column_list_status.GetColumnTypes() ):
            
            self.headerItem().setData( i, QC.Qt.UserRole, column_type )
            
            if column_types_to_name_overrides is not None and column_type in column_types_to_name_overrides:
                
                name = column_types_to_name_overrides[ column_type ]
                
            else:
                
                name = CGLC.column_list_column_name_lookup[ self._column_list_type ][ column_type ]
                
            
            self.headerItem().setText( i, name )
            self.headerItem().setToolTip( i, name )
            
            if i == last_column_index:
                
                width_chars = MIN_SECTION_SIZE_CHARS
                
            else:
                
                width_chars = self._column_list_status.GetColumnWidth( column_type )
                
            
            width_chars = max( width_chars, MIN_SECTION_SIZE_CHARS )
            
            # ok this is a pain in the neck issue, but fontmetrics changes afte widget init. I guess font gets styled on top afterwards
            # this means that if I use this window's fontmetrics here, in init, then it is different later on, and we get creeping growing columns lmao
            # several other places in the client are likely affected in different ways by this also!
            width_pixels = ClientGUIFunctions.ConvertTextToPixelWidth( main_tlw, width_chars )
            
            self.setColumnWidth( i, width_pixels )
            
        
        self.header().setStretchLastSection( True )
        
        self._delete_key_callback = delete_key_callback
        self._activation_callback = activation_callback
        
        self._widget_event_filter = QP.WidgetEventFilter( self )
        self._widget_event_filter.EVT_KEY_DOWN( self.EventKeyDown )
        self.itemDoubleClicked.connect( self.EventItemActivated )
        
        self.header().setSectionsMovable( False ) # can only turn this on when we move from data/sort tuples
        # self.header().setFirstSectionMovable( True ) # same
        self.header().setSectionsClickable( True )
        self.header().sectionClicked.connect( self.EventColumnClick )
        
        #self.header().sectionMoved.connect( self._DoStatusChanged ) # same
        self.header().sectionResized.connect( self._SectionsResized )
        
    
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
        
    
    def _SectionsResized( self, logical_index, old_size, new_size ):
        
        self._DoStatusChanged()
        
        self.updateGeometry()
        
    
    def _DoStatusChanged( self ):
        
        self._column_list_status = self._GenerateCurrentStatus()
        
        HG.client_controller.column_list_manager.SaveStatus( self._column_list_status )
        
    
    def _GenerateCurrentStatus( self ) -> ClientGUIListStatus.ColumnListStatus:
        
        status = ClientGUIListStatus.ColumnListStatus()
        
        status.SetColumnListType( self._column_list_type )
        
        main_tlw = HG.client_controller.GetMainTLW()
        
        columns = []
        
        header = self.header()
        
        num_columns = header.count()
        
        last_column_index = num_columns - 1
        
        # ok, the big pain in the ass situation here is getting a precise last column size that is reproduced on next dialog launch
        # ultimately, with fuzzy sizing, style padding, scrollbars appearing, and other weirdness, the more precisely we try to define it, the more we will get dialogs that grow/shrink by a pixel each time
        # *therefore*, the actual solution here is to move to snapping with a decent snap distance. the user loses size setting precision, but we'll snap back to a decent size every time, compensating for fuzz
        
        LAST_COLUMN_SNAP_DISTANCE_CHARS = 5
        
        total_fixed_columns_width = 0
        
        for visual_index in range( num_columns ):
            
            logical_index = header.logicalIndex( visual_index )
            
            column_type = self.headerItem().data( logical_index, QC.Qt.UserRole )
            width_pixels = header.sectionSize( logical_index )
            shown = not header.isSectionHidden( logical_index )
            
            if visual_index == last_column_index:
                
                # testing if scrollbar is visible is unreliable, since we don't know if it is laid out correct yet (we could be doing that now!)
                # so let's just hack it
                
                width_pixels = self.width() - ( self.frameWidth() * 2 ) - total_fixed_columns_width
                
            else:
                
                total_fixed_columns_width += width_pixels
                
            
            width_chars = ClientGUIFunctions.ConvertPixelsToTextWidth( main_tlw, width_pixels )
            
            if visual_index == last_column_index:
                
                # here's the snap magic. final width_chars is always a multiple of 5
                width_chars = round( width_chars / LAST_COLUMN_SNAP_DISTANCE_CHARS ) * LAST_COLUMN_SNAP_DISTANCE_CHARS
                
            
            columns.append( ( column_type, width_chars, shown ) )
            
        
        status.SetColumns( columns )
        
        status.SetSort( self._sort_column_type, self._sort_asc )
        
        return status
        
    
    def _GetDisplayAndSortTuples( self, data ):
        
        try:
            
            ( display_tuple, sort_tuple ) = self._data_to_tuples_func( data )
            
        except Exception as e:
            
            if not self._have_shown_a_column_data_error:
                
                HydrusData.ShowText( 'A multi-column list was unable to generate text or sort data for one or more rows! Please send hydrus dev the traceback!' )
                HydrusData.ShowException( e )
                
                self._have_shown_a_column_data_error = True
                
            
            error_display_tuple = [ 'unable to display' for i in range( self._column_list_status.GetColumnCount() ) ]
            
            return ( error_display_tuple, None )
            
        
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
            
            if self.topLevelItem( i ).isSelected():
                
                indices.append( i )
                
            
        
        return indices
        
    
    def _RecalculateIndicesAfterDelete( self ):
        
        indices_and_data_info = sorted( self._indices_to_data_info.items() )
        
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
        
        sort_column_index = self._column_list_status.GetColumnIndexFromType( self._sort_column_type )
        
        data_infos = list( self._indices_to_data_info.values() )
        
        data_infos_good = [ ( data, display_tuple, sort_tuple ) for ( data, display_tuple, sort_tuple ) in data_infos if sort_tuple is not None ]
        data_infos_bad = [ ( data, display_tuple, sort_tuple ) for ( data, display_tuple, sort_tuple ) in data_infos if sort_tuple is None ]
        
        def sort_key( data_info ):
            
            ( data, display_tuple, sort_tuple ) = data_info
            
            return ( sort_tuple[ sort_column_index ], sort_tuple ) # add the sort tuple to get secondary sorting
            
        
        try:
            
            data_infos_good.sort( key = sort_key, reverse = not self._sort_asc )
            
        except Exception as e:
            
            HydrusData.ShowText( 'A multi-column list failed to sort! Please send hydrus dev the traceback!' )
            HydrusData.ShowException( e )
            
        
        data_infos_bad.extend( data_infos_good )
        
        data_infos = data_infos_bad
        
        return data_infos
        
    
    def _SortAndRefreshRows( self ):
        
        selected_data_quick = set( self.GetData( only_selected = True ) )
        
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
                
            
        
    
    def AddDatas( self, datas: typing.Iterable[ object ] ):
        
        for data in datas:
            
            ( display_tuple, sort_tuple ) = self._GetDisplayAndSortTuples( data )
            
            self._AddDataInfo( ( data, display_tuple, sort_tuple ) )
            
        
        self.columnListContentsChanged.emit()
        
    
    def AddMenuCallable( self, menu_callable ):
        
        self._menu_callable = menu_callable
        
        self.setContextMenuPolicy( QC.Qt.CustomContextMenu )
        self.customContextMenuRequested.connect( self.EventShowMenu )
        
    
    def DeleteDatas( self, datas: typing.Iterable[ object ] ):
        
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
        
        self.columnListContentsChanged.emit()
        
    
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
        
        self.columnListContentsChanged.emit()
        
    
    def EventColumnClick( self, col ):
        
        sort_column_type = self._column_list_status.GetColumnTypeFromIndex( col )
        
        if sort_column_type == self._sort_column_type:
            
            self._sort_asc = not self._sort_asc
            
        else:
            
            self._sort_column_type = sort_column_type
            
            self._sort_asc = True
            
        
        self._SortAndRefreshRows()
        
        self._DoStatusChanged()
        
    
    def EventItemActivated( self, item, column ):
        
        if self._activation_callback is not None:
            
            self._activation_callback()
            
        
    
    def EventKeyDown( self, event ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        if key in ClientGUIShortcuts.DELETE_KEYS_QT:
            
            self.ProcessDeleteAction()
            
        elif key in ( QC.Qt.Key_Enter, QC.Qt.Key_Return ):
            
            self.ProcessActivateAction()
            
        elif key in ( ord( 'A' ), ord( 'a' ) ) and modifier == QC.Qt.ControlModifier:
            
            self.selectAll()
            
        else:
            
            return True # was: event.ignore()
            
        
    
    def EventShowMenu( self ):
        
        QP.CallAfter( self._ShowMenu )
        
    
    def ForceHeight( self, rows ):
        
        self._forced_height_num_chars = rows
        
        self.updateGeometry()
        
        # +2 for the header row and * 1.25 for magic rough text-to-rowheight conversion
        
        #existing_min_width = self.minimumWidth()
        
        #( width_gumpf, ideal_client_height ) = ClientGUIFunctions.ConvertTextToPixels( self, ( 20, int( ( ideal_rows + 2 ) * 1.25 ) ) )
        
        #QP.SetMinClientSize( self, ( existing_min_width, ideal_client_height ) )
        
    
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
        
    
    def HasData( self, data: object ):
        
        return data in self._data_to_indices
        
    
    def HasOneSelected( self ):
        
        return len( self.selectedItems() ) == 1
        
    
    def HasSelected( self ):
        
        return len( self.selectedItems() ) > 0 
        
    
    def ProcessActivateAction( self ):
        
        if self._activation_callback is not None:
            
            self._activation_callback()
            
        
    
    def ProcessDeleteAction( self ):
        
        if self._use_simple_delete:
            
            self.ShowDeleteSelectedDialog()
            
        elif self._delete_key_callback is not None:
            
            self._delete_key_callback()
            
        
    
    def SelectDatas( self, datas: typing.Iterable[ object ] ):
        
        for data in datas:
            
            if data in self._data_to_indices:
                
                index = self._data_to_indices[ data ]
                
                self.topLevelItem( index ).setSelected( True )
                
            
        
    
    def SetData( self, datas: typing.Iterable[ object ] ):
        
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
        
        self.columnListContentsChanged.emit()
        
    
    def ShowDeleteSelectedDialog( self ):
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.Accepted:
            
            self.DeleteSelected()
            
        
    
    def _GetRowHeightEstimate( self ):
        
        if self.topLevelItemCount() > 0:
            
            height = self.rowHeight( self.indexFromItem( self.topLevelItem( 0 ) ) )
            
        else:
            
            ( width_gumpf, height ) = ClientGUIFunctions.ConvertTextToPixels( self, ( 20, 1 ) )
            
        
        return height
        
    
    def minimumSizeHint( self ):
        
        width = 0
        
        for i in range( self.columnCount() - 1 ):
            
            width += self.columnWidth( i )
            
        
        width += self._min_section_width # the last column
        
        width += self.frameWidth() * 2
        
        if self._forced_height_num_chars is None:
            
            min_num_rows = 4
            
        else:
            
            min_num_rows = self._forced_height_num_chars
            
        
        header_size = self.header().sizeHint() # this is better than min size hint for some reason ?( 69, 69 )?
        
        data_area_height = self._GetRowHeightEstimate() * min_num_rows
        
        PADDING = 10
        
        min_size_hint = QC.QSize( width, header_size.height() + data_area_height + PADDING )
        
        return min_size_hint
        
    
    def resizeEvent( self, event ):
        
        self._DoStatusChanged()
        
        return QW.QTreeWidget.resizeEvent( self, event )
        
    
    def sizeHint( self ):
        
        width = 0
        
        width += self.frameWidth() * 2
        
        # all but last column
        
        for i in range( self.columnCount() - 1 ):
            
            width += self.columnWidth( i )
            
        
        #
        
        # ok, we are going full slippery dippery doo now
        # the issue is: when we first boot up, we want to give a 'hey, it would be nice' size of the last actual recorded final column
        # HOWEVER, after that: we want to use the current size of the last column
        # so, if it is the first couple of seconds, lmao. after that, oaml
        # I later updated this to use the columnWidth, rather than hickery dickery text-to-pixel-width, since it was juddering resize around text width phase
        
        last_column_type = self._column_list_status.GetColumnTypes()[-1]
        
        if HydrusData.TimeHasPassed( self._creation_time + 2 ):
            
            width += self.columnWidth( self.columnCount() - 1 )
            
            # this is a hack to stop the thing suddenly growing to screen width in a weird resize loop
            # I couldn't reproduce this error, so I assume it is a QSS or whatever font/style/scrollbar on some systems that caused inaccurate columnWidth result
            width = min( width, self.width() )
            
        else:
            
            last_column_chars = self._original_column_list_status.GetColumnWidth( last_column_type )
            
            main_tlw = HG.client_controller.GetMainTLW()
            
            width += ClientGUIFunctions.ConvertTextToPixelWidth( main_tlw, last_column_chars )
            
        
        #
        
        if self._forced_height_num_chars is None:
            
            num_rows = self._initial_height_num_chars
            
        else:
            
            num_rows = self._forced_height_num_chars
            
        
        header_size = self.header().sizeHint()
        
        data_area_height = self._GetRowHeightEstimate() * num_rows
        
        PADDING = 10
        
        size_hint = QC.QSize( width, header_size.height() + data_area_height + PADDING )
        
        return size_hint
        
    
    def Sort( self, sort_column_type = None, sort_asc = None ):
        
        if sort_column_type is not None:
            
            self._sort_column_type = sort_column_type
            
        
        if sort_asc is not None:
            
            self._sort_asc = sort_asc
            
        
        self._SortAndRefreshRows()
        
        self.columnListContentsChanged.emit()
        
        self._DoStatusChanged()
        
    
    def UpdateDatas( self, datas: typing.Optional[ typing.Iterable[ object ] ] = None ):
        
        if datas is None:
            
            # keep it sorted here, which is sometimes useful
            
            indices_and_datas = sorted( ( ( index, data ) for ( data, index ) in self._data_to_indices.items() ) )
            
            datas = [ data for ( index, data ) in indices_and_datas ]
            
        
        sort_data_has_changed = False
        sort_index = self._column_list_status.GetColumnIndexFromType( self._sort_column_type )
        
        for data in datas:
            
            ( display_tuple, sort_tuple ) = self._GetDisplayAndSortTuples( data )
            
            data_info = ( data, display_tuple, sort_tuple )
            
            index = self._data_to_indices[ data ]
            
            existing_data_info = self._indices_to_data_info[ index ]
            
            if data_info != existing_data_info:
                
                if not sort_data_has_changed:
                    
                    ( existing_data, existing_display_tuple, existing_sort_tuple ) = existing_data_info
                    
                    if existing_sort_tuple is not None and sort_tuple is not None:
                        
                        # this does not govern secondary sorts, but let's not spam sorts m8
                        if sort_tuple[ sort_index ] != existing_sort_tuple[ sort_index ]:
                            
                            sort_data_has_changed = True
                            
                        
                    
                
                self._indices_to_data_info[ index ] = data_info
                
                self._UpdateRow( index, display_tuple )
                
            
        
        self.columnListContentsChanged.emit()
        
        return sort_data_has_changed
    

    def SetNonDupeName( self, obj: object ):

        current_names = { o.GetName() for o in self.GetData() if o is not obj }

        HydrusSerialisable.SetNonDupeName( obj, current_names )
        
    
    def ReplaceData( self, old_data: object, new_data: object ):
        
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
        
        QP.AddToLayout( self._buttonbox, button, CC.FLAGS_CENTER_PERPENDICULAR )
        
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
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        try:
            
            defaults_to_add = ClientGUIDialogsQuick.SelectMultipleFromList( self, 'select the defaults to add', choice_tuples )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
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
            
        
    
    def _ExportToJSON( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            with QP.FileDialog( self, 'select where to save the json file', default_filename = 'export.json', wildcard = 'JSON (*.json)', acceptMode = QW.QFileDialog.AcceptSave, fileMode = QW.QFileDialog.AnyFile ) as f_dlg:
                
                if f_dlg.exec() == QW.QDialog.Accepted:
                    
                    path = f_dlg.GetPath()
                    
                    if os.path.exists( path ):
                        
                        from hydrus.client.gui import ClientGUIDialogsQuick
                        
                        message = 'The path "{}" already exists! Ok to overwrite?'.format( path )
                        
                        result = ClientGUIDialogsQuick.GetYesNo( self, message )
                        
                        if result != QW.QDialog.Accepted:
                            
                            return
                            
                        
                    
                    with open( path, 'w', encoding = 'utf-8' ) as f:
                        
                        f.write( json )
                        
                    
                
            
        
    
    def _ExportToPNG( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            from hydrus.client.gui import ClientGUITopLevelWindowsPanels
            from hydrus.client.gui import ClientGUISerialisable
            
            with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export to png' ) as dlg:
                
                panel = ClientGUISerialisable.PNGExportPanel( dlg, export_object )
                
                dlg.SetPanel( panel )
                
                dlg.exec()
                
            
        
    
    def _ExportToPNGs( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is None:
            
            return
            
        
        if not isinstance( export_object, HydrusSerialisable.SerialisableList ):
            
            self._ExportToPNG()
            
            return
            
        
        from hydrus.client.gui import ClientGUITopLevelWindowsPanels
        from hydrus.client.gui import ClientGUISerialisable
        
        with ClientGUITopLevelWindowsPanels.DialogNullipotent( self, 'export to pngs' ) as dlg:
            
            panel = ClientGUISerialisable.PNGsExportPanel( dlg, export_object )
            
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
        
        if HG.client_controller.ClipboardHasImage():
            
            try:
                
                qt_image = HG.client_controller.GetClipboardImage()
                
            except:
                
                # no image on clipboard obviously
                do_text = True
                
            
            try:
                
                payload = ClientSerialisable.LoadFromQtImage( qt_image )
                
                obj = HydrusSerialisable.CreateFromNetworkBytes( payload, raise_error_on_future_version = True )
                
            except HydrusExceptions.SerialisationException as e:
                
                QW.QMessageBox.critical( self, 'Problem loading', 'Problem loading that object: {}'.format( str( e ) ) )
                
                return
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard: {}'.format( str( e ) ) )
                
                return
                
            
        else:
            
            try:
                
                raw_text = HG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( raw_text, raise_error_on_future_version = True )
                
            except HydrusExceptions.SerialisationException as e:
                
                QW.QMessageBox.critical( self, 'Problem loading', 'Problem loading that object: {}'.format( str( e ) ) )
                
                return
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Error', 'I could not understand what was in the clipboard: {}'.format( str( e ) ) )
                
                return
                
            
        
        try:
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            QW.QMessageBox.critical( self, 'Error', 'Problem importing: {}'.format( str( e ) ) )
            
        
        self._listctrl.Sort()
        
    
    def _ImportFromJSON( self ):
        
        with QP.FileDialog( self, 'select the json or jsons with the serialised data', acceptMode = QW.QFileDialog.AcceptOpen, fileMode = QW.QFileDialog.ExistingFiles, wildcard = 'JSON (*.json)|*.json' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                paths = dlg.GetPaths()
                
                self._ImportJSONs( paths )
                
            
        
        self._listctrl.Sort()
        
    
    def _ImportFromPNG( self ):
        
        with QP.FileDialog( self, 'select the png or pngs with the encoded data', acceptMode = QW.QFileDialog.AcceptOpen, fileMode = QW.QFileDialog.ExistingFiles, wildcard = 'PNG (*.png)|*.png' ) as dlg:
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                paths = dlg.GetPaths()
                
                self._ImportPNGs( paths )
                
            
        
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
            
        
    
    def _ImportJSONs( self, paths ):
        
        have_shown_load_error = False
        
        for path in paths:
            
            try:
                
                with open( path, 'r', encoding = 'utf-8' ) as f:
                    
                    payload = f.read()
                    
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( payload, raise_error_on_future_version = True )
                
                self._ImportObject( obj )
                
            except HydrusExceptions.SerialisationException as e:
                
                if not have_shown_load_error:
                    
                    message = str( e )
                    
                    if len( paths ) > 1:
                        
                        message += os.linesep * 2
                        message += 'If there are more objects in this import with similar load problems, they will now be skipped silently.'
                        
                    
                    QW.QMessageBox.critical( self, 'Problem loading', str( e ) )
                    
                    have_shown_load_error = True
                    
                
            except:
                
                QW.QMessageBox.critical( self, 'Error', 'I could not understand what was encoded in "{}"!'.format( path ) )
                
                return
                
            
        
    
    def _ImportPNGs( self, paths ):
        
        have_shown_load_error = False
        
        for path in paths:
            
            try:
                
                payload = ClientSerialisable.LoadFromPNG( path )
                
            except Exception as e:
                
                QW.QMessageBox.critical( self, 'Error', str(e) )
                
                return
                
            
            try:
                
                obj = HydrusSerialisable.CreateFromNetworkBytes( payload, raise_error_on_future_version = True )
                
                self._ImportObject( obj )
                
            except HydrusExceptions.SerialisationException as e:
                
                if not have_shown_load_error:
                    
                    message = str( e )
                    
                    if len( paths ) > 1:
                        
                        message += os.linesep * 2
                        message += 'If there are more objects in this import with similar load problems, they will now be skipped silently.'
                        
                    
                    QW.QMessageBox.critical( self, 'Problem loading', str( e ) )
                    
                    have_shown_load_error = True
                    
                
            except:
                
                QW.QMessageBox.critical( self, 'Error', 'I could not understand what was encoded in "{}"!'.format( path ) )
                
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
        export_menu_items.append( ( 'normal', 'to json file', 'Serialise the selected data and export to a json file.', self._ExportToJSON ) )
        export_menu_items.append( ( 'normal', 'to png file', 'Serialise the selected data and encode it to an image file you can easily share with other hydrus users.', self._ExportToPNG ) )
        
        if self._custom_get_callable is None:
            
            all_objs_are_named = False not in ( issubclass( o, HydrusSerialisable.SerialisableBaseNamed ) for o in self._permitted_object_types )
            
            if all_objs_are_named:
                
                export_menu_items.append( ( 'normal', 'to pngs', 'Serialise the selected data and encode it to multiple image files you can easily share with other hydrus users.', self._ExportToPNGs ) )
                
            
        
        import_menu_items = []
        
        import_menu_items.append( ( 'normal', 'from clipboard', 'Load a data from text in your clipboard.', self._ImportFromClipboard ) )
        import_menu_items.append( ( 'normal', 'from json files', 'Load a data from .json files.', self._ImportFromJSON ) )
        import_menu_items.append( ( 'normal', 'from png files (you can also drag and drop pngs onto this list)', 'Load a data from an encoded png.', self._ImportFromPNG ) )
        
        self.AddMenuButton( 'export', export_menu_items, enabled_only_on_selection = True )
        self.AddMenuButton( 'import', import_menu_items )
        self.AddButton( 'duplicate', self._Duplicate, enabled_only_on_selection = True )
        
        self.setAcceptDrops( True )
        self.installEventFilter( ClientGUIDragDrop.FileDropTarget( self, filenames_callable = self.ImportFromDragDrop ) )
        
    
    def AddMenuButton( self, label, menu_items, enabled_only_on_selection = False, enabled_check_func = None ):
        
        button = ClientGUIMenuButton.MenuButton( self, label, menu_items )
        
        self._AddButton( button, enabled_only_on_selection = enabled_only_on_selection, enabled_check_func = enabled_check_func )
        
        self._UpdateButtons()
        
    
    def AddSeparator( self ):
        
        self._buttonbox.addSpacing( 12 )
        
    
    def AddWindow( self, window ):
        
        QP.AddToLayout( self._buttonbox, window, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def EventContentChanged( self, parent, first, last ):
        
        if not self._listctrl:
            
            return
            
        
        self._UpdateButtons()
        
    
    def EventSelectionChanged( self ):
        
        if not self._listctrl:
            
            return
            
        
        self._UpdateButtons()
        
    
    def ImportFromDragDrop( self, paths ):
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        message = 'Try to import the {} dropped files to this list? I am expecting json or png files.'.format( HydrusData.ToHumanInt( len( paths ) ) )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            ( jsons, pngs ) = HydrusData.PartitionIteratorIntoLists( lambda path: path.endswith( '.png' ), paths )
            
            self._ImportPNGs( pngs )
            self._ImportJSONs( jsons )
            
            self._listctrl.Sort()
            
        
    
    def NewButtonRow( self ):
        
        self._buttonbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._vbox, self._buttonbox, CC.FLAGS_ON_RIGHT )
        
    
    def SetListCtrl( self, listctrl ):
        
        self._listctrl = listctrl
        
        QP.AddToLayout( self._vbox, self._listctrl, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( self._vbox, self._buttonbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( self._vbox )
        
        self._listctrl.itemSelectionChanged.connect( self.EventSelectionChanged )
        
        self._listctrl.model().rowsInserted.connect( self.EventContentChanged )
        self._listctrl.model().rowsRemoved.connect( self.EventContentChanged )
        
    
    def UpdateButtons( self ):
        
        self._UpdateButtons()
        
