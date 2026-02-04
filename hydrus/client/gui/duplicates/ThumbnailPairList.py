import typing

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusTime

from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientRendering
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.media import ClientMediaResult

class ThumbnailPairListModel( QC.QAbstractTableModel ):
    
    def __init__( self ):
        
        super().__init__( None )
        
        self._data_rows = []
        
        self._media_results_to_thumbnail_pixmaps = {}
        self._media_results_being_loaded = set()
        
    
    def rowCount(self, parent = QC.QModelIndex() ):
        
        return len( self._data_rows )
        
    
    def columnCount(self, parent = QC.QModelIndex() ):
        
        raise NotImplemented()
        
    
    def data( self, index: QC.QModelIndex, role: QC.Qt.ItemDataRole.DisplayRole ):
        
        if not index.isValid():
            
            return None
            
        
        row = index.row()
        col = index.column()
        
        if role == QC.Qt.ItemDataRole.DecorationRole and col <= 1:
            
            media_result = self._data_rows[ row ][ col ]
            
            if media_result in self._media_results_to_thumbnail_pixmaps:
                
                return self._media_results_to_thumbnail_pixmaps[ media_result ]
                
            else:
                
                self._LoadMediaResultThumbnailPixmap( index, media_result )
                
            
        
        return None
        
    
    def _LoadMediaResultThumbnailPixmap( self, index: QC.QModelIndex, media_result: ClientMediaResult.MediaResult ):
        
        if media_result in self._media_results_being_loaded:
            
            return
            
        
        self._media_results_being_loaded.add( media_result )
        
        def work_callable():
            
            thumbnail_hydrus_bmp = CG.client_controller.thumbnails_cache.GetThumbnail( media_result )
            
            return thumbnail_hydrus_bmp
            
        
        def publish_callable( thumbnail_hydrus_bmp: ClientRendering.HydrusBitmap ):
            
            pixmap = thumbnail_hydrus_bmp.GetQtPixmap()
            
            self._media_results_to_thumbnail_pixmaps[ media_result ] = pixmap
            
            row = index.row()
            col = index.column()
            
            try:
                
                current_media_result_at_this_position = self._data_rows[ row ][ col ]
                
                if current_media_result_at_this_position != media_result:
                    
                    raise Exception()
                    
                
            except Exception as e:
                
                return
                
            
            self.dataChanged.emit( index, index, [ QC.Qt.ItemDataRole.DecorationRole ] )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def AppendData( self, data_row ):
        
        self.AppendDatas( ( data_row, ) )
        
    
    def AppendDatas( self, data_rows ):
        
        row = self.rowCount()
        
        self.beginInsertRows( QC.QModelIndex(), row, row + ( len( data_rows ) - 1 ) )
        
        self._data_rows.extend( data_rows )
        
        self.endInsertRows()
        
    
    def GetMediaResultPairsStartingAtIndex( self, row: int ):
        
        # wraparound list fetch
        
        we_hit_our_index = False
        second_half = []
        first_half = []
        
        for ( i, r ) in enumerate( self._data_rows ):
            
            if i == row:
                
                we_hit_our_index = True
                
            
            media_result_pair = ( r[0], r[1] )
            
            if we_hit_our_index:
                
                first_half.append( media_result_pair )
                
            else:
                
                second_half.append( media_result_pair )
                
            
        
        result = first_half + second_half
        
        return result
        
    
    def GetMediaResultPair( self, row: int ):
        
        r = self._data_rows[ row ]
        
        return ( r[0], r[1] )
        
    
    def SetData( self, data_rows ):
        
        self.beginResetModel()
        self._data_rows = data_rows
        self.endResetModel()
        
    

class ThumbnailPairListModelJustThumbs( ThumbnailPairListModel ):
    
    def columnCount(self, parent = QC.QModelIndex() ):
        
        return 2
        
    

