import collections
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.duplicates import ClientPotentialDuplicatesPairFactory
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvasDuplicates
from hydrus.client.gui.canvas import ClientGUICanvasFrame
from hydrus.client.gui.duplicates import ThumbnailPairList
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.media import ClientMedia

class PreviewPanel( ClientGUICommon.StaticBox ):
    
    def __init__( self, parent: QW.QWidget, value_callable ):
        
        super().__init__( parent, 'preview of rule work' )
        
        self._value_callable = value_callable
        
        self._value: ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule | None = None
        
        self._potential_duplicate_pairs_fragmentary_search = ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch(
            ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext(),
            True
        )
        
        self._potential_duplicate_pairs_fragmentary_search.SetDesiredNumHits( 250 ) # just a nice hint
        
        self._fetch_pairs_job_status = ClientThreading.JobStatus( cancellable = True )
        
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
        self._num_to_fetch = ClientGUICommon.NoneableSpinCtrl( self._search_panel, 250, min = 1, none_phrase = 'fetch all' )
        
        self._pause_search_button = ClientGUICommon.IconButton( self, CC.global_icons().pause, self._PausePlaySearch )
        
        self._refetch_pairs_button = ClientGUICommon.IconButton( self._search_panel, CC.global_icons().refresh, self._RefetchPairs )
        self._refetch_pairs_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Fetch a sample of pairs' ) )
        
        #
        
        self._pairs_still_to_test_label = ClientGUICommon.BetterStaticText( self, label = 'ready to test new pairs' )
        self._pairs_still_to_test_label.setWordWrap( True )
        
        self._pause_testing_button = ClientGUICommon.IconButton( self, CC.global_icons().pause, self._PausePlayTesting )
        
        self._retest_pairs_button = ClientGUICommon.IconButton( self, CC.global_icons().refresh, self._RetestPairs )
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
        
        QP.AddToLayout( hbox, self._pairs_still_to_test_label, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._pause_testing_button, CC.FLAGS_CENTER )
        QP.AddToLayout( hbox, self._retest_pairs_button, CC.FLAGS_CENTER )
        
        self.Add( self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
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
        
        media_result_pairs = self._fail_pairs_list.model().GetMediaResultPairsStartingAtIndex( row )
        
        if len( media_result_pairs ) == 0:
            
            return
            
        
        media_result_pairs = [ ( m_a, m_b ) for ( m_a, m_b ) in media_result_pairs if m_a.GetLocationsManager().IsLocal() and m_b.GetLocationsManager().IsLocal() ]
        
        if len( media_result_pairs ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, but it seems there is nothing to show! Every pair I saw had at least one non-local file. Try refreshing the panel!' )
            
            return
            
        
        # with a bit of jiggling I can probably deliver the real distance, but w/e for now, not important
        
        media_result_pairs_and_fake_distances = [ ( m_a, m_b, 0 ) for ( m_a, m_b ) in media_result_pairs ]
        
        potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( media_result_pairs_and_fake_distances )
        
        self._ShowDuplicateFilter( potential_duplicate_media_result_pairs_and_distances )
        
    
    def _InitialisePotentialDuplicatePairs( self ):
        
        if self._value is None or self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised() or self._potential_duplicate_pairs_fragmentary_search.SearchSpaceFetchStarted():
            
            return
            
        
        self._potential_duplicate_pairs_fragmentary_search.NotifySearchSpaceFetchStarted()
        
        location_context = self._potential_duplicate_pairs_fragmentary_search.GetLocationContext()
        
        def work_callable():
            
            potential_duplicate_id_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances = CG.client_controller.Read( 'potential_duplicate_id_pairs_and_distances', location_context )
            
            return potential_duplicate_id_pairs_and_distances
            
        
        def publish_callable( potential_duplicate_id_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances ):
            
            self._potential_duplicate_pairs_fragmentary_search.SetSearchSpace( potential_duplicate_id_pairs_and_distances )
            
            self._RefetchPairs()
            
        
        self._UpdateSearchLabels()
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _InitialiseSearchWorkUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def pre_work_callable():
            
            if self._value is None or self._WeHaveSearchedEnough() or self._potential_duplicate_pairs_fragmentary_search.SearchDone() or self._search_paused or not self._page_currently_shown:
                
                self._UpdateSearchLabels()
                
                raise HydrusExceptions.CancelledException()
                
            
            return ( self._potential_duplicate_pairs_fragmentary_search, self._fetch_pairs_job_status )
            
        
        def work_callable( args ):
            
            ( potential_duplicate_pairs_fragmentary_search, job_status ) = args
            
            if job_status.IsCancelled():
                
                return ( [], job_status )
                
            
            potential_duplicate_media_result_pairs_and_distances = CG.client_controller.Read( 'potential_duplicate_media_result_pairs_and_distances_fragmentary', potential_duplicate_pairs_fragmentary_search )
            
            potential_duplicate_media_result_pairs_and_distances.Sort( ClientDuplicates.DUPE_PAIR_SORT_MIN_FILESIZE, False )
            
            return ( potential_duplicate_media_result_pairs_and_distances, job_status )
            
        
        def publish_callable( result ):
            
            ( potential_duplicate_media_result_pairs_and_distances, job_status ) = result
            
            if job_status != self._fetch_pairs_job_status:
                
                return
                
            
            some_fetched_pairs = potential_duplicate_media_result_pairs_and_distances.GetPairs()
            
            self._fetched_pairs.extend( some_fetched_pairs )
            self._fetched_pairs_still_to_test.extend( some_fetched_pairs )
            
            self._UpdateSearchLabels()
            
            self._DoSearchWork()
            self._DoTestWork()
            
        
        return ClientGUIAsync.AsyncQtUpdater( 'preview auto-resolution search', self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
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
            
        
        return ClientGUIAsync.AsyncQtUpdater( 'preview auto-resolution test', self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _PassRowActivated( self, model_index: QC.QModelIndex ):
        
        if not model_index.isValid():
            
            return
            
        
        row = model_index.row()
        
        media_result_pairs = self._pass_pairs_list.model().GetMediaResultPairsStartingAtIndex( row )
        
        if len( media_result_pairs ) == 0:
            
            return
            
        
        media_result_pairs = [ ( m1, m2 ) for ( m1, m2 ) in media_result_pairs if m1.GetLocationsManager().IsLocal() and m2.GetLocationsManager().IsLocal() ]
        
        if len( media_result_pairs ) == 0:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'Sorry, but it seems there is nothing to show! Every pair I saw had at least one non-local file. Try refreshing the panel!' )
            
            return
            
        
        # with a bit of jiggling I can probably deliver the real distance, but w/e for now, not important
        
        media_result_pairs_and_fake_distances = [ ( m1, m2, 0 ) for ( m1, m2 ) in media_result_pairs ]
        
        potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( media_result_pairs_and_fake_distances )
        
        self._ShowDuplicateFilter( potential_duplicate_media_result_pairs_and_distances )
        
    
    def _PausePlaySearch( self ):
        
        self._search_paused = not self._search_paused
        
        if self._search_paused:
            
            self._pause_search_button.SetIconSmart( CC.global_icons().play )
            
        else:
            
            self._pause_search_button.SetIconSmart( CC.global_icons().pause )
            
        
        self._DoSearchWork()
        
    
    def _PausePlayTesting( self ):
        
        self._testing_paused = not self._testing_paused
        
        if self._testing_paused:
            
            self._pause_testing_button.SetIconSmart( CC.global_icons().play )
            
        else:
            
            self._pause_testing_button.SetIconSmart( CC.global_icons().pause )
            
        
        self._DoTestWork()
        
    
    def _RefetchPairs( self ):
        
        if self._value is None:
            
            return
            
        
        if not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised():
            
            if not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceFetchStarted():
                
                self._InitialisePotentialDuplicatePairs()
                
            
            return
            
        
        self._fetched_pairs = []
        self._fetched_pairs_still_to_test = []
        
        self._potential_duplicate_pairs_fragmentary_search = self._potential_duplicate_pairs_fragmentary_search.SpawnNewSearch()
        
        self._fetch_pairs_job_status.Cancel()
        
        self._fetch_pairs_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._RetestPairs()
        
        self._search_results_label.setText( f'fetching pairs{HC.UNICODE_ELLIPSIS}' )
        
        self._DoSearchWork()
        
    
    def _RetestPairs( self ):
        
        if self._value is None:
            
            return
            
        
        if not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised():
            
            if not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceFetchStarted():
                
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
        
    
    def _ShowDuplicateFilter( self, potential_duplicate_media_result_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances ):
        
        canvas_frame = ClientGUICanvasFrame.CanvasFrame( self.window(), set_parent = True )
        
        potential_duplicate_pair_factory = ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactoryMediaResults( potential_duplicate_media_result_pairs_and_distances )
        
        canvas_window = ClientGUICanvasDuplicates.CanvasFilterDuplicates( canvas_frame, potential_duplicate_pair_factory )
        
        canvas_window.canvasWithHoversExiting.connect( CG.client_controller.gui.NotifyMediaViewerExiting )
        canvas_window.showPairInPage.connect( self._ShowPairInPage )
        
        canvas_window.canvasDuplicateFilterExitingAfterWorkDone.connect( self._RefetchPairs )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _ShowPairInPage( self, media: collections.abc.Collection[ ClientMedia.MediaSingleton ] ):
        
        hashes = [ m.GetHash() for m in media ]
        
        CG.client_controller.pub( 'imported_files_to_page', hashes, 'duplicate pairs' )
        
    
    def _UpdateSearchLabels( self ):
        
        if not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised():
            
            self._search_results_label.setText( f'initialising{HC.UNICODE_ELLIPSIS}' )
            
        elif self._potential_duplicate_pairs_fragmentary_search.SearchSpaceIsEmpty():
            
            self._search_results_label.setText( f'no potential pairs in this file domain!' )
            
        elif self._potential_duplicate_pairs_fragmentary_search.SearchDone():
            
            self._search_results_label.setText( f'{HydrusNumbers.ToHumanInt(self._potential_duplicate_pairs_fragmentary_search.NumPairsInSearchSpace())} pairs searched; {HydrusNumbers.ToHumanInt( len( self._fetched_pairs ) )} matched' )
            
        else:
            
            value = self._potential_duplicate_pairs_fragmentary_search.NumPairsSearched()
            range = self._potential_duplicate_pairs_fragmentary_search.NumPairsInSearchSpace()
            
            self._search_results_label.setText( f'{HydrusNumbers.ValueRangeToPrettyString(value, range)} pairs searched; {HydrusNumbers.ToHumanInt( len( self._fetched_pairs ) )} matched{HC.UNICODE_ELLIPSIS}' )
            
        
    
    def _UpdateTestLabels( self ):
        
        if len( self._fetched_pairs_still_to_test ) == 0:
            
            label = ''
            
        else:
            
            label = f'{HydrusNumbers.ToHumanInt( len( self._fetched_pairs_still_to_test ))} pairs still to test'
            
        
        self._pairs_still_to_test_label.setText( label )
        
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
        
        self._potential_duplicate_pairs_fragmentary_search.SetPotentialDuplicatesSearchContext( self._value.GetPotentialDuplicatesSearchContext() )
        
        if old_value is None:
            
            self._RefetchPairs()
            
        else:
            
            old_search = old_value.GetPotentialDuplicatesSearchContext()
            new_search = new_value.GetPotentialDuplicatesSearchContext()
            
            if new_search.GetLocationContext() != old_search.GetLocationContext():
                
                self._InitialisePotentialDuplicatePairs()
                
            elif new_search.DumpToString() != old_search.DumpToString():
                
                self._RefetchPairs()
                
            else:
                
                old_selector = old_value.GetPairSelector()
                new_selector = new_value.GetPairSelector()
                
                if new_selector.DumpToString() != old_selector.DumpToString():
                    
                    self._RetestPairs()
                    
                
            
        
        self._DoSearchWork()
        self._DoTestWork()
        
    
