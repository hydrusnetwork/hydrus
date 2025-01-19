from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusData

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon

class EditPotentialDuplicatesSearchContextPanel( ClientGUICommon.StaticBox ):
    
    valueChanged = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, potential_duplicates_search_context: ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext, synchronised = True, page_key = None, put_searches_side_by_side = False ):
        
        super().__init__( parent, 'potential duplicate pairs search' )
        
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
        
        self._tag_autocomplete_1.searchChanged.connect( self.Search1Changed )
        self._tag_autocomplete_2.searchChanged.connect( self.Search2Changed )
        
        self._dupe_search_type.currentIndexChanged.connect( self.DupeSearchTypeChanged )
        self._pixel_dupes_preference.currentIndexChanged.connect( self.PixelDupesPreferenceChanged )
        self._max_hamming_distance.valueChanged.connect( self.MaxHammingDistanceChanged )
        
    
    def _UpdateControls( self ):
        
        dupe_search_type = self._dupe_search_type.GetValue()
        
        self._tag_autocomplete_2.setVisible( dupe_search_type == ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
        
        pixel_dupes_preference = self._pixel_dupes_preference.GetValue()
        
        self._max_hamming_distance.setEnabled( pixel_dupes_preference != ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED )
        
    
    def DupeSearchTypeChanged( self ):
        
        self._UpdateControls()
        
        self.valueChanged.emit()
        
    
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
        
        self.valueChanged.emit()
        
    
    def PageHidden( self ):
        
        self._tag_autocomplete_1.SetForceDropdownHide( True )
        self._tag_autocomplete_2.SetForceDropdownHide( True )
        
    
    def PageShown( self ):
        
        self._tag_autocomplete_1.SetForceDropdownHide( False )
        self._tag_autocomplete_2.SetForceDropdownHide( False )
        
    
    def PixelDupesPreferenceChanged( self ):
        
        self._UpdateControls()
        
        self.valueChanged.emit()
        
    
    def REPEATINGPageUpdate( self ):
        
        self._tag_autocomplete_1.REPEATINGPageUpdate()
        self._tag_autocomplete_2.REPEATINGPageUpdate()
        
    
    def Search1Changed( self ):
        
        self._tag_autocomplete_2.blockSignals( True )
        
        self._tag_autocomplete_2.SetLocationContext( self._tag_autocomplete_1.GetLocationContext() )
        self._tag_autocomplete_2.SetSynchronised( self._tag_autocomplete_1.IsSynchronised() )
        
        self._tag_autocomplete_2.blockSignals( False )
        
        self.valueChanged.emit()
        
    
    def Search2Changed( self ):
        
        self._tag_autocomplete_1.blockSignals( True )
        
        self._tag_autocomplete_1.SetLocationContext( self._tag_autocomplete_2.GetLocationContext() )
        self._tag_autocomplete_1.SetSynchronised( self._tag_autocomplete_2.IsSynchronised() )
        
        self._tag_autocomplete_1.blockSignals( False )
        
        self.valueChanged.emit()
        
    