class ThumbnailPairListModelPendingAutoResolutionAction( ThumbnailPairListModel ):
    
    def __init__( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, do_either_way_test: bool ):
        
        super().__init__()
        
        self._rule = rule
        self._do_either_way_test = do_either_way_test
        
        self._pairs_to_third_column_info = {}
        self._pairs_we_are_calculating = set()
        
    
    def columnCount(self, parent = QC.QModelIndex() ):
        
        return 3
        
    
    def data( self, index: QC.QModelIndex, role: QC.Qt.ItemDataRole.DisplayRole ):
        
        if not index.isValid():
            
            return None
            
        
        row = index.row()
        col = index.column()
        
        if role in ( QC.Qt.ItemDataRole.DisplayRole, QC.Qt.ItemDataRole.ToolTipRole ):
            
            if col == 2:
                
                pair = self.GetMediaResultPair( row )
                
                if pair in self._pairs_to_third_column_info:
                    
                    return self._pairs_to_third_column_info[ pair ]
                    
                else:
                    
                    self._EnsureWeAreCalculatingInfo( index, pair )
                    
                    return f'calculating{HC.UNICODE_ELLIPSIS}'
                    
                
            
        
        return super().data( index, role )
        
    
    def headerData( self, section: int, orientation: QC.Qt.Orientation, role = QC.Qt.ItemDataRole.DisplayRole ):
        
        if orientation == QC.Qt.Orientation.Horizontal and role == QC.Qt.ItemDataRole.DisplayRole:
            
            if section == 0:
                
                return 'A'
                
            elif section == 1:
                
                return 'B'
                
            else:
                
                return 'action'
                
            
        else:
            
            return super().headerData( section, orientation, role = role )
            
        
    
    def _EnsureWeAreCalculatingInfo( self, index: QC.QModelIndex, pair ):
        
        if pair in self._pairs_we_are_calculating:
            
            return
            
        
        self._pairs_we_are_calculating.add( pair )
        
        def work_callable():
            
            summary_string = rule.GetActionSummaryOnMatchingPair( media_result_a, media_result_b, do_either_way_test = do_either_way_test )
            
            return summary_string
            
        
        def publish_callable( summary_string: str ):
            
            pairs_to_third_column_info[ pair ] = summary_string
            
            self.dataChanged.emit( index, index, [ QC.Qt.ItemDataRole.DisplayRole ] )
            
        
        ( media_result_a, media_result_b ) = pair
        rule = self._rule
        do_either_way_test = self._do_either_way_test
        pairs_to_third_column_info = self._pairs_to_third_column_info
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def SetRule( self, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        if rule.DumpToString() != self._rule.DumpToString():
            
            self._rule = rule
            
            self._pairs_to_third_column_info = {}
            self._pairs_we_are_calculating = set()
            
            if self.rowCount() > 0:
                
                top_left = self.index( 0, 2 )
                bottom_right = self.index( self.rowCount() - 1, 2 )
                
                self.dataChanged.emit( top_left, bottom_right, [ QC.Qt.ItemDataRole.DisplayRole ] )
                
            
        
    

class ThumbnailPairListModelDeniedAutoResolutionAction( ThumbnailPairListModel ):
    
    def columnCount(self, parent = QC.QModelIndex() ):
        
        return 3
        
    
    def data( self, index: QC.QModelIndex, role: QC.Qt.ItemDataRole.DisplayRole ):
        
        if not index.isValid():
            
            return None
            
        
        row = index.row()
        col = index.column()
        
        if role == QC.Qt.ItemDataRole.DisplayRole:
            
            if col == 2:
                
                timestamp_ms = self._data_rows[ row ][ col ]
                
                timestamp = HydrusTime.SecondiseMS( timestamp_ms )
                
                s = HydrusTime.TimestampToPrettyTime( timestamp )
                s += '\n'
                s += HydrusTime.TimestampToPrettyTimeDelta( timestamp, force_no_iso = True )
                
                return s
                
            
        
        return super().data( index, role )
        
    
    def headerData( self, section: int, orientation: QC.Qt.Orientation, role = QC.Qt.ItemDataRole.DisplayRole ):
        
        if orientation == QC.Qt.Orientation.Horizontal and role == QC.Qt.ItemDataRole.DisplayRole:
            
            if section == 0:
                
                return '1'
                
            elif section == 1:
                
                return '2'
                
            else:
                
                return 'time'
                
            
        else:
            
            return super().headerData( section, orientation, role = role )
            
        
    

class ThumbnailPairListModelTakenAutoResolutionAction( ThumbnailPairListModel ):
    
    def columnCount(self, parent = QC.QModelIndex() ):
        
        return 3
        
    
    def data( self, index: QC.QModelIndex, role: QC.Qt.ItemDataRole.DisplayRole ):
        
        if not index.isValid():
            
            return None
            
        
        row = index.row()
        col = index.column()
        
        if role == QC.Qt.ItemDataRole.DisplayRole:
            
            if col == 2:
                
                ( duplicate_type, timestamp_ms ) = self._data_rows[ row ][ col ]
                
                timestamp = HydrusTime.SecondiseMS( timestamp_ms )
                
                s = HC.duplicate_type_auto_resolution_action_description_lookup[ duplicate_type ]
                s += '\n'
                s += HydrusTime.TimestampToPrettyTime( timestamp )
                s += '\n'
                s += HydrusTime.TimestampToPrettyTimeDelta( timestamp, force_no_iso = True )
                
                return s
                
            
        
        return super().data( index, role )
        
    
    def headerData( self, section: int, orientation: QC.Qt.Orientation, role = QC.Qt.ItemDataRole.DisplayRole ):
        
        if orientation == QC.Qt.Orientation.Horizontal and role == QC.Qt.ItemDataRole.DisplayRole:
            
            if section == 0:
                
                return 'A'
                
            elif section == 1:
                
                return 'B'
                
            else:
                
                return 'action'
                
            
        else:
            
            return super().headerData( section, orientation, role = role )
            
        
    

class ThumbnailPairList( QW.QTableView ):
    
    MIN_NUM_ROWS_HEIGHT = 2
    
    def __init__( self, parent, model: ThumbnailPairListModel ):
        
        super().__init__( parent )
        
        self.setModel( model )
        
        self.verticalHeader().setVisible( False )
        
        self.setSelectionBehavior( QW.QAbstractItemView.SelectionBehavior.SelectRows )
        self.setSelectionMode( QW.QAbstractItemView.SelectionMode.SingleSelection )
        
        ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
        
        self.verticalHeader().setDefaultSectionSize( thumbnail_height )
        self.verticalHeader().setSectionResizeMode( QW.QHeaderView.ResizeMode.Fixed )
        
        self.setVerticalScrollMode( QW.QAbstractItemView.ScrollMode.ScrollPerItem )
        self.verticalScrollBar().setSingleStep( 1 )
        
        self.horizontalHeader().setDefaultSectionSize( thumbnail_width )
        
        self.setColumnWidth( 0, thumbnail_width )
        
        column_count = model.columnCount()
        
        for i in range( column_count ):
            
            if i == column_count - 1:
                
                self.horizontalHeader().setSectionResizeMode( i, QW.QHeaderView.ResizeMode.Stretch )
                
            else:
                
                self.horizontalHeader().setSectionResizeMode( i, QW.QHeaderView.ResizeMode.Fixed )
                
            
        
        my_width = thumbnail_width * model.columnCount() + 24
        
        # this was going bonkers dialog sizing for some users
        max_thumbnail_height_for_min_height_calc = min( thumbnail_height, 200 )
        
        self.setMinimumSize( QC.QSize( my_width, max_thumbnail_height_for_min_height_calc * self.MIN_NUM_ROWS_HEIGHT ) )
        
    
    def model( self ) -> ThumbnailPairListModel:
        
        return typing.cast( ThumbnailPairListModel, super().model() )
        
    
    def SetData( self, tuples_of_data ):
        
        self.model().SetData( tuples_of_data )
        
    

class ThumbnailPairListJustThumbs( ThumbnailPairList ):
    
    def __init__( self, parent ):
        
        super().__init__( parent, ThumbnailPairListModelJustThumbs() )
        
        self.horizontalHeader().setVisible( False )
        
    

class ThumbnailPairListPreviewPendingAutoResolutionAction( ThumbnailPairList ):
    
    def __init__( self, parent, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        super().__init__( parent, ThumbnailPairListModelPendingAutoResolutionAction( rule, True ) )
        
    
    def model( self ) -> ThumbnailPairListModelPendingAutoResolutionAction:
        
        return typing.cast( ThumbnailPairListModelPendingAutoResolutionAction, super().model() )
        
    

class ThumbnailPairListReviewPendingPreviewAutoResolutionAction( ThumbnailPairList ):
    
    MIN_NUM_ROWS_HEIGHT = 4
    
    def __init__( self, parent, rule: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ):
        
        super().__init__( parent, ThumbnailPairListModelPendingAutoResolutionAction( rule, False ) )
        
        self.setSelectionMode( QW.QAbstractItemView.SelectionMode.ExtendedSelection )
        
    

class ThumbnailPairListDeniedAutoResolutionAction( ThumbnailPairList ):
    
    MIN_NUM_ROWS_HEIGHT = 4
    
    def __init__( self, parent ):
        
        super().__init__( parent, ThumbnailPairListModelDeniedAutoResolutionAction() )
        
        self.setSelectionMode( QW.QAbstractItemView.SelectionMode.ExtendedSelection )
        
    

class ThumbnailPairListTakenAutoResolutionAction( ThumbnailPairList ):
    
    MIN_NUM_ROWS_HEIGHT = 4
    
    def __init__( self, parent ):
        
        super().__init__( parent, ThumbnailPairListModelTakenAutoResolutionAction() )
        
        self.setSelectionMode( QW.QAbstractItemView.SelectionMode.ExtendedSelection )
        
    

class ListEnterCatcher( QC.QObject ):
    
    def __init__( self, parent, thumbnail_pair_list: ThumbnailPairList ):
        
        self._thumbnail_pair_list = thumbnail_pair_list
        
        super().__init__( parent )
        
        self._thumbnail_pair_list.installEventFilter( self )
        
    
    def eventFilter( self, obj, event ):
        
        # we can't use the normal activated guy since this appears to not stop enter propagation, allowing the dialog to close immediately after lol
        # this signals to stop event propagation
        
        if event.type() == QC.QEvent.Type.KeyPress:
            
            event = typing.cast( QG.QKeyEvent, event )
            
            if event.key() in ( QC.Qt.Key.Key_Return, QC.Qt.Key.Key_Enter ):
                
                current_index = self._thumbnail_pair_list.currentIndex()
                
                if current_index.isValid():
                    
                    self._thumbnail_pair_list.activated.emit( current_index )
                    
                
                return True
                
            
        
        return False
        
    
























































































# if you are reading this, hydev was using a page of empty space for screenshot backing and forgot to delete this
