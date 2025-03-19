import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientRendering
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.widgets import ClientGUICommon
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
            
            thumbnail_hydrus_bmp = CG.client_controller.GetCache( 'thumbnail' ).GetThumbnail( media_result )
            
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
                    
                
            except:
                
                return
                
            
            self.dataChanged.emit( index, index, [ QC.Qt.ItemDataRole.DecorationRole ] )
            
        
        job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        job.start()
        
    
    def SetData( self, data_rows ):
        
        self.beginResetModel()
        self._data_rows = data_rows
        self.endResetModel()
        
    

class ThumbnailPairListModelFails( ThumbnailPairListModel ):
    
    def columnCount(self, parent = QC.QModelIndex() ):
        
        return 2
        
    

class ThumbnailPairListModelPasses( ThumbnailPairListModel ):
    
    def columnCount(self, parent = QC.QModelIndex() ):
        
        return 3
        
    
    def data( self, index: QC.QModelIndex, role: QC.Qt.ItemDataRole.DisplayRole ):
        
        if not index.isValid():
            
            return None
            
        
        row = index.row()
        col = index.column()
        
        if role == QC.Qt.ItemDataRole.DisplayRole:
            
            if col == 2:
                
                fixed_order = self._data_rows[ row ][ col ]
                
                if fixed_order:
                    
                    return 'yes'
                    
                else:
                    
                    return 'no, could be either way'
                    
                
            
        
        return super().data( index, role )
        
    
    def headerData( self, section: int, orientation: QC.Qt.Orientation, role = QC.Qt.ItemDataRole.DisplayRole ):
        
        if orientation == QC.Qt.Orientation.Horizontal and role == QC.Qt.ItemDataRole.DisplayRole:
            
            if section == 0:
                
                return 'A'
                
            elif section == 1:
                
                return 'B'
                
            else:
                
                return 'certain on this order?'
                
            
        else:
            
            return super().headerData( section, orientation, role = role )
            
        
    

class ThumbnailPairList( QW.QTableView ):
    
    def __init__( self, parent, model: ThumbnailPairListModel ):
        
        super().__init__( parent )
        
        self.setModel( model )
        
        self.verticalHeader().setVisible( False )
        
        self.setSelectionBehavior( QW.QAbstractItemView.SelectionBehavior.SelectRows )
        self.setSelectionMode( QW.QAbstractItemView.SelectionMode.SingleSelection )
        
        ( thumbnail_width, thumbnail_height ) = HC.options[ 'thumbnail_dimensions' ]
        
        self.verticalHeader().setDefaultSectionSize( thumbnail_height )
        self.verticalHeader().setSectionResizeMode( QW.QHeaderView.ResizeMode.Fixed )
        
        self.horizontalHeader().setDefaultSectionSize( thumbnail_width )
        
        self.setColumnWidth( 0, thumbnail_width )
        
        column_count = model.columnCount()
        
        for i in range( column_count ):
            
            if i == column_count - 1:
                
                self.horizontalHeader().setSectionResizeMode( i, QW.QHeaderView.ResizeMode.Stretch )
                
            else:
                
                self.horizontalHeader().setSectionResizeMode( i, QW.QHeaderView.ResizeMode.Fixed )
                
            
        
        self.setMinimumSize( QC.QSize( thumbnail_width * 2 + 24, thumbnail_height * 2 ) )
        
    
    def SetData( self, tuples_of_data ):
        
        self.model().SetData( tuples_of_data )
        
    

class ThumbnailPairListFails( ThumbnailPairList ):
    
    def __init__( self, parent ):
        
        super().__init__( parent, ThumbnailPairListModelFails() )
        
        self.horizontalHeader().setVisible( False )
        
    

class ThumbnailPairListPasses( ThumbnailPairList ):
    
    def __init__( self, parent ):
        
        super().__init__( parent, ThumbnailPairListModelPasses() )
        
    

class PreviewPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent: QW.QWidget, value_callable ):
        
        super().__init__( parent, 'preview of rule work' )
        
        self._value_callable = value_callable
        
        self._value: typing.Optional[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] = None
        
        self._num_pairs = 0
        self._fetched_pairs = []
        self._ab_pairs_that_pass_with_fixed_order_info = []
        self._pairs_that_fail = []
        
        self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
        
        self._search_results_label = ClientGUICommon.BetterStaticText( self._search_panel, label = 'ready to fetch pairs' )
        self._num_to_fetch = ClientGUICommon.NoneableSpinCtrl( self._search_panel, 256, none_phrase = 'fetch all' )
        self._fetch_pairs_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.global_pixmaps().refresh, self._RefetchPairs )
        self._fetch_pairs_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Refresh the search' ) )
        
        #
        
        self._test_pairs_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().refresh, self._RetestPairs )
        self._test_pairs_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Retest the fetched pairs' ) )
        
        #
        
        self._pass_panel = ClientGUICommon.StaticBox( self, 'pairs that will be actioned' )
        
        self._pass_pairs_label = ClientGUICommon.BetterStaticText( self, label = 'ready to generate preview' )
        
        self._pass_pairs_list = ThumbnailPairListPasses( self._pass_panel )
        
        #
        
        self._fail_panel = ClientGUICommon.StaticBox( self, 'pairs that will be skipped' )
        
        self._fail_pairs_label = ClientGUICommon.BetterStaticText( self, label = 'ready to generate preview' )
        
        self._fail_pairs_list = ThumbnailPairListFails( self._fail_panel )
        
        #
        
        self._test_pairs_button.setEnabled( False )
        
        hbox = QP.HBoxLayout()
        
        rows = []
        
        rows.append( ( 'only sample this many: ', self._num_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( hbox, gridbox, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._fetch_pairs_button, CC.FLAGS_CENTER )
        
        self._search_panel.Add( self._search_results_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._search_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        
        #
        
        self._pass_panel.Add( self._pass_pairs_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._pass_panel.Add( self._pass_pairs_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._fail_panel.Add( self._fail_pairs_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._fail_panel.Add( self._fail_pairs_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self.Add( self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( self._test_pairs_button, CC.FLAGS_ON_RIGHT )
        self.Add( self._pass_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self.Add( self._fail_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _RefetchPairs( self ):
        
        if self._value is None:
            
            return
            
        
        fetch_limit = self._num_to_fetch.GetValue()
        
        potential_duplicates_search_context = self._value.GetPotentialDuplicatesSearchContext()
        
        def work_callable():
            
            ( num_pairs, fetched_pairs ) = CG.client_controller.Read( 'potential_duplicate_pairs', potential_duplicates_search_context, fetch_limit = fetch_limit )
            
            return ( num_pairs, fetched_pairs )
            
        
        def publish_callable( result ):
            
            ( num_pairs, fetched_pairs ) = result
            
            self._num_pairs = num_pairs
            self._fetched_pairs = fetched_pairs
            
            self._UpdateSearchLabel()
            
            if len( self._fetched_pairs ) == 0:
                
                self._test_pairs_button.setEnabled( False )
                
                self._fetch_pairs_button.setEnabled( True )
                
            else:
                
                self._RetestPairs()
                
            
        
        self._fetched_pairs = []
        self._ab_pairs_that_pass_with_fixed_order_info = []
        self._pairs_that_fail = []
        
        self._fetch_pairs_button.setEnabled( False )
        self._test_pairs_button.setEnabled( False )
        
        self._search_results_label.setText( f'fetching pairs{HC.UNICODE_ELLIPSIS}' )
        self._pass_pairs_label.setText( '' )
        self._fail_pairs_label.setText( '' )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _RetestPairs( self ):
        
        if self._value is None:
            
            return
            
        
        selector = self._value.GetPairSelector()
        
        fetched_pairs = self._fetched_pairs
        
        def work_callable():
            
            ab_pairs_that_pass_with_fixed_order_info = []
            pairs_that_fail = []
            
            for pair in fetched_pairs:
                
                ( media_result_one, media_result_two ) = pair
                
                result = selector.GetMatchingAB( media_result_one, media_result_two )
                
                if result is None:
                    
                    pairs_that_fail.append( pair )
                    
                else:
                    
                    ( media_result_one, media_result_two ) = result # this might be either order, if not fixed_order mate, so let's show that in UI
                    
                    fixed_order = not selector.PairMatchesBothWaysAround( media_result_one, media_result_two )
                    
                    ab_pairs_that_pass_with_fixed_order_info.append( ( media_result_one, media_result_two, fixed_order ) )
                    
                
            
            return ( ab_pairs_that_pass_with_fixed_order_info, pairs_that_fail )
            
        
        def publish_callable( result ):
            
            ( self._ab_pairs_that_pass_with_fixed_order_info, self._pairs_that_fail ) = result
            
            self._pass_pairs_list.SetData( self._ab_pairs_that_pass_with_fixed_order_info )
            self._fail_pairs_list.SetData( self._pairs_that_fail )
            
            self._UpdateTestLabels()
            
            self._fetch_pairs_button.setEnabled( True )
            self._test_pairs_button.setEnabled( True )
            
        
        self._fetch_pairs_button.setEnabled( False )
        self._test_pairs_button.setEnabled( False )
        
        self._pass_pairs_label.setText( f'testing pairs{HC.UNICODE_ELLIPSIS}' )
        self._fail_pairs_label.setText( f'testing pairs{HC.UNICODE_ELLIPSIS}' )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _UpdateSearchLabel( self ):
        
        if self._value is None:
            
            label = 'unknown rule'
            
        else:
            
            if self._num_pairs == 0:
                
                label = 'no pairs found with this search'
                
            else:
                
                label = f'{HydrusNumbers.ToHumanInt( self._num_pairs )} pairs found'
                
            
        
        self._search_results_label.setText( label )
        
    
    def _UpdateTestLabels( self ):
        
        if len( self._ab_pairs_that_pass_with_fixed_order_info ) == 0:
            
            label = 'None!'
            
        else:
            
            label = f'{HydrusNumbers.ToHumanInt(len(self._ab_pairs_that_pass_with_fixed_order_info))} pairs'
            
        
        self._pass_pairs_label.setText( label )
        
        if len( self._pairs_that_fail ) == 0:
            
            label = 'None!'
            
        else:
            
            label = f'{HydrusNumbers.ToHumanInt(len(self._pairs_that_fail))} pairs'
            
        
        self._fail_pairs_label.setText( label )
        
    
    def PageShown( self ):
        
        old_value = self._value
        
        try:
            
            new_value = typing.cast( ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, self._value_callable() )
            
        except Exception as e:
            
            if not isinstance( e, HydrusExceptions.VetoException ):
                
                HydrusData.PrintException( e, do_wait = False )
                
            
            self._value = None
            
            self._fetch_pairs_button.setEnabled( False )
            self._test_pairs_button.setEnabled( False )
            
            self._search_results_label.setText( f'Problem fetching the current rule! {e}' )
            
            return
            
        
        self._value = new_value
        
        if old_value is None:
            
            self._RefetchPairs()
            
        else:
            
            old_search = old_value.GetPotentialDuplicatesSearchContext()
            new_search = new_value.GetPotentialDuplicatesSearchContext()
            
            if new_search.DumpToString() != old_search.DumpToString():
                
                self._RefetchPairs()
                
            else:
                
                old_selector = old_value.GetPairSelector()
                new_selector = new_value.GetPairSelector()
                
                if new_selector.DumpToString() != old_selector.DumpToString():
                    
                    self._RetestPairs()
                    
                
            
        
    
