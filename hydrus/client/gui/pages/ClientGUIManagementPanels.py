import collections
import os
import random
import threading
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusLists
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientDuplicates
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientParsing
from hydrus.client import ClientPaths
from hydrus.client import ClientServices
from hydrus.client import ClientThreading
from hydrus.client import ClientTime
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogs
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIScrolledPanels
from hydrus.client.gui import ClientGUIFileSeedCache
from hydrus.client.gui import ClientGUIGallerySeedLog
from hydrus.client.gui import ClientGUIScrolledPanelsEdit
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.canvas import ClientGUICanvasFrame
from hydrus.client.gui.importing import ClientGUIImport
from hydrus.client.gui.importing import ClientGUIImportOptions
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.lists import ClientGUIListConstants as CGLC
from hydrus.client.gui.lists import ClientGUIListCtrl
from hydrus.client.gui.networking import ClientGUIHydrusNetwork
from hydrus.client.gui.networking import ClientGUINetworkJobControl
from hydrus.client.gui.pages import ClientGUIManagementController
from hydrus.client.gui.pages import ClientGUIResults
from hydrus.client.gui.pages import ClientGUIResultsSortCollect
from hydrus.client.gui.parsing import ClientGUIParsingFormulae
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIControls
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.importing import ClientImporting
from hydrus.client.importing import ClientImportWatchers
from hydrus.client.importing import ClientImportLocal
from hydrus.client.importing import ClientImportSimpleURLs
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearch

management_panel_types_to_classes = {}

def AddPresentationSubmenu( menu: QW.QMenu, importer_name: str, single_selected_presentation_import_options: typing.Optional[ PresentationImportOptions.PresentationImportOptions ], callable ):
    
    submenu = ClientGUIMenus.GenerateMenu( menu )
    
    # inbox only
    # detect single_selected_presentation_import_options and deal with it
    
    description = 'Gather these files for the selected importers and show them.'
    
    if single_selected_presentation_import_options is None:
        
        ClientGUIMenus.AppendMenuItem( submenu, 'default presented files', description, callable )
        
    else:
        
        ClientGUIMenus.AppendMenuItem( submenu, 'default presented files ({})'.format( single_selected_presentation_import_options.GetSummary() ), description, callable )
        
    
    sets_of_options = []
    
    presentation_import_options = PresentationImportOptions.PresentationImportOptions()
    
    presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
    
    sets_of_options.append( presentation_import_options )
    
    presentation_import_options = PresentationImportOptions.PresentationImportOptions()
    
    presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_REQUIRE_INBOX )
    
    sets_of_options.append( presentation_import_options )
    
    presentation_import_options = PresentationImportOptions.PresentationImportOptions()
    
    sets_of_options.append( presentation_import_options )
    
    presentation_import_options = PresentationImportOptions.PresentationImportOptions()
    
    presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
    
    sets_of_options.append( presentation_import_options )
    
    for presentation_import_options in sets_of_options:
        
        if single_selected_presentation_import_options is not None and presentation_import_options == single_selected_presentation_import_options:
            
            continue
            
        
        ClientGUIMenus.AppendMenuItem( submenu, presentation_import_options.GetSummary(), description, callable, presentation_import_options = presentation_import_options )
        
    
    ClientGUIMenus.AppendMenu( menu, submenu, 'show files' )
    

class ListBoxTagsMediaManagementPanel( ClientGUIListBoxes.ListBoxTagsMedia ):
    
    def __init__( self, parent, management_controller: ClientGUIManagementController.ManagementController, page_key, tag_display_type = ClientTags.TAG_DISPLAY_SELECTION_LIST, tag_autocomplete: typing.Optional[ ClientGUIACDropdown.AutoCompleteDropdownTagsRead ] = None ):
        
        ClientGUIListBoxes.ListBoxTagsMedia.__init__( self, parent, tag_display_type, include_counts = True )
        
        self._management_controller = management_controller
        self._minimum_height_num_chars = 15
        
        self._page_key = page_key
        self._tag_autocomplete = tag_autocomplete
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        predicates = self._GetPredicatesFromTerms( self._selected_terms )
        
        if len( predicates ) > 0:
            
            if ctrl_down:
                
                predicates = [ predicate.GetInverseCopy() for predicate in predicates ]
                
            
            if shift_down and len( predicates ) > 1:
                
                predicates = ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, value = predicates ), )
                
            
            CG.client_controller.pub( 'enter_predicates', self._page_key, predicates )
            
            return True
            
        
        return False
        
    
    def _CanProvideCurrentPagePredicates( self ):
        
        return self._tag_autocomplete is not None
        
    
    def _GetCurrentLocationContext( self ):
        
        return self._management_controller.GetLocationContext()
        
    
    def _GetCurrentPagePredicates( self ) -> typing.Set[ ClientSearch.Predicate ]:
        
        if self._tag_autocomplete is None:
            
            return set()
            
        else:
            
            return self._tag_autocomplete.GetPredicates()
            
        
    
    def _ProcessMenuPredicateEvent( self, command ):
        
        ( predicates, or_predicate, inverse_predicates, namespace_predicate, inverse_namespace_predicate ) = self._GetSelectedPredicatesAndInverseCopies()
        
        p = None
        permit_remove = True
        permit_add = True
        
        if command == 'add_predicates':
            
            p = predicates
            permit_remove = False
            
        elif command == 'add_or_predicate':
            
            p = ( or_predicate, )
            permit_remove = False
            
        elif command == 'remove_predicates':
            
            p = predicates
            permit_add = False
            
        elif command == 'add_inverse_predicates':
            
            p = inverse_predicates
            permit_remove = False
            
        elif command == 'add_namespace_predicate':
            
            p = ( namespace_predicate, )
            permit_remove = False
            
        elif command == 'add_inverse_namespace_predicate':
            
            p = ( inverse_namespace_predicate, )
            permit_remove = False
            
        
        if p is not None:
            
            CG.client_controller.pub( 'enter_predicates', self._page_key, p, permit_remove = permit_remove, permit_add = permit_add )
            
        
    

class ManagementPanel( QW.QScrollArea ):
    
    locationChanged = QC.Signal( ClientLocation.LocationContext )
    
    SHOW_COLLECT = True
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        QW.QScrollArea.__init__( self, parent )
        
        self.setFrameShape( QW.QFrame.NoFrame )
        self.setWidget( QW.QWidget( self ) )
        self.setWidgetResizable( True )
        #self.setFrameStyle( QW.QFrame.Panel | QW.QFrame.Sunken )
        #self.setLineWidth( 2 )
        #self.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarAlwaysOff )
        self.setVerticalScrollBarPolicy( QC.Qt.ScrollBarAsNeeded )
        
        self._controller = controller
        self._management_controller = management_controller
        
        self._last_seen_location_context = self._management_controller.GetLocationContext()
        
        self._page = page
        self._page_key = self._management_controller.GetVariable( 'page_key' )
        
        self._page_state = CC.PAGE_STATE_NORMAL
        
        self._current_selection_tags_list = None
        
        self._media_sort_widget = ClientGUIResultsSortCollect.MediaSortControl( self, media_sort = self._management_controller.GetVariable( 'media_sort' ) )
        
        if self._management_controller.HasVariable( 'media_collect' ):
            
            media_collect = self._management_controller.GetVariable( 'media_collect' )
            
        else:
            
            media_collect = ClientMedia.MediaCollect()
            
        
        self._media_collect_widget = ClientGUIResultsSortCollect.MediaCollectControl( self, media_collect = media_collect )
        
        self._media_collect_widget.ListenForNewOptions()
        
        if self.SHOW_COLLECT:
            
            self._media_collect_widget.collectChanged.connect( self._CollectChanged )
            
        else:
            
            self._media_collect_widget.hide()
            
        
        self._media_sort_widget.sortChanged.connect( self._SortChanged )
        
    
    def _CollectChanged( self, media_collect ):
        
        self._management_controller.SetVariable( 'media_collect', media_collect )
        
    
    def _GetDefaultEmptyPageStatusOverride( self ) -> str:
        
        return 'empty page'
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer, tag_display_type = ClientTags.TAG_DISPLAY_SELECTION_LIST ):
        
        self._current_selection_tags_box = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        self._current_selection_tags_list = ListBoxTagsMediaManagementPanel( self._current_selection_tags_box, self._management_controller, self._page_key, tag_display_type = tag_display_type )
        
        self._current_selection_tags_box.SetTagsBox( self._current_selection_tags_list )
        
        QP.AddToLayout( sizer, self._current_selection_tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        if location_context != self._last_seen_location_context:
            
            self._last_seen_location_context = location_context
            
            self.locationChanged.emit( location_context )
            
        
    
    def _SortChanged( self, media_sort ):
        
        self._management_controller.SetVariable( 'media_sort', media_sort )
        
    
    def ConnectMediaPanelSignals( self, media_panel: ClientGUIResults.MediaPanel ):
        
        if self._current_selection_tags_list is not None:
            
            media_panel.selectedMediaTagPresentationChanged.connect( self._current_selection_tags_list.SetTagsByMediaFromMediaPanel )
            media_panel.selectedMediaTagPresentationIncremented.connect( self._current_selection_tags_list.IncrementTagsByMedia )
            self._media_collect_widget.collectChanged.connect( media_panel.Collect )
            self._media_sort_widget.sortChanged.connect( media_panel.Sort )
            
            media_panel.PublishSelectionChange()
            
        
    
    def CheckAbleToClose( self ):
        
        pass
        
    
    def CleanBeforeClose( self ):
        
        pass
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def GetDefaultEmptyMediaPanel( self ) -> ClientGUIResults.MediaPanel:
        
        panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, [] )
        
        status = self._GetDefaultEmptyPageStatusOverride()
        
        panel.SetEmptyPageStatusOverride( status )
        
        return panel
        
    
    def GetMediaCollect( self ):
        
        if self.SHOW_COLLECT:
            
            return self._media_collect_widget.GetValue()
            
        else:
            
            return ClientMedia.MediaCollect()
            
        
    
    def GetMediaSort( self ):
        
        return self._media_sort_widget.GetSort()
        
    
    def GetPageState( self ) -> int:
        
        return self._page_state
        
    
    def PageHidden( self ):
        
        pass
        
    
    def PageShown( self ):
        
        if self._controller.new_options.GetBoolean( 'set_search_focus_on_page_change' ):
            
            self.SetSearchFocus()
            
        
    
    def RefreshQuery( self ):
        
        pass
        
    
    def SetMediaSort( self, media_sort, do_sort = True ):
        
        return self._media_sort_widget.SetSort( media_sort, do_sort = do_sort )
        
    
    def SetSearchFocus( self ):
        
        pass
        
    
    def Start( self ):
        
        pass
        
    
    def REPEATINGPageUpdate( self ):
        
        pass
        
    

def CreateManagementPanel( parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ) -> ManagementPanel:
    
    management_type = management_controller.GetType()
    
    management_class = management_panel_types_to_classes[ management_type ]
    
    management_panel = management_class( parent, page, controller, management_controller )
    
    return management_panel
    

