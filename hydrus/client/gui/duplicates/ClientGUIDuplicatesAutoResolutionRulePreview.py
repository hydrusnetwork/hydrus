import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.canvas import ClientGUICanvasFrame
from hydrus.client.gui.duplicates import ThumbnailPairList
from hydrus.client.gui.widgets import ClientGUICommon

POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE = 1024

class PreviewPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent: QW.QWidget, value_callable ):
        
        super().__init__( parent, 'preview of rule work' )
        
        self._value_callable = value_callable
        
        self._value: typing.Optional[ ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule ] = None
        
        self._all_potential_duplicate_pairs_and_distances = []
        self._all_potential_duplicate_pairs_and_distances_initialised = False
        self._all_potential_duplicate_pairs_and_distances_fetch_started = False
        
        self._fetch_pairs_job_status = ClientThreading.JobStatus( cancellable = True )
        self._potential_duplicate_pairs_and_distances_still_to_search = []
        
        self._fetched_pairs = []
        
        self._test_pairs_job_status = ClientThreading.JobStatus( cancellable = True )
        self._fetched_pairs_still_to_test = []
        
        self._ab_pairs_that_pass = []
        self._pairs_that_fail = []
        
        self._search_paused = False
        self._testing_paused = False
        self._page_currently_shown = False
        
        self._search_work_updater = self._InitialiseSearchWorkUpdater()
        self._test_work_updater = self._InitialiseTestWorkUpdater()
        
        self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
        
        self._search_results_label = ClientGUICommon.BetterStaticText( self._search_panel, label = 'ready to fetch pairs' )
        self._search_results_label.setWordWrap( True )
        self._num_to_fetch = ClientGUICommon.NoneableSpinCtrl( self._search_panel, 256, min = 1, none_phrase = 'fetch all' )
        
        self._pause_search_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().pause, self._PausePlaySearch )
        
        self._refetch_pairs_button = ClientGUICommon.BetterBitmapButton( self._search_panel, CC.global_pixmaps().refresh, self._RefetchPairs )
        self._refetch_pairs_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Fetch a sample of pairs' ) )
        
        #
        
        self._pause_testing_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().pause, self._PausePlayTesting )
        
        self._retest_pairs_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().refresh, self._RetestPairs )
        self._retest_pairs_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Retest the fetched pairs' ) )
        
        #
        
        self._pass_panel = ClientGUICommon.StaticBox( self, 'pairs that will be actioned', can_expand = True, start_expanded = True, expanded_size_vertical_policy = QW.QSizePolicy.Policy.Expanding )
        
        self._pass_pairs_label = ClientGUICommon.BetterStaticText( self, label = 'ready to generate preview' )
        self._pass_pairs_label.setWordWrap( True )
        
        self._pass_pairs_list = ThumbnailPairList.ThumbnailPairListPreviewPendingAutoResolutionAction( self._pass_panel, ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'initialising' ) )
        
        #
        
        self._fail_panel = ClientGUICommon.StaticBox( self, 'pairs that will be skipped', can_expand = True, start_expanded = True, expanded_size_vertical_policy = QW.QSizePolicy.Policy.Expanding )
        
        self._fail_pairs_label = ClientGUICommon.BetterStaticText( self, label = 'ready to generate preview' )
        self._fail_pairs_label.setWordWrap( True )
        
        self._fail_pairs_list = ThumbnailPairList.ThumbnailPairListJustThumbs( self._fail_panel )
        
        #
        
        self._search_panel.Add( self._search_results_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        rows = []
        
        rows.append( ( 'only sample this many: ', self._num_to_fetch ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        QP.AddToLayout( hbox, gridbox, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._pause_search_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._refetch_pairs_button, CC.FLAGS_CENTER )
        
        self._search_panel.Add( hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._pass_panel.Add( self._pass_pairs_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._pass_panel.Add( self._pass_pairs_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._fail_panel.Add( self._fail_pairs_label, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._fail_panel.Add( self._fail_pairs_list, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._pause_testing_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._retest_pairs_button, CC.FLAGS_CENTER )
        
        self.Add( self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( hbox, CC.FLAGS_ON_RIGHT )
        self.Add( self._pass_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self.Add( self._fail_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        self._pass_pairs_list.activated.connect( self._PassRowActivated )
        self._fail_pairs_list.activated.connect( self._FailRowActivated )
        
        self._enter_catcher_pass = ThumbnailPairList.ListEnterCatcher( self, self._pass_pairs_list )
        self._enter_catcher_fail = ThumbnailPairList.ListEnterCatcher( self, self._fail_pairs_list )
        
        self._num_to_fetch.valueChanged.connect( self._DoSearchWork )
        self._num_to_fetch.valueChanged.connect( self._DoTestWork )
        
    
    def _DoSearchWork( self ):
        
        self._search_work_updater.update()
        
    
    def _DoTestWork( self ):
        
        self._test_work_updater.update()
        
    
    def _FailRowActivated( self, model_index: QC.QModelIndex ):
        
        if not model_index.isValid():
            
            return
            
        
        row = model_index.row()
        
        ( media_result_1, media_result_2 ) = self._fail_pairs_list.model().GetMediaResultPair( row )
        
        self._ShowMediaViewer( media_result_1, media_result_2 )
        
    
    def _InitialisePotentialDuplicatePairs( self ):
        
        if self._all_potential_duplicate_pairs_and_distances_initialised or self._all_potential_duplicate_pairs_and_distances_fetch_started:
            
            return
            
        
        self._all_potential_duplicate_pairs_and_distances_fetch_started = True
        
        def work_callable():
            
            all_potential_duplicate_pairs_and_distances = CG.client_controller.Read( 'all_potential_duplicate_pairs_and_distances' )
            
            # ok randomise the order we'll do this guy, but only at the block level
            # we'll preserve order each block came in since we'll then keep db-proximal indices close together on each actual block fetch
            
            all_potential_duplicate_pairs_and_distances = HydrusLists.RandomiseListByChunks( all_potential_duplicate_pairs_and_distances, POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE )
            
            return all_potential_duplicate_pairs_and_distances
            
        
        def publish_callable( all_potential_duplicate_pairs_and_distances ):
            
            self._all_potential_duplicate_pairs_and_distances = all_potential_duplicate_pairs_and_distances
            
            self._all_potential_duplicate_pairs_and_distances_initialised = True
            
            self._RefetchPairs()
            
        
        self._UpdateSearchLabels()
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _InitialiseSearchWorkUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def pre_work_callable():
            
            if self._WeHaveSearchedEnough() or self._value is None or len( self._potential_duplicate_pairs_and_distances_still_to_search ) == 0 or self._search_paused or not self._page_currently_shown:
                
                self._UpdateSearchLabels()
                
                raise HydrusExceptions.CancelledException()
                
            
            potential_duplicates_search_context = self._value.GetPotentialDuplicatesSearchContext()
            
            block_of_pairs_and_distances = self._potential_duplicate_pairs_and_distances_still_to_search[ : POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE ]
            
            self._potential_duplicate_pairs_and_distances_still_to_search = self._potential_duplicate_pairs_and_distances_still_to_search[ POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE : ]
            
            return ( potential_duplicates_search_context, block_of_pairs_and_distances, self._fetch_pairs_job_status )
            
        
        def work_callable( args ):
            
            ( potential_duplicates_search_context, block_of_pairs_and_distances, job_status ) = args
            
            if job_status.IsCancelled():
                
                return ( [], job_status )
                
            
            fetched_pairs = CG.client_controller.Read( 'potential_duplicate_pairs_fragmentary', potential_duplicates_search_context, block_of_pairs_and_distances )
            
            return ( fetched_pairs, job_status )
            
        
        def publish_callable( result ):
            
            ( some_fetched_pairs, job_status ) = result
            
            if job_status != self._fetch_pairs_job_status:
                
                return
                
            
            self._fetched_pairs.extend( some_fetched_pairs )
            self._fetched_pairs_still_to_test.extend( some_fetched_pairs )
            
            self._UpdateSearchLabels()
            
            self._DoSearchWork()
            self._DoTestWork()
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _InitialiseTestWorkUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def pre_work_callable():
            
            if self._value is None or len( self._fetched_pairs_still_to_test ) == 0 or self._WeHaveTestedEnough() or self._testing_paused or not self._page_currently_shown:
                
                self._UpdateTestLabels()
                
                raise HydrusExceptions.CancelledException()
                
            
            rule = self._value
            
            pair = self._fetched_pairs_still_to_test.pop( 0 )
            
            selector = rule.GetPairSelector()
            
            return ( pair, selector, self._test_pairs_job_status )
            
        
        def work_callable( args ):
            
            ( pair, selector, job_status ) = args
            
            ab_pair_that_passed = None
            pair_that_failed = None
            
            if job_status.IsCancelled():
                
                return ( ab_pair_that_passed, pair_that_failed, job_status )
                
            
            ( media_result_one, media_result_two ) = pair
            
            result = selector.GetMatchingAB( media_result_one, media_result_two )
            
            if result is None:
                
                pair_that_failed = pair
                
            else:
                
                ab_pair_that_passed = result
                
            
            return ( ab_pair_that_passed, pair_that_failed, job_status )
            
        
        def publish_callable( result ):
            
            ( ab_pair_that_passed, pair_that_failed, job_status ) = result
            
            if job_status != self._test_pairs_job_status:
                
                return
                
            
            if ab_pair_that_passed is not None:
                
                self._ab_pairs_that_pass.append( ab_pair_that_passed )
                self._pass_pairs_list.model().AppendData( ab_pair_that_passed )
                
            
            if pair_that_failed is not None:
                
                self._pairs_that_fail.append( pair_that_failed )
                self._fail_pairs_list.model().AppendData( pair_that_failed )
                
            
            self._UpdateTestLabels()
            
            self._DoTestWork()
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _PassRowActivated( self, model_index: QC.QModelIndex ):
        
        if not model_index.isValid():
            
            return
            
        
        row = model_index.row()
        
        ( media_result_1, media_result_2 ) = self._pass_pairs_list.model().GetMediaResultPair( row )
        
        self._ShowMediaViewer( media_result_1, media_result_2 )
        
    
    def _PausePlaySearch( self ):
        
        self._search_paused = not self._search_paused
        
        if self._search_paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_search_button, CC.global_pixmaps().play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_search_button, CC.global_pixmaps().pause )
            
        
        self._DoSearchWork()
        
    
    def _PausePlayTesting( self ):
        
        self._testing_paused = not self._testing_paused
        
        if self._testing_paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_testing_button, CC.global_pixmaps().play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_testing_button, CC.global_pixmaps().pause )
            
        
        self._DoTestWork()
        
    
    def _RefetchPairs( self ):
        
        if self._value is None:
            
            return
            
        
        if not self._all_potential_duplicate_pairs_and_distances_initialised:
            
            if not self._all_potential_duplicate_pairs_and_distances_fetch_started:
                
                self._InitialisePotentialDuplicatePairs()
                
            
            return
            
        
        self._fetched_pairs = []
        self._fetched_pairs_still_to_test = []
        
        self._potential_duplicate_pairs_and_distances_still_to_search = list( self._all_potential_duplicate_pairs_and_distances )
        
        self._fetch_pairs_job_status.Cancel()
        
        self._fetch_pairs_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._RetestPairs()
        
        self._search_results_label.setText( f'fetching pairs{HC.UNICODE_ELLIPSIS}' )
        
        self._DoSearchWork()
        
    
    def _RetestPairs( self ):
        
        if self._value is None:
            
            return
            
        
        if not self._all_potential_duplicate_pairs_and_distances_initialised:
            
            if not self._all_potential_duplicate_pairs_and_distances_fetch_started:
                
                self._InitialisePotentialDuplicatePairs()
                
            
            return
            
        
        self._fetched_pairs_still_to_test = list( self._fetched_pairs )
        self._ab_pairs_that_pass = []
        self._pairs_that_fail = []
        
        self._pass_pairs_list.SetData( [] )
        self._fail_pairs_list.SetData( [] )
        
        self._pass_pairs_list.model().SetRule( self._value )
        
        self._pass_pairs_label.setText( f'testing pairs{HC.UNICODE_ELLIPSIS}' )
        self._fail_pairs_label.setText( f'testing pairs{HC.UNICODE_ELLIPSIS}' )
        
        self._DoTestWork()
        
    
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
        
        canvas_window.canvasWithHoversExiting.connect( CG.client_controller.gui.NotifyMediaViewerExiting )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _UpdateSearchLabels( self ):
        
        if not self._all_potential_duplicate_pairs_and_distances_initialised:
            
            self._search_results_label.setText( f'initialising{HC.UNICODE_ELLIPSIS}' )
            
        elif len( self._all_potential_duplicate_pairs_and_distances ) == 0:
            
            self._search_results_label.setText( f'no potential pairs in this database!' )
            
        elif len( self._potential_duplicate_pairs_and_distances_still_to_search ) == 0:
            
            self._search_results_label.setText( f'{HydrusNumbers.ToHumanInt(len( self._all_potential_duplicate_pairs_and_distances))} potentials searched; found {HydrusNumbers.ToHumanInt( len( self._fetched_pairs ) )} pairs' )
            
        else:
            
            value = len( self._all_potential_duplicate_pairs_and_distances ) - len( self._potential_duplicate_pairs_and_distances_still_to_search )
            range = len( self._all_potential_duplicate_pairs_and_distances )
            
            self._search_results_label.setText( f'{HydrusNumbers.ValueRangeToPrettyString(value, range)} potentials searched; found {HydrusNumbers.ToHumanInt( len( self._fetched_pairs ) )} pairs{HC.UNICODE_ELLIPSIS}' )
            
        
    
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
        
    
    def _WeHaveSearchedEnough( self ):
        
        num_to_fetch = self._num_to_fetch.GetValue()
        
        if num_to_fetch is not None and len( self._fetched_pairs ) >= num_to_fetch:
            
            return True
            
        
        return False
        
    
    def _WeHaveTestedEnough( self ):
        
        num_to_fetch = self._num_to_fetch.GetValue()
        
        if num_to_fetch is not None and len( self._ab_pairs_that_pass ) + len( self._pairs_that_fail ) >= num_to_fetch:
            
            return True
            
        
        return False
        
    
    def PageIsHidden( self ):
        
        self._page_currently_shown = False
        
    
    def PageShown( self ):
        
        self._page_currently_shown = True
        
        old_value = self._value
        
        try:
            
            new_value = typing.cast( ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule, self._value_callable() )
            
        except Exception as e:
            
            if not isinstance( e, HydrusExceptions.VetoException ):
                
                HydrusData.PrintException( e, do_wait = False )
                
            
            self._value = None
            
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
                    
                
            
        
        self._DoSearchWork()
        self._DoTestWork()
        
    
