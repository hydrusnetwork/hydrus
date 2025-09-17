import collections.abc
import os
import typing

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusText
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientSerialisable
from hydrus.client.gui import ClientGUIDragDrop
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
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
    

# note that this AbstractItemModel can support nested folder stuff, with some work. we'd prob want to move to a data storage system that actuall was a tree, rather than this indices-to-data stuff
class HydrusListItemModel( QC.QAbstractItemModel ):
    
    def __init__( self, parent: QW.QWidget, column_list_type: int, data_to_display_tuple_func: collections.abc.Callable, data_to_sort_tuple_func: collections.abc.Callable, column_types_to_name_overrides = None ):
        
        super().__init__( parent )
        
        if column_types_to_name_overrides is None:
            
            column_types_to_name_overrides = {}
            
        
        # an obvious extention here is to no longer use tuples for the main data/sort/display storage stuff, but dicts that do column_type->data, and then we can do dynamic column hiding and stuff and just do dict lookups
        
        self._column_list_type = column_list_type
        self._column_list_status: ClientGUIListStatus.ColumnListStatus = CG.client_controller.column_list_manager.GetStatus( self._column_list_type )
        
        self._column_types_to_name_overrides = column_types_to_name_overrides
        
        self._data_to_display_tuple_func = data_to_display_tuple_func
        self._data_to_sort_tuple_func = data_to_sort_tuple_func
        
        self._indices_to_data = {}
        self._data_to_indices = {}
        self._data_to_display_tuples = {}
        self._data_to_sort_tuples = {}
        
        self._sort_column_type = 0
        
    
    def _ConvertCurrentColumnIntToColumnType( self, column: int ) -> int:
        
        # if and when this guy supports column hiding and rearranging, it'll all, fingers crossed, just work with minimal extra finagling
        # yo actually it seems TreeView does columnHidden gubbins by itself, so the answer here is just to do a ton of testing
        
        return self._column_list_status.GetColumnTypeFromIndex( column )
        
    
    def _RecalculateIndicesAfterDelete( self ):
        
        data_sorted = sorted( self._indices_to_data.items() )
        
        self._indices_to_data = {}
        self._data_to_indices = {}
        
        for ( index, ( old_index, data ) ) in enumerate( data_sorted ):
            
            self._data_to_indices[ data ] = index
            self._indices_to_data[ index ] = data
            
        
    
    def AddDatas( self, datas ):
        
        insert_index = len( self._indices_to_data )
        
        self.beginInsertRows( QC.QModelIndex(), insert_index, insert_index + ( len( datas ) - 1 ) )
        
        for data in datas:
            
            if data in self._data_to_indices:
                
                continue
                
            
            self._indices_to_data[ insert_index ] = data
            self._data_to_indices[ data ] = insert_index
            
            insert_index += 1
            
        
        self.endInsertRows()
        
    
    def columnCount( self, parent = QC.QModelIndex() ):
        
        return self._column_list_status.GetColumnCount()
        
    
    def data( self, index: QC.QModelIndex, role = QC.Qt.ItemDataRole.DisplayRole ):
        
        if not index.isValid():
            
            return None
            
        
        if role in ( QC.Qt.ItemDataRole.DisplayRole, QC.Qt.ItemDataRole.ToolTipRole ):
            
            column_type = self._ConvertCurrentColumnIntToColumnType( index.column() )
            
            data = self._indices_to_data[ index.row() ]
            
            if data not in self._data_to_display_tuples:
                
                display_tuple = self._data_to_display_tuple_func( data )
                
                display_tuple = tuple( ( HydrusText.GetFirstLineSummary( t ) for t in display_tuple ) )
                
                self._data_to_display_tuples[ data ] = display_tuple
                
            
            column_logical_position = CGLC.column_list_column_type_logical_position_lookup[ self._column_list_type ][ column_type ]
            
            text = self._data_to_display_tuples[ data ][ column_logical_position ]
            
            # TODO: might be nice to maintain an optional tooltip dict for when the getfirstlinesummary differs, so we can tooltip the whole contents
            if role == QC.Qt.ItemDataRole.ToolTipRole:
                
                return ClientGUIFunctions.WrapToolTip( text )
                
            else:
                
                return text
                
            
            
        elif role == QC.Qt.ItemDataRole.UserRole:
            
            return self._indices_to_data[ index.row() ] # same data no matter the column in this system!
            
        
        return None
        
    
    def DeleteDatas( self, deletee_datas ):
        
        deletee_indices = [ self._data_to_indices[ data ] for data in deletee_datas ]
        
        if len( deletee_indices ) == 0:
            
            return
            
        
        start = min( deletee_indices )
        end = max( deletee_indices )
        
        self.beginRemoveRows( QC.QModelIndex(), start, end )
        
        for data in deletee_datas:
            
            if data in self._data_to_indices:
                
                del self._data_to_indices[ data ]
                
            
            if data in self._data_to_sort_tuples:
                
                del self._data_to_sort_tuples[ data ]
                
            
            if data in self._data_to_display_tuples:
                
                del self._data_to_display_tuples[ data ]
                
            
        
        for index in deletee_indices:
            
            del self._indices_to_data[ index ]
            
        
        self._RecalculateIndicesAfterDelete()
        
        self.endRemoveRows()
        
    
    def flags( self, index: QC.QModelIndex ):
        
        if not index.isValid():
            
            return QC.Qt.ItemFlag.NoItemFlags
            
        
        return QC.Qt.ItemFlag.ItemIsEnabled | QC.Qt.ItemFlag.ItemIsSelectable | QC.Qt.ItemFlag.ItemNeverHasChildren
        
    
    def GetColumnListType( self ) -> int:
        
        return self._column_list_type
        
    
    def GetData( self, indices: typing.Optional[ collections.abc.Collection[ int ] ] = None ):
        
        if indices is None:
            
            return [ data for ( index, data ) in sorted( self._indices_to_data.items() ) ]
            
        else:
            
            return [ self._indices_to_data[ index ] for index in indices if index in self._indices_to_data ]
            
        
    
    def GetEarliestData( self, datas ):
        
        if len( datas ) == 0:
            
            return None
            
        
        matching_tuples = sorted( ( ( self._data_to_indices[ data ], data ) for data in datas if data in self._data_to_indices ) )
        
        if len( matching_tuples ) == 0:
            
            return None
            
        
        return matching_tuples[0][1]
        
    def GetModelIndexFromData( self, data: object ):
        
        if data in self._data_to_indices:
            
            index = self._data_to_indices[ data ]
            
            return self.createIndex( index, 0 )
            
        else:
            
            return QC.QModelIndex()
            
        
    
    def HasData( self, data: object ):
        
        return data in self._data_to_indices
        
    
    def headerData( self, section: int, orientation: QC.Qt.Orientation, role = QC.Qt.ItemDataRole.DisplayRole ):
        
        if orientation != QC.Qt.Orientation.Horizontal:
            
            return None
            
        
        column_type = self._ConvertCurrentColumnIntToColumnType( section )
        
        if role in ( QC.Qt.ItemDataRole.DisplayRole, QC.Qt.ItemDataRole.ToolTipRole ):
            
            if column_type in self._column_types_to_name_overrides:
                
                name = self._column_types_to_name_overrides[ column_type ]
                
            else:
                
                name = CGLC.column_list_column_name_lookup[ self._column_list_type ][ column_type ]
                
            
            return name
            
        elif role == QC.Qt.ItemDataRole.UserRole:
            
            return column_type
            
        else:
            
            return super().headerData( section, orientation, role = role )
            
        
    
    def index( self, row: int, column: int, parent = QC.QModelIndex() ):
        
        if not self.hasIndex( row, column, parent ):
            
            return QC.QModelIndex()
            
        
        # WOOP WOOP, TWO MAN-HOURS DIED HERE
        # do not return self.createIndex( row, column, parent ), it causes the >0 columns to not repaint or respond to mouse clicks
        # I guess somehow the default parent here was like the 0, 0 index or -1, -1 or something crazy since I'm not setting up a root 'properly' or something
        # anyway it broke the whole thing. just doing row, column fixes the selection and repaint issues
        return self.createIndex( row, column )
        
    
    def parent( self, index = QC.QModelIndex() ):
        
        # if we want clever nested stuff, we'll implement this, using stuff like QAbstractItemModel.createIndex
        # otherwise everything is top layer flat list, so no extra dimension
        return QC.QModelIndex()
        
    
    def rowCount( self, parent = QC.QModelIndex() ):
        
        return len( self._indices_to_data )
        
    
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
            
        
    
    def sort( self, column_logical_position: int, order: QC.Qt.SortOrder = QC.Qt.SortOrder.AscendingOrder ):
        
        self.layoutAboutToBeChanged.emit()
        
        # TODO: OK, so I understand we can upgrade this and extend to allowing filter behaviour by inserting a QSortFilterProxyModel
        # that dude would handle sort, which I guess means it would do the data_to_sort_tuples stuff too, and would do so by overriding a 'lessThan' method in a subclass
        # it would also allow quick filtering
        # note, important, however, that you need to be careful in the view or whatever to do mapFromSource and mapToSource when handling indices since they'll jump around via the proxy's sort/filtering
        
        self._sort_column_type = self.headerData( column_logical_position, QC.Qt.Orientation.Horizontal, QC.Qt.ItemDataRole.UserRole )
        
        asc = order == QC.Qt.SortOrder.AscendingOrder
        
        # anything with busted None sort data gets appended to the end
        no_sort_data_magic_reverso_index_failure = 1 if asc else -1
        
        def master_sort_key( data ):
            
            if data not in self._data_to_sort_tuples:
                
                sort_tuple = HydrusLists.ConvertTupleOfDatasToCasefolded( self._data_to_sort_tuple_func( data ) )
                
                self._data_to_sort_tuples[ data ] = sort_tuple
                
            
            sort_tuple = self._data_to_sort_tuples[ data ]
            
            if sort_tuple is None:
                
                return ( no_sort_data_magic_reverso_index_failure, tuple(), tuple() )
                
            else:
                
                # TODO: when we do hidden/rearranged columns, there will be a question on how to arrange the fallback here. I guess a frozen tuple according to the current order, if that isn't too CPU crazy
                # or just the first column_logical_position or two!
                return ( 0, sort_tuple[ column_logical_position ], sort_tuple )
                
            
        
        try:
            
            datas_sorted = sorted( self._data_to_indices.keys(), key = master_sort_key, reverse = not asc )
            
        except Exception as e:
            
            datas_sorted = list( self._data_to_indices.keys() )
            
            HydrusData.ShowText( 'A multi-column list failed to sort! Please send hydrus dev the traceback!' )
            HydrusData.ShowException( e )
            
        
        self._indices_to_data = { index : data for ( index, data ) in enumerate( datas_sorted ) }
        self._data_to_indices = { data : index for ( index, data ) in enumerate( datas_sorted ) }
        
        self.layoutChanged.emit()
        
    
    def ReplaceDatas( self, replacement_tuples ):
        
        for ( old_data, new_data ) in replacement_tuples:
            
            index = self._data_to_indices[ old_data ]
            
            del self._data_to_indices[ old_data ]
            
            self._data_to_indices[ new_data ] = index
            self._indices_to_data[ index ] = new_data
            
        
        new_datas = [ new_data for ( old_data, new_data ) in replacement_tuples ]
        
        # tell the View the display strings have updated
        self.UpdateDatas( new_datas )
        
    
    def UpdateDatas( self, datas, check_for_changed_sort_data = False ):
        
        sort_data_has_changed = False
        
        if len( datas ) == 0:
            
            return sort_data_has_changed 
            
        
        try:
            
            existing_sort_logical_index = CGLC.column_list_column_type_logical_position_lookup[ self._column_list_type ][ self._sort_column_type ]
            
        except:
            
            existing_sort_logical_index = 0
            
        
        for data in datas:
            
            index = self._data_to_indices[ data ]
            
            existing_data = self._indices_to_data[ index ]
            
            # catching an object that __eq__ with another but is actually a different lad--we want to swap the new one in
            the_data_is_actually_a_different_object = data is not existing_data
            
            if the_data_is_actually_a_different_object:
                
                # in this careful case, there's an optimisation that doesn't update to new 'is' object when __eq__ True wew
                del self._data_to_indices[ data ]
                
                self._data_to_indices[ data ] = index
                self._indices_to_data[ index ] = data
                
            
            if data in self._data_to_display_tuples:
                
                del self._data_to_display_tuples[ data ]
                
            
            if check_for_changed_sort_data and not sort_data_has_changed:
                
                if data in self._data_to_sort_tuples:
                    
                    existing_sort_tuple = self._data_to_sort_tuples[ data ]
                    
                    new_sort_tuple = HydrusLists.ConvertTupleOfDatasToCasefolded( self._data_to_sort_tuple_func( data ) )
                    
                    if existing_sort_tuple[ existing_sort_logical_index ] != new_sort_tuple[ existing_sort_logical_index ]:
                        
                        sort_data_has_changed = True
                        
                    
                    self._data_to_sort_tuples[ data ] = new_sort_tuple
                    
                else:
                    
                    sort_data_has_changed = True
                    
                
            else:
                
                if data in self._data_to_sort_tuples:
                    
                    del self._data_to_sort_tuples[ data ]
                    
                
            
            top_left = self.index( index, 0 )
            bottom_right = self.index( index, self.columnCount() - 1 )
            
            self.dataChanged.emit( top_left, bottom_right, [ QC.Qt.ItemDataRole.DisplayRole, QC.Qt.ItemDataRole.ToolTipRole ] )
            
        
        return sort_data_has_changed
        
    

