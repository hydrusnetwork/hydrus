from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton

class EditPotentialDuplicatesSearchContextPanel( ClientGUICommon.StaticBox ):
    
    restartedSearch = QC.Signal()
    thisSearchHasPairs = QC.Signal()
    thisSearchDefinitelyHasNoPairs = QC.Signal()
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, synchronised = True, page_key = None, put_searches_side_by_side = False, collapsible = False ):
        
        super().__init__( parent, 'potential duplicate pairs search', start_expanded = True, can_expand = collapsible )
        
        #
        
        self._potential_duplicate_pairs_fragmentary_search = ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch( potential_duplicates_search_context, True )
        
        self._count_job_status = ClientThreading.JobStatus( cancellable = True )
        self._estimate_confidence_reached = False
        
        self._num_potential_duplicate_pairs = 0
        
        self._count_paused = False
        
        self._count_work_updater = self._InitialiseCountWorkUpdater()
        
        #
        
        file_search_context_1 = potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = potential_duplicates_search_context.GetFileSearchContext2()
        
        file_search_context_1.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        file_search_context_2.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        if page_key is None:
            
            page_key = HydrusData.GenerateKey()
            
        
        self._tag_autocomplete_1 = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self, page_key, file_search_context_1, allow_all_known_files = False, only_allow_local_file_domains = True, only_allow_combined_local_file_domains = True, allow_multiple_file_domains = False, synchronised = synchronised, force_system_everything = True )
        self._tag_autocomplete_2 = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self, page_key, file_search_context_2, allow_all_known_files = False, only_allow_local_file_domains = True, only_allow_combined_local_file_domains = True, allow_multiple_file_domains = False, synchronised = synchronised, force_system_everything = True )
        
        self._dupe_search_type = ClientGUICommon.BetterChoice( self )
        
        self._dupe_search_type.addItem( 'at least one file matches the search', ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
        self._dupe_search_type.addItem( 'both files match the search', ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH )
        self._dupe_search_type.addItem( 'the two files match different searches', ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
        
        self._pixel_dupes_preference = ClientGUICommon.BetterChoice( self )
        
        for p in ( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED, ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED, ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED ):
            
            self._pixel_dupes_preference.addItem( ClientDuplicates.similar_files_pixel_dupes_string_lookup[ p ], p )
            
        
        self._max_hamming_distance = ClientGUICommon.BetterSpinBox( self, min = 0, max = 64 )
        self._max_hamming_distance.setSingleStep( 2 )
        
        self._num_potential_duplicate_pairs_label = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        self._pause_count_button = ClientGUICommon.IconButton( self, CC.global_icons().pause, self._PausePlayCount )
        self._refresh_dupe_counts_button = ClientGUICommon.IconButton( self, CC.global_icons().refresh, self._RefreshPotentialDuplicateIdPairsAndDistances )
        
        menu_template_items = []
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'potential_duplicate_pairs_search_context_panel_stops_to_estimate' )
        check_manager.AddNotifyCall( self.NotifyCountOptionsChanged )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'try to state an estimate of final count rather than counting everything', 'You can choose to have this panel produce an exact count every time, or stop early and estimate.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'potential_duplicate_pairs_search_can_do_file_search_based_optimisation' )
        
        tt = 'If the incremental search is getting a very low hit-rate (like 5 out of 750,000 pairs), it is usually faster for the database to just run the file searches and then cross-reference.'
        tt += '\n\n'
        tt += 'In complicated edge cases, this optimisation has very bad performance, so if you see a block or two of work and then your search halts for 30+ seconds, you can turn it off here.'
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'allow single slow search optimisation when seeing low hit-rate', tt, check_manager ) )
        
        self._cog_button = ClientGUIMenuButton.CogIconButton( self, menu_template_items )
        
        #
        
        self._dupe_search_type.SetValue( potential_duplicates_search_context.GetDupeSearchType() )
        self._pixel_dupes_preference.SetValue( potential_duplicates_search_context.GetPixelDupesPreference() )
        self._max_hamming_distance.setValue( potential_duplicates_search_context.GetMaxHammingDistance() )
        
        #
        
        self._UpdateControls()
        
        #
        
        self.Add( self._dupe_search_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if put_searches_side_by_side:
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._tag_autocomplete_1, CC.FLAGS_EXPAND_BOTH_WAYS )
            QP.AddToLayout( hbox, self._tag_autocomplete_2, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            self.Add( hbox, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        else:
            
            self.Add( self._tag_autocomplete_1, CC.FLAGS_EXPAND_BOTH_WAYS )
            self.Add( self._tag_autocomplete_2, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        
        rows = []
        
        rows.append( ( 'maximum search distance of pair: ', self._max_hamming_distance ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self, rows )
        
        self.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self.Add( self._pixel_dupes_preference, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        text_and_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( text_and_button_hbox, self._num_potential_duplicate_pairs_label, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( text_and_button_hbox, self._pause_count_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( text_and_button_hbox, self._refresh_dupe_counts_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( text_and_button_hbox, self._cog_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.Add( text_and_button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._tag_autocomplete_1.searchChanged.connect( self.Search1Changed )
        self._tag_autocomplete_2.searchChanged.connect( self.Search2Changed )
        
        self._dupe_search_type.currentIndexChanged.connect( self.DupeSearchTypeChanged )
        self._pixel_dupes_preference.currentIndexChanged.connect( self.PixelDupesPreferenceChanged )
        self._max_hamming_distance.valueChanged.connect( self.MaxHammingDistanceChanged )
        
        CG.client_controller.sub( self, 'NotifyPotentialDuplicatePairsUpdate', 'potential_duplicate_pairs_update' )
        
    
    def _AllGoodToDoCountWork( self ):
        
        if not self.isVisible():
            
            return False
            
        
        if self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised() and self._potential_duplicate_pairs_fragmentary_search.SearchSpaceIsStale():
            
            self._RefreshPotentialDuplicateIdPairsAndDistances()
            
            return False
            
        
        if not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised():
            
            if not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceFetchStarted():
                
                self._InitialisePotentialDuplicatePairs()
                
            
            return False
            
        
        return True
        
    
    def _DoCountWork( self ):
        
        self._count_work_updater.update()
        
    
    def _BroadcastValueChanged( self ):
        
        self._potential_duplicate_pairs_fragmentary_search.SetPotentialDuplicatesSearchContext( self.GetValue() )
        
        self._RefreshDuplicateCounts()
        
        self.valueChanged.emit()
        
    
    def _InitialiseCountWorkUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def pre_work_callable():
            
            if not self._AllGoodToDoCountWork():
                
                raise HydrusExceptions.CancelledException()
                
            
            if self._WeAreDoingACountEstimateAndHaveEnough():
                
                self._UpdateCountLabel()
                
                raise HydrusExceptions.CancelledException()
                
            
            if self._potential_duplicate_pairs_fragmentary_search.SearchDone() or self._count_paused:
                
                self._UpdateCountLabel()
                
                raise HydrusExceptions.CancelledException()
                
            
            return ( self._potential_duplicate_pairs_fragmentary_search, self._count_job_status )
            
        
        def work_callable( args ):
            
            ( potential_duplicate_pairs_fragmentary_search, job_status ) = args
            
            if job_status.IsCancelled():
                
                return ( [], job_status )
                
            
            start_time = HydrusTime.GetNowPrecise()
            
            count = CG.client_controller.Read( 'potential_duplicates_count_fragmentary', potential_duplicate_pairs_fragmentary_search )
            
            actual_work_period = HydrusTime.GetNowPrecise() - start_time
            
            potential_duplicate_pairs_fragmentary_search.NotifyWorkTimeForAutothrottle( actual_work_period, 0.5 )
            
            return ( count, job_status )
            
        
        def publish_callable( result ):
            
            ( count, job_status ) = result
            
            if job_status != self._count_job_status:
                
                return
                
            
            if self._num_potential_duplicate_pairs == 0 and count > 0:
                
                self.thisSearchHasPairs.emit()
                
            
            self._num_potential_duplicate_pairs += count
            
            if self._potential_duplicate_pairs_fragmentary_search.SearchDone() and self._num_potential_duplicate_pairs == 0:
                
                self.thisSearchDefinitelyHasNoPairs.emit()
                
            
            self._UpdateCountLabel()
            
            self._DoCountWork()
            
        
        return ClientGUIAsync.AsyncQtUpdater( 'potential duplicate pairs search context count', self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
    def _InitialisePotentialDuplicatePairs( self ):
        
        if self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised() or self._potential_duplicate_pairs_fragmentary_search.SearchSpaceFetchStarted():
            
            return
            
        
        self._potential_duplicate_pairs_fragmentary_search.NotifySearchSpaceFetchStarted()
        
        location_context = self.GetValue().GetLocationContext()
        
        def work_callable():
            
            potential_duplicate_id_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances = CG.client_controller.Read( 'potential_duplicate_id_pairs_and_distances', location_context )
            
            return potential_duplicate_id_pairs_and_distances
            
        
        def publish_callable( potential_duplicate_id_pairs_and_distances: ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances ):
            
            self._potential_duplicate_pairs_fragmentary_search.SetSearchSpace( potential_duplicate_id_pairs_and_distances )
            
            self._RefreshDuplicateCounts()
            
        
        self._UpdateCountLabel()
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _PausePlayCount( self ):
        
        self._count_paused = not self._count_paused
        
        if self._count_paused:
            
            self._pause_count_button.SetIconSmart( CC.global_icons().play )
            
        else:
            
            self._pause_count_button.SetIconSmart( CC.global_icons().pause )
            
        
        self._DoCountWork()
        
    
    def _RefreshPotentialDuplicateIdPairsAndDistances( self ):
        
        self._potential_duplicate_pairs_fragmentary_search.ResetSearchSpace()
        
        self._RefreshDuplicateCounts()
        
    
    def _RefreshDuplicateCounts( self ):
        
        self.restartedSearch.emit()
        
        self._num_potential_duplicate_pairs = 0
        
        self._count_job_status.Cancel()
        
        self._count_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._potential_duplicate_pairs_fragmentary_search = self._potential_duplicate_pairs_fragmentary_search.SpawnNewSearch()
        self._estimate_confidence_reached = False
        
        self._DoCountWork()
        
    
    def _UpdateControls( self ):
        
        dupe_search_type = self._dupe_search_type.GetValue()
        
        self._tag_autocomplete_2.setVisible( dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
        
        pixel_dupes_preference = self._pixel_dupes_preference.GetValue()
        
        self._max_hamming_distance.setEnabled( pixel_dupes_preference != ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED )
        
    
    def _UpdateCountLabel( self ):
        
        tooltip_override = None
        
        if not self._potential_duplicate_pairs_fragmentary_search.SearchSpaceInitialised():
            
            text = f'initialising{HC.UNICODE_ELLIPSIS}'
            
        elif self._potential_duplicate_pairs_fragmentary_search.SearchSpaceIsEmpty():
            
            text = f'no potential pairs in this file domain!'
            
        else:
            
            num_pairs_in_search_space = self._potential_duplicate_pairs_fragmentary_search.NumPairsInSearchSpace()
            num_pairs_searched = self._potential_duplicate_pairs_fragmentary_search.NumPairsSearched()
            
            if self._WeAreDoingACountEstimateAndHaveEnough():
                
                if self._potential_duplicate_pairs_fragmentary_search.SearchDone():
                    
                    text = f'{HydrusNumbers.ToHumanInt( num_pairs_in_search_space )} pairs; {HydrusNumbers.ToHumanInt( self._num_potential_duplicate_pairs )} match'
                    
                else:
                    
                    estimate = self._potential_duplicate_pairs_fragmentary_search.EstimatedNumHits()
                    
                    estimate_base = estimate
                    estimate_base_multiplier = 1
                    
                    # cut 25,123 to 25,000
                    while len( str( estimate_base ) ) > 2:
                        
                        estimate_base = int( estimate_base / 10 )
                        estimate_base_multiplier *= 10
                        
                    
                    estimate = estimate_base * estimate_base_multiplier
                    
                    text = f'{HydrusNumbers.ToHumanInt(num_pairs_in_search_space)} pairs; ~{HydrusNumbers.ToHumanInt( estimate )} match'
                    
                
            else:
                
                if self._potential_duplicate_pairs_fragmentary_search.SearchDone():
                    
                    text = f'{HydrusNumbers.ToHumanInt(num_pairs_in_search_space)} pairs searched; {HydrusNumbers.ToHumanInt( self._num_potential_duplicate_pairs )} match'
                    
                else:
                    
                    value = num_pairs_searched
                    range = num_pairs_in_search_space
                    
                    text = f'{HydrusNumbers.ValueRangeToPrettyString(value, range)} pairs searched; {HydrusNumbers.ToHumanInt( self._num_potential_duplicate_pairs )} match{HC.UNICODE_ELLIPSIS}'
                    
                
            
            tooltip_override = 'The number on the left is how many pairs are in the system; on the right is how many match your current search.'
            tooltip_override += '\n\n'
            tooltip_override += 'A system:everything search in "combined local file domains" at a distance of 8+ should find ~100%. Do not worry if there are a couple of loose pairs you cannot find--they are probably in the trash, waiting to be deleted.'
            
        
        self._num_potential_duplicate_pairs_label.setText( text )
        
        if tooltip_override is not None:
            
            self._num_potential_duplicate_pairs_label.setToolTip( ClientGUIFunctions.WrapToolTip( tooltip_override ) )
            
        
    
    def _WeAreDoingACountEstimateAndHaveEnough( self ):
        
        if not CG.client_controller.new_options.GetBoolean( 'potential_duplicate_pairs_search_context_panel_stops_to_estimate' ):
            
            return False
            
        
        if self._potential_duplicate_pairs_fragmentary_search.ThereIsJustABitLeftBro():
            
            # for whatever reason we are in a 'searched 1700 out of 1703 rows' type situation, so let's do the last little bit and get a nice number
            
            return False
            
        
        # this is mostly AI vomit, but I'm generally there. 95% of <2.5%, simple as
        
        REL_ERROR  = 0.025 # 2.5% error
        
        if self._estimate_confidence_reached:
            
            return True
            
        
        rel = self._potential_duplicate_pairs_fragmentary_search.GetRelativeErrorAt95Certainty()
        
        should_stop = rel <= REL_ERROR
        
        if should_stop:
            
            self._estimate_confidence_reached = True
            
        
        return should_stop
        
        # old way lol
        # return self._num_potential_duplicate_pairs >= 1000
        
    
    def DupeSearchTypeChanged( self ):
        
        self._UpdateControls()
        
        self._BroadcastValueChanged()
        
    
    def GetValue( self, optimise_for_search = True ) -> ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext:
        
        file_search_context_1 = self._tag_autocomplete_1.GetFileSearchContext()
        file_search_context_2 = self._tag_autocomplete_2.GetFileSearchContext()
        
        dupe_search_type = self._dupe_search_type.GetValue()
        
        pixel_dupes_preference = self._pixel_dupes_preference.GetValue()
        
        max_hamming_distance = self._max_hamming_distance.value()
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        return potential_duplicates_search_context
        
    
    def IsSynchronised( self ) -> bool:
        
        return self._tag_autocomplete_1.IsSynchronised()
        
    
    def MaxHammingDistanceChanged( self ):
        
        self._BroadcastValueChanged()
        
    
    def NotifyCountOptionsChanged( self ):
        
        self._DoCountWork()
        
    
    def ForceRefreshNumbers( self ):
        
        self._RefreshPotentialDuplicateIdPairsAndDistances()
        
    
    def NotifyPotentialDuplicatePairsUpdate( self, update_type, *args ):
        
        self._potential_duplicate_pairs_fragmentary_search.NotifyPotentialDuplicatePairsUpdate( update_type, *args )
        
        self._num_potential_duplicate_pairs = self._potential_duplicate_pairs_fragmentary_search.GetNumHits()
        
        self._DoCountWork()
        
    
    def PageHidden( self ):
        
        self._tag_autocomplete_1.SetForceDropdownHide( True )
        self._tag_autocomplete_2.SetForceDropdownHide( True )
        
    
    def PageShown( self ):
        
        self._tag_autocomplete_1.SetForceDropdownHide( False )
        self._tag_autocomplete_2.SetForceDropdownHide( False )
        
        self._DoCountWork()
        
    
    def PixelDupesPreferenceChanged( self ):
        
        self._UpdateControls()
        
        self._BroadcastValueChanged()
        
    
    def REPEATINGPageUpdate( self ):
        
        self._tag_autocomplete_1.REPEATINGPageUpdate()
        self._tag_autocomplete_2.REPEATINGPageUpdate()
        
    
    def Search1Changed( self ):
        
        reinit_pairs = self._tag_autocomplete_1.GetLocationContext() != self._tag_autocomplete_2.GetLocationContext()
        
        self._tag_autocomplete_2.blockSignals( True )
        
        self._tag_autocomplete_2.SetLocationContext( self._tag_autocomplete_1.GetLocationContext() )
        self._tag_autocomplete_2.SetSynchronised( self._tag_autocomplete_1.IsSynchronised() )
        
        self._tag_autocomplete_2.blockSignals( False )
        
        self._BroadcastValueChanged()
        
    
    def Search2Changed( self ):
        
        reinit_pairs = self._tag_autocomplete_1.GetLocationContext() != self._tag_autocomplete_2.GetLocationContext()
        
        self._tag_autocomplete_1.blockSignals( True )
        
        self._tag_autocomplete_1.SetLocationContext( self._tag_autocomplete_2.GetLocationContext() )
        self._tag_autocomplete_1.SetSynchronised( self._tag_autocomplete_2.IsSynchronised() )
        
        self._tag_autocomplete_1.blockSignals( False )
        
        self._BroadcastValueChanged()
        
    

class PotentialDuplicatesSortWidget( QW.QWidget ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, duplicate_pair_sort_type: int, duplicate_pair_sort_asc: bool ):
        
        super().__init__( parent )
        
        choice_tuples = [ ( 'sort by: ' + ClientDuplicates.dupe_pair_sort_string_lookup[ sort_type ], sort_type ) for sort_type in (
            ClientDuplicates.DUPE_PAIR_SORT_MAX_FILESIZE,
            ClientDuplicates.DUPE_PAIR_SORT_MIN_FILESIZE,
            ClientDuplicates.DUPE_PAIR_SORT_SIMILARITY,
            ClientDuplicates.DUPE_PAIR_SORT_RANDOM
        ) ]
        
        self._sort_type = ClientGUIMenuButton.MenuChoiceButton( self, choice_tuples )
        
        choice_tuples = [
            ( 'asc', True ),
            ( 'desc', False )
        ]
        
        self._sort_asc = ClientGUIMenuButton.MenuChoiceButton( self, choice_tuples )
        
        #
        
        self.SetValue( duplicate_pair_sort_type, duplicate_pair_sort_asc )
        
        #
        
        hbox = QP.HBoxLayout( margin = 0 )
        
        QP.AddToLayout( hbox, self._sort_type, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._sort_asc, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self.setLayout( hbox )
        
        #
        
        self._sort_type.valueChanged.connect( self._UpdateControlsAfterSortTypeChanged )
        
        self._sort_type.valueChanged.connect( self._HandleValueChanged )
        self._sort_asc.valueChanged.connect( self._HandleValueChanged )
        
    
    def _UpdateControlsAfterSortTypeChanged( self ):
        
        sort_type = self._sort_type.GetValue()
        
        if sort_type == ClientDuplicates.DUPE_PAIR_SORT_RANDOM:
            
            self._sort_asc.setVisible( False )
            
        else:
            
            self._sort_asc.setVisible( True )
            
            choice_tuples = [
                ( 'asc', True ),
                ( 'desc', False )
            ]
            
            if sort_type in ( ClientDuplicates.DUPE_PAIR_SORT_MAX_FILESIZE, ClientDuplicates.DUPE_PAIR_SORT_MIN_FILESIZE ):
                
                choice_tuples = [
                    ( 'largest first', False ),
                    ( 'smallest first', True )
                ]
                
            elif sort_type == ClientDuplicates.DUPE_PAIR_SORT_SIMILARITY:
                
                choice_tuples = [
                    ( 'most similar first', True ),
                    ( 'least similar first', False )
                ]
                
            
            self._sort_asc.SetChoiceTuples( choice_tuples )
            
        
    
    def _HandleValueChanged( self ):
        
        self.valueChanged.emit()
        
    
    def GetValue( self ):
        
        sort_type = self._sort_type.GetValue()
        
        sort_asc = self._sort_asc.GetValue()
        
        return ( sort_type, sort_asc )
        
    
    def SetValue( self, sort_type: int, sort_asc: bool ):
        
        self._sort_type.blockSignals( True )
        self._sort_asc.blockSignals( True )
        
        self._sort_type.SetValue( sort_type )
        
        self._UpdateControlsAfterSortTypeChanged()
        
        self._sort_asc.SetValue( sort_asc )
        
        self._sort_type.blockSignals( False )
        self._sort_asc.blockSignals( False )
        
        self._HandleValueChanged()
        
    
