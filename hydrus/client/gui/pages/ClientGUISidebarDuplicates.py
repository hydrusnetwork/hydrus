import collections.abc

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.duplicates import ClientPotentialDuplicatesManager
from hydrus.client.duplicates import ClientPotentialDuplicatesPairFactory
from hydrus.client.gui import ClientGUIAsync
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUITopLevelWindowsPanels
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.canvas import ClientGUICanvasDuplicates
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
from hydrus.client.search import ClientSearchTagContext

class FilterPanel( QW.QWidget ):
    
    locationChanged = QC.Signal( ClientLocation.LocationContext )
    tagContextChanged = QC.Signal( ClientSearchTagContext.TagContext )
    setCurrentMediaAs = QC.Signal( int )
    showPotentialDupes = QC.Signal( list )
    setPageState = QC.Signal( int )
    showPairInPage = QC.Signal( list )
    
    def __init__( self, parent: QW.QWidget, page_manager: ClientGUIPageManager.PageManager, media_sort_widget, make_tags_box_callable ):
        
        super().__init__( parent )
        
        self._page_manager = page_manager
        self._page_key = self._page_manager.GetVariable( 'page_key' )
        
        new_options = CG.client_controller.new_options
        
        #
        
        potential_duplicates_search_context = self._page_manager.GetVariable( 'potential_duplicates_search_context' )
        
        if self._page_manager.HasVariable( 'synchronised' ):
            
            synchronised = self._page_manager.GetVariable( 'synchronised' )
            
        else:
            
            synchronised = True
            
        
        self._potential_duplicates_search_context = ClientGUIPotentialDuplicatesSearchContext.EditPotentialDuplicatesSearchContextPanel( self, potential_duplicates_search_context, synchronised = synchronised, page_key = self._page_key, collapsible = True )
        
        self._potential_duplicates_search_context.valueChanged.connect( self._PotentialDuplicatesSearchContextChanged )
        
        #
        
        self._filtering_panel = ClientGUICommon.StaticBox( self, 'duplicate filter', start_expanded = True, can_expand = True )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'edit duplicate metadata merge options for \'this is better\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_BETTER ) ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'edit duplicate metadata merge options for \'same quality\'', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_SAME_QUALITY ) ) )
        
        if new_options.GetBoolean( 'advanced_mode' ):
            
            menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'edit duplicate metadata merge options for \'alternates\' (advanced!)', 'edit what content is merged when you filter files', HydrusData.Call( self._EditMergeOptions, HC.DUPLICATE_ALTERNATE ) ) )
            
        
        self._edit_merge_options = ClientGUIMenuButton.MenuButton( self._filtering_panel, 'edit default duplicate metadata merge options', menu_template_items )
        
        duplicate_pair_sort_type = page_manager.GetVariable( 'duplicate_pair_sort_type' )
        duplicate_pair_sort_asc = page_manager.GetVariable( 'duplicate_pair_sort_asc' )
        
        self._potential_duplicates_sort_widget = ClientGUIPotentialDuplicatesSearchContext.PotentialDuplicatesSortWidget( self._filtering_panel, duplicate_pair_sort_type, duplicate_pair_sort_asc )
        
        self._potential_duplicates_sort_widget.valueChanged.connect( self._PotentialDuplicatesSortChanged )
        
        filter_group_mode = page_manager.GetVariable( 'filter_group_mode' )
        
        choice_tuples = [
            ( 'mixed pairs', False ),
            ( 'group mode', True )
        ]
        
        self._filter_group_mode = ClientGUIMenuButton.MenuChoiceButton( self, choice_tuples )
        self._filter_group_mode.setToolTip( ClientGUIFunctions.WrapToolTip( 'In group mode, each batch in the duplicate filter will include one entire group of files that are transitively related, much like you see when hitting "show some random potential duplicates". The filter will iteratively work on the group until all relationships are cleared, and then move on to another. Groups are selected randomly.' ) )
        
        self._filter_group_mode.SetValue( filter_group_mode )
        
        self._filter_group_mode.valueChanged.connect( self._FilterGroupModeChanged )
        
        self._launch_filter = ClientGUICommon.BetterButton( self._filtering_panel, 'launch the filter', self._LaunchFilter )
        
        #
        
        random_filtering_panel = ClientGUICommon.StaticBox( self, 'quick and dirty processing', start_expanded = True, can_expand = True )
        
        self._show_some_dupes = ClientGUICommon.BetterButton( random_filtering_panel, 'show some random potential duplicates', self.ShowRandomPotentialDupes )
        tt = 'This will randomly select a file in the current pair search and show you all the directly or transitively potential files that are also in the same domain. Sometimes this will just be a pair, others it might be a hundred alternates, but they should all look similar.'
        self._show_some_dupes.setToolTip( ClientGUIFunctions.WrapToolTip( tt ) )
        
        self._set_random_as_same_quality_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as duplicates of the same quality', self._SetCurrentMediaAs, HC.DUPLICATE_SAME_QUALITY )
        self._set_random_as_alternates_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as all related alternates', self._SetCurrentMediaAs, HC.DUPLICATE_ALTERNATE )
        self._set_random_as_false_positives_button = ClientGUICommon.BetterButton( random_filtering_panel, 'set current media as not related/false positive', self._SetCurrentMediaAs, HC.DUPLICATE_FALSE_POSITIVE )
        
        #
        
        self._filtering_panel.Add( self._edit_merge_options, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._potential_duplicates_sort_widget, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._filter_group_mode, CC.FLAGS_CENTER )
        
        self._filtering_panel.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._filtering_panel.Add( self._launch_filter, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        random_filtering_panel.Add( media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        # random_filtering_panel.Add( self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR ) # hidden for now
        random_filtering_panel.Add( self._show_some_dupes, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_same_quality_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_alternates_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        random_filtering_panel.Add( self._set_random_as_false_positives_button, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._potential_duplicates_search_context, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, random_filtering_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        make_tags_box_callable( vbox )
        
        self.setLayout( vbox )
        
        #
        
        self._potential_duplicates_search_context.restartedSearch.connect( self._NotifyPotentialsSearchStarted )
        self._potential_duplicates_search_context.thisSearchDefinitelyHasNoPairs.connect( self._NotifyPotentialsSearchDefinitelyHasNoPairs )
        
    
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
                
            
        
    
    def _FilterGroupModeChanged( self ):
        
        filter_group_mode = self._filter_group_mode.GetValue()
        
        self._page_manager.SetVariable( 'filter_group_mode', filter_group_mode )
        
    
    def _LaunchFilter( self ):
        
        potential_duplicates_search_context = self._potential_duplicates_search_context.GetValue()
        
        ( duplicate_pair_sort_type, duplicate_pair_sort_asc ) = self._potential_duplicates_sort_widget.GetValue()
        filter_group_mode = self._filter_group_mode.GetValue()
        
        if filter_group_mode:
            
            potential_duplicate_pair_factory = ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactoryDBGroupMode(
                potential_duplicates_search_context,
                duplicate_pair_sort_type,
                duplicate_pair_sort_asc
            )
            
        else:
            
            no_more_than = CG.client_controller.new_options.GetInteger( 'duplicate_filter_max_batch_size' )
            
            potential_duplicate_pair_factory = ClientPotentialDuplicatesPairFactory.PotentialDuplicatePairFactoryDBMixed(
                potential_duplicates_search_context,
                duplicate_pair_sort_type,
                duplicate_pair_sort_asc,
                no_more_than
            )
            
        
        canvas_frame = ClientGUICanvasFrame.CanvasFrame( self.window() )
        
        canvas_window = ClientGUICanvasDuplicates.CanvasFilterDuplicates( canvas_frame, potential_duplicate_pair_factory )
        
        canvas_window.showPairInPage.connect( self.showPairInPage )
        
        canvas_window.canvasWithHoversExiting.connect( CG.client_controller.gui.NotifyMediaViewerExiting )
        
        canvas_frame.SetCanvas( canvas_window )
        
    
    def _NotifyPotentialsSearchStarted( self ):
        
        self._launch_filter.setEnabled( True )
        self._show_some_dupes.setEnabled( True )
        
    
    def _NotifyPotentialsSearchDefinitelyHasNoPairs( self ):
        
        self._launch_filter.setEnabled( False )
        self._show_some_dupes.setEnabled( False )
        
    
    def _PotentialDuplicatesSearchContextChanged( self ):
        
        potential_duplicates_search_context = self._potential_duplicates_search_context.GetValue()
        
        self._page_manager.SetVariable( 'potential_duplicates_search_context', potential_duplicates_search_context )
        
        synchronised = self._potential_duplicates_search_context.IsSynchronised()
        
        self._page_manager.SetVariable( 'synchronised', synchronised )
        
        self.locationChanged.emit( potential_duplicates_search_context.GetLocationContext() )
        self.tagContextChanged.emit( potential_duplicates_search_context.GetTagContext() )
        
    
    def _PotentialDuplicatesSortChanged( self ):
        
        ( duplicate_pair_sort_type, duplicate_pair_sort_asc ) = self._potential_duplicates_sort_widget.GetValue()
        
        self._page_manager.SetVariable( 'duplicate_pair_sort_type', duplicate_pair_sort_type )
        self._page_manager.SetVariable( 'duplicate_pair_sort_asc', duplicate_pair_sort_asc )
        
    
    def _SetCurrentMediaAs( self, duplicate_type ):
        
        self.setCurrentMediaAs.emit( duplicate_type )
        
    
    def PageHidden( self ):
        
        self._potential_duplicates_search_context.PageHidden()
        
    
    def PageShown( self ):
        
        self._potential_duplicates_search_context.PageShown()
        
    
    def RefreshDuplicateNumbers( self ):
        
        self._potential_duplicates_search_context.ForceRefreshNumbers()
        
    
    def ShowRandomPotentialDupes( self ):
        
        def work_callable():
            
            hashes = CG.client_controller.Read( 'random_potential_duplicate_hashes', potential_duplicates_search_context )
            
            return hashes
            
        
        def publish_callable( hashes ):
            
            self._show_some_dupes.setEnabled( True )
            
            self.setPageState.emit( CC.PAGE_STATE_NORMAL )
            
            if len( hashes ) == 0:
                
                ClientGUIDialogsMessage.ShowInformation( self, 'No potential files in this search!' )
                
                self._potential_duplicates_search_context.ForceRefreshNumbers()
                
            else:
                
                self.showPotentialDupes.emit( hashes )
                
            
        
        self._show_some_dupes.setEnabled( False )
        
        self.setPageState.emit( CC.PAGE_STATE_SEARCHING )
        
        potential_duplicates_search_context = self._potential_duplicates_search_context.GetValue()
        
        ClientGUIAsync.AsyncQtJob( self, work_callable, publish_callable ).start()
        
    
    def REPEATINGPageUpdate( self ):
        
        self._potential_duplicates_search_context.REPEATINGPageUpdate()
        
    

class PreparationPanel( QW.QWidget ):
    
    pageTabNameChanged = QC.Signal( str )
    
    def __init__( self, parent: QW.QWidget ):
        
        super().__init__( parent )
        
        menu_template_items = []
        
        page_func = HydrusData.Call( ClientGUIDialogsQuick.OpenDocumentation, self, HC.DOCUMENTATION_DUPLICATES )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'open the html duplicates help', 'Open the help page for duplicates processing in your web browser.', page_func ) )
        
        self._help_button = ClientGUIMenuButton.MenuIconButton( self, CC.global_icons().help, menu_template_items )
        
        #
        
        self._searching_panel = ClientGUICommon.StaticBox( self, 'potential duplicate pair discovery' )
        
        self._refresh_maintenance_button = ClientGUICommon.IconButton( self._searching_panel, CC.global_icons().refresh, self._RefreshMaintenanceNumbers )
        
        #
        
        menu_template_items = []
        
        submenu_template_items = []
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'maintain_similar_files_duplicate_pairs_during_idle' )
        check_manager.AddNotifyCall( CG.client_controller.potential_duplicates_manager.Wake )
        
        submenu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'during idle time', 'Tell the client to find potential duplicate pairs in its idle time maintenance.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerOptions( 'maintain_similar_files_duplicate_pairs_during_active' )
        check_manager.AddNotifyCall( CG.client_controller.potential_duplicates_manager.Wake )
        
        submenu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'during normal time', 'Tell the client to find potential duplicate pairs all the time.', check_manager ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSubmenu( 'search for potential duplicate pairs', submenu_template_items ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'regenerate search tree', 'This will clear and regenerate the search tree. Useful if it appears to have orphan branches.', self._RegenerateSimilarFilesTree ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'regenerate search numbers', 'This will clear and regenerate the cache of the counts of which files have been searched at particular distances. Only useful if there is a miscount.', self._RegenerateMaintenanceNumbers ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'resync potential duplicate pairs to storage', 'This will clear out any potential duplicate pairs where one of the files has been physically deleted.', self._ResyncPotentialPairsToHydrusLocalFileStorage ) )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemSeparator() )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'delete all potential duplicate pairs and re-search', 'This will delete all the discovered potential duplicate pairs. All files that may have potential pairs will be queued up for similar file search again.', self._ResetPotentialDuplicates ) )
        
        self._cog_button = ClientGUIMenuButton.CogIconButton( self._searching_panel, menu_template_items )
        
        #
        
        self._eligible_files = ClientGUICommon.BetterStaticText( self._searching_panel, ellipsize_end = True )
        
        menu_template_items = []
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'exact match', 'Search for exact matches.', HydrusData.Call( self._SetSearchDistance, CC.HAMMING_EXACT_MATCH ) ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'very similar', 'Search for very similar files.', HydrusData.Call( self._SetSearchDistance, CC.HAMMING_VERY_SIMILAR ) ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'similar', 'Search for similar files.', HydrusData.Call( self._SetSearchDistance, CC.HAMMING_SIMILAR ) ) )
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCall( 'speculative', 'Search for files that are probably similar.', HydrusData.Call( self._SetSearchDistance, CC.HAMMING_SPECULATIVE ) ) )
        
        self._max_hamming_distance_for_potential_discovery_button = ClientGUIMenuButton.MenuButton( self._searching_panel, 'similarity', menu_template_items )
        
        self._max_hamming_distance_for_potential_discovery_spinctrl = ClientGUICommon.BetterSpinBox( self._searching_panel, min=0, max=64, width = 50 )
        self._max_hamming_distance_for_potential_discovery_spinctrl.setToolTip( ClientGUIFunctions.WrapToolTip( 'The max "hamming distance" allowed in the search. The higher you go, the slower the search and the more false positives.' ) )
        self._max_hamming_distance_for_potential_discovery_spinctrl.setSingleStep( 2 )
        
        self._num_searched = ClientGUICommon.TextAndGauge( self._searching_panel )
        
        self._start_search_button = ClientGUICommon.IconButton( self._searching_panel, CC.global_icons().play, self._StartWorkingHard )
        self._start_search_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Go/work harder!' ) )
        self._pause_search_button = ClientGUICommon.IconButton( self._searching_panel, CC.global_icons().pause, self._StopWorkingHard )
        self._pause_search_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Stop/pump the breaks!' ) )
        
        self._start_search_button.setEnabled( False )
        self._pause_search_button.setVisible( False )
        
        #
        
        distance_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( distance_hbox, ClientGUICommon.BetterStaticText(self._searching_panel,label='search distance: '), CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( distance_hbox, self._max_hamming_distance_for_potential_discovery_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( distance_hbox, self._max_hamming_distance_for_potential_discovery_spinctrl, CC.FLAGS_CENTER_PERPENDICULAR )
        
        num_files_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( num_files_hbox, self._num_searched, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( num_files_hbox, self._start_search_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( num_files_hbox, self._pause_search_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        info_hbox = QP.HBoxLayout()
        
        QP.AddToLayout( info_hbox, self._eligible_files, CC.FLAGS_CENTER_PERPENDICULAR_EXPAND_DEPTH )
        QP.AddToLayout( info_hbox, self._refresh_maintenance_button, CC.FLAGS_CENTER_PERPENDICULAR )
        QP.AddToLayout( info_hbox, self._cog_button, CC.FLAGS_CENTER_PERPENDICULAR )
        
        self._searching_panel.Add( info_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._searching_panel.Add( distance_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        self._searching_panel.Add( num_files_hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._help_button, CC.FLAGS_ON_RIGHT )
        QP.AddToLayout( vbox, self._searching_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        vbox.addStretch( 0 )
        
        self.setLayout( vbox )
        
        #
        
        self._maintenance_status_updater = self._InitialiseMaintenanceStatusUpdater()
        
        CG.client_controller.sub( self, 'NotifyNewMaintenanceNumbers', 'new_similar_files_maintenance_numbers' )
        
        self._max_hamming_distance_for_potential_discovery_spinctrl.valueChanged.connect( self.MaxHammingDistanceForPotentialDiscoveryChanged )
        
        self._maintenance_status_updater.update()
        
    
    def _InitialiseMaintenanceStatusUpdater( self ):
        
        def loading_callable():
            
            pass
            
        
        def work_callable( args ):
            
            searched_distances_to_count = ClientPotentialDuplicatesManager.PotentialDuplicatesMaintenanceNumbersStore.instance().GetMaintenanceNumbers()
            
            return searched_distances_to_count
            
        
        def publish_callable( searched_distances_to_count ):
            
            total_num_files = sum( searched_distances_to_count.values() )
            
            self._eligible_files.setText( '{} eligible files in the system.'.format(HydrusNumbers.ToHumanInt(total_num_files)) )
            
            search_distance = CG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
            
            num_searched = sum( ( count for ( value, count ) in searched_distances_to_count.items() if value >= search_distance ) )
            
            not_all_files_searched = num_searched < total_num_files
            
            self._start_search_button.setEnabled( not_all_files_searched )
            
            page_name = 'preparation'
            
            if not_all_files_searched:
                
                if num_searched == 0:
                    
                    self._num_searched.SetValue( 'Have not yet searched at this distance.', 0, total_num_files )
                    
                else:
                    
                    self._num_searched.SetValue( 'Searched ' + HydrusNumbers.ValueRangeToPrettyString( num_searched, total_num_files ) + ' files at this distance.', num_searched, total_num_files )
                    
                
                show_percentage_page_name = True
                
                percent_done = num_searched / total_num_files
                
                if CG.client_controller.new_options.GetBoolean( 'hide_duplicates_needs_work_message_when_reasonably_caught_up' ) and percent_done > 0.99:
                    
                    show_percentage_page_name = False
                    
                
                if show_percentage_page_name:
                    
                    percent_string = HydrusNumbers.FloatToPercentage( percent_done )
                    
                    if percent_string == '100.0%':
                        
                        percent_string = '99.9%'
                        
                    
                    page_name = f'preparation ({percent_string} done)'
                    
                
            else:
                
                self._num_searched.SetValue( 'All potential duplicates found at this distance.', total_num_files, total_num_files )
                
            
            self.pageTabNameChanged.emit( page_name )
            
        
        return ClientGUIAsync.AsyncQtUpdater( 'duplicates page preparation searched distance counts', self, loading_callable, work_callable, publish_callable )
        
    
    def _RefreshMaintenanceNumbers( self ):
        
        ClientPotentialDuplicatesManager.PotentialDuplicatesMaintenanceNumbersStore.instance().RefreshMaintenanceNumbers()
        
        self._maintenance_status_updater.update()
        
        CG.client_controller.potential_duplicates_manager.WakeIfNotWorking()
        
    
    def _RegenerateMaintenanceNumbers( self ):
        
        text = 'The store of how many files have been searched at each distance has cached numbers. If you believe the count is incorrect, hit this and they will be regenerated from source. Correcting a miscount is the only purpose of this task.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'regenerate_similar_files_search_count_numbers' )
            
            self._RefreshMaintenanceNumbers()
            
        
    
    def _RegenerateSimilarFilesTree( self ):
        
        message = 'This will delete and then recreate the similar files search tree. This is useful if it has orphans or if you suspect it has become unbalanced in a way that maintenance cannot correct.'
        message += '\n' * 2
        message += 'If you have a lot of files, it can take a little while, during which the gui may hang.'
        message += '\n' * 2
        message += 'If you do not have a specific reason to run this, it is pointless.'
        
        ( result, was_cancelled ) = ClientGUIDialogsQuick.GetYesNo( self, message, yes_label = 'do it', no_label = 'forget it', check_for_cancelled = True )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'regenerate_similar_files_tree' )
            
        
    
    def _ResetPotentialDuplicates( self ):
        
        text = 'ADVANCED TOOL: This will delete all the current potential duplicate pairs and queue every eligible file up for another re-search.'
        text += '\n' * 2
        text += 'This can be useful if you know you have database damage and need to reset and re-search everything, or if you have accidentally searched too broadly and are now swamped with too many false positives. It is not useful for much else.'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'delete_potential_duplicate_pairs' )
            
            self._RefreshMaintenanceNumbers()
            
        
    
    def _ResyncPotentialPairsToHydrusLocalFileStorage( self ):
        
        text = 'There was a time that pairs were not delisted when one or both of the pair were deleted. This maintenance task corrects that problem. You should not need to run it again unless you know something is wrong with your numbers (they might just be incorrect, but if you set many trashed/deleted files to be part of potential pairs, this would also do it).'
        
        result = ClientGUIDialogsQuick.GetYesNo( self, text )
        
        if result == QW.QDialog.DialogCode.Accepted:
            
            CG.client_controller.Write( 'resync_potential_pairs_to_hydrus_local_file_storage' )
            
            self._RefreshMaintenanceNumbers()
            
        
    
    def _SetSearchDistance( self, value ):
        
        self._max_hamming_distance_for_potential_discovery_spinctrl.setValue( value )
        
        self._maintenance_status_updater.update()
        
    
    def _StartWorkingHard( self ):
        
        self._start_search_button.setVisible( False )
        self._pause_search_button.setVisible( True )
        
        CG.client_controller.potential_duplicates_manager.SetWorkHard( True )
        
    
    def _StopWorkingHard( self ):
        
        self._start_search_button.setVisible( True )
        self._pause_search_button.setVisible( False )
        
        CG.client_controller.potential_duplicates_manager.SetWorkHard( False )
        
    
    def _UpdateSearchStatus( self ):
        
        search_distance = CG.client_controller.new_options.GetInteger( 'similar_files_duplicate_pairs_search_distance' )
        
        if self._max_hamming_distance_for_potential_discovery_spinctrl.value() != search_distance:
            
            self._max_hamming_distance_for_potential_discovery_spinctrl.setValue( search_distance )
            
        
        if search_distance in CC.hamming_string_lookup:
            
            button_label = CC.hamming_string_lookup[ search_distance ]
            
        else:
            
            button_label = 'custom'
            
        
        if button_label != self._max_hamming_distance_for_potential_discovery_button.text():
            
            self._max_hamming_distance_for_potential_discovery_button.setText( button_label )
            
        
        is_working_hard = CG.client_controller.potential_duplicates_manager.IsWorkingHard()
        
        self._start_search_button.setVisible( not is_working_hard )
        self._pause_search_button.setVisible( is_working_hard )
        
    
    def MaxHammingDistanceForPotentialDiscoveryChanged( self ):
        
        search_distance = self._max_hamming_distance_for_potential_discovery_spinctrl.value()
        
        CG.client_controller.new_options.SetInteger( 'similar_files_duplicate_pairs_search_distance', search_distance )
        
        self._maintenance_status_updater.update()
        
        CG.client_controller.potential_duplicates_manager.Wake()
        
    
    def NotifyNewMaintenanceNumbers( self ):
        
        # note this thing is basically instant and we want the page name update so we are fine to call it even when we are not visible
        self._maintenance_status_updater.update()
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateSearchStatus()
        
    

class SidebarDuplicateFilter( ClientGUISidebarCore.Sidebar ):
    
    SHOW_COLLECT = False
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
        #
        
        self._main_notebook = ClientGUICommon.BetterNotebook( self )
        
        self._preparation_panel = PreparationPanel( self._main_notebook )
        self._filter_panel = FilterPanel( self._main_notebook, self._page_manager, self._media_sort_widget, self._MakeCurrentSelectionTagsBox )
        self._duplicates_auto_resolution_panel = ClientGUIDuplicatesAutoResolution.ReviewDuplicatesAutoResolutionPanel( self._main_notebook )
        
        #
        
        self._main_notebook.addTab( self._preparation_panel, 'preparation' )
        self._main_notebook.addTab( self._filter_panel, 'filtering' )
        self._main_notebook.addTab( self._duplicates_auto_resolution_panel, 'auto-resolution' )
        
        self._main_notebook.setCurrentWidget( self._filter_panel )
        
        #
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._main_notebook, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
        
        self.widget().setLayout( vbox )
        
        self._main_notebook.currentChanged.connect( self._CurrentPageChanged )
        
        self._CurrentPageChanged()
        
        self._preparation_panel.pageTabNameChanged.connect( self._RenamePreparationTabName )
        
        self._filter_panel.locationChanged.connect( self.locationChanged )
        self._filter_panel.tagContextChanged.connect( self.tagContextChanged )
        self._filter_panel.setCurrentMediaAs.connect( self._SetCurrentMediaAs )
        self._filter_panel.showPotentialDupes.connect( self.ShowPotentialDupes )
        self._filter_panel.setPageState.connect( self._SetPageState )
        self._filter_panel.showPairInPage.connect( self._ShowPairInPage )
        
    
    def _CurrentPageChanged( self ):
        
        page = self._main_notebook.currentWidget()
        
        if page == self._filter_panel:
            
            self._filter_panel.PageShown()
            
        else:
            
            self._filter_panel.PageHidden()
            
        
        if page == self._duplicates_auto_resolution_panel:
            
            self._duplicates_auto_resolution_panel.PageShown()
            
        else:
            
            self._duplicates_auto_resolution_panel.PageHidden()
            
        
    
    def _RenamePreparationTabName( self, page_name: str ):
        
        self._main_notebook.setTabText( 0, page_name )
        
    
    def _SetCurrentMediaAs( self, duplicate_type ):
        
        media_panel = self._page.GetMediaResultsPanel()
        
        change_made = media_panel.SetDuplicateStatusForAll( duplicate_type )
        
        if change_made:
            
            self._filter_panel.ShowRandomPotentialDupes()
            
        
    
    def _SetPageState( self, page_state: int ):
        
        self._page_state = page_state
        
    
    def _ShowPairInPage( self, media: collections.abc.Collection[ ClientMedia.MediaSingleton ] ):
        
        media_results = [ m.GetMediaResult() for m in media ]
        
        self._page.GetMediaResultsPanel().AddMediaResults( self._page_key, media_results )
        
    
    def PageHidden( self ):
        
        super().PageHidden()
        
        page = self._main_notebook.currentWidget()
        
        if page == self._filter_panel:
            
            self._filter_panel.PageHidden()
            
        elif page == self._duplicates_auto_resolution_panel:
            
            self._duplicates_auto_resolution_panel.PageHidden()
            
        
    
    def PageShown( self ):
        
        super().PageShown()
        
        page = self._main_notebook.currentWidget()
        
        if page == self._filter_panel:
            
            self._filter_panel.PageShown()
            
        elif page == self._duplicates_auto_resolution_panel:
            
            self._duplicates_auto_resolution_panel.PageShown()
            
        
    
    def RefreshQuery( self ):
        
        self._filter_panel.RefreshDuplicateNumbers()
        
    
    def ShowPotentialDupes( self, hashes ):
        
        if len( hashes ) > 0:
            
            media_results = CG.client_controller.Read( 'media_results', hashes, sorted = True )
            
        else:
            
            media_results = []
            
        
        panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
        
        panel.SetEmptyPageStatusOverride( 'no dupes found' )
        
        # panel.Collect( self._media_collect_widget.GetValue() ) hidden for now
        
        panel.Sort( self._media_sort_widget.GetSort() )
        
        self._page.SwapMediaResultsPanel( panel )
        
    
    def REPEATINGPageUpdate( self ):
        
        current_page = self._main_notebook.currentWidget()
        
        if current_page == self._preparation_panel:
            
            self._preparation_panel.REPEATINGPageUpdate()
            
        elif current_page == self._filter_panel:
            
            self._filter_panel.REPEATINGPageUpdate()
            
        
    
