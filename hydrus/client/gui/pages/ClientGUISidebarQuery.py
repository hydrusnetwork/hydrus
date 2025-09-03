import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIDialogsQuick
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIMediaResultsPanel
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelLoading
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelThumbnails
from hydrus.client.gui.pages import ClientGUISidebarCore
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.gui.widgets import ClientGUIMenuButton
from hydrus.client.media import ClientMedia
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate

class SystemHashLockPanel( ClientGUICommon.StaticBox ):
    
    unlockSearch = QC.Signal()
    newSettings = QC.Signal()
    
    def __init__( self, parent: QW.QWidget, syncs_new: bool, syncs_removes: bool, num_files: int ):
        
        super().__init__( parent, 'search locked' )
        
        desc_tt = 'The page\'s search is locked. If you click here, the page will unlock and the search will become a system:hash.'
        
        self._unlock_button = ClientGUICommon.BetterButton( self, 'initialising', self.unlockSearch.emit )
        self._unlock_button.setToolTip( ClientGUIFunctions.WrapToolTip( desc_tt ) )
        
        self._syncs_new = syncs_new
        self._syncs_removes = syncs_removes
        self._num_files = num_files
        
        menu_template_items = []
        
        check_manager = ClientGUICommon.CheckboxManagerCalls( self._FlipSyncsNew, lambda: self._syncs_new )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'update when files added to page', 'If this is checked, then the underlying system:hash behind this page will add new files that are added here.', check_manager ) )
        
        check_manager = ClientGUICommon.CheckboxManagerCalls( self._FlipSyncsRemoves, lambda: self._syncs_removes )
        
        menu_template_items.append( ClientGUIMenuButton.MenuTemplateItemCheck( 'update when files removed from page', 'If this is checked, then the underlying system:hash behind this page will remove files that are removed from here. If you want to remove files temporarily and then re-run the query to get them back again, uncheck this.', check_manager ) )
        
        self._cog_button = ClientGUIMenuButton.CogIconButton( self, menu_template_items )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._unlock_button, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._cog_button, CC.FLAGS_CENTER )
        
        self.Add( hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        
        self._UpdateLabel()
        
    
    def _FlipSyncsNew( self ):
        
        self._syncs_new = not self._syncs_new
        
        self.newSettings.emit()
        
    
    def _FlipSyncsRemoves( self ):
        
        self._syncs_removes = not self._syncs_removes
        
        self.newSettings.emit()
        
    
    def _UpdateLabel( self ):
        
        self._unlock_button.setText( f'Locked at {HydrusNumbers.ToHumanInt( self._num_files )} files.' )
        
    
    def GetSyncsNew( self ):
        
        return self._syncs_new
        
    
    def GetSyncsRemoves( self ):
        
        return self._syncs_removes
        
    
    def SetNumFiles( self, num_files: int ):
        
        self._num_files = num_files
        
        self._UpdateLabel()
        
    

class SidebarQuery( ClientGUISidebarCore.Sidebar ):
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
        file_search_context = self._page_manager.GetVariable( 'file_search_context' )
        
        file_search_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        self._query_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._query_job_status.Finish()
        
        self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
        
        synchronised = self._page_manager.GetVariable( 'synchronised' )
        
        self._tag_autocomplete = ClientGUIACDropdown.AutoCompleteDropdownTagsRead( self._search_panel, self._page_key, file_search_context, media_sort_widget = self._media_sort_widget, media_collect_widget = self._media_collect_widget, media_callable = self._page.GetMedia, synchronised = synchronised, show_lock_search_button = True )
        
        self._tag_autocomplete.searchCancelled.connect( self._CancelSearch )
        
        system_hash_locked_syncs_new = self._page_manager.GetVariable( 'system_hash_locked_syncs_new' )
        system_hash_locked_syncs_removes = self._page_manager.GetVariable( 'system_hash_locked_syncs_removes' )
        
        self._system_hash_lock_panel = SystemHashLockPanel( self._search_panel, system_hash_locked_syncs_new, system_hash_locked_syncs_removes, 0 )
        
        self._search_panel.Add( self._tag_autocomplete, CC.FLAGS_EXPAND_BOTH_WAYS )
        self._search_panel.Add( self._system_hash_lock_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, self._media_sort_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._media_collect_widget, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        QP.AddToLayout( vbox, self._search_panel, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self._MakeCurrentSelectionTagsBox( vbox )
        
        self.widget().setLayout( vbox )
        
        self._tag_autocomplete.searchChanged.connect( self.SearchChanged )
        
        self._tag_autocomplete.locationChanged.connect( self.locationChanged )
        
        self._tag_autocomplete.tagContextChanged.connect( self.tagContextChanged )
        
        self._tag_autocomplete.lockSearch.connect( self.LockSearch )
        self._system_hash_lock_panel.unlockSearch.connect( self.UnlockSearch )
        self._system_hash_lock_panel.newSettings.connect( self._UpdateNewLockSettings )
        
        self._UpdateSystemLockedVisibilityAndControls()
        
    
    def _CancelSearch( self ):
        
        self._query_job_status.Cancel()
        
        panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, [] )
        
        panel.SetEmptyPageStatusOverride( 'search cancelled!' )
        
        self._page.SwapMediaResultsPanel( panel )
        
        self._page_state = CC.PAGE_STATE_SEARCHING_CANCELLED
        
        self._UpdateCancelButton()
        
    
    def _GetDefaultEmptyPageStatusOverride( self ) -> str:
        
        return 'no search done yet'
        
    
    def _GetExistingLockHashes( self ):
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        predicates = file_search_context.GetPredicates()
        
        if len( predicates ) == 1:
            
            ( predicate, ) = predicates
            
            if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH:
                
                if predicate.IsInclusive():
                    
                    ( existing_hashes, hash_type ) = predicate.GetValue()
                    
                    if hash_type == 'sha256':
                        
                        return list( existing_hashes )
                        
                    
                
            
        
        return []
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer, **kwargs ):
        
        self._current_selection_tags_box = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( self, 'selection tags', CC.TAG_PRESENTATION_SEARCH_PAGE )
        
        self._current_selection_tags_list = ClientGUISidebarCore.ListBoxTagsMediaSidebar( self._current_selection_tags_box, self._page_manager, self._page_key, tag_autocomplete = self._tag_autocomplete )
        
        self._current_selection_tags_box.SetTagsBox( self._current_selection_tags_list )
        
        file_search_context = self._page_manager.GetVariable( 'file_search_context' )
        
        file_search_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        tag_service_key = file_search_context.GetTagContext().service_key
        
        self._current_selection_tags_box.SetTagServiceKey( tag_service_key )
        
        self._tag_autocomplete.tagContextChanged.connect( self._current_selection_tags_box.SetTagContext )
        
        QP.AddToLayout( sizer, self._current_selection_tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _RefreshQuery( self ):
        
        CG.client_controller.ResetIdleTimer()
        
        if self._page_manager.GetVariable( 'system_hash_locked' ):
            
            return
            
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        synchronised = self._tag_autocomplete.IsSynchronised()
        
        # a query refresh now undoes paused sync
        if not synchronised:
            
            # this will trigger a refresh of search
            self._tag_autocomplete.SetSynchronised( True )
            
            return
            
        
        self._query_job_status.Cancel()
        
        if len( file_search_context.GetPredicates() ) > 0:
            
            self._query_job_status = ClientThreading.JobStatus( cancellable = True )
            
            sort_by = self._media_sort_widget.GetSort()
            
            CG.client_controller.CallToThread( self.THREADDoQuery, self._page_manager, self._page_key, self._query_job_status, file_search_context, sort_by )
            
            panel = ClientGUIMediaResultsPanelLoading.MediaResultsPanelLoading( self._page, self._page_key, self._page_manager )
            
            self._page_state = CC.PAGE_STATE_SEARCHING
            
        else:
            
            panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, [] )
            
            panel.SetEmptyPageStatusOverride( 'no search' )
            
        
        self._page.SwapMediaResultsPanel( panel )
        
    
    def _SortChanged( self, media_sort: ClientMedia.MediaSort ):
        
        super()._SortChanged( media_sort )
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        if media_sort.CanSortAtDBLevel( file_search_context.GetLocationContext() ):
            
            if CG.client_controller.new_options.GetBoolean( 'refresh_search_page_on_system_limited_sort_changed' ) and self._tag_autocomplete.IsSynchronised() and file_search_context.GetSystemPredicates().HasSystemLimit():
                
                self._RefreshQuery()
                
            
        
    
    def _UpdateCancelButton( self ):
        
        if self._query_job_status.IsDone():
            
            self._tag_autocomplete.ShowCancelSearchButton( False )
            
        else:
            
            # don't show it immediately to save on flickeriness on short queries
            
            WAIT_PERIOD = 3.0
            
            search_is_lagging = HydrusTime.TimeHasPassedFloat( self._query_job_status.GetCreationTime() + WAIT_PERIOD )
            
            self._tag_autocomplete.ShowCancelSearchButton( search_is_lagging )
            
        
    
    def _UpdateNewLockSettings( self ):
        
        self._page_manager.SetVariable( 'system_hash_locked_syncs_new', self._system_hash_lock_panel.GetSyncsNew() )
        self._page_manager.SetVariable( 'system_hash_locked_syncs_removes', self._system_hash_lock_panel.GetSyncsRemoves() )
        
    
    def _UpdateSystemLockedVisibilityAndControls( self ):
        
        system_hash_locked = self._page_manager.GetVariable( 'system_hash_locked' )
        
        self._tag_autocomplete.setVisible( not system_hash_locked )
        self._system_hash_lock_panel.setVisible( system_hash_locked )
        
        if system_hash_locked:
            
            file_search_context = self._tag_autocomplete.GetFileSearchContext()
            
            predicates = file_search_context.GetPredicates()
            
            if len( predicates ) == 1:
                
                ( predicate, ) = predicates
                
                predicate = typing.cast( ClientSearchPredicate.Predicate, predicate )
                
                if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH:
                    
                    if predicate.IsInclusive():
                        
                        ( existing_hashes, hash_type ) = predicate.GetValue()
                        
                        self._system_hash_lock_panel.SetNumFiles( len( existing_hashes ) )
                        
                    
                
            
        
    
    def _UpdateSystemLockFiles( self, hashes ):
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext().Duplicate()
        
        predicate = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, ( tuple( hashes ), 'sha256' ) )
        
        file_search_context.SetPredicates( ( predicate, ) )
        
        self._tag_autocomplete.SetFileSearchContext( file_search_context )
        
        self._UpdateSystemLockedVisibilityAndControls()
        
    
    def ConnectMediaResultsPanelSignals( self, media_panel: ClientGUIMediaResultsPanel.MediaResultsPanel ):
        
        super().ConnectMediaResultsPanelSignals( media_panel )
        
        media_panel.newMediaAdded.connect( self.PauseSearching )
        media_panel.filesAdded.connect( self.NotifyFilesAdded )
        media_panel.filesRemoved.connect( self.NotifyFilesRemoved )
        
    
    def CleanBeforeClose( self ):
        
        super().CleanBeforeClose()
        
        self._tag_autocomplete.CancelCurrentResultsFetchJob()
        
        self._query_job_status.Cancel()
        
    
    def CleanBeforeDestroy( self ):
        
        super().CleanBeforeDestroy()
        
        self._tag_autocomplete.CancelCurrentResultsFetchJob()
        
        self._query_job_status.Cancel()
        
    
    def GetPredicates( self ):
        
        return self._tag_autocomplete.GetPredicates()
        
    
    def LockSearch( self ):
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        predicates = file_search_context.GetPredicates()
        
        do_yes_no = True
        
        hashes = [ m.GetHash() for m in ClientMedia.FlattenMedia( self._page.GetMedia() ) ]
        
        if len( predicates ) == 0:
            
            do_yes_no = False
            
        elif len( predicates ) == 1:
            
            ( predicate, ) = predicates
            
            predicate = typing.cast( ClientSearchPredicate.Predicate, predicate )
            
            if predicate.GetType() == ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH:
                
                if predicate.IsInclusive():
                    
                    ( existing_hashes, hash_type ) = predicate.GetValue()
                    
                    if hash_type == 'sha256':
                        
                        do_yes_no = False
                        
                        if set( existing_hashes ) != set( hashes ):
                            
                            text = 'This will lock the page, collapsing the current search to a system:hash of the current files.\n\nYour search already has a system:hash, but its files are different than what is currently in view. If you want to lock your current system:hash, not what is currently in view, click no and refresh the search to reset you back to what the existing system:hash says, and then try locking again.'
                            
                            result = ClientGUIDialogsQuick.GetYesNo( self, text )
                            
                            if result != QW.QDialog.DialogCode.Accepted:
                                
                                return
                                
                            
                        
                    
                
            
        
        if do_yes_no:
            
            text = 'This will lock the page, collapsing the current search to a system:hash of the current files. Is this ok?'
            
            result = ClientGUIDialogsQuick.GetYesNo( self, text )
            
            if result != QW.QDialog.DialogCode.Accepted:
                
                return
                
            
        
        self._page_manager.SetVariable( 'system_hash_locked', True )
        
        self._UpdateSystemLockFiles( hashes )
        
    
    def NotifyFilesAdded( self, hashes ):
        
        if self._page_manager.GetVariable( 'system_hash_locked' ) and self._page_manager.GetVariable( 'system_hash_locked_syncs_new' ):
            
            existing_lock_hashes = self._GetExistingLockHashes()
            
            updated_hashes = HydrusLists.DedupeList( existing_lock_hashes + hashes )
            
            self._UpdateSystemLockFiles( updated_hashes )
            
        
    
    def NotifyFilesRemoved( self, hashes ):
        
        if self._page_manager.GetVariable( 'system_hash_locked' ) and self._page_manager.GetVariable( 'system_hash_locked_syncs_removes' ):
            
            existing_lock_hashes = self._GetExistingLockHashes()
            
            fast_hashes = set( hashes )
            
            updated_hashes = [ hash for hash in existing_lock_hashes if hash not in fast_hashes ]
            
            self._UpdateSystemLockFiles( updated_hashes )
            
        
    
    def PageHidden( self ):
        
        super().PageHidden()
        
        self._tag_autocomplete.SetForceDropdownHide( True )
        
    
    def PageShown( self ):
        
        super().PageShown()
        
        self._tag_autocomplete.SetForceDropdownHide( False )
        
    
    def PauseSearching( self ):
        
        if not self._page_manager.GetVariable( 'system_hash_locked' ):
            
            self._tag_autocomplete.SetSynchronised( False )
            
        
    
    def RefreshQuery( self ):
        
        self._RefreshQuery()
        
    
    def SearchChanged( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext ):
        
        file_search_context = self._tag_autocomplete.GetFileSearchContext()
        
        self._page_manager.SetVariable( 'file_search_context', file_search_context.Duplicate() )
        
        self.locationChanged.emit( file_search_context.GetLocationContext() )
        self.tagContextChanged.emit( file_search_context.GetTagContext() )
        
        synchronised = self._tag_autocomplete.IsSynchronised()
        
        self._page_manager.SetVariable( 'synchronised', synchronised )
        
        self._page_manager.SetDirty()
        
        if synchronised:
            
            self._RefreshQuery()
            
        else:
            
            interrupting_current_search = not self._query_job_status.IsDone()
            
            if interrupting_current_search:
                
                self._CancelSearch()
                
            
        
    
    def SetSearchFocus( self ):
        
        ClientGUIFunctions.SetFocusLater( self._tag_autocomplete )
        
    
    def ShowFinishedQuery( self, query_job_status, media_results ):
        
        if query_job_status == self._query_job_status:
            
            location_context = self._page_manager.GetLocationContext()
            
            panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
            
            # little ugly, but whatever we out here for now
            panel.SetTagContext( self._tag_autocomplete.GetFileSearchContext().GetTagContext() )
            
            panel.SetEmptyPageStatusOverride( 'no files found for this search' )
            
            panel.Collect( self._media_collect_widget.GetValue() )
            
            panel.Sort( self._media_sort_widget.GetSort() )
            
            self._page.SwapMediaResultsPanel( panel )
            
            self._page_state = CC.PAGE_STATE_NORMAL
            
        
    
    def Start( self ):
        
        file_search_context = self._page_manager.GetVariable( 'file_search_context' )
        
        file_search_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        initial_predicates = file_search_context.GetPredicates()
        
        if len( initial_predicates ) > 0 and not file_search_context.IsComplete():
            
            CG.client_controller.CallAfter( self, self.RefreshQuery )
            
        
    
    def UnlockSearch( self ):
        
        self._page_manager.SetVariable( 'system_hash_locked', False )
        
        self._UpdateSystemLockedVisibilityAndControls()
        
    
    def THREADDoQuery( self, page_manager, page_key, query_job_status, file_search_context: ClientSearchFileSearchContext.FileSearchContext, sort_by ):
        
        def qt_code():
            
            query_job_status.Finish()
            
            if not self or not QP.isValid( self ):
                
                return
                
            
            self.ShowFinishedQuery( query_job_status, media_results )
            
        
        QUERY_CHUNK_SIZE = 256
        
        CG.client_controller.file_viewing_stats_manager.Flush()
        
        query_hash_ids = CG.client_controller.Read( 'file_query_ids', file_search_context, job_status = query_job_status, limit_sort_by = sort_by )
        
        if query_job_status.IsCancelled():
            
            return
            
        
        media_results = []
        
        for ( num_done, num_to_do, sub_query_hash_ids ) in HydrusLists.SplitListIntoChunksRich( query_hash_ids, QUERY_CHUNK_SIZE ):
            
            if query_job_status.IsCancelled():
                
                return
                
            
            more_media_results = CG.client_controller.Read( 'media_results_from_ids', sub_query_hash_ids )
            
            media_results.extend( more_media_results )
            
            CG.client_controller.pub( 'set_num_query_results', page_key, num_done, num_to_do )
            
            CG.client_controller.WaitUntilViewFree()
            
        
        file_search_context.SetComplete()
        
        page_manager.SetVariable( 'file_search_context', file_search_context.Duplicate() )
        
        page_manager.SetDirty()
        
        CG.client_controller.CallAfter( self, qt_code )
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateCancelButton()
        
        self._tag_autocomplete.REPEATINGPageUpdate()
        
    
