import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientRendering
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.canvas import ClientGUICanvasFrame
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
        
    
    def GetMediaResultPair( self, row: int ):
        
        r = self._data_rows[ row ]
        
        return ( r[0], r[1] )
        
    
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
        
        self.setMinimumSize( QC.QSize( my_width, thumbnail_height * 2 ) )
        
    
    def SetData( self, tuples_of_data ):
        
        self.model().SetData( tuples_of_data )
        
    

class ThumbnailPairListFails( ThumbnailPairList ):
    
    def __init__( self, parent ):
        
        super().__init__( parent, ThumbnailPairListModelFails() )
        
        self.horizontalHeader().setVisible( False )
        
    

class ThumbnailPairListPasses( ThumbnailPairList ):
    
    def __init__( self, parent ):
        
        super().__init__( parent, ThumbnailPairListModelPasses() )
        
    

class ListEnterCatcher( QC.QObject ):
    
    def __init__( self, parent, thumbnail_pair_list: ThumbnailPairList ):
        
        self._thumbnail_pair_list = thumbnail_pair_list
        
        super().__init__( parent )
        
        self._thumbnail_pair_list.installEventFilter( self )
        
    
    def eventFilter( self, obj, event ):
        
        # we can't use the normal activated guy since this appears to not stop enter propagation, allowing the dialog to close immediately after lol
        # this signals to stop event propagation
        
        if event.type() == QC.QEvent.Type.KeyPress:
            
            if event.key() in ( QC.Qt.Key.Key_Return, QC.Qt.Key.Key_Enter ):
                
                current_index = self._thumbnail_pair_list.currentIndex()
                
                if current_index.isValid():
                    
                    self._thumbnail_pair_list.activated.emit( current_index )
                    
                
                return True
                
            
        
        return False
        
    

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
        self._search_results_label.setWordWrap( True )
        self._num_to_fetch = ClientGUICommon.NoneableSpinCtrl( self._search_panel, 256, min = 1, none_phrase = 'fetch all' )
        
        self._fetch_count_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.global_pixmaps().refresh, self._RefetchCount )
        self._fetch_count_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Refresh the whole search' ) )
        
        self._fetch_pairs_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.global_pixmaps().refresh, self._RefetchPairs )
        self._fetch_pairs_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Fetch a sample of pairs' ) )
        
        #
        
        self._test_pairs_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().refresh, self._RetestPairs )
        self._test_pairs_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Retest the fetched pairs' ) )
        
        #
        
        self._pass_panel = ClientGUICommon.StaticBox( self, 'pairs that will be actioned' )
        
        self._pass_pairs_label = ClientGUICommon.BetterStaticText( self, label = 'ready to generate preview' )
        self._pass_pairs_label.setWordWrap( True )
        
        self._pass_pairs_list = ThumbnailPairListPasses( self._pass_panel )
        
        #
        
        self._fail_panel = ClientGUICommon.StaticBox( self, 'pairs that will be skipped' )
        
        self._fail_pairs_label = ClientGUICommon.BetterStaticText( self, label = 'ready to generate preview' )
        self._fail_pairs_label.setWordWrap( True )
        
        self._fail_pairs_list = ThumbnailPairListFails( self._fail_panel )
        
        #
        
        self._test_pairs_button.setEnabled( False )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._search_results_label, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._fetch_count_button, CC.FLAGS_CENTER )
        
        self._search_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        rows = []
        
        rows.append( ( 'only sample this many: ', self._num_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( hbox, gridbox, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._fetch_pairs_button, CC.FLAGS_CENTER )
        
        self._search_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
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
        
        #
        
        self._pass_pairs_list.activated.connect( self._PassRowActivated )
        self._fail_pairs_list.activated.connect( self._FailRowActivated )
        
        self._enter_catcher_pass = ListEnterCatcher( self, self._pass_pairs_list )
        self._enter_catcher_fail = ListEnterCatcher( self, self._fail_pairs_list )
        
    
    def _FailRowActivated( self, model_index: QC.QModelIndex ):
        
        if not model_index.isValid():
            
            return
            
        
        row = model_index.row()
        
        ( media_result_1, media_result_2 ) = self._fail_pairs_list.model().GetMediaResultPair( row )
        
        self._ShowMediaViewer( media_result_1, media_result_2 )
        
    
    def _PassRowActivated( self, model_index: QC.QModelIndex ):
        
        if not model_index.isValid():
            
            return
            
        
        row = model_index.row()
        
        ( media_result_1, media_result_2 ) = self._pass_pairs_list.model().GetMediaResultPair( row )
        
        self._ShowMediaViewer( media_result_1, media_result_2 )
        
    
    def _RefetchCount( self ):
        
        if self._value is None:
            
            return
            
        
        # if and when the search tab gets and caches this, we could just ask that guy
        
        potential_duplicates_search_context = self._value.GetPotentialDuplicatesSearchContext()
        
        def work_callable():
            
            num_pairs = CG.client_controller.Read( 'potential_duplicates_count', potential_duplicates_search_context )
            
            return num_pairs
            
        
        def publish_callable( num_pairs ):
            
            self._num_pairs = num_pairs
            
            self._UpdateSearchLabel()
            
            self._RefetchPairs()
            
        
        self._ResetSearchAppearance()
        
        self._search_results_label.setText( f'fetching count{HC.UNICODE_ELLIPSIS}' )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _RefetchPairs( self ):
        
        if self._value is None:
            
            return
            
        
        fetch_limit = self._num_to_fetch.GetValue()
        
        potential_duplicates_search_context = self._value.GetPotentialDuplicatesSearchContext()
        
        def work_callable():
            
            fetched_pairs = CG.client_controller.Read( 'potential_duplicate_pairs', potential_duplicates_search_context, fetch_limit = fetch_limit )
            
            return fetched_pairs
            
        
        def publish_callable( fetched_pairs ):
            
            self._fetched_pairs = fetched_pairs
            
            self._UpdateSearchLabel()
            
            self._RetestPairs()
            
        
        self._ResetFetchPairsAppearance()
        
        self._search_results_label.setText( f'fetching pairs{HC.UNICODE_ELLIPSIS}' )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _ResetFetchPairsAppearance( self ):
        
        self._fetched_pairs = []
        
        self._ResetTestPairsAppearance()
        
    
    def _ResetSearchAppearance( self ):
        
        self._num_pairs = 0
        self._search_results_label.setText( '' )
        
        self._ResetFetchPairsAppearance()
        
    
    def _ResetTestPairsAppearance( self ):
        
        self._ab_pairs_that_pass_with_fixed_order_info = []
        self._pairs_that_fail = []
        
        self._pass_pairs_list.SetData( [] )
        self._fail_pairs_list.SetData( [] )
        
        self._fetch_pairs_button.setEnabled( False )
        self._test_pairs_button.setEnabled( False )
        
        self._pass_pairs_label.setText( '' )
        self._fail_pairs_label.setText( '' )
        
    
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
            
        
        self._ResetTestPairsAppearance()
        
        self._pass_pairs_label.setText( f'testing pairs{HC.UNICODE_ELLIPSIS}' )
        self._fail_pairs_label.setText( f'testing pairs{HC.UNICODE_ELLIPSIS}' )
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _ShowMediaViewer( self, media_result_1, media_result_2 ):
        
        canvas_frame = ClientGUICanvasFrame.CanvasFrame( self.window(), set_parent = True )
        
        page_key = HydrusData.GenerateKey()
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        media_results = [ media_result_1, media_result_2 ]
        first_hash = media_result_1.GetHash()
        
        canvas_window = ClientGUICanvas.CanvasMediaListBrowser( canvas_frame, page_key, location_context, media_results, first_hash )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
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
            
            label = f'{HydrusNumbers.ToHumanInt(len(self._ab_pairs_that_pass_with_fixed_order_info))} pairs - double-click to open a media viewer'
            
        
        self._pass_pairs_label.setText( label )
        
        if len( self._pairs_that_fail ) == 0:
            
            label = 'None!'
            
        else:
            
            label = f'{HydrusNumbers.ToHumanInt(len(self._pairs_that_fail))} pairs - double-click to open a media viewer'
            
        
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
            
            self._ResetSearchAppearance()
            
            self._search_results_label.setText( f'Problem fetching the current rule! {e}' )
            
            return
            
        
        self._value = new_value
        
        if old_value is None:
            
            self._RefetchCount()
            
        else:
            
            old_search = old_value.GetPotentialDuplicatesSearchContext()
            new_search = new_value.GetPotentialDuplicatesSearchContext()
            
            if new_search.DumpToString() != old_search.DumpToString():
                
                self._RefetchCount()
                
            else:
                
                old_selector = old_value.GetPairSelector()
                new_selector = new_value.GetPairSelector()
                
                if new_selector.DumpToString() != old_selector.DumpToString():
                    
                    self._RetestPairs()
                    
                
            
        
    
