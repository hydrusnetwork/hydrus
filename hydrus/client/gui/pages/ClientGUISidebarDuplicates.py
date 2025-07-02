import collections.abc

from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvas
from hydrus.client.gui.canvas import ClientGUICanvasFrame
from hydrus.client.gui.duplicates import ClientGUIDuplicatesAutoResolution
from hydrus.client.gui.duplicates import ClientGUIDuplicatesContentMergeOptions
from hydrus.client.gui.duplicates import ClientGUIPotentialDuplicatesSearchContext
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelThumbnails
from hydrus.client.gui.pages import ClientGUISidebarCore
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia

class SidebarDuplicateFilter( ClientGUISidebarCore.Sidebar ):
    
    SHOW_COLLECT = False
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
        self._duplicates_manager = ClientDuplicates.DuplicatesManager.instance()
        
        self._similar_files_maintenance_status = None
        self._duplicates_manager_is_fetching_maintenance_numbers = False
        self._potential_file_search_currently_happening = False
        self._maintenance_numbers_need_redrawing = True
        
        self._have_done_first_maintenance_numbers_show = False
        
        new_options = CG.client_controller.new_options
        
        #
        
        self._main_notebook = ClientGUICommon.BetterNotebook( self )
        
        # TODO: make these two panels into their own classes and rewire everything into panel signals
        self._main_left_panel = QW.QWidget( self._main_notebook )
        self._main_right_panel = QW.QWidget( self._main_notebook )
        
        self._duplicates_auto_resolution_panel = ClientGUIDuplicatesAutoResolution.ReviewDuplicatesAutoResolutionPanel( self )
        
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
        
        self._options_panel = ClientGUICommon.StaticBox( self._main_right_panel, 'merge options' )
        
        menu_items = []
        
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'this is better\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_BETTER ) ) )
        menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'same quality\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_SAME_QUALITY ) ) )
        
        if new_options.GetBoolean( 'advanced_mode' ):
            
            menu_items.append( ( 'normal', 'edit duplicate metadata merge options for \'alternates\' (advanced!)', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_ALTERNATE ) ) )
            
        
        self._edit_merge_options = ClientGUIMenuButton.MenuButton( self._options_panel, 'edit default duplicate metadata merge options', menu_items )
        
        #
        
        potential_duplicates_search_context = page_manager.GetVariable( 'potential_duplicates_search_context' )
        
        if self._page_manager.HasVariable( 'synchronised' ):
            
            synchronised = self._page_manager.GetVariable( 'synchronised' )
            
        else:
            
            synchronised = True
            
        
        self._potential_duplicates_search_context = ClientGUIPotentialDuplicatesSearchContext.EditPotentialDuplicatesSearchContextPanel( self, potential_duplicates_search_context, synchronised = synchronised, page_key = self._page_key )
        
        self._potential_duplicates_search_context.valueChanged.connect( self._PotentialDuplicatesSearchContextChanged )
        
        #
        
        self._filtering_panel = ClientGUICommon.StaticBox( self._main_right_panel, 'duplicate filter' )
        
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
        self._main_notebook.addTab( self._duplicates_auto_resolution_panel, 'auto-resolution' )
        
        self._main_notebook.setCurrentWidget( self._main_right_panel )
        
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
        vbox.addStretch( 0 )
        
        self._main_left_panel.setLayout( vbox )
        
        #
        
        self._options_panel.Add( self._edit_merge_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._filtering_panel.Add( self._launch_filter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        random_filtering_panel.Add( self._show_some_dupes, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_same_quality_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_alternates_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_false_positives_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._options_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._potential_duplicates_search_context, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, random_filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self._main_right_panel.setLayout( vbox )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._main_notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        CG.client_controller.sub( self, 'NotifyNewMaintenanceNumbers', 'new_similar_files_maintenance_numbers' )
        CG.client_controller.sub( self, 'NotifyNewPotentialsSearchNumbers', 'new_similar_files_potentials_search_numbers' )
        
        self._max_hamming_distance_for_potential_discovery_spinctrl.valueChanged.connect( self.MaxHammingDistanceForPotentialDiscoveryChanged )
        
        self._potential_duplicates_search_context.restartedSearch.connect( self._NotifyPotentialsSearchStarted )
        self._potential_duplicates_search_context.thisSearchHasPairs.connect( self._NotifyPotentialsSearchHasPairs )
        
        self._main_notebook.currentChanged.connect( self._CurrentPageChanged )
        
        self._CurrentPageChanged()
        
    
    def _CurrentPageChanged( self ):
        
        page = self._main_notebook.currentWidget()
        
        if page == self._main_right_panel:
            
            self._potential_duplicates_search_context.PageShown()
            
        else:
            
            self._potential_duplicates_search_context.PageHidden()
            
        
    
    def _EditMergeOptions( self, duplicate_type ):
        
        new_options = CG.client_controller.new_options
        
        duplicate_content_merge_options = new_options.GetDuplicateContentMergeOptions( duplicate_type )
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( self, 'edit duplicate merge options' ) as dlg:
            
            panel = ClientGUIScrolledPanels.EditSingleCtrlPanel( dlg )
            
            ctrl = ClientGUIDuplicatesContentMergeOptions.EditDuplicateContentMergeOptionsWidget( panel, duplicate_type, duplicate_content_merge_options )
            
            panel.SetControl( ctrl )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.DialogCode.Accepted:
                
                duplicate_content_merge_options = ctrl.GetValue()
                
                new_options.SetDuplicateContentMergeOptions( duplicate_type, duplicate_content_merge_options )
                
            
        
    
    def _LaunchFilter( self ):
        
        potential_duplicates_search_context = self._potential_duplicates_search_context.GetValue()
        
        canvas_frame = ClientGUICanvasFrame.CanvasFrame( self.window() )
        
        canvas_window = ClientGUICanvas.CanvasFilterDuplicates( canvas_frame, potential_duplicates_search_context )
        
        canvas_window.showPairInPage.connect( self._ShowPairInPage )
        
        canvas_window.canvasWithHoversExiting.connect( CG.client_controller.gui.NotifyMediaViewerExiting )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _NotifyPotentialsSearchStarted( self ):
        
        self._launch_filter.setEnabled( False )
        self._show_some_dupes.setEnabled( False )
        
    
    def _NotifyPotentialsSearchHasPairs( self ):
        
        self._launch_filter.setEnabled( True )
        self._show_some_dupes.setEnabled( True )
        
    
    def _PotentialDuplicatesSearchContextChanged( self ):
        
        potential_duplicates_search_context = self._potential_duplicates_search_context.GetValue()
        
        self._page_manager.SetVariable( 'potential_duplicates_search_context', potential_duplicates_search_context )
        
        synchronised = self._potential_duplicates_search_context.IsSynchronised()
        
        self._page_manager.SetVariable( 'synchronised', synchronised )
        
        self.locationChanged.emit( potential_duplicates_search_context.GetFileSearchContext1().GetLocationContext() )
        self.tagContextChanged.emit( potential_duplicates_search_context.GetFileSearchContext1().GetTagContext() )
        
    
    def _ResetUnknown( self ):
        
        text = 'ADVANCED TOOL: This will delete all the current potential duplicate pairs. All files that may be similar will be queued for search again.'
        text += '\n' * 2
        text += 'This can be useful if you know you have database damage and need to reset and re-search everything, or if you have accidentally searched too broadly and are now swamped with too many false positives. It is not useful for much else.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'delete_potential_duplicate_pairs' )
            
            self._duplicates_manager.RefreshMaintenanceNumbers()
            
        
    
    def _SetCurrentMediaAs( self, duplicate_type ):
        
        media_panel = self._page.GetMediaResultsPanel()
        
        change_made = media_panel.SetDuplicateStatusForAll( duplicate_type )
        
        if change_made:
            
            self._ShowRandomPotentialDupes()
            
        
    
    def _SetSearchDistance( self, value ):
        
        self._max_hamming_distance_for_potential_discovery_spinctrl.setValue( value )
        
        self._UpdateMaintenanceStatus()
        
    
    def _ShowPairInPage( self, media: collections.abc.Collection[ ClientMedia.MediaSingleton ] ):
        
        media_results = [ m.GetMediaResult() for m in media ]
        
        self._page.GetMediaResultsPanel().AddMediaResults( self._page_key, media_results )
        
    
    def _ShowPotentialDupes( self, hashes ):
        
        if len( hashes ) > 0:
            
            media_results = CG.client_controller.Read( 'media_results', hashes, sorted = True )
            
        else:
            
            media_results = []
            
        
        panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
        
        panel.SetEmptyPageStatusOverride( 'no dupes found' )
        
        self._page.SwapMediaResultsPanel( panel )
        
        self._page_state = CC.PAGE_STATE_NORMAL
        
    
    def _ShowRandomPotentialDupes( self ):
        
        potential_duplicates_search_context = self._potential_duplicates_search_context.GetValue()
        
        self._page_state = CC.PAGE_STATE_SEARCHING
        
        hashes = CG.client_controller.Read( 'random_potential_duplicate_hashes', potential_duplicates_search_context )
        
        if len( hashes ) == 0:
            
            self._potential_duplicates_search_context.NotifyNewDupePairs()
            
        else:
            
            self._ShowPotentialDupes( hashes )
            
        
    
    def _UpdateMaintenanceStatus( self ):
        
        self._refresh_maintenance_button.setEnabled( not ( self._duplicates_manager_is_fetching_maintenance_numbers or self._potential_file_search_currently_happening ) )
        
        if self._similar_files_maintenance_status is None:
            
            self._search_button.setEnabled( False )
            
            return
            
        
        searched_distances_to_count = self._similar_files_maintenance_status
        
        self._cog_button.setEnabled( True )
        
        total_num_files = sum( searched_distances_to_count.values() )
        
        self._eligible_files.setText( '{} eligible files in the system.'.format(HydrusNumbers.ToHumanInt(total_num_files)) )
        
        self._max_hamming_distance_for_potential_discovery_button.setEnabled( True )
        self._max_hamming_distance_for_potential_discovery_spinctrl.setEnabled( True )
        
        options_search_distance = CG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
        
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
        
        page_name = 'preparation'
        
        if not_all_files_searched:
            
            if num_searched == 0:
                
                self._num_searched.SetValue( 'Have not yet searched at this distance.', 0, total_num_files )
                
            else:
                
                self._num_searched.SetValue( 'Searched ' + HydrusNumbers.ValueRangeToPrettyString( num_searched, total_num_files ) + ' files at this distance.', num_searched, total_num_files )
                
            
            show_page_name = True
            
            percent_done = num_searched / total_num_files
            
            if CG.client_controller.new_options.GetBoolean( 'hide_duplicates_needs_work_message_when_reasonably_caught_up' ) and percent_done > 0.99:
                
                show_page_name = False
                
            
            if show_page_name:
                
                percent_string = HydrusNumbers.FloatToPercentage(percent_done)
                
                if percent_string == '100.0%':
                    
                    percent_string = '99.9%'
                    
                
                page_name = f'preparation ({percent_string} done)'
                
            
        else:
            
            self._num_searched.SetValue( 'All potential duplicates found at this distance.', total_num_files, total_num_files )
            
        
        self._main_notebook.setTabText( 0, page_name )
        
    
    def MaxHammingDistanceForPotentialDiscoveryChanged( self ):
        
        search_distance = self._max_hamming_distance_for_potential_discovery_spinctrl.value()
        
        CG.client_controller.new_options.SetInteger( 'similar_files_duplicate_pairs_search_distance', search_distance )
        
        CG.client_controller.pub( 'new_similar_files_maintenance_numbers' )
        
        self._UpdateMaintenanceStatus()
        
    
    def NotifyNewMaintenanceNumbers( self ):
        
        self._maintenance_numbers_need_redrawing = True
        
    
    def NotifyNewPotentialsSearchNumbers( self ):
        
        self._potential_duplicates_search_context.NotifyNewDupePairs()
        
    
    def PageHidden( self ):
        
        super().PageHidden()
        
        page = self._main_notebook.currentWidget()
        
        if page == self._main_right_panel:
            
            self._potential_duplicates_search_context.PageHidden()
            
        
    
    def PageShown( self ):
        
        super().PageShown()
        
        page = self._main_notebook.currentWidget()
        
        if page == self._main_right_panel:
            
            self._potential_duplicates_search_context.PageShown()
            
        
    
    def RefreshDuplicateNumbers( self ):
        
        self._potential_duplicates_search_context.NotifyNewDupePairs()
        
    
    def RefreshQuery( self ):
        
        self._potential_duplicates_search_context.NotifyNewDupePairs()
        
    
    def REPEATINGPageUpdate( self ):
        
        if self._maintenance_numbers_need_redrawing:
            
            ( self._similar_files_maintenance_status, self._duplicates_manager_is_fetching_maintenance_numbers, self._potential_file_search_currently_happening ) = self._duplicates_manager.GetMaintenanceNumbers()
            
            self._maintenance_numbers_need_redrawing = False
            
            self._UpdateMaintenanceStatus()
            
        
        self._potential_duplicates_search_context.REPEATINGPageUpdate()
        
    
