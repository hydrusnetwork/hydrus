import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusLists

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.lists import ClientGUIListBoxes
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUIMediaResultsPanel
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelThumbnails
from hydrus.client.gui.pages import ClientGUIMediaResultsPanelSortCollect
from hydrus.client.gui.search import ClientGUIACDropdown
from hydrus.client.media import ClientMedia
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

class ListBoxTagsMediaSidebar( ClientGUIListBoxes.ListBoxTagsMedia ):
    
    def __init__( self, parent: QW.QWidget, page_manager: ClientGUIPageManager.PageManager, page_key, tag_display_type = ClientTags.TAG_DISPLAY_SELECTION_LIST, tag_autocomplete: typing.Optional[ ClientGUIACDropdown.AutoCompleteDropdownTagsRead ] = None ):
        
        super().__init__( parent, tag_display_type, CC.TAG_PRESENTATION_SEARCH_PAGE, include_counts = True )
        
        self._page_manager = page_manager
        self._minimum_height_num_chars = 15
        
        self._page_key = page_key
        self._tag_autocomplete = tag_autocomplete
        
    
    def _Activate( self, ctrl_down, shift_down ) -> bool:
        
        predicates = self._GetPredicatesFromTerms( self._selected_terms )
        
        if len( predicates ) > 0:
            
            if ctrl_down:
                
                predicates = [ predicate.GetInverseCopy() for predicate in predicates ]
                
            
            if shift_down and len( predicates ) > 1:
                
                predicates = ( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, value = predicates ), )
                
            
            CG.client_controller.pub( 'enter_predicates', self._page_key, predicates )
            
            return True
            
        
        return False
        
    
    def _CanProvideCurrentPagePredicates( self ):
        
        return self._tag_autocomplete is not None
        
    
    def _GetCurrentLocationContext( self ):
        
        return self._page_manager.GetLocationContext()
        
    
    def _GetCurrentPagePredicates( self ) -> set[ ClientSearchPredicate.Predicate ]:
        
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
            
            if or_predicate is None:
                
                return
                
            
            p = ( or_predicate, )
            permit_remove = False
            
        elif command == 'dissolve_or_predicate':
            
            or_preds = [ p for p in predicates if p.IsORPredicate() ]
            
            sub_preds = HydrusLists.MassUnion( [ p.GetValue() for p in or_preds ] )
            
            CG.client_controller.pub( 'enter_predicates', self._page_key, or_preds, permit_remove = True, permit_add = False )
            CG.client_controller.pub( 'enter_predicates', self._page_key, sub_preds, permit_remove = False, permit_add = True )
            
        elif command == 'replace_or_predicate':
            
            if or_predicate is None:
                
                return
                
            
            CG.client_controller.pub( 'enter_predicates', self._page_key, predicates, permit_remove = True, permit_add = False )
            CG.client_controller.pub( 'enter_predicates', self._page_key, ( or_predicate, ), permit_remove = False, permit_add = True )
            
        elif command == 'start_or_predicate':
            
            CG.client_controller.pub( 'enter_predicates', self._page_key, predicates, start_or_predicate = True )
            
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
            
        
    

