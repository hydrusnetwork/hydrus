from hydrus.core import HydrusLists
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientThreading
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIMediaResultsPanel
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelLoading
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelThumbnails
from hydrus.client.gui.pages import ClientGUISidebarCore
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.search import ClientSearchFileSearchContext

class SidebarQuery( ClientGUISidebarCore.Sidebar ):
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent, page, page_manager )
        
        file_search_context = self._page_manager.GetVariable( 'file_search_context' )
        
        file_search_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        self._search_enabled = self._page_manager.GetVariable( 'search_enabled' )
        
        self._query_job_status = ClientThreading.JobStatus( cancellable = True )
        
        self._query_job_status.Finish()
        
        if self._search_enabled:
            
            self._search_panel = ClientGUICommon.StaticBox( self, 'search' )
            
            synchronised = self._page_manager.GetVariable( 'synchronised' )
            
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
            
            panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, [] )
            
            panel.SetEmptyPageStatusOverride( 'search cancelled!' )
            
            self._page.SwapMediaResultsPanel( panel )
            
            self._page_state = CC.PAGE_STATE_SEARCHING_CANCELLED
            
            self._UpdateCancelButton()
            
        
    
    def _GetDefaultEmptyPageStatusOverride( self ) -> str:
        
        return 'no search done yet'
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer, **kwargs ):
        
        self._current_selection_tags_box = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( self, 'selection tags', CC.TAG_PRESENTATION_SEARCH_PAGE )
        
        if self._search_enabled:
            
            self._current_selection_tags_list = ClientGUISidebarCore.ListBoxTagsMediaSidebar( self._current_selection_tags_box, self._page_manager, self._page_key, tag_autocomplete = self._tag_autocomplete )
            
        else:
            
            self._current_selection_tags_list = ClientGUISidebarCore.ListBoxTagsMediaSidebar( self._current_selection_tags_box, self._page_manager, self._page_key )
            
        
        self._current_selection_tags_box.SetTagsBox( self._current_selection_tags_list )
        
        if self._search_enabled:
            
            file_search_context = self._page_manager.GetVariable( 'file_search_context' )
            
            file_search_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
            
            tag_service_key = file_search_context.GetTagContext().service_key
            
            self._current_selection_tags_box.SetTagServiceKey( tag_service_key )
            
            self._tag_autocomplete.tagServiceChanged.connect( self._current_selection_tags_box.SetTagServiceKey )
            
        
        QP.AddToLayout( sizer, self._current_selection_tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _RefreshQuery( self ):
        
        CG.client_controller.ResetIdleTimer()
        
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
                
                CG.client_controller.CallToThread( self.THREADDoQuery, self._page_manager, self._page_key, self._query_job_status, file_search_context, sort_by )
                
                panel = ClientGUIMediaResultsPanelLoading.MediaResultsPanelLoading( self._page, self._page_key, self._page_manager )
                
                self._page_state = CC.PAGE_STATE_SEARCHING
                
            else:
                
                panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, [] )
                
                panel.SetEmptyPageStatusOverride( 'no search' )
                
            
            self._page.SwapMediaResultsPanel( panel )
            
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
                
            
        
    
    def ConnectMediaResultsPanelSignals( self, media_panel: ClientGUIMediaResultsPanel.MediaResultsPanel ):
        
        super().ConnectMediaResultsPanelSignals( media_panel )
        
        media_panel.newMediaAdded.connect( self.PauseSearching )
        
    
    def SetLocationContext( self, location_context: ClientLocation.LocationContext ):
        
        self._SetLocationContext( location_context )
        
    
    def CleanBeforeClose( self ):
        
        super().CleanBeforeClose()
        
        if self._search_enabled:
            
            self._tag_autocomplete.CancelCurrentResultsFetchJob()
            
        
        self._query_job_status.Cancel()
        
    
    def CleanBeforeDestroy( self ):
        
        super().CleanBeforeDestroy()
        
        if self._search_enabled:
            
            self._tag_autocomplete.CancelCurrentResultsFetchJob()
            
        
        self._query_job_status.Cancel()
        
    
    def GetPredicates( self ):
        
        if self._search_enabled:
            
            return self._tag_autocomplete.GetPredicates()
            
        else:
            
            return []
            
        
    
    def PageHidden( self ):
        
        super().PageHidden()
        
        if self._search_enabled:
            
            self._tag_autocomplete.SetForceDropdownHide( True )
            
        
    
    def PageShown( self ):
        
        super().PageShown()
        
        if self._search_enabled:
            
            self._tag_autocomplete.SetForceDropdownHide( False )
            
        
    
    def PauseSearching( self ):
        
        if self._search_enabled:
            
            self._tag_autocomplete.SetSynchronised( False )
            
        
    
    def RefreshQuery( self ):
        
        self._RefreshQuery()
        
    
    def SearchChanged( self, file_search_context: ClientSearchFileSearchContext.FileSearchContext ):
        
        if self._search_enabled:
            
            file_search_context = self._tag_autocomplete.GetFileSearchContext()
            
            self._page_manager.SetVariable( 'file_search_context', file_search_context.Duplicate() )
            
            location_context = file_search_context.GetLocationContext()
            
            self._SetLocationContext( location_context )
            
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
        
        if self._search_enabled:
            
            ClientGUIFunctions.SetFocusLater( self._tag_autocomplete )
            
        
    
    def ShowFinishedQuery( self, query_job_status, media_results ):
        
        if query_job_status == self._query_job_status:
            
            location_context = self._page_manager.GetLocationContext()
            
            panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( self._page, self._page_key, self._page_manager, media_results )
            
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
            
            QP.CallAfter( self.RefreshQuery )
            
        
    
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
        
        for sub_query_hash_ids in HydrusLists.SplitListIntoChunks( query_hash_ids, QUERY_CHUNK_SIZE ):
            
            if query_job_status.IsCancelled():
                
                return
                
            
            more_media_results = CG.client_controller.Read( 'media_results_from_ids', sub_query_hash_ids )
            
            media_results.extend( more_media_results )
            
            CG.client_controller.pub( 'set_num_query_results', page_key, len( media_results ), len( query_hash_ids ) )
            
            CG.client_controller.WaitUntilViewFree()
            
        
        file_search_context.SetComplete()
        
        page_manager.SetVariable( 'file_search_context', file_search_context.Duplicate() )
        
        page_manager.SetDirty()
        
        QP.CallAfter( qt_code )
        
    
    def REPEATINGPageUpdate( self ):
        
        self._UpdateCancelButton()
        
        if self._search_enabled:
            
            self._tag_autocomplete.REPEATINGPageUpdate()
            
        
    