class ManagementPanelDuplicateFilter( ManagementPanel ):
    
    SHOW_COLLECT = False
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._duplicates_manager = ClientDuplicates.DuplicatesManager.instance()
        
        self._similar_files_maintenance_status = None
        self._duplicates_manager_is_fetching_maintenance_numbers = False
        self._potential_file_search_currently_happening = False
        self._maintenance_numbers_need_redrawing = True
        
        self._potential_duplicates_count = 0
        
        self._have_done_first_maintenance_numbers_show = False
        
        new_options = self._controller.new_options
        
        self._dupe_count_numbers_dirty = True
        
        self._currently_refreshing_dupe_count_numbers = False
        
        #
        
        self._main_notebook = ClientGUICommon.BetterNotebook( self )
        
        self._main_left_panel = QW.QWidget( self._main_notebook )
        self._main_right_panel = QW.QWidget( self._main_notebook )
        
        #
        
        self._refresh_maintenance_status = ClientGUICommon.BetterStaticText( self._main_left_panel, ellipsize_end = True )
        self._refresh_maintenance_button = ClientGUICommon.BetterBitmapButton( self._main_left_panel, CC.global_pixmaps().refresh, self._duplicates_manager.RefreshMaintenanceNumbers )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'reset potential duplicates', 'This will delete all the discovered potential duplicate pairs. All files that may have potential pairs will be queued up for similar file search again.', self._ResetUnknown ) )
        menu_items.append( ( 'separator', 0, 0, 0 ) )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'maintain_similar_files_duplicate_pairs_during_idle' )
        
        menu_items.append( ( 'check', 'search for potential duplicates at the current distance during idle time/shutdown', 'Tell the client to find duplicate pairs in its normal db maintenance cycles, whether you have that set to idle or shutdown time.', check_manager ) )
        
        self._cog_button = ClientGUIMenuButton.MenuBitmapButton( self._main_left_panel, CC.global_pixmaps().cog, menu_items )
        
        menu_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DUPLICATES )
        
        menu_items.append( ( 'normal', 'open the html duplicates help', 'Open the help page for duplicates processing in your web browser.', page_func ) )
        
        self._help_button = ClientGUIMenuButton.MenuBitmapButton( self._main_left_panel, CC.global_pixmaps().help, menu_items )
        
        #
        
        self._searching_panel = ClientGUICommon.StaticBox( self._main_left_panel, 'finding potential duplicates' )
        
        self._eligible_files = ClientGUICommon.BetterStaticText( self._searching_panel, ellipsize_end = True )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'exact match', 'Search for exact matches.', HydrusData.Call( self._SetSearchDistance, CC.HAMMING_EXACT_MATCH ) ) )
        menu_items.append( ( 'normal', 'very similar', 'Search for very similar files.', HydrusData.Call( self._SetSearchDistance, CC.HAMMING_VERY_SIMILAR ) ) )
        menu_items.append( ( 'normal', 'similar', 'Search for similar files.', HydrusData.Call( self._SetSearchDistance, CC.HAMMING_SIMILAR ) ) )
        menu_items.append( ( 'normal', 'speculative', 'Search for files that are probably similar.', HydrusData.Call( self._SetSearchDistance, CC.HAMMING_SPECULATIVE ) ) )
        
        self._max_hamming_distance_for_potential_discovery_button = ClientGUIMenuButton.MenuButton( self._searching_panel, 'similarity', menu_items )
        
        self._max_hamming_distance_for_potential_discovery_spinctrl = ClientGUICommon.BetterSpinBox( self._searching_panel, min=0, max=64, width = 50 )
        self._max_hamming_distance_for_potential_discovery_spinctrl.setSingleStep( 2 )
        
        self._num_searched = ClientGUICommon.TextAndGauge( self._searching_panel )
        
        self._search_button = ClientGUICommon.BetterBitmapButton( self._searching_panel, CC.global_pixmaps().play, self._duplicates_manager.StartPotentialsSearch )
        
        #
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'this is better\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_BETTER ) ) )
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'same quality\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_SAME_QUALITY ) ) )
        
        if new_options.GetBoolean( 'advanced_mode' ):
            
            menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'alternates\' (advanced!)', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_ALTERNATE ) ) )
            
        
        self._edit_merge_options = ClientGUIMenuButton.MenuButton( self._main_right_panel, 'edit default duplicate metadata merge options', menu_items )
        
        #
        
        self._filtering_panel = ClientGUICommon.StaticBox( self._main_right_panel, 'duplicate filter' )
        
        file_search_context_1 = management_controller.GetVariable( 'file_search_context_1' )
        file_search_context_2 = management_controller.GetVariable( 'file_search_context_2' )
        
        file_search_context_1.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        file_search_context_2.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        if self._management_controller.HasVariable( 'synchronised' ):
            
            synchronised = self._management_controller.GetVariable( 'synchronised' )
            
        else:
            
            synchronised = True
            
        
        self._tag_autocomplete_1 = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._filtering_panel, self._page_key, file_search_context_1, media_sort_widget = self._media_sort_widget, media_collect_widget = self._media_collect_widget, allow_all_known_files = False, synchronised = synchronised, force_system_everything = True )
        self._tag_autocomplete_2 = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._filtering_panel, self._page_key, file_search_context_2, media_sort_widget = self._media_sort_widget, media_collect_widget = self._media_collect_widget, allow_all_known_files = False, synchronised = synchronised, force_system_everything = True )
        
        self._dupe_search_type = ClientGUICommon.BetterChoice( self._filtering_panel )
        
        self._dupe_search_type.addItem( 'at least one file matches the search', CC.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
        self._dupe_search_type.addItem( 'both files match the search', CC.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH )
        self._dupe_search_type.addItem( 'both files match different searches', CC.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
        
        self._pixel_dupes_preference = ClientGUICommon.BetterChoice( self._filtering_panel )
        
        for p in ( CC.SIMILAR_FILES_PIXEL_DUPES_REQUIRED, CC.SIMILAR_FILES_PIXEL_DUPES_ALLOWED, CC.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED ):
            
            self._pixel_dupes_preference.addItem( CC.similar_files_pixel_dupes_string_lookup[ p ], p )
            
        
        self._max_hamming_distance_for_filter = ClientGUICommon.BetterSpinBox( self._filtering_panel, min = 0, max = 64 )
        self._max_hamming_distance_for_filter.setSingleStep( 2 )
        
        self._num_potential_duplicates = ClientGUICommon.BetterStaticText( self._filtering_panel, ellipsize_end = True )
        self._refresh_dupe_counts_button = ClientGUICommon.BetterBitmapButton( self._filtering_panel, CC.global_pixmaps().refresh, self.RefreshDuplicateNumbers )
        
        self._launch_filter = ClientGUICommon.BetterButton( self._filtering_panel, 'launch the filter', self._LaunchFilter )
        
        #
        
        random_filtering_panel = ClientGUICommon.StaticBox( self._main_right_panel, 'quick and dirty processing' )
        
        self._show_some_dupes = ClientGUICommon.BetterButton( random_filtering_panel, 'show some random potential pairs', self._ShowRandomPotentialDupes )
        
        self._set_random_as_same_quality_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as duplicates of the same quality', self._SetCurrentMediaAs, HC.DUPLICATE_SAME_QUALITY )
        self._set_random_as_alternates_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as all related alternates', self._SetCurrentMediaAs, HC.DUPLICATE_ALTERNATE )
        self._set_random_as_false_positives_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as not related/false positive', self._SetCurrentMediaAs, HC.DUPLICATE_FALSE_POSITIVE )
        
        #
        
        self._main_notebook.addTab( self._main_left_panel, 'preparation' )
        self._main_notebook.addTab( self._main_right_panel, 'filtering' )
        self._main_notebook.setCurrentWidget( self._main_right_panel )
        
        #
        
        self._max_hamming_distance_for_potential_discovery_spinctrl.setValue( new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' ) )
        
        self._dupe_search_type.SetValue( management_controller.GetVariable( 'dupe_search_type' ) )
        
        if not management_controller.HasVariable( 'pixel_dupes_preference' ):
            
            management_controller.SetVariable( 'pixel_dupes_preference', CC.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
            
        
        self._pixel_dupes_preference.SetValue( management_controller.GetVariable( 'pixel_dupes_preference' ) )
        
        self._pixel_dupes_preference.currentIndexChanged.connect( self.FilterSearchDomainChanged )
        
        if not management_controller.HasVariable( 'max_hamming_distance' ):
            
            management_controller.SetVariable( 'max_hamming_distance', 4 )
            
        
        self._max_hamming_distance_for_filter.setValue( management_controller.GetVariable( 'max_hamming_distance' ) )
        
        self._max_hamming_distance_for_filter.valueChanged.connect( self.FilterSearchDomainChanged )
        
        #
        
        self._UpdateFilterSearchControls()
        
        #
        
        self._media_sort_widget.hide()
        
        distance_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( distance_hbox, ClientGUICommon.BetterStaticText(self._searching_panel,label='search distance: '), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( distance_hbox, self._max_hamming_distance_for_potential_discovery_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( distance_hbox, self._max_hamming_distance_for_potential_discovery_spinctrl, CC.FLAGS_CENTER_PERPENDICULAR )
        
        gridbox_2 = QP.GridLayout( cols = 2 )
        
        gridbox_2.setColumnStretch( 0, 1 )
        
        QP.AddToLayout( gridbox_2, self._num_searched, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( gridbox_2, self._search_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._searching_panel.Add( self._eligible_files, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._searching_panel.Add( distance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._searching_panel.Add( gridbox_2, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._refresh_maintenance_status, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._refresh_maintenance_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._cog_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( hbox, self._help_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._searching_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 1 )
        
        self._main_left_panel.setLayout( vbox )
        
        #
        
        text_and_button_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( text_and_button_hbox, self._num_potential_duplicates, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( text_and_button_hbox, self._refresh_dupe_counts_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        rows = []
        
        rows.append( ( 'maximum search distance of pair: ', self._max_hamming_distance_for_filter ) )
        
        gridbox = ClientGUICommon.WrapInGrid( self._filtering_panel, rows )
        
        self._filtering_panel.Add( self._dupe_search_type, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._tag_autocomplete_1, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._tag_autocomplete_2, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( gridbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._filtering_panel.Add( self._pixel_dupes_preference, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( text_and_button_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._filtering_panel.Add( self._launch_filter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        random_filtering_panel.Add( self._show_some_dupes, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_same_quality_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_alternates_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_false_positives_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._edit_merge_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, random_filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self._main_right_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._main_notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._controller.sub( self, 'NotifyNewMaintenanceNumbers', 'new_similar_files_maintenance_numbers' )
        self._controller.sub( self, 'NotifyNewPotentialsSearchNumbers', 'new_similar_files_potentials_search_numbers' )
        
        self._tag_autocomplete_1.searchChanged.connect( self.Search1Changed )
        self._tag_autocomplete_2.searchChanged.connect( self.Search2Changed )
        
        self._dupe_search_type.currentIndexChanged.connect( self.FilterDupeSearchTypeChanged )
        
        self._max_hamming_distance_for_potential_discovery_spinctrl.valueChanged.connect( self.MaxHammingDistanceForPotentialDiscoveryChanged )
        
    
    def _EditMergeOptions( self, duplicate_type ):
        
        new_options = CG.client_controller.new_options
        
        duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit duplicate merge options' ) as dlg:
            
            panel = ClientGUIScrolledPanelsEdit.EditDuplicateContentMergeOptionsPanel( dlg, duplicate_type, duplicate_content_merge_options )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                duplicate_content_merge_options = panel.GetValue()
                
                new_options.SetDuplicateContentMergeOptions( duplicate_type, duplicate_content_merge_options )
                
            
        
    
    def _FilterSearchDomainUpdated( self ):
        
        ( file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance ) = self._GetDuplicateFileSearchData( optimise_for_search = False )
        
        self._management_controller.SetVariable( 'file_search_context_1', file_search_context_1 )
        self._management_controller.SetVariable( 'file_search_context_2', file_search_context_2 )
        
        synchronised = self._tag_autocomplete_1.IsSynchronised()
        
        self._management_controller.SetVariable( 'synchronised', synchronised )
        
        self._management_controller.SetVariable( 'dupe_search_type', dupe_search_type )
        self._management_controller.SetVariable( 'pixel_dupes_preference', pixel_dupes_preference )
        self._management_controller.SetVariable( 'max_hamming_distance', max_hamming_distance )
        
        self._SetLocationContext( file_search_context_1.GetLocationContext() )
        
        self._UpdateFilterSearchControls()
        
        if self._tag_autocomplete_1.IsSynchronised():
            
            self._dupe_count_numbers_dirty = True
            
        
    
    def _GetDuplicateFileSearchData( self, optimise_for_search = True ) -> typing.Tuple[ ClientSearch.FileSearchContext, ClientSearch.FileSearchContext, int, int, int ]:
        
        file_search_context_1 = self._tag_autocomplete_1.GetFileSearchContext()
        file_search_context_2 = self._tag_autocomplete_2.GetFileSearchContext()
        
        dupe_search_type = self._dupe_search_type.GetValue()
        
        if optimise_for_search:
            
            if dupe_search_type == CC.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH and ( file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates() ):
                
                dupe_search_type = CC.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
                
            elif dupe_search_type == CC.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES:
                
                if file_search_context_1.IsJustSystemEverything() or file_search_context_1.HasNoPredicates():
                    
                    f = file_search_context_1
                    file_search_context_1 = file_search_context_2
                    file_search_context_2 = f
                    
                    dupe_search_type = CC.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
                    
                elif file_search_context_2.IsJustSystemEverything() or file_search_context_2.HasNoPredicates():
                    
                    dupe_search_type = CC.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
                    
                
            
        
        pixel_dupes_preference = self._pixel_dupes_preference.GetValue()
        
        max_hamming_distance = self._max_hamming_distance_for_filter.value()
        
        return ( file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance )
        
    
    def _LaunchFilter( self ):
        
        ( file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance ) = self._GetDuplicateFileSearchData()
        
        canvas_frame = ClientGUICanvasFrame.CanvasFrame( self.window() )
        
        canvas_window = ClientGUICanvas.CanvasFilterDuplicates( canvas_frame, file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance )
        
        canvas_window.showPairInPage.connect( self._ShowPairInPage )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _RefreshDuplicateCounts( self ):
        
        def qt_code( potential_duplicates_count ):
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self._currently_refreshing_dupe_count_numbers = False
            
            self._dupe_count_numbers_dirty = False
            
            self._refresh_dupe_counts_button.setEnabled( True )
            
            self._UpdatePotentialDuplicatesCount( potential_duplicates_count )
            
        
        def thread_do_it( file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance ):
            
            potential_duplicates_count = CG.client_controller.Read( 'potential_duplicates_count', file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance )
            
            QP.CallAfter( qt_code, potential_duplicates_count )
            
        
        if not self._currently_refreshing_dupe_count_numbers:
            
            self._currently_refreshing_dupe_count_numbers = True
            
            self._refresh_dupe_counts_button.setEnabled( False )
            
            self._num_potential_duplicates.setText( 'updating' + HC.UNICODE_ELLIPSIS )
            
            ( file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance ) = self._GetDuplicateFileSearchData()
            
            CG.client_controller.CallToThread( thread_do_it, file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance )
            
        
    
    def _ResetUnknown( self ):
        
        text = 'ADVANCED TOOL: This will delete all the current potential duplicate pairs. All files that may be similar will be queued for search again.'
        text += os.linesep * 2
        text += 'This can be useful if you know you have database damage and need to reset and re-search everything, or if you have accidentally searched too broadly and are now swamped with too many false positives. It is not useful for much else.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.Accepted:
            
            self._controller.Write( 'delete_potential_duplicate_pairs' )
            
            self._duplicates_manager.RefreshMaintenanceNumbers()
            
        
    
    def _SetCurrentMediaAs( self, duplicate_type ):
        
        media_panel = self._page.GetMediaPanel()
        
        change_made = media_panel.SetDuplicateStatusForAll( duplicate_type )
        
        if change_made:
            
            self._dupe_count_numbers_dirty = True
            
            if self._potential_duplicates_count > 1:
                
                self._ShowRandomPotentialDupes()
                
            else:
                
                self._ShowPotentialDupes( [] )
                
            
        
    
    def _SetSearchDistance( self, value ):
        
        self._max_hamming_distance_for_potential_discovery_spinctrl.setValue( value )
        
        self._UpdateMaintenanceStatus()
        
    
    def _ShowPairInPage( self, media: typing.Collection[ ClientMedia.MediaSingleton ] ):
        
        media_results = [ m.GetMediaResult() for m in media ]
        
        self._page.GetMediaPanel().AddMediaResults( self._page_key, media_results )
        
    
    def _ShowPotentialDupes( self, hashes ):
        
        ( file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance ) = self._GetDuplicateFileSearchData()
        
        location_context = file_search_context_1.GetLocationContext()
        
        self._SetLocationContext( location_context )
        
        if len( hashes ) > 0:
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
        else:
            
            media_results = []
            
        
        panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, media_results )
        
        panel.SetEmptyPageStatusOverride( 'no dupes found' )
        
        self._page.SwapMediaPanel( panel )
        
        self._page_state = CC.PAGE_STATE_NORMAL
        
    
    def _ShowRandomPotentialDupes( self ):
        
        ( file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance ) = self._GetDuplicateFileSearchData()
        
        self._page_state = CC.PAGE_STATE_SEARCHING
        
        hashes = self._controller.Read( 'random_potential_duplicate_hashes', file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance )
        
        if len( hashes ) == 0:
            
            HydrusData.ShowText( 'No random potential duplicates were found. Try refreshing the count, and if this keeps happening, please let hydrus_dev know.' )
            
        
        self._ShowPotentialDupes( hashes )
        
    
    def _UpdateMaintenanceStatus( self ):
        
        self._refresh_maintenance_button.setEnabled( not ( self._duplicates_manager_is_fetching_maintenance_numbers or self._potential_file_search_currently_happening ) )
        
        if self._similar_files_maintenance_status is None:
            
            self._search_button.setEnabled( False )
            
            return
            
        
        searched_distances_to_count = self._similar_files_maintenance_status
        
        self._cog_button.setEnabled( True )
        
        total_num_files = sum( searched_distances_to_count.values() )
        
        self._eligible_files.setText( '{} eligible files in the system.'.format(HydrusData.ToHumanInt(total_num_files)) )
        
        self._max_hamming_distance_for_potential_discovery_button.setEnabled( True )
        self._max_hamming_distance_for_potential_discovery_spinctrl.setEnabled( True )
        
        options_search_distance = self._controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
        
        if self._max_hamming_distance_for_potential_discovery_spinctrl.value() != options_search_distance:
            
            self._max_hamming_distance_for_potential_discovery_spinctrl.setValue( options_search_distance )
            
        
        search_distance = self._max_hamming_distance_for_potential_discovery_spinctrl.value()
        
        if search_distance in CC.hamming_string_lookup:
            
            button_label = CC.hamming_string_lookup[ search_distance ]
            
        else:
            
            button_label = 'custom'
            
        
        self._max_hamming_distance_for_potential_discovery_button.setText( button_label )
        
        num_searched = sum( ( count for ( value, count ) in searched_distances_to_count.items() if value is not None and value >= search_distance ) )
        
        not_all_files_searched = num_searched < total_num_files
        
        we_can_start_work = not_all_files_searched and not self._potential_file_search_currently_happening
        
        self._search_button.setEnabled( we_can_start_work )
        
        if not_all_files_searched:
            
            if num_searched == 0:
                
                self._num_searched.SetValue( 'Have not yet searched at this distance.', 0, total_num_files )
                
            else:
                
                self._num_searched.SetValue( 'Searched ' + HydrusData.ConvertValueRangeToPrettyString( num_searched, total_num_files ) + ' files at this distance.', num_searched, total_num_files )
                
            
            page_name = 'preparation (needs work)'
            
        else:
            
            self._num_searched.SetValue( 'All potential duplicates found at this distance.', total_num_files, total_num_files )
            
            page_name = 'preparation'
            
        
        self._main_notebook.setTabText( 0, page_name )
        
    
    def _UpdatePotentialDuplicatesCount( self, potential_duplicates_count ):
        
        self._potential_duplicates_count = potential_duplicates_count
        
        self._num_potential_duplicates.setText( '{} potential pairs.'.format( HydrusData.ToHumanInt( potential_duplicates_count ) ) )
        
        if self._potential_duplicates_count > 0:
            
            self._show_some_dupes.setEnabled( True )
            self._launch_filter.setEnabled( True )
            
        else:
            
            self._show_some_dupes.setEnabled( False )
            self._launch_filter.setEnabled( False )
            
        
    
    def _UpdateFilterSearchControls( self ):
        
        ( file_search_context_1, file_search_context_2, dupe_search_type, pixel_dupes_preference, max_hamming_distance ) = self._GetDuplicateFileSearchData( optimise_for_search = False )
        
        self._tag_autocomplete_2.setVisible( dupe_search_type == CC.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES )
        
        self._max_hamming_distance_for_filter.setEnabled( self._pixel_dupes_preference.GetValue() != CC.SIMILAR_FILES_PIXEL_DUPES_REQUIRED )
        
    
    def FilterDupeSearchTypeChanged( self ):
        
        self._FilterSearchDomainUpdated()
        
    
    def FilterSearchDomainChanged( self ):
        
        self._FilterSearchDomainUpdated()
        
    
    def MaxHammingDistanceForPotentialDiscoveryChanged( self ):
        
        search_distance = self._max_hamming_distance_for_potential_discovery_spinctrl.value()
        
        self._controller.new_options.SetInteger( 'similar_files_duplicate_pairs_search_distance', search_distance )
        
        self._controller.pub( 'new_similar_files_maintenance_numbers' )
        
        self._UpdateMaintenanceStatus()
        
    
    def NotifyNewMaintenanceNumbers( self ):
        
        self._maintenance_numbers_need_redrawing = True
        
    
    def NotifyNewPotentialsSearchNumbers( self ):
        
        self._dupe_count_numbers_dirty = True
        
    
    def PageHidden( self ):
        
        ManagementPanel.PageHidden( self )
        
        self._tag_autocomplete_1.SetForceDropdownHide( True )
        
    
    def PageShown( self ):
        
        ManagementPanel.PageShown( self )
        
        self._tag_autocomplete_1.SetForceDropdownHide( False )
        
    
    def RefreshDuplicateNumbers( self ):
        
        self._dupe_count_numbers_dirty = True
        
    
    def RefreshQuery( self ):
        
        self._FilterSearchDomainUpdated()
        
    
    def REPEATINGPageUpdate( self ):
        
        if self._maintenance_numbers_need_redrawing:
            
            ( self._similar_files_maintenance_status, self._duplicates_manager_is_fetching_maintenance_numbers, self._potential_file_search_currently_happening ) = self._duplicates_manager.GetMaintenanceNumbers()
            
            self._maintenance_numbers_need_redrawing = False
            
            self._UpdateMaintenanceStatus()
            
        
        if self._dupe_count_numbers_dirty:
            
            self._RefreshDuplicateCounts()
            
        
        self._tag_autocomplete_1.REPEATINGPageUpdate()
        self._tag_autocomplete_2.REPEATINGPageUpdate()
        
    
    def Search1Changed( self, file_search_context: ClientSearch.FileSearchContext ):
        
        self._tag_autocomplete_2.blockSignals( True )
        
        self._tag_autocomplete_2.SetLocationContext( self._tag_autocomplete_1.GetLocationContext() )
        self._tag_autocomplete_2.SetSynchronised( self._tag_autocomplete_1.IsSynchronised() )
        
        self._tag_autocomplete_2.blockSignals( False )
        
        self._FilterSearchDomainUpdated()
        
    
    def Search2Changed( self, file_search_context: ClientSearch.FileSearchContext ):
        
        self._tag_autocomplete_1.blockSignals( True )
        
        self._tag_autocomplete_1.SetLocationContext( self._tag_autocomplete_2.GetLocationContext() )
        self._tag_autocomplete_1.SetSynchronised( self._tag_autocomplete_2.IsSynchronised() )
        
        self._tag_autocomplete_1.blockSignals( False )
        
        self._FilterSearchDomainUpdated()
        
    

management_panel_types_to_classes[ ClientGUIManagementController.MANAGEMENT_TYPE_DUPLICATE_FILTER ] = ManagementPanelDuplicateFilter

class ManagementPanelImporter( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
    
    def _UpdateImportStatus( self ):
        
        raise NotImplementedError()
        
    
    def PageShown( self ):
        
        ManagementPanel.PageShown( self )
        
        self._UpdateImportStatus()
        
    
    def RefreshQuery( self ):
        
        self._media_sort_widget.BroadcastSort()
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateImportStatus()
        
    
class ManagementPanelImporterHDD( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self, 'imports' )
        
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel, ellipsize_end = True )
        
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._controller, self._page_key )
        
        self._pause_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.global_pixmaps().file_pause, self.Pause )
        self._pause_button.setToolTip( 'pause/play imports' )
        
        self._hdd_import: ClientImportLocal.HDDImport = self._management_controller.GetVariable( 'hdd_import' )
        
        file_import_options = self._hdd_import.GetFileImportOptions()
        
        show_downloader_options = False
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._current_action, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._pause_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._import_queue_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        file_seed_cache = self._hdd_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        self._UpdateImportStatus()
        
        self._import_options_button.fileImportOptionsChanged.connect( self._hdd_import.SetFileImportOptions )
        
    
    def _UpdateImportStatus( self ):
        
        ( current_action, paused ) = self._hdd_import.GetStatus()
        
        if paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.global_pixmaps().file_play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.global_pixmaps().file_pause )
            
        
        self._current_action.setText( current_action )
        
    
    def CheckAbleToClose( self ):
        
        if self._hdd_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def Pause( self ):
        
        self._hdd_import.PausePlay()
        
        self._UpdateImportStatus()
        
    
    def Start( self ):
        
        self._hdd_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ ClientGUIManagementController.MANAGEMENT_TYPE_IMPORT_HDD ] = ManagementPanelImporterHDD

class ManagementPanelImporterMultipleGallery( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._last_time_imports_changed = 0
        self._next_update_time = 0
        
        self._multiple_gallery_import = self._management_controller.GetVariable( 'multiple_gallery_import' )
        
        self._highlighted_gallery_import = self._multiple_gallery_import.GetHighlightedGalleryImport()
        
        self._loading_highlight_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._loading_highlight_job_status.Finish()
        
        #
        
        self._gallery_downloader_panel = ClientGUICommon.StaticBox( self, 'gallery downloader' )
        
        #
        
        self._gallery_importers_status_st_top = ClientGUICommon.BetterStaticText( self._gallery_downloader_panel, ellipsize_end = True )
        self._gallery_importers_status_st_bottom = ClientGUICommon.BetterStaticText( self._gallery_downloader_panel, ellipsize_end = True )
        
        self._gallery_importers_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._gallery_downloader_panel )
        
        self._gallery_importers_listctrl = ClientGUIListCtrl.BetterListCtrl( self._gallery_importers_listctrl_panel, CGLC.COLUMN_LIST_GALLERY_IMPORTERS.ID, 4, self._ConvertDataToListCtrlTuples, delete_key_callback = self._RemoveGalleryImports, activation_callback = self._HighlightSelectedGalleryImport )
        
        self._gallery_importers_listctrl_panel.SetListCtrl( self._gallery_importers_listctrl )
        
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().highlight, self._HighlightSelectedGalleryImport, tooltip = 'highlight', enabled_check_func = self._CanHighlight )
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().clear_highlight, self._ClearExistingHighlightAndPanel, tooltip = 'clear highlight', enabled_check_func = self._CanClearHighlight )
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().file_pause, self._PausePlayFiles, tooltip = 'pause/play files', enabled_only_on_selection = True )
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().gallery_pause, self._PausePlayGallery, tooltip = 'pause/play search', enabled_only_on_selection = True )
        self._gallery_importers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().trash, self._RemoveGalleryImports, tooltip = 'remove selected', enabled_only_on_selection = True )
        
        self._gallery_importers_listctrl_panel.NewButtonRow()
        
        self._gallery_importers_listctrl_panel.AddButton( 'retry failed', self._RetryFailed, enabled_check_func = self._CanRetryFailed )
        self._gallery_importers_listctrl_panel.AddButton( 'retry ignored', self._RetryIgnored, enabled_check_func = self._CanRetryIgnored )
        
        self._gallery_importers_listctrl_panel.NewButtonRow()
        
        self._gallery_importers_listctrl_panel.AddButton( 'set options to queries', self._SetOptionsToGalleryImports, enabled_only_on_selection = True )
        
        self._gallery_importers_listctrl.Sort()
        
        #
        
        self._query_input = ClientGUIControls.TextAndPasteCtrl( self._gallery_downloader_panel, self._PendQueries )
        
        self._cog_button = ClientGUICommon.BetterBitmapButton( self._gallery_downloader_panel, CC.global_pixmaps().cog, self._ShowCogMenu )
        
        self._gug_key_and_name = ClientGUIImport.GUGKeyAndNameSelector( self._gallery_downloader_panel, self._multiple_gallery_import.GetGUGKeyAndName(), update_callable = self._SetGUGKeyAndName )
        
        self._file_limit = ClientGUICommon.NoneableSpinCtrl( self._gallery_downloader_panel, 'stop after this many files', min = 1, none_phrase = 'no limit' )
        self._file_limit.valueChanged.connect( self.EventFileLimit )
        self._file_limit.setToolTip( 'per query, stop searching the gallery once this many files has been reached' )
        
        file_import_options = self._multiple_gallery_import.GetFileImportOptions()
        tag_import_options = self._multiple_gallery_import.GetTagImportOptions()
        note_import_options = self._multiple_gallery_import.GetNoteImportOptions()
        file_limit = self._multiple_gallery_import.GetFileLimit()
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        self._import_options_button.SetNoteImportOptions( note_import_options )
        
        #
        
        input_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( input_hbox, self._query_input, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( input_hbox, self._cog_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._gallery_downloader_panel.Add( self._gallery_importers_status_st_top, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gallery_importers_status_st_bottom, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gallery_importers_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._gallery_downloader_panel.Add( input_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._gug_key_and_name, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._file_limit, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_downloader_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._highlighted_gallery_import_panel = ClientGUIImport.GalleryImportPanel( self, self._page_key, name = 'highlighted query' )
        
        self._highlighted_gallery_import_panel.SetGalleryImport( self._highlighted_gallery_import )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._gallery_downloader_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._highlighted_gallery_import_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
        
        self._query_input.setPlaceholderText( initial_search_text )
        
        self._file_limit.SetValue( file_limit )
        
        self._UpdateImportStatus()
        
        self._gallery_importers_listctrl.AddRowsMenuCallable( self._GetListCtrlMenu )
        
        self._import_options_button.fileImportOptionsChanged.connect( self._multiple_gallery_import.SetFileImportOptions )
        self._import_options_button.noteImportOptionsChanged.connect( self._multiple_gallery_import.SetNoteImportOptions )
        self._import_options_button.tagImportOptionsChanged.connect( self._multiple_gallery_import.SetTagImportOptions )
        
    
    def _CanClearHighlight( self ):
        
        return self._highlighted_gallery_import is not None or not self._loading_highlight_job_status.IsDone()
        
    
    def _CanHighlight( self ):
        
        selected = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return False
            
        
        gallery_import = selected[0]
        
        return not self._ThisIsTheCurrentOrLoadingHighlight( gallery_import )
        
    
    def _CanRetryFailed( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            if gallery_import.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _CanRetryIgnored( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            if gallery_import.CanRetryIgnored():
                
                return True
                
            
        
        return False
        
    
    def _ClearExistingHighlight( self ):
        
        if not self._loading_highlight_job_status.IsDone():
            
            self._loading_highlight_job_status.Cancel()
            
        
        if self._highlighted_gallery_import is not None:
            
            self._highlighted_gallery_import.PublishToPage( False )
            
            self._highlighted_gallery_import = None
            
            self._multiple_gallery_import.ClearHighlightedGalleryImport()
            
            self._gallery_importers_listctrl_panel.UpdateButtons()
            
            self._highlighted_gallery_import_panel.SetGalleryImport( None )
            
        
    
    def _ClearExistingHighlightAndPanel( self ):
        
        self._ClearExistingHighlight()
        
        media_results = []
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        
        self._SetLocationContext( location_context )
        
        panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, media_results )
        
        panel.SetEmptyPageStatusOverride( 'no highlighted query' )
        
        self._page.SwapMediaPanel( panel )
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _ConvertDataToListCtrlTuples( self, gallery_import ):
        
        query_text = gallery_import.GetQueryText()
        
        pretty_query_text = query_text
        
        if gallery_import == self._highlighted_gallery_import:
            
            pretty_query_text = f'* {pretty_query_text}'
            
        elif not self._loading_highlight_job_status.IsDone():
            
            downloader = self._loading_highlight_job_status.GetIfHasVariable( 'downloader' )
            
            if downloader is not None and gallery_import == downloader:
                
                pretty_query_text = f'> {pretty_query_text}'
                
            
        
        source = gallery_import.GetSourceName()
        
        pretty_source = source
        
        files_finished = gallery_import.FilesFinished()
        files_paused = gallery_import.FilesPaused()
        
        if files_finished:
            
            pretty_files_paused = CG.client_controller.new_options.GetString( 'stop_character' )
            
            sort_files_paused = -1
            
        elif files_paused:
            
            pretty_files_paused = CG.client_controller.new_options.GetString( 'pause_character' )
            
            sort_files_paused = 0
            
        else:
            
            pretty_files_paused = ''
            
            sort_files_paused = 1
            
        
        gallery_finished = gallery_import.GalleryFinished()
        gallery_paused = gallery_import.GalleryPaused()
        
        if gallery_finished:
            
            pretty_gallery_paused = CG.client_controller.new_options.GetString( 'stop_character' )
            
            sort_gallery_paused = -1
            
        elif gallery_paused:
            
            pretty_gallery_paused = CG.client_controller.new_options.GetString( 'pause_character' )
            
            sort_gallery_paused = 0
            
        else:
            
            pretty_gallery_paused = ''
            
            sort_gallery_paused = 1
            
        
        ( status_enum, pretty_status ) = gallery_import.GetSimpleStatus()
        
        sort_status = ClientImporting.downloader_enum_sort_lookup[ status_enum ]
        
        file_seed_cache_status = gallery_import.GetFileSeedCache().GetStatus()
        
        ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
        
        progress = ( num_total, num_done )
        
        pretty_progress = file_seed_cache_status.GetStatusText( simple = True )
        
        added = gallery_import.GetCreationTime()
        
        pretty_added = ClientTime.TimestampToPrettyTimeDelta( added, show_seconds = False )
        
        display_tuple = ( pretty_query_text, pretty_source, pretty_files_paused, pretty_gallery_paused, pretty_status, pretty_progress, pretty_added )
        sort_tuple = ( query_text, pretty_source, sort_files_paused, sort_gallery_paused, sort_status, progress, added )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedQueries( self ):
        
        gallery_importers = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_importers ) > 0:
            
            text = os.linesep.join( ( gallery_importer.GetQueryText() for gallery_importer in gallery_importers ) )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _GetDefaultEmptyPageStatusOverride( self ) -> str:
        
        return 'no highlighted query'
        
    
    def _GetListCtrlMenu( self ):
        
        selected_importers = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected_importers ) == 0:
            
            raise HydrusExceptions.DataMissing()
            
        
        menu = ClientGUIMenus.GenerateMenu( self )

        ClientGUIMenus.AppendMenuItem( menu, 'copy queries', 'Copy all the selected downloaders\' queries to clipboard.', self._CopySelectedQueries )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        single_selected_presentation_import_options = None
        
        if len( selected_importers ) == 1:
            
            ( importer, ) = selected_importers
            
            fio = importer.GetFileImportOptions()
            
            single_selected_presentation_import_options = FileImportOptions.GetRealPresentationImportOptions( fio, FileImportOptions.IMPORT_TYPE_LOUD )
            
        
        AddPresentationSubmenu( menu, 'downloader', single_selected_presentation_import_options, self._ShowSelectedImportersFiles )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if len( selected_importers ) == 1:
            
            ( importer, ) = selected_importers
            
            file_seed_cache = importer.GetFileSeedCache()
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'show file log', 'Show the file log windows for the selected query.', self._ShowSelectedImportersFileSeedCaches )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIFileSeedCache.PopulateFileSeedCacheMenu( self, submenu, file_seed_cache )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'file log' )
            
            gallery_seed_log = importer.GetGallerySeedLog()
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'show search log', 'Show the search log windows for the selected query.', self._ShowSelectedImportersGallerySeedLogs )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIGallerySeedLog.PopulateGallerySeedLogButton( self, submenu, gallery_seed_log, False, True, 'search' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'search log' )
            
        else:
            
            ClientGUIMenus.AppendMenuItem( menu, 'show file logs', 'Show the file log windows for the selected queries.', self._ShowSelectedImportersFileSeedCaches )
            ClientGUIMenus.AppendMenuItem( menu, 'show search log', 'Show the search log windows for the selected query.', self._ShowSelectedImportersGallerySeedLogs )
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'remove', 'Remove the selected queries.', self._RemoveGalleryImports )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play files', 'Pause/play all the selected downloaders\' file queues.', self._PausePlayFiles )
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play search', 'Pause/play all the selected downloaders\' gallery searches.', self._PausePlayGallery )
        
        return menu
        
    
    def _HighlightGalleryImport( self, new_highlight ):
        
        if self._ThisIsTheCurrentOrLoadingHighlight( new_highlight ):
            
            self._ClearExistingHighlightAndPanel()
            
        else:
            
            self._ClearExistingHighlight()
            
            self._loading_highlight_job_status = ClientThreading.JobStatus( cancellable = True )
            
            name = new_highlight.GetQueryText()
            
            self._loading_highlight_job_status.SetStatusTitle( f'Loading {name}' )
            
            self._loading_highlight_job_status.SetVariable( 'downloader', new_highlight )
            
            self._gallery_importers_listctrl_panel.UpdateButtons()
            
            self._gallery_importers_listctrl.UpdateDatas()
            
            job_status = self._loading_highlight_job_status
            hashes = new_highlight.GetPresentedHashes()
            
            num_to_do = len( hashes )
            
            if num_to_do > 0:
                
                panel = ClientGUIResults.MediaPanelLoading( self._page, self._page_key, self._management_controller )
                
                self._page.SwapMediaPanel( panel )
                
            
            def work_callable():
                
                BLOCK_SIZE = 256
                
                start_time = HydrusTime.GetNowFloat()
                have_published_job_status = False
                
                all_media_results = []
                
                for ( i, block_of_hashes ) in enumerate( HydrusData.SplitIteratorIntoChunks( hashes, BLOCK_SIZE ) ):
                    
                    num_done = i * BLOCK_SIZE
                    
                    job_status.SetStatusText( 'Loading files: {}'.format( HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ) ) )
                    job_status.SetVariable( 'popup_gauge_1', ( num_done, num_to_do ) )
                    
                    if not have_published_job_status and HydrusTime.TimeHasPassedFloat( start_time + 3 ):
                        
                        CG.client_controller.pub( 'message', job_status )
                        
                        have_published_job_status = True
                        
                    
                    if job_status.IsCancelled():
                        
                        return all_media_results
                        
                    
                    block_of_media_results = CG.client_controller.Read( 'media_results', block_of_hashes, sorted = True )
                    
                    all_media_results.extend( block_of_media_results )
                    
                
                job_status.SetStatusText( 'Done!' )
                job_status.DeleteVariable( 'popup_gauge_1' )
                
                return all_media_results
                
            
            def publish_callable( media_results ):
                
                try:
                    
                    if job_status != self._loading_highlight_job_status or job_status.IsCancelled():
                        
                        return
                        
                    
                    self._highlighted_gallery_import = new_highlight
                    
                    self._multiple_gallery_import.SetHighlightedGalleryImport( self._highlighted_gallery_import )
                    
                    self._highlighted_gallery_import.PublishToPage( True )
                    
                    location_context = FileImportOptions.GetRealFileImportOptions( self._highlighted_gallery_import.GetFileImportOptions(), FileImportOptions.IMPORT_TYPE_LOUD ).GetDestinationLocationContext()
                    
                    self._SetLocationContext( location_context )
                    
                    panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, media_results )
                    
                    panel.SetEmptyPageStatusOverride( 'no files for this query and its publishing settings' )
                    
                    self._page.SwapMediaPanel( panel )
                    
                    self._highlighted_gallery_import_panel.SetGalleryImport( self._highlighted_gallery_import )
                    
                finally:
                    
                    self._gallery_importers_listctrl_panel.UpdateButtons()
                    
                    self._gallery_importers_listctrl.UpdateDatas()
                    
                    job_status.FinishAndDismiss()
                    
                
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            job.start()
            
        
    
    def _HighlightSelectedGalleryImport( self ):
        
        selected = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            new_highlight = selected[0]
            
            self._HighlightGalleryImport( new_highlight )
            
        
    
    def _PausePlayFiles( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.PausePlayFiles()
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _PausePlayGallery( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.PausePlayGallery()
            
        
        self._gallery_importers_listctrl.UpdateDatas()
        
    
    def _PendQueries( self, queries ):
        
        results = self._multiple_gallery_import.PendQueries( queries )
        
        if len( results ) > 0 and self._highlighted_gallery_import is None and CG.client_controller.new_options.GetBoolean( 'highlight_new_query' ):
            
            first_result = results[ 0 ]
            
            self._HighlightGalleryImport( first_result )
            
        
        self._UpdateImportStatusNow()
        
    
    def _RemoveGalleryImports( self ):
        
        removees = list( self._gallery_importers_listctrl.GetData( only_selected = True ) )
        
        if len( removees ) == 0:
            
            return
            
        
        num_working = 0
        
        for gallery_import in removees:
            
            if gallery_import.CurrentlyWorking():
                
                num_working += 1
                
            
        
        message = 'Remove the ' + HydrusData.ToHumanInt( len( removees ) ) + ' selected queries?'
        
        if num_working > 0:
            
            message += os.linesep * 2
            message += HydrusData.ToHumanInt( num_working ) + ' are still working.'
            
        
        if self._highlighted_gallery_import is not None and self._highlighted_gallery_import in removees:
            
            message += os.linesep * 2
            message += 'The currently highlighted query will be removed, and the media panel cleared.'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            highlight_was_included = False
            
            for gallery_import in removees:
                
                if self._ThisIsTheCurrentOrLoadingHighlight( gallery_import ):
                    
                    highlight_was_included = True
                    
                
                self._multiple_gallery_import.RemoveGalleryImport( gallery_import.GetGalleryImportKey() )
                
            
            if highlight_was_included:
                
                self._ClearExistingHighlightAndPanel()
                
            
        
        self._UpdateImportStatusNow()
        
    
    def _RetryFailed( self ):
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.RetryFailed()
            
        
    
    def _RetryIgnored( self ):
        
        try:
            
            ignored_regex = ClientGUIFileSeedCache.GetRetryIgnoredParam( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for gallery_import in self._gallery_importers_listctrl.GetData( only_selected = True ):
            
            gallery_import.RetryIgnored( ignored_regex = ignored_regex )
            
        
    
    def _SetGUGKeyAndName( self, gug_key_and_name ):
        
        current_initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
        
        current_input_value = self._query_input.GetValue()
        
        should_initialise_new_text = current_input_value in ( current_initial_search_text, '' )
        
        self._multiple_gallery_import.SetGUGKeyAndName( gug_key_and_name )
        
        if should_initialise_new_text:
            
            new_initial_search_text = self._multiple_gallery_import.GetInitialSearchText()
            
            self._query_input.setPlaceholderText( new_initial_search_text )
            
        
        self._query_input.setFocus( QC.Qt.OtherFocusReason )
        
    
    def _SetOptionsToGalleryImports( self ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        message = 'Set the current file limit, file import, and tag import options to all the selected queries? (by default, these options are only applied to new queries)'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            file_limit = self._file_limit.GetValue()
            file_import_options = self._import_options_button.GetFileImportOptions()
            tag_import_options = self._import_options_button.GetTagImportOptions()
            note_import_options = self._import_options_button.GetNoteImportOptions()
            
            for gallery_import in gallery_imports:
                
                gallery_import.SetFileLimit( file_limit )
                gallery_import.SetFileImportOptions( file_import_options )
                gallery_import.SetTagImportOptions( tag_import_options )
                gallery_import.SetNoteImportOptions( note_import_options )
                
            
        
    
    def _ShowCogMenu( self ):
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        start_file_queues_paused = self._multiple_gallery_import.GetStartFileQueuesPaused()
        start_gallery_queues_paused = self._multiple_gallery_import.GetStartGalleryQueuesPaused()
        do_not_allow_new_dupes = self._multiple_gallery_import.GetDoNotAllowNewDupes()
        merge_simultaneous_pends_to_one_importer = self._multiple_gallery_import.GetMergeSimultaneousPendsToOneImporter()
        
        ClientGUIMenus.AppendMenuCheckItem( menu, 'start new importers\' files paused', 'Start any new importers in a file import-paused state.', start_file_queues_paused, self._multiple_gallery_import.SetStartFileQueuesPaused, not start_file_queues_paused )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'start new importers\' search paused', 'Start any new importers in a gallery search-paused state.', start_gallery_queues_paused, self._multiple_gallery_import.SetStartGalleryQueuesPaused, not start_gallery_queues_paused )
        ClientGUIMenus.AppendSeparator( menu )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'do not allow new duplicates', 'This will discard any query/source pair you try to add that is already in the list.', do_not_allow_new_dupes, self._multiple_gallery_import.SetDoNotAllowNewDupes, not do_not_allow_new_dupes )
        ClientGUIMenus.AppendMenuCheckItem( menu, 'bundle multiple pasted queries into one importer (advanced)', 'If you are pasting many small queries at once (such as md5 lookups), check this to smooth out the workflow.', merge_simultaneous_pends_to_one_importer, self._multiple_gallery_import.SetMergeSimultaneousPendsToOneImporter, not merge_simultaneous_pends_to_one_importer )
        
        CGC.core().PopupMenu( self._cog_button, menu )
        
    
    def _ShowSelectedImportersFileSeedCaches( self ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        gallery_import = gallery_imports[0]
        
        file_seed_cache = gallery_import.GetFileSeedCache()
        
        title = 'file log'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIFileSeedCache.EditFileSeedCachePanel( frame, CG.client_controller, file_seed_cache )
        
        frame.SetPanel( panel )
        
    
    def _ShowSelectedImportersFiles( self, presentation_import_options = None ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        hashes = list()
        seen_hashes = set()
        
        for gallery_import in gallery_imports:
            
            gallery_hashes = gallery_import.GetPresentedHashes( presentation_import_options = presentation_import_options )
            
            new_hashes = [ hash for hash in gallery_hashes if hash not in seen_hashes ]
            
            hashes.extend( new_hashes )
            seen_hashes.update( new_hashes )
            
        
        if len( hashes ) > 0:
            
            self._ClearExistingHighlightAndPanel()
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
            
            self._SetLocationContext( location_context )
            
            panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, media_results )
            
            self._page.SwapMediaPanel( panel )
            
        else:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'No presented files for that selection!' )
            
        
    
    def _ShowSelectedImportersGallerySeedLogs( self ):
        
        gallery_imports = self._gallery_importers_listctrl.GetData( only_selected = True )
        
        if len( gallery_imports ) == 0:
            
            return
            
        
        gallery_import = gallery_imports[0]
        
        gallery_seed_log = gallery_import.GetGallerySeedLog()
        
        title = 'search log'
        frame_key = 'gallery_import_log'
        
        read_only = False
        can_generate_more_pages = True
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIGallerySeedLog.EditGallerySeedLogPanel( frame, CG.client_controller, read_only, can_generate_more_pages, 'search', gallery_seed_log )
        
        frame.SetPanel( panel )
        
    
    def _ThisIsTheCurrentOrLoadingHighlight( self, gallery_import ):
        
        if self._highlighted_gallery_import is not None and gallery_import == self._highlighted_gallery_import:
            
            return True
            
        else:
            
            if not self._loading_highlight_job_status.IsDone():
                
                downloader = self._loading_highlight_job_status.GetIfHasVariable( 'downloader' )
                
                if downloader is not None and downloader == gallery_import:
                    
                    return True
                    
                
            
            return False
            
        
    
    def _UpdateImportStatus( self ):
        
        if HydrusTime.TimeHasPassed( self._next_update_time ):
            
            num_items = len( self._gallery_importers_listctrl.GetData() )
            
            update_period = max( 1, int( ( num_items / 10 ) ** 0.33 ) )
            
            self._next_update_time = HydrusTime.GetNow() + update_period
            
            #
            
            last_time_imports_changed = self._multiple_gallery_import.GetLastTimeImportsChanged()
            
            num_gallery_imports = self._multiple_gallery_import.GetNumGalleryImports()
            
            #
            
            if num_gallery_imports == 0:
                
                text_top = 'waiting for new queries'
                text_bottom = ''
                
            else:
                
                file_seed_cache_status = self._multiple_gallery_import.GetTotalStatus()
                
                ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
                
                text_top = '{} queries - {}'.format( HydrusData.ToHumanInt( num_gallery_imports ), HydrusData.ConvertValueRangeToPrettyString( num_done, num_total ) )
                text_bottom = file_seed_cache_status.GetStatusText()
                
            
            self._gallery_importers_status_st_top.setText( text_top )
            self._gallery_importers_status_st_bottom.setText( text_bottom )
            
            #
            
            if self._last_time_imports_changed != last_time_imports_changed:
                
                self._last_time_imports_changed = last_time_imports_changed
                
                gallery_imports = self._multiple_gallery_import.GetGalleryImports()
                
                self._gallery_importers_listctrl.SetData( gallery_imports )
                
                ideal_rows = len( gallery_imports )
                ideal_rows = max( 4, ideal_rows )
                ideal_rows = min( ideal_rows, 24 )
                
                self._gallery_importers_listctrl.ForceHeight( ideal_rows )
                
            else:
                
                sort_data_has_changed = self._gallery_importers_listctrl.UpdateDatas()
                
                if sort_data_has_changed:
                    
                    self._gallery_importers_listctrl.Sort()
                    
                
            
        
    
    def _UpdateImportStatusNow( self ):
        
        self._next_update_time = 0
        
        self._UpdateImportStatus()
        
    
    def CheckAbleToClose( self ):
        
        num_working = 0
        
        for gallery_import in self._multiple_gallery_import.GetGalleryImports():
            
            if gallery_import.CurrentlyWorking():
                
                num_working += 1
                
            
        
        if num_working > 0:
            
            raise HydrusExceptions.VetoException( HydrusData.ToHumanInt( num_working ) + ' queries are still importing.' )
            
        
    
    def EventFileLimit( self ):
        
        self._multiple_gallery_import.SetFileLimit( self._file_limit.GetValue() )
        
    
    def PendSubscriptionGapDownloader( self, gug_key_and_name, query_text, file_import_options, tag_import_options, note_import_options, file_limit ):
        
        new_query = self._multiple_gallery_import.PendSubscriptionGapDownloader( gug_key_and_name, query_text, file_import_options, tag_import_options, note_import_options, file_limit )
        
        if new_query is not None and self._highlighted_gallery_import is None and CG.client_controller.new_options.GetBoolean( 'highlight_new_query' ):
            
            self._HighlightGalleryImport( new_query )
            
        
    
    def SetSearchFocus( self ):
        
        ClientGUIFunctions.SetFocusLater( self._query_input )
        
    
    def Start( self ):
        
        self._multiple_gallery_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ ClientGUIManagementController.MANAGEMENT_TYPE_IMPORT_MULTIPLE_GALLERY ] = ManagementPanelImporterMultipleGallery

class ManagementPanelImporterMultipleWatcher( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._last_time_watchers_changed = 0
        self._next_update_time = 0
        
        self._multiple_watcher_import = self._management_controller.GetVariable( 'multiple_watcher_import' )
        
        self._highlighted_watcher = self._multiple_watcher_import.GetHighlightedWatcher()
        
        self._loading_highlight_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._loading_highlight_job_status.Finish()
        
        checker_options = self._multiple_watcher_import.GetCheckerOptions()
        file_import_options = self._multiple_watcher_import.GetFileImportOptions()
        tag_import_options = self._multiple_watcher_import.GetTagImportOptions()
        note_import_options = self._multiple_watcher_import.GetNoteImportOptions()
        
        #
        
        self._watchers_panel = ClientGUICommon.StaticBox( self, 'watchers' )
        
        self._watchers_status_st_top = ClientGUICommon.BetterStaticText( self._watchers_panel, ellipsize_end = True )
        self._watchers_status_st_bottom = ClientGUICommon.BetterStaticText( self._watchers_panel, ellipsize_end = True )
        
        self._watchers_listctrl_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._watchers_panel )
        
        self._watchers_listctrl = ClientGUIListCtrl.BetterListCtrl( self._watchers_listctrl_panel, CGLC.COLUMN_LIST_WATCHERS.ID, 4, self._ConvertDataToListCtrlTuples, delete_key_callback = self._RemoveWatchers, activation_callback = self._HighlightSelectedWatcher )
        
        self._watchers_listctrl_panel.SetListCtrl( self._watchers_listctrl )
        
        self._watchers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().highlight, self._HighlightSelectedWatcher, tooltip = 'highlight', enabled_check_func = self._CanHighlight )
        self._watchers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().clear_highlight, self._ClearExistingHighlightAndPanel, tooltip = 'clear highlight', enabled_check_func = self._CanClearHighlight )
        self._watchers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().file_pause, self._PausePlayFiles, tooltip = 'pause/play files', enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().gallery_pause, self._PausePlayChecking, tooltip = 'pause/play checking', enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddBitmapButton( CC.global_pixmaps().trash, self._RemoveWatchers, tooltip = 'remove selected', enabled_only_on_selection = True )
        self._watchers_listctrl_panel.AddButton( 'check now', self._CheckNow, enabled_only_on_selection = True )
        
        self._watchers_listctrl_panel.NewButtonRow()
        
        self._watchers_listctrl_panel.AddButton( 'retry failed', self._RetryFailed, enabled_check_func = self._CanRetryFailed )
        self._watchers_listctrl_panel.AddButton( 'retry ignored', self._RetryIgnored, enabled_check_func = self._CanRetryIgnored )
        
        self._watchers_listctrl_panel.NewButtonRow()
        
        self._watchers_listctrl_panel.AddButton( 'set options to watchers', self._SetOptionsToWatchers, enabled_only_on_selection = True )
        
        self._watchers_listctrl.Sort()
        
        self._watcher_url_input = ClientGUIControls.TextAndPasteCtrl( self._watchers_panel, self._AddURLs )
        
        self._watcher_url_input.setPlaceholderText( 'watcher url' )
        
        self._checker_options = ClientGUIImport.CheckerOptionsButton( self._watchers_panel, checker_options )
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        self._import_options_button.SetNoteImportOptions( note_import_options )
        
        # suck up watchers from elsewhere in the program (presents a checkboxlistdialog)
        
        #
        
        self._highlighted_watcher_panel = ClientGUIImport.WatcherReviewPanel( self, self._page_key, name = 'highlighted watcher' )
        
        self._highlighted_watcher_panel.SetWatcher( self._highlighted_watcher )
        
        #
        
        self._watchers_panel.Add( self._watchers_status_st_top, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_status_st_bottom, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._watchers_listctrl_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._watchers_panel.Add( self._watcher_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._checker_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._watchers_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._watchers_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( vbox, self._highlighted_watcher_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._watchers_listctrl.AddRowsMenuCallable( self._GetListCtrlMenu )
        
        self._UpdateImportStatus()
        
        CG.client_controller.sub( self, '_ClearExistingHighlightAndPanel', 'clear_multiwatcher_highlights' )
        
        self._import_options_button.fileImportOptionsChanged.connect( self._OptionsUpdated )
        self._import_options_button.noteImportOptionsChanged.connect( self._OptionsUpdated )
        self._import_options_button.tagImportOptionsChanged.connect( self._OptionsUpdated )
        
        self._checker_options.valueChanged.connect( self._OptionsUpdated )
        
    
    def _AddURLs( self, urls, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        first_result = None
        
        for url in urls:
            
            result = self._multiple_watcher_import.AddURL( url, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
            
            if result is not None and first_result is None:
                
                first_result = result
                
            
        
        if first_result is not None and self._highlighted_watcher is None and CG.client_controller.new_options.GetBoolean( 'highlight_new_watcher' ):
            
            self._HighlightWatcher( first_result )
            
        
        self._UpdateImportStatusNow()
        
    
    def _CanClearHighlight( self ):
        
        return self._highlighted_watcher is not None or not self._loading_highlight_job_status.IsDone()
        
    
    def _CanHighlight( self ):
        
        selected = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected ) != 1:
            
            return False
            
        
        watcher = selected[0]
        
        return not self._ThisIsTheCurrentOrLoadingHighlight( watcher )
        
    
    def _CanRetryFailed( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            if watcher.CanRetryFailed():
                
                return True
                
            
        
        return False
        
    
    def _CanRetryIgnored( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            if watcher.CanRetryIgnored():
                
                return True
                
            
        
        return False
        
    
    def _CheckNow( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.CheckNow()
            
        
    
    def _ClearExistingHighlight( self ):
        
        if not self._loading_highlight_job_status.IsDone():
            
            self._loading_highlight_job_status.Cancel()
            
        
        if self._highlighted_watcher is not None:
            
            self._highlighted_watcher.PublishToPage( False )
            
            self._highlighted_watcher = None
            
            self._multiple_watcher_import.ClearHighlightedWatcher()
            
            self._watchers_listctrl_panel.UpdateButtons()
            
            self._highlighted_watcher_panel.SetWatcher( None )
            
        
    
    def _ClearExistingHighlightAndPanel( self ):
        
        self._ClearExistingHighlight()
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
        
        media_results = []
        
        self._SetLocationContext( location_context )
        
        panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, media_results )
        
        panel.SetEmptyPageStatusOverride( 'no highlighted watcher' )
        
        self._page.SwapMediaPanel( panel )
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _ConvertDataToListCtrlTuples( self, watcher: ClientImportWatchers.WatcherImport ):
        
        subject = watcher.GetSubject()
        
        pretty_subject = subject
        
        if watcher == self._highlighted_watcher:
            
            pretty_subject = f'* {pretty_subject}'
            
        elif not self._loading_highlight_job_status.IsDone():
            
            downloader = self._loading_highlight_job_status.GetIfHasVariable( 'downloader' )
            
            if downloader is not None and downloader == watcher:
                
                pretty_subject = f'> {pretty_subject}'
                
            
        
        files_paused = watcher.FilesPaused()
        
        if files_paused:
            
            pretty_files_paused = CG.client_controller.new_options.GetString( 'pause_character' )
            
        else:
            
            pretty_files_paused = ''
            
        
        checking_dead = watcher.IsDead()
        checking_paused = watcher.CheckingPaused()
        
        if checking_dead:
            
            pretty_checking_paused = CG.client_controller.new_options.GetString( 'stop_character' )
            
            sort_checking_paused = -1
            
        elif checking_paused:
            
            pretty_checking_paused = CG.client_controller.new_options.GetString( 'pause_character' )
            
            sort_checking_paused = 0
            
        else:
            
            pretty_checking_paused = ''
            
            sort_checking_paused = 1
            
        
        file_seed_cache_status = watcher.GetFileSeedCache().GetStatus()
        
        ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
        
        progress = ( num_total, num_done )
        
        pretty_progress = file_seed_cache_status.GetStatusText( simple = True )
        
        added = watcher.GetCreationTime()
        
        pretty_added = ClientTime.TimestampToPrettyTimeDelta( added, show_seconds = False )
        
        ( status_enum, pretty_watcher_status ) = self._multiple_watcher_import.GetWatcherSimpleStatus( watcher )
        
        checking_status = watcher.GetCheckingStatus()
        
        if checking_status == ClientImporting.CHECKER_STATUS_OK:
            
            next_check_time = watcher.GetNextCheckTime()
            
            if next_check_time is None:
                
                next_check_time = 0
                
            
            sort_watcher_status = ( ClientImporting.downloader_enum_sort_lookup[ status_enum ], next_check_time )
            
        else:
            
            # this lets 404 and DEAD sort different
            
            sort_watcher_status = ( ClientImporting.downloader_enum_sort_lookup[ status_enum ], checking_status )
            
        
        display_tuple = ( pretty_subject, pretty_files_paused, pretty_checking_paused, pretty_watcher_status, pretty_progress, pretty_added )
        sort_tuple = ( subject, files_paused, sort_checking_paused, sort_watcher_status, progress, added )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopySelectedSubjects( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            text = os.linesep.join( ( watcher.GetSubject() for watcher in watchers ) )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _CopySelectedURLs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            text = os.linesep.join( ( watcher.GetURL() for watcher in watchers ) )
            
            CG.client_controller.pub( 'clipboard', 'text', text )
            
        
    
    def _GetDefaultEmptyPageStatusOverride( self ) -> str:
        
        return 'no highlighted watcher'
        
    
    def _GetListCtrlMenu( self ):
        
        selected_watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected_watchers ) == 0:
            
            raise HydrusExceptions.DataMissing()
            
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        ClientGUIMenus.AppendMenuItem( menu, 'copy urls', 'Copy all the selected watchers\' urls to clipboard.', self._CopySelectedURLs )
        ClientGUIMenus.AppendMenuItem( menu, 'open urls', 'Open all the selected watchers\' urls in your browser.', self._OpenSelectedURLs )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'copy subjects', 'Copy all the selected watchers\' subjects to clipboard.', self._CopySelectedSubjects )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        single_selected_presentation_import_options = None
        
        if len( selected_watchers ) == 1:
            
            ( watcher, ) = selected_watchers
            
            fio = watcher.GetFileImportOptions()
            
            single_selected_presentation_import_options = FileImportOptions.GetRealPresentationImportOptions( fio, FileImportOptions.IMPORT_TYPE_LOUD )
            
        
        AddPresentationSubmenu( menu, 'watcher', single_selected_presentation_import_options, self._ShowSelectedImportersFiles )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        if len( selected_watchers ) == 1:
            
            ( watcher, ) = selected_watchers
            
            file_seed_cache = watcher.GetFileSeedCache()
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'show file log', 'Show the file log windows for the selected watcher.', self._ShowSelectedImportersFileSeedCaches )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIFileSeedCache.PopulateFileSeedCacheMenu( self, submenu, file_seed_cache )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'file log' )
            
            gallery_seed_log = watcher.GetGallerySeedLog()
            
            submenu = ClientGUIMenus.GenerateMenu( menu )
            
            ClientGUIMenus.AppendMenuItem( submenu, 'show check log', 'Show the check log windows for the selected watcher.', self._ShowSelectedImportersGallerySeedLogs )
            
            ClientGUIMenus.AppendSeparator( submenu )
            
            ClientGUIGallerySeedLog.PopulateGallerySeedLogButton( self, submenu, gallery_seed_log, True, False, 'check' )
            
            ClientGUIMenus.AppendMenu( menu, submenu, 'check log' )
            
        else:
            
            ClientGUIMenus.AppendMenuItem( menu, 'show file logs', 'Show the file log windows for the selected queries.', self._ShowSelectedImportersFileSeedCaches )
            ClientGUIMenus.AppendMenuItem( menu, 'show check log', 'Show the checker log windows for the selected watcher.', self._ShowSelectedImportersGallerySeedLogs )
            
        
        if self._CanRetryFailed() or self._CanRetryIgnored():
            
            ClientGUIMenus.AppendSeparator( menu )
            
            if self._CanRetryFailed():
                
                ClientGUIMenus.AppendMenuItem( menu, 'retry failed', 'Retry all the failed downloads.', self._RetryFailed )
                
            
            if self._CanRetryIgnored():
                
                ClientGUIMenus.AppendMenuItem( menu, 'retry ignored', 'Retry all the ignored downloads.', self._RetryIgnored )
                
            
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'remove selected', 'Remove the selected watchers.', self._RemoveWatchers )
        
        ClientGUIMenus.AppendSeparator( menu )
        
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play files', 'Pause/play all the selected watchers\' file queues.', self._PausePlayFiles )
        ClientGUIMenus.AppendMenuItem( menu, 'pause/play checking', 'Pause/play all the selected watchers\' checking routines.', self._PausePlayChecking )
        
        return menu
        
    
    def _HighlightWatcher( self, new_highlight ):
        
        if self._ThisIsTheCurrentOrLoadingHighlight( new_highlight ):
            
            self._ClearExistingHighlightAndPanel()
            
        else:
            
            self._ClearExistingHighlight()
            
            self._loading_highlight_job_status = ClientThreading.JobStatus( cancellable = True )
            
            name = new_highlight.GetSubject()
            
            self._loading_highlight_job_status.SetStatusTitle( f'Loading {name}' )
            
            self._loading_highlight_job_status.SetVariable( 'downloader', new_highlight )
            
            self._watchers_listctrl_panel.UpdateButtons()
            
            self._watchers_listctrl.UpdateDatas()
            
            job_status = self._loading_highlight_job_status
            hashes = new_highlight.GetPresentedHashes()
            
            num_to_do = len( hashes )
            
            if num_to_do > 0:
                
                panel = ClientGUIResults.MediaPanelLoading( self._page, self._page_key, self._management_controller )
                
                self._page.SwapMediaPanel( panel )
                
            
            def work_callable():
                
                BLOCK_SIZE = 256
                
                start_time = HydrusTime.GetNowFloat()
                have_published_job_status = False
                
                all_media_results = []
                
                for ( i, block_of_hashes ) in enumerate( HydrusData.SplitIteratorIntoChunks( hashes, BLOCK_SIZE ) ):
                    
                    num_done = i * BLOCK_SIZE
                    
                    job_status.SetStatusText( 'Loading files: {}'.format( HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ) ) )
                    job_status.SetVariable( 'popup_gauge_1', ( num_done, num_to_do ) )
                    
                    if not have_published_job_status and HydrusTime.TimeHasPassedFloat( start_time + 3 ):
                        
                        CG.client_controller.pub( 'message', job_status )
                        
                        have_published_job_status = True
                        
                    
                    if job_status.IsCancelled():
                        
                        return all_media_results
                        
                    
                    block_of_media_results = CG.client_controller.Read( 'media_results', block_of_hashes, sorted = True )
                    
                    all_media_results.extend( block_of_media_results )
                    
                
                job_status.SetStatusText( 'Done!' )
                job_status.DeleteVariable( 'popup_gauge_1' )
                
                return all_media_results
                
            
            def publish_callable( media_results ):
                
                try:
                    
                    if job_status != self._loading_highlight_job_status or job_status.IsCancelled():
                        
                        return
                        
                    
                    self._highlighted_watcher = new_highlight
                    
                    self._multiple_watcher_import.SetHighlightedWatcher( self._highlighted_watcher )
                    
                    self._highlighted_watcher.PublishToPage( True )
                    
                    location_context = FileImportOptions.GetRealFileImportOptions( self._highlighted_watcher.GetFileImportOptions(), FileImportOptions.IMPORT_TYPE_LOUD ).GetDestinationLocationContext()
                    
                    self._SetLocationContext( location_context )
                    
                    panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, media_results )
                    
                    panel.SetEmptyPageStatusOverride( 'no files for this watcher and its publishing settings' )
                    
                    self._page.SwapMediaPanel( panel )
                    
                    self._highlighted_watcher_panel.SetWatcher( self._highlighted_watcher )
                    
                finally:
                    
                    self._watchers_listctrl_panel.UpdateButtons()
                    
                    self._watchers_listctrl.UpdateDatas()
                    
                    job_status.FinishAndDismiss()
                    
                
            
            job = ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable )
            
            job.start()
            
        
    
    def _HighlightSelectedWatcher( self ):
        
        selected = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( selected ) == 1:
            
            new_highlight = selected[0]
            
            self._HighlightWatcher( new_highlight )
            
        
    
    def _OpenSelectedURLs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) > 0:
            
            if len( watchers ) > 10:
                
                message = 'You have many watchers selected--are you sure you want to open them all?'
                
                result = ClientGUIDialogsQuick.GetYesNo( self, message )
                
                if result != QW.QDialog.Accepted:
                    
                    return
                    
                
            
            for watcher in watchers:
                
                ClientPaths.LaunchURLInWebBrowser( watcher.GetURL() )
                
            
        
    
    def _OptionsUpdated( self, *args, **kwargs ):
        
        self._multiple_watcher_import.SetCheckerOptions( self._checker_options.GetValue() )
        self._multiple_watcher_import.SetFileImportOptions( self._import_options_button.GetFileImportOptions() )
        self._multiple_watcher_import.SetNoteImportOptions( self._import_options_button.GetNoteImportOptions() )
        self._multiple_watcher_import.SetTagImportOptions( self._import_options_button.GetTagImportOptions() )
        
    
    def _PausePlayChecking( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.PausePlayChecking()
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _PausePlayFiles( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.PausePlayFiles()
            
        
        self._watchers_listctrl.UpdateDatas()
        
    
    def _RemoveWatchers( self ):
        
        removees = list( self._watchers_listctrl.GetData( only_selected = True ) )
        
        if len( removees ) == 0:
            
            return
            
        
        num_working = 0
        num_alive = 0
        
        for watcher in removees:
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
            if watcher.CurrentlyAlive():
                
                num_alive += 1
                
            
        
        message = 'Remove the ' + HydrusData.ToHumanInt( len( removees ) ) + ' selected watchers?'
        
        if num_working > 0:
            
            message += os.linesep * 2
            message += HydrusData.ToHumanInt( num_working ) + ' are still working.'
            
        
        if num_alive > 0:
            
            message += os.linesep * 2
            message += HydrusData.ToHumanInt( num_alive ) + ' are not yet DEAD.'
            
        
        if self._highlighted_watcher is not None and self._highlighted_watcher in removees:
            
            message += os.linesep * 2
            message += 'The currently highlighted watcher will be removed, and the media panel cleared.'
            
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            highlight_was_included = False
            
            for watcher in removees:
                
                if self._ThisIsTheCurrentOrLoadingHighlight( watcher ):
                    
                    highlight_was_included = True
                    
                
                self._multiple_watcher_import.RemoveWatcher( watcher.GetWatcherKey() )
                
            
            if highlight_was_included:
                
                self._ClearExistingHighlightAndPanel()
                
            
        
        self._UpdateImportStatusNow()
        
    
    def _RetryFailed( self ):
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.RetryFailed()
            
        
    
    def _RetryIgnored( self ):
        
        try:
            
            ignored_regex = ClientGUIFileSeedCache.GetRetryIgnoredParam( self )
            
        except HydrusExceptions.CancelledException:
            
            return
            
        
        for watcher in self._watchers_listctrl.GetData( only_selected = True ):
            
            watcher.RetryIgnored( ignored_regex = ignored_regex )
            
        
    
    def _SetOptionsToWatchers( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        message = 'Set the current checker, file import, and tag import options to all the selected watchers? (by default, these options are only applied to new watchers)'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result == QW.QDialog.Accepted:
            
            checker_options = self._checker_options.GetValue()
            file_import_options = self._import_options_button.GetFileImportOptions()
            tag_import_options = self._import_options_button.GetTagImportOptions()
            
            for watcher in watchers:
                
                watcher.SetCheckerOptions( checker_options )
                watcher.SetFileImportOptions( file_import_options )
                watcher.SetTagImportOptions( tag_import_options )
                
            
        
    
    def _ShowSelectedImportersFileSeedCaches( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        watcher = watchers[0]
        
        file_seed_cache = watcher.GetFileSeedCache()
        
        title = 'file log'
        frame_key = 'file_import_status'
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIFileSeedCache.EditFileSeedCachePanel( frame, CG.client_controller, file_seed_cache )
        
        frame.SetPanel( panel )
        
    
    def _ShowSelectedImportersFiles( self, presentation_import_options = None ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        hashes = list()
        seen_hashes = set()
        
        for watcher in watchers:
            
            watcher_hashes = watcher.GetPresentedHashes( presentation_import_options = presentation_import_options )
            
            new_hashes = [ hash for hash in watcher_hashes if hash not in seen_hashes ]
            
            hashes.extend( new_hashes )
            seen_hashes.update( new_hashes )
            
        
        if len( hashes ) > 0:
            
            self._ClearExistingHighlightAndPanel()
            
            media_results = self._controller.Read( 'media_results', hashes, sorted = True )
            
            location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_MEDIA_SERVICE_KEY )
            
            self._SetLocationContext( location_context )
            
            panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, media_results )
            
            self._page.SwapMediaPanel( panel )
            
        else:
            
            ClientGUIDialogsMessage.ShowWarning( self, 'No presented files for that selection!' )
            
        
    
    def _ShowSelectedImportersGallerySeedLogs( self ):
        
        watchers = self._watchers_listctrl.GetData( only_selected = True )
        
        if len( watchers ) == 0:
            
            return
            
        
        watcher = watchers[0]
        
        gallery_seed_log = watcher.GetGallerySeedLog()
        
        title = 'check log'
        frame_key = 'gallery_import_log'
        
        read_only = True
        can_generate_more_pages = False
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, title, frame_key )
        
        panel = ClientGUIGallerySeedLog.EditGallerySeedLogPanel( frame, CG.client_controller, read_only, can_generate_more_pages, 'check', gallery_seed_log )
        
        frame.SetPanel( panel )
        
    
    def _ThisIsTheCurrentOrLoadingHighlight( self, watcher ):
        
        if self._highlighted_watcher is not None and watcher == self._highlighted_watcher:
            
            return True
            
        else:
            
            if not self._loading_highlight_job_status.IsDone():
                
                downloader = self._loading_highlight_job_status.GetIfHasVariable( 'downloader' )
                
                if downloader is not None and downloader == watcher:
                    
                    return True
                    
                
            
            return False
            
        
    
    def _UpdateImportStatus( self ):
        
        if HydrusTime.TimeHasPassed( self._next_update_time ):
            
            num_items = len( self._watchers_listctrl.GetData() )
            
            update_period = max( 1, int( ( num_items / 10 ) ** 0.33 ) )
            
            self._next_update_time = HydrusTime.GetNow() + update_period
            
            #
            
            last_time_watchers_changed = self._multiple_watcher_import.GetLastTimeWatchersChanged()
            num_watchers = self._multiple_watcher_import.GetNumWatchers()
            
            #
            
            if num_watchers == 0:
                
                text_top = 'waiting for new watchers'
                text_bottom = ''
                
            else:
                
                num_dead = self._multiple_watcher_import.GetNumDead()
                
                if num_dead == 0:
                    
                    num_dead_text = ''
                    
                else:
                    
                    num_dead_text = HydrusData.ToHumanInt( num_dead ) + ' DEAD - '
                    
                
                file_seed_cache_status = self._multiple_watcher_import.GetTotalStatus()
                
                ( num_done, num_total ) = file_seed_cache_status.GetValueRange()
                
                text_top = '{} watchers - {}'.format( HydrusData.ToHumanInt( num_watchers ), HydrusData.ConvertValueRangeToPrettyString( num_done, num_total ) )
                text_bottom = file_seed_cache_status.GetStatusText()
                
            
            self._watchers_status_st_top.setText( text_top )
            self._watchers_status_st_bottom.setText( text_bottom )
            
            #
            
            if self._last_time_watchers_changed != last_time_watchers_changed:
                
                self._last_time_watchers_changed = last_time_watchers_changed
                
                watchers = self._multiple_watcher_import.GetWatchers()
                
                self._watchers_listctrl.SetData( watchers )
                
                ideal_rows = len( watchers )
                ideal_rows = max( 4, ideal_rows )
                ideal_rows = min( ideal_rows, 24 )
                
                self._watchers_listctrl.ForceHeight( ideal_rows )
                
            else:
                
                sort_data_has_changed = self._watchers_listctrl.UpdateDatas()
                
                if sort_data_has_changed:
                    
                    self._watchers_listctrl.Sort()
                    
                
            
        
    
    def _UpdateImportStatusNow( self ):
        
        self._next_update_time = 0
        
        self._UpdateImportStatus()
        
    
    def CheckAbleToClose( self ):
        
        num_working = 0
        
        for watcher in self._multiple_watcher_import.GetWatchers():
            
            if watcher.CurrentlyWorking():
                
                num_working += 1
                
            
        
        if num_working > 0:
            
            raise HydrusExceptions.VetoException( HydrusData.ToHumanInt( num_working ) + ' watchers are still importing.' )
            
        
    
    def PendURL( self, url, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        self._AddURLs( ( url, ), filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
        
    
    def SetSearchFocus( self ):
        
        ClientGUIFunctions.SetFocusLater( self._watcher_url_input )
        
    
    def Start( self ):
        
        self._multiple_watcher_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ ClientGUIManagementController.MANAGEMENT_TYPE_IMPORT_MULTIPLE_WATCHER ] = ManagementPanelImporterMultipleWatcher

class ManagementPanelImporterSimpleDownloader( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        self._simple_downloader_import: ClientImportSimpleURLs.SimpleDownloaderImport = self._management_controller.GetVariable( 'simple_downloader_import' )
        
        #
        
        self._simple_downloader_panel = ClientGUICommon.StaticBox( self, 'simple downloader' )
        
        #
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'imports' )
        
        self._pause_files_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.global_pixmaps().file_pause, self.PauseFiles )
        self._pause_files_button.setToolTip( 'pause/play files' )
        self._current_action = ClientGUICommon.BetterStaticText( self._import_queue_panel, ellipsize_end = True )
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._controller, self._page_key )
        self._file_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._import_queue_panel )
        
        #
        
        #
        
        self._simple_parsing_jobs_panel = ClientGUICommon.StaticBox( self._simple_downloader_panel, 'parsing' )
        
        self._pause_queue_button = ClientGUICommon.BetterBitmapButton( self._simple_parsing_jobs_panel, CC.global_pixmaps().gallery_pause, self.PauseQueue )
        self._pause_queue_button.setToolTip( 'pause/play queue' )
        
        self._parser_status = ClientGUICommon.BetterStaticText( self._simple_parsing_jobs_panel, ellipsize_end = True )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._simple_parsing_jobs_panel, self._controller, True, False, 'parsing', self._page_key )
        
        self._page_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._simple_parsing_jobs_panel )
        
        self._pending_jobs_listbox = ClientGUIListBoxes.BetterQListWidget( self._simple_parsing_jobs_panel )
        
        self._pending_jobs_listbox.setSelectionMode( QW.QAbstractItemView.ExtendedSelection )
        
        self._advance_button = QW.QPushButton( '\u2191', self._simple_parsing_jobs_panel )
        self._advance_button.clicked.connect( self.EventAdvance )
        
        self._delete_button = QW.QPushButton( 'X', self._simple_parsing_jobs_panel )
        self._delete_button.clicked.connect( self.EventDelete )
        
        self._delay_button = QW.QPushButton( '\u2193', self._simple_parsing_jobs_panel )
        self._delay_button.clicked.connect( self.EventDelay )
        
        self._page_url_input = ClientGUIControls.TextAndPasteCtrl( self._simple_parsing_jobs_panel, self._PendPageURLs )
        
        self._page_url_input.setPlaceholderText( 'url to be parsed by the selected formula' )
        
        self._formulae = ClientGUICommon.BetterChoice( self._simple_parsing_jobs_panel )
        
        formulae_width = ClientGUIFunctions.ConvertTextToPixelWidth( self._formulae, 10 )
        
        self._formulae.setMinimumWidth( formulae_width )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit formulae', 'Edit these parsing formulae.', self._EditFormulae ) )
        
        self._formula_cog = ClientGUIMenuButton.MenuBitmapButton( self._simple_parsing_jobs_panel, CC.global_pixmaps().cog, menu_items )
        
        self._RefreshFormulae()
        
        file_import_options = self._simple_downloader_import.GetFileImportOptions()
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._current_action, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._pause_files_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._import_queue_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        queue_buttons_vbox = QP.VBoxLayout()
        
        QP.AddToLayout( queue_buttons_vbox, self._advance_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( queue_buttons_vbox, self._delete_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( queue_buttons_vbox, self._delay_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        queue_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( queue_hbox, self._pending_jobs_listbox, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( queue_hbox, queue_buttons_vbox, CC.FLAGS_CENTER_PERPENDICULAR )
        
        formulae_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( formulae_hbox, self._formulae, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( formulae_hbox, self._formula_cog, CC.FLAGS_CENTER_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._parser_status, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( hbox, self._pause_queue_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._simple_parsing_jobs_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( self._page_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( queue_hbox, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        self._simple_parsing_jobs_panel.Add( self._page_url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_parsing_jobs_panel.Add( formulae_hbox, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        self._simple_downloader_panel.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._simple_parsing_jobs_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._simple_downloader_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._simple_downloader_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        self._formulae.currentIndexChanged.connect( self.EventFormulaChanged )
        
        file_seed_cache = self._simple_downloader_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        gallery_seed_log = self._simple_downloader_import.GetGallerySeedLog()
        
        self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
        
        self._UpdateImportStatus()
        
        self._import_options_button.fileImportOptionsChanged.connect( self._simple_downloader_import.SetFileImportOptions )
        
    
    def _EditFormulae( self ):
        
        def data_to_pretty_callable( data ):
            
            simple_downloader_formula = data
            
            return simple_downloader_formula.GetName()
            
        
        def edit_callable( data ):
            
            simple_downloader_formula = data
            
            name = simple_downloader_formula.GetName()
            
            with ClientGUIDialogs.DialogTextEntry( dlg, 'edit name', default = name ) as dlg_2:
                
                if dlg_2.exec() == QW.QDialog.Accepted:
                    
                    name = dlg_2.GetValue()
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( dlg, 'edit formula' ) as dlg_3:
                
                panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg_3 )
                
                formula = simple_downloader_formula.GetFormula()
                
                control = ClientGUIParsingFormulae.EditFormulaPanel( panel, formula, lambda: ClientParsing.ParsingTestData( {}, ( '', ) ) )
                
                panel.SetControl( control )
                
                dlg_3.SetPanel( panel )
                
                if dlg_3.exec() == QW.QDialog.Accepted:
                    
                    formula = control.GetValue()
                    
                    simple_downloader_formula = ClientParsing.SimpleDownloaderParsingFormula( name = name, formula = formula )
                    
                    return simple_downloader_formula
                    
                else:
                    
                    raise HydrusExceptions.VetoException()
                    
                
            
        
        def add_callable():
            
            data = ClientParsing.SimpleDownloaderParsingFormula()
            
            return edit_callable( data )
            
        
        formulae = list( self._controller.new_options.GetSimpleDownloaderFormulae() )
        
        formulae.sort( key = lambda o: o.GetName() )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit simple downloader formulae' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            height_num_chars = 20
            
            control = ClientGUIListBoxes.AddEditDeleteListBoxUniqueNamedObjects( panel, height_num_chars, data_to_pretty_callable, add_callable, edit_callable )
            
            control.AddSeparator()
            control.AddImportExportButtons( ( ClientParsing.SimpleDownloaderParsingFormula, ) )
            control.AddSeparator()
            control.AddDefaultsButton( ClientDefaults.GetDefaultSimpleDownloaderFormulae )
            
            control.AddDatas( formulae )
            
            panel.SetControl( control )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                formulae = control.GetData()
                
                self._controller.new_options.SetSimpleDownloaderFormulae( formulae )
                
            
        
        self._RefreshFormulae()
        
    
    def _PendPageURLs( self, urls ):
        
        urls = [ url for url in urls if url.startswith( 'http' ) ]
        
        simple_downloader_formula = self._formulae.GetValue()
        
        for url in urls:
            
            job = ( url, simple_downloader_formula )
            
            self._simple_downloader_import.PendJob( job )
            
        
        self._UpdateImportStatus()
        
    
    def _RefreshFormulae( self ):
        
        self._formulae.blockSignals( True )
        
        self._formulae.clear()
        
        to_select = None
        
        select_name = self._simple_downloader_import.GetFormulaName()
        
        simple_downloader_formulae = list( self._controller.new_options.GetSimpleDownloaderFormulae() )
        
        simple_downloader_formulae.sort( key = lambda o: o.GetName() )
        
        for ( i, simple_downloader_formula ) in enumerate( simple_downloader_formulae ):
            
            name = simple_downloader_formula.GetName()
            
            self._formulae.addItem( name, simple_downloader_formula )
            
            if name == select_name:
                
                to_select = i
                
            
        
        self._formulae.blockSignals( False )
        
        if to_select is not None:
            
            self._formulae.setCurrentIndex( to_select )
            
        
    
    def _UpdateImportStatus( self ):
        
        ( pending_jobs, parser_status, current_action, queue_paused, files_paused ) = self._simple_downloader_import.GetStatus()
        
        current_pending_jobs = self._pending_jobs_listbox.GetData()
        
        if current_pending_jobs != pending_jobs:
            
            selected_jobs = set( self._pending_jobs_listbox.GetData( only_selected = True ) )
            
            self._pending_jobs_listbox.clear()
            
            for job in pending_jobs:
                
                ( url, simple_downloader_formula ) = job
                
                pretty_job = simple_downloader_formula.GetName() + ': ' + url
                
                self._pending_jobs_listbox.Append( pretty_job, job )
                
            
            self._pending_jobs_listbox.SelectData( selected_jobs )
            
        
        self._parser_status.setText( parser_status )
        
        self._current_action.setText( current_action )
        
        if files_paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_files_button, CC.global_pixmaps().file_play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_files_button, CC.global_pixmaps().file_pause )
            
        
        if queue_paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_queue_button, CC.global_pixmaps().gallery_play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_queue_button, CC.global_pixmaps().gallery_pause )
            
        
        ( file_network_job, page_network_job ) = self._simple_downloader_import.GetNetworkJobs()
        
        if file_network_job is None:
            
            self._file_download_control.ClearNetworkJob()
            
        else:
            
            self._file_download_control.SetNetworkJob( file_network_job )
            
        
        if page_network_job is None:
            
            self._page_download_control.ClearNetworkJob()
            
        else:
            
            self._page_download_control.SetNetworkJob( page_network_job )
            
        
    
    def CheckAbleToClose( self ):
        
        if self._simple_downloader_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def EventAdvance( self ):
        
        selected_jobs = self._pending_jobs_listbox.GetData( only_selected = True )
        
        for job in selected_jobs:
            
            self._simple_downloader_import.AdvanceJob( job )
            
        
        if len( selected_jobs ) > 0:
            
            self._UpdateImportStatus()
            
        
    
    def EventDelay( self ):
        
        selected_jobs = list( self._pending_jobs_listbox.GetData( only_selected = True ) )
        
        selected_jobs.reverse()
        
        for job in selected_jobs:
            
            self._simple_downloader_import.DelayJob( job )
            
        
        if len( selected_jobs ) > 0:
            
            self._UpdateImportStatus()
            
        
    
    def EventDelete( self ):
        
        selected_jobs = self._pending_jobs_listbox.GetData( only_selected = True )
        
        message = 'Delete {} jobs?'.format( HydrusData.ToHumanInt( len( selected_jobs ) ) )
        
        result = ClientGUIDialogsQuick.GetYesNo( self, message )
        
        if result != QW.QDialog.Accepted:
            
            return
            
        
        for job in selected_jobs:
            
            self._simple_downloader_import.DeleteJob( job )
            
        
        if len( selected_jobs ) > 0:
            
            self._UpdateImportStatus()
            
        
    
    def EventFormulaChanged( self ):
        
        formula = self._formulae.GetValue()
        
        formula_name = formula.GetName()
        
        self._simple_downloader_import.SetFormulaName( formula_name )
        self._controller.new_options.SetString( 'favourite_simple_downloader_formula', formula_name )
        
    
    def PauseQueue( self ):
        
        self._simple_downloader_import.PausePlayQueue()
        
        self._UpdateImportStatus()
        
    
    def PauseFiles( self ):
        
        self._simple_downloader_import.PausePlayFiles()
        
        self._UpdateImportStatus()
        
    
    def SetSearchFocus( self ):
        
        ClientGUIFunctions.SetFocusLater( self._page_url_input )
        
    
    def Start( self ):
        
        self._simple_downloader_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ ClientGUIManagementController.MANAGEMENT_TYPE_IMPORT_SIMPLE_DOWNLOADER ] = ManagementPanelImporterSimpleDownloader

class ManagementPanelImporterURLs( ManagementPanelImporter ):
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        ManagementPanelImporter.__init__( self, parent, page, controller, management_controller )
        
        #
        
        self._url_panel = ClientGUICommon.StaticBox( self, 'url downloader' )
        
        #
        
        self._import_queue_panel = ClientGUICommon.StaticBox( self._url_panel, 'imports' )
        
        self._pause_button = ClientGUICommon.BetterBitmapButton( self._import_queue_panel, CC.global_pixmaps().file_pause, self.Pause )
        self._pause_button.setToolTip( 'pause/play files' )
        
        self._file_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._import_queue_panel )
        
        self._urls_import: ClientImportSimpleURLs.URLsImport = self._management_controller.GetVariable( 'urls_import' )
        
        self._file_seed_cache_control = ClientGUIFileSeedCache.FileSeedCacheStatusControl( self._import_queue_panel, self._controller, page_key = self._page_key )
        
        #
        
        self._gallery_panel = ClientGUICommon.StaticBox( self._url_panel, 'search' )
        
        self._gallery_download_control = ClientGUINetworkJobControl.NetworkJobControl( self._gallery_panel )
        
        self._gallery_seed_log_control = ClientGUIGallerySeedLog.GallerySeedLogStatusControl( self._gallery_panel, self._controller, False, False, 'search', page_key = self._page_key )
        
        #
        
        self._url_input = ClientGUIControls.TextAndPasteCtrl( self._url_panel, self._PendURLs )
        
        self._url_input.setPlaceholderText( 'any url hydrus recognises, or a raw file url' )
        
        file_import_options = self._urls_import.GetFileImportOptions()
        tag_import_options = self._urls_import.GetTagImportOptions()
        note_import_options = self._urls_import.GetNoteImportOptions()
        
        show_downloader_options = True
        allow_default_selection = True
        
        self._import_options_button = ClientGUIImportOptions.ImportOptionsButton( self, show_downloader_options, allow_default_selection )
        
        self._import_options_button.SetFileImportOptions( file_import_options )
        self._import_options_button.SetTagImportOptions( tag_import_options )
        self._import_options_button.SetNoteImportOptions( note_import_options )
        
        #
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._pause_button, CC.FLAGS_ON_RIGHT )

        self._import_queue_panel.Add( hbox, CC.FLAGS_ON_RIGHT )
        self._import_queue_panel.Add( self._file_seed_cache_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._import_queue_panel.Add( self._file_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._gallery_panel.Add( self._gallery_seed_log_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._gallery_panel.Add( self._gallery_download_control, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._url_panel.Add( self._import_queue_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._gallery_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._url_input, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._url_panel.Add( self._import_options_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._url_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        #
        
        file_seed_cache = self._urls_import.GetFileSeedCache()
        
        self._file_seed_cache_control.SetFileSeedCache( file_seed_cache )
        
        gallery_seed_log = self._urls_import.GetGallerySeedLog()
        
        self._gallery_seed_log_control.SetGallerySeedLog( gallery_seed_log )
        
        self._UpdateImportStatus()
        
        self._import_options_button.fileImportOptionsChanged.connect( self._urls_import.SetFileImportOptions )
        self._import_options_button.noteImportOptionsChanged.connect( self._urls_import.SetNoteImportOptions )
        self._import_options_button.tagImportOptionsChanged.connect( self._urls_import.SetTagImportOptions )
        
    
    def _PendURLs( self, urls, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        urls = [ url for url in urls if url.startswith( 'http' ) ]
        
        self._urls_import.PendURLs( urls, filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
        
        self._UpdateImportStatus()
        
    
    def _UpdateImportStatus( self ):
        
        paused = self._urls_import.IsPaused()
        
        if paused:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.global_pixmaps().file_play )
            
        else:
            
            ClientGUIFunctions.SetBitmapButtonBitmap( self._pause_button, CC.global_pixmaps().file_pause )
            
        
        ( file_network_job, gallery_network_job ) = self._urls_import.GetNetworkJobs()
        
        if file_network_job is None:
            
            self._file_download_control.ClearNetworkJob()
            
        else:
            
            self._file_download_control.SetNetworkJob( file_network_job )
            
        
        if gallery_network_job is None:
            
            self._gallery_download_control.ClearNetworkJob()
            
        else:
            
            self._gallery_download_control.SetNetworkJob( gallery_network_job )
            
        
    
    def CheckAbleToClose( self ):
        
        if self._urls_import.CurrentlyWorking():
            
            raise HydrusExceptions.VetoException( 'This page is still importing.' )
            
        
    
    def Pause( self ):
        
        self._urls_import.PausePlay()
        
        self._UpdateImportStatus()
        
    
    def PendURL( self, url, filterable_tags = None, additional_service_keys_to_tags = None ):
        
        if filterable_tags is None:
            
            filterable_tags = set()
            
        
        if additional_service_keys_to_tags is None:
            
            additional_service_keys_to_tags = ClientTags.ServiceKeysToTags()
            
        
        self._PendURLs( ( url, ), filterable_tags = filterable_tags, additional_service_keys_to_tags = additional_service_keys_to_tags )
        
    
    def SetSearchFocus( self ):
        
        ClientGUIFunctions.SetFocusLater( self._url_input )
        
    
    def Start( self ):
        
        self._urls_import.Start( self._page_key )
        
    
management_panel_types_to_classes[ ClientGUIManagementController.MANAGEMENT_TYPE_IMPORT_URLS ] = ManagementPanelImporterURLs

def GetPetitionActionInfo( petition: HydrusNetwork.Petition ):
    
    add_contents = petition.GetContents( HC.CONTENT_UPDATE_PEND )
    delete_contents = petition.GetContents( HC.CONTENT_UPDATE_PETITION )
    
    have_add = len( add_contents ) > 0
    have_delete = len( delete_contents ) > 0
    
    action_text = 'UNKNOWN'
    hydrus_text = 'default'
    object_name = 'normal'
    
    if have_add or have_delete:
        
        if have_add and have_delete:
            
            action_text = 'REPLACE'
            
        elif have_add:
            
            action_text = 'ADD'
            hydrus_text = 'valid'
            object_name = 'HydrusValid'
            
        else:
            
            action_text = 'DELETE'
            hydrus_text = 'invalid'
            object_name = 'HydrusInvalid'
            
        
    
    return ( action_text, hydrus_text, object_name )
    

class ManagementPanelPetitions( ManagementPanel ):
    
    TAG_DISPLAY_TYPE = ClientTags.TAG_DISPLAY_STORAGE
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        self._petition_service_key = management_controller.GetVariable( 'petition_service_key' )
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        self._service = self._controller.services_manager.GetService( self._petition_service_key )
        self._can_ban = self._service.HasPermission( HC.CONTENT_TYPE_ACCOUNTS, HC.PERMISSION_ACTION_MODERATE )
        
        service_type = self._service.GetServiceType()
        
        self._petition_types_to_count = collections.Counter()
        self._current_petition = None
        
        content_type = management_controller.GetVariable( 'petition_type_content_type' )
        status = management_controller.GetVariable( 'petition_type_status' )
        
        if content_type is None or status is None:
            
            self._last_petition_type_fetched = None
            
        else:
            
            self._last_petition_type_fetched = ( content_type, status )
            
        
        self._last_fetched_subject_account_key = None
        
        self._petition_headers_to_fetched_petitions_cache = {}
        self._petition_headers_we_failed_to_fetch = set()
        self._petition_headers_we_are_fetching = []
        self._outgoing_petition_headers_to_petitions = {}
        self._failed_outgoing_petition_headers_to_petitions = {}
        
        self._petition_fetcher_and_uploader_work_lock = threading.Lock()
        
        #
        
        self._petition_numbers_panel = ClientGUICommon.StaticBox( self, 'counts' )
        
        self._petition_account_key = QW.QLineEdit( self._petition_numbers_panel )
        self._petition_account_key.setPlaceholderText( 'account id filter' )
        
        self._num_petitions_to_fetch = ClientGUICommon.BetterSpinBox( self._petition_numbers_panel, min = 1, max = 10000 )
        
        self._num_petitions_to_fetch.setValue( management_controller.GetVariable( 'num_petitions_to_fetch' ) )
        
        self._refresh_num_petitions_button = ClientGUICommon.BetterButton( self._petition_numbers_panel, 'refresh counts', self._StartFetchNumPetitions )
        
        self._petition_types_to_controls = {}
        
        content_type_hboxes = []
        
        self._my_petition_types = []
        
        if service_type == HC.FILE_REPOSITORY:
            
            self._my_petition_types.append( ( HC.CONTENT_TYPE_FILES, HC.CONTENT_STATUS_PETITIONED ) )
            
        elif service_type == HC.TAG_REPOSITORY:
            
            self._my_petition_types.append( ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED ) )
            self._my_petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING ) )
            self._my_petition_types.append( ( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PETITIONED ) )
            self._my_petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PENDING ) )
            self._my_petition_types.append( ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_STATUS_PETITIONED ) )
            
        
        for petition_type in self._my_petition_types:
            
            ( content_type, status ) = petition_type
            
            func = HydrusData.Call( self._FetchPetitionsSummary, petition_type )
            
            st = ClientGUICommon.BetterStaticText( self._petition_numbers_panel )
            button = ClientGUICommon.BetterButton( self._petition_numbers_panel, 'fetch ' + HC.content_status_string_lookup[ status ] + ' ' + HC.content_type_string_lookup[ content_type ] + ' petitions', func )
            
            button.setEnabled( False )
            
            self._petition_types_to_controls[ ( content_type, status ) ] = ( st, button )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, st, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
            QP.AddToLayout( hbox, button, CC.FLAGS_CENTER_PERPENDICULAR )
            
            content_type_hboxes.append( hbox )
            
        
        #
        
        self._petitions_panel = ClientGUICommon.StaticBox( self, 'petitions' )
        
        self._petitions_summary_list_panel = ClientGUIListCtrl.BetterListCtrlPanel( self._petitions_panel )
        
        self._petitions_summary_list = ClientGUIListCtrl.BetterListCtrl( self._petitions_summary_list_panel, CGLC.COLUMN_LIST_PETITIONS_SUMMARY.ID, 12, self._ConvertDataToListCtrlTuples, activation_callback = self._ActivateToHighlightPetition )
        
        self._petitions_summary_list_panel.SetListCtrl( self._petitions_summary_list )
        
        self._petitions_summary_list_panel.AddButton( 'mass-approve', self._ApproveSelected, enabled_check_func = self._OnlySelectingLoadedPetitions, tooltip = 'Approve the selected petitions' )
        self._petitions_summary_list_panel.AddButton( 'mass-deny', self._DenySelected, enabled_check_func = self._OnlySelectingLoadedPetitions, tooltip = 'Deny the selected petitions' )
        
        #
        
        self._petition_panel = ClientGUICommon.StaticBox( self, 'highlighted petition' )
        
        self._num_files_to_show = ClientGUICommon.NoneableSpinCtrl( self._petition_panel, message = 'number of files to show', min = 1 )
        
        self._num_files_to_show.SetValue( management_controller.GetVariable( 'num_files_to_show' ) )
        
        self._action_text = ClientGUICommon.BetterStaticText( self._petition_panel, label = '' )
        
        self._reason_text = QW.QTextEdit( self._petition_panel )
        self._reason_text.setReadOnly( True )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._reason_text, ( 16, 6 ) )
        
        self._reason_text.setFixedHeight( min_height )
        
        check_all = ClientGUICommon.BetterButton( self._petition_panel, 'check all', self._CheckAll )
        flip_selected = ClientGUICommon.BetterButton( self._petition_panel, 'flip selected', self._FlipSelected )
        check_none = ClientGUICommon.BetterButton( self._petition_panel, 'check none', self._CheckNone )
        
        self._sort_by_left = ClientGUICommon.BetterButton( self._petition_panel, 'sort by left', self._SortBy, 'left' )
        self._sort_by_right = ClientGUICommon.BetterButton( self._petition_panel, 'sort by right', self._SortBy, 'right' )
        
        self._sort_by_left.setEnabled( False )
        self._sort_by_right.setEnabled( False )
        
        self._contents_add = ClientGUICommon.BetterCheckBoxList( self._petition_panel )
        self._contents_add.itemDoubleClicked.connect( self.ContentsAddDoubleClick )
        self._contents_add.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarAlwaysOff )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._contents_add, ( 16, 20 ) )
        
        self._contents_add.setFixedHeight( min_height )
        
        self._contents_delete = ClientGUICommon.BetterCheckBoxList( self._petition_panel )
        self._contents_delete.itemDoubleClicked.connect( self.ContentsDeleteDoubleClick )
        self._contents_delete.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarAlwaysOff )
        
        ( min_width, min_height ) = ClientGUIFunctions.ConvertTextToPixels( self._contents_delete, ( 16, 20 ) )
        
        self._contents_delete.setFixedHeight( min_height )
        
        self._process = QW.QPushButton( 'process', self._petition_panel )
        self._process.clicked.connect( self.ProcessCurrentPetition )
        self._process.setObjectName( 'HydrusAccept' )
        
        self._copy_account_key_button = ClientGUICommon.BetterButton( self._petition_panel, 'copy petitioner account id', self._CopyAccountKey )
        
        self._modify_petitioner = QW.QPushButton( 'modify petitioner', self._petition_panel )
        self._modify_petitioner.clicked.connect( self.EventModifyPetitioner )
        self._modify_petitioner.setEnabled( False )
        if not self._can_ban: self._modify_petitioner.setVisible( False )
        
        #
        
        self._petition_numbers_panel.Add( self._petition_account_key, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_numbers_panel.Add( self._refresh_num_petitions_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_numbers_panel.Add( ClientGUICommon.WrapInText( self._num_petitions_to_fetch, self, 'number of petitions to fetch' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        
        for hbox in content_type_hboxes:
            
            self._petition_numbers_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
        
        #
        
        self._petitions_panel.Add( self._petitions_summary_list_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        #
        
        check_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( check_hbox, check_all, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( check_hbox, flip_selected, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( check_hbox, check_none, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        sort_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( sort_hbox, self._sort_by_left, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( sort_hbox, self._sort_by_right, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        
        self._petition_panel.Add( ClientGUICommon.BetterStaticText( self._petition_panel, label = 'Double-click a petition row to see its files, if it has them.' ), CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._num_files_to_show, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._action_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._reason_text, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( sort_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.Add( self._contents_add, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._contents_delete, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( check_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._petition_panel.Add( self._process, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._copy_account_key_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._petition_panel.Add( self._modify_petitioner, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._petition_numbers_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._petitions_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._petition_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if service_type == HC.TAG_REPOSITORY:
            
            tag_display_type = ClientTags.TAG_DISPLAY_STORAGE
            
        else:
            
            tag_display_type = ClientTags.TAG_DISPLAY_SELECTION_LIST
            
        
        self._MakeCurrentSelectionTagsBox( vbox, tag_display_type = tag_display_type )
        
        self.widget().setLayout( vbox )
        
        self._contents_add.rightClicked.connect( self.EventAddRowRightClick )
        self._contents_delete.rightClicked.connect( self.EventDeleteRowRightClick )
        
        self._petition_account_key.textChanged.connect( self._UpdateAccountKey )
        
        self._num_files_to_show.valueChanged.connect( self._NotifyNumsUpdated )
        self._num_petitions_to_fetch.valueChanged.connect( self._NotifyNumsUpdated )
        
        self._UpdateAccountKey()
        self._DrawCurrentPetition()
        
    
    def _ActivateToHighlightPetition( self ):
        
        for eligible_petition_header in self._petitions_summary_list.GetData( only_selected = True ):
            
            if self._CanHighlight( eligible_petition_header ):
                
                self._HighlightPetition( eligible_petition_header )
                
                break
                
            
        
    
    def _ApproveSelected( self ):
        
        selected_petition_headers = self._petitions_summary_list.GetData( only_selected = True )
        
        viable_petitions = [ self._petition_headers_to_fetched_petitions_cache[ petition_header ] for petition_header in selected_petition_headers if self._CanHighlight( petition_header ) ]
        
        if len( viable_petitions ) > 0:
            
            text = 'Approve all the content in these {} petitions?'.format( HydrusData.ToHumanInt( len( viable_petitions ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            if result == QW.QDialog.Accepted:
                
                for petition in viable_petitions:
                    
                    petition.ApproveAll()
                    
                
                self._StartUploadingCompletedPetitions( viable_petitions )
                
            
        
    
    def _CanHighlight( self, petition_header: HydrusNetwork.PetitionHeader ):
        
        if petition_header in self._outgoing_petition_headers_to_petitions:
            
            return False
            
        
        if petition_header in self._failed_outgoing_petition_headers_to_petitions:
            
            return False
            
        
        return petition_header in self._petition_headers_to_fetched_petitions_cache
        
    
    def _CheckAll( self ):
        
        for i in range( self._contents_add.count() ):
            
            self._contents_add.Check( i, True )
            
        
        for i in range( self._contents_delete.count() ):
            
            self._contents_delete.Check( i, True )
            
        
    
    def _CheckNone( self ):
        
        for i in range( self._contents_add.count() ):
            
            self._contents_add.Check( i, False )
            
        
        for i in range( self._contents_delete.count() ):
            
            self._contents_delete.Check( i, False )
            
        
    
    def _ClearCurrentPetition( self ):
        
        if self._current_petition is not None:
            
            petition_header = self._current_petition.GetPetitionHeader()
            
            self._current_petition = None
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.UpdateDatas( ( petition_header, ) )
                
            
            self._DrawCurrentPetition()
            
            self._ShowHashes( [] )
            
        
    
    def _ClearPetitionsSummary( self ):
        
        self._petitions_summary_list.DeleteDatas( self._petitions_summary_list.GetData() )
        
        self._petition_headers_we_are_fetching = []
        self._petition_headers_we_failed_to_fetch = set()
        self._failed_outgoing_petition_headers_to_petitions = {}
        
        self._ClearCurrentPetition()
        
    
    def _ConvertDataToListCtrlTuples( self, petition_header: HydrusNetwork.PetitionHeader ):
        
        pretty_action = ''
        pretty_content = 'fetching' + HC.UNICODE_ELLIPSIS
        
        sort_content = 1
        
        petition = None
        this_is_current_petition = False
        
        if petition_header in self._outgoing_petition_headers_to_petitions:
            
            petition = self._outgoing_petition_headers_to_petitions[ petition_header ]
            
            pretty_content = 'uploading' + HC.UNICODE_ELLIPSIS
            
        elif petition_header in self._failed_outgoing_petition_headers_to_petitions:
            
            petition = self._failed_outgoing_petition_headers_to_petitions[ petition_header ]
            
            pretty_content = 'failed to upload!'
            
        elif petition_header in self._petition_headers_to_fetched_petitions_cache:
            
            petition = self._petition_headers_to_fetched_petitions_cache[ petition_header ]
            
            pretty_content = petition.GetContentSummary()
            
            this_is_current_petition = False
            
            if self._current_petition is not None and petition_header == self._current_petition.GetPetitionHeader():
                
                this_is_current_petition = True
                
            
        elif petition_header in self._petition_headers_we_failed_to_fetch:
            
            pretty_content = 'failed to fetch!'
            
        
        if petition is not None:
            
            pretty_action = GetPetitionActionInfo( petition )[0]
            
            sort_content = petition.GetActualContentWeight()
            
        
        if this_is_current_petition:
            
            pretty_action = f'* {pretty_action}'
            
        
        pretty_account_key = petition_header.account_key.hex()
        pretty_reason = petition_header.reason
        
        sort_action = pretty_action
        sort_account_key = pretty_account_key
        sort_reason = pretty_reason
        
        display_tuple = ( pretty_action, pretty_account_key, pretty_reason, pretty_content )
        sort_tuple = ( sort_action, sort_account_key, sort_reason, sort_content )
        
        return ( display_tuple, sort_tuple )
        
    
    def _CopyAccountKey( self ):
        
        if self._current_petition is None:
            
            return
            
        
        account_key = self._current_petition.GetPetitionerAccount().GetAccountKey()
        
        CG.client_controller.pub( 'clipboard', 'text', account_key.hex() )
        
    
    def _DenySelected( self ):
        
        selected_petition_headers = self._petitions_summary_list.GetData( only_selected = True )
        
        viable_petitions = [ self._petition_headers_to_fetched_petitions_cache[ petition_header ] for petition_header in selected_petition_headers if self._CanHighlight( petition_header ) ]
        
        if len( viable_petitions ) > 0:
            
            text = 'Deny all the content in these {} petitions?'.format( HydrusData.ToHumanInt( len( viable_petitions ) ) )
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            if result == QW.QDialog.Accepted:
                
                for petition in viable_petitions:
                    
                    petition.DenyAll()
                    
                
                self._StartUploadingCompletedPetitions( viable_petitions )
                
            
        
    
    def _DrawCurrentPetition( self ):
        
        if self._current_petition is None:
            
            self._action_text.clear()
            self._action_text.setProperty( 'hydrus_text', 'default' )
            
            self._reason_text.clear()
            self._reason_text.setProperty( 'hydrus_text', 'default' )
            
            self._contents_add.clear()
            self._contents_delete.clear()
            
            self._contents_add.hide()
            self._contents_delete.hide()
            
            self._process.setEnabled( False )
            self._copy_account_key_button.setEnabled( False )
            
            self._sort_by_left.setEnabled( False )
            self._sort_by_right.setEnabled( False )
            
            if self._can_ban:
                
                self._modify_petitioner.setEnabled( False )
                
            
        else:
            
            add_contents = self._current_petition.GetContents( HC.CONTENT_UPDATE_PEND )
            delete_contents = self._current_petition.GetContents( HC.CONTENT_UPDATE_PETITION )
            
            have_add = len( add_contents ) > 0
            have_delete = len( delete_contents ) > 0
            
            ( action_text, hydrus_text, object_name ) = GetPetitionActionInfo( self._current_petition )
            
            self._action_text.setText( action_text )
            self._action_text.setObjectName( object_name )
            #self._action_text.setProperty( 'hydrus_text', hydrus_text )
            
            reason = self._current_petition.GetReason()
            
            self._reason_text.setPlainText( reason )
            self._reason_text.setObjectName( object_name )
            #self._reason_text.setProperty( 'hydrus_text', hydrus_text )
            
            if self._last_petition_type_fetched[0] in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                self._sort_by_left.setEnabled( True )
                self._sort_by_right.setEnabled( True )
                
            else:
                
                self._sort_by_left.setEnabled( False )
                self._sort_by_right.setEnabled( False )
                
            
            self._contents_add.setVisible( have_add )
            self._contents_delete.setVisible( have_delete )
            
            contents_and_checks = [ ( c, True ) for c in add_contents ]
            
            self._SetContentsAndChecks( HC.CONTENT_UPDATE_PEND, contents_and_checks, 'right' )
            
            contents_and_checks = [ ( c, True ) for c in delete_contents ]
            
            self._SetContentsAndChecks( HC.CONTENT_UPDATE_PETITION, contents_and_checks, 'right' )
            
            self._process.setEnabled( True )
            self._copy_account_key_button.setEnabled( True )
            
            if self._can_ban:
                
                self._modify_petitioner.setEnabled( True )
                
            
        
        self._action_text.style().polish( self._action_text )
        self._reason_text.style().polish( self._reason_text )
        
    
    def _DrawNumPetitions( self ):
        
        for ( petition_type, ( st, button ) ) in self._petition_types_to_controls.items():
            
            count = self._petition_types_to_count[ petition_type ]
            
            ( st, button ) = self._petition_types_to_controls[ petition_type ]
            
            st.setText( '{} petitions'.format( HydrusData.ToHumanInt( count ) ) )
            
            button.setEnabled( count > 0 )
            
        
    
    def _FetchBestPetitionsSummary( self ):
        
        top_petition_type_with_count = None
        
        for petition_type in self._my_petition_types:
            
            count = self._petition_types_to_count[ petition_type ]
            
            if count == 0:
                
                continue
                
            
            if self._last_petition_type_fetched is not None and self._last_petition_type_fetched == petition_type:
                
                self._FetchPetitionsSummary( petition_type )
                
                return
                
            
            if top_petition_type_with_count is None:
                
                top_petition_type_with_count = petition_type
                
            
        
        if top_petition_type_with_count is not None:
            
            self._FetchPetitionsSummary( top_petition_type_with_count )
            
        
    
    def _FetchPetitionsSummary( self, petition_type ):
        
        ( st, button ) = self._petition_types_to_controls[ petition_type ]
        
        ( content_type, status ) = petition_type
        
        num_to_fetch = self._num_petitions_to_fetch.value()
        
        subject_account_key = self._GetSubjectAccountKey()
        
        def qt_set_petitions_summary( petitions_summary ):
            
            if self._last_petition_type_fetched != petition_type:
                
                last_petition_type = self._last_petition_type_fetched
                
                self._last_petition_type_fetched = petition_type
                
                self._management_controller.SetVariable( 'petition_type_content_type', content_type )
                self._management_controller.SetVariable( 'petition_type_status', status )
                
                self._UpdateFetchButtonText( last_petition_type )
                
            
            self._SetPetitionsSummary( petitions_summary )
            
        
        def qt_done():
            
            button.setEnabled( True )
            
            self._UpdateFetchButtonText( self._last_petition_type_fetched )
            
        
        def do_it( service ):
            
            try:
                
                if subject_account_key is None:
                    
                    response = service.Request( HC.GET, 'petitions_summary', { 'content_type' : content_type, 'status' : status, 'num' : num_to_fetch } )
                    
                else:
                    
                    response = service.Request( HC.GET, 'petitions_summary', { 'content_type' : content_type, 'status' : status, 'num' : num_to_fetch, 'subject_account_key' : subject_account_key } )
                    
                
                CG.client_controller.CallBlockingToQt( self, qt_set_petitions_summary, response[ 'petitions_summary' ] )
                
            except HydrusExceptions.NotFoundException:
                
                job_status = ClientThreading.JobStatus()
                
                job_status.SetStatusText( 'Hey, the server did not have that type of petition after all. Please hit refresh counts.' )
                
                job_status.FinishAndDismiss( 5 )
                
                CG.client_controller.pub( 'message', job_status )
                
            finally:
                
                CG.client_controller.CallBlockingToQt( self, qt_done )
                
            
        
        if petition_type != self._last_petition_type_fetched:
            
            self._ClearPetitionsSummary()
            
        
        button.setEnabled( False )
        button.setText( 'Fetching' + HC.UNICODE_ELLIPSIS )
        
        self._controller.CallToThread( do_it, self._service )
        
    
    def _FlipSelected( self ):
        
        for i in self._contents_add.GetSelectedIndices():
            
            flipped_state = not self._contents_add.IsChecked( i )
            
            self._contents_add.Check( i, flipped_state )
            
        
        for i in self._contents_delete.GetSelectedIndices():
            
            flipped_state = not self._contents_delete.IsChecked( i )
            
            self._contents_delete.Check( i, flipped_state )
            
        
    
    def _GetContentsAndChecks( self, action ):
        
        if action == HC.CONTENT_UPDATE_PEND:
            
            contents = self._contents_add
            
        else:
            
            contents = self._contents_delete
            
        
        contents_and_checks = []
        
        for i in range( contents.count() ):
            
            content = contents.GetData( i )
            check = contents.IsChecked( i )
            
            contents_and_checks.append( ( content, check ) )
            
        
        return contents_and_checks
        
    
    def _GetSubjectAccountKey( self ):
        
        account_key_hex = self._petition_account_key.text()
        
        if len( account_key_hex ) == 0:
            
            return None
            
        else:
            
            try:
                
                account_key_bytes = bytes.fromhex( account_key_hex )
                
                if len( account_key_bytes ) != 32:
                    
                    raise Exception()
                    
                
                return account_key_bytes
                
            except Exception as e:
                
                return None
                
            
        
    
    def _HighlightAPetitionIfNeeded( self ):
        
        if self._current_petition is None:
            
            for eligible_petition_header in self._petitions_summary_list.GetData():
                
                if self._CanHighlight( eligible_petition_header ):
                    
                    self._HighlightPetition( eligible_petition_header )
                    
                    break
                    
                
            
        
    
    def _HighlightPetition( self, petition_header ):
        
        if not self._CanHighlight( petition_header ):
            
            return
            
        
        if self._current_petition is not None and petition_header == self._current_petition.GetPetitionHeader():
            
            self._ClearCurrentPetition()
            
        elif petition_header in self._petition_headers_to_fetched_petitions_cache:
            
            petition = self._petition_headers_to_fetched_petitions_cache[ petition_header ]
            
            self._SetCurrentPetition( petition )
            
        
    
    def _OnlySelectingLoadedPetitions( self ):
        
        petition_headers = self._petitions_summary_list.GetData( only_selected = True )
        
        if len( petition_headers ) == 0:
            
            return False
            
        
        for petition_header in petition_headers:
            
            if petition_header not in self._petition_headers_to_fetched_petitions_cache:
                
                return False
                
            
        
        return True
        
    
    def _NotifyNumsUpdated( self ):
        
        self._management_controller.SetVariable( 'num_petitions_to_fetch', self._num_petitions_to_fetch.value() )
        self._management_controller.SetVariable( 'num_files_to_show', self._num_files_to_show.GetValue() )
        
    
    def _SetContentsAndChecks( self, action, contents_and_checks, sort_type ):
        
        def key( c_and_s ):
            
            ( c, s ) = c_and_s
            
            if c.GetContentType() in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                ( left, right ) = c.GetContentData()
                
                if sort_type == 'left':
                    
                    ( part_one, part_two ) = ( HydrusTags.SplitTag( left ), HydrusTags.SplitTag( right ) )
                    
                elif sort_type == 'right':
                    
                    ( part_one, part_two ) = ( HydrusTags.SplitTag( right ), HydrusTags.SplitTag( left ) )
                    
                
            elif c.GetContentType() == HC.CONTENT_TYPE_MAPPINGS:
                
                ( tag, hashes ) = c.GetContentData()
                
                part_one = HydrusTags.SplitTag( tag )
                part_two = None
                
            else:
                
                part_one = None
                part_two = None
                
            
            return ( -c.GetVirtualWeight(), part_one, part_two )
            
        
        contents_and_checks.sort( key = key )
        
        if action == HC.CONTENT_UPDATE_PEND:
            
            contents = self._contents_add
            
            string_template = 'ADD: {}'
            
        else:
            
            contents = self._contents_delete
            
            string_template = 'DELETE: {}'
            
        
        contents.clear()
        
        for ( i, ( content, check ) ) in enumerate( contents_and_checks ):
            
            content_string = string_template.format( content.ToString() )
            
            contents.Append( content_string, content, starts_checked = check )
            
        
        if contents.count() > 0:
            
            ideal_height_in_rows = max( 1, min( 20, len( contents_and_checks ) ) )
            
            pixels_per_row = contents.sizeHintForRow( 0 )
            
        else:
            
            ideal_height_in_rows = 1
            pixels_per_row = 16
            
        
        ideal_height_in_pixels = ( ideal_height_in_rows * pixels_per_row ) + ( contents.frameWidth() * 2 )
        
        contents.setFixedHeight( ideal_height_in_pixels )
        
    
    def _SetCurrentPetition( self, petition: HydrusNetwork.Petition ):
        
        self._ClearCurrentPetition()
        
        self._current_petition = petition
        
        self._petitions_summary_list.UpdateDatas( ( self._current_petition.GetPetitionHeader(), ) )
        
        self._DrawCurrentPetition()
        
        self._ShowHashes( [] )
        
    
    def _SetPetitionsSummary( self, petitions_summary: typing.List[ HydrusNetwork.PetitionHeader ] ):
        
        # note we can't make this a nice 'append' so easily, since we still need to cull petitions that were processed without us looking
        # we'll keep the current since the user is looking, but otherwise we'll be good for now
        # maybe add a hard refresh button in future? we'll see how common these issues are
        
        if self._current_petition is not None and len( petitions_summary ) > 0:
            
            current_petition_header = self._current_petition.GetPetitionHeader()
            
            if current_petition_header not in petitions_summary:
                
                petitions_summary.append( current_petition_header )
                
            
        
        self._petitions_summary_list.SetData( petitions_summary )
        
        sorted_petition_headers = self._petitions_summary_list.GetData()
        
        self._petition_headers_we_are_fetching = [ petition_header for petition_header in sorted_petition_headers if petition_header not in self._petition_headers_to_fetched_petitions_cache ]
        
        if len( self._petition_headers_we_are_fetching ) > 0:
            
            CG.client_controller.CallToThread( self.THREADPetitionFetcherAndUploader, self._petition_fetcher_and_uploader_work_lock, self._service )
            
        
        self._HighlightAPetitionIfNeeded()
        
    
    def _ShowHashes( self, hashes ):
        
        with ClientGUICommon.BusyCursor():
            
            media_results = self._controller.Read( 'media_results', hashes )
            
        
        panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, media_results )
        
        panel.Collect( self._media_collect_widget.GetValue() )
        
        panel.Sort( self._media_sort_widget.GetSort() )
        
        self._page.SwapMediaPanel( panel )
        
    
    def _SortBy( self, sort_type ):
        
        for action in [ HC.CONTENT_UPDATE_PEND, HC.CONTENT_UPDATE_PETITION ]:
            
            contents_and_checks = self._GetContentsAndChecks( action )
            
            self._SetContentsAndChecks( action, contents_and_checks, sort_type )
            
        
    
    def _StartFetchNumPetitions( self ):
        
        def do_it( service, subject_account_key = None ):
            
            def qt_draw( petition_count_rows ):
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                num_petitions_currently_listed = len( self._petitions_summary_list.GetData() )
                
                old_petition_types_to_count = self._petition_types_to_count
                
                self._petition_types_to_count = collections.Counter()
                
                # we had a whole thing here that did 'if count dropped by more than 1, refresh summary' and 'if we only have 20% left of our desired count, refresh summary'
                # but the count from the server and the count of what we see differs for mappings, where petitions are bunched, and it was just a pain
                # maybe try again later, with better counting tech and more experience of what is actually wanted here
                
                for ( content_type, status, count ) in petition_count_rows:
                    
                    petition_type = ( content_type, status )
                    
                    self._petition_types_to_count[ petition_type ] = count
                    
                
                self._DrawNumPetitions()
                
                if num_petitions_currently_listed == 0:
                    
                    self._FetchBestPetitionsSummary()
                    
                
            
            def qt_reset():
                
                if not self or not QP.isValid( self ):
                    
                    return
                    
                
                self._refresh_num_petitions_button.setText( 'refresh counts' )
                
            
            try:
                
                if subject_account_key is None:
                    
                    response = service.Request( HC.GET, 'num_petitions' )
                    
                else:
                    
                    try:
                        
                        response = service.Request( HC.GET, 'num_petitions', { 'subject_account_key' : subject_account_key } )
                        
                    except HydrusExceptions.NotFoundException:
                        
                        HydrusData.ShowText( 'That account id was not found!' )
                        
                        QP.CallAfter( qt_draw, [] )
                        
                        return
                        
                    
                
                num_petition_info = response[ 'num_petitions' ]
                
                QP.CallAfter( qt_draw, num_petition_info )
                
            finally:
                
                QP.CallAfter( qt_reset )
                
            
        
        self._refresh_num_petitions_button.setText( 'Fetching' + HC.UNICODE_ELLIPSIS )
        
        subject_account_key = self._GetSubjectAccountKey()
        
        self._last_fetched_subject_account_key = subject_account_key
        
        self._controller.CallToThread( do_it, self._service, subject_account_key )
        
    
    def _StartUploadingCompletedPetitions( self, petitions: typing.Collection[ HydrusNetwork.Petition ] ):
        
        for petition in petitions:
            
            self._outgoing_petition_headers_to_petitions[ petition.GetPetitionHeader() ] = petition
            
            if petition == self._current_petition:
                
                self._ClearCurrentPetition()
                
            
        
        self._HighlightAPetitionIfNeeded()
        
        CG.client_controller.CallToThread( self.THREADPetitionFetcherAndUploader, self._petition_fetcher_and_uploader_work_lock, self._service )
        
    
    def _UpdateAccountKey( self ):
        
        account_key_hex = self._petition_account_key.text()
        
        if len( account_key_hex ) == 0:
            
            valid = True
            
        else:
            
            try:
                
                account_key_bytes = bytes.fromhex( account_key_hex )
                
                if len( account_key_bytes ) != 32:
                    
                    raise Exception()
                    
                
                valid = True
                
            except Exception as e:
                
                valid = False
                
            
        
        if valid:
            
            self._petition_account_key.setObjectName( 'HydrusValid' )
            
            if self._GetSubjectAccountKey() != self._last_fetched_subject_account_key:
                
                self._StartFetchNumPetitions()
                
            
        else:
            
            self._petition_account_key.setObjectName( 'HydrusInvalid' )
            
        
        self._petition_account_key.style().polish( self._petition_account_key )
        
    
    def _UpdateFetchButtonText( self, petition_type ):
        
        if petition_type is not None:
            
            ( st, button ) = self._petition_types_to_controls[ petition_type ]
            
            ( content_type, status ) = petition_type
            
            label = 'fetch {} {} petitions'.format( HC.content_status_string_lookup[ status ], HC.content_type_string_lookup[ content_type ] )
            
            if petition_type == self._last_petition_type_fetched:
                
                label = f'{label} (*)'
                
            
            button.setText( label )
            
        
    
    def ContentsAddDoubleClick( self, item ):
        
        selected_indices = self._contents_add.GetSelectedIndices()
        
        if len( selected_indices ) > 0:
            
            selection = selected_indices[0]
            
            content = self._contents_add.GetData( selection )
            
            self.EventContentsDoubleClick( content )
            
        
    
    def ContentsDeleteDoubleClick( self, item ):
        
        selected_indices = self._contents_delete.GetSelectedIndices()
        
        if len( selected_indices ) > 0:
            
            selection = selected_indices[0]
            
            content = self._contents_delete.GetData( selection )
            
            self.EventContentsDoubleClick( content )
            
        
    
    def EventContentsDoubleClick( self, content ):
        
        if content.HasHashes():
            
            hashes = content.GetHashes()
            
            num_files_to_show = self._num_files_to_show.GetValue()
            
            if num_files_to_show is not None and len( hashes ) > num_files_to_show:
                
                hashes = random.sample( hashes, num_files_to_show )
                
            
            self._ShowHashes( hashes )
            
        
    
    def EventModifyPetitioner( self ):
        
        subject_account_key = self._current_petition.GetPetitionerAccount().GetAccountKey()
        
        subject_account_identifiers = [ HydrusNetwork.AccountIdentifier( account_key = subject_account_key ) ]
        
        frame = ClientGUITopLevelWindowsPanels.FrameThatTakesScrollablePanel( self, 'manage accounts' )
        
        panel = ClientGUIHydrusNetwork.ModifyAccountsPanel( frame, self._petition_service_key, subject_account_identifiers )
        
        frame.SetPanel( panel )
        
    
    def EventAddRowRightClick( self ):
        
        selected_indices = self._contents_add.GetSelectedIndices()
        
        selected_contents = []
        
        for i in selected_indices:
            
            content = self._contents_add.GetData( i )
            
            selected_contents.append( content )
            
        
        self.EventContentsRightClick( selected_contents )
        
    
    def EventDeleteRowRightClick( self ):
        
        selected_indices = self._contents_delete.GetSelectedIndices()
        
        selected_contents = []
        
        for i in selected_indices:
            
            content = self._contents_delete.GetData( i )
            
            selected_contents.append( content )
            
        
        self.EventContentsRightClick( selected_contents )
        
    
    def EventContentsRightClick( self, contents ):
        
        copyable_items_a = []
        copyable_items_b = []
        
        for content in contents:
            
            content_type = content.GetContentType()
            
            if content_type == HC.CONTENT_TYPE_MAPPINGS:
                
                ( tag, hashes ) = content.GetContentData()
                
                copyable_items_a.append( tag )
                
            elif content_type in ( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_TYPE_TAG_PARENTS ):
                
                ( tag_a, tag_b ) = content.GetContentData()
                
                copyable_items_a.append( tag_a )
                copyable_items_b.append( tag_b )
                
            
        
        copyable_items_a = HydrusData.DedupeList( copyable_items_a )
        copyable_items_b = HydrusData.DedupeList( copyable_items_b )
        
        if len( copyable_items_a ) + len( copyable_items_b ) > 0:
            
            menu = ClientGUIMenus.GenerateMenu( self )
            
            for copyable_items in [ copyable_items_a, copyable_items_b ]:
                
                if len( copyable_items ) > 0:
                    
                    if len( copyable_items ) == 1:
                        
                        tag = copyable_items[0]
                        
                        ClientGUIMenus.AppendMenuItem( menu, 'copy {}'.format( tag ), 'Copy this tag.', CG.client_controller.pub, 'clipboard', 'text', tag )
                        
                    else:
                        
                        text = os.linesep.join( copyable_items )
                        
                        ClientGUIMenus.AppendMenuItem( menu, 'copy {} tags'.format( HydrusData.ToHumanInt( len( copyable_items ) ) ), 'Copy this tag.', CG.client_controller.pub, 'clipboard', 'text', text )
                        
                    
                
            
            CGC.core().PopupMenu( self, menu )
            
        
    
    def PageShown( self ):
        
        ManagementPanel.PageShown( self )
        
        CG.client_controller.CallToThread( self.THREADPetitionFetcherAndUploader, self._petition_fetcher_and_uploader_work_lock, self._service )
        
    
    def ProcessCurrentPetition( self ):
        
        if self._current_petition is None:
            
            return
            
        
        jobs = [
            ( self._contents_add, HC.CONTENT_UPDATE_PEND ),
            ( self._contents_delete, HC.CONTENT_UPDATE_PETITION )
        ]
        
        for ( contents_list, action ) in jobs:
            
            for index in range( contents_list.count() ):
                
                content = contents_list.GetData( index )
                
                if contents_list.IsChecked( index ):
                    
                    self._current_petition.Approve( action, content )
                    
                else:
                    
                    self._current_petition.Deny( action, content )
                    
                
            
        
        self._StartUploadingCompletedPetitions( ( self._current_petition, ) )
        
    
    def RefreshQuery( self ):
        
        self._DrawCurrentPetition()
        
    
    def Start( self ):
        
        QP.CallAfter( self._StartFetchNumPetitions )
        
    
    def THREADPetitionFetcherAndUploader( self, work_lock: threading.Lock, service: ClientServices.ServiceRepository ):
        
        def qt_get_work():
            
            fetch_petition_header = None
            outgoing_petition = None
            
            if len( self._petition_headers_we_are_fetching ) > 0:
                
                if CG.client_controller.PageAliveAndNotClosed( self._page_key ):
                    
                    fetch_petition_header = self._petition_headers_we_are_fetching[0]
                    
                elif CG.client_controller.PageDestroyed( self._page_key ):
                    
                    self._petition_headers_we_are_fetching = []
                    
                
            
            if len( self._outgoing_petition_headers_to_petitions ) > 0:
                
                item = list( self._outgoing_petition_headers_to_petitions.keys() )[0]
                
                outgoing_petition = self._outgoing_petition_headers_to_petitions[ item ]
                
            
            return ( fetch_petition_header, outgoing_petition )
            
        
        def qt_petition_cleared( petition: HydrusNetwork.Petition ):
            
            petition_header = petition.GetPetitionHeader()
            
            if petition_header in self._outgoing_petition_headers_to_petitions:
                
                del self._outgoing_petition_headers_to_petitions[ petition_header ]
                
            
            if petition_header in self._failed_outgoing_petition_headers_to_petitions:
                
                del self._failed_outgoing_petition_headers_to_petitions[ petition_header ]
                
            
            if petition_header in self._petition_headers_to_fetched_petitions_cache:
                
                del self._petition_headers_to_fetched_petitions_cache[ petition_header ]
                
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.DeleteDatas( ( petition_header, ) )
                
            
            self._StartFetchNumPetitions()
            
        
        def qt_petition_clear_failed( petition: HydrusNetwork.Petition ):
            
            petition_header = petition.GetPetitionHeader()
            
            if petition_header in self._outgoing_petition_headers_to_petitions:
                
                del self._outgoing_petition_headers_to_petitions[ petition_header ]
                
            
            self._failed_outgoing_petition_headers_to_petitions[ petition_header ] = petition
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.UpdateDatas( ( petition_header, ) )
                
            
        
        def qt_petition_fetch_404( petition_header: HydrusNetwork.PetitionHeader ):
            
            if petition_header in self._petition_headers_we_are_fetching:
                
                self._petition_headers_we_are_fetching.remove( petition_header )
                
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.DeleteDatas( ( petition_header, ) )
                
            
        
        def qt_petition_fetch_failed( petition_header: HydrusNetwork.PetitionHeader ):
            
            if petition_header in self._petition_headers_we_are_fetching:
                
                self._petition_headers_we_are_fetching.remove( petition_header )
                
            
            self._petition_headers_we_failed_to_fetch.add( petition_header )
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petitions_summary_list.UpdateDatas( ( petition_header, ) )
                
            
        
        def qt_petition_fetched( petition: HydrusNetwork.Petition ):
            
            petition_header = petition.GetPetitionHeader()
            
            if petition_header in self._petition_headers_we_are_fetching:
                
                self._petition_headers_we_are_fetching.remove( petition_header )
                
            
            self._petition_headers_we_failed_to_fetch.discard( petition_header )
            
            if self._petitions_summary_list.HasData( petition_header ):
                
                self._petition_headers_to_fetched_petitions_cache[ petition_header ] = petition
                
                self._petitions_summary_list.UpdateDatas( ( petition_header, ) )
                
            
            if self._current_petition is None:
                
                self._HighlightAPetitionIfNeeded()
                
            
        
        with work_lock:
            
            while True:
                
                fetch_petition_header: typing.Optional[ HydrusNetwork.PetitionHeader ] = None
                outgoing_petition: typing.Optional[ HydrusNetwork.Petition ] = None
                
                ( fetch_petition_header, outgoing_petition ) = CG.client_controller.CallBlockingToQt( self, qt_get_work )
                
                if fetch_petition_header is None and outgoing_petition is None:
                    
                    break
                    
                
                if fetch_petition_header is not None:
                    
                    try:
                        
                        request_dict = {
                            'content_type' : fetch_petition_header.content_type,
                            'status' : fetch_petition_header.status,
                            'subject_account_key' : fetch_petition_header.account_key,
                            'reason' : fetch_petition_header.reason
                        }
                        
                        response = service.Request( HC.GET, 'petition', request_dict )
                        
                        petition = response[ 'petition' ]
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_fetched, petition )
                        
                    except HydrusExceptions.NotFoundException:
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_fetch_404, fetch_petition_header )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Failed to fetch a petition!' )
                        HydrusData.ShowException( e )
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_fetch_failed, fetch_petition_header )
                        
                    
                
                if outgoing_petition is not None:
                    
                    try:
                        
                        job_status = ClientThreading.JobStatus( cancellable = True )
                        
                        job_status.SetStatusTitle( 'committing petition' )
                        
                        time_started = HydrusTime.GetNowFloat()
                        
                        try:
                            
                            updates = outgoing_petition.GetCompletedUploadableClientToServerUpdates()
                            
                            num_to_do = len( updates )
                            
                            for ( num_done, update ) in enumerate( updates ):
                                
                                if HydrusTime.TimeHasPassed( time_started + 3 ):
                                    
                                    CG.client_controller.pub( 'message', job_status )
                                    
                                
                                ( i_paused, should_quit ) = job_status.WaitIfNeeded()
                                
                                if should_quit:
                                    
                                    return
                                    
                                
                                service.Request( HC.POST, 'update', { 'client_to_server_update' : update } )
                                
                                content_updates = ClientContentUpdates.ConvertClientToServerUpdateToContentUpdates( update )
                                
                                if len( content_updates ) > 0:
                                    
                                    CG.client_controller.WriteSynchronous( 'content_updates', ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( service.GetServiceKey(), content_updates ) )
                                    
                                
                                job_status.SetStatusText( HydrusData.ConvertValueRangeToPrettyString( num_done, num_to_do ) )
                                job_status.SetVariable( 'popup_gauge_1', ( num_done, num_to_do ) )
                                
                            
                        finally:
                            
                            job_status.FinishAndDismiss()
                            
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_cleared, outgoing_petition )
                        
                    except Exception as e:
                        
                        HydrusData.ShowText( 'Failed to upload a petition!' )
                        HydrusData.ShowException( e )
                        
                        CG.client_controller.CallBlockingToQt( self, qt_petition_clear_failed, outgoing_petition )
                        
                    
                
            
        
    

management_panel_types_to_classes[ ClientGUIManagementController.MANAGEMENT_TYPE_PETITIONS ] = ManagementPanelPetitions

class ManagementPanelQuery( ManagementPanel ):
    
    def __init__( self, parent, page, controller, management_controller: ClientGUIManagementController.ManagementController ):
        
        ManagementPanel.__init__( self, parent, page, controller, management_controller )
        
        file_search_context = self._management_controller.GetVariable( 'file_search_context' )
        
        file_search_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        self._search_enabled = self._management_controller.GetVariable( 'search_enabled' )
        
        self._query_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._query_job_status.Finish()
        
        if self._search_enabled:
            
            self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
            
            synchronised = self._management_controller.GetVariable( 'synchronised' )
            
            self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, self._page_key, file_search_context, media_sort_widget = self._media_sort_widget, media_collect_widget = self._media_collect_widget, media_callable = self._page.GetMedia, synchronised = synchronised )
            
            self._tag_autocomplete.searchCancelled.connect( self._CancelSearch )
            
            self._search_panel.Add( self._tag_autocomplete, CC.FLAGS_EXPAND_BOTH_WAYS )
            
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        if self._search_enabled:
            
            QP.AddToLayout( vbox, self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        if self._search_enabled:
            
            self._tag_autocomplete.searchChanged.connect( self.SearchChanged )
            
            self._tag_autocomplete.locationChanged.connect( self.SetLocationContext )
            
        
    
    def _CancelSearch( self ):
        
        if self._search_enabled:
            
            self._query_job_status.Cancel()
            
            file_search_context = self._tag_autocomplete.GetFileSearchContext()
            
            location_context = file_search_context.GetLocationContext()
            
            self._SetLocationContext( location_context )
            
            panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, [] )
            
            panel.SetEmptyPageStatusOverride( 'search cancelled!' )
            
            self._page.SwapMediaPanel( panel )
            
            self._page_state = CC.PAGE_STATE_SEARCHING_CANCELLED
            
            self._UpdateCancelButton()
            
        
    
    def _GetDefaultEmptyPageStatusOverride( self ) -> str:
        
        return 'no search done yet'
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer ):
        
        self._current_selection_tags_box = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( self, 'selection tags' )
        
        if self._search_enabled:
            
            self._current_selection_tags_list = ListBoxTagsMediaManagementPanel( self._current_selection_tags_box, self._management_controller, self._page_key, tag_autocomplete = self._tag_autocomplete )
            
        else:
            
            self._current_selection_tags_list = ListBoxTagsMediaManagementPanel( self._current_selection_tags_box, self._management_controller, self._page_key )
            
        
        self._current_selection_tags_box.SetTagsBox( self._current_selection_tags_list )
        
        if self._search_enabled:
            
            file_search_context = self._management_controller.GetVariable( 'file_search_context' )
            
            file_search_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
            
            tag_service_key = file_search_context.GetTagContext().service_key
            
            self._current_selection_tags_box.SetTagServiceKey( tag_service_key )
            
            self._tag_autocomplete.tagServiceChanged.connect( self._current_selection_tags_box.SetTagServiceKey )
            
        
        QP.AddToLayout( sizer, self._current_selection_tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _RefreshQuery( self ):
        
        self._controller.ResetIdleTimer()
        
        if self._search_enabled:
            
            file_search_context = self._tag_autocomplete.GetFileSearchContext()
            
            synchronised = self._tag_autocomplete.IsSynchronised()
            
            # a query refresh now undoes paused sync
            if not synchronised:
                
                # this will trigger a refresh of search
                self._tag_autocomplete.SetSynchronised( True )
                
                return
                
            
            interrupting_current_search = not self._query_job_status.IsDone()
            
            self._query_job_status.Cancel()
            
            if len( file_search_context.GetPredicates() ) > 0:
                
                self._query_job_status = ClientThreading.JobStatus( cancellable = True )
                
                sort_by = self._media_sort_widget.GetSort()
                
                self._controller.CallToThread( self.THREADDoQuery, self._controller, self._page_key, self._query_job_status, file_search_context, sort_by )
                
                panel = ClientGUIResults.MediaPanelLoading( self._page, self._page_key, self._management_controller )
                
                self._page_state = CC.PAGE_STATE_SEARCHING
                
            else:
                
                panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, [] )
                
                panel.SetEmptyPageStatusOverride( 'no search' )
                
            
            self._page.SwapMediaPanel( panel )
            
        else:
            
            self._media_sort_widget.BroadcastSort()
            
        
    
    def _UpdateCancelButton( self ):
        
        if self._search_enabled:
            
            if self._query_job_status.IsDone():
                
                self._tag_autocomplete.ShowCancelSearchButton( False )
                
            else:
                
                # don't show it immediately to save on flickeriness on short queries
                
                WAIT_PERIOD = 3.0
                
                search_is_lagging = HydrusTime.TimeHasPassedFloat( self._query_job_status.GetCreationTime() + WAIT_PERIOD )
                
                self._tag_autocomplete.ShowCancelSearchButton( search_is_lagging )
                
            
        
    
    def ConnectMediaPanelSignals( self, media_panel: ClientGUIResults.MediaPanel ):
        
        ManagementPanel.ConnectMediaPanelSignals( self, media_panel )
        
        media_panel.newMediaAdded.connect( self.PauseSearching )
        
    
    def SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._SetLocationContext( location_context )
        
    
    def CleanBeforeClose( self ):
        
        ManagementPanel.CleanBeforeClose( self )
        
        if self._search_enabled:
            
            self._tag_autocomplete.CancelCurrentResultsFetchJob()
            
        
        self._query_job_status.Cancel()
        
    
    def CleanBeforeDestroy( self ):
        
        ManagementPanel.CleanBeforeDestroy( self )
        
        if self._search_enabled:
            
            self._tag_autocomplete.CancelCurrentResultsFetchJob()
            
        
        self._query_job_status.Cancel()
        
    
    def GetPredicates( self ):
        
        if self._search_enabled:
            
            return self._tag_autocomplete.GetPredicates()
            
        else:
            
            return []
            
        
    
    def PageHidden( self ):
        
        ManagementPanel.PageHidden( self )
        
        if self._search_enabled:
            
            self._tag_autocomplete.SetForceDropdownHide( True )
            
        
    
    def PageShown( self ):
        
        ManagementPanel.PageShown( self )
        
        if self._search_enabled:
            
            self._tag_autocomplete.SetForceDropdownHide( False )
            
        
    
    def PauseSearching( self ):
        
        if self._search_enabled:
            
            self._tag_autocomplete.SetSynchronised( False )
            
        
    
    def RefreshQuery( self ):
        
        self._RefreshQuery()
        
    
    def SearchChanged( self, file_search_context: ClientSearch.FileSearchContext ):
        
        if self._search_enabled:
            
            file_search_context = self._tag_autocomplete.GetFileSearchContext()
            
            self._management_controller.SetVariable( 'file_search_context', file_search_context.Duplicate() )
            
            location_context = file_search_context.GetLocationContext()
            
            self._SetLocationContext( location_context )
            
            synchronised = self._tag_autocomplete.IsSynchronised()
            
            self._management_controller.SetVariable( 'synchronised', synchronised )
            
            self._management_controller.SetDirty()
            
            if synchronised:
                
                self._RefreshQuery()
                
            else:
                
                interrupting_current_search = not self._query_job_status.IsDone()
                
                if interrupting_current_search:
                    
                    self._CancelSearch()
                    
                
            
        
    
    def SetSearchFocus( self ):
        
        if self._search_enabled:
            
            ClientGUIFunctions.SetFocusLater( self._tag_autocomplete )
            
        
    
    def ShowFinishedQuery( self, query_job_status, media_results ):
        
        if query_job_status == self._query_job_status:
            
            location_context = self._management_controller.GetLocationContext()
            
            panel = ClientGUIResults.MediaPanelThumbnails( self._page, self._page_key, self._management_controller, media_results )
            
            panel.SetEmptyPageStatusOverride( 'no files found for this search' )
            
            panel.Collect( self._media_collect_widget.GetValue() )
            
            panel.Sort( self._media_sort_widget.GetSort() )
            
            self._page.SwapMediaPanel( panel )
            
            self._page_state = CC.PAGE_STATE_NORMAL
            
        
    
    def Start( self ):
        
        file_search_context = self._management_controller.GetVariable( 'file_search_context' )
        
        file_search_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        initial_predicates = file_search_context.GetPredicates()
        
        if len( initial_predicates ) > 0 and not file_search_context.IsComplete():
            
            QP.CallAfter( self.RefreshQuery )
            
        
    
    def THREADDoQuery( self, controller, page_key, query_job_status, file_search_context: ClientSearch.FileSearchContext, sort_by ):
        
        def qt_code():
            
            query_job_status.Finish()
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self.ShowFinishedQuery( query_job_status, media_results )
            
        
        QUERY_CHUNK_SIZE = 256
        
        CG.client_controller.file_viewing_stats_manager.Flush()
        
        query_hash_ids = controller.Read( 'file_query_ids', file_search_context, job_status = query_job_status, limit_sort_by = sort_by )
        
        if query_job_status.IsCancelled():
            
            return
            
        
        media_results = []
        
        for sub_query_hash_ids in HydrusLists.SplitListIntoChunks( query_hash_ids, QUERY_CHUNK_SIZE ):
            
            if query_job_status.IsCancelled():
                
                return
                
            
            more_media_results = controller.Read( 'media_results_from_ids', sub_query_hash_ids )
            
            media_results.extend( more_media_results )
            
            controller.pub( 'set_num_query_results', page_key, len( media_results ), len( query_hash_ids ) )
            
            controller.WaitUntilViewFree()
            
        
        file_search_context.SetComplete()
        
        self._management_controller.SetVariable( 'file_search_context', file_search_context.Duplicate() )
        
        self._management_controller.SetDirty()
        
        QP.CallAfter( qt_code )
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateCancelButton()
        
        if self._search_enabled:
            
            self._tag_autocomplete.REPEATINGPageUpdate()
            
        
    
management_panel_types_to_classes[ ClientGUIManagementController.MANAGEMENT_TYPE_QUERY ] = ManagementPanelQuery