class BetterListCtrlTreeView( QW.QTreeView ):
    
    columnListContentsChanged = QC.Signal()
    
    def __init__( self, parent, height_num_chars, model: HydrusListItemModel, use_simple_delete = False, delete_key_callback = None, can_delete_callback = None, activation_callback = None, column_types_to_name_overrides = None ):
        
        super().__init__( parent )
        
        self._have_shown_a_column_data_error = False
        
        self._creation_time = HydrusTime.GetNow()
        
        self._column_list_type = model.GetColumnListType()
        
        self._column_list_status: ClientGUIListStatus.ColumnListStatus = CG.client_controller.column_list_manager.GetStatus( self._column_list_type )
        self._original_column_list_status = self._column_list_status
        
        self._temp_selected_data_record = []
        
        self.setUniformRowHeights( True )
        self.setAlternatingRowColors( True )
        self.setSortingEnabled( True )
        self.setSelectionMode( QW.QAbstractItemView.SelectionMode.ExtendedSelection )
        self.setSelectionBehavior( QW.QAbstractItemView.SelectionBehavior.SelectRows )
        self.setRootIsDecorated( False )
        self.setEditTriggers( QW.QAbstractItemView.EditTrigger.NoEditTriggers )
        
        self._initial_height_num_chars = height_num_chars
        self._forced_height_num_chars = None
        
        self._has_initialised_size = False
        
        self._use_simple_delete = use_simple_delete
        self._has_done_deletes = False
        self._can_delete_callback = can_delete_callback
        
        self._copy_rows_callable = None
        
        self._rows_menu_callable = None
        
        # DO NOT REARRANGE BRO
        # This sets header data, so we can now do header-section-sizing gubbins
        self.setModel( model )
        
        main_tlw = CG.client_controller.GetMainTLW()
        
        # Note: now (2024-08) we moved to TreeView, I have no idea what the status of this stuff is
        # if last section is set too low, for instance 3, the column seems unable to ever shrink from initial (expanded to fill space) size
        #  _    _  ___  _    _    __     __   ___  
        # ( \/\/ )(  _)( \/\/ )  (  )   (  ) (   \ 
        #  \    /  ) _) \    /    )(__  /__\  ) ) )
        #   \/\/  (___)  \/\/    (____)(_)(_)(___/ 
        #
        # I think this is because of mismatch between set size and min size! So ensuring we never set smaller than that initially should fix this???!?
        
        MIN_SECTION_SIZE_CHARS = 3
        
        self._min_section_width = ClientGUIFunctions.ConvertTextToPixelWidth( main_tlw, MIN_SECTION_SIZE_CHARS )
        
        self.header().setMinimumSectionSize( self._min_section_width )
        
        last_column_index = self._column_list_status.GetColumnCount() - 1
        
        self.header().setStretchLastSection( True )
        
        for ( i, column_type ) in enumerate( self._column_list_status.GetColumnTypes() ):
            
            if i == last_column_index:
                
                width_chars = MIN_SECTION_SIZE_CHARS
                
            else:
                
                width_chars = self._column_list_status.GetColumnWidth( column_type )
                
            
            width_chars = max( width_chars, MIN_SECTION_SIZE_CHARS )
            
            # ok this is a pain in the neck issue, but fontmetrics changes after widget init. I guess font gets styled on top afterwards
            # this means that if I use this window's fontmetrics here, in init, then it is different later on, and we get creeping growing columns lmao
            # several other places in the client are likely affected in different ways by this also!
            width_pixels = ClientGUIFunctions.ConvertTextToPixelWidth( main_tlw, width_chars )
            
            self.setColumnWidth( i, width_pixels )
            
        
        self._delete_key_callback = delete_key_callback
        self._activation_callback = activation_callback
        
        self.Sort()
        
        self.header().setSectionsMovable( False ) # can only turn this on when we move from data/sort tuples
        # self.header().setFirstSectionMovable( True ) # same
        self.header().setSectionsClickable( True )
        
        #self.header().sectionMoved.connect( self._DoStatusChanged ) # same
        self.header().sectionResized.connect( self._SectionsResized )
        
        self.model().layoutAboutToBeChanged.connect( self._PreserveSelectionStore )
        self.model().rowsAboutToBeInserted.connect( self._PreserveSelectionStore )
        self.model().rowsAboutToBeRemoved.connect( self._PreserveSelectionStore )
        self.model().layoutChanged.connect( self._PreserveSelectionRestoreFromSort )
        self.model().rowsInserted.connect( self._PreserveSelectionRestore )
        self.model().rowsRemoved.connect( self._PreserveSelectionRestore )
        
        self.header().setContextMenuPolicy( QC.Qt.ContextMenuPolicy.CustomContextMenu )
        self.header().customContextMenuRequested.connect( self._ShowHeaderMenu )
        
        CG.client_controller.CallAfterQtSafe( self, 'initialising multi-column list widths', self._InitialiseColumnWidths )
        
        CG.client_controller.sub( self, 'NotifySettingsUpdated', 'reset_all_listctrl_status' )
        CG.client_controller.sub( self, 'NotifySettingsUpdated', 'reset_listctrl_status' )
        
    
    def _InitialiseColumnWidths( self ):
        
        MIN_SECTION_SIZE_CHARS = 3
        
        main_tlw = CG.client_controller.GetMainTLW()
        
        last_column_index = self._column_list_status.GetColumnCount() - 1
        
        for ( i, column_type ) in enumerate( self._column_list_status.GetColumnTypes() ):
            
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
            
        
        self._has_initialised_size = True
        
    
    def _DoStatusChanged( self ):
        
        self._column_list_status = self._GenerateCurrentStatus()
        
        CG.client_controller.column_list_manager.SaveStatus( self._column_list_status )
        
    
    def _GenerateCurrentStatus( self ) -> ClientGUIListStatus.ColumnListStatus:
        
        status = ClientGUIListStatus.ColumnListStatus()
        
        status.SetColumnListType( self._column_list_type )
        
        main_tlw = CG.client_controller.GetMainTLW()
        
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
            
            column_type = self.model().headerData( logical_index, QC.Qt.Orientation.Horizontal, QC.Qt.ItemDataRole.UserRole )
            
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
        
        sort_column = self.header().sortIndicatorSection()
        order = self.header().sortIndicatorOrder()
        
        sort_column_type = status.GetColumnTypeFromIndex( sort_column )
        sort_asc = order == QC.Qt.SortOrder.AscendingOrder
        
        status.SetSort( sort_column_type, sort_asc )
        
        return status
        
    
    def _GetRowHeightEstimate( self ):
        
        if self.model().rowCount() > 0:
            
            height = self.sizeHintForRow( 0 )
            
            # this straight-up returns 0 during dialog init wew, I guess when I ask during init the text isn't initialised or whatever
            '''
            model_index = self.model().index( 0 )
            
            height = self.rowHeight( model_index )
            '''
        else:
            
            ( width_gumpf, height ) = ClientGUIFunctions.ConvertTextToPixels( self, ( 20, 1 ) )
            
        
        return height
        
    
    def _GetSelectedIndicesIterator( self ) -> typing.Iterator[ int ]:
        
        # selectedRows() is quite expensive, so let's peer into the underlying gubbins
        
        selection = self.selectionModel().selection()
        
        selected_row_ranges = []
        
        # this guy is iterable (it is a subclass of QList), trust me linterbros
        for selection_range in selection:
            
            typing.cast( QC.QItemSelectionRange, selection_range )
            
            selected_row_ranges.append( ( selection_range.top(), selection_range.bottom() + 1 ) )
            
        
        # we are assuming no overlapping ranges because we are in rowSelection mode!
        
        selected_row_ranges.sort()
        
        selected_rows_iterator = ( row_index for row_indices in ( range( top, bottom ) for ( top, bottom ) in selected_row_ranges ) for row_index in row_indices )
        
        return selected_rows_iterator
        
    
    def _PreserveSelectionRestore( self ):
        
        self.SelectDatas( self._temp_selected_data_record, deselect_others = True )
        
        self._temp_selected_data_record = []
        
    
    def _PreserveSelectionRestoreFromSort( self ):
        
        self._PreserveSelectionRestore()
        
        # save that a sort just happened
        self._DoStatusChanged()
        
    
    def _PreserveSelectionStore( self ):
        
        self._temp_selected_data_record = self.GetData( only_selected = True )
        
    
    def _SectionsResized( self, logical_index, old_size, new_size ):
        
        if self._has_initialised_size:
            
            self._DoStatusChanged()
            
            self.updateGeometry()
            
        
    
    def _ShowHeaderMenu( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        name = CGLC.column_list_type_name_lookup[ self._column_list_type ]
        
        ClientGUIMenus.AppendMenuItem( menu, f'reset default column widths for "{name}" lists', 'Reset the column widths and other display settings for all lists of this type', CG.client_controller.column_list_manager.ResetToDefaults, self._column_list_type )
        
        CGC.core().PopupMenu( self, menu )
        
    
    def _ShowRowsMenu( self ):
        
        if self._rows_menu_callable is None:
            
            return
            
        
        try:
            
            menu = self._rows_menu_callable()
            
        except HydrusExceptions.DataMissing:
            
            return
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def AddData( self, data: object, select_sort_and_scroll = False ):
        
        self.AddDatas( ( data, ), select_sort_and_scroll = select_sort_and_scroll )
        
    
    def AddDatas( self, datas: collections.abc.Iterable[ object ], select_sort_and_scroll = False ):
        
        datas = list( datas )
        
        if len( datas ) == 0:
            
            return
            
        
        datas = QP.ListsToTuples( datas )
        
        self.model().AddDatas( datas )
        
        if select_sort_and_scroll:
            
            self.SelectDatas( datas, deselect_others = True )
            
            self.Sort()
            
            first_data = self.model().GetEarliestData( datas )
            
            self.ScrollToData( first_data )
            
        
        self.columnListContentsChanged.emit()
        
    
    def AddRowsMenuCallable( self, menu_callable ):
        
        self._rows_menu_callable = menu_callable
        
        self.setContextMenuPolicy( QC.Qt.ContextMenuPolicy.CustomContextMenu )
        self.customContextMenuRequested.connect( self.EventShowMenu )
        
    
    def DeleteDatas( self, deletee_datas: collections.abc.Iterable[ object ] ):
        
        deletee_datas = [ QP.ListsToTuples( data ) for data in deletee_datas ]
        
        self.model().DeleteDatas( deletee_datas )
        
        self.columnListContentsChanged.emit()
        
        self._has_done_deletes = True
        
    
    def DeleteSelected( self ):
        
        deletee_datas = self.GetData( only_selected = True )
        
        self.DeleteDatas( deletee_datas )
        
    
    def keyPressEvent( self, event: QG.QKeyEvent ):
        
        ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
        
        event_processed = False
        
        if key in ClientGUIShortcuts.DELETE_KEYS_QT:
            
            self.ProcessDeleteAction()
            
            event_processed = True
            
        elif key in ( QC.Qt.Key.Key_Enter, QC.Qt.Key.Key_Return ):
            
            self.ProcessActivateAction()
            
            event_processed = True
            
        elif key in ( ord( 'A' ), ord( 'a' ) ) and modifier == QC.Qt.KeyboardModifier.ControlModifier:
            
            self.selectAll()
            
            event_processed = True
            
        elif ClientGUIShortcuts.KeyPressEventIsACopy( event ):
            
            if self._copy_rows_callable is not None:
                
                copyable_texts = self._copy_rows_callable()
                
                if len( copyable_texts ) > 0:
                    
                    CG.client_controller.pub( 'clipboard', 'text', '\n'.join( copyable_texts ) )
                    
                    event_processed = True
                    
                
            
        
        if event_processed:
            
            event.accept()
            
        else:
            
            QW.QTreeView.keyPressEvent( self, event )
            
        
    
    def EventShowMenu( self ):
        
        CG.client_controller.CallAfterQtSafe( self, 'list menu show', self._ShowRowsMenu )
        
    
    def ForceHeight( self, rows ):
        
        # TODO: Rework this. I use this guy to do the gallery/watcher auto-grow, but really I think sizeHint would handle it better via an internal bounding range
        # with presumably an 'updateGeometry()' call when we recognise we have a diff number of rows
        
        self._forced_height_num_chars = rows
        
        self.updateGeometry()
        
        # +2 for the header row and * 1.25 for magic rough text-to-rowheight conversion
        
        #existing_min_width = self.minimumWidth()
        
        #( width_gumpf, ideal_client_height ) = ClientGUIFunctions.ConvertTextToPixels( self, ( 20, int( ( ideal_rows + 2 ) * 1.25 ) ) )
        
        #QP.SetMinClientSize( self, ( existing_min_width, ideal_client_height ) )
        
    
    def count( self ):
        
        return self.model().rowCount()
        
    
    def GetData( self, only_selected = False ) -> list:
        
        if only_selected:
            
            indices = list( self._GetSelectedIndicesIterator() )
            
            return self.model().GetData( indices = indices )
            
        else:
            
            return self.model().GetData()
            
        
    
    def GetTopSelectedData( self ) -> typing.Optional[ typing.Any ]:
        
        indices_iter = self._GetSelectedIndicesIterator()
        
        try:
            
            top_index = next( indices_iter )
            
            result = self.model().GetData( ( top_index, ) )
            
            if len( result ) > 0:
                
                return result[ 0 ]
                
            
        except StopIteration:
            
            return None
            
        
        return None
        
    
    def HasData( self, data: object ):
        
        data = QP.ListsToTuples( data )
        
        return self.model().HasData( data )
        
    
    def HasDoneDeletes( self ):
        
        return self._has_done_deletes
        
    
    def HasOneSelected( self ):
        
        rows_seen = set()
        
        indices_iter = self._GetSelectedIndicesIterator()
        
        for index in indices_iter:
            
            rows_seen.add( index )
            
            if len( rows_seen ) > 1:
                
                break
                
            
        
        return len( rows_seen ) == 1
        
    
    def HasSelected( self ):
        
        return self.selectionModel().hasSelection()
        
    
    def minimumSizeHint( self ):
        
        width = 0
        
        for i in range( self.model().columnCount() - 1 ):
            
            width += self.columnWidth( i )
            
        
        width += self._min_section_width # the last column
        
        FRAMEWIDTH_PADDING = self.frameWidth() * 2
        
        width += FRAMEWIDTH_PADDING
        
        if self._forced_height_num_chars is None:
            
            num_rows = 4
            
        else:
            
            num_rows = self._forced_height_num_chars
            
        
        data_area_height = self._GetRowHeightEstimate() * num_rows
        
        PADDING = self.header().sizeHint().height() + FRAMEWIDTH_PADDING
        
        if self.horizontalScrollBar().isVisible():
            
            PADDING + self.horizontalScrollBar().height()
            
        
        min_size_hint = QC.QSize( width, data_area_height + PADDING )
        
        return min_size_hint
        
    
    def model( self ) -> HydrusListItemModel:
        
        return typing.cast( HydrusListItemModel, super().model() )
        
    
    def mouseDoubleClickEvent( self, event: QG.QMouseEvent ):
        
        if event.button() == QC.Qt.MouseButton.LeftButton:
            
            index = self.indexAt(event.pos())  # Get the index of the item clicked
            
            if index.isValid():
                
                self.ProcessActivateAction()
                
                event.accept()
                
                return
                
            
        
        QW.QTreeView.mouseDoubleClickEvent( self, event )
        
    
    def NotifySettingsUpdated( self, column_list_type = None ):
        
        if column_list_type is not None and column_list_type != self._column_list_type:
            
            return
            
        
        self.blockSignals( True )
        self.header().blockSignals( True )
        
        self._column_list_status: ClientGUIListStatus.ColumnListStatus = CG.client_controller.column_list_manager.GetStatus( self._column_list_type )
        self._original_column_list_status = self._column_list_status
        
        #
        
        main_tlw = CG.client_controller.GetMainTLW()
        
        MIN_SECTION_SIZE_CHARS = 3
        
        last_column_index = self._column_list_status.GetColumnCount() - 1
        
        for ( i, column_type ) in enumerate( self._column_list_status.GetColumnTypes() ):
            
            if i == last_column_index:
                
                width_chars = MIN_SECTION_SIZE_CHARS
                
            else:
                
                width_chars = self._column_list_status.GetColumnWidth( column_type )
                
            
            width_chars = max( width_chars, MIN_SECTION_SIZE_CHARS )
            
            width_pixels = ClientGUIFunctions.ConvertTextToPixelWidth( main_tlw, width_chars )
            
            self.setColumnWidth( i, width_pixels )
            
        
        self.header().blockSignals( False )
        self.blockSignals( False )
        
        #
        
        self.Sort() # note this saves the current status, so don't do it until we resize stuff
        
    
    def ProcessActivateAction( self ):
        
        if self._activation_callback is not None:
            
            try:
                
                self._activation_callback()
                
            except Exception as e:
                
                HydrusData.ShowException( e )
                
            
        
    
    def ProcessDeleteAction( self ):
        
        if self._can_delete_callback is not None:
            
            if not self._can_delete_callback():
                
                return
                
            
        
        if self._use_simple_delete:
            
            self.ShowDeleteSelectedDialog()
            
        elif self._delete_key_callback is not None:
            
            self._delete_key_callback()
            
        
    
    def ReplaceData( self, old_data: object, new_data: object, sort_and_scroll = False ):
        
        self.ReplaceDatas( [ ( old_data, new_data ) ], sort_and_scroll = sort_and_scroll )
        
    
    def ReplaceDatas( self, replacement_tuples, sort_and_scroll = False ):
        
        if len( replacement_tuples ) == 0:
            
            return
            
        
        replacement_tuples = [ ( QP.ListsToTuples( old_data ), QP.ListsToTuples( new_data ) ) for ( old_data, new_data ) in replacement_tuples ]
        
        self.model().ReplaceDatas( replacement_tuples )
        
        if sort_and_scroll:
            
            self.Sort()
            
            first_new_data = self.model().GetEarliestData( [ new_data for ( old_data, new_data ) in replacement_tuples ] )
            
            self.ScrollToData( first_new_data )
            
        
        self.columnListContentsChanged.emit()
        
    
    def resizeEvent( self, event ):
        
        result = QW.QTreeView.resizeEvent( self, event )
        
        # do not touch this! weird hack that fixed a new bug in 6.6.1 where all columns would reset on load to 100px wide!
        if self._has_initialised_size:
            
            self._DoStatusChanged()
            
        
        return result
        
    
    def sizeHint( self ):
        
        width = 0
        
        FRAMEWIDTH_PADDING = self.frameWidth() * 2
        
        width += FRAMEWIDTH_PADDING
        
        # all but last column
        
        for i in range( self.model().columnCount() - 1 ):
            
            width += self.columnWidth( i )
            
        
        #
        
        # ok, we are going full slippery dippery doo now
        # the issue is: when we first boot up, we want to give a 'hey, it would be nice' size of the last actual recorded final column
        # HOWEVER, after that: we want to use the current size of the last column
        # so, if it is the first couple of seconds, lmao. after that, oaml
        # I later updated this to use the columnWidth, rather than hickery dickery text-to-pixel-width, since it was juddering resize around text width phase
        
        last_column_type = self._column_list_status.GetColumnTypes()[-1]
        
        if HydrusTime.TimeHasPassed( self._creation_time + 2 ):
            
            width += self.columnWidth( self.model().columnCount() - 1 )
            
            # this is a hack to stop the thing suddenly growing to screen width in a weird resize loop
            # I couldn't reproduce this error, so I assume it is a QSS or whatever font/style/scrollbar on some systems that caused inaccurate columnWidth result
            width = min( width, self.width() )
            
        else:
            
            last_column_chars = self._original_column_list_status.GetColumnWidth( last_column_type )
            
            main_tlw = CG.client_controller.GetMainTLW()
            
            width += ClientGUIFunctions.ConvertTextToPixelWidth( main_tlw, last_column_chars )
            
        
        #
        
        if self._forced_height_num_chars is None:
            
            num_rows = self._initial_height_num_chars
            
        else:
            
            num_rows = self._forced_height_num_chars
            
        
        data_area_height = self._GetRowHeightEstimate() * num_rows
        
        PADDING = self.header().sizeHint().height() + FRAMEWIDTH_PADDING
        
        if self.horizontalScrollBar().isVisible():
            
            PADDING + self.horizontalScrollBar().height()
            
        
        size_hint = QC.QSize( width, data_area_height + PADDING )
        
        return size_hint
        
    
    def ScrollToData( self, data: object, do_focus = True ):
        
        data = QP.ListsToTuples( data )
        
        model_index = self.model().GetModelIndexFromData( data )
        
        if model_index.isValid():
            
            self.scrollTo( model_index, hint = QW.QAbstractItemView.ScrollHint.PositionAtCenter )
            
            if do_focus:
                
                self.setFocus( QC.Qt.FocusReason.OtherFocusReason )
                
            
        
    
    def SelectDatas( self, datas: collections.abc.Iterable[ object ], deselect_others = False ):
        
        selectee_datas = { QP.ListsToTuples( data ) for data in datas }
        
        current_selection = self.GetData( only_selected = True )
        
        model = self.model()
        selection_model = self.selectionModel()
        
        if deselect_others:
            
            deselectee_datas = set( current_selection ).difference( selectee_datas )
            
            if len( deselectee_datas ) > 0:
                
                selection = QC.QItemSelection()
                
                for data in deselectee_datas:
                    
                    model_index = model.GetModelIndexFromData( data )
                    
                    selection.select( model_index, model_index )
                    
                
                selection_model.select( selection, QC.QItemSelectionModel.SelectionFlag.Deselect | QC.QItemSelectionModel.SelectionFlag.Rows )
                
            
        
        selectee_datas.difference_update( current_selection )
        
        if len( selectee_datas ) > 0:
            
            selection = QC.QItemSelection()
            
            for data in selectee_datas:
                
                model_index = model.GetModelIndexFromData( data )
                
                selection.select( model_index, model_index )
                
            
            selection_model.select( selection, QC.QItemSelectionModel.SelectionFlag.Select | QC.QItemSelectionModel.SelectionFlag.Rows )
            
            data = model.GetEarliestData( selectee_datas )
            
            model_index = model.GetModelIndexFromData( data )
            
            selection_model.setCurrentIndex( model_index, QC.QItemSelectionModel.SelectionFlag.Current )
            
        
    
    def SetCopyRowsCallable( self, copy_rows_callable ):
        
        self._copy_rows_callable = copy_rows_callable
        
    
    def SetData( self, datas: collections.abc.Iterable[ object ] ):
        
        datas = [ QP.ListsToTuples( data ) for data in datas ]
        
        self.model().SetData( datas )
        
        self.Sort()
        
        self.columnListContentsChanged.emit()
        
    
    def SetNonDupeName( self, obj: object, do_casefold = False ):
        
        current_names = { o.GetName() for o in self.GetData() if o is not obj }

        HydrusSerialisable.SetNonDupeName( obj, current_names, do_casefold = do_casefold )
        
    
    def ShowDeleteSelectedDialog( self ):
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        result = ClientGUIDialogsQuick.GetYesNo( self, 'Remove all selected?' )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            self.DeleteSelected()
            
        
    
    def Sort( self, sort_column_type = None, sort_asc = None ):
        
        try:
            
            ( default_sort_column_type, default_sort_asc ) = self._column_list_status.GetSort()
            
            if sort_column_type is None:
                
                sort_column_type = default_sort_column_type
                
            
            if sort_asc is None:
                
                sort_asc = default_sort_asc
                
            
            # TODO: this may want to be column_list_column_type_logical_position_lookup rather than the status lookup, depending on how we implement column order memory
            # or it may simply need to navigate that question carefully if we have multiple lists open with different orders or whatever
            column = self._column_list_status.GetColumnIndexFromType( sort_column_type )
            ord = QC.Qt.SortOrder.AscendingOrder if sort_asc else QC.Qt.SortOrder.DescendingOrder
            
            # do not call model().sort directly, it does not update the header arrow gubbins
            self.sortByColumn( column, ord )
            
        except Exception as e:
            
            HydrusData.ShowText( 'An attempt to sort a multi-column list failed! Error follows:' )
            
            HydrusData.ShowException( e )
            
        
    
    def UpdateDatas( self, datas: typing.Optional[ collections.abc.Iterable[ object ] ] = None, check_for_changed_sort_data = False ):
        
        if datas is not None:
            
            datas = [ QP.ListsToTuples( data ) for data in datas ]
            
        else:
            
            datas = self.GetData()
            
        
        if len( datas ) == 0:
            
            return False
            
        
        sort_data_has_changed = self.model().UpdateDatas( datas, check_for_changed_sort_data = check_for_changed_sort_data )
        
        self.columnListContentsChanged.emit()
        
        return sort_data_has_changed
        
    

class BetterListCtrlPanel( QW.QWidget ):
    
    def __init__( self, parent ):
        
        super().__init__( parent )
        
        self._vbox = QP.VBoxLayout()
        
        self._buttonbox = QP.HBoxLayout()
        
        self._listctrl: typing.Optional[ BetterListCtrlTreeView ] = None
        
        self._permitted_object_types = []
        self._import_add_callable = lambda x: None
        self._custom_get_callable = None
        
        self._button_infos = []
        
    
    def _AddAllDefaults( self, defaults_callable, add_callable ):
        
        defaults = defaults_callable()
        
        if len( defaults ) == 0:
            
            return
            
        
        for default in defaults:
            
            add_callable( default )
            
        
        # try it, it might not work, if what is actually added differs, but it may!
        self._listctrl.SelectDatas( defaults )
        self._listctrl.Sort()
        self._listctrl.ScrollToData( list( defaults )[0] )
        
    
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
            
        
        if len( defaults_to_add ) == 0:
            
            return
            
        
        for default in defaults_to_add:
            
            add_callable( default )
            
        
        # try it, it might not work, if what is actually added differs, but it may!
        self._listctrl.SelectDatas( defaults_to_add )
        self._listctrl.Sort()
        self._listctrl.ScrollToData( list( defaults_to_add )[0] )
        
    
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
            
            CG.client_controller.pub( 'clipboard', 'text', json )
            
        
    
    def _ExportToJSON( self ):
        
        export_object = self._GetExportObject()
        
        if export_object is not None:
            
            json = export_object.DumpToString()
            
            with QP.FileDialog( self, 'select where to save the json file', default_filename = 'export.json', wildcard = 'JSON (*.json)', acceptMode = QW.QFileDialog.AcceptMode.AcceptSave, fileMode = QW.QFileDialog.FileMode.AnyFile ) as f_dlg:
                
                if f_dlg.exec() == QW.QDialog.DialogCode.Accepted:
                    
                    path = f_dlg.GetPath()
                    
                    if os.path.exists( path ):
                        
                        from hydrus.client.gui import ClientGUIDialogsQuick
                        
                        message = 'The path "{}" already exists! Ok to overwrite?'.format( path )
                        
                        result = ClientGUIDialogsQuick.GetYesNo( self, message )
                        
                        if result != QW.QDialog.DialogCode.Accepted:
                            
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
            
        
    
    def _GetExportObject( self ) -> typing.Optional[ HydrusSerialisable.SerialisableBase ]:
        
        to_export = HydrusSerialisable.SerialisableList()
        
        if self._custom_get_callable is None:
            
            for obj in self._listctrl.GetData( only_selected = True ):
                
                to_export.append( obj )
                
            
        else:
            
            to_export.append( self._custom_get_callable() )
            
        
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
        
        if CG.client_controller.ClipboardHasImage():
            
            try:
                
                qt_image = CG.client_controller.GetClipboardImage()
                
            except Exception as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading!', f'Problem loading from clipboard: {e}' )
                
                return
                
            
            try:
                
                payload = ClientSerialisable.LoadFromQtImage( qt_image )
                
                obj = HydrusSerialisable.CreateFromNetworkBytes( payload, raise_error_on_future_version = True )
                
            except HydrusExceptions.SerialisationException as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading!', f'Problem loading that object: {e}' )
                
                return
                
            except Exception as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading!', f'I could not understand what was in the clipboard: {e}' )
                
                return
                
            
            # TODO: add a thing here that checks for local paths and eats up PNG or JSON files depending obviously on file content
            
        else:
            
            try:
                
                raw_text = CG.client_controller.GetClipboardText()
                
            except HydrusExceptions.DataMissing as e:
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
                
                return
                
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( raw_text, raise_error_on_future_version = True )
                
            except Exception as e:
                
                ClientGUIDialogsQuick.PresentClipboardParseError( self, raw_text, 'JSON-serialised Hydrus Object(s)', e )
                
                return
                
            
        
        try:
            
            self._ImportObject( obj )
            
        except Exception as e:
            
            ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str( e ) )
            
        
        self._listctrl.Sort()
        
    
    def _ImportFromJSON( self ):
        
        with QP.FileDialog( self, 'select the json or jsons with the serialised data', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen, fileMode = QW.QFileDialog.FileMode.ExistingFiles, wildcard = 'JSON (*.json)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                paths = dlg.GetPaths()
                
                self._ImportJSONs( paths )
                
            
        
        self._listctrl.Sort()
        
    
    def _ImportFromPNG( self ):
        
        with QP.FileDialog( self, 'select the png or pngs with the encoded data', acceptMode = QW.QFileDialog.AcceptMode.AcceptOpen, fileMode = QW.QFileDialog.FileMode.ExistingFiles, wildcard = 'PNG (*.png)' ) as dlg:
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                paths = dlg.GetPaths()
                
                self._ImportPNGs( paths )
                
            
        
        self._listctrl.Sort()
        
    
    def _ImportObject( self, obj, can_present_messages = True ):
        
        bad_object_type_names = set()
        objects_added = []
        
        if isinstance( obj, HydrusSerialisable.SerialisableList ):
            
            for sub_obj in obj:
                
                ( sub_objects_added, sub_bad_object_type_names ) = self._ImportObject( sub_obj, can_present_messages = False )
                
                objects_added.extend( sub_objects_added )
                bad_object_type_names.update( sub_bad_object_type_names )
                
            
        else:
            
            if isinstance( obj, self._permitted_object_types ):
                
                self._import_add_callable( obj )
                
                objects_added.append( obj )
                
            else:
                
                bad_object_type_names.add( HydrusData.GetTypeName( type( obj ) ) )
                
            
        
        if can_present_messages and len( bad_object_type_names ) > 0:
            
            message = 'The imported objects included these types:'
            message += '\n' * 2
            message += '\n'.join( bad_object_type_names )
            message += '\n' * 2
            message += 'Whereas this control only allows:'
            message += '\n' * 2
            message += '\n'.join( ( HydrusData.GetTypeName( o ) for o in self._permitted_object_types ) )
            
            ClientGUIDialogsMessage.ShowWarning( self, message )
            
        
        num_added = len( objects_added )
        
        if can_present_messages and num_added > 0:
            
            message = '{} objects added!'.format( HydrusNumbers.ToHumanInt( num_added ) )
            
            ClientGUIDialogsMessage.ShowInformation( self, message )
            
            self._listctrl.SelectDatas( objects_added )
            self._listctrl.Sort()
            self._listctrl.ScrollToData( objects_added[0] )
            
        
        return ( objects_added, bad_object_type_names )
        
    
    def _ImportJSONs( self, paths ):
        
        have_shown_load_error = False
        
        for path in paths:
            
            try:
                
                with open( path, 'r', encoding = 'utf-8' ) as f:
                    
                    payload = f.read()
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem loading!', str(e) )
                
                return
                
            
            try:
                
                obj = HydrusSerialisable.CreateFromString( payload, raise_error_on_future_version = True )
                
                self._ImportObject( obj )
                
            except HydrusExceptions.SerialisationException as e:
                
                HydrusData.PrintException( e )
                
                if not have_shown_load_error:
                    
                    message = str( e )
                    
                    if len( paths ) > 1:
                        
                        message += '\n' * 2
                        message += 'If there are more objects in this import with similar load problems, they will now be skipped silently.'
                        
                    
                    ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str( e ) )
                    
                    have_shown_load_error = True
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', f'I could not understand what was encoded in "{path}"!' )
                
                return
                
            
        
    
    def _ImportPNGs( self, paths ):
        
        have_shown_load_error = False
        
        for path in paths:
            
            try:
                
                payload = ClientSerialisable.LoadFromPNG( path )
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str(e) )
                
                return
                
            
            try:
                
                obj = HydrusSerialisable.CreateFromNetworkBytes( payload, raise_error_on_future_version = True )
                
                self._ImportObject( obj )
                
            except HydrusExceptions.SerialisationException as e:
                
                HydrusData.PrintException( e )
                
                if not have_shown_load_error:
                    
                    message = str( e )
                    
                    if len( paths ) > 1:
                        
                        message += '\n' * 2
                        message += 'If there are more objects in this import with similar load problems, they will now be skipped silently.'
                        
                    
                    ClientGUIDialogsMessage.ShowCritical( self, 'Problem importing!', str( e ) )
                    
                    have_shown_load_error = True
                    
                
            except Exception as e:
                
                HydrusData.PrintException( e )
                
                ClientGUIDialogsMessage.ShowCritical( self, 'Error', 'I could not understand what was encoded in "{path}"!' )
                
                return
                
            
        
    
    def _UpdateButtons( self ):
        
        for ( button, enabled_check_func ) in self._button_infos:
            
            if enabled_check_func():
                
                button.setEnabled( True )
                
            else:
                
                button.setEnabled( False )
                
            
        
    
    def AddIconButton( self, icon: QG.QIcon, clicked_func, tooltip = None, enabled_only_on_selection = False, enabled_only_on_single_selection = False, enabled_check_func = None ):
        
        button = ClientGUICommon.IconButton( self, icon, clicked_func )
        
        if tooltip is not None:
            
            button.setToolTip( ClientGUIFunctions.WrapToolTip( tooltip ) )
            
        
        self._AddButton( button, enabled_only_on_selection = enabled_only_on_selection, enabled_only_on_single_selection = enabled_only_on_single_selection, enabled_check_func = enabled_check_func )
        
        self._UpdateButtons()
        
    
    def AddButton( self, label, clicked_func, enabled_only_on_selection = False, enabled_only_on_single_selection = False, enabled_check_func = None, tooltip = None ):
        
        button = ClientGUICommon.BetterButton( self, label, clicked_func )
        
        if tooltip is not None:
            
            button.setToolTip( ClientGUIFunctions.WrapToolTip( tooltip ) )
            
        
        self._AddButton( button, enabled_only_on_selection = enabled_only_on_selection, enabled_only_on_single_selection = enabled_only_on_single_selection, enabled_check_func = enabled_check_func )
        
        self._UpdateButtons()
        
        return button
        
    
    def AddDefaultsButton( self, defaults_callable, add_callable ):
        
        import_menu_template_items = []
        
        all_call = HydrusData.Call( self._AddAllDefaults, defaults_callable, add_callable )
        some_call = HydrusData.Call( self._AddSomeDefaults, defaults_callable, add_callable )
        
        import_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'add them all', 'Load all the defaults.', all_call ) )
        import_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'select from a list', 'Load some of the defaults.', some_call ) )
        
        self.AddMenuButton( 'add defaults', import_menu_template_items )
        
    
    def AddDeleteButton( self, enabled_check_func = None ):
        
        if enabled_check_func is None:
            
            enabled_only_on_selection = True
            
        else:
            
            enabled_only_on_selection = False
            
        
        self.AddButton( 'delete', self._listctrl.ProcessDeleteAction, enabled_check_func = enabled_check_func, enabled_only_on_selection = enabled_only_on_selection )
        
    
    def AddImportExportButtons( self, permitted_object_types, import_add_callable, custom_get_callable = None, and_duplicate_button = True ):
        
        self._permitted_object_types = permitted_object_types
        self._import_add_callable = import_add_callable
        self._custom_get_callable = custom_get_callable
        
        export_menu_template_items = []
        
        export_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to clipboard', 'Serialise the selected data and put it on your clipboard.', self._ExportToClipboard ) )
        export_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to json file', 'Serialise the selected data and export to a json file.', self._ExportToJSON ) )
        export_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to png file', 'Serialise the selected data and encode it to an image file you can easily share with other hydrus users.', self._ExportToPNG ) )
        
        if self._custom_get_callable is None:
            
            all_objs_are_named = False not in ( issubclass( o, HydrusSerialisable.SerialisableBaseNamed ) for o in self._permitted_object_types )
            
            if all_objs_are_named:
                
                export_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'to pngs', 'Serialise the selected data and encode it to multiple image files you can easily share with other hydrus users.', self._ExportToPNGs ) )
                
            
        
        import_menu_template_items = []
        
        import_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from clipboard', 'Load a data from text in your clipboard.', self._ImportFromClipboard ) )
        import_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from json files', 'Load a data from .json files.', self._ImportFromJSON ) )
        import_menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'from png files (you can also drag and drop pngs onto this list)', 'Load a data from an encoded png.', self._ImportFromPNG ) )
        
        self.AddMenuButton( 'export', export_menu_template_items, enabled_only_on_selection = True )
        self.AddMenuButton( 'import', import_menu_template_items )
        
        if and_duplicate_button:
            
            self.AddButton( 'duplicate', self._Duplicate, enabled_only_on_selection = True )
            
        
        self.setAcceptDrops( True )
        self.installEventFilter( ClientGUIDragDrop.FileDropTarget( self, filenames_callable = self.ImportFromDragDrop ) )
        
    
    def AddMenuButton( self, label, menu_template_items: list[ ClientGUIMenuButton.MenuTemplateItem ], enabled_only_on_selection = False, enabled_check_func = None ):
        
        button = ClientGUIMenuButton.MenuButton( self, label, menu_template_items )
        
        self._AddButton( button, enabled_only_on_selection = enabled_only_on_selection, enabled_check_func = enabled_check_func )
        
        self._UpdateButtons()
        
    
    def AddMenuIconButton( self, icon: QG.QIcon, tooltip: str, menu_template_items: list[ ClientGUIMenuButton.MenuTemplateItem ], enabled_only_on_selection = False, enabled_check_func = None ):
        
        button = ClientGUIMenuButton.MenuIconButton( self, icon, menu_template_items )
        
        button.setToolTip( ClientGUIFunctions.WrapToolTip( tooltip ) )
        
        self._AddButton( button, enabled_only_on_selection = enabled_only_on_selection, enabled_check_func = enabled_check_func )
        
        self._UpdateButtons()
        
    
    def AddSeparator( self, pixels = 12 ):
        
        self._buttonbox.addSpacing( pixels )
        
    
    def AddWindow( self, window ):
        
        QP.AddToLayout( self._buttonbox, window, CC.FLAGS_CENTER_PERPENDICULAR )
        
    
    def ImportFromDragDrop( self, paths ):
        
        from hydrus.client.gui import ClientGUIDialogsQuick
        
        message = 'Try to import the {} dropped files to this list? I am expecting json or png files.'.format( HydrusNumbers.ToHumanInt( len( paths ) ) )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            ( jsons, pngs ) = HydrusLists.PartitionIteratorIntoLists( lambda path: path.endswith( '.png' ), paths )
            
            self._ImportPNGs( pngs )
            self._ImportJSONs( jsons )
            
            self._listctrl.Sort()
            
        
    
    def NewButtonRow( self ):
        
        self._buttonbox = QP.HBoxLayout()
        
        QP.AddToLayout( self._vbox, self._buttonbox, CC.FLAGS_ON_RIGHT )
        
    
    def SetListCtrl( self, listctrl: BetterListCtrlTreeView ):
        
        self._listctrl = listctrl
        
        QP.AddToLayout( self._vbox, self._listctrl, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        QP.AddToLayout( self._vbox, self._buttonbox, CC.FLAGS_ON_RIGHT )
        
        self.setLayout( self._vbox )
        
        self._listctrl.selectionModel().selectionChanged.connect( self.UpdateButtons )
        
        self._listctrl.model().rowsInserted.connect( self.UpdateButtons )
        self._listctrl.model().rowsRemoved.connect( self.UpdateButtons )
        
        self._listctrl.columnListContentsChanged.connect( self.UpdateButtons )
        
    
    def UpdateButtons( self ):
        
        if not self._listctrl:
            
            return
            
        
        try:
            
            self._UpdateButtons()
            
        except Exception as e:
            
            HydrusData.ShowException( e )
            
        
    