class Sidebar( QW.QScrollArea ):
    
    locationChanged = QC.Signal( ClientLocation.LocationContext )
    tagContextChanged = QC.Signal( ClientSearchTagContext.TagContext )
    
    SHOW_COLLECT = True
    
    def __init__( self, parent, page, page_manager: ClientGUIPageManager.PageManager ):
        
        super().__init__( parent )
        
        self.setFrameShape( QW.QFrame.Shape.NoFrame )
        self.setWidget( QW.QWidget( self ) )
        self.setWidgetResizable( True )
        #self.setFrameStyle( QW.QFrame.Shape.Panel | QW.QFrame.Shadow.Sunken )
        #self.setLineWidth( 2 )
        self.setHorizontalScrollBarPolicy( QC.Qt.ScrollBarPolicy.ScrollBarAsNeeded )
        self.setVerticalScrollBarPolicy( QC.Qt.ScrollBarPolicy.ScrollBarAsNeeded )
        
        self._page_manager = page_manager
        
        # page here should be a data object not the UI widget, or an interface, to provide the various 'Get/AppendMediaResults' and such. the future version of MediaList
        self._page = page
        self._page_key = self._page_manager.GetVariable( 'page_key' )
        
        self._page_state = CC.PAGE_STATE_NORMAL
        
        self._current_selection_tags_list = None
        
        self._media_sort_widget = ClientGUIMediaResultsPanelSortCollect.MediaSortControl( self, media_sort = self._page_manager.GetVariable( 'media_sort' ) )
        
        if self._page_manager.HasVariable( 'media_collect' ):
            
            media_collect = self._page_manager.GetVariable( 'media_collect' )
            
        else:
            
            media_collect = ClientMedia.MediaCollect()
            
        
        self._media_collect_widget = ClientGUIMediaResultsPanelSortCollect.MediaCollectControl( self, media_collect = media_collect )
        
        if self.SHOW_COLLECT:
            
            self._media_collect_widget.collectChanged.connect( self._CollectChanged )
            
        else:
            
            self._media_collect_widget.hide()
            
        
        self._media_sort_widget.sortChanged.connect( self._SortChanged )
        
    
    def _CollectChanged( self, media_collect ):
        
        self._page_manager.SetVariable( 'media_collect', media_collect )
        
    
    def _GetDefaultEmptyPageStatusOverride( self ) -> str:
        
        return 'empty page'
        
    
    def _MakeCurrentSelectionTagsBox( self, sizer, tag_display_type = ClientTags.TAG_DISPLAY_SELECTION_LIST ):
        
        self._current_selection_tags_box = ClientGUIListBoxes.StaticBoxSorterForListBoxTags( self, 'selection tags', CC.TAG_PRESENTATION_SEARCH_PAGE )
        
        self._current_selection_tags_list = ListBoxTagsMediaSidebar( self._current_selection_tags_box, self._page_manager, self._page_key, tag_display_type = tag_display_type )
        
        self._current_selection_tags_box.SetTagsBox( self._current_selection_tags_list )
        
        QP.AddToLayout( sizer, self._current_selection_tags_box, CC.FLAGS_EXPAND_BOTH_WAYS )
        
    
    def _SortChanged( self, media_sort ):
        
        self._page_manager.SetVariable( 'media_sort', media_sort )
        
    
    def ConnectMediaResultsPanelSignals( self, media_panel: ClientGUIMediaResultsPanel.MediaResultsPanel ):
        
        if self._current_selection_tags_list is not None:
            
            media_panel.selectedMediaTagPresentationChanged.connect( self._current_selection_tags_list.SetTagsByMediaFromMediaResultsPanel )
            media_panel.selectedMediaTagPresentationIncremented.connect( self._current_selection_tags_list.IncrementTagsByMedia )
            self._media_collect_widget.collectChanged.connect( media_panel.Collect )
            self._media_sort_widget.sortChanged.connect( media_panel.Sort )
            
            media_panel.PublishSelectionChange()
            
        
    
    def CheckAbleToClose( self, for_session_close = False ):
        
        pass
        
    
    def CleanBeforeClose( self ):
        
        pass
        
    
    def CleanBeforeDestroy( self ):
        
        pass
        
    
    def GetDefaultEmptyMediaResultsPanel( self, win: QW.QWidget ) -> ClientGUIMediaResultsPanel.MediaResultsPanel:
        
        panel = ClientGUIMediaResultsPanelThumbnails.MediaResultsPanelThumbnails( win, self._page_key, self._page_manager, [] )
        
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
        
        if CG.client_controller.new_options.GetBoolean( 'set_search_focus_on_page_change' ):
            
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
        
    
