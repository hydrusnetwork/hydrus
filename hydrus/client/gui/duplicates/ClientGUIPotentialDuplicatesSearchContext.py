from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
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

# good idea to refresh this cache regularly, to clear out since-deleted pairs and catch other unusual desync situations
POTENTIAL_PAIRS_REFRESH_TIMEOUT = 3600

POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE = 4096

class EditPotentialDuplicatesSearchContextPanel( ClientGUICommon.StaticBox ):
    
    restartedSearch = QC.Signal()
    thisSearchHasPairs = QC.Signal()
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, synchronised = True, page_key = None, put_searches_side_by_side = False ):
        
        super().__init__( parent, 'potential duplicate pairs search' )
        
        #
        
        self._all_potential_duplicate_pairs_and_distances = []
        self._all_potential_duplicate_pairs_and_distances_initialised = False
        self._all_potential_duplicate_pairs_and_distances_fetch_started = False
        self._all_potential_duplicate_pairs_and_distances_initialised_time = 0
        
        self._count_job_status = ClientThreading.JobStatus( cancellable = True )
        self._potential_duplicate_pairs_and_distances_still_to_search = []
        
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
            
        
        self._tag_autocomplete_1 = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self, page_key, file_search_context_1, allow_all_known_files = False, only_allow_local_file_domains = True, only_allow_all_my_files_domains = True, synchronised = synchronised, force_system_everything = True )
        self._tag_autocomplete_2 = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self, page_key, file_search_context_2, allow_all_known_files = False, only_allow_local_file_domains = True, only_allow_all_my_files_domains = True, synchronised = synchronised, force_system_everything = True )
        
        self._dupe_search_type = ClientGUICommon.BetterChoice( self )
        
        self._dupe_search_type.addItem( 'at least one file matches the search', ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
        self._dupe_search_type.addItem( 'both files match the search', ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH )
        self._dupe_search_type.addItem( 'both files match different searches', ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
        
        self._pixel_dupes_preference = ClientGUICommon.BetterChoice( self )
        
        for p in ( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED, ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED, ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED ):
            
            self._pixel_dupes_preference.addItem( ClientDuplicates.similar_files_pixel_dupes_string_lookup[ p ], p )
            
        
        self._max_hamming_distance = ClientGUICommon.BetterSpinBox( self, min = 0, max = 64 )
        self._max_hamming_distance.setSingleStep( 2 )
        
        self._num_potential_duplicate_pairs_label = ClientGUICommon.BetterStaticText( self, ellipsize_end = True )
        self._pause_count_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().pause, self._PausePlayCount )
        self._refresh_dupe_counts_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().refresh, self._RefreshAllPotentialDuplicatePairsAndDistances )
        
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
        
        self.Add( text_and_button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._tag_autocomplete_1.searchChanged.connect( self.Search1Changed )
        self._tag_autocomplete_2.searchChanged.connect( self.Search2Changed )
        
        self._dupe_search_type.currentIndexChanged.connect( self.DupeSearchTypeChanged )
        self._pixel_dupes_preference.currentIndexChanged.connect( self.PixelDupesPreferenceChanged )
        self._max_hamming_distance.valueChanged.connect( self.MaxHammingDistanceChanged )
        
    
    def _AllGoodToDoCountWork( self ):
        
        if not self.isVisible():
            
            return False
            
        
        if self._all_potential_duplicate_pairs_and_distances_initialised and HydrusTime.TimeHasPassed( self._all_potential_duplicate_pairs_and_distances_initialised_time + POTENTIAL_PAIRS_REFRESH_TIMEOUT ):
            
            self._RefreshAllPotentialDuplicatePairsAndDistances()
            
            return False
            
        
        if not self._all_potential_duplicate_pairs_and_distances_initialised:
            
            if not self._all_potential_duplicate_pairs_and_distances_fetch_started:
                
                self._InitialisePotentialDuplicatePairs()
                
            
            return False
            
        
        return True
        
    
    def _DoCountWork( self ):
        
        self._count_work_updater.update()
        
    
    def _BroadcastValueChanged( self ):
        
        self._RefreshDuplicateCounts()
        
        self.valueChanged.emit()
        
    
    def _InitialiseCountWorkUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def pre_work_callable():
            
            if not self._AllGoodToDoCountWork():
                
                raise HydrusExceptions.CancelledException()
                
            
            if len( self._potential_duplicate_pairs_and_distances_still_to_search ) == 0 or self._count_paused:
                
                self._UpdateCountLabel()
                
                raise HydrusExceptions.CancelledException()
                
            
            potential_duplicates_search_context = self.GetValue()
            
            block_of_pairs_and_distances = self._potential_duplicate_pairs_and_distances_still_to_search[ : POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE ]
            
            self._potential_duplicate_pairs_and_distances_still_to_search = self._potential_duplicate_pairs_and_distances_still_to_search[ POTENTIAL_DUPLICATE_PAIRS_BLOCK_SIZE : ]
            
            return ( potential_duplicates_search_context, block_of_pairs_and_distances, self._count_job_status )
            
        
        def work_callable( args ):
            
            ( potential_duplicates_search_context, block_of_pairs_and_distances, job_status ) = args
            
            if job_status.IsCancelled():
                
                return ( [], job_status )
                
            
            count = CG.client_controller.Read( 'potential_duplicates_count_fragmentary', potential_duplicates_search_context, block_of_pairs_and_distances )
            
            return ( count, job_status )
            
        
        def publish_callable( result ):
            
            ( count, job_status ) = result
            
            if job_status != self._count_job_status:
                
                return
                
            
            if self._num_potential_duplicate_pairs == 0 and count > 0:
                
                self.thisSearchHasPairs.emit()
                
            
            self._num_potential_duplicate_pairs += count
            
            self._UpdateCountLabel()
            
            self._DoCountWork()
            
        
        return ClientGUIAsync.AsyncQtUpdater( self, loading_callable, work_callable, publish_callable, pre_work_callable = pre_work_callable )
        
    
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
            self._all_potential_duplicate_pairs_and_distances_initialised_time = HydrusTime.GetNow()
            
            self._all_potential_duplicate_pairs_and_distances_fetch_started = False
            
            self._RefreshDuplicateCounts()
            
        
        self._UpdateCountLabel()
        
        async_job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
        
        async_job.start()
        
    
    def _PausePlayCount( self ):
        
        self._count_paused = not self._count_paused
        
        if self._count_paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_count_button, CC.global_pixmaps().play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_count_button, CC.global_pixmaps().pause )
            
        
        self._DoCountWork()
        
    
    def _RefreshAllPotentialDuplicatePairsAndDistances( self ):
        
        self._all_potential_duplicate_pairs_and_distances_initialised = False
        
        self._all_potential_duplicate_pairs_and_distances = []
        
        self._RefreshDuplicateCounts()
        
    
    def _RefreshDuplicateCounts( self ):
        
        self.restartedSearch.emit()
        
        self._num_potential_duplicate_pairs = 0
        
        self._count_job_status.Cancel()
        
        self._count_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._potential_duplicate_pairs_and_distances_still_to_search = list( self._all_potential_duplicate_pairs_and_distances )
        
        self._DoCountWork()
        
    
    def _UpdateControls( self ):
        
        dupe_search_type = self._dupe_search_type.GetValue()
        
        self._tag_autocomplete_2.setVisible( dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
        
        pixel_dupes_preference = self._pixel_dupes_preference.GetValue()
        
        self._max_hamming_distance.setEnabled( pixel_dupes_preference != ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED )
        
    
    def _UpdateCountLabel( self ):
        
        if not self._all_potential_duplicate_pairs_and_distances_initialised:
            
            self._num_potential_duplicate_pairs_label.setText( f'initialising{HC.UNICODE_ELLIPSIS}' )
            
        elif len( self._all_potential_duplicate_pairs_and_distances ) == 0:
            
            self._num_potential_duplicate_pairs_label.setText( f'no potential pairs in this database!' )
            
        elif len( self._potential_duplicate_pairs_and_distances_still_to_search ) == 0:
            
            self._num_potential_duplicate_pairs_label.setText( f'{HydrusNumbers.ToHumanInt(len( self._all_potential_duplicate_pairs_and_distances))} potentials searched; found {HydrusNumbers.ToHumanInt( self._num_potential_duplicate_pairs )} pairs' )
            
        else:
            
            value = len( self._all_potential_duplicate_pairs_and_distances ) - len( self._potential_duplicate_pairs_and_distances_still_to_search )
            range = len( self._all_potential_duplicate_pairs_and_distances )
            
            self._num_potential_duplicate_pairs_label.setText( f'{HydrusNumbers.ValueRangeToPrettyString(value, range)} potentials searched; found {HydrusNumbers.ToHumanInt( self._num_potential_duplicate_pairs )} pairs{HC.UNICODE_ELLIPSIS}' )
            
        
    
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
        
    
    def NotifyNewDupePairs( self ):
        
        self._RefreshAllPotentialDuplicatePairsAndDistances()
        
    
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
        
        self._tag_autocomplete_2.blockSignals( True )
        
        self._tag_autocomplete_2.SetLocationContext( self._tag_autocomplete_1.GetLocationContext() )
        self._tag_autocomplete_2.SetSynchronised( self._tag_autocomplete_1.IsSynchronised() )
        
        self._tag_autocomplete_2.blockSignals( False )
        
        self._BroadcastValueChanged()
        
    
    def Search2Changed( self ):
        
        self._tag_autocomplete_1.blockSignals( True )
        
        self._tag_autocomplete_1.SetLocationContext( self._tag_autocomplete_2.GetLocationContext() )
        self._tag_autocomplete_1.SetSynchronised( self._tag_autocomplete_2.IsSynchronised() )
        
        self._tag_autocomplete_1.blockSignals( False )
        
        self._BroadcastValueChanged()
        
    
