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
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.canvas import ClientGUICanvasFrame
from hydrus.client.gui.duplicates import ThumbnailPairList
from hydrus.client.gui.widgets import ClientGUICommon

class PreviewPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent: QW.QWidget, value_callable ):
        
        super().__init__( parent, 'preview of rule work' )
        
        self._value_callable = value_callable
        
        self._value: typing.Optional[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] = None
        
        self._num_pairs = 0
        self._fetched_pairs = []
        self._ab_pairs_that_pass = []
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
        
        self._pass_panel = ClientGUICommon.StaticBox( self, 'pairs that will be actioned', can_expand = True, start_expanded = True )
        
        self._pass_pairs_label = ClientGUICommon.BetterStaticText( self, label = 'ready to generate preview' )
        self._pass_pairs_label.setWordWrap( True )
        
        self._pass_pairs_list = ThumbnailPairList.ThumbnailPairListPreviewPendingAutoResolutionAction( self._pass_panel, ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'initialising' ) )
        
        #
        
        self._fail_panel = ClientGUICommon.StaticBox( self, 'pairs that will be skipped', can_expand = True, start_expanded = True )
        
        self._fail_pairs_label = ClientGUICommon.BetterStaticText( self, label = 'ready to generate preview' )
        self._fail_pairs_label.setWordWrap( True )
        
        self._fail_pairs_list = ThumbnailPairList.ThumbnailPairListJustThumbs( self._fail_panel )
        
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
        
        self._enter_catcher_pass = ThumbnailPairList.ListEnterCatcher( self, self._pass_pairs_list )
        self._enter_catcher_fail = ThumbnailPairList.ListEnterCatcher( self, self._fail_pairs_list )
        
    
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
        
        self._ab_pairs_that_pass = []
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
            
        
        rule = self._value
        selector = self._value.GetPairSelector()
        
        fetched_pairs = self._fetched_pairs
        
        def work_callable():
            
            ab_pairs_that_pass = []
            pairs_that_fail = []
            
            for pair in fetched_pairs:
                
                ( media_result_one, media_result_two ) = pair
                
                # TODO: Argh this will be slow. We need to figure out a better stream here then. incremental addition or something like it
                result = selector.GetMatchingAB( media_result_one, media_result_two )
                
                if result is None:
                    
                    pairs_that_fail.append( pair )
                    
                else:
                    
                    ab_pairs_that_pass.append( pair )
                    
                
            
            return ( ab_pairs_that_pass, pairs_that_fail )
            
        
        def publish_callable( result ):
            
            ( self._ab_pairs_that_pass, self._pairs_that_fail ) = result
            
            self._pass_pairs_list.model().SetRule( self._value )
            self._pass_pairs_list.SetData( self._ab_pairs_that_pass )
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
        
        media_results = [ mr for mr in media_results if mr.GetLocationsManager().IsLocal() ]
        
        if len( media_results ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, but neither of those files is local (they were probably deleted), so they cannot be displayed in the media viewer!' )
            
            return
            
        
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
        
        if len( self._ab_pairs_that_pass ) == 0:
            
            label = 'None!'
            
        else:
            
            label = f'{HydrusNumbers.ToHumanInt(len(self._ab_pairs_that_pass))} pairs - double-click to open a media viewer'
            
        
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
                    
                
            
        
    
